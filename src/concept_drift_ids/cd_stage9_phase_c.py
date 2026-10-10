from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np

from concept_drift_ids.cd_control_plane import canonical_sha256, write_json_new
from concept_drift_ids.cd_evidence import read_jsonl
from concept_drift_ids.cd_primary_adapter import EXPECTED_PRE_ROWS, load_primary_stream
from concept_drift_ids.cd_primary_phase_c import (
    _evaluation_for_weight,
    _explanation_by_domain,
    _metrics_by_domain,
    _recovery_summary,
    _rule_version_ids,
    _window_summaries,
    _write_trace_gzip_new,
)
from concept_drift_ids.cd_runtime import configure_torch_primary_runtime
from concept_drift_ids.cd_stage9_config import (
    PRIMARY_SEEDS,
    STAGE9_OUTPUT_ROOT,
    verify_stage9_config_for_execution,
)
from concept_drift_ids.cd_stage9_offline import _verified_trace as verified_stage8_trace
from concept_drift_ids.cd_stage9_phase_a import (
    _seed_dir as phase_a_seed_dir,
    adaptive_condition_ids,
    control_plane_for_condition,
    verify_stage9_phase_a_seed,
)
from concept_drift_ids.cd_stage9_phase_b import (
    ARM_NAMES,
    GATE_CONDITIONS,
    _phase_a_dir,
    _phase_b_dir,
    _verify_phase_a_source,
    load_stage9_arm_trajectory,
    verify_stage9_phase_b_seed,
)
from concept_drift_ids.cd_symbolic_evaluation import (
    PRIMARY_NEURAL_WEIGHT,
    SymbolicArmEvaluation,
    evaluate_dynamic_symbolic_trajectory,
    fused_threshold,
    verify_lambda_one_negative_control,
)
from concept_drift_ids.frozen_preprocessing import load_frozen_preprocessing
from concept_drift_ids.scenario_manifest import sha256_file


STAGE9_PHASE_C_SUBDIR = "phase_c_offline_evaluation"


def _phase_c_dir(condition: str, seed: int) -> Path:
    return (
        STAGE9_OUTPUT_ROOT
        / condition
        / STAGE9_PHASE_C_SUBDIR
        / f"seed-{seed}"
    )


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_verified_json(path: Path) -> dict[str, Any]:
    payload = _read_json(path)
    stored_payload = payload.pop("payload_sha256", None)
    if stored_payload is not None and canonical_sha256(payload) != stored_payload:
        raise ValueError(f"JSON payload hash mismatch: {path}")
    return payload


def _enabled_scoring_conditions(config: Mapping[str, Any]) -> tuple[str, ...]:
    return adaptive_condition_ids(config) + tuple(GATE_CONDITIONS)


def _arm_manifest(condition: str, seed: int, arm: str) -> dict[str, Any]:
    path = _phase_b_dir(condition, seed) / arm / "arm_manifest.json"
    payload = _read_verified_json(path)
    stored = payload.get("manifest_sha256")
    core = dict(payload)
    core.pop("manifest_sha256", None)
    if stored != canonical_sha256(core):
        raise ValueError("Stage-9 Phase-B arm manifest identity mismatch.")
    return payload


def _trigger_diagnostics(
    events: Sequence[Mapping[str, Any]],
    *,
    label_latency: int,
) -> dict[str, Any]:
    drift = sorted(
        (
            event
            for event in events
            if event.get("event_type") == "drift_event"
            and event.get("status") == "confirmed"
        ),
        key=lambda item: int(item["logical_clock"]),
    )
    pre = [
        int(item["logical_clock"])
        for item in drift
        if int(item["logical_clock"]) < EXPECTED_PRE_ROWS
    ]
    post = [
        int(item["logical_clock"])
        for item in drift
        if int(item["logical_clock"]) >= EXPECTED_PRE_ROWS
    ]
    first_post = post[0] if post else None
    publications = [
        event
        for event in events
        if event.get("event_type") == "neural_publication"
        and event.get("status") == "published"
    ]
    return {
        "detector_event_count": len(drift),
        "pre_reference_alarm_count": len(pre),
        "pre_reference_alarm_clocks": pre,
        "post_reference_event_count": len(post),
        "first_post_reference_confirmation_clock": first_post,
        "first_post_reference_confirmation_delay_rows": (
            first_post - EXPECTED_PRE_ROWS if first_post is not None else None
        ),
        "label_latency": int(label_latency),
        "latency_adjusted_excess_delay_rows": (
            first_post - (EXPECTED_PRE_ROWS + int(label_latency))
            if first_post is not None
            else None
        ),
        "repeated_post_reference_events": max(0, len(post) - 1),
        "neural_publication_count": len(publications),
    }


