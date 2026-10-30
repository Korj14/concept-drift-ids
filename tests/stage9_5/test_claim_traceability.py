from __future__ import annotations

import json
import subprocess

import pytest
from pathlib import Path

from tools.stage9_5.claim_traceability import (
    PROJECT_ROOT,
    _assert_append_only_ledger,
    _validate_claim_source_identities,
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


def test_ledger_append_only_extension_is_accepted() -> None:
    _assert_append_only_ledger(
        b"frozen claim text\\n",
        b"frozen claim text\\naccepted later notes\\n",
        b"frozen claim text\\naccepted later notes\\nnew future notes\\n",
    )


@pytest.mark.parametrize(
    ("frozen", "snapshot", "current"),
    [
        (b"original\\n", b"changed\\n", b"changed\\n"),
        (b"original\\n", b"original\\nrecord\\n", b"original\\n"),
        (b"original\\n", b"original\\nrecord\\n", b"original\\naltered\\n"),
        (b"", b"snapshot", b"snapshot"),
        (b"original\\n", b"", b"original\\n"),
    ],
)
def test_ledger_append_only_rejects_erasure_or_rewriting(
    frozen: bytes, snapshot: bytes, current: bytes
) -> None:
    with pytest.raises(ValueError):
        _assert_append_only_ledger(frozen, snapshot, current)


def test_live_four_claim_source_identities_are_frozen() -> None:
    contract = json.loads(
        (PROJECT_ROOT / "data/manifests/stage9_5_claim_reporting_v1.json").read_text(
            encoding="utf-8"
        )
    )
    frozen = _validate_claim_source_identities(contract)
    assert len(frozen) == 4
    assert frozen["METHODOLOGY_LEDGER.md"] == (
        "9b977705b9748138bb12745e9f0fb3d77d73c2b2"
    )


def test_claim_freeze_rejects_local_uncommitted_document_tampering(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from tools.stage9_5 import claim_traceability as verifier

    contract = json.loads(
        (PROJECT_ROOT / "data/manifests/stage9_5_claim_reporting_v1.json").read_text(
            encoding="utf-8"
        )
    )
    original_git = verifier._git_bytes

    def reject_dirty_source(*args: str) -> bytes:
        if args[:2] == ("diff", "--quiet"):
            raise subprocess.CalledProcessError(returncode=1, cmd=["git", *args])
        return original_git(*args)

    monkeypatch.setattr(verifier, "_git_bytes", reject_dirty_source)
    with pytest.raises(ValueError, match="inputs differ from the checked HEAD"):
        _validate_claim_source_identities(contract)
