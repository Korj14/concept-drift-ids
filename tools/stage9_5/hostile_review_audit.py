from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

from tools.stage9_5.work_package_order_gate import evaluate as evaluate_order_gate

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


# Versioned post-recovery overlay: the original v1 hostile-review contract is
# immutable historical authority, not a mutable current-status register.
STAGE10_MASTER_V1_1_PATH = (
    PROJECT_ROOT / "data" / "manifests"
    / "stage10_plus_master_replication_sensitivity_v1_1.json"
)
STAGE10_MASTER_BINDING_PATH = (
    PROJECT_ROOT / "data" / "manifests"
    / "stage9_5_9_stage10_v1_1_binding_v1_3.json"
)

POST_RECOVERY_PATH = (
    PROJECT_ROOT / "data" / "manifests"
    / "stage9_5_9_post_recovery_assurance_v1_2.json"
)
_PINNED_POST_RECOVERY_POLICY: dict[str, Any] = {'schema_version': '1.2', 'status': 'assurance_only_corrective_pending_fresh_exact_head_ci', 'scope': 'stage9.5-9-hostile-review-post-recovery-state', 'original_contract': {'path': 'data/manifests/stage9_5_hostile_review_v1.json', 'git_blob_sha': '49e77541d4adea56b32b2cb76579fb0d5fe278e3'}, 'q1_register': {'path': 'Q1_ADVERSARIAL_AUDIT_REGISTER.md', 'frozen_git_blob_sha': 'e1db2f5d9031e502668ec3960bac4a16d710fd57', 'frozen_historical_commit': '4c3c74bb708f9fdd67d05c33b6a8c556a63d8438', 'published_snapshot_blob_sha': '54f604941a61443330e4d49541471c0c4e2c4400', 'published_snapshot_commit': '4460439b2d25dbcc3cafe18af5a647d334f22a22', 'compatibility_rule': 'frozen_byte_prefix_and_published_snapshot_byte_prefix'}, 'source_rule': 'original_frozen_identity_for_q1_and_strict_exact_identity_for_protocol', 'historical_class_a_id': 'A-PROV-01', 'current_resolution_authority': {'contract': 'data/manifests/stage9_5_6_closure_order_gate_v1.json', 'rule': 'evaluate_current_order_gate_validates_canonical_stage9_5_1_and_6_evidence'}, 'historical_failure_records_modified': False, 'accepted_scientific_objects_modified': False, 'stage10_outcomes_accessed': False, 'formal_stage9_5_closure_asserted': False}


def _git_bytes(*args: str) -> bytes:
    return subprocess.run(
        ["git", *args],
        cwd=PROJECT_ROOT,
        capture_output=True,
        check=True,
    ).stdout


def _tree_sha(commit: str, relative: str) -> str:
    return _git_bytes("rev-parse", f"{commit}:{relative}").decode("ascii").strip()


