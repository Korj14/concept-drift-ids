from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any, Mapping

from concept_drift_ids.cd_control_plane import canonical_sha256, write_json_new
from concept_drift_ids.cd_stage9_config import (
    PRIMARY_SEEDS,
    PROJECT_ROOT,
    STAGE9_COMPACT_ROOT,
    STAGE9_CONFIG_PATH,
    STAGE9_OUTPUT_ROOT,
    verify_stage9_config_for_execution,
)
from concept_drift_ids.cd_stage9_evaluation import (
    OFFLINE_CONDITIONS,
    _paired_effect_summary,
    verify_stage9_condition_aggregate,
    verify_stage9_evaluation_seed,
)
from concept_drift_ids.cd_stage9_phase_a import ADAPTIVE_CONDITIONS, verify_stage9_phase_a_seed
from concept_drift_ids.cd_stage9_symbolic import (
    ARM_NAMES,
    verify_stage9_symbolic_seed,
)
from concept_drift_ids.scenario_manifest import sha256_file


BASE_REQUIRED_CONDITIONS = (
    *OFFLINE_CONDITIONS,
    "G_STATIC_GATE",
    "A_LATENCY_0",
    "A_LATENCY_10000",
    "A_PAGE_HINKLEY",
    "A_ADWIN_BRIER",
    "A_NO_REPLAY",
)


def required_conditions(config: Mapping[str, Any]) -> tuple[str, ...]:
    out = list(BASE_REQUIRED_CONDITIONS)
    if bool(config["conditions"]["A_BASELINE"]["required"]):
        out.append("A_BASELINE")
    return tuple(out)


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


def _phase_a_root(condition_id: str) -> Path:
    return (
        STAGE9_OUTPUT_ROOT
        / "adaptive"
        / condition_id
        / "phase_a_shared_control_plane"
    )


def _phase_b_root(condition_id: str) -> Path:
    if condition_id == "G_STATIC_GATE":
        return (
            STAGE9_OUTPUT_ROOT
            / "symbolic_gate"
            / condition_id
            / "phase_b_symbolic_arms"
        )
    return (
        STAGE9_OUTPUT_ROOT
        / "adaptive"
        / condition_id
        / "phase_b_symbolic_arms"
    )


def _copy_new(src: Path, dst: Path) -> str:
    if not src.is_file():
        raise FileNotFoundError(f"Missing Stage-9 compact-export input: {src}")
    if dst.exists():
        raise FileExistsError(f"Refusing to overwrite compact Stage-9 evidence: {dst}")
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dst)
    if sha256_file(dst) != sha256_file(src):
        raise ValueError("Stage-9 compact copy raw hash mismatch.")
    return sha256_file(dst)


def _copy_rel(
    src: Path,
    *,
    source_root: Path,
    destination_root: Path,
    files: dict[str, dict[str, str]],
) -> None:
    relative = src.relative_to(source_root)
    dst = destination_root / relative
    digest = _copy_new(src, dst)
    key = relative.as_posix()
    files[key] = {"path": key, "sha256": digest}


def _compact_files_for_condition(condition_id: str) -> list[Path]:
    files: list[Path] = []
    eval_root = _evaluation_root(condition_id)
    files.append(eval_root / "aggregate.json")
    for seed in PRIMARY_SEEDS:
        seed_eval = eval_root / f"seed-{seed}"
        if condition_id in OFFLINE_CONDITIONS:
            files.append(seed_eval / "result.json")
            continue

        files.append(seed_eval / "evaluation_manifest.json")
        for arm in ARM_NAMES:
            files.append(seed_eval / f"{arm}_evaluation.json")

        phase_b = _phase_b_root(condition_id) / f"seed-{seed}"
        files.append(phase_b / "phase_b_manifest.json")
        for arm in ARM_NAMES:
            arm_dir = phase_b / arm
            files.append(arm_dir / "arm_manifest.json")
            files.append(arm_dir / "maintenance.jsonl")
            files.append(arm_dir / "initial_state.json")
            files.append(arm_dir / "final_state.json")
            versions = arm_dir / "versions"
            if versions.exists():
                files.extend(sorted(versions.glob("*.json")))

        if condition_id in ADAPTIVE_CONDITIONS:
            phase_a = _phase_a_root(condition_id) / f"seed-{seed}"
            files.append(phase_a / "run_manifest.json")
            files.append(phase_a / "shared_identity.json")
            files.append(phase_a / "input_identity.json")
            files.append(phase_a / "checkpoint_chain.jsonl")
    return files


