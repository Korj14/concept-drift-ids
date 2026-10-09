from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Mapping

from concept_drift_ids.cd_control_plane import canonical_sha256, write_json_new
from concept_drift_ids.cd_primary_config import (
    PRIMARY_CONFIG_PATH,
    PRIMARY_OUTPUT_ROOT,
    PRIMARY_SEEDS,
    PROJECT_ROOT,
    PROTOCOL_PATHS,
    SCIENTIFIC_SOURCE_PATHS,
    _git,
    _git_output,
    _requirements_identity,
    _text_hashes,
    load_primary_run_config,
    require_clean_worktree,
    verify_implementation_tag,
)
from concept_drift_ids.cd_primary_phase_a import verify_phase_a_seed
from concept_drift_ids.cd_primary_phase_b import verify_phase_b_seed
from concept_drift_ids.scenario_manifest import sha256_file


PARENT_PRIMARY_CONFIG_MANIFEST_SHA256 = (
    "3e3f768b5aa32f469440bb334508f747bbf2f7f5b08d9570a7aef2dbb9cb0257"
)
CORRECTION_RUN_ID = "cd-primary-v1.1"
CORRECTION_CONFIG_PATH = (
    PROJECT_ROOT / "data" / "manifests" / "cd_primary_run_config_v1_1.json"
)
FAILED_PHASE_C_V1_DIR = (
    PRIMARY_OUTPUT_ROOT / "phase_c_offline_evaluation" / "seed-0"
)
CORRECTED_PHASE_C_SUBDIR = "phase_c_offline_evaluation_v1_1"
CORRECTION_PROTOCOL_PATH = "STAGE8_PHASE_C_V1_1_CORRECTION.md"
CORRECTION_SOURCE_PATH = "src/concept_drift_ids/cd_primary_correction.py"

CORRECTION_PROTOCOL_PATHS = tuple(
    (*PROTOCOL_PATHS, CORRECTION_PROTOCOL_PATH)
)
CORRECTION_SOURCE_PATHS = tuple(
    (*SCIENTIFIC_SOURCE_PATHS, CORRECTION_SOURCE_PATH)
)

FROZEN_SCIENTIFIC_BLOCKS = (
    "governing_source_hashes",
    "scenario",
    "system_a",
    "r0_v2",
    "primary_control_plane",
    "primary_symbolic_operator",
    "fusion",
    "analysis",
)


def _read_verified_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"Missing correction evidence: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    stored_payload = payload.pop("payload_sha256", None)
    if stored_payload is not None and canonical_sha256(payload) != stored_payload:
        raise ValueError(f"Correction evidence payload hash mismatch: {path}")
    return payload


def _load_parent_config(
    *,
    project_root: Path = PROJECT_ROOT,
) -> dict[str, Any]:
    path = (
        project_root
        / "data"
        / "manifests"
        / "cd_primary_run_config_v1.json"
    )
    parent = load_primary_run_config(path=path)
    if parent["manifest_sha256"] != PARENT_PRIMARY_CONFIG_MANIFEST_SHA256:
        raise ValueError("Parent primary v1 config identity changed.")
    return parent


