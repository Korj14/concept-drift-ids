from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = (
    PROJECT_ROOT / "data" / "manifests" / "stage9_5_hostile_review_v1.json"
)
STAGE10_PATH = (
    PROJECT_ROOT
    / "data"
    / "manifests"
    / "stage10_plus_master_replication_sensitivity_v1.json"
)

PACKAGE_EVIDENCE = {
    "9.5-0": "STAGE9_5_0_PARAMETER_CONTROL_COMPLETENESS_CLOSURE.md",
    "9.5-1": "STAGE9_5_1_FRESH_CLONE_RECONSTRUCTION_BLOCKED.md",
    "9.5-2": "STAGE9_5_2_INDEPENDENT_STATISTICAL_ORACLE_CLOSURE.md",
    "9.5-3": "STAGE9_5_3_CAUSAL_PROPERTY_ASSURANCE_CLOSURE.md",
    "9.5-4": "STAGE9_5_4_TARGETED_MUTATION_ASSURANCE_CLOSURE.md",
    "9.5-5": "STAGE9_5_5_STATIC_SOFTWARE_ASSURANCE_CLOSURE.md",
    "9.5-6": "STAGE9_5_6_CLEAN_DETERMINISTIC_FULL_SEED_RERUN_BLOCKED.md",
    "9.5-7": "STAGE9_5_7_CLAIM_TRACEABILITY_CLOSURE.md",
    "9.5-8": "STAGE9_5_8_INDEPENDENT_REPORTING_CLOSURE.md",
}

FAILURE_NAME_TOKENS = (
    "first_run_failure",
    "parameter_scan_failure",
    "scanner_harness_failure",
    "failed_run",
)


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"Expected JSON object: {path}")
    return value


