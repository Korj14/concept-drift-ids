from __future__ import annotations

import json
from pathlib import Path

from tools.stage9_5.claim_traceability import (
    PROJECT_ROOT,
    _contains_numeric_literal,
    _pointer,
    run,
)


def test_json_pointer_supports_mapping_and_list() -> None:
    payload = {"a": {"b": [{"c": 7}]}}
    assert _pointer(payload, "/a/b/0/c") == 7


def test_claim_definitions_have_no_numeric_evidence_literals() -> None:
    definitions = json.loads(
        (PROJECT_ROOT / "data/manifests/stage9_5_claim_definitions_v1.json").read_text(
            encoding="utf-8"
        )
    )
    for claim in definitions["claims"]:
        assert not _contains_numeric_literal(claim["values"]), claim["claim_id"]


def test_all_frozen_claim_families_are_defined() -> None:
    contract = json.loads(
        (PROJECT_ROOT / "data/manifests/stage9_5_claim_reporting_v1.json").read_text(
            encoding="utf-8"
        )
    )
    definitions = json.loads(
        (PROJECT_ROOT / "data/manifests/stage9_5_claim_definitions_v1.json").read_text(
            encoding="utf-8"
        )
    )
    assert {item["family"] for item in definitions["claims"]} == set(
        contract["claim_families"]
    )


def test_claim_traceability_integration(tmp_path: Path) -> None:
    report = run(tmp_path)
    assert report["pass"] is True
    assert report["missing_families"] == []
    assert report["extra_families"] == []
    assert report["orphan_current_claims"] == []
    assert report["hand_entered_numeric_evidence_literals"] == 0
    assert report["claim_count"] >= report["frozen_family_count"]
    assert all(item["resolved_values"] for item in report["claims"])
