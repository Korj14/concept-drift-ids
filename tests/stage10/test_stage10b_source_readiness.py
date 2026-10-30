from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np

import tools.stage10.stage10b_source_readiness as readiness


def test_frozen_stage10b_protocol_and_source_audit_identities() -> None:
    manifest = json.loads(readiness.MANIFEST_PATH.read_text(encoding="utf-8"))
    audit = json.loads(readiness.AUDIT_PATH.read_text(encoding="utf-8"))

    assert readiness._embedded_sha_ok(manifest)
    assert readiness._embedded_sha_ok(audit)
    assert (
        readiness._git_blob_sha1(readiness.PROTOCOL_PATH)
        == manifest["protocol_document"]["git_blob_sha1"]
    )
    assert (
        readiness._git_blob_sha1(readiness.AUDIT_PATH)
        == manifest["source_audit"]["git_blob_sha1"]
    )
    assert audit["canonical_sha256"] == manifest["source_audit"]["canonical_sha256"]
    assert manifest["stage10_treatment_execution_authorized"] is False
    assert manifest["stage9_5_hard_gate_required"] is True
    assert manifest["inherited_identities"]["seeds"] == [0, 1, 2, 3, 4]
    assert manifest["post_estimand"] == "full_69270_row_ramp_plus_plateau"


def test_hash_preimage_is_deterministic_for_two_slots() -> None:
    slot_ids = np.asarray([100, 101], dtype=np.int64)
    first = readiness._deterministic_replacement_mask(
        slot_ids, post_start=100, ramp_rows=1, salt="test-salt"
    )
    second = readiness._deterministic_replacement_mask(
        slot_ids, post_start=100, ramp_rows=1, salt="test-salt"
    )
    assert np.array_equal(first, second)
    assert first.dtype == bool
    assert first[1] is np.True_ or bool(first[1])


def test_ramp_end_is_complete_without_boundary_trigger() -> None:
    values = np.arange(200, 250, dtype=np.int64)
    mask = readiness._deterministic_replacement_mask(
        values, post_start=200, ramp_rows=20, salt="test-salt"
    )
    assert np.all(mask[20:])
    assert not np.any(np.isnan(mask.astype(np.float64)))


def test_selected_thursday_candidates_use_frozen_integer_floor_mapping() -> None:
    population = np.array([4, 6, 8, 10, 12, 14, 16, 18], dtype=np.int64)
    observed = readiness._selected_thursday_candidates(population, 4)
    assert observed.tolist() == [4, 8, 12, 16]


def test_source_only_success_report_does_not_unlock_treatment() -> None:
    report = readiness._report(
        [],
        {"available": True, "head": "a" * 40, "clean": True},
        {"Wednesday": {"sha256": "b" * 64}},
        {"replacement": {"replaced": 41_935}},
    )
    assert report["pass"] is True
    assert report["source_only_feature_ks_recomputed"] is False
    assert report["stage10_treatment_outcomes_accessed"] is False
    assert report["stage10_treatment_execution_authorized"] is False
    assert "before_stage9_5_closure" in report["prohibited_next_action"]


def test_failure_report_stays_blocked() -> None:
    report = readiness._report(["source_exact_byte_identity_mismatch"], {}, {}, None)
    assert report["pass"] is False
    assert report["status"] == "blocked"
    assert report["stage10_treatment_execution_authorized"] is False
    assert report["next_permitted_action"].startswith("correct_source_only_identity_failure")


def test_source_audit_and_manifest_reject_edits(tmp_path: Path) -> None:
    audit = json.loads(readiness.AUDIT_PATH.read_text(encoding="utf-8"))
    audit["replacement"]["replaced"] += 1
    assert readiness._embedded_sha_ok(audit) is False

    manifest = json.loads(readiness.MANIFEST_PATH.read_text(encoding="utf-8"))
    manifest["stage10_treatment_execution_authorized"] = True
    assert readiness._embedded_sha_ok(manifest) is False


def test_frozen_source_audit_window_progression() -> None:
    audit = json.loads(readiness.AUDIT_PATH.read_text(encoding="utf-8"))
    slots = audit["window_benign_slots"]
    reps = audit["window_replacements"]
    ratios = [r / s for r, s in zip(reps, slots)]
    assert len(slots) == len(reps) == 14
    assert all(a < b for a, b in zip(ratios[:10], ratios[1:10]))
    assert all(r == 1.0 for r in ratios[10:])
    assert sum(reps) == 41_935
    assert sum(slots) == 65_697


def test_git_blob_binding_is_windows_crlf_portable(tmp_path: Path) -> None:
    manifest = json.loads(readiness.MANIFEST_PATH.read_text(encoding="utf-8"))
    for path, expected in (
        (
            readiness.PROTOCOL_PATH,
            manifest["protocol_document"]["git_blob_sha1"],
        ),
        (
            readiness.AUDIT_PATH,
            manifest["source_audit"]["git_blob_sha1"],
        ),
    ):
        canonical = path.read_bytes().replace(bytes((13, 10)), bytes((10,)))
        probe = tmp_path / path.name
        probe.write_bytes(canonical.replace(bytes((10,)), bytes((13, 10))))
        assert readiness._git_blob_sha1(probe) == expected
