from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
from pathlib import Path
from statistics import mean, median, stdev
from typing import Any, Iterable, Mapping, Sequence

import numpy as np
from scipy.stats import t

from concept_drift_ids.cd_control_plane import canonical_sha256, write_json_new
from concept_drift_ids.cd_evidence import read_jsonl
from concept_drift_ids.cd_primary_adapter import EXPECTED_PRE_ROWS, load_primary_stream
from concept_drift_ids.cd_primary_phase_c import (
    _evaluation_for_weight,
    _explanation_by_domain,
    _metrics_by_domain,
    _recovery_summary,
    _rule_version_ids,
    _safe_binary_metrics,
    _safe_explanation,
    _window_summaries,
)
from concept_drift_ids.cd_runtime import configure_torch_primary_runtime
from concept_drift_ids.cd_stage9_config import (
    PRIMARY_BOUNDARY_INDEX,
    PRIMARY_COMPACT_ROOT,
    PRIMARY_SEEDS,
    PRIMARY_STREAM_ROWS,
    PROJECT_ROOT,
    STAGE9_OUTPUT_ROOT,
    verify_stage9_config_for_execution,
)
from concept_drift_ids.cd_stage9_symbolic import (
    ARM_NAMES,
    SYMBOLIC_CONDITIONS,
    _load_arm,
    _phase_a_dir,
    _phase_b_dir,
    verify_stage9_symbolic_seed,
)
from concept_drift_ids.cd_symbolic_evaluation import (
    PRIMARY_NEURAL_WEIGHT,
    evaluate_dynamic_symbolic_trajectory,
    fused_threshold,
    verify_lambda_one_negative_control,
)
from concept_drift_ids.frozen_preprocessing import load_frozen_preprocessing
from concept_drift_ids.scenario_manifest import sha256_file
from concept_drift_ids.symbolic import reporting_windows


OFFLINE_CONDITIONS = (
    "O_LAMBDA_070",
    "O_LAMBDA_090",
    "O_LAMBDA_100",
    "O_WINDOW_2500",
    "O_WINDOW_10000",
)
NEW_TRAJECTORY_CONDITIONS = SYMBOLIC_CONDITIONS
EVALUATION_CONDITIONS = (*OFFLINE_CONDITIONS, *NEW_TRAJECTORY_CONDITIONS)

PRIMARY_HEAVY_PHASE_C_ROOT = (
    PROJECT_ROOT
    / "artifacts"
    / "cd_primary_v1"
    / "phase_c_offline_evaluation_v1_1"
)
PRIMARY_COMPACT_PHASE_C_ROOT = (
    PRIMARY_COMPACT_ROOT / "phase_c_offline_evaluation_v1_1"
)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _verified_writer_json(path: Path) -> dict[str, Any]:
    payload = _read_json(path)
    stored = payload.pop("payload_sha256", None)
    if stored is not None and stored != canonical_sha256(payload):
        raise ValueError(f"JSON writer payload hash mismatch: {path}")
    return payload


def _evaluation_root(condition_id: str) -> Path:
    if condition_id in OFFLINE_CONDITIONS:
        return STAGE9_OUTPUT_ROOT / "offline" / condition_id
    if condition_id == "G_STATIC_GATE":
        return (
            STAGE9_OUTPUT_ROOT
            / "symbolic_gate"
            / condition_id
            / "phase_c_offline_evaluation"
        )
    return (
        STAGE9_OUTPUT_ROOT
        / "adaptive"
        / condition_id
        / "phase_c_offline_evaluation"
    )


def _seed_dir(condition_id: str, seed: int) -> Path:
    return _evaluation_root(condition_id) / f"seed-{seed}"


