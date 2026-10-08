from __future__ import annotations

import json
import subprocess
from dataclasses import asdict
from pathlib import Path
from typing import Any, Mapping, Sequence

from concept_drift_ids.cd_analysis import PRIMARY_CONFIRMATORY_ENDPOINTS
from concept_drift_ids.cd_control_plane import (
    ADAPTATION_SHUFFLE_SEED_BASE,
    ADWIN_CONFIG,
    ANCHOR_SEED,
    ONLINE_RESERVOIR_SEED,
    REPLAY_SAMPLE_SEED_BASE,
    SYSTEM_A_MONITOR_THRESHOLDS,
    canonical_sha256,
    write_json_new,
)
from concept_drift_ids.cd_implementation_preflight import (
    ACCEPTED_R0_V2_MANIFEST_SHA256,
    EXPECTED_PREPROCESSING_STATE_HASH,
    EXPECTED_SCENARIO_CANONICAL_SHA256,
    EXPECTED_SCENARIO_RAW_SHA256,
    EXPECTED_SYSTEM_A_CHECKPOINT_SHA256,
    EXPECTED_SYSTEM_A_MANIFEST_SHA256,
    PROJECT_ROOT,
    verify_implementation_ready,
)
from concept_drift_ids.cd_runtime import PRIMARY_THREAD_ENV
from concept_drift_ids.cd_shared_runner import ControlPlaneConfig
from concept_drift_ids.cd_symbolic_arms import (
    PRIMARY_PERIODIC_CLOCKS,
    PRIMARY_STREAM_LENGTH,
    SymbolicOperatorConfig,
)
from concept_drift_ids.cd_symbolic_evaluation import (
    FUSION_THRESHOLDS,
    PRIMARY_NEURAL_WEIGHT,
)
from concept_drift_ids.scenario_manifest import (
    sha256_file,
    sha256_normalized_text,
)


PRIMARY_CONFIG_SCHEMA_VERSION = 1
PRIMARY_RUN_ID = "cd-primary-v1"
IMPLEMENTATION_READY_TAG = "cd-implementation-ready-v1.1"
IMPLEMENTATION_READY_COMMIT = (
    "5627e36c7f1fef9620346e31e2aee01a2dd155ee"
)
PRIMARY_CONFIG_PATH = (
    PROJECT_ROOT / "data" / "manifests" / "cd_primary_run_config_v1.json"
)
PRIMARY_OUTPUT_ROOT = PROJECT_ROOT / "artifacts" / "cd_primary_v1"
PRIMARY_SEEDS = (0, 1, 2, 3, 4)
PRIMARY_PHASES = (
    "phase_a_shared_control_plane",
    "phase_b_symbolic_arms",
    "phase_c_offline_evaluation",
)
PRIMARY_ARMS = (
    "c_frozen_symbolic",
    "d_drift",
    "d_periodic",
)

CURRENT_GOVERNING_SOURCE_HASHES = {
    "MAIN - Concept_Drift_NIDS_Research_Gap_Doctrine.docx": (
        "c3f1fed692ff0478c221925fca5c311380617a993e7ebf0021af2e05a362ab66"
    ),
    "Reconciled_Pre-Stage_3_and_Stage_3_Implementation_Plan.docx": (
        "05378ef14437f037bab0aa77853a16980b4fc60ac303398acc1cc293bdd32bdb"
    ),
}

PROTOCOL_PATHS = (
    "GOVERNING_SOURCES.md",
    "RESEARCH_DOCTRINE.md",
    "EXPERIMENT_CONTROL_REGISTER.md",
    "STATISTICAL_ANALYSIS_PLAN.md",
    "C_D_STREAM_TIME_CONTRACT.md",
    "C_D_DRIFT_MONITOR_PROTOCOL.md",
    "C_D_NEURAL_ADAPTATION_PROTOCOL.md",
    "C_D_FUSION_THRESHOLD_PROTOCOL.md",
    "D_SYMBOLIC_LIFECYCLE_PROTOCOL.md",
    "D_TRIGGER_ABLATION_PROTOCOL.md",
    "C_D_FINAL_ANALYSIS_REPRODUCIBILITY_PROTOCOL.md",
    "STAGE7_SYMBOLIC_IMPLEMENTATION.md",
    "STAGE7_R0_V2_PORTABILITY_CORRECTION.md",
    "STAGE8_PRIMARY_EXECUTION_PROTOCOL.md",
)