# v1.3 additive, exact-policy-bound source identity correction.
_PINNED_STAGE10_MASTER_BINDING: dict[str, Any] = {'schema_version': '1.3', 'status': 'prospective_assurance_only_correction_pending_exact_head_validation', 'scope': 'stage9.5-9-binding-to-frozen-stage10-master-v1_1', 'historical_stage10_master': {'manifest_path': 'data/manifests/stage10_plus_master_replication_sensitivity_v1.json', 'manifest_git_blob_sha': 'e9971ebb9fe5b46352c27a73b0ebdac09937d091', 'protocol_path': 'STAGE10_PLUS_MASTER_REPLICATION_SENSITIVITY_PROTOCOL.md', 'protocol_git_blob_sha': '8c24d9e7c72fce278baa56e3f17b665ae992fa52', 'protocol_id': 'stage10-plus-master-replication-sensitivity-v1'}, 'governing_stage10_master': {'freeze_commit': '93df16b059b55eb1dc0ce33248d9ddbf75c158b9', 'manifest_path': 'data/manifests/stage10_plus_master_replication_sensitivity_v1_1.json', 'manifest_git_blob_sha': '8ac82c8d907243556a5673d09600cd1bdc19aa52', 'protocol_path': 'STAGE10_PLUS_MASTER_REPLICATION_SENSITIVITY_PROTOCOL_V1_1.md', 'protocol_git_blob_sha': 'ac61908d30bcc26cddbe6467d807a3de119689d9', 'protocol_id': 'stage10-plus-master-replication-sensitivity-v1_1', 'required_obligation_ids': ['S10-01', 'S10-02', 'S10-03', 'S10-04', 'S10-05', 'S10-06', 'S10-07', 'S10-08', 'S10-09', 'S10-10', 'S10-11', 'S10-12', 'S10-13', 'S10-14', 'S10-15', 'S10-16'], 'required_stage_specific_freeze_item_count': 19, 'required_hostile_review_rule': 'In-order Stage 9.5-9 must verify v1.1 or a later prospectively justified master protocol.'}, 'binding': 'verify_original_and_v1_1_git_source_identities_and_locked_semantics', 'original_stage9_5_9_contract_untouched': True, 'original_stage9_5_9_v1_2_overlay_untouched': True, 'original_stage10_master_versions_untouched': True, 'stage9_5_formal_closure_candidate_untouched': True, 'scientific_objects_modified': False, 'stage10_treatment_outcomes_accessed': False, 'stage10_execution_released': False}


def _verify_stage10_master_binding(
    historical: dict[str, Any], current: dict[str, Any]
) -> dict[str, Any]:
    """Bind the frozen v1 history AND already frozen prospective v1.1."""
    policy = _load_json(STAGE10_MASTER_BINDING_PATH)
    if policy != _PINNED_STAGE10_MASTER_BINDING:
        raise ValueError("Unrecognized Stage-9.5-9 Stage-10 v1.1 binding policy.")
    old = policy["historical_stage10_master"]
    new = policy["governing_stage10_master"]
    tracked = [
        old["manifest_path"], old["protocol_path"],
        new["manifest_path"], new["protocol_path"],
    ]
    for item in (old, new):
        for path_key, hash_key in (
            ("manifest_path", "manifest_git_blob_sha"),
            ("protocol_path", "protocol_git_blob_sha"),
        ):
            path = item[path_key]
            if not (PROJECT_ROOT / path).is_file():
                raise ValueError(f"Frozen Stage-10 master source missing: {path}")
            if _tree_sha("HEAD", path) != item[hash_key]:
                raise ValueError(f"Frozen Stage-10 master Git identity changed: {path}")
    _git_bytes("merge-base", "--is-ancestor", new["freeze_commit"], "HEAD")
    for path_key, hash_key in (
        ("manifest_path", "manifest_git_blob_sha"),
        ("protocol_path", "protocol_git_blob_sha"),
    ):
        if _tree_sha(new["freeze_commit"], new[path_key]) != new[hash_key]:
            raise ValueError("Stage-10 master v1.1 is not its prospective freeze object.")
    try:
        _git_bytes("diff", "--quiet", "HEAD", "--", *tracked)
    except subprocess.CalledProcessError as exc:
        raise ValueError("Frozen Stage-10 master working-tree inputs changed.") from exc

    ids = [item.get("id") for item in current.get("master_obligations", [])]
    old_valid = bool(
        historical.get("protocol_id") == old["protocol_id"]
        and historical.get("status")
        == "prospectively_frozen_before_any_stage10_treatment_execution"
        and historical.get("hard_gate", {}).get("stage10_execution_permitted") is False
        and historical.get("stage10_treatment_outcomes_accessed") is False
        and len(historical.get("master_obligations", [])) >= 15
    )
    new_valid = bool(
        current.get("protocol_id") == new["protocol_id"]
        and current.get("status")
        == "prospectively_frozen_before_any_stage10_treatment_execution"
        and current.get("supersedes_for_future_stage10_governance") == old["protocol_id"]
        and current.get("historical_v1_preserved") is True
        and current.get("governing_stage9_5_protocol")
        == "STAGE9_5_Q1_INDEPENDENT_ASSURANCE_PROTOCOL.md"
        and current.get("hard_gate", {}).get("stage10_execution_permitted") is False
        and current.get("stage10_treatment_outcomes_accessed") is False
        and ids == new["required_obligation_ids"]
        and len(set(ids)) == 16
        and all(
            isinstance(item.get("requirement"), str)
            and bool(item["requirement"].strip())
            and isinstance(item.get("type"), str)
            and bool(item["type"].strip())
            for item in current.get("master_obligations", [])
        )
        and len(current.get("stage_specific_pre_outcome_freeze_required", []))
        == new["required_stage_specific_freeze_item_count"]
        and current.get("future_hostile_review_requirement")
        == new["required_hostile_review_rule"]
    )
    return {
        "historical_v1_verified": old_valid,
        "governing_v1_1_verified": new_valid,
        "pass": bool(old_valid and new_valid),
        "historical_v1_manifest_blob": old["manifest_git_blob_sha"],
        "governing_v1_1_manifest_blob": new["manifest_git_blob_sha"],
        "governing_v1_1_freeze_commit": new["freeze_commit"],
        "governing_v1_1_obligation_count": len(ids),
        "stage10_execution_released": False,
    }