def execute_stage9_phase_c_seed(condition: str, seed: int) -> dict[str, Any]:
    if seed not in PRIMARY_SEEDS:
        raise ValueError(f"Unsupported Stage-9 seed: {seed}")
    config = verify_stage9_config_for_execution()
    if condition not in _enabled_scoring_conditions(config):
        raise ValueError("Stage-9 Phase-C condition is not enabled.")
    configure_torch_primary_runtime()

    phase_a_verified = {
        other: _verify_phase_a_source(condition, other, config)
        for other in PRIMARY_SEEDS
    }
    phase_b_verified = {
        other: verify_stage9_phase_b_seed(condition, other, config=config)
        for other in PRIMARY_SEEDS
    }

    output_dir = _phase_c_dir(condition, seed)
    if output_dir.exists():
        raise FileExistsError(f"Refusing to reuse Stage-9 Phase-C output: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=False)
    write_json_new(
        output_dir / "attempt.json",
        {
            "condition_id": condition,
            "seed": seed,
            "stage9_config_manifest_sha256": config["manifest_sha256"],
            "phase": "offline_boundary_aware_evaluation",
            "adaptive_components_received_boundary": False,
        },
    )

    try:
        phase_a_dir = _phase_a_dir(condition, seed)
        predictions = read_jsonl(phase_a_dir / "predictions.jsonl")
        events = read_jsonl(phase_a_dir / "events.jsonl")
        preprocessing = load_frozen_preprocessing()
        stream_rows = load_primary_stream(preprocessing=preprocessing)
        X = np.stack(
            [np.asarray(row.features, dtype=np.float32) for row in stream_rows]
        )
        y = np.asarray([int(row.label) for row in stream_rows], dtype=np.int8)
        neural_probability = np.asarray(
            [float(item["neural_probability"]) for item in predictions],
            dtype=np.float64,
        )
        checkpoint_ids = [str(item["checkpoint_sha256"]) for item in predictions]
        if len(X) != int(config["scenario"]["stream_rows"]):
            raise ValueError("Stage-9 Phase-C stream length changed.")

        arm_summaries: dict[str, Any] = {}
        lambda_one: dict[str, SymbolicArmEvaluation] = {}
        primary_c_trace = (
            verified_stage8_trace(seed, "c_frozen_symbolic")
            if condition in GATE_CONDITIONS
            else None
        )

        for arm in ARM_NAMES:
            trajectory = load_stage9_arm_trajectory(condition, seed, arm)
            base = evaluate_dynamic_symbolic_trajectory(
                seed=seed,
                X=X,
                y_true=y,
                neural_probability=neural_probability,
                feature_names=preprocessing.feature_columns,
                trajectory=trajectory,
                neural_weight=PRIMARY_NEURAL_WEIGHT,
            )
            neural_only = _evaluation_for_weight(
                seed=seed,
                base=base,
                y_true=y,
                weight=1.0,
            )
            lambda_one[arm] = neural_only

            if arm == "c_frozen_symbolic" and primary_c_trace is not None:
                if len(primary_c_trace) != len(y):
                    raise ValueError("Static-gate C reference row count changed.")
                for index, frozen in enumerate(primary_c_trace):
                    if int(frozen["decision_lambda_0_5"]) != int(
                        base.thresholded_decision[index]
                    ):
                        raise ValueError(
                            "Static-gate C decision differs from frozen Stage-8 C."
                        )
                    if float(frozen["fused_probability_lambda_0_5"]) != float(
                        base.fused_probability[index]
                    ):
                        raise ValueError(
                            "Static-gate C fused score differs from frozen Stage-8 C."
                        )
                    if bool(frozen["covered"]) != bool(base.covered[index]):
                        raise ValueError(
                            "Static-gate C coverage differs from frozen Stage-8 C."
                        )
                    if int(frozen["symbolic_class"]) != int(base.symbolic_class[index]):
                        raise ValueError(
                            "Static-gate C symbolic class differs from frozen Stage-8 C."
                        )

            primary_threshold = fused_threshold(
                seed=seed,
                neural_weight=PRIMARY_NEURAL_WEIGHT,
            )
            neural_threshold = fused_threshold(seed=seed, neural_weight=1.0)
            metrics = {
                "0.5": _metrics_by_domain(
                    y=y,
                    probability=base.fused_probability,
                    decision=base.thresholded_decision,
                    threshold=primary_threshold,
                ),
                "1.0": _metrics_by_domain(
                    y=y,
                    probability=neural_only.fused_probability,
                    decision=neural_only.thresholded_decision,
                    threshold=neural_threshold,
                ),
            }
            explanation = _explanation_by_domain(y=y, evaluation=base)
            windows = _window_summaries(
                y=y,
                evaluation=base,
                threshold=primary_threshold,
            )
            recovery = _recovery_summary(windows)
            versions = _rule_version_ids(trajectory, len(y))

            def trace_rows() -> Iterable[dict[str, Any]]:
                for index in range(len(y)):
                    symbolic_probability = (
                        None
                        if np.isnan(base.symbolic_attack_probability[index])
                        else float(base.symbolic_attack_probability[index])
                    )
                    yield {
                        "row_id": stream_rows[index].row_id,
                        "origin_index": index,
                        "true_label": int(y[index]),
                        "neural_checkpoint_sha256": checkpoint_ids[index],
                        "rule_base_version_id": versions[index],
                        "neural_probability": float(neural_probability[index]),
                        "symbolic_attack_probability": symbolic_probability,
                        "symbolic_class": int(base.symbolic_class[index]),
                        "covered": bool(base.covered[index]),
                        "uncovered": bool(base.uncovered[index]),
                        "conflict_abstain": bool(base.conflict_abstain[index]),
                        "fused_probability_lambda_0_5": float(
                            base.fused_probability[index]
                        ),
                        "decision_lambda_0_5": int(base.thresholded_decision[index]),
                        "fused_probability_lambda_1_0": float(
                            neural_only.fused_probability[index]
                        ),
                        "decision_lambda_1_0": int(
                            neural_only.thresholded_decision[index]
                        ),
                    }

            trace_path = output_dir / f"{arm}_prediction_trace.jsonl.gz"
            trace_identity = _write_trace_gzip_new(trace_path, trace_rows())
            arm_manifest = _arm_manifest(condition, seed, arm)
            summary = {
                "seed": seed,
                "condition_id": condition,
                "arm": arm,
                "stage9_config_manifest_sha256": config["manifest_sha256"],
                "phase_b_arm_manifest_sha256": arm_manifest["manifest_sha256"],
                "shared_identity_sha256": trajectory.shared_identity_sha256,
                "metrics_by_neural_weight": metrics,
                "explanation": explanation,
                "primary_windows": windows,
                "primary_recovery": recovery,
                "maintenance_summary": arm_manifest["maintenance_summary"],
                "prediction_trace": {
                    "path": trace_path.name,
                    "row_count": len(y),
                    **trace_identity,
                },
            }
            summary["summary_sha256"] = canonical_sha256(summary)
            write_json_new(output_dir / f"{arm}_evaluation.json", summary)
            arm_summaries[arm] = summary

        verify_lambda_one_negative_control(
            lambda_one["c_frozen_symbolic"], lambda_one["d_drift"]
        )
        verify_lambda_one_negative_control(
            lambda_one["c_frozen_symbolic"], lambda_one["d_periodic"]
        )

        latency = (
            int(config["conditions"]["adaptive"][condition]["label_latency"])
            if condition in config["conditions"]["adaptive"]
            else 5000
        )
        trigger = _trigger_diagnostics(events, label_latency=latency)
        seed_manifest = {
            "schema_version": 1,
            "seed": seed,
            "condition_id": condition,
            "status": "complete_stage9_offline_evaluation",
            "stage9_config_manifest_sha256": config["manifest_sha256"],
            "phase_a_run_manifest_sha256": phase_a_verified[seed][
                "run_manifest_sha256"
            ],
            "phase_b_seed_manifest_sha256": phase_b_verified[seed][
                "phase_b_manifest_sha256"
            ],
            "arm_summary_sha256": {
                arm: summary["summary_sha256"]
                for arm, summary in arm_summaries.items()
            },
            "lambda_one_predictive_equality": True,
            "trigger_diagnostics": trigger,
            "boundary_index": EXPECTED_PRE_ROWS,
            "adaptive_components_received_boundary": False,
        }
        seed_manifest["manifest_sha256"] = canonical_sha256(seed_manifest)
        write_json_new(output_dir / "phase_c_seed_manifest.json", seed_manifest)
        verified = verify_stage9_phase_c_seed(condition, seed, config=config)
        return {
            "status": "stage9_phase_c_seed_complete",
            "condition_id": condition,
            "seed": seed,
            "phase_c_manifest_sha256": verified["phase_c_manifest_sha256"],
            "lambda_one_predictive_equality": True,
        }
    except Exception as exc:
        failure_path = output_dir / "failure.json"
        if not failure_path.exists():
            write_json_new(
                failure_path,
                {
                    "condition_id": condition,
                    "seed": seed,
                    "exception_type": type(exc).__name__,
                    "message": str(exc),
                    "phase": "offline_boundary_aware_evaluation",
                    "adaptive_components_received_boundary": False,
                },
            )
        raise


def verify_stage9_phase_c_seed(
    condition: str,
    seed: int,
    *,
    config: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if config is None:
        config = verify_stage9_config_for_execution()
    if condition not in _enabled_scoring_conditions(config):
        raise ValueError("Stage-9 Phase-C condition is not enabled.")

    output_dir = _phase_c_dir(condition, seed)
    manifest = _read_verified_json(output_dir / "phase_c_seed_manifest.json")
    stored = manifest.pop("manifest_sha256", None)
    if stored != canonical_sha256(manifest):
        raise ValueError("Stage-9 Phase-C seed manifest hash mismatch.")
    if int(manifest["seed"]) != seed or manifest["condition_id"] != condition:
        raise ValueError("Stage-9 Phase-C seed/condition mismatch.")
    if manifest["stage9_config_manifest_sha256"] != config["manifest_sha256"]:
        raise ValueError("Stage-9 Phase-C references wrong config.")

    phase_a = _verify_phase_a_source(condition, seed, config)
    phase_b = verify_stage9_phase_b_seed(condition, seed, config=config)
    if manifest["phase_a_run_manifest_sha256"] != phase_a["run_manifest_sha256"]:
        raise ValueError("Stage-9 Phase-C Phase-A identity mismatch.")
    if manifest["phase_b_seed_manifest_sha256"] != phase_b["phase_b_manifest_sha256"]:
        raise ValueError("Stage-9 Phase-C Phase-B identity mismatch.")
    if manifest["lambda_one_predictive_equality"] is not True:
        raise ValueError("Stage-9 lambda=1 control failed.")
    if manifest["adaptive_components_received_boundary"] is not False:
        raise ValueError("Stage-9 boundary-contamination flag failed.")

    phase_b_root = _phase_b_dir(condition, seed)
    phase_b_manifest = _read_verified_json(phase_b_root / "phase_b_manifest.json")
    expected_shared = phase_a["shared_identity_sha256"]

    for arm in ARM_NAMES:
        summary = _read_verified_json(output_dir / f"{arm}_evaluation.json")
        stored_summary = summary.pop("summary_sha256", None)
        if stored_summary != canonical_sha256(summary):
            raise ValueError("Stage-9 arm evaluation summary hash mismatch.")
        if stored_summary != manifest["arm_summary_sha256"][arm]:
            raise ValueError("Stage-9 arm summary manifest binding mismatch.")
        if summary["shared_identity_sha256"] != expected_shared:
            raise ValueError("Stage-9 scored arm detached from shared Phase A.")
        descriptor = phase_b_manifest["arms"][arm]
        if summary["phase_b_arm_manifest_sha256"] != descriptor["manifest_sha256"]:
            raise ValueError("Stage-9 scored arm detached from Phase B.")
        arm_manifest = _read_verified_json(
            phase_b_root / str(descriptor["path"])
        )
        if summary["maintenance_summary"] != arm_manifest["maintenance_summary"]:
            raise ValueError("Stage-9 maintenance summary diverges from Phase B.")

        trace = summary["prediction_trace"]
        trace_path = output_dir / str(trace["path"])
        if sha256_file(trace_path) != trace["sha256"]:
            raise ValueError("Stage-9 prediction trace raw hash mismatch.")
        digest = hashlib.sha256()
        with gzip.open(trace_path, "rb") as file:
            while True:
                chunk = file.read(1024 * 1024)
                if not chunk:
                    break
                digest.update(chunk)
        if digest.hexdigest() != trace["canonical_jsonl_sha256"]:
            raise ValueError("Stage-9 prediction trace content hash mismatch.")
        with gzip.open(trace_path, "rt", encoding="utf-8") as file:
            row_count = sum(1 for line in file if line.strip())
        if row_count != int(config["scenario"]["stream_rows"]):
            raise ValueError("Stage-9 prediction trace row count mismatch.")

    return {
        "status": "stage9_phase_c_seed_verified",
        "condition_id": condition,
        "seed": seed,
        "phase_c_manifest_sha256": stored,
        "lambda_one_predictive_equality": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--condition", required=True)
    parser.add_argument("--seed", type=int, required=True, choices=PRIMARY_SEEDS)
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    result = (
        verify_stage9_phase_c_seed(args.condition, args.seed)
        if args.verify_only
        else execute_stage9_phase_c_seed(args.condition, args.seed)
    )
    print(json.dumps(result, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
