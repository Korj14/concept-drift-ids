from __future__ import annotations

import json
from pathlib import Path

from tools.stage9_5.hostile_review_audit import (
    CONTRACT_PATH,
    STAGE10_PATH,
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


def test_hostile_review_audit_passes_execution_but_remains_blocked(
    tmp_path: Path,
) -> None:
    report = run(tmp_path)
    assert report["audit_execution_pass"] is True
    assert report["stage9_5_closure_eligible"] is False
    assert report["status"] == "open_blocked"
    assert report["unresolved_class_a_count"] == 1
    assert report["reviewer_attacks"]["class_b_all_dispositioned"] is True
    assert report["reviewer_attacks"]["class_c_all_dispositioned"] is True
    assert report["failure_artifact_parse_errors"] == []
