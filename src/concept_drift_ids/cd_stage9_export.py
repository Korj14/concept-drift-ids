from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from math import sqrt
from statistics import mean, median, stdev
from typing import Any, Mapping, Sequence

from scipy.stats import t as student_t

from concept_drift_ids.cd_control_plane import canonical_sha256, write_json_new
from concept_drift_ids.cd_primary_phase_b import ARM_NAMES
from concept_drift_ids.cd_stage9_config import (
    GATE_CONDITIONS,
    OFFLINE_CONDITIONS,
    PRIMARY_SEEDS,
    STAGE8_COMPACT_ROOT,
    STAGE9_COMPACT_ROOT,
    STAGE9_OUTPUT_ROOT,
    verify_stage9_config_for_execution,
)
from concept_drift_ids.cd_stage9_execute import PLAN_PATH, _load_verified_plan
from concept_drift_ids.cd_stage9_offline import (
    _output_dir as offline_output_dir,
    _stage8_eval_payload,
    verify_offline_condition,
)
from concept_drift_ids.cd_stage9_phase_a import adaptive_condition_ids
from concept_drift_ids.cd_stage9_phase_b import _phase_a_dir, _phase_b_dir
from concept_drift_ids.cd_stage9_phase_c import (
    _phase_c_dir,
    verify_stage9_phase_c_seed,
)
from concept_drift_ids.scenario_manifest import sha256_file


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_verified_json(
    path: Path,
    *,
    inner_hash_key: str | None = None,
) -> dict[str, Any]:
    payload = _read_json(path)
    stored_payload = payload.pop("payload_sha256", None)
    if stored_payload is not None and stored_payload != canonical_sha256(payload):
        raise ValueError(f"Writer payload hash mismatch: {path}")
    if inner_hash_key is not None:
        stored_inner = payload.get(inner_hash_key)
        core = dict(payload)
        core.pop(inner_hash_key, None)
        if stored_inner != canonical_sha256(core):
            raise ValueError(
                f"Canonical {inner_hash_key} mismatch: {path}"
            )
    return payload


def _numeric_summary(values: Sequence[float]) -> dict[str, Any]:
    vals = [float(v) for v in values]
    avg = mean(vals)
    sd = stdev(vals) if len(vals) > 1 else 0.0
    loo = [
        mean(vals[:index] + vals[index + 1 :])
        for index in range(len(vals))
        if len(vals) > 1
    ]
    if len(vals) > 1:
        critical = float(student_t.ppf(0.975, df=len(vals) - 1))
        half_width = critical * sd / sqrt(len(vals))
        interval = [avg - half_width, avg + half_width]
    else:
        interval = [avg, avg]
    return {
        "values": vals,
        "mean": avg,
        "median": median(vals),
        "sample_sd": sd,
        "minimum": min(vals),
        "maximum": max(vals),
        "positive": sum(v > 0 for v in vals),
        "negative": sum(v < 0 for v in vals),
        "zero": sum(v == 0 for v in vals),
        "leave_one_seed_out_mean_range": (
            [min(loo), max(loo)] if loo else [avg, avg]
        ),
        "t95_interval_descriptive": interval,
        "t95_interval_scope": (
            "stochastic_seed_dispersion_conditional_on_fixed_scenario;"
            "not_environmental_or_deployment_population_inference"
        ),
    }


def _optional_numeric_summary(values: Sequence[float]) -> dict[str, Any] | None:
    vals = [float(v) for v in values if float(v) == float(v)]
    return _numeric_summary(vals) if vals else None


def _offline_result(condition: str, seed: int) -> dict[str, Any]:
    return _read_verified_json(
        offline_output_dir(condition, seed) / "result.json",
        inner_hash_key="result_sha256",
    )


def _offline_lambda_metrics(
    condition: str,
    seed: int,
    arm: str,
) -> dict[str, float]:
    result = _offline_result(condition, seed)["results"][arm]
    post = result["metrics"]["post"]
    explanation = _stage8_eval_payload(seed, arm)["explanation"]["post"]
    return {
        "mcc": float(post["mcc"]),
        "f1": float(post["f1"]),
        "fpr": float(post["fpr"]),
        "mcsc": float(explanation["mcsc"]),
        "resolved_coverage": float(explanation["resolved_coverage"]),
    }


