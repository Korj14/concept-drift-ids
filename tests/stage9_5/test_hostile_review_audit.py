from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.stage9_5 import hostile_review_audit as audit
from tools.stage9_5.hostile_review_audit import (
    CONTRACT_PATH,
    STAGE10_PATH,
    _assert_append_only_register,
    run,
)


def test_hostile_review_contract_covers_a_through_t() -> None:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    attacks = contract["reviewer_attacks"]
    assert [item["id"] for item in attacks] == [
        chr(code) for code in range(ord("A"), ord("T") + 1)
    ]
    assert sum(item["classification"] == "Class B" for item in attacks) == 6
    assert sum(item["classification"] == "Class C" for item in attacks) == 14
    assert all(str(item["disposition"]).strip() for item in attacks)


def test_stage10_master_protocol_remains_hard_gated() -> None:
    contract = json.loads(STAGE10_PATH.read_text(encoding="utf-8"))
    assert contract["hard_gate"]["stage10_execution_permitted"] is False
    assert contract["stage10_treatment_outcomes_accessed"] is False
    assert len(contract["master_obligations"]) >= 15


def test_hostile_review_audit_uses_verified_post_recovery_state(
    tmp_path: Path,
) -> None:
    report = run(tmp_path)
    assert report["audit_execution_pass"] is True
    assert report["stage9_5_1_6_verified"] is True
    assert report["stage9_5_closure_eligible"] is True
    assert report["status"] == "closed"
    assert report["unresolved_class_a_count"] == 0
    assert report["historical_unresolved_class_a_count"] == 1
    assert report["historical_unresolved_class_a"][0]["id"] == "A-PROV-01"
    assert report["formal_stage9_5_closure_established"] is False
    assert report["exact_head_ci_chain_requires_independent_verification"] is True
    assert report["reviewer_attacks"]["class_b_all_dispositioned"] is True
    assert report["reviewer_attacks"]["class_c_all_dispositioned"] is True
    assert report["failure_artifact_parse_errors"] == []


def test_hostile_review_gate_failure_reinstates_blocker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        audit, "evaluate_order_gate",
        lambda: {"later_packages_unlocked": False, "failures": ["tampered_recovery"]},
    )
    report = run(tmp_path)
    assert report["audit_execution_pass"] is True
    assert report["stage9_5_closure_eligible"] is False
    assert report["status"] == "open_blocked"
    assert report["unresolved_class_a_count"] == 1
    assert report["historical_unresolved_class_a_count"] == 1
    assert report["formal_stage9_5_closure_established"] is False


@pytest.mark.parametrize(
    ("old", "snapshot", "head"),
    [
        (b"fixed", b"changed", b"changed"),
        (b"fixed", b"fixed plus notes", b"fixed"),
        (b"fixed", b"fixed plus notes", b"fixed rewritten"),
        (b"", b"snapshot", b"snapshot"),
        (b"fixed", b"", b"fixed"),
    ],
)
def test_hostile_review_register_rejects_history_erasure(
    old: bytes, snapshot: bytes, head: bytes
) -> None:
    with pytest.raises(ValueError):
        _assert_append_only_register(old, snapshot, head)


def test_hostile_review_register_allows_append_only_history() -> None:
    _assert_append_only_register(b"frozen", b"frozen\nlater", b"frozen\nlater\nnew")


def test_hostile_review_rejects_unrecognized_reconciliation_policy(
    monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(audit, "_load_json", lambda path: {} if path == audit.POST_RECOVERY_PATH else json.loads(path.read_text(encoding="utf-8")))
    with pytest.raises(ValueError, match="Unrecognized"):
        audit._current_source_identities(json.loads(CONTRACT_PATH.read_text(encoding="utf-8")))