def _failed_attempt_identity(
    *,
    project_root: Path = PROJECT_ROOT,
) -> dict[str, Any]:
    root = (
        project_root
        / "artifacts"
        / "cd_primary_v1"
        / "phase_c_offline_evaluation"
        / "seed-0"
    )
    if not root.is_dir():
        raise FileNotFoundError(
            "Expected failed Phase-C v1 seed-0 directory is absent."
        )
    entries = tuple(sorted(path.name for path in root.iterdir()))
    expected = ("attempt.json", "failure.json")
    if entries != expected:
        raise ValueError(
            "Failed Phase-C v1 directory must contain exactly the preserved "
            f"attempt/failure artifacts. Observed: {entries}"
        )

    attempt_path = root / "attempt.json"
    failure_path = root / "failure.json"
    attempt = _read_verified_json(attempt_path)
    failure = _read_verified_json(failure_path)

    if int(attempt["seed"]) != 0 or int(failure["seed"]) != 0:
        raise ValueError("Failed Phase-C v1 seed identity changed.")
    if (
        attempt["primary_config_manifest_sha256"]
        != PARENT_PRIMARY_CONFIG_MANIFEST_SHA256
    ):
        raise ValueError(
            "Failed Phase-C v1 attempt references the wrong primary config."
        )
    if attempt["phase"] != "offline_boundary_aware_evaluation":
        raise ValueError("Unexpected failed Phase-C attempt phase.")
    if failure["phase"] != "offline_boundary_aware_evaluation":
        raise ValueError("Unexpected failed Phase-C failure phase.")
    if attempt["adaptive_components_received_boundary"] is not False:
        raise ValueError("Failed attempt reports adaptive boundary contamination.")
    if failure["adaptive_components_received_boundary"] is not False:
        raise ValueError("Failed attempt reports adaptive boundary contamination.")
    if failure["exception_type"] != "NameError":
        raise ValueError("Unexpected Phase-C v1 failure exception type.")
    if "read_jsonl" not in str(failure["message"]):
        raise ValueError("Phase-C v1 failure is not the frozen read_jsonl defect.")

    return {
        "seed": 0,
        "directory": root.relative_to(project_root).as_posix(),
        "entries": list(entries),
        "attempt_file_sha256": sha256_file(attempt_path),
        "failure_file_sha256": sha256_file(failure_path),
        "attempt_payload_sha256": canonical_sha256(attempt),
        "failure_payload_sha256": canonical_sha256(failure),
        "exception_type": failure["exception_type"],
        "message": str(failure["message"]),
        "successful_scoring_artifacts_present": False,
    }


def _upstream_artifact_identities(
    parent: Mapping[str, Any],
) -> dict[str, Any]:
    phase_a: dict[str, Any] = {}
    phase_b: dict[str, Any] = {}
    for seed in PRIMARY_SEEDS:
        a = verify_phase_a_seed(seed, config=parent)
        b = verify_phase_b_seed(seed, config=parent)
        phase_a[str(seed)] = {
            "run_manifest_sha256": a["run_manifest_sha256"],
            "shared_identity_sha256": a["shared_identity_sha256"],
            "prediction_rows": int(a["prediction_rows"]),
        }
        phase_b[str(seed)] = {
            "phase_b_manifest_sha256": b["phase_b_manifest_sha256"],
            "arm_isolation_sha256": b["arm_isolation_sha256"],
        }
    return {
        "phase_a": phase_a,
        "phase_b": phase_b,
    }