def _recovery_metric_summary(
    condition: str,
    arm: str,
    metric: str,
) -> dict[str, Any]:
    per_seed: list[dict[str, Any]] = []
    observed_rows: list[float] = []
    primary_observed_rows: list[float] = []
    paired_observed_deltas: list[float] = []

    for seed in PRIMARY_SEEDS:
        alternative = _offline_result(condition, seed)["results"][arm]["recovery"][metric]
        primary = _stage8_eval_payload(seed, arm)["primary_recovery"][metric]
        record = {
            "seed": seed,
            "alternative": alternative,
            "primary_window_5000": primary,
        }
        per_seed.append(record)

        alt_rows = (
            alternative.get("recovery_rows_from_boundary")
            if alternative.get("available") is True
            and alternative.get("right_censored") is False
            else None
        )
        primary_rows = (
            primary.get("recovery_rows_from_boundary")
            if primary.get("available") is True
            and primary.get("right_censored") is False
            else None
        )
        if alt_rows is not None:
            observed_rows.append(float(alt_rows))
        if primary_rows is not None:
            primary_observed_rows.append(float(primary_rows))
        if alt_rows is not None and primary_rows is not None:
            paired_observed_deltas.append(float(alt_rows) - float(primary_rows))

    def _count(key: str, expected: Any) -> int:
        return sum(
            row["alternative"].get(key) is expected
            for row in per_seed
        )

    return {
        "per_seed": per_seed,
        "available_count": _count("available", True),
        "recovered_count": _count("recovered", True),
        "right_censored_count": _count("right_censored", True),
        "observed_recovery_rows_summary": _optional_numeric_summary(observed_rows),
        "primary_5000_observed_recovery_rows_summary": _optional_numeric_summary(
            primary_observed_rows
        ),
        "paired_observed_recovery_row_delta_vs_5000": _optional_numeric_summary(
            paired_observed_deltas
        ),
        "paired_delta_scope": (
            "descriptive_only_for_seeds_with_observed_recovery_under_both_windows"
        ),
    }


def _offline_condition_aggregate(condition: str) -> dict[str, Any]:
    if condition.startswith("lambda_"):
        by_arm = {
            arm: [
                _offline_lambda_metrics(condition, seed, arm)
                for seed in PRIMARY_SEEDS
            ]
            for arm in ARM_NAMES
        }
        reference = {
            arm: [_stage8_reference(seed, arm) for seed in PRIMARY_SEEDS]
            for arm in ARM_NAMES
        }
        payload: dict[str, Any] = {
            "type": "fusion_authority_sensitivity",
            "reference": "stage8_primary_lambda_0_5",
            "adaptive_state_rerun": False,
            "threshold_refit": False,
            "arms": {},
            "within_condition_primary_contrasts": {
                "d_drift_minus_c": _paired_effects(
                    by_arm["d_drift"], by_arm["c_frozen_symbolic"]
                ),
                "d_periodic_minus_c": _paired_effects(
                    by_arm["d_periodic"], by_arm["c_frozen_symbolic"]
                ),
                "d_drift_minus_d_periodic": _paired_effects(
                    by_arm["d_drift"], by_arm["d_periodic"]
                ),
            },
        }
        for arm in ARM_NAMES:
            payload["arms"][arm] = {
                metric: _numeric_summary([row[metric] for row in by_arm[arm]])
                for metric in ("mcc", "f1", "fpr", "mcsc", "resolved_coverage")
            }
            payload["arms"][arm]["paired_effect_vs_primary_lambda_0_5"] = (
                _paired_effects(by_arm[arm], reference[arm])
            )
        return payload

    window_size = 2500 if condition == "window_2500" else 10000
    return {
        "type": "reporting_window_sensitivity",
        "reference": "stage8_primary_window_5000",
        "reporting_window_rows": window_size,
        "adaptive_state_rerun": False,
        "threshold_refit": False,
        "whole_post_endpoints_changed": False,
        "whole_post_endpoint_note": (
            "Window size changes recovery reporting only; whole-post Stage-8 "
            "endpoints and decisions remain immutable."
        ),
        "recovery": {
            arm: {
                metric: _recovery_metric_summary(condition, arm, metric)
                for metric in ("mcc", "mcsc", "fpr")
            }
            for arm in ARM_NAMES
        },
    }


