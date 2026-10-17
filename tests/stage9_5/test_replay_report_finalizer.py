from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from tools.stage9_5.replay_report_finalizer import (
    CONTRACT_PATH,
    _canonical_sha256,
    run,
)


def _head() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _set_path(payload: dict[str, Any], dotted: str, value: Any) -> None:
    parts = dotted.split(".")
    node = payload
    for part in parts[:-1]:
        child = node.get(part)
        if not isinstance(child, dict):
            child = {}
            node[part] = child
        node = child
    node[parts[-1]] = value


def _seal(payload: dict[str, Any]) -> dict[str, Any]:
    payload.pop("canonical_sha256", None)
    payload["canonical_sha256"] = _canonical_sha256(payload)
    return payload


def _comparison_evidence() -> dict[str, Any]:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    expected = contract["comparison_evidence_contract"]
    assert isinstance(expected, dict)
    payload: dict[str, Any] = {"audited_head": _head()}
    for dotted, value in expected.items():
        _set_path(payload, dotted, value)
    payload["stage1_reconstruction_report_canonical_sha256"] = "b" * 64
    return _seal(payload)


def _write_evidence(tmp_path: Path, payload: dict[str, Any]) -> Path:
    path = tmp_path / "comparison_evidence.json"
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path


def test_valid_comparison_evidence_finalizes_canonical_success(
    tmp_path: Path,
) -> None:
    evidence = _comparison_evidence()
    path = _write_evidence(tmp_path, evidence)

    report = run(path, tmp_path / "out")

    assert report["pass"] is True
    assert report["status"] == "pass"
    assert report["failures"] == []
    assert report["blockers"] == []
    construction = report["construction"]
    assert construction["contract_id"] == "stage9.5-6-replay-report-construction-v1"
    assert construction["producer_id"] == "stage9.5-6-replay-equivalence-assurance-v1"
    assert construction["comparator_id"] == "stage9.5-6-replay-equivalence-comparator-v1"
    assert construction["finalizer_id"] == "stage9.5-6-replay-report-finalizer-v1"
    assert construction["manual_success_report_permitted"] is False
    assert construction["deterministic_comparison_complete"] is True
    assert construction["source_evidence_complete"] is True
    assert construction["mismatch_count"] == 0
    assert (
        construction["comparison_evidence_canonical_sha256"]
        == evidence["canonical_sha256"]
    )
    assert (
        construction["stage1_reconstruction_report_canonical_sha256"]
        == "b" * 64
    )
    core = dict(report)
    observed = core.pop("canonical_sha256")
    assert observed == _canonical_sha256(core)


def test_manual_override_comparison_evidence_is_blocked(tmp_path: Path) -> None:
    evidence = _comparison_evidence()
    evidence["manual_override_used"] = True
    _seal(evidence)
    path = _write_evidence(tmp_path, evidence)

    report = run(path, tmp_path / "out")

    assert report["pass"] is False
    assert "comparison_evidence_value_mismatch:manual_override_used" in report["failures"]
    assert report["construction"]["deterministic_comparison_complete"] is False


def test_nonzero_comparison_mismatch_is_blocked(tmp_path: Path) -> None:
    evidence = _comparison_evidence()
    evidence["mismatch_count"] = 1
    evidence["mismatches"] = [{"name": "phase_b.seed0.d_drift"}]
    _seal(evidence)
    path = _write_evidence(tmp_path, evidence)

    report = run(path, tmp_path / "out")

    assert report["pass"] is False
    assert "comparison_evidence_value_mismatch:mismatch_count" in report["failures"]
    assert "comparison_evidence_value_mismatch:mismatches" in report["failures"]
    assert report["construction"]["mismatch_count"] == 1


def test_incomplete_phase_a_seed_set_is_blocked(tmp_path: Path) -> None:
    evidence = _comparison_evidence()
    phase_a = evidence["phase_a"]
    assert isinstance(phase_a, dict)
    phase_a["complete_seeds"] = [0, 1, 2, 3]
    _seal(evidence)
    path = _write_evidence(tmp_path, evidence)

    report = run(path, tmp_path / "out")

    assert report["pass"] is False
    assert (
        "comparison_evidence_value_mismatch:phase_a.complete_seeds"
        in report["failures"]
    )

def test_stale_comparison_evidence_canonical_hash_is_blocked(
    tmp_path: Path,
) -> None:
    evidence = _comparison_evidence()
    evidence["manual_override_used"] = True
    path = _write_evidence(tmp_path, evidence)

    report = run(path, tmp_path / "out")

    assert report["pass"] is False
    assert (
        "comparison_evidence_canonical_sha256_mismatch"
        in report["failures"]
    )

