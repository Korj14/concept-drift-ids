from __future__ import annotations

import json
import platform
from dataclasses import asdict
from pathlib import Path
from typing import Any

from concept_drift_ids.cd_control_plane import (
    SYSTEM_A_MONITOR_THRESHOLDS,
    canonical_sha256,
)
from concept_drift_ids.cd_r0_lifecycle import (
    ACCEPTED_R0_V2_MANIFEST_SHA256,
    load_accepted_r0_v2_manifest,
    load_accepted_r0_v2_rules,
)
from concept_drift_ids.cd_shared_runner import (
    ControlPlaneConfig,
    verify_primary_control_plane_configuration,
)
from concept_drift_ids.cd_symbolic_arms import (
    SymbolicOperatorConfig,
    verify_primary_symbolic_operator_config,
)
from concept_drift_ids.scenario_manifest import sha256_file


PROJECT_ROOT = Path(__file__).resolve().parents[2]

EXPECTED_SYSTEM_A_MANIFEST_SHA256 = (
    "42004b5ed100b690023b9998bdc959fac41ab947b996fb7c58e44cee5e8dc6de"
)
EXPECTED_PREPROCESSING_STATE_HASH = (
    "4527f77220f2cf6063108a7d71d80aaa0e82099ad282ff25408a2d9ce3488b1e"
)
EXPECTED_SCENARIO_RAW_SHA256 = (
    "c864cd53b155ae1b29f2321d28b18562381fb6d1a77dc563b5f5eba3ec3eb82c"
)
EXPECTED_SCENARIO_CANONICAL_SHA256 = (
    "3d1c3f9775ac5c8a73053634784be513bb1714ef7f26fa9db406ccd78c4344e3"
)
EXPECTED_SYSTEM_A_CHECKPOINT_SHA256 = {
    0: "514c6d552b3cd680ae966bbb568105bd2871bc68d3a47aded070a70ba0615bd1",
    1: "07696c3f580645d9c96ac3e736cfb5eeaa8033f148bf64822e8ee105861cf552",
    2: "7630514cf409256bd2bbe27eca59f881acb238be698b5fdb1ee12bca8e402491",
    3: "cce1ce47db047b9d441bbe6dad9bd53f1ee6ff3ad7d404521cae72a38bccd4b4",
    4: "9b9e56371f3246482998c4efea4829e1e6d5aaf549bb43e1af05e471dfcb9e93",
}

REQUIRED_IMPLEMENTATION_FILES = (
    "C_D_FINAL_ANALYSIS_REPRODUCIBILITY_PROTOCOL.md",
    "D_SYMBOLIC_LIFECYCLE_PROTOCOL.md",
    "D_TRIGGER_ABLATION_PROTOCOL.md",
    "STATISTICAL_ANALYSIS_PLAN.md",
    "EXPERIMENT_CONTROL_REGISTER.md",
    "STAGE6_HANDOFF.md",
    "STAGE7_SYMBOLIC_IMPLEMENTATION.md",
    "STAGE7_HANDOFF.md",
    "STAGE7_R0_V2_PORTABILITY_CORRECTION.md",
)


def _canonical_file_hash(path: Path) -> str:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return canonical_sha256(payload)


def _verify_preprocessing_state(
    project_root: Path,
) -> dict[str, Any]:
    path = (
        project_root
        / "data"
        / "manifests"
        / "sudden_benign_v1_preprocessing_v1.json"
    )
    if not path.is_file():
        raise FileNotFoundError(f"Missing frozen preprocessing state: {path}")
    state = json.loads(path.read_text(encoding="utf-8"))
    stored = state.get("core_state_sha256")
    core = dict(state)
    core.pop("core_state_sha256", None)
    if canonical_sha256(core) != stored:
        raise ValueError("Frozen preprocessing core hash mismatch.")
    if stored != EXPECTED_PREPROCESSING_STATE_HASH:
        raise ValueError("Frozen preprocessing state is not the accepted identity.")
    if len(state["feature_schema"]["ordered_columns"]) != 77:
        raise ValueError("Frozen preprocessing feature count changed.")
    return state


def _verify_scenario_manifest(
    project_root: Path,
    preprocessing_state: dict[str, Any],
) -> dict[str, Any]:
    path = project_root / "data" / "manifests" / "sudden_benign_v1.json"
    if not path.is_file():
        raise FileNotFoundError(f"Missing frozen scenario manifest: {path}")
    if sha256_file(path) != EXPECTED_SCENARIO_RAW_SHA256:
        raise ValueError("Frozen scenario raw manifest hash mismatch.")
    if _canonical_file_hash(path) != EXPECTED_SCENARIO_CANONICAL_SHA256:
        raise ValueError("Frozen scenario canonical manifest hash mismatch.")
    scenario = json.loads(path.read_text(encoding="utf-8"))
    if scenario.get("scenario_id") != "cicids2017_sudden_benign_v1":
        raise ValueError("Unexpected frozen scenario identity.")
    if scenario.get("scenario_version") != 1:
        raise ValueError("Unexpected frozen scenario version.")

    state_scenario = preprocessing_state["scenario"]
    if (
        state_scenario["scenario_manifest_sha256"]
        != EXPECTED_SCENARIO_RAW_SHA256
    ):
        raise ValueError("Preprocessing state references wrong scenario raw hash.")
    if (
        state_scenario["scenario_manifest_canonical_sha256"]
        != EXPECTED_SCENARIO_CANONICAL_SHA256
    ):
        raise ValueError(
            "Preprocessing state references wrong scenario canonical hash."
        )
    return scenario


