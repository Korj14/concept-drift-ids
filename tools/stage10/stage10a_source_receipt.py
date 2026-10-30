"""Fail-closed Stage-10A original-source receipt only: never runs a treatment.

Requires the exact frozen Python 3.11.9 runtime, a clean stage10a-governance
checkout, original Wednesday CSV, and frozen training-only preprocessing.
Writes one canonical, non-outcome JSON report with exclusive creation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
from pathlib import Path
from typing import Any

from concept_drift_ids.stage10a_source_adapter import load_stage10a_source_only

PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXPECTED_PYTHON = "3.11.9"
EXPECTED_BRANCH = "stage10a-governance"
SOURCE_ONLY_ID = "stage10a-original-source-receipt-v1"


def _canonical_sha256(document: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(
            document,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _require_exact_version(actual: str) -> None:
    if actual != EXPECTED_PYTHON:
        raise RuntimeError(
            f"Source receipt requires Python {EXPECTED_PYTHON}; found {actual}."
        )


def _git_output(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _validate_git_identity(
    head: str, branch: str, status: str, root: str
) -> dict[str, str]:
    if (len(head) != 40 or any(c not in "0123456789abcdef" for c in head)):
        raise RuntimeError("Git HEAD is not a 40-character Git SHA.")
    if branch != EXPECTED_BRANCH:
        raise RuntimeError("Wrong Stage-10A execution-governance branch.")
    if status:
        raise RuntimeError("Git checkout is dirty. Refusing source receipt.")
    if Path(root).resolve() != PROJECT_ROOT.resolve():
        raise RuntimeError("Git root does not match the source-receipt module.")
    return {"head": head, "branch": branch, "clean": "true"}


def _source_report(
    *,
    git: dict[str, str],
    source_sha256: str,
    row_hash: str,
    row_count: int,
    feature_count: int,
    python_version: str,
) -> dict[str, Any]:
    if (not source_sha256 or len(source_sha256) != 64
        or not row_hash or len(row_hash) != 64):
        raise ValueError("Source identity must be pinned by SHA-256.")
    if row_count != 138_530 or feature_count != 77:
        raise ValueError("Source-only report violates the frozen row/feature count.")
    if python_version != EXPECTED_PYTHON:
        raise RuntimeError("Cannot mark other Python versions accepted.")
    if git.get("branch") != EXPECTED_BRANCH or git.get("clean") != "true":
        raise RuntimeError("Source-only receipt requires a clean Stage-10A branch.")
    document: dict[str, Any] = {
        "audit_id": SOURCE_ONLY_ID,
        "stage": "10A",
        "scope": "source_only_original_csv_and_frozen_preprocessing",
        "pass": True,
        "git": git,
        "python_version": python_version,
        "scenario_id": "cicids2017_goldeneye_temporal_attack_shift_v1",
        "raw_source_sha256": source_sha256,
        "ordered_row_ids_sha256": row_hash,
        "logical_rows": row_count,
        "frozen_features": feature_count,
        "label_latency_rows": 5000,
        "boundary_role": "offline_evaluator_only_not_exposed_to_observations",
        "stage10_treatment_execution_authorized": False,
        "stage10_treatment_outcomes_accessed": False,
        "model_checkpoints_loaded": False,
        "neural_or_symbolic_treatments_executed": False,
        "next_action": "hold_and_verify_matched_c_d_executor_before_separate_release",
    }
    document["canonical_sha256"] = _canonical_sha256(document)
    return document


def _write_once(path: Path, report: dict[str, Any]) -> None:
    """Never replace an earlier attempt, even a failed/partial one."""
    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(
        report, indent=2, sort_keys=True, allow_nan=False
    ) + "\n"
    with path.open("x", encoding="utf-8", newline="\n") as file:
        file.write(content)
        file.flush()
        os.fsync(file.fileno())


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Stage-10A original-source-only receipt (NO treatments)"
    )
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    _require_exact_version(platform.python_version())
    git = _validate_git_identity(
        head=_git_output("rev-parse", "HEAD"),
        branch=_git_output("branch", "--show-current"),
        status=_git_output("status", "--porcelain"),
        root=_git_output("rev-parse", "--show-toplevel"),
    )
    # No adaptive neural model, classifier, detector, or symbolic executor is used.
    package = load_stage10a_source_only(args.data_root)
    if package.receipt.treatment_execution_authorized:
        raise RuntimeError("Source adapter attempted to authorize treatment.")
    report = _source_report(
        git=git,
        source_sha256=package.receipt.source_sha256,
        row_hash=package.receipt.ordered_row_ids_sha256,
        row_count=len(package.observations),
        feature_count=77,
        python_version=platform.python_version(),
    )
    _write_once(args.output, report)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
