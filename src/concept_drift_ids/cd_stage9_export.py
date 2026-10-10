from __future__ import annotations

import json
import shutil
from pathlib import Path
from statistics import mean, median, stdev
from typing import Any, Mapping, Sequence

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
from concept_drift_ids.cd_stage9_offline import (
    _output_dir as offline_output_dir,
    verify_offline_condition,
)
from concept_drift_ids.cd_stage9_phase_a import adaptive_condition_ids
from concept_drift_ids.cd_stage9_phase_c import (
    _phase_c_dir,
    verify_stage9_phase_c_seed,
)
from concept_drift_ids.scenario_manifest import sha256_file


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _numeric_summary(values: Sequence[float]) -> dict[str, Any]:
    vals = [float(v) for v in values]
    return {
        "values": vals,
        "mean": mean(vals),
        "median": median(vals),
        "sample_sd": stdev(vals) if len(vals) > 1 else 0.0,
        "minimum": min(vals),
        "maximum": max(vals),
        "positive": sum(v > 0 for v in vals),
        "negative": sum(v < 0 for v in vals),
        "zero": sum(v == 0 for v in vals),
    }


def _stage8_reference(seed: int, arm: str) -> dict[str, float]:
    path = (
        STAGE8_COMPACT_ROOT
        / "phase_c_offline_evaluation_v1_1"
        / f"seed-{seed}"
        / f"{arm}_evaluation.json"
    )
    payload = _read_json(path)
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
    payload = _read_json(_phase_c_dir(condition, seed) / f"{arm}_evaluation.json")
    post = payload["metrics_by_neural_weight"]["0.5"]["post"]
    explanation = payload["explanation"]["post"]
    return {
        "mcc": float(post["mcc"]),
        "f1": float(post["f1"]),
        "fpr": float(post["fpr"]),
        "mcsc": float(explanation["mcsc"]),
        "resolved_coverage": float(explanation["resolved_coverage"]),
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


def export_stage9() -> dict[str, Any]:
    config = verify_stage9_config_for_execution()
    if STAGE9_COMPACT_ROOT.exists():
        raise FileExistsError(
            f"Refusing to reuse Stage-9 compact evidence root: {STAGE9_COMPACT_ROOT}"
        )

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
            condition_files[str(seed)] = copied
        files[f"scored:{condition}"] = condition_files

    if bool(config["matched_baseline_required"]):
        baseline_condition = "matched_primary_baseline"
        reference_kind = "matched_stage9_baseline"
    else:
        baseline_condition = None
        reference_kind = "frozen_stage8_primary"

    aggregate: dict[str, Any] = {
        "schema_version": 1,
        "status": "stage9_robustness_aggregate_complete",
        "stage9_config_manifest_sha256": config["manifest_sha256"],
        "stage8_parent": config["stage8_parent"],
        "reference_kind": reference_kind,
        "conditions": {},
        "inference": "prespecified_robustness_no_new_confirmatory_family",
    }

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
        "conditions": {
            "offline": list(OFFLINE_CONDITIONS),
            "scored": list(scored_conditions),
        },
        "files": files,
    }
    manifest["manifest_sha256"] = canonical_sha256(manifest)
    write_json_new(STAGE9_COMPACT_ROOT / "compact_export_manifest.json", manifest)
    return {
        "status": manifest["status"],
        "manifest_sha256": manifest["manifest_sha256"],
        "aggregate_sha256": aggregate["aggregate_sha256"],
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
    print(json.dumps(export_stage9(), sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