def _verify_system_a_manifest(
    project_root: Path,
    *,
    preprocessing_state_hash: str,
) -> dict[str, Any]:
    path = project_root / "data" / "manifests" / "system_a_v1.json"
    if not path.is_file():
        raise FileNotFoundError(f"Missing System-A manifest: {path}")
    manifest = json.loads(path.read_text(encoding="utf-8"))
    stored = manifest.get("manifest_sha256")
    core = dict(manifest)
    core.pop("manifest_sha256", None)
    if canonical_sha256(core) != stored:
        raise ValueError("System-A manifest canonical hash mismatch.")
    if stored != EXPECTED_SYSTEM_A_MANIFEST_SHA256:
        raise ValueError("System-A manifest is not the accepted identity.")
    if manifest["preprocessing_state_hash"] != preprocessing_state_hash:
        raise ValueError("System-A manifest preprocessing identity mismatch.")

    records = manifest["seed_records"]
    if sorted(int(record["seed"]) for record in records) != [0, 1, 2, 3, 4]:
        raise ValueError("System-A seed inventory differs from frozen contract.")
    for record in records:
        seed = int(record["seed"])
        expected_hash = EXPECTED_SYSTEM_A_CHECKPOINT_SHA256[seed]
        if record["checkpoint_sha256"] != expected_hash:
            raise ValueError(
                f"System-A checkpoint manifest hash changed for seed {seed}."
            )
        checkpoint = project_root / str(record["checkpoint_file"])
        if not checkpoint.is_file():
            raise FileNotFoundError(
                f"Missing accepted System-A checkpoint for seed {seed}: "
                f"{checkpoint}"
            )
        if sha256_file(checkpoint) != expected_hash:
            raise ValueError(
                f"System-A checkpoint file hash mismatch for seed {seed}."
            )
        if float(record["threshold"]) != float(
            SYSTEM_A_MONITOR_THRESHOLDS[seed]
        ):
            raise ValueError(
                f"System-A threshold changed for seed {seed}."
            )
    return manifest


def verify_implementation_ready(
    *,
    project_root: Path = PROJECT_ROOT,
) -> dict[str, Any]:
    if platform.python_version() != "3.11.9":
        raise RuntimeError("Implementation-ready preflight requires Python 3.11.9.")

    for relative in REQUIRED_IMPLEMENTATION_FILES:
        path = project_root / relative
        if not path.is_file():
            raise FileNotFoundError(
                f"Missing implementation-ready governance artifact: {path}"
            )

    sap = (project_root / "STATISTICAL_ANALYSIS_PLAN.md").read_text(
        encoding="utf-8"
    )
    if "**Version:** 1.0 — frozen prospective C/D analysis plan" not in sap:
        raise ValueError("Statistical Analysis Plan is not frozen at v1.0.")
    if "TBD BEFORE C/D" in sap:
        raise ValueError("Statistical Analysis Plan has unresolved C/D TBD.")

    preprocessing = _verify_preprocessing_state(project_root)
    scenario = _verify_scenario_manifest(project_root, preprocessing)
    system_a = _verify_system_a_manifest(
        project_root,
        preprocessing_state_hash=preprocessing["core_state_sha256"],
    )

    r0_manifest = load_accepted_r0_v2_manifest(project_root=project_root)
    if r0_manifest["manifest_sha256"] != ACCEPTED_R0_V2_MANIFEST_SHA256:
        raise ValueError("R0.v2 accepted identity mismatch.")
    r0_counts = {
        seed: len(load_accepted_r0_v2_rules(seed, project_root=project_root))
        for seed in range(5)
    }

    for seed in range(5):
        verify_primary_control_plane_configuration(
            seed=seed,
            monitor_threshold=SYSTEM_A_MONITOR_THRESHOLDS[seed],
            anchor_row_count=10_000,
            config=ControlPlaneConfig(),
        )
    verify_primary_symbolic_operator_config(SymbolicOperatorConfig())

    return {
        "status": "implementation_ready_preflight_passed",
        "python_version": platform.python_version(),
        "scenario_id": scenario["scenario_id"],
        "scenario_version": scenario["scenario_version"],
        "scenario_raw_sha256": EXPECTED_SCENARIO_RAW_SHA256,
        "scenario_canonical_sha256": EXPECTED_SCENARIO_CANONICAL_SHA256,
        "preprocessing_state_hash": preprocessing["core_state_sha256"],
        "system_a_manifest_sha256": system_a["manifest_sha256"],
        "system_a_checkpoint_sha256": dict(EXPECTED_SYSTEM_A_CHECKPOINT_SHA256),
        "system_b_v2_manifest_sha256": r0_manifest["manifest_sha256"],
        "system_b_v2_text_hash_policy": "normalized_text_to_repository_lf_identity",
        "system_b_v2_active_rule_counts": r0_counts,
        "primary_control_plane_config_sha256": canonical_sha256(
            {
                "config": asdict(ControlPlaneConfig()),
                "thresholds": SYSTEM_A_MONITOR_THRESHOLDS,
            }
        ),
        "primary_symbolic_operator_config_sha256": (
            SymbolicOperatorConfig().sha256()
        ),
        "primary_pre_post_partitions_loaded": False,
    }



def main() -> None:
    result = verify_implementation_ready()
    print(json.dumps(result, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
