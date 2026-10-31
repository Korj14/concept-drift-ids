"""Synthetic/repository-only review checks. No Stage-10A model or outcomes."""
from __future__ import annotations

import copy
import inspect
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.stage10 import stage10a_production_schema_review as a


def _authorities():
    master = {
        "hard_gate": {"stage10_execution_permitted": False},
        "stage10_treatment_outcomes_accessed": False,
        "master_obligations": list(range(16)),
        "stage_specific_pre_outcome_freeze_required": list(range(19)),
    }
    stage = {
        "stage10_treatment_execution_authorized": False,
        "stage10_treatment_outcomes_accessed_during_freeze": False,
        "scenario_id": "cicids2017_goldeneye_temporal_attack_shift_v1",
        "raw_source": {"sha256": "893c27dc968bf7a8adef1689f90be55ca4a4dc3088fb63d6ff247ac56856df2a"},
        "scenario": {
            "boundary_role": "offline_evaluator_scoring_and_diagnostics_only",
            "pre": {"rows": 69260}, "post": {"rows": 69270},
            "stream_row_ids_sha256": "81924f3c39cb49adfaebea11d9aef045ab73804dd61faee49dcfbd2dd5f33f25",
        },
        "information_timing": {"label_latency_rows": 5000, "prediction_before_label_release": True},
        "primary_arms": ["c_frozen_symbolic", "d_drift", "d_periodic"],
        "inherited_identities": {
            "seeds": list(range(5)),
            "preprocessing_core_state_sha256": "4527f77220f2cf6063108a7d71d80aaa0e82099ad282ff25408a2d9ce3488b1e",
            "r0_v2_manifest_sha256": "131027d2f136494eb388183f18dcb7eb0e9d7e9fe786f22dba25f4e1624c1483",
        },
    }
    primary = {"execution": {
        "arms": stage["primary_arms"],
        "phase_order": ["phase_a_shared_control_plane", "phase_b_symbolic_arms", "phase_c_offline_evaluation"],
        "phase_a_must_freeze_before_phase_b": True,
        "write_once_outputs": True,
    }}
    source = {
        "pass": True, "logical_rows": 138530, "frozen_features": 77,
        "label_latency_rows": 5000, "raw_source_sha256": stage["raw_source"]["sha256"],
        "ordered_row_ids_sha256": stage["scenario"]["stream_row_ids_sha256"],
        "model_checkpoints_loaded": False, "neural_or_symbolic_treatments_executed": False,
        "canonical_sha256": "eb145dda1654df375016eb254e90e469b3318ebbc7a6fd17b4402a9ef855c93a",
    }
    checkpoint = {
        "pass": True, "no_model_loaded_or_predicted": True,
        "source_receipt_canonical_sha256": source["canonical_sha256"],
        "checkpoint_files": [{"seed": seed} for seed in range(5)],
    }
    return (stage, master, primary, source, checkpoint)


def _candidate():
    return a._expected(*_authorities())


def test_candidate_review_consistency_only_no_release():
    c = _candidate()
    result = a.assess_candidate(c, *_authorities())
    assert result["review_candidate_consistent"] is True
    assert result["stage10a_release_ready"] is False
    assert result["stage10a_treatment_execution_authorized"] is False
    assert c["scientific_scope"]["within_stream_mature_labels"] == 133530
    assert c["scientific_scope"]["right_censored_labels"] == 5000
    assert c["layout_reuse"]["all_five_phase_a_seals_required_before_any_phase_b"] is True
    assert len(c["layout_reuse"]["phase_a_six_journals"]) == 6
    assert len(c["unresolved_review_choices"]) == 4
    assert all(v["status"] == "PENDING_EXPLICIT_DESIGN_REVIEW"
               for v in c["unresolved_review_choices"].values())
    assert set(c["governance"].values()) == {False}