def _load_writer_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    stored = payload.pop("payload_sha256", None)
    if stored is not None and stored != canonical_sha256(payload):
        raise ValueError(f"JSON writer payload hash mismatch: {path}")
    return payload


def _master_summary(
    config: Mapping[str, Any],
    conditions: tuple[str, ...],
) -> dict[str, Any]:
    full_aggregates: dict[str, dict[str, Any]] = {}
    aggregates: dict[str, Any] = {}
    for condition_id in conditions:
        aggregate = _load_writer_json(_evaluation_root(condition_id) / "aggregate.json")
        full_aggregates[condition_id] = aggregate
        aggregates[condition_id] = {
            "aggregate_sha256": aggregate["aggregate_sha256"],
            "effects": aggregate["effects"],
            "qualitative_stage8_relation": aggregate[
                "qualitative_stage8_relation"
            ],
            "inference": aggregate["inference"],
        }

    baseline_required = bool(
        config["runtime"]["comparison"]["matched_stage9_baseline_required"]
    )
    matched_baseline: dict[str, Any] = {
        "required": baseline_required,
        "comparison_scope": (
            "adaptive_variant_minus_matched_stage9_baseline_on_seed_level_effects"
            if baseline_required
            else "not_required_same_material_runtime"
        ),
        "stage8_primary_replaced": False,
        "variants": {},
    }
    if baseline_required:
        if "A_BASELINE" not in full_aggregates:
            raise ValueError(
                "Cross-runtime Stage 9 requires an aggregated A_BASELINE."
            )
        baseline = full_aggregates["A_BASELINE"]
        for condition_id in (
            "A_LATENCY_0",
            "A_LATENCY_10000",
            "A_PAGE_HINKLEY",
            "A_ADWIN_BRIER",
            "A_NO_REPLAY",
        ):
            if condition_id not in full_aggregates:
                raise ValueError(
                    f"Missing adaptive variant required for baseline comparison: {condition_id}"
                )
            variant = full_aggregates[condition_id]
            endpoint_deltas: dict[str, Any] = {}
            for endpoint in baseline["effects"]:
                baseline_values = [
                    float(value)
                    for value in baseline["effects"][endpoint]["values"]
                ]
                variant_values = [
                    float(value)
                    for value in variant["effects"][endpoint]["values"]
                ]
                if len(baseline_values) != len(variant_values):
                    raise ValueError("Matched Stage-9 baseline seed count mismatch.")
                deltas = [
                    value - reference
                    for value, reference in zip(
                        variant_values,
                        baseline_values,
                    )
                ]
                endpoint_deltas[endpoint] = _paired_effect_summary(deltas)
            matched_baseline["variants"][condition_id] = {
                "endpoint_effect_delta_vs_A_BASELINE": endpoint_deltas,
                "interpretation": (
                    "paired robustness delta within the Stage-9 runtime; "
                    "does not replace the frozen Stage-8 primary"
                ),
            }

    return {
        "schema_version": 1,
        "status": "stage9_robustness_master_summary_complete",
        "stage9_config_manifest_sha256": config["manifest_sha256"],
        "parent_stage8": config["parent_stage8"],
        "runtime_comparison": config["runtime"]["comparison"],
        "required_conditions": list(conditions),
        "conditions": aggregates,
        "matched_stage9_baseline_comparison": matched_baseline,
        "interpretation_rule": (
            "condition_by_condition_robustness; no pooling as independent replicates; "
            "when runtime differs, adaptive variants are interpreted primarily against "
            "A_BASELINE; Stage-8 primary remains authoritative"
        ),
    }