def _canonical_sha256(payload: Any) -> str:
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _git_blob_sha(path: Path) -> str:
    relative = path.relative_to(PROJECT_ROOT).as_posix()
    result = subprocess.run(  # noqa: S603
        ["git", "rev-parse", f"HEAD:{relative}"],  # noqa: S607
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    return result.stdout.strip()


def _failure_artifacts() -> list[str]:
    root = PROJECT_ROOT / "results" / "audits"
    paths: list[str] = []
    for path in root.rglob("*.json"):
        relative = path.relative_to(PROJECT_ROOT).as_posix()
        if not relative.startswith("results/audits/stage9_5"):
            continue
        if any(token in path.name for token in FAILURE_NAME_TOKENS):
            paths.append(relative)
    return sorted(paths)


def run(output_dir: Path) -> dict[str, Any]:
    contract = _load_json(CONTRACT_PATH)
    stage10 = _load_json(STAGE10_PATH)

    identity_checks: dict[str, bool] = {}
    for name, descriptor in contract["source_identities"].items():
        path = PROJECT_ROOT / str(descriptor["path"])
        identity_checks[name] = (
            path.is_file()
            and _git_blob_sha(path) == str(descriptor["git_blob_sha"])
        )

    package_checks = {
        package: (PROJECT_ROOT / path).is_file()
        for package, path in PACKAGE_EVIDENCE.items()
    }

    attacks = list(contract["reviewer_attacks"])
    ids = [str(item["id"]) for item in attacks]
    expected_ids = [chr(code) for code in range(ord("A"), ord("T") + 1)]
    class_b = [
        item for item in attacks if item["classification"] == "Class B"
    ]
    class_c = [
        item for item in attacks if item["classification"] == "Class C"
    ]
    other_classes = [
        item
        for item in attacks
        if item["classification"] not in {"Class B", "Class C"}
    ]

    class_b_dispositioned = all(
        bool(str(item.get("disposition", "")).strip()) for item in class_b
    )
    class_c_dispositioned = all(
        bool(str(item.get("disposition", "")).strip()) for item in class_c
    )

    unresolved_class_a = list(contract["unresolved_class_a"])
    class_a_blockers_are_hard = all(
        item.get("classification") == "Class A"
        and item.get("status") == "open_blocked"
        and item.get("blocks_stage9_5_closure") is True
        and item.get("blocks_stage10") is True
        for item in unresolved_class_a
    )

    stage10_frozen = bool(
        stage10.get("status")
        == "prospectively_frozen_before_any_stage10_treatment_execution"
        and stage10.get("hard_gate", {}).get("stage10_execution_permitted")
        is False
        and stage10.get("stage10_treatment_outcomes_accessed") is False
        and len(stage10.get("master_obligations", [])) >= 15
    )

    failures = _failure_artifacts()
    failure_parse_errors: list[str] = []
    for relative in failures:
        try:
            _load_json(PROJECT_ROOT / relative)
        except (OSError, ValueError, TypeError) as exc:
            failure_parse_errors.append(f"{relative}: {type(exc).__name__}")

    no_stage10_results = not any(
        path.is_file()
        for pattern in (
            "results/stage10*/*",
            "results/**/stage10*/*",
        )
        for path in PROJECT_ROOT.glob(pattern)
    )

    audit_execution_pass = bool(
        all(identity_checks.values())
        and all(package_checks.values())
        and ids == expected_ids
        and len(attacks) == 20
        and len(class_b) == 6
        and len(class_c) == 14
        and not other_classes
        and class_b_dispositioned
        and class_c_dispositioned
        and class_a_blockers_are_hard
        and not failure_parse_errors
        and stage10_frozen
        and no_stage10_results
        and contract.get("stage10_outcomes_accessed") is False
    )

    closure_eligible = bool(
        audit_execution_pass and len(unresolved_class_a) == 0
    )
    status = "closed" if closure_eligible else "open_blocked"

    report: dict[str, Any] = {
        "audit_id": "stage9.5-9-hostile-review-audit-v1_1",
        "status": status,
        "audit_execution_pass": audit_execution_pass,
        "stage9_5_closure_eligible": closure_eligible,
        "contract": str(CONTRACT_PATH.relative_to(PROJECT_ROOT)),
        "source_identity_checks": identity_checks,
        "package_evidence_checks": package_checks,
        "reviewer_attacks": {
            "count": len(attacks),
            "ids": ids,
            "class_b_count": len(class_b),
            "class_c_count": len(class_c),
            "other_class_count": len(other_classes),
            "class_b_all_dispositioned": class_b_dispositioned,
            "class_c_all_dispositioned": class_c_dispositioned,
        },
        "unresolved_class_a": unresolved_class_a,
        "unresolved_class_a_count": len(unresolved_class_a),
        "repository_failed_audit_artifacts": failures,
        "repository_failed_audit_artifact_count": len(failures),
        "failure_artifact_parse_errors": failure_parse_errors,
        "stage10_master_protocol_frozen": stage10_frozen,
        "stage10_master_obligation_count": len(
            stage10.get("master_obligations", [])
        ),
        "stage10_results_present": not no_stage10_results,
        "stage10_outcomes_accessed": False,
        "interpretation": (
            "All Class-B/Class-C reviewer attacks are dispositioned, but "
            "Stage 9.5 remains open because the exact System-A checkpoint "
            "byte provenance/reconstructibility blocker is unresolved."
            if not closure_eligible
            else "All frozen hostile-review closure criteria are satisfied."
        ),
    }
    report["canonical_sha256"] = _canonical_sha256(
        {key: value for key, value in report.items() if key != "canonical_sha256"}
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "hostile_review_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    lines = [
        "# Stage 9.5-9 Hostile-Review Audit",
        "",
        f"- audit execution: **{'PASS' if audit_execution_pass else 'FAIL'}**",
        f"- Stage 9.5 closure eligible: **{closure_eligible}**",
        f"- gate status: **{status.upper()}**",
        f"- reviewer attacks: **{len(attacks)}**",
        f"- Class B: **{len(class_b)}**",
        f"- Class C: **{len(class_c)}**",
        f"- unresolved Class A: **{len(unresolved_class_a)}**",
        f"- preserved failed-audit artifacts: **{len(failures)}**",
        f"- Stage-10+ master protocol frozen: **{stage10_frozen}**",
        f"- report SHA-256: `{report['canonical_sha256']}`",
    ]
    (output_dir / "HOSTILE_REVIEW_REPORT.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )

    if not audit_execution_pass:
        raise SystemExit("Stage 9.5-9 hostile-review audit execution failed.")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run Stage 9.5-9 hostile-review closure audit"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("artifacts/stage9_5_hostile_review_v1_1"),
    )
    args = parser.parse_args()
    run(args.output_dir)


if __name__ == "__main__":
    main()