def build_correction_config(
    *,
    project_root: Path = PROJECT_ROOT,
) -> dict[str, Any]:
    verify_implementation_tag(project_root=project_root)
    require_clean_worktree(project_root=project_root)

    parent = _load_parent_config(project_root=project_root)
    upstream = _upstream_artifact_identities(parent)
    failed_attempt = _failed_attempt_identity(project_root=project_root)

    source_hashes = _text_hashes(
        CORRECTION_SOURCE_PATHS,
        project_root=project_root,
    )
    protocol_hashes = _text_hashes(
        CORRECTION_PROTOCOL_PATHS,
        project_root=project_root,
    )
    prepared_from = _git_output(
        "rev-parse",
        "HEAD",
        project_root=project_root,
    )

    payload = copy.deepcopy(parent)
    payload.pop("manifest_sha256", None)
    payload["schema_version"] = 2
    payload["run_id"] = CORRECTION_RUN_ID
    payload["status"] = (
        "frozen_post_access_phase_c_v1_1_correction_before_successful_scoring"
    )
    payload["implementation_ready"]["prepared_from_git_commit"] = prepared_from
    payload["upstream_artifact_config_manifest_sha256"] = (
        PARENT_PRIMARY_CONFIG_MANIFEST_SHA256
    )
    payload["protocol_hashes"] = protocol_hashes
    payload["protocol_bundle_sha256"] = canonical_sha256(protocol_hashes)
    payload["scientific_source_hashes"] = source_hashes
    payload["scientific_source_tree_sha256"] = canonical_sha256(source_hashes)
    payload["requirements"] = _requirements_identity(project_root=project_root)
    payload["execution"]["phase_c_output_subdir"] = CORRECTED_PHASE_C_SUBDIR
    payload["execution"]["phase_a_reexecution_allowed"] = False
    payload["execution"]["phase_b_reexecution_allowed"] = False
    payload["execution"]["reuse_verified_phase_a_b_from_parent_config"] = True
    payload["preparation"] = {
        "parent_preflight_status": parent["preparation"]["preflight_status"],
        "primary_partitions_loaded_during_correction_preparation": False,
        "heldout_access_occurred": True,
        "phase_a_complete_and_reused": True,
        "phase_b_complete_and_reused": True,
        "successful_boundary_scoring_occurred_before_correction": False,
    }
    payload["correction"] = {
        "correction_id": "phase-c-read-jsonl-import-v1.1",
        "classification": "implementation_defect_correction",
        "parent_config_manifest_sha256": (
            PARENT_PRIMARY_CONFIG_MANIFEST_SHA256
        ),
        "defect": (
            "cd_primary_phase_c.execute_phase_c_seed referenced read_jsonl "
            "without importing it"
        ),
        "scientific_parameter_change": False,
        "treatment_change": False,
        "endpoint_change": False,
        "threshold_change": False,
        "upstream_adaptive_artifact_reexecution": False,
        "failed_phase_c_v1": failed_attempt,
        "reused_upstream_artifacts": upstream,
        "corrected_phase_c_output_subdir": CORRECTED_PHASE_C_SUBDIR,
    }
    payload["manifest_sha256"] = canonical_sha256(payload)
    return payload


def write_correction_config(
    *,
    path: Path = CORRECTION_CONFIG_PATH,
    project_root: Path = PROJECT_ROOT,
) -> dict[str, Any]:
    if path.exists():
        raise FileExistsError(
            f"Refusing to overwrite Phase-C correction config: {path}"
        )
    payload = build_correction_config(project_root=project_root)
    write_json_new(path, payload)
    return payload


def load_correction_config(
    *,
    path: Path = CORRECTION_CONFIG_PATH,
) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(
            "Phase-C v1.1 correction config is absent. Run "
            "cd-primary-correction-prepare and commit only that generated "
            "manifest before corrected Phase C."
        )
    payload = json.loads(path.read_text(encoding="utf-8"))
    stored_payload = payload.pop("payload_sha256", None)
    stored_manifest = payload.get("manifest_sha256")
    core = dict(payload)
    core.pop("manifest_sha256", None)
    if stored_manifest != canonical_sha256(core):
        raise ValueError("Phase-C v1.1 correction config hash mismatch.")
    if stored_payload is not None and canonical_sha256(payload) != stored_payload:
        raise ValueError("Phase-C v1.1 writer payload hash mismatch.")
    return payload


def _require_correction_config_commit(
    config: Mapping[str, Any],
    *,
    project_root: Path = PROJECT_ROOT,
) -> None:
    require_clean_worktree(project_root=project_root)
    relative = "data/manifests/cd_primary_run_config_v1_1.json"
    tracked = _git(
        "ls-files",
        "--error-unmatch",
        relative,
        project_root=project_root,
        check=False,
    )
    if tracked.returncode != 0:
        raise RuntimeError("Correction config must be committed before Phase C.")

    head = _git_output("rev-parse", "HEAD", project_root=project_root)
    config_commit = _git_output(
        "log",
        "-1",
        "--format=%H",
        "--",
        relative,
        project_root=project_root,
    )
    if head != config_commit:
        raise RuntimeError(
            "Corrected Phase C requires HEAD to be exactly the correction "
            "config freeze commit."
        )
    parent = _git_output("rev-parse", "HEAD^", project_root=project_root)
    prepared_from = str(
        config["implementation_ready"]["prepared_from_git_commit"]
    )
    if parent != prepared_from:
        raise RuntimeError(
            "Correction config commit parent differs from the source head "
            "recorded during correction preparation."
        )
    changed = tuple(
        line.strip()
        for line in _git_output(
            "diff-tree",
            "--no-commit-id",
            "--name-only",
            "-r",
            "HEAD",
            project_root=project_root,
        ).splitlines()
        if line.strip()
    )
    if changed != (relative,):
        raise RuntimeError(
            "Correction config freeze commit must change exactly "
            f"{relative}. Observed: {changed}"
        )