@pytest.mark.parametrize("area,key,value", [
    ("governance", "stage10a_treatment_execution_authorized", True),
    ("governance", "release_signed", True),
    ("governance", "production_schema_frozen", True),
    ("governance", "real_stage10a_entrypoint_exists", True),
    ("governance", "outcome_access_authorized", True),
    ("scientific_scope", "pre_rows", 69259),
    ("scientific_scope", "latency_rows", 0),
    ("scientific_scope", "boundary_evaluator_only", False),
    ("layout_reuse", "phase_a_six_journals", ["predictions.jsonl"]),
    ("layout_reuse", "all_five_phase_a_seals_required_before_any_phase_b", False),
    ("required_event_invariants", "prediction_append_and_fsync_before_current_clock_label_release", False),
    ("required_event_invariants", "neural_monitor_uses_neural_hard_error_not_fused_arm_score", False),
])
def test_refuse_any_unauthorized_candidate_change(area, key, value):
    bad = copy.deepcopy(_candidate())
    bad[area][key] = value
    with pytest.raises(ValueError, match="candidate mismatches"):
        a.assess_candidate(bad, *_authorities())


@pytest.mark.parametrize("choice", [
    "runtime_identity_external_witness", "label_availability_access_control",
    "checkpoint_and_phase_b_custody", "s10_04_release_scope",
])
def test_pending_decisions_cannot_be_silently_claimed_complete(choice):
    bad = copy.deepcopy(_candidate())
    bad["unresolved_review_choices"][choice]["status"] = "APPROVED"
    with pytest.raises(ValueError, match="candidate mismatches"):
        a.assess_candidate(bad, *_authorities())


def test_extra_authority_claim_rejected():
    bad = _candidate()
    bad["additional_unfrozen_protocol"] = {"grants_execution": True}
    with pytest.raises(ValueError, match="candidate mismatches"):
        a.assess_candidate(bad, *_authorities())


def test_frozen_treatment_and_outcome_holds_fail_closed():
    stage, master, primary, source, checkpoint = copy.deepcopy(_authorities())
    master["hard_gate"]["stage10_execution_permitted"] = True
    with pytest.raises(ValueError, match="HOLD"):
        a.assess_candidate(_candidate(), stage, master, primary, source, checkpoint)
    stage, master, primary, source, checkpoint = copy.deepcopy(_authorities())
    stage["stage10_treatment_outcomes_accessed_during_freeze"] = True
    with pytest.raises(ValueError, match="HOLD"):
        a.assess_candidate(_candidate(), stage, master, primary, source, checkpoint)


def test_source_checkpoint_and_frozen_clock_substitution_rejected():
    for mode in ("source", "checkpoint", "latency", "rows", "arms"):
        stage, master, primary, source, checkpoint = copy.deepcopy(_authorities())
        if mode == "source":
            source["raw_source_sha256"] = "0" * 64
        elif mode == "checkpoint":
            checkpoint["no_model_loaded_or_predicted"] = False
        elif mode == "latency":
            stage["information_timing"]["label_latency_rows"] = 12
        elif mode == "rows":
            stage["scenario"]["post"]["rows"] = 0
        else:
            stage["primary_arms"].append("new-arm")
        with pytest.raises(ValueError):
            a.assess_candidate(_candidate(), stage, master, primary, source, checkpoint)


def test_no_runtime_or_model_interface_in_review_module():
    code = inspect.getsource(a)
    for banned in ("import torch", "torch.load(", "pandas.read_csv(", "model.predict(",
                   "urlopen(", "requests.get(", "subprocess.run(", "os.system(",
                   ".write_bytes(", "open(\"wb\""):
        assert banned not in code


def test_repository_candidate_matches_frozen_original_bytes():
    """Executes only in a complete checkout; verifies exact historical receipts."""
    if not (a.ROOT / a.MASTER).is_file():
        pytest.skip("Standalone fixture path has no full GitHub repository checkout")
    out = a.assess_repository()
    assert out["review_candidate_consistent"] is True
    assert out["production_schema_frozen"] is False
    assert out["stage10a_release_ready"] is False