def _write_trace_gzip_new(
    path: Path,
    rows: Iterable[Mapping[str, Any]],
) -> dict[str, str]:
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite Stage-9 trace: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    content_digest = hashlib.sha256()
    with path.open("xb") as raw:
        with gzip.GzipFile(
            filename="",
            mode="wb",
            fileobj=raw,
            compresslevel=9,
            mtime=0,
        ) as compressed:
            for row in rows:
                line = (
                    json.dumps(
                        dict(row),
                        sort_keys=True,
                        separators=(",", ":"),
                        allow_nan=False,
                    )
                    + "\n"
                ).encode("utf-8")
                content_digest.update(line)
                compressed.write(line)
    return {
        "sha256": sha256_file(path),
        "canonical_jsonl_sha256": content_digest.hexdigest(),
    }


def _read_verified_primary_trace(seed: int, arm: str) -> list[dict[str, Any]]:
    compact = _verified_writer_json(
        PRIMARY_COMPACT_PHASE_C_ROOT / f"seed-{seed}" / f"{arm}_evaluation.json"
    )
    descriptor = compact["prediction_trace"]
    path = (
        PRIMARY_HEAVY_PHASE_C_ROOT
        / f"seed-{seed}"
        / str(descriptor["path"])
    )
    if not path.is_file():
        raise FileNotFoundError(
            f"Missing frozen heavy Stage-8 trace required for window sensitivity: {path}"
        )
    if sha256_file(path) != descriptor["sha256"]:
        raise ValueError("Frozen Stage-8 prediction trace raw hash mismatch.")

    rows: list[dict[str, Any]] = []
    digest = hashlib.sha256()
    with gzip.open(path, "rb") as handle:
        for raw_line in handle:
            digest.update(raw_line)
            rows.append(json.loads(raw_line.decode("utf-8")))
    if digest.hexdigest() != descriptor["canonical_jsonl_sha256"]:
        raise ValueError("Frozen Stage-8 prediction trace canonical hash mismatch.")
    if len(rows) != int(descriptor["row_count"]) or len(rows) != PRIMARY_STREAM_ROWS:
        raise ValueError("Frozen Stage-8 prediction trace row count mismatch.")
    return rows


def _window_summary_from_trace(
    rows: Sequence[Mapping[str, Any]],
    *,
    window_size: int,
    seed: int,
) -> dict[str, Any]:
    if window_size not in {2_500, 10_000}:
        raise ValueError("Unsupported Stage-9 reporting-window size.")
    y = np.asarray([int(row["true_label"]) for row in rows], dtype=np.int8)
    probability = np.asarray(
        [float(row["fused_probability_lambda_0_5"]) for row in rows],
        dtype=np.float64,
    )
    decision = np.asarray(
        [int(row["decision_lambda_0_5"]) for row in rows],
        dtype=np.int8,
    )
    symbolic_class = np.asarray(
        [int(row["symbolic_class"]) for row in rows],
        dtype=np.int8,
    )
    covered = np.asarray([bool(row["covered"]) for row in rows], dtype=bool)
    uncovered = np.asarray([bool(row["uncovered"]) for row in rows], dtype=bool)
    conflict = np.asarray(
        [bool(row["conflict_abstain"]) for row in rows],
        dtype=bool,
    )
    threshold = fused_threshold(seed=seed, neural_weight=PRIMARY_NEURAL_WEIGHT)

    windows: dict[str, list[dict[str, Any]]] = {"pre": [], "post": []}
    for domain, start, stop in (
        ("pre", 0, PRIMARY_BOUNDARY_INDEX),
        ("post", PRIMARY_BOUNDARY_INDEX, len(rows)),
    ):
        for local_start, local_stop in reporting_windows(
            stop - start,
            window_size=window_size,
            min_remainder=1_000,
        ):
            absolute_start = start + local_start
            absolute_stop = start + local_stop
            s = slice(absolute_start, absolute_stop)
            detection = _safe_binary_metrics(y[s], probability[s], threshold)
            # Verify the frozen decision vector is exactly the thresholded score.
            expected = (probability[s] >= threshold).astype(np.int8)
            if not np.array_equal(expected, decision[s]):
                raise ValueError("Frozen Stage-8 trace decision/threshold mismatch.")
            explanation = _safe_explanation(
                y[s],
                symbolic_class=symbolic_class[s],
                covered=covered[s],
                uncovered=uncovered[s],
                conflict=conflict[s],
            )
            windows[domain].append(
                {
                    "start_index": absolute_start,
                    "end_index_exclusive": absolute_stop,
                    "row_count": absolute_stop - absolute_start,
                    "mcc": detection["mcc"],
                    "fpr": detection["fpr"],
                    "f1": detection["f1"],
                    "mcsc": explanation["mcsc"],
                    "resolved_coverage": explanation["resolved_coverage"],
                    "conflict_abstain_rate": explanation["conflict_abstain_rate"],
                }
            )

    return {
        "window_size": window_size,
        "min_remainder": 1_000,
        "windows": windows,
        "recovery": _recovery_summary(windows),
    }


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
        if int(item["logical_clock"]) < PRIMARY_BOUNDARY_INDEX
    ]
    post = [
        int(item["logical_clock"])
        for item in drift
        if int(item["logical_clock"]) >= PRIMARY_BOUNDARY_INDEX
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
            first_post - PRIMARY_BOUNDARY_INDEX
            if first_post is not None
            else None
        ),
        "latency_adjusted_excess_delay_rows": (
            first_post - (PRIMARY_BOUNDARY_INDEX + int(label_latency))
            if first_post is not None
            else None
        ),
        "repeated_post_reference_events": max(0, len(post) - 1),
        "neural_publication_count": len(publications),
    }