def _stage8_reference(seed: int, arm: str) -> dict[str, float]:
    payload = _stage8_eval_payload(seed, arm)
    post = payload["metrics_by_neural_weight"]["0.5"]["post"]
    explanation = payload["explanation"]["post"]
    return {
        "mcc": float(post["mcc"]),
        "f1": float(post["f1"]),
        "fpr": float(post["fpr"]),
        "mcsc": float(explanation["mcsc"]),
        "resolved_coverage": float(explanation["resolved_coverage"]),
    }


def _stage9_metrics(condition: str, seed: int, arm: str) -> dict[str, float]:
    payload = _read_verified_json(
        _phase_c_dir(condition, seed) / f"{arm}_evaluation.json",
        inner_hash_key="summary_sha256",
    )
    post = payload["metrics_by_neural_weight"]["0.5"]["post"]
    explanation = payload["explanation"]["post"]
    return {
        "mcc": float(post["mcc"]),
        "f1": float(post["f1"]),
        "fpr": float(post["fpr"]),
        "mcsc": float(explanation["mcsc"]),
        "resolved_coverage": float(explanation["resolved_coverage"]),
    }



def _stage9_seed_manifest(condition: str, seed: int) -> dict[str, Any]:
    return _read_verified_json(
        _phase_c_dir(condition, seed) / "phase_c_seed_manifest.json",
        inner_hash_key="manifest_sha256",
    )


def _maintenance_metrics(condition: str, seed: int, arm: str) -> dict[str, float]:
    payload = _read_verified_json(
        _phase_c_dir(condition, seed) / f"{arm}_evaluation.json",
        inner_hash_key="summary_sha256",
    )
    summary = payload["maintenance_summary"]
    return {
        "opportunity_count": float(summary["opportunity_count"]),
        "publication_count": float(summary["publication_count"]),
        "completed_validation_count": float(summary["completed_validation_count"]),
        "censored_or_blocked_count": float(summary["censored_or_blocked_count"]),
        "compute_seconds": float(summary["compute_seconds"]),
        "mean_validation_wait_rows": (
            float(summary["mean_validation_wait_rows"])
            if summary["mean_validation_wait_rows"] is not None
            else float("nan")
        ),
    }


def _trigger_summary(condition: str) -> dict[str, Any]:
    rows = [
        _stage9_seed_manifest(condition, seed)["trigger_diagnostics"]
        for seed in PRIMARY_SEEDS
    ]
    first_post = [
        row["first_post_reference_confirmation_delay_rows"] for row in rows
    ]
    excess = [row["latency_adjusted_excess_delay_rows"] for row in rows]
    return {
        "per_seed": rows,
        "pre_reference_alarm_count": _numeric_summary(
            [float(row["pre_reference_alarm_count"]) for row in rows]
        ),
        "detector_event_count": _numeric_summary(
            [float(row["detector_event_count"]) for row in rows]
        ),
        "post_reference_event_count": _numeric_summary(
            [float(row["post_reference_event_count"]) for row in rows]
        ),
        "first_post_reference_confirmation_delay_rows": {
            "values": first_post,
            "observed_count": sum(value is not None for value in first_post),
            "censored_count": sum(value is None for value in first_post),
            "observed_summary": (
                _numeric_summary([float(v) for v in first_post if v is not None])
                if any(v is not None for v in first_post)
                else None
            ),
        },
        "latency_adjusted_excess_delay_rows": {
            "values": excess,
            "observed_count": sum(value is not None for value in excess),
            "censored_count": sum(value is None for value in excess),
            "observed_summary": (
                _numeric_summary([float(v) for v in excess if v is not None])
                if any(v is not None for v in excess)
                else None
            ),
        },
    }


def _paired_effects(
    target: Sequence[Mapping[str, float]],
    reference: Sequence[Mapping[str, float]],
) -> dict[str, Any]:
    if len(target) != len(reference):
        raise ValueError("Paired robustness arrays differ in length.")
    metrics = ("mcc", "f1", "fpr", "mcsc", "resolved_coverage")
    return {
        metric: _numeric_summary(
            [float(t[metric]) - float(r[metric]) for t, r in zip(target, reference)]
        )
        for metric in metrics
    }