def _assert_append_only_register(
    frozen: bytes, published_snapshot: bytes, observed_head: bytes
) -> None:
    if not frozen or not published_snapshot or not observed_head:
        raise ValueError("Q1 register frozen or snapshot object is empty.")
    if not published_snapshot.startswith(frozen):
        raise ValueError("Published Q1 register rewrites the frozen historical source.")
    if not observed_head.startswith(published_snapshot):
        raise ValueError("Current Q1 register rewrites or truncates preserved history.")


def _current_source_identities(
    contract: dict[str, Any]
) -> dict[str, bool]:
    policy = _load_json(POST_RECOVERY_PATH)
    if policy != _PINNED_POST_RECOVERY_POLICY:
        raise ValueError("Unrecognized Stage-9.5-9 v1.2 reconciliation policy.")
    orig = policy["original_contract"]
    q1 = policy["q1_register"]
    if _tree_sha("HEAD", orig["path"]) != orig["git_blob_sha"]:
        raise ValueError("Frozen hostile-review v1 contract was modified.")
    frozen_sources = contract["source_identities"]
    if (len(frozen_sources) != 2
        or frozen_sources["q1_adversarial_register"]["git_blob_sha"]
        != q1["frozen_git_blob_sha"]
        or frozen_sources["q1_adversarial_register"]["path"] != q1["path"]):
        raise ValueError("Hostile-review frozen Q1 source identity was substituted.")
    tracked = [orig["path"]] + [v["path"] for v in frozen_sources.values()]
    try:
        _git_bytes("diff", "--quiet", "HEAD", "--", *tracked)
    except subprocess.CalledProcessError as exc:
        raise ValueError("Frozen hostile-review sources differ from checked HEAD.") from exc
    _git_bytes("merge-base", "--is-ancestor", q1["published_snapshot_commit"], "HEAD")
    old_sha = _tree_sha(q1["frozen_historical_commit"], q1["path"])
    snapshot_sha = _tree_sha(q1["published_snapshot_commit"], q1["path"])
    current_sha = _tree_sha("HEAD", q1["path"])
    if old_sha != q1["frozen_git_blob_sha"]:
        raise ValueError("Frozen Q1 register does not match the original historical commit.")
    if snapshot_sha != q1["published_snapshot_blob_sha"]:
        raise ValueError("Q1 register published preservation witness changed.")
    _assert_append_only_register(
        _git_bytes("cat-file", "blob", old_sha),
        _git_bytes("cat-file", "blob", snapshot_sha),
        _git_bytes("cat-file", "blob", current_sha),
    )
    original_protocol = frozen_sources["stage9_5_protocol"]
    protocol_path = PROJECT_ROOT / original_protocol["path"]
    if not protocol_path.is_file():
        raise ValueError("Original Stage-9.5 frozen protocol is missing.")
    return {
        "q1_adversarial_register": True,
        "stage9_5_protocol": _tree_sha("HEAD", original_protocol["path"])
        == original_protocol["git_blob_sha"],
    }


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
    result = subprocess.run(
        ["git", "rev-parse", f"HEAD:{relative}"],
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
    stage10_v1_1 = _load_json(STAGE10_MASTER_V1_1_PATH)
    stage10_binding = _verify_stage10_master_binding(stage10, stage10_v1_1)

    identity_checks = _current_source_identities(contract)

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

    # This array is immutable *historical* evidence, not the current gate.
    historical_class_a = list(contract["unresolved_class_a"])
    class_a_blockers_are_hard = bool(
        len(historical_class_a) == 1
        and historical_class_a[0].get("id") == "A-PROV-01"
        and historical_class_a[0].get("classification") == "Class A"
        and historical_class_a[0].get("status") == "open_blocked"
        and historical_class_a[0].get("blocks_stage9_5_closure") is True
        and historical_class_a[0].get("blocks_stage10") is True
    )
    # Reuse the frozen canonical Stage-9.5-1/6 verifier, including Git ancestry.
    order_gate = evaluate_order_gate()
    predecessor_verified = bool(
        order_gate["later_packages_unlocked"] and not order_gate["failures"]
    )
    unresolved_class_a = [] if predecessor_verified else historical_class_a

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
        and stage10_binding["pass"]
        and no_stage10_results
        and contract.get("stage10_outcomes_accessed") is False
    )

    closure_eligible = bool(
        audit_execution_pass and len(unresolved_class_a) == 0
    )
    status = "closed" if closure_eligible else "open_blocked"

    report: dict[str, Any] = {
        "audit_id": "stage9.5-9-hostile-review-audit-v1_3",
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
        "historical_unresolved_class_a": historical_class_a,
        "historical_unresolved_class_a_count": len(historical_class_a),
        "stage9_5_1_6_order_gate": order_gate,
        "stage9_5_1_6_verified": predecessor_verified,
        "post_recovery_assurance_policy": str(POST_RECOVERY_PATH.relative_to(PROJECT_ROOT)),
        "formal_stage9_5_closure_established": False,
        "exact_head_ci_chain_requires_independent_verification": True,
        "repository_failed_audit_artifacts": failures,
        "repository_failed_audit_artifact_count": len(failures),
        "failure_artifact_parse_errors": failure_parse_errors,
        "stage10_master_protocol_frozen": stage10_frozen,
        "stage10_master_binding_v1_3": stage10_binding,
        "stage10_master_v1_1_verified": stage10_binding["governing_v1_1_verified"],
        "stage10_master_v1_1_binding_contract": str(
            STAGE10_MASTER_BINDING_PATH.relative_to(PROJECT_ROOT)
        ),
        "stage10_master_obligation_count": len(
            stage10.get("master_obligations", [])
        ),
        "stage10_results_present": not no_stage10_results,
        "stage10_outcomes_accessed": False,
        "interpretation": (
            "Stage-9.5-9 audit criteria satisfied from the frozen predecessor "
            "reports. This report alone is not formal Stage-9.5 closure; "
            "exact-head CI, static dispositions and final retrospective remain."
            if closure_eligible
            else "Stage-9.5-9 audit is blocked; the frozen predecessor "
            "gate did not verify current Stage-9.5-1/6 closure. "
            "Original Class-A failure history is preserved."
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
        f"- Stage-10+ governing v1.1 verified: **{stage10_binding['governing_v1_1_verified']}**",
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