def _verify_frozen_scientific_blocks(
    correction: Mapping[str, Any],
    parent: Mapping[str, Any],
) -> None:
    for key in FROZEN_SCIENTIFIC_BLOCKS:
        if correction[key] != parent[key]:
            raise ValueError(
                f"Scientific block changed in Phase-C correction: {key}"
            )


def verify_primary_correction_for_execution(
    *,
    project_root: Path = PROJECT_ROOT,
) -> dict[str, Any]:
    verify_implementation_tag(project_root=project_root)
    config = load_correction_config(
        path=project_root
        / "data"
        / "manifests"
        / "cd_primary_run_config_v1_1.json"
    )
    _require_correction_config_commit(config, project_root=project_root)

    if config["run_id"] != CORRECTION_RUN_ID:
        raise ValueError("Unexpected Phase-C correction run ID.")
    if config["status"] != (
        "frozen_post_access_phase_c_v1_1_correction_before_successful_scoring"
    ):
        raise ValueError("Unexpected Phase-C correction config status.")
    if (
        config["upstream_artifact_config_manifest_sha256"]
        != PARENT_PRIMARY_CONFIG_MANIFEST_SHA256
    ):
        raise ValueError("Correction references wrong parent primary config.")

    parent = _load_parent_config(project_root=project_root)
    _verify_frozen_scientific_blocks(config, parent)

    source_hashes = _text_hashes(
        CORRECTION_SOURCE_PATHS,
        project_root=project_root,
    )
    if source_hashes != config["scientific_source_hashes"]:
        raise ValueError("Correction scientific source tree changed.")
    if (
        canonical_sha256(source_hashes)
        != config["scientific_source_tree_sha256"]
    ):
        raise ValueError("Correction source-tree identity mismatch.")

    protocol_hashes = _text_hashes(
        CORRECTION_PROTOCOL_PATHS,
        project_root=project_root,
    )
    if protocol_hashes != config["protocol_hashes"]:
        raise ValueError("Correction protocol bundle changed.")
    if (
        canonical_sha256(protocol_hashes)
        != config["protocol_bundle_sha256"]
    ):
        raise ValueError("Correction protocol identity mismatch.")

    requirements = _requirements_identity(project_root=project_root)
    if requirements != config["requirements"]:
        raise ValueError("Correction dependency environment changed.")

    failed = _failed_attempt_identity(project_root=project_root)
    if failed != config["correction"]["failed_phase_c_v1"]:
        raise ValueError("Preserved failed Phase-C v1 evidence changed.")

    upstream = _upstream_artifact_identities(config)
    if upstream != config["correction"]["reused_upstream_artifacts"]:
        raise ValueError("Reused Phase-A/Phase-B evidence identity changed.")

    return config


def main() -> None:
    payload = write_correction_config()
    print(
        json.dumps(
            {
                "status": "phase_c_v1_1_correction_config_written",
                "path": CORRECTION_CONFIG_PATH.relative_to(
                    PROJECT_ROOT
                ).as_posix(),
                "manifest_sha256": payload["manifest_sha256"],
                "parent_config_manifest_sha256": (
                    payload["upstream_artifact_config_manifest_sha256"]
                ),
                "failed_attempt_preserved": True,
                "phase_a_reexecution_allowed": False,
                "phase_b_reexecution_allowed": False,
                "successful_boundary_scoring_occurred_before_correction": False,
                "next_gate": (
                    "commit only this correction manifest, require clean "
                    "worktree and green exact-head CI before corrected Phase C"
                ),
            },
            sort_keys=True,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
