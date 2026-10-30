from __future__ import annotations

import json
import subprocess
from copy import deepcopy
from pathlib import Path

import pytest

from tools.stage9_5 import hostile_review_audit as audit
from tools.stage9_5.hostile_review_audit import (
    CONTRACT_PATH,
    STAGE10_MASTER_V1_1_PATH,
    STAGE10_PATH,
    _assert_append_only_register,
    _verify_stage10_master_binding,
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
    assert report["stage10_master_v1_1_verified"] is True
    assert report["stage10_master_binding_v1_3"]["pass"] is True
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


def _frozen_stage10_master_inputs() -> tuple[dict, dict]:
    old = json.loads(STAGE10_PATH.read_text(encoding="utf-8"))
    new = json.loads(STAGE10_MASTER_V1_1_PATH.read_text(encoding="utf-8"))
    return old, new


def test_v1_1_stage10_master_is_explicitly_verified() -> None:
    old, new = _frozen_stage10_master_inputs()
    report = _verify_stage10_master_binding(old, new)
    assert report["historical_v1_verified"] is True
    assert report["governing_v1_1_verified"] is True
    assert report["governing_v1_1_obligation_count"] == 16
    assert report["stage10_execution_released"] is False


@pytest.mark.parametrize("defect", [
    "released", "outcomes", "missing_obligation", "duplicate_obligation",
    "wrong_master", "no_historical_preservation", "short_freeze", "wrong_hostile_rule",
])
def test_v1_1_tampering_fails_closed(defect: str) -> None:
    old, current = _frozen_stage10_master_inputs()
    current = deepcopy(current)
    if defect == "released":
        current["hard_gate"]["stage10_execution_permitted"] = True
    elif defect == "outcomes":
        current["stage10_treatment_outcomes_accessed"] = True
    elif defect == "missing_obligation":
        current["master_obligations"].pop()
    elif defect == "duplicate_obligation":
        current["master_obligations"][1]["id"] = "S10-01"
    elif defect == "wrong_master":
        current["protocol_id"] = "stage10-plus-master-replication-sensitivity-v1"
    elif defect == "no_historical_preservation":
        current["historical_v1_preserved"] = False
    elif defect == "short_freeze":
        current["stage_specific_pre_outcome_freeze_required"].pop()
    elif defect == "wrong_hostile_rule":
        current["future_hostile_review_requirement"] = "v1 only"
    assert _verify_stage10_master_binding(old, current)["pass"] is False


def test_v1_stage10_master_tampering_fails_closed() -> None:
    old, current = _frozen_stage10_master_inputs()
    old = deepcopy(old)
    old["hard_gate"]["stage10_execution_permitted"] = True
    result = _verify_stage10_master_binding(old, current)
    assert result["historical_v1_verified"] is False
    assert result["pass"] is False


def test_v1_1_stage10_master_wrong_git_blob_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    old, current = _frozen_stage10_master_inputs()
    original = audit._tree_sha

    def wrong_sha(commit: str, path: str) -> str:
        if commit == "HEAD" and path == (
            "data/manifests/stage10_plus_master_replication_sensitivity_v1_1.json"
        ):
            return "0" * 40
        return original(commit, path)

    monkeypatch.setattr(audit, "_tree_sha", wrong_sha)
    with pytest.raises(ValueError, match="Git identity changed"):
        _verify_stage10_master_binding(old, current)


def test_v1_1_stage10_master_dirty_input_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    old, current = _frozen_stage10_master_inputs()
    original = audit._git_bytes

    def dirty(*args: str) -> bytes:
        if args[:3] == ("diff", "--quiet", "HEAD"):
            raise subprocess.CalledProcessError(1, ["git", *args])
        return original(*args)

    monkeypatch.setattr(audit, "_git_bytes", dirty)
    with pytest.raises(ValueError, match="working-tree inputs changed"):
        _verify_stage10_master_binding(old, current)


def test_v1_1_stage10_master_unrecognized_policy_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    old, current = _frozen_stage10_master_inputs()
    original = audit._load_json

    def altered(path: Path) -> dict:
        if path == audit.STAGE10_MASTER_BINDING_PATH:
            return {"status": "manual_override"}
        return original(path)

    monkeypatch.setattr(audit, "_load_json", altered)
    with pytest.raises(ValueError, match="Unrecognized"):
        _verify_stage10_master_binding(old, current)


def test_v1_1_stage10_failure_blocks_hostile_audit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    old_load = audit._load_json

    def released(path: Path) -> dict:
        payload = old_load(path)
        if path == STAGE10_MASTER_V1_1_PATH:
            payload = deepcopy(payload)
            payload["hard_gate"]["stage10_execution_permitted"] = True
        return payload

    monkeypatch.setattr(audit, "_load_json", released)
    with pytest.raises(SystemExit, match="hostile-review audit execution failed"):
        run(tmp_path)
    report = json.loads((tmp_path / "hostile_review_report.json").read_text(encoding="utf-8"))
    assert report["audit_execution_pass"] is False
    assert report["stage9_5_closure_eligible"] is False
    assert report["stage10_master_v1_1_verified"] is False
    assert report["formal_stage9_5_closure_established"] is False
