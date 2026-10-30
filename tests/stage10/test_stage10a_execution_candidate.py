"""Stage-10A executable-binding candidate only; no models or real outcomes."""
from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from tools.stage10.stage10a_execution_candidate import (
    derive_expected, verify_candidate, verify_from_repository,
)

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def documents() -> tuple[dict, dict, dict, dict]:
    files = (
        "data/manifests/stage10_plus_master_replication_sensitivity_v1_1.json",
        "data/manifests/stage10a_goldeneye_attack_pattern_v1.json",
        "data/manifests/cd_primary_run_config_v1_1.json",
        "data/manifests/stage10a_execution_candidate_v1.json",
    )
    return tuple(
        json.loads((ROOT / path).read_text(encoding="utf-8"))
        for path in files
    )


def test_exact_frozen_bindings_and_gate_are_verified(documents) -> None:
    master, stage, primary, candidate = documents
    assert candidate == derive_expected(master, stage, primary)
    assert verify_from_repository() == {
        "candidate_consistent": True, "execution_authorized": False,
        "source_receipt_accepted": False, "real_three_arm_isolation_verified": False,
    }
    assert candidate["source_only"]["feature_count"] == 77
    assert candidate["implementation"]["label_latency_rows"] == 5000
    assert candidate["implementation"]["stage10a_execution_entrypoint_exists"] is False
    assert candidate["arms"]["seeds"] == [0, 1, 2, 3, 4]
    assert candidate["arms"]["names"] == [
        "c_frozen_symbolic", "d_drift", "d_periodic"
    ]


@pytest.mark.parametrize("path,value", [
    (("governance", "stage10_execution_permitted"), True),
    (("governance", "release_signed"), True),
    (("source_only", "scenario", "boundary_role"), "visible_to_detector"),
    (("source_only", "source_receipt_status"), "accepted_without_proof"),
    (("arms", "seeds"), [0, 1, 2, 3, 4, 5]),
    (("arms", "shared_trace_real_provenance_verified"), True),
    (("inherited_neural", "checkpoint_sha256_by_seed", "0"), "0" * 64),
    (("inherited_neural", "monitor_threshold_by_seed", "0"), 0.01),
    (("inherited_neural", "primary_control_plane", "adwin", "delta"), 0.01),
    (("inherited_neural", "primary_fusion", "neural_weight"), 0.9),
    (("inherited_symbolic", "primary_symbolic_operator", "periodic_clocks"), [2, 3]),
    (("implementation", "label_latency_rows"), 0),
    (("implementation", "write_once_outputs"), False),
    (("implementation", "stage10a_execution_entrypoint_exists"), True),
    (("evaluation", "primary_endpoints"), []),
    (("evaluation", "multiplicity"), "no_correction"),
])
def test_candidate_mutation_fails_closed(documents, path, value) -> None:
    master, stage, primary, candidate = copy.deepcopy(documents)
    node = candidate
    for key in path[:-1]:
        node = node[key]
    node[path[-1]] = value
    with pytest.raises(ValueError, match="does not exactly match"):
        verify_candidate(candidate, master, stage, primary)


def test_original_authority_mutations_fail_even_if_candidate_unchanged(documents) -> None:
    master, stage, primary, candidate = copy.deepcopy(documents)
    stage["adaptive_mechanism"]["adwin_delta"] = 0.01
    with pytest.raises(ValueError, match="diverges"):
        verify_candidate(candidate, master, stage, primary)
    stage["adaptive_mechanism"]["adwin_delta"] = 0.002
    master["hard_gate"]["stage10_execution_permitted"] = True
    with pytest.raises(ValueError, match="hard gate"):
        verify_candidate(candidate, master, stage, primary)
    master["hard_gate"]["stage10_execution_permitted"] = False
    primary["system_a"]["monitor_threshold_by_seed"]["1"] = 0.5
    with pytest.raises(ValueError, match="does not exactly match"):
        verify_candidate(candidate, master, stage, primary)


def test_no_unknown_field_can_be_injected(documents) -> None:
    master, stage, primary, candidate = copy.deepcopy(documents)
    candidate["extra_treatment_outcomes"] = {"E1": 1.0}
    with pytest.raises(ValueError, match="does not exactly match"):
        verify_candidate(candidate, master, stage, primary)


def test_candidate_requires_frozen_input_files(tmp_path) -> None:
    with pytest.raises(FileNotFoundError):
        verify_from_repository(root=tmp_path)


def test_candidate_rejects_reformatted_upstream_manifest(documents, tmp_path) -> None:
    master, stage, primary, candidate = documents
    tmp_manifest = tmp_path / "data/manifests"
    tmp_manifest.mkdir(parents=True)
    (tmp_manifest / "stage10_plus_master_replication_sensitivity_v1_1.json").write_text(
        json.dumps(master), encoding="utf-8"
    )
    (tmp_manifest / "stage10a_goldeneye_attack_pattern_v1.json").write_text(
        json.dumps(stage), encoding="utf-8"
    )
    (tmp_manifest / "cd_primary_run_config_v1_1.json").write_text(
        json.dumps(primary), encoding="utf-8"
    )
    (tmp_manifest / "stage10a_execution_candidate_v1.json").write_text(
        json.dumps(candidate), encoding="utf-8"
    )
    with pytest.raises(ValueError, match="Frozen Git blob identity changed"):
        verify_from_repository(root=tmp_path)