def _copy_json_new(source: Path, destination: Path) -> dict[str, str]:
    if destination.exists():
        raise FileExistsError(f"Refusing to overwrite compact evidence: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    data = source.read_bytes()
    destination.write_bytes(data)
    return {
        "path": destination.relative_to(STAGE9_COMPACT_ROOT).as_posix(),
        "sha256": sha256_file(destination),
    }



def _verify_json_file_hashes(path: Path) -> dict[str, Any]:
    payload = _read_json(path)
    stored_payload = payload.pop("payload_sha256", None)
    if stored_payload is not None and stored_payload != canonical_sha256(payload):
        raise ValueError(f"Stage-9 compact writer payload hash mismatch: {path}")
    return payload


def _verify_file_descriptors(node: Any) -> None:
    if isinstance(node, dict):
        if set(("path", "sha256")).issubset(node):
            path = STAGE9_COMPACT_ROOT / str(node["path"])
            if not path.is_file():
                raise FileNotFoundError(f"Missing Stage-9 compact file: {path}")
            if sha256_file(path) != str(node["sha256"]):
                raise ValueError(f"Stage-9 compact raw file hash mismatch: {path}")
            return
        for value in node.values():
            _verify_file_descriptors(value)


def verify_stage9_compact_export() -> dict[str, Any]:
    config = verify_stage9_config_for_execution(
        allow_untracked_compact_output=True
    )
    manifest_path = STAGE9_COMPACT_ROOT / "compact_export_manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError("Stage-9 compact export manifest is absent.")
    manifest = _verify_json_file_hashes(manifest_path)
    stored_manifest = manifest.pop("manifest_sha256", None)
    if stored_manifest != canonical_sha256(manifest):
        raise ValueError("Stage-9 compact export manifest canonical hash mismatch.")
    if manifest["stage9_config_manifest_sha256"] != config["manifest_sha256"]:
        raise ValueError("Stage-9 compact export references wrong frozen config.")
    if manifest["stage8_parent"] != config["stage8_parent"]:
        raise ValueError("Stage-9 compact export Stage-8 parent changed.")
    plan = _load_verified_plan(config)
    if manifest["execution_plan_sha256"] != plan["plan_sha256"]:
        raise ValueError("Stage-9 compact export execution-plan identity changed.")

    expected_scored = list(adaptive_condition_ids(config) + tuple(GATE_CONDITIONS))
    if manifest["conditions"]["offline"] != list(OFFLINE_CONDITIONS):
        raise ValueError("Stage-9 compact offline condition set changed.")
    if manifest["conditions"]["scored"] != expected_scored:
        raise ValueError("Stage-9 compact scored condition set changed.")

    _verify_file_descriptors(manifest["files"])

    aggregate_path = STAGE9_COMPACT_ROOT / "aggregate.json"
    aggregate = _verify_json_file_hashes(aggregate_path)
    stored_aggregate = aggregate.pop("aggregate_sha256", None)
    if stored_aggregate != canonical_sha256(aggregate):
        raise ValueError("Stage-9 aggregate canonical hash mismatch.")
    if aggregate["stage9_config_manifest_sha256"] != config["manifest_sha256"]:
        raise ValueError("Stage-9 aggregate references wrong frozen config.")
    if aggregate["stage8_parent"] != config["stage8_parent"]:
        raise ValueError("Stage-9 aggregate Stage-8 parent changed.")
    if aggregate["execution_plan_sha256"] != plan["plan_sha256"]:
        raise ValueError("Stage-9 aggregate execution-plan identity changed.")

    expected_conditions = set(OFFLINE_CONDITIONS) | set(expected_scored)
    if set(aggregate["conditions"]) != expected_conditions:
        raise ValueError("Stage-9 aggregate condition coverage is incomplete.")

    return {
        "status": "stage9_compact_export_verified",
        "manifest_sha256": stored_manifest,
        "aggregate_sha256": stored_aggregate,
        "condition_count": len(expected_conditions),
        "seed_count_per_condition": len(PRIMARY_SEEDS),
    }

def export_stage9() -> dict[str, Any]:
    config = verify_stage9_config_for_execution()
    if STAGE9_COMPACT_ROOT.exists():
        raise FileExistsError(
            f"Refusing to reuse Stage-9 compact evidence root: {STAGE9_COMPACT_ROOT}"
        )

    plan = _load_verified_plan(config)
    adaptive = adaptive_condition_ids(config)
    scored_conditions = adaptive + tuple(GATE_CONDITIONS)

    # Full verification occurs before the first compact write.
    for condition in OFFLINE_CONDITIONS:
        for seed in PRIMARY_SEEDS:
            verify_offline_condition(condition, seed)
    for condition in scored_conditions:
        for seed in PRIMARY_SEEDS:
            verify_stage9_phase_c_seed(condition, seed, config=config)

    STAGE9_COMPACT_ROOT.mkdir(parents=True, exist_ok=False)
    files: dict[str, Any] = {}
    files["execution_plan"] = _copy_json_new(
        PLAN_PATH,
        STAGE9_COMPACT_ROOT / "execution_plan.json",
    )

    for condition in OFFLINE_CONDITIONS:
        condition_files: dict[str, Any] = {}
        for seed in PRIMARY_SEEDS:
            source = offline_output_dir(condition, seed) / "result.json"
            dest = (
                STAGE9_COMPACT_ROOT
                / "offline"
                / condition
                / f"seed-{seed}.json"
            )
            condition_files[str(seed)] = _copy_json_new(source, dest)
        files[f"offline:{condition}"] = condition_files

    for condition in scored_conditions:
        condition_files: dict[str, Any] = {}
        for seed in PRIMARY_SEEDS:
            seed_dir = _phase_c_dir(condition, seed)
            copied: dict[str, Any] = {}
            for name in (
                "phase_c_seed_manifest.json",
                "c_frozen_symbolic_evaluation.json",
                "d_drift_evaluation.json",
                "d_periodic_evaluation.json",
            ):
                source = seed_dir / name
                dest = (
                    STAGE9_COMPACT_ROOT
                    / "scored"
                    / condition
                    / f"seed-{seed}"
                    / name
                )
                copied[name] = _copy_json_new(source, dest)

            phase_a_root = _phase_a_dir(condition, seed)
            phase_b_root = _phase_b_dir(condition, seed)
            provenance: dict[str, Any] = {
                "phase_a": {},
                "phase_b": {},
            }
            for name in (
                "run_manifest.json",
                "input_identity.json",
                "shared_identity.json",
            ):
                source = phase_a_root / name
                dest = (
                    STAGE9_COMPACT_ROOT
                    / "provenance"
                    / condition
                    / f"seed-{seed}"
                    / "phase_a"
                    / name
                )
                provenance["phase_a"][name] = _copy_json_new(source, dest)

            source = phase_b_root / "phase_b_manifest.json"
            dest = (
                STAGE9_COMPACT_ROOT
                / "provenance"
                / condition
                / f"seed-{seed}"
                / "phase_b"
                / "phase_b_manifest.json"
            )
            provenance["phase_b"]["phase_b_manifest.json"] = _copy_json_new(
                source, dest
            )
            for arm in ARM_NAMES:
                source = phase_b_root / arm / "arm_manifest.json"
                dest = (
                    STAGE9_COMPACT_ROOT
                    / "provenance"
                    / condition
                    / f"seed-{seed}"
                    / "phase_b"
                    / arm
                    / "arm_manifest.json"
                )
                provenance["phase_b"][f"{arm}/arm_manifest.json"] = (
                    _copy_json_new(source, dest)
                )

            condition_files[str(seed)] = {
                "phase_c": copied,
                "provenance": provenance,
            }
        files[f"scored:{condition}"] = condition_files

    if bool(config["matched_baseline_required"]):
        baseline_condition = "matched_primary_baseline"
    else:
        baseline_condition = None

    aggregate: dict[str, Any] = {
        "schema_version": 1,
        "status": "stage9_robustness_aggregate_complete",
        "stage9_config_manifest_sha256": config["manifest_sha256"],
        "stage8_parent": config["stage8_parent"],
        "execution_plan_sha256": plan["plan_sha256"],
        "reference_policy": {
            "offline_conditions": "frozen_stage8_primary",
            "static_symbolic_gate": "frozen_stage8_primary",
            "matched_primary_baseline": "frozen_stage8_primary",
            "adaptive_variants": (
                "matched_stage9_baseline"
                if baseline_condition is not None
                else "frozen_stage8_primary"
            ),
        },
        "conditions": {},
        "inference": {
            "classification": "prespecified_robustness_no_new_confirmatory_family",
            "p_values_computed": False,
            "all_frozen_conditions_reported": True,
            "condition_selection_by_outcome_forbidden": True,
            "seed_is_inferential_unit_within_fixed_scenario": True,
            "environmental_replication_claim_forbidden": True,
        },
    }

    for condition in OFFLINE_CONDITIONS:
        aggregate["conditions"][condition] = _offline_condition_aggregate(condition)

    for condition in scored_conditions:
        by_arm = {
            arm: [_stage9_metrics(condition, seed, arm) for seed in PRIMARY_SEEDS]
            for arm in ARM_NAMES
        }
        use_matched_baseline = (
            baseline_condition is not None
            and condition != baseline_condition
            and condition not in GATE_CONDITIONS
        )
        if use_matched_baseline:
            reference = {
                arm: [
                    _stage9_metrics(baseline_condition, seed, arm)
                    for seed in PRIMARY_SEEDS
                ]
                for arm in ARM_NAMES
            }
            reference_id = baseline_condition
        else:
            reference = {
                arm: [_stage8_reference(seed, arm) for seed in PRIMARY_SEEDS]
                for arm in ARM_NAMES
            }
            reference_id = "stage8_primary"

        condition_payload: dict[str, Any] = {
            "arms": {},
            "within_condition_primary_contrasts": {},
            "reference": reference_id,
        }
        for arm in ARM_NAMES:
            condition_payload["arms"][arm] = {
                metric: _numeric_summary([row[metric] for row in by_arm[arm]])
                for metric in ("mcc", "f1", "fpr", "mcsc", "resolved_coverage")
            }
            condition_payload["arms"][arm]["paired_effect_vs_reference"] = _paired_effects(
                by_arm[arm], reference[arm]
            )

        condition_payload["within_condition_primary_contrasts"] = {
            "d_drift_minus_c": _paired_effects(
                by_arm["d_drift"], by_arm["c_frozen_symbolic"]
            ),
            "d_periodic_minus_c": _paired_effects(
                by_arm["d_periodic"], by_arm["c_frozen_symbolic"]
            ),
            "d_drift_minus_d_periodic": _paired_effects(
                by_arm["d_drift"], by_arm["d_periodic"]
            ),
        }
        condition_payload["trigger_diagnostics"] = _trigger_summary(condition)
        condition_payload["maintenance"] = {
            arm: {
                metric: _optional_numeric_summary(
                    [
                        row[metric]
                        for row in [
                            _maintenance_metrics(condition, seed, arm)
                            for seed in PRIMARY_SEEDS
                        ]
                    ]
                )
                for metric in (
                    "opportunity_count",
                    "publication_count",
                    "completed_validation_count",
                    "censored_or_blocked_count",
                    "compute_seconds",
                    "mean_validation_wait_rows",
                )
            }
            for arm in ("d_drift", "d_periodic")
        }
        aggregate["conditions"][condition] = condition_payload

    aggregate["aggregate_sha256"] = canonical_sha256(aggregate)
    aggregate_descriptor = _copy_json_payload_new(
        STAGE9_COMPACT_ROOT / "aggregate.json", aggregate
    )
    files["aggregate"] = aggregate_descriptor

    manifest = {
        "schema_version": 1,
        "status": "stage9_compact_export_complete",
        "stage9_config_manifest_sha256": config["manifest_sha256"],
        "stage8_parent": config["stage8_parent"],
        "execution_plan_sha256": plan["plan_sha256"],
        "conditions": {
            "offline": list(OFFLINE_CONDITIONS),
            "scored": list(scored_conditions),
        },
        "files": files,
    }
    manifest["manifest_sha256"] = canonical_sha256(manifest)
    write_json_new(STAGE9_COMPACT_ROOT / "compact_export_manifest.json", manifest)
    verified = verify_stage9_compact_export()
    return {
        "status": manifest["status"],
        "manifest_sha256": verified["manifest_sha256"],
        "aggregate_sha256": verified["aggregate_sha256"],
        "verified": True,
    }


def _copy_json_payload_new(path: Path, payload: Mapping[str, Any]) -> dict[str, str]:
    file_sha = write_json_new(path, payload)
    return {
        "path": path.relative_to(STAGE9_COMPACT_ROOT).as_posix(),
        "sha256": file_sha,
        "canonical_sha256": str(
            payload.get("aggregate_sha256", payload.get("manifest_sha256", ""))
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    result = (
        verify_stage9_compact_export()
        if args.verify_only
        else export_stage9()
    )
    print(json.dumps(result, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