SCIENTIFIC_SOURCE_PATHS = (
    ".gitattributes",
    ".gitignore",
    "src/concept_drift_ids/neural.py",
    "src/concept_drift_ids/frozen_preprocessing.py",
    "src/concept_drift_ids/scenario_loader.py",
    "src/concept_drift_ids/system_a.py",
    "src/concept_drift_ids/cd_control_plane.py",
    "src/concept_drift_ids/cd_evidence.py",
    "src/concept_drift_ids/cd_runtime.py",
    "src/concept_drift_ids/cd_shared_runner.py",
    "src/concept_drift_ids/cd_symbolic_lifecycle.py",
    "src/concept_drift_ids/cd_symbolic_candidates.py",
    "src/concept_drift_ids/cd_symbolic_arms.py",
    "src/concept_drift_ids/cd_symbolic_runner.py",
    "src/concept_drift_ids/cd_symbolic_evidence.py",
    "src/concept_drift_ids/cd_symbolic_evaluation.py",
    "src/concept_drift_ids/cd_analysis.py",
    "src/concept_drift_ids/cd_r0_lifecycle.py",
    "src/concept_drift_ids/cd_implementation_preflight.py",
    "src/concept_drift_ids/cd_primary_config.py",
    "src/concept_drift_ids/cd_primary_adapter.py",
    "src/concept_drift_ids/cd_primary_phase_a.py",
    "src/concept_drift_ids/cd_primary_phase_b.py",
    "src/concept_drift_ids/cd_primary_phase_c.py",
    "src/concept_drift_ids/cd_primary_export.py",
    "run.py",
    "scripts/run_primary.ps1",
)


