from __future__ import annotations

import json
from pathlib import Path

import pytest

import concept_drift_ids.cd_implementation_preflight as preflight
from concept_drift_ids.cd_implementation_preflight import (
    EXPECTED_PREPROCESSING_STATE_HASH,
    EXPECTED_SCENARIO_CANONICAL_SHA256,
    EXPECTED_SCENARIO_RAW_SHA256,
    EXPECTED_SYSTEM_A_MANIFEST_SHA256,
    _verify_preprocessing_state,
    _verify_scenario_manifest,
)


def test_repository_preflight_manifests_match_frozen_identities() -> None:
    state = _verify_preprocessing_state(preflight.PROJECT_ROOT)
    scenario = _verify_scenario_manifest(preflight.PROJECT_ROOT, state)

    assert state["core_state_sha256"] == EXPECTED_PREPROCESSING_STATE_HASH
    assert (
        state["scenario"]["scenario_manifest_sha256"]
        == EXPECTED_SCENARIO_RAW_SHA256
    )
    assert (
        state["scenario"]["scenario_manifest_canonical_sha256"]
        == EXPECTED_SCENARIO_CANONICAL_SHA256
    )
    assert scenario["scenario_id"] == "cicids2017_sudden_benign_v1"
    assert scenario["scenario_version"] == 1


def test_system_a_manifest_identity_is_pinned_without_claiming_checkpoint_presence() -> None:
    path = preflight.PROJECT_ROOT / "data" / "manifests" / "system_a_v1.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    assert manifest["manifest_sha256"] == EXPECTED_SYSTEM_A_MANIFEST_SHA256
    assert manifest["preprocessing_state_hash"] == EXPECTED_PREPROCESSING_STATE_HASH
    assert [int(item["seed"]) for item in manifest["seed_records"]] == [0, 1, 2, 3, 4]


def test_implementation_preflight_fails_closed_when_checkpoint_bytes_are_missing(
    tmp_path: Path,
    monkeypatch,
) -> None:
    source = preflight.PROJECT_ROOT

    for relative in (
        "STATISTICAL_ANALYSIS_PLAN.md",
        "EXPERIMENT_CONTROL_REGISTER.md",
        "C_D_FINAL_ANALYSIS_REPRODUCIBILITY_PROTOCOL.md",
        "D_SYMBOLIC_LIFECYCLE_PROTOCOL.md",
        "D_TRIGGER_ABLATION_PROTOCOL.md",
        "STAGE6_HANDOFF.md",
        "data/manifests/sudden_benign_v1.json",
        "data/manifests/sudden_benign_v1_preprocessing_v1.json",
        "data/manifests/system_a_v1.json",
        "data/manifests/system_b_v2.json",
    ):
        source_path = source / relative
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source_path.read_bytes())

    # R0 artifacts are needed only after checkpoint verification. The expected
    # fail-closed point here is deliberately earlier: missing external A bytes.
    with pytest.raises(FileNotFoundError, match="System-A checkpoint"):
        preflight.verify_implementation_ready(project_root=tmp_path)


def test_preflight_module_has_no_partition_loader_or_primary_execution_surface() -> None:
    path = Path(preflight.__file__)
    text = path.read_text(encoding="utf-8")
    assert "scenario_loader" not in text
    assert "load_partition" not in text
    assert "pre_drift" not in text
    assert "post_drift" not in text
