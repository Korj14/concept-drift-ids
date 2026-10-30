"""Synthetic metadata only; prospective S10-04 freeze and no outcome access."""
from __future__ import annotations

import copy
import json

import pytest

from tools.stage10.stage10a_s10_04_selection import (
    NO_FIELDS, YES_FIELDS, REQUIRED_SOURCE_DOSSIER, POLICY_PATH, MASTER_PATH,
    STAGE10A_PATH, screen_synthetic_dossier, verify_policy,
    verify_repository_policy,
)


@pytest.fixture
def frozen() -> tuple[dict, dict, dict]:
    return (
        json.loads(POLICY_PATH.read_text(encoding="utf-8")),
        json.loads(MASTER_PATH.read_text(encoding="utf-8")),
        json.loads(STAGE10A_PATH.read_text(encoding="utf-8")),
    )


def _synthetic() -> dict:
    record = {k: True for k in YES_FIELDS}
    record.update({k: False for k in NO_FIELDS})
    record["candidate_id"] = "fixture-source-only"
    assert set(record) == REQUIRED_SOURCE_DOSSIER
    return record


def test_criteria_consistent_with_untouched_master_and_stage10a(frozen) -> None:
    verify_policy(*frozen)
    verify_repository_policy()
    assert frozen[0]["selection"]["selected_dataset_id"] is None
    assert frozen[0]["selection"]["selection_completion_status"] == "HOLD"


def test_independent_source_only_dossier_pass_is_not_dataset_selection() -> None:
    result = screen_synthetic_dossier(_synthetic())
    assert result["source_eligibility_pass"] is True
    assert result["candidate_selected"] is False
    assert result["independent_environment_replication_demonstrated"] is False
    assert result["stage10a_treatment_execution_authorized"] is False


@pytest.mark.parametrize("field", sorted(YES_FIELDS | NO_FIELDS))
def test_each_incompatible_source_fact_is_independently_rejected(field: str) -> None:
    dossier = _synthetic()
    dossier[field] = field in NO_FIELDS
    result = screen_synthetic_dossier(dossier)
    assert result["source_eligibility_pass"] is False
    assert field in result["failed_source_fields"]


def test_unfrozen_or_leaky_dossier_schema_rejected() -> None:
    d = _synthetic()
    d["post_mcc"] = 0.99
    with pytest.raises(ValueError, match="unauthorized outcome field"):
        screen_synthetic_dossier(d)
    d.pop("post_mcc")
    d["candidate_id"] = ""
    with pytest.raises(ValueError, match="identity"):
        screen_synthetic_dossier(d)
    d = _synthetic()
    d["independent_collection"] = 1
    with pytest.raises(ValueError, match="explicit boolean"):
        screen_synthetic_dossier(d)


def test_any_attempt_to_claim_dataset_selection_rejected(frozen) -> None:
    p, m, a = copy.deepcopy(frozen)
    p["selection"]["selected_dataset_id"] = "fixture"
    with pytest.raises(ValueError, match="must not assert dataset selection"):
        verify_policy(p, m, a)


def test_master_and_stage10a_gate_cannot_be_overridden(frozen) -> None:
    p, m, a = copy.deepcopy(frozen)
    m["hard_gate"]["stage10_execution_permitted"] = True
    with pytest.raises(ValueError, match="firewall"):
        verify_policy(p, m, a)
    m["hard_gate"]["stage10_execution_permitted"] = False
    a["stage10_treatment_execution_authorized"] = True
    with pytest.raises(ValueError, match="firewall"):
        verify_policy(p, m, a)


def test_prospective_safeguards_and_claim_boundaries_fail_closed(frozen) -> None:
    p, m, a = copy.deepcopy(frozen)
    p["causal_reporting"]["event_or_window_pseudoreplication_prohibited"] = False
    with pytest.raises(ValueError, match="safeguards"):
        verify_policy(p, m, a)
    p, m, a = copy.deepcopy(frozen)
    p["selection"]["independent_external_replication_claim_permitted"] = True
    with pytest.raises(ValueError, match="must not assert dataset selection"):
        verify_policy(p, m, a)