def _git(
    *args: str,
    project_root: Path = PROJECT_ROOT,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=project_root,
        check=check,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


def _git_output(
    *args: str,
    project_root: Path = PROJECT_ROOT,
) -> str:
    return _git(*args, project_root=project_root).stdout.strip()


def require_clean_worktree(
    *,
    project_root: Path = PROJECT_ROOT,
) -> None:
    status = _git_output("status", "--porcelain", project_root=project_root)
    if status:
        raise RuntimeError(
            "Primary C/D preparation/execution requires a clean worktree."
        )


def verify_implementation_tag(
    *,
    project_root: Path = PROJECT_ROOT,
) -> None:
    target = _git_output(
        "rev-list",
        "-n",
        "1",
        IMPLEMENTATION_READY_TAG,
        project_root=project_root,
    )
    if target != IMPLEMENTATION_READY_COMMIT:
        raise ValueError(
            "Corrected implementation-ready tag does not resolve to the "
            "accepted commit."
        )
    ancestor = _git(
        "merge-base",
        "--is-ancestor",
        IMPLEMENTATION_READY_COMMIT,
        "HEAD",
        project_root=project_root,
        check=False,
    )
    if ancestor.returncode != 0:
        raise ValueError(
            "Current HEAD does not descend from the corrected "
            "implementation-ready milestone."
        )


def _text_hashes(
    paths: Sequence[str],
    *,
    project_root: Path,
) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for relative in paths:
        path = project_root / relative
        if not path.is_file():
            raise FileNotFoundError(f"Missing frozen source/protocol file: {path}")
        hashes[relative] = sha256_normalized_text(path)
    return hashes


def _requirements_identity(
    *,
    project_root: Path,
) -> dict[str, str]:
    path = project_root / "requirements-lock.txt"
    if not path.is_file():
        raise FileNotFoundError(f"Missing requirements lock: {path}")
    return {
        "path": "requirements-lock.txt",
        "sha256": sha256_file(path),
        "normalized_text_sha256": sha256_normalized_text(path),
    }


def build_primary_run_config(
    *,
    project_root: Path = PROJECT_ROOT,
    preflight: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    verify_implementation_tag(project_root=project_root)
    require_clean_worktree(project_root=project_root)
    preflight_result = (
        dict(preflight)
        if preflight is not None
        else verify_implementation_ready(project_root=project_root)
    )
    if (
        preflight_result.get("status")
        != "implementation_ready_preflight_passed"
    ):
        raise ValueError("Implementation-ready preflight has not passed.")
    if preflight_result.get("primary_pre_post_partitions_loaded") is not False:
        raise ValueError("Preparation preflight unexpectedly loaded primary data.")

    source_hashes = _text_hashes(
        SCIENTIFIC_SOURCE_PATHS,
        project_root=project_root,
    )
    protocol_hashes = _text_hashes(
        PROTOCOL_PATHS,
        project_root=project_root,
    )
    source_tree_sha256 = canonical_sha256(source_hashes)
    protocol_bundle_sha256 = canonical_sha256(protocol_hashes)
    prepared_from = _git_output(
        "rev-parse",
        "HEAD",
        project_root=project_root,
    )

    payload: dict[str, Any] = {
        "schema_version": PRIMARY_CONFIG_SCHEMA_VERSION,
        "run_id": PRIMARY_RUN_ID,
        "status": "frozen_before_primary_adaptive_access",
        "implementation_ready": {
            "tag": IMPLEMENTATION_READY_TAG,
            "commit": IMPLEMENTATION_READY_COMMIT,
            "prepared_from_git_commit": prepared_from,
        },
        "governing_source_hashes": dict(CURRENT_GOVERNING_SOURCE_HASHES),
        "protocol_hashes": protocol_hashes,
        "protocol_bundle_sha256": protocol_bundle_sha256,
        "scientific_source_hashes": source_hashes,
        "scientific_source_tree_sha256": source_tree_sha256,
        "requirements": _requirements_identity(project_root=project_root),
        "scenario": {
            "scenario_id": "cicids2017_sudden_benign_v1",
            "scenario_version": 1,
            "manifest_raw_sha256": EXPECTED_SCENARIO_RAW_SHA256,
            "manifest_canonical_sha256": (
                EXPECTED_SCENARIO_CANONICAL_SHA256
            ),
            "preprocessing_state_hash": EXPECTED_PREPROCESSING_STATE_HASH,
            "stream_rows": PRIMARY_STREAM_LENGTH,
            "stream_order": ["pre_drift", "post_drift"],
            "logical_time": "zero_based_stream_row_index",
            "boundary_role": "offline_scoring_and_diagnostics_only",
        },
        "system_a": {
            "manifest_sha256": EXPECTED_SYSTEM_A_MANIFEST_SHA256,
            "checkpoint_sha256_by_seed": {
                str(seed): digest
                for seed, digest in sorted(
                    EXPECTED_SYSTEM_A_CHECKPOINT_SHA256.items()
                )
            },
            "monitor_threshold_by_seed": {
                str(seed): float(threshold)
                for seed, threshold in sorted(
                    SYSTEM_A_MONITOR_THRESHOLDS.items()
                )
            },
        },
        "r0_v2": {
            "manifest_sha256": ACCEPTED_R0_V2_MANIFEST_SHA256,
            "text_hash_policy": (
                "utf8_eol_normalized_to_repository_lf_identity"
            ),
            "active_rule_counts": {
                str(key): int(value)
                for key, value in sorted(
                    preflight_result[
                        "system_b_v2_active_rule_counts"
                    ].items()
                )
            },
        },
        "primary_control_plane": {
            "config": asdict(ControlPlaneConfig()),
            "config_sha256": preflight_result[
                "primary_control_plane_config_sha256"
            ],
            "adwin": dict(ADWIN_CONFIG),
            "rng": {
                "anchor_seed": ANCHOR_SEED,
                "online_reservoir_seed": ONLINE_RESERVOIR_SEED,
                "replay_sample_seed_base": REPLAY_SAMPLE_SEED_BASE,
                "adaptation_shuffle_seed_base": (
                    ADAPTATION_SHUFFLE_SEED_BASE
                ),
            },
        },
        "primary_symbolic_operator": {
            "config": asdict(SymbolicOperatorConfig()),
            "config_sha256": preflight_result[
                "primary_symbolic_operator_config_sha256"
            ],
            "periodic_clocks": list(PRIMARY_PERIODIC_CLOCKS),
            "maximum_opportunities_per_seed": 4,
        },
        "fusion": {
            "primary_neural_weight": PRIMARY_NEURAL_WEIGHT,
            "thresholds": {
                str(weight): {
                    str(seed): float(threshold)
                    for seed, threshold in sorted(seed_map.items())
                }
                for weight, seed_map in sorted(FUSION_THRESHOLDS.items())
            },
            "post_hoc_recalibration": False,
        },
        "analysis": {
            "confirmatory_endpoints": list(PRIMARY_CONFIRMATORY_ENDPOINTS),
            "paired_seeds": list(PRIMARY_SEEDS),
            "confirmatory_unit": (
                "matched_seed_within_fixed_primary_scenario"
            ),
        },
        "execution": {
            "phase_order": list(PRIMARY_PHASES),
            "arms": list(PRIMARY_ARMS),
            "phase_a_must_freeze_before_phase_b": True,
            "phase_b_must_use_shared_phase_a_identity": True,
            "primary_cpu_only": True,
            "required_thread_environment": dict(PRIMARY_THREAD_ENV),
            "write_once_outputs": True,
            "execution_output_root": "artifacts/cd_primary_v1",
            "execution_outputs_gitignored": True,
            "compact_export_root": "results/frozen/cd_primary_v1",
            "first_heldout_access_allowed_only_after_config_is_tracked_clean_and_ci_green": True,
        },
        "preparation": {
            "preflight_status": preflight_result["status"],
            "primary_partitions_loaded": False,
            "heldout_access_occurred": False,
        },
    }
    payload["manifest_sha256"] = canonical_sha256(payload)
    return payload


def write_primary_run_config(
    *,
    path: Path = PRIMARY_CONFIG_PATH,
    project_root: Path = PROJECT_ROOT,
) -> dict[str, Any]:
    if path.exists():
        raise FileExistsError(
            f"Refusing to overwrite frozen primary config: {path}"
        )
    payload = build_primary_run_config(project_root=project_root)
    write_json_new(path, payload)
    return payload


def load_primary_run_config(
    *,
    path: Path = PRIMARY_CONFIG_PATH,
) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(
            "Primary run config is absent. Run cd-primary-prepare and commit "
            "the generated manifest before any primary adaptive execution."
        )
    payload = json.loads(path.read_text(encoding="utf-8"))
    stored_payload_sha = payload.pop("payload_sha256", None)
    stored_manifest_sha = payload.get("manifest_sha256")
    core = dict(payload)
    core.pop("manifest_sha256", None)
    expected_manifest_sha = canonical_sha256(core)
    if stored_manifest_sha != expected_manifest_sha:
        raise ValueError("Primary run config manifest hash mismatch.")
    if stored_payload_sha is not None:
        payload_for_writer_hash = dict(payload)
        if canonical_sha256(payload_for_writer_hash) != stored_payload_sha:
            raise ValueError("Primary run config writer payload hash mismatch.")
    return payload


def _require_config_tracked_clean(
    *,
    project_root: Path,
) -> None:
    require_clean_worktree(project_root=project_root)
    result = _git(
        "ls-files",
        "--error-unmatch",
        "data/manifests/cd_primary_run_config_v1.json",
        project_root=project_root,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "Primary run config must be committed before held-out access."
        )


def _require_exact_config_commit(
    *,
    project_root: Path = PROJECT_ROOT,
) -> str:
    head = _git_output("rev-parse", "HEAD", project_root=project_root)
    config_commit = _git_output(
        "log",
        "-1",
        "--format=%H",
        "--",
        "data/manifests/cd_primary_run_config_v1.json",
        project_root=project_root,
    )
    if not config_commit or head != config_commit:
        raise RuntimeError(
            "Primary execution requires HEAD to be exactly the commit that "
            "froze cd_primary_run_config_v1.json."
        )
    return head


def verify_primary_run_config_for_execution(
    *,
    project_root: Path = PROJECT_ROOT,
) -> dict[str, Any]:
    verify_implementation_tag(project_root=project_root)
    _require_config_tracked_clean(project_root=project_root)
    _require_exact_config_commit(project_root=project_root)
    config = load_primary_run_config(
        path=project_root
        / "data"
        / "manifests"
        / "cd_primary_run_config_v1.json"
    )
    if config["run_id"] != PRIMARY_RUN_ID:
        raise ValueError("Unexpected primary run ID.")
    if config["status"] != "frozen_before_primary_adaptive_access":
        raise ValueError("Primary config status is not frozen.")
    if (
        config["implementation_ready"]["commit"]
        != IMPLEMENTATION_READY_COMMIT
    ):
        raise ValueError("Primary config uses wrong implementation parent.")
    if config["preparation"]["heldout_access_occurred"] is not False:
        raise ValueError("Primary config was not frozen before held-out access.")

    source_hashes = _text_hashes(
        SCIENTIFIC_SOURCE_PATHS,
        project_root=project_root,
    )
    if source_hashes != config["scientific_source_hashes"]:
        raise ValueError("Scientific source tree changed after config freeze.")
    if (
        canonical_sha256(source_hashes)
        != config["scientific_source_tree_sha256"]
    ):
        raise ValueError("Scientific source-tree identity mismatch.")

    protocol_hashes = _text_hashes(
        PROTOCOL_PATHS,
        project_root=project_root,
    )
    if protocol_hashes != config["protocol_hashes"]:
        raise ValueError("Protocol bundle changed after config freeze.")
    if (
        canonical_sha256(protocol_hashes)
        != config["protocol_bundle_sha256"]
    ):
        raise ValueError("Protocol-bundle identity mismatch.")

    requirements = _requirements_identity(project_root=project_root)
    if requirements != config["requirements"]:
        raise ValueError("Frozen dependency lock changed after config freeze.")
    return config


def main() -> None:
    payload = write_primary_run_config()
    print(
        json.dumps(
            {
                "status": "primary_run_config_written",
                "path": PRIMARY_CONFIG_PATH.relative_to(
                    PROJECT_ROOT
                ).as_posix(),
                "manifest_sha256": payload["manifest_sha256"],
                "scientific_source_tree_sha256": payload[
                    "scientific_source_tree_sha256"
                ],
                "protocol_bundle_sha256": payload[
                    "protocol_bundle_sha256"
                ],
                "primary_pre_post_partitions_loaded": False,
                "next_gate": (
                    "commit this manifest, require clean worktree and "
                    "green exact-head CI before Phase A"
                ),
            },
            sort_keys=True,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
