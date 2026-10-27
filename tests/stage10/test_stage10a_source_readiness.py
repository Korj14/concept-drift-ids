from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np

import tools.stage10.stage10a_source_readiness as readiness


def test_frozen_stage10a_artifacts_self_verify() -> None:
    manifest = json.loads(readiness.MANIFEST_PATH.read_text(encoding="utf-8"))
    source_audit = json.loads(readiness.SOURCE_AUDIT_PATH.read_text(encoding="utf-8"))

    assert readiness._embedded_hash_ok(manifest) is True
    assert readiness._embedded_hash_ok(source_audit) is True
    assert (
        readiness._git_blob_sha1(readiness.PROTOCOL_PATH)
        == manifest["protocol_document"]["git_blob_sha1"]
    )
    assert (
        readiness._git_blob_sha1(readiness.SOURCE_AUDIT_PATH)
        == manifest["source_audit"]["git_blob_sha1"]
    )
    assert (
        source_audit["canonical_sha256"]
        == manifest["source_audit"]["canonical_sha256"]
    )


def test_final_report_never_authorizes_treatment() -> None:
    report = readiness._final_report(
        [],
        {
            "available": True,
            "head": "a" * 40,
            "branch": "stage10a-preoutcome-protocol",
            "clean": True,
            "status": "",
        },
        {"sha256": readiness.EXPECTED_SOURCE_SHA256},
        {"boundary_index": readiness.BOUNDARY_INDEX},
    )

    assert report["pass"] is True
    assert report["stage10_treatment_outcomes_accessed"] is False
    assert report["stage10_treatment_execution_authorized"] is False
    assert "before_stage9_5_closure" in report["prohibited_next_action"]


def test_row_hash_encoding_is_little_endian_int64() -> None:
    values = np.asarray([0, 1, 2, 2**40], dtype="<i8")
    expected = hashlib.sha256(values.tobytes()).hexdigest()
    assert readiness._sha256_int64_array(values) == expected


def test_failure_report_stays_fail_closed() -> None:
    report = readiness._final_report(
        ["synthetic_identity_failure"],
        {
            "available": True,
            "head": "b" * 40,
            "branch": "stage10a-preoutcome-protocol",
            "clean": True,
            "status": "",
        },
        None,
        None,
    )

    assert report["pass"] is False
    assert report["status"] == "blocked"
    assert report["stage10_treatment_execution_authorized"] is False
    assert report["next_permitted_action"] == (
        "correct_preoutcome_source_or_identity_failure_only"
    )


def test_git_blob_header_uses_actual_nul_separator(tmp_path: Path) -> None:
    probe = tmp_path / "probe.txt"
    content = bytes((97, 98, 99, 10))
    probe.write_bytes(content)
    expected = hashlib.sha1(b"blob 4" + bytes((0,)) + content).hexdigest()
    assert readiness._git_blob_sha1(probe) == expected


def test_frozen_artifact_hashes_allow_crlf_but_reject_content_edits(
    tmp_path: Path,
) -> None:
    manifest = json.loads(readiness.MANIFEST_PATH.read_text(encoding="utf-8"))
    for file_path, expected in (
        (
            readiness.PROTOCOL_PATH,
            manifest["protocol_document"]["git_blob_sha1"],
        ),
        (
            readiness.SOURCE_AUDIT_PATH,
            manifest["source_audit"]["git_blob_sha1"],
        ),
    ):
        canonical = file_path.read_bytes().replace(bytes((13, 10)), bytes((10,)))
        probe = tmp_path / file_path.name
        probe.write_bytes(canonical.replace(bytes((10,)), bytes((13, 10))))
        assert readiness._git_blob_sha1(probe) == expected

        tampered = canonical[:-1] + (b"X" if canonical[-1:] != b"X" else b"Y")
        probe.write_bytes(tampered)
        assert readiness._git_blob_sha1(probe) != expected