def export_stage9_compact_evidence() -> dict[str, Any]:
    config = verify_stage9_config_for_execution(require_clean=False)
    conditions = required_conditions(config)

    # Verify every required seed/condition and aggregate before copying anything.
    for condition_id in conditions:
        for seed in PRIMARY_SEEDS:
            verify_stage9_evaluation_seed(condition_id, seed)
            if condition_id in ADAPTIVE_CONDITIONS:
                verify_stage9_phase_a_seed(condition_id, seed, config=config)
            if condition_id not in OFFLINE_CONDITIONS:
                verify_stage9_symbolic_seed(condition_id, seed, config=config)
        verify_stage9_condition_aggregate(condition_id)

    if STAGE9_COMPACT_ROOT.exists():
        raise FileExistsError(
            f"Refusing to reuse Stage-9 compact evidence root: {STAGE9_COMPACT_ROOT}"
        )
    STAGE9_COMPACT_ROOT.mkdir(parents=True, exist_ok=False)

    files: dict[str, dict[str, str]] = {}
    config_dst = STAGE9_COMPACT_ROOT / "stage9_run_config_v1.json"
    files["stage9_run_config_v1.json"] = {
        "path": "stage9_run_config_v1.json",
        "sha256": _copy_new(STAGE9_CONFIG_PATH, config_dst),
    }

    source_root = STAGE9_OUTPUT_ROOT
    for condition_id in conditions:
        for src in _compact_files_for_condition(condition_id):
            _copy_rel(
                src,
                source_root=source_root,
                destination_root=STAGE9_COMPACT_ROOT,
                files=files,
            )

    summary = _master_summary(config, conditions)
    summary["summary_sha256"] = canonical_sha256(summary)
    summary_path = STAGE9_COMPACT_ROOT / "stage9_master_summary.json"
    summary_file_sha = write_json_new(summary_path, summary)
    files["stage9_master_summary.json"] = {
        "path": "stage9_master_summary.json",
        "sha256": summary_file_sha,
        "canonical_sha256": summary["summary_sha256"],
    }

    manifest = {
        "schema_version": 1,
        "status": "stage9_compact_evidence_complete",
        "stage9_config_manifest_sha256": config["manifest_sha256"],
        "parent_stage8": config["parent_stage8"],
        "required_conditions": list(conditions),
        "seed_count": len(PRIMARY_SEEDS),
        "heavy_artifact_root": "artifacts/cd_robustness_v1",
        "large_artifact_archive_required_for_publication": True,
        "row_level_prediction_traces_exported": False,
        "neural_checkpoint_binaries_exported": False,
        "files": dict(sorted(files.items())),
    }
    manifest["manifest_sha256"] = canonical_sha256(manifest)
    write_json_new(STAGE9_COMPACT_ROOT / "compact_export_manifest.json", manifest)
    return {
        "status": "stage9_compact_evidence_written",
        "manifest_sha256": manifest["manifest_sha256"],
        "master_summary_sha256": summary["summary_sha256"],
        "condition_count": len(conditions),
        "seed_count": len(PRIMARY_SEEDS),
    }


def verify_stage9_compact_evidence() -> dict[str, Any]:
    config = verify_stage9_config_for_execution(require_clean=False)
    manifest_path = STAGE9_COMPACT_ROOT / "compact_export_manifest.json"
    manifest = _load_writer_json(manifest_path)
    stored = manifest.pop("manifest_sha256", None)
    if stored != canonical_sha256(manifest):
        raise ValueError("Stage-9 compact manifest canonical identity mismatch.")
    if manifest["stage9_config_manifest_sha256"] != config["manifest_sha256"]:
        raise ValueError("Stage-9 compact evidence references wrong config.")
    if tuple(manifest["required_conditions"]) != required_conditions(config):
        raise ValueError("Stage-9 compact condition set changed.")
    if int(manifest["seed_count"]) != len(PRIMARY_SEEDS):
        raise ValueError("Stage-9 compact evidence seed count changed.")
    if manifest["row_level_prediction_traces_exported"] is not False:
        raise ValueError("Stage-9 compact export unexpectedly contains row traces.")
    if manifest["neural_checkpoint_binaries_exported"] is not False:
        raise ValueError("Stage-9 compact export unexpectedly contains checkpoints.")

    for descriptor in manifest["files"].values():
        path = STAGE9_COMPACT_ROOT / descriptor["path"]
        if not path.is_file():
            raise FileNotFoundError(f"Missing Stage-9 compact file: {path}")
        if sha256_file(path) != descriptor["sha256"]:
            raise ValueError(f"Stage-9 compact file hash mismatch: {path}")

    summary = _load_writer_json(STAGE9_COMPACT_ROOT / "stage9_master_summary.json")
    summary_sha = summary.pop("summary_sha256", None)
    if summary_sha != canonical_sha256(summary):
        raise ValueError("Stage-9 master summary canonical identity mismatch.")
    return {
        "status": "stage9_compact_evidence_verified",
        "manifest_sha256": stored,
        "master_summary_sha256": summary_sha,
        "condition_count": len(manifest["required_conditions"]),
        "seed_count": int(manifest["seed_count"]),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Export or verify Stage-9 compact evidence.")
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    result = (
        verify_stage9_compact_evidence()
        if args.verify_only
        else export_stage9_compact_evidence()
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