def _post_endpoint(summary: Mapping[str, Any], metric: str) -> float:
    if metric == "mcc":
        return float(summary["metrics"]["post"]["mcc"])
    if metric == "mcsc":
        value = summary["explanation"]["post"]["mcsc"]
        if value is None:
            raise ValueError("Post MCSC is undefined.")
        return float(value)
    raise ValueError(metric)


def _new_trajectory_seed(condition_id: str, seed: int) -> dict[str, Any]:
    config = verify_stage9_config_for_execution()
    configure_torch_primary_runtime()

    # Outcome access is allowed only after every seed's symbolic treatment is frozen.
    phase_b_verified = {
        other: verify_stage9_symbolic_seed(condition_id, other, config=config)
        for other in PRIMARY_SEEDS
    }

    output_dir = _seed_dir(condition_id, seed)
    if output_dir.exists():
        raise FileExistsError(f"Refusing to reuse Stage-9 evaluation output: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=False)
    write_json_new(
        output_dir / "attempt.json",
        {
            "condition_id": condition_id,
            "seed": seed,
            "stage9_config_manifest_sha256": config["manifest_sha256"],
            "phase": "offline_boundary_aware_evaluation",
            "adaptive_components_received_boundary": False,
            "all_five_symbolic_seeds_frozen_before_scoring": True,
        },
    )

    try:
        phase_a_dir = _phase_a_dir(condition_id, seed)
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
        if len(y) != PRIMARY_STREAM_ROWS or len(predictions) != PRIMARY_STREAM_ROWS:
            raise ValueError("Stage-9 scoring stream length changed.")

        arm_summaries: dict[str, Any] = {}
        lambda_one: dict[str, Any] = {}
        primary_threshold = fused_threshold(
            seed=seed,
            neural_weight=PRIMARY_NEURAL_WEIGHT,
        )

        for arm in ARM_NAMES:
            trajectory = _load_arm(condition_id, seed, arm)
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
            metrics = _metrics_by_domain(
                y=y,
                probability=base.fused_probability,
                decision=base.thresholded_decision,
                threshold=primary_threshold,
            )
            explanation = _explanation_by_domain(y=y, evaluation=base)
            windows = _window_summaries(
                y=y,
                evaluation=base,
                threshold=primary_threshold,
            )
            recovery = _recovery_summary(windows)
            rule_versions = _rule_version_ids(trajectory, len(y))

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
                        "rule_base_version_id": rule_versions[index],
                        "neural_probability": float(neural_probability[index]),
                        "symbolic_attack_probability": symbolic_probability,
                        "symbolic_class": int(base.symbolic_class[index]),
                        "covered": bool(base.covered[index]),
                        "uncovered": bool(base.uncovered[index]),
                        "conflict_abstain": bool(base.conflict_abstain[index]),
                        "fused_probability_lambda_0_5": float(
                            base.fused_probability[index]
                        ),
                        "decision_lambda_0_5": int(
                            base.thresholded_decision[index]
                        ),
                        "fused_probability_lambda_1_0": float(
                            neural_only.fused_probability[index]
                        ),
                        "decision_lambda_1_0": int(
                            neural_only.thresholded_decision[index]
                        ),
                    }

            trace_path = output_dir / f"{arm}_prediction_trace.jsonl.gz"
            trace_identity = _write_trace_gzip_new(trace_path, trace_rows())
            arm_manifest = _verified_writer_json(
                _phase_b_dir(condition_id, seed) / arm / "arm_manifest.json"
            )
            summary = {
                "schema_version": 1,
                "condition_id": condition_id,
                "seed": seed,
                "arm": arm,
                "stage9_config_manifest_sha256": config["manifest_sha256"],
                "phase_b_arm_manifest_sha256": arm_manifest["manifest_sha256"],
                "shared_identity_sha256": trajectory.shared_identity_sha256,
                "primary_neural_weight": PRIMARY_NEURAL_WEIGHT,
                "primary_threshold": primary_threshold,
                "metrics": metrics,
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
            lambda_one["c_frozen_symbolic"],
            lambda_one["d_drift"],
        )
        verify_lambda_one_negative_control(
            lambda_one["c_frozen_symbolic"],
            lambda_one["d_periodic"],
        )

        latency = (
            5_000
            if condition_id == "G_STATIC_GATE"
            else int(config["conditions"][condition_id]["label_latency"])
        )
        seed_manifest = {
            "schema_version": 1,
            "condition_id": condition_id,
            "seed": seed,
            "status": "complete_stage9_offline_evaluation",
            "stage9_config_manifest_sha256": config["manifest_sha256"],
            "phase_b_seed_manifest_sha256": phase_b_verified[seed][
                "phase_b_manifest_sha256"
            ],
            "arm_summary_sha256": {
                arm: summary["summary_sha256"]
                for arm, summary in arm_summaries.items()
            },
            "lambda_one_predictive_equality": True,
            "trigger_diagnostics": _trigger_diagnostics(
                events,
                label_latency=latency,
            ),
            "boundary_index": PRIMARY_BOUNDARY_INDEX,
            "adaptive_components_received_boundary": False,
            "all_five_symbolic_seeds_frozen_before_scoring": True,
        }
        seed_manifest["manifest_sha256"] = canonical_sha256(seed_manifest)
        write_json_new(output_dir / "evaluation_manifest.json", seed_manifest)
        verified = verify_stage9_evaluation_seed(condition_id, seed)
    except Exception as exc:
        failure = output_dir / "failure.json"
        if not failure.exists():
            write_json_new(
                failure,
                {
                    "condition_id": condition_id,
                    "seed": seed,
                    "exception_type": type(exc).__name__,
                    "message": str(exc),
                    "phase": "offline_boundary_aware_evaluation",
                    "adaptive_components_received_boundary": False,
                },
            )
        raise
    return verified


