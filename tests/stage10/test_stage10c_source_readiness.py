from __future__ import annotations

import json
from pathlib import Path

import numpy as np

import tools.stage10.stage10c_source_readiness as readiness


def test_stage10c_frozen_artifact_self_hash_and_blob_links() -> None:
    manifest = json.loads(readiness.MANIFEST_PATH.read_text(encoding="utf-8"))
    audit = json.loads(readiness.AUDIT_PATH.read_text(encoding="utf-8"))
    assert readiness._embedded_sha_ok(manifest)
    assert readiness._embedded_sha_ok(audit)
    assert readiness._git_blob_sha1(readiness.PROTOCOL_PATH) == (
        manifest["protocol_document"]["git_blob_sha1"]
    )
    assert readiness._git_blob_sha1(readiness.AUDIT_PATH) == (
        manifest["source_audit"]["git_blob_sha1"]
    )
    assert audit["canonical_sha256"] == manifest["source_audit"]["canonical_sha256"]
    assert manifest["inherited_identities"] == readiness.EXPECTED_INIT
    assert manifest["stage9_5_hard_gate_required"] is True
    assert manifest["stage10_treatment_execution_authorized"] is False


def test_attack_slots_are_deterministic_spread_no_collisions() -> None:
    pre = readiness._attack_slots(69260, 1966)
    post = readiness._attack_slots(69270, 1966)
    assert len(pre) == len(post) == 1966
    assert np.all(np.diff(pre) > 0)
    assert np.all(np.diff(post) > 0)
    assert pre[0] >= 0 and pre[-1] < 69260
    assert post[0] >= 0 and post[-1] < 69270
    assert np.array_equal(pre, readiness._attack_slots(69260, 1966))


def test_even_selection_without_replacement_and_sample_limits() -> None:
    pool = np.arange(100, 124, dtype=np.int64)
    sampled = readiness._evenly_select(pool, 10)
    assert len(sampled) == len(set(sampled)) == 10
    assert sampled.tolist() == [100, 102, 104, 107, 109, 112, 114, 116, 119, 121]


def test_synthetic_source_assembly_retains_exact_order() -> None:
    benign = np.asarray([10, 11, 12, 13, 14, 15], dtype=np.int64)
    attacks = np.asarray([99, 100], dtype=np.int64)
    pre = readiness._assemble(benign, attacks, 2, 8)
    assert len(pre["source_row_ids"]) == 8
    assert pre["source_order"][pre["attack_slots"]].tolist() == [2, 2]
    assert pre["source_row_ids"][pre["attack_slots"]].tolist() == [99, 100]
    assert pre["source_row_ids"][pre["source_order"] == 5].tolist() == benign.tolist()


def test_frozen_attack_window_tallies_are_consistent() -> None:
    audit = json.loads(readiness.AUDIT_PATH.read_text(encoding="utf-8"))
    for regime in ("pre", "post"):
        observed = audit["attack_windows"][regime]
        assert len(observed) == 14
        assert sum(observed) == 1966
        assert observed[-1] == 121
        assert all(141 <= n <= 142 for n in observed[:-1])


def test_success_report_never_unlocks_treatment() -> None:
    report = readiness._report(
        [],
        {"available": True, "clean": True, "branch": "stage10c-preoutcome-protocol"},
        {},
        {"attack_per_regime": 1966},
        {"benign_pre_vs_post": {"mean": 0.002}},
    )
    assert report["pass"] is True
    assert report["source_only_feature_ks_recomputed"] is True
    assert report["stage10_treatment_outcomes_accessed"] is False
    assert report["stage10_treatment_execution_authorized"] is False
    assert "before_stage9_5_closure" in report["prohibited_next_action"]


def test_failed_report_stops_and_preserves_failure() -> None:
    report = readiness._report(["mismatched_raw_source"], {}, {}, None, None)
    assert report["pass"] is False
    assert report["status"] == "blocked"
    assert report["next_permitted_action"] == "stop_and_version_correct_source_only_failure"
    assert report["stage10_treatment_execution_authorized"] is False


def test_artifact_edits_break_freeze_identity() -> None:
    a = json.loads(readiness.AUDIT_PATH.read_text(encoding="utf-8"))
    a["source_selection"]["attack_count_each_regime"] = 1965
    assert not readiness._embedded_sha_ok(a)
    m = json.loads(readiness.MANIFEST_PATH.read_text(encoding="utf-8"))
    m["stage10_treatment_execution_authorized"] = True
    assert not readiness._embedded_sha_ok(m)


def test_portable_git_blob_transport_but_tamper_rejected(tmp_path: Path) -> None:
    manifest = json.loads(readiness.MANIFEST_PATH.read_text(encoding="utf-8"))
    for artifact, expected in (
        (readiness.PROTOCOL_PATH, manifest["protocol_document"]["git_blob_sha1"]),
        (readiness.AUDIT_PATH, manifest["source_audit"]["git_blob_sha1"]),
    ):
        lf = artifact.read_bytes().replace(bytes((13, 10)), bytes((10,)))
        out = tmp_path / artifact.name
        out.write_bytes(lf.replace(bytes((10,)), bytes((13, 10))))
        assert readiness._git_blob_sha1(out) == expected
        out.write_bytes(lf + b"tampered")
        assert readiness._git_blob_sha1(out) != expected


def test_source_only_ks_known_synthetic_separation() -> None:
    import pandas as pd

    one = pd.DataFrame({"x": [0, 0, 1, 1], "y": [1, 1, 1, 1]})
    two = pd.DataFrame({"x": [5, 5, 6, 6], "y": [1, 1, 1, 1]})
    stats = readiness._ks_summary(one, two, ["x", "y"])
    assert stats["max"] == 1.0
    assert stats["ge_0_1"] == 1
    assert stats["ge_0_2"] == 1


def test_stage10c_requires_exact_unseen_family_raw_source_counts() -> None:
    import pytest

    w = np.repeat("BENIGN", 692703).astype(object)
    f = np.repeat("BENIGN", 191033).astype(object)
    with pytest.raises(ValueError, match="GoldenEye"):
        readiness._build_selection(w, f)
