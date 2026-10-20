from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

from tools.stage9_5.regenerated_correction_config_verifier import (
    verify_regenerated_correction_config,
)
from tools.stage9_5.replay_equivalence_comparator import (
    PHASE_C_CORRECTED_SUBDIR,
    _verify_accepted_stage8_archive_root,
    _verify_stage9_5_1_recovery_report,
    compare_phase_a,
    compare_phase_b,
    compare_phase_c_preconditions,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
AUDIT_ID = "stage9.5-6-phase-c-pre-rerun-verification-v1"
SEEDS = [0, 1, 2, 3, 4]
ARMS = ["c_frozen_symbolic", "d_drift", "d_periodic"]
CORRECTION_SOURCE_HEAD = "79ddc4c6d6dea52c7cabc55a6d082448fc24fcf9"
CORRECTION_CONFIG_RELATIVE_PATH = Path(
    "data/manifests/cd_primary_run_config_v1_1.json"
)


def _canonical_sha256(payload: object) -> str:
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _git_head() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _git(
    repo_root: Path,
    *args: str,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo_root,
        check=check,
        capture_output=True,
        text=True,
    )


def _verify_correction_worktree_provenance(
    correction_worktree_root: Path,
    regenerated_config_path: Path,
) -> dict[str, Any]:
    failures: list[str] = []
    root = correction_worktree_root.resolve()
    config = regenerated_config_path.resolve()
    expected_config = (root / CORRECTION_CONFIG_RELATIVE_PATH).resolve()

    if config != expected_config:
        failures.append("regenerated_config_not_at_frozen_relative_path")

    try:
        head = _git(root, "rev-parse", "HEAD").stdout.strip()
        parent = _git(root, "rev-parse", "HEAD^").stdout.strip()
        changed = [
            line.strip()
            for line in _git(
                root,
                "diff-tree",
                "--no-commit-id",
                "--name-only",
                "-r",
                "HEAD",
            ).stdout.splitlines()
            if line.strip()
        ]
        tracked_status = _git(
            root,
            "status",
            "--porcelain",
            "--untracked-files=no",
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        return {
            "pass": False,
            "failures": [f"correction_worktree_git_error:{type(exc).__name__}"],
            "head": None,
            "parent": None,
            "changed_paths": [],
            "tracked_worktree_clean": False,
        }

    if parent != CORRECTION_SOURCE_HEAD:
        failures.append("correction_freeze_parent_not_frozen_source")
    if changed != [CORRECTION_CONFIG_RELATIVE_PATH.as_posix()]:
        failures.append("correction_freeze_commit_not_config_only")
    if tracked_status:
        failures.append("correction_worktree_has_tracked_changes")

    return {
        "pass": not failures,
        "failures": failures,
        "head": head,
        "parent": parent,
        "changed_paths": changed,
        "tracked_worktree_clean": not tracked_status,
        "expected_parent": CORRECTION_SOURCE_HEAD,
        "expected_only_changed_path": CORRECTION_CONFIG_RELATIVE_PATH.as_posix(),
    }


def _phase_b_shape_passed(phase_b: dict[str, Any]) -> bool:
    if phase_b.get("pass") is not True:
        return False
    results = phase_b.get("seed_results")
    if not isinstance(results, list) or len(results) != len(SEEDS):
        return False
    by_seed: dict[int, dict[str, Any]] = {}
    for item in results:
        if not isinstance(item, dict):
            return False
        seed = item.get("seed")
        if not isinstance(seed, int) or isinstance(seed, bool):
            return False
        by_seed[seed] = item
    if sorted(by_seed) != SEEDS:
        return False
    for seed in SEEDS:
        item = by_seed[seed]
        if item.get("pass") is not True:
            return False
        arm_results = item.get("arm_results")
        if not isinstance(arm_results, list):
            return False
        arms = {
            result.get("arm")
            for result in arm_results
            if isinstance(result, dict) and result.get("pass") is True
        }
        if arms != set(ARMS):
            return False
    return True


def _corrected_phase_c_surface_absent(fresh_root: Path) -> tuple[bool, list[str]]:
    root = fresh_root / PHASE_C_CORRECTED_SUBDIR / "seed-0"
    if not root.exists():
        return True, []
    entries = sorted(path.name for path in root.iterdir()) if root.is_dir() else []
    return False, entries


def verify_pre_rerun_state(
    *,
    accepted_root: Path,
    fresh_root: Path,
    accepted_correction_config: Path,
    regenerated_correction_config: Path,
    stage9_5_1_recovery_report: Path,
    correction_worktree_root: Path,
) -> dict[str, Any]:
    failures: list[str] = []

    recovery = _verify_stage9_5_1_recovery_report(stage9_5_1_recovery_report)
    accepted_archive = _verify_accepted_stage8_archive_root(accepted_root)
    phase_a = compare_phase_a(accepted_root=accepted_root, fresh_root=fresh_root)
    phase_b = compare_phase_b(
        accepted_root=accepted_root,
        fresh_root=fresh_root,
        phase_a_result=phase_a,
    )

    phase_a_complete = bool(
        phase_a.get("pass") is True
        and phase_a.get("complete_seeds") == SEEDS
    )
    phase_b_complete = _phase_b_shape_passed(phase_b)
    hard_prerequisites_pass = bool(
        recovery.get("pass") is True
        and accepted_archive.get("pass") is True
        and phase_a_complete
        and phase_b_complete
    )

    if recovery.get("pass") is not True:
        failures.append("hard_prerequisite:stage9_5_1_v1_2_verifier_not_passed")
    if accepted_archive.get("pass") is not True:
        failures.append("hard_prerequisite:accepted_stage8_archive_not_verified")
    if not phase_a_complete:
        failures.append("hard_prerequisite:phase_a_replay_not_fully_verified")
    if not phase_b_complete:
        failures.append("hard_prerequisite:phase_b_replay_not_fully_verified")

    corrected_absent, corrected_entries = _corrected_phase_c_surface_absent(
        fresh_root
    )
    if not corrected_absent:
        failures.append("stop_boundary:corrected_phase_c_seed0_output_already_present")

    if not hard_prerequisites_pass or not corrected_absent:
        report: dict[str, Any] = {
            "audit_id": AUDIT_ID,
            "status": "blocked",
            "pass": False,
            "repository_head": _git_head(),
            "failures": failures,
            "hard_prerequisites_pass": hard_prerequisites_pass,
            "stage9_5_1_recovery": recovery,
            "accepted_stage8_archive": accepted_archive,
            "phase_a": phase_a,
            "phase_b": phase_b,
            "phase_c_preconditions": None,
            "regenerated_correction_config_verification": None,
            "regenerated_correction_config_commit_provenance": None,
            "corrected_phase_c_seed0_output_absent": corrected_absent,
            "corrected_phase_c_seed0_existing_entries": corrected_entries,
            "corrected_phase_c_seed0_rerun_executed_by_this_tool": False,
            "stage10_outcomes_accessed": False,
        }
        report["canonical_sha256"] = _canonical_sha256(report)
        return report

    correction_provenance = _verify_correction_worktree_provenance(
        correction_worktree_root,
        regenerated_correction_config,
    )
    if correction_provenance.get("pass") is not True:
        failures.append("regenerated_correction_config_commit_provenance_not_verified")

    preconditions = compare_phase_c_preconditions(
        accepted_root=accepted_root,
        fresh_root=fresh_root,
        accepted_config_path=accepted_correction_config,
        fresh_config_path=regenerated_correction_config,
    )
    regenerated = verify_regenerated_correction_config(
        regenerated_correction_config,
        fresh_root,
    )

    if preconditions.get("pass") is not True:
        failures.append("phase_c_preconditions_not_verified")
    if preconditions.get("failed_lineage_preserved") is not True:
        failures.append("original_phase_c_v1_seed0_failure_lineage_not_verified")
    if preconditions.get("scientific_blocks_equal") is not True:
        failures.append("correction_config_scientific_blocks_not_equal")
    if regenerated.get("pass") is not True:
        failures.append("regenerated_correction_config_verifier_not_passed")
    if regenerated.get("scientific_blocks_equal") is not True:
        failures.append("regenerated_correction_config_scientific_blocks_not_equal")
    if regenerated.get("phase_c_outcomes_accessed") is not False:
        failures.append("regenerated_config_verifier_phase_c_outcome_access_violation")
    if regenerated.get("stage10_outcomes_accessed") is not False:
        failures.append("stage10_outcome_access_violation")

    report = {
        "audit_id": AUDIT_ID,
        "status": "pass" if not failures else "blocked",
        "pass": not failures,
        "repository_head": _git_head(),
        "failures": failures,
        "hard_prerequisites_pass": hard_prerequisites_pass,
        "stage9_5_1_recovery": recovery,
        "accepted_stage8_archive": accepted_archive,
        "phase_a": phase_a,
        "phase_b": phase_b,
        "phase_c_preconditions": preconditions,
        "regenerated_correction_config_verification": regenerated,
        "regenerated_correction_config_commit_provenance": correction_provenance,
        "original_phase_c_v1_seed0_failure_lineage_verified": bool(
            preconditions.get("failed_lineage_preserved") is True
        ),
        "regenerated_correction_config_scientific_blocks_equal": bool(
            preconditions.get("scientific_blocks_equal") is True
            and regenerated.get("scientific_blocks_equal") is True
        ),
        "corrected_phase_c_seed0_output_absent": True,
        "corrected_phase_c_seed0_existing_entries": [],
        "corrected_phase_c_seed0_rerun_executed_by_this_tool": False,
        "stage10_outcomes_accessed": False,
        "next_authorized_step": (
            "corrected_phase_c_seed0_rerun"
            if not failures
            else "none_fail_closed"
        ),
    }
    report["canonical_sha256"] = _canonical_sha256(report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Verify Stage-9.5-6 Phase-C pre-rerun readiness after successful "
            "Stage-9.5-1 recovery and complete Phase-A/B historical replay."
        )
    )
    parser.add_argument("--accepted-root", type=Path, required=True)
    parser.add_argument("--fresh-root", type=Path, required=True)
    parser.add_argument("--accepted-correction-config", type=Path, required=True)
    parser.add_argument("--regenerated-correction-config", type=Path, required=True)
    parser.add_argument("--stage9-5-1-recovery-report", type=Path, required=True)
    parser.add_argument("--correction-worktree-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    report = verify_pre_rerun_state(
        accepted_root=args.accepted_root,
        fresh_root=args.fresh_root,
        accepted_correction_config=args.accepted_correction_config,
        regenerated_correction_config=args.regenerated_correction_config,
        stage9_5_1_recovery_report=args.stage9_5_1_recovery_report,
        correction_worktree_root=args.correction_worktree_root,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    if not report["pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