def _offline_lambda_seed(condition_id: str, seed: int) -> dict[str, Any]:
    config = verify_stage9_config_for_execution()
    weight = {
        "O_LAMBDA_070": 0.7,
        "O_LAMBDA_090": 0.9,
        "O_LAMBDA_100": 1.0,
    }[condition_id]
    output_dir = _seed_dir(condition_id, seed)
    if output_dir.exists():
        raise FileExistsError(f"Refusing to reuse Stage-9 offline output: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=False)

    arms: dict[str, Any] = {}
    for arm in ARM_NAMES:
        source_path = (
            PRIMARY_COMPACT_PHASE_C_ROOT
            / f"seed-{seed}"
            / f"{arm}_evaluation.json"
        )
        source = _verified_writer_json(source_path)
        metrics = source["metrics_by_neural_weight"][str(weight)]
        arms[arm] = {
            "source_path": source_path.relative_to(PROJECT_ROOT).as_posix(),
            "source_summary_sha256": source["summary_sha256"],
            "source_prediction_trace": source["prediction_trace"],
            "neural_weight": weight,
            "threshold": fused_threshold(seed=seed, neural_weight=weight),
            "metrics": metrics,
            # Symbolic explanation construct is independent of fusion weight.
            "explanation": source["explanation"],
        }

    payload = {
        "schema_version": 1,
        "status": "stage9_offline_lambda_seed_complete",
        "condition_id": condition_id,
        "seed": seed,
        "stage9_config_manifest_sha256": config["manifest_sha256"],
        "adaptive_rerun": False,
        "threshold_refit": False,
        "arms": arms,
    }
    if condition_id == "O_LAMBDA_100":
        decisions = [
            float(arms[arm]["metrics"]["post"]["mcc"])
            for arm in ARM_NAMES
        ]
        if len(set(decisions)) != 1:
            raise ValueError("Lambda=1 post MCC differs across symbolic arms.")
        payload["lambda_one_post_mcc_equality"] = True
    payload["result_sha256"] = canonical_sha256(payload)
    write_json_new(output_dir / "result.json", payload)
    return verify_stage9_evaluation_seed(condition_id, seed)


def _offline_window_seed(condition_id: str, seed: int) -> dict[str, Any]:
    config = verify_stage9_config_for_execution()
    window_size = {
        "O_WINDOW_2500": 2_500,
        "O_WINDOW_10000": 10_000,
    }[condition_id]
    output_dir = _seed_dir(condition_id, seed)
    if output_dir.exists():
        raise FileExistsError(f"Refusing to reuse Stage-9 offline output: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=False)

    arms: dict[str, Any] = {}
    for arm in ARM_NAMES:
        rows = _read_verified_primary_trace(seed, arm)
        sensitivity = _window_summary_from_trace(
            rows,
            window_size=window_size,
            seed=seed,
        )
        compact = _verified_writer_json(
            PRIMARY_COMPACT_PHASE_C_ROOT
            / f"seed-{seed}"
            / f"{arm}_evaluation.json"
        )
        arms[arm] = {
            "source_summary_sha256": compact["summary_sha256"],
            "source_prediction_trace": compact["prediction_trace"],
            "whole_post_metrics": compact["metrics_by_neural_weight"]["0.5"]["post"],
            "whole_post_explanation": compact["explanation"]["post"],
            **sensitivity,
        }

    payload = {
        "schema_version": 1,
        "status": "stage9_offline_window_seed_complete",
        "condition_id": condition_id,
        "seed": seed,
        "stage9_config_manifest_sha256": config["manifest_sha256"],
        "adaptive_rerun": False,
        "whole_post_endpoint_unchanged": True,
        "arms": arms,
    }
    payload["result_sha256"] = canonical_sha256(payload)
    write_json_new(output_dir / "result.json", payload)
    return verify_stage9_evaluation_seed(condition_id, seed)


def execute_stage9_evaluation_seed(condition_id: str, seed: int) -> dict[str, Any]:
    if condition_id not in EVALUATION_CONDITIONS:
        raise ValueError(f"Unsupported Stage-9 evaluation condition: {condition_id}")
    if seed not in PRIMARY_SEEDS:
        raise ValueError(f"Unsupported Stage-9 seed: {seed}")
    if condition_id in {"O_LAMBDA_070", "O_LAMBDA_090", "O_LAMBDA_100"}:
        return _offline_lambda_seed(condition_id, seed)
    if condition_id in {"O_WINDOW_2500", "O_WINDOW_10000"}:
        return _offline_window_seed(condition_id, seed)
    return _new_trajectory_seed(condition_id, seed)


def _verify_trace(
    path: Path,
    descriptor: Mapping[str, Any],
) -> None:
    if sha256_file(path) != descriptor["sha256"]:
        raise ValueError("Stage-9 evaluation trace raw hash mismatch.")
    digest = hashlib.sha256()
    count = 0
    with gzip.open(path, "rb") as handle:
        for line in handle:
            digest.update(line)
            count += 1
    if digest.hexdigest() != descriptor["canonical_jsonl_sha256"]:
        raise ValueError("Stage-9 evaluation trace canonical hash mismatch.")
    if count != int(descriptor["row_count"]):
        raise ValueError("Stage-9 evaluation trace row count mismatch.")


def verify_stage9_evaluation_seed(
    condition_id: str,
    seed: int,
) -> dict[str, Any]:
    config = verify_stage9_config_for_execution(require_clean=False)
    output_dir = _seed_dir(condition_id, seed)
    if condition_id in OFFLINE_CONDITIONS:
        result = _verified_writer_json(output_dir / "result.json")
        stored = result.pop("result_sha256", None)
        if stored != canonical_sha256(result):
            raise ValueError("Stage-9 offline result canonical identity mismatch.")
        if result["condition_id"] != condition_id or int(result["seed"]) != seed:
            raise ValueError("Stage-9 offline condition/seed identity mismatch.")
        if result["stage9_config_manifest_sha256"] != config["manifest_sha256"]:
            raise ValueError("Stage-9 offline result references wrong config.")
        if result.get("adaptive_rerun") is not False:
            raise ValueError("Stage-9 offline condition incorrectly claims adaptive rerun.")
        return {
            "status": "stage9_offline_seed_verified",
            "condition_id": condition_id,
            "seed": seed,
            "result_sha256": stored,
        }

    # New-trajectory evaluation
    for other in PRIMARY_SEEDS:
        verify_stage9_symbolic_seed(condition_id, other, config=config)
    manifest = _verified_writer_json(output_dir / "evaluation_manifest.json")
    stored_manifest = manifest.pop("manifest_sha256", None)
    if stored_manifest != canonical_sha256(manifest):
        raise ValueError("Stage-9 evaluation manifest canonical identity mismatch.")
    if manifest["condition_id"] != condition_id or int(manifest["seed"]) != seed:
        raise ValueError("Stage-9 evaluation condition/seed identity mismatch.")
    if manifest["stage9_config_manifest_sha256"] != config["manifest_sha256"]:
        raise ValueError("Stage-9 evaluation references wrong config.")
    if manifest.get("adaptive_components_received_boundary") is not False:
        raise ValueError("Adaptive boundary-contamination flag changed.")
    if manifest.get("all_five_symbolic_seeds_frozen_before_scoring") is not True:
        raise ValueError("Stage-9 scoring occurred without all five symbolic seeds frozen.")

    summaries: dict[str, dict[str, Any]] = {}
    for arm in ARM_NAMES:
        summary = _verified_writer_json(output_dir / f"{arm}_evaluation.json")
        stored_summary = summary.pop("summary_sha256", None)
        if stored_summary != canonical_sha256(summary):
            raise ValueError("Stage-9 arm evaluation canonical identity mismatch.")
        if stored_summary != manifest["arm_summary_sha256"][arm]:
            raise ValueError("Stage-9 evaluation manifest arm binding mismatch.")
        descriptor = summary["prediction_trace"]
        _verify_trace(output_dir / descriptor["path"], descriptor)
        summaries[arm] = summary

    # lambda=1 trace decisions and scores must be exactly arm invariant row-by-row.
    lambda_rows: dict[str, list[tuple[float, int]]] = {}
    for arm in ARM_NAMES:
        pairs: list[tuple[float, int]] = []
        with gzip.open(
            output_dir / summaries[arm]["prediction_trace"]["path"],
            "rt",
            encoding="utf-8",
            newline="",
        ) as handle:
            for line in handle:
                row = json.loads(line)
                pairs.append(
                    (
                        float(row["fused_probability_lambda_1_0"]),
                        int(row["decision_lambda_1_0"]),
                    )
                )
        lambda_rows[arm] = pairs
    if not (
        lambda_rows["c_frozen_symbolic"]
        == lambda_rows["d_drift"]
        == lambda_rows["d_periodic"]
    ):
        raise ValueError("Stage-9 lambda=1 neural-only trace differs across symbolic arms.")

    return {
        "status": "stage9_evaluation_seed_verified",
        "condition_id": condition_id,
        "seed": seed,
        "evaluation_manifest_sha256": stored_manifest,
        "lambda_one_predictive_equality": True,
    }


def _numeric_summary(values: Sequence[float]) -> dict[str, Any]:
    data = [float(value) for value in values]
    if not data:
        raise ValueError("Cannot summarize empty Stage-9 values.")
    return {
        "values": data,
        "mean": float(mean(data)),
        "median": float(median(data)),
        "sample_sd": float(stdev(data)) if len(data) > 1 else 0.0,
        "minimum": float(min(data)),
        "maximum": float(max(data)),
        "positive": sum(value > 0 for value in data),
        "negative": sum(value < 0 for value in data),
        "zero": sum(value == 0 for value in data),
        "leave_one_seed_out_mean_range": (
            [
                float(min(
                    mean([value for j, value in enumerate(data) if j != i])
                    for i in range(len(data))
                )),
                float(max(
                    mean([value for j, value in enumerate(data) if j != i])
                    for i in range(len(data))
                )),
            ]
            if len(data) > 1
            else [data[0], data[0]]
        ),
    }


def _paired_effect_summary(values: Sequence[float]) -> dict[str, Any]:
    if len(values) != len(PRIMARY_SEEDS):
        raise ValueError("Stage-9 paired effect summary requires all five frozen seeds.")
    summary = _numeric_summary(values)
    sample_sd = float(summary["sample_sd"])
    sem = sample_sd / math.sqrt(float(len(PRIMARY_SEEDS)))
    margin = float(t.ppf(0.975, df=len(PRIMARY_SEEDS) - 1) * sem)
    summary["paired_t95_interval"] = [
        float(summary["mean"] - margin),
        float(summary["mean"] + margin),
    ]
    summary["interval_scope"] = (
        "paired_seed_variation_within_fixed_scenario_not_deployment_population"
    )
    summary["p_value_computed"] = False
    return summary


def _seed_arm_post(condition_id: str, seed: int, arm: str) -> tuple[float, float]:
    output_dir = _seed_dir(condition_id, seed)
    if condition_id in OFFLINE_CONDITIONS:
        result = _verified_writer_json(output_dir / "result.json")
        if condition_id.startswith("O_WINDOW"):
            mcc = float(result["arms"][arm]["whole_post_metrics"]["mcc"])
            mcsc = float(result["arms"][arm]["whole_post_explanation"]["mcsc"])
        else:
            mcc = float(result["arms"][arm]["metrics"]["post"]["mcc"])
            mcsc = float(result["arms"][arm]["explanation"]["post"]["mcsc"])
        return mcc, mcsc

    summary = _verified_writer_json(output_dir / f"{arm}_evaluation.json")
    return (
        float(summary["metrics"]["post"]["mcc"]),
        float(summary["explanation"]["post"]["mcsc"]),
    )


def build_stage9_condition_aggregate(condition_id: str) -> dict[str, Any]:
    if condition_id not in EVALUATION_CONDITIONS:
        raise ValueError(f"Unsupported Stage-9 condition: {condition_id}")
    config = verify_stage9_config_for_execution(require_clean=False)
    for seed in PRIMARY_SEEDS:
        verify_stage9_evaluation_seed(condition_id, seed)

    effects = {"E1_post_mcc_d_drift_minus_c": [], "E2_post_mcsc_d_drift_minus_c": [], "E3_post_mcsc_d_drift_minus_d_periodic": []}
    arm_post: dict[str, dict[str, list[float]]] = {
        arm: {"mcc": [], "mcsc": []} for arm in ARM_NAMES
    }
    for seed in PRIMARY_SEEDS:
        values = {}
        for arm in ARM_NAMES:
            mcc, mcsc = _seed_arm_post(condition_id, seed, arm)
            arm_post[arm]["mcc"].append(mcc)
            arm_post[arm]["mcsc"].append(mcsc)
            values[arm] = (mcc, mcsc)
        effects["E1_post_mcc_d_drift_minus_c"].append(
            values["d_drift"][0] - values["c_frozen_symbolic"][0]
        )
        effects["E2_post_mcsc_d_drift_minus_c"].append(
            values["d_drift"][1] - values["c_frozen_symbolic"][1]
        )
        effects["E3_post_mcsc_d_drift_minus_d_periodic"].append(
            values["d_drift"][1] - values["d_periodic"][1]
        )

    aggregate = {
        "schema_version": 1,
        "status": "stage9_condition_aggregate_complete",
        "condition_id": condition_id,
        "stage9_config_manifest_sha256": config["manifest_sha256"],
        "seed_count": len(PRIMARY_SEEDS),
        "inference": "robustness_descriptive_no_new_confirmatory_pvalue_family",
        "arm_post": {
            arm: {
                metric: _numeric_summary(vals)
                for metric, vals in metrics.items()
            }
            for arm, metrics in arm_post.items()
        },
        "effects": {
            endpoint: _paired_effect_summary(values)
            for endpoint, values in effects.items()
        },
    }

    if condition_id.startswith("O_WINDOW"):
        aggregate["window_sensitivity"] = {
            "whole_post_endpoints_invariant_by_design": True,
            "window_size": int(config["conditions"][condition_id]["window_rows"]),
            "min_remainder": 1_000,
            "seed_recovery": {
                str(seed): _verified_writer_json(
                    _seed_dir(condition_id, seed) / "result.json"
                )["arms"]
                for seed in PRIMARY_SEEDS
            },
        }

    aggregate["aggregate_sha256"] = canonical_sha256(aggregate)
    path = _evaluation_root(condition_id) / "aggregate.json"
    write_json_new(path, aggregate)
    return aggregate


def verify_stage9_condition_aggregate(condition_id: str) -> dict[str, Any]:
    for seed in PRIMARY_SEEDS:
        verify_stage9_evaluation_seed(condition_id, seed)
    path = _evaluation_root(condition_id) / "aggregate.json"
    aggregate = _verified_writer_json(path)
    stored = aggregate.pop("aggregate_sha256", None)
    if stored != canonical_sha256(aggregate):
        raise ValueError("Stage-9 condition aggregate canonical identity mismatch.")
    if aggregate["condition_id"] != condition_id:
        raise ValueError("Stage-9 aggregate condition identity mismatch.")
    if int(aggregate["seed_count"]) != len(PRIMARY_SEEDS):
        raise ValueError("Stage-9 aggregate does not contain all five seeds.")
    return {
        "status": "stage9_condition_aggregate_verified",
        "condition_id": condition_id,
        "aggregate_sha256": stored,
        "seed_count": len(PRIMARY_SEEDS),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Stage-9 evaluation and aggregation.")
    parser.add_argument("--condition", required=True, choices=EVALUATION_CONDITIONS)
    parser.add_argument("--seed", type=int, choices=PRIMARY_SEEDS)
    parser.add_argument("--aggregate", action="store_true")
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()

    if args.aggregate:
        if args.seed is not None:
            parser.error("--aggregate does not accept --seed")
        result = (
            verify_stage9_condition_aggregate(args.condition)
            if args.verify_only
            else build_stage9_condition_aggregate(args.condition)
        )
    else:
        if args.seed is None:
            parser.error("seed execution/verification requires --seed")
        result = (
            verify_stage9_evaluation_seed(args.condition, args.seed)
            if args.verify_only
            else execute_stage9_evaluation_seed(args.condition, args.seed)
        )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
