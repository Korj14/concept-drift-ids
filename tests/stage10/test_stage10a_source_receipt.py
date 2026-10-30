"""Repository-only negative tests; no original CSV or treatment is loaded."""
from __future__ import annotations

import json

import pytest

from tools.stage10.stage10a_source_receipt import (
    _canonical_sha256,
    _require_exact_version,
    _source_report,
    _validate_git_identity,
    _write_once,
)


def _git() -> dict[str, str]:
    return {
        "head": "a" * 40,
        "branch": "stage10a-governance",
        "clean": "true",
    }


def _report() -> dict:
    return _source_report(
        git=_git(),
        source_sha256="b" * 64,
        row_hash="c" * 64,
        row_count=138_530,
        feature_count=77,
        python_version="3.11.9",
    )


def test_report_is_canonical_source_only_and_denies_treatment() -> None:
    report = _report()
    assert report["pass"] is True
    assert report["canonical_sha256"] == _canonical_sha256(
        {k: v for k, v in report.items() if k != "canonical_sha256"}
    )
    assert report["stage10_treatment_execution_authorized"] is False
    assert report["stage10_treatment_outcomes_accessed"] is False
    assert report["model_checkpoints_loaded"] is False
    assert report["neural_or_symbolic_treatments_executed"] is False
    assert "predictions" not in report
    assert "mcc" not in report


@pytest.mark.parametrize("python_version", ["3.11.8", "3.12.0", "3.13.5"])
def test_other_python_versions_block(python_version: str) -> None:
    with pytest.raises(RuntimeError, match="requires Python"):
        _require_exact_version(python_version)


@pytest.mark.parametrize(
    "head,branch,status,root",
    [
        ("x" * 40, "stage10a-governance", "", "/unused"),
        ("a" * 40, "main", "", "/unused"),
        ("a" * 40, "stage10a-governance", " M README.md", "/unused"),
    ],
)
def test_bad_git_identity_refused(
    head: str, branch: str, status: str, root: str
) -> None:
    with pytest.raises(RuntimeError):
        _validate_git_identity(head, branch, status, root)


def test_wrong_source_geometry_is_not_a_pass() -> None:
    for rows, features in ((138_529, 77), (138_530, 78)):
        with pytest.raises(ValueError, match="row/feature"):
            _source_report(
                git=_git(), source_sha256="b" * 64, row_hash="c" * 64,
                row_count=rows, feature_count=features,
                python_version="3.11.9",
            )


def test_noncanonical_python_cannot_mark_a_source_receipt_pass() -> None:
    with pytest.raises(RuntimeError, match="other Python"):
        _source_report(
            git=_git(), source_sha256="b" * 64, row_hash="c" * 64,
            row_count=138_530, feature_count=77,
            python_version="3.13.5",
        )


def test_write_once_preserves_original_report(tmp_path) -> None:
    path = tmp_path / "stage10a_source_receipt.json"
    _write_once(path, _report())
    expected = path.read_bytes()
    assert json.loads(expected)["stage10_treatment_execution_authorized"] is False
    with pytest.raises(FileExistsError):
        _write_once(path, _report())
    assert path.read_bytes() == expected


def test_unapproved_git_state_and_unpinned_sha_fail() -> None:
    with pytest.raises(RuntimeError, match="clean"):
        _source_report(
            git={"branch": "stage10a-governance", "clean": "false"},
            source_sha256="b"*64, row_hash="c"*64, row_count=138_530,
            feature_count=77, python_version="3.11.9",
        )
    with pytest.raises(ValueError, match="SHA-256"):
        _source_report(
            git=_git(), source_sha256="", row_hash="c"*64,
            row_count=138_530, feature_count=77, python_version="3.11.9",
        )
