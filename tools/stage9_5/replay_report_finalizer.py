from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = (
    PROJECT_ROOT
    / "data"
    / "manifests"
    / "stage9_5_6_replay_report_construction_v1.json"
)
OUTPUT_NAME = "replay_equivalence_report.json"
SHA40_RE = re.compile(r"^[0-9a-f]{40}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for key, value in pairs:
        if key in payload:
            raise ValueError(f"Duplicate JSON object key: {key}")
        payload[key] = value
    return payload


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=_reject_duplicate_pairs,
    )
    if not isinstance(payload, dict):
        raise TypeError(f"Expected JSON object: {path}")
    return payload


def _canonical_sha256(payload: object) -> str:
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _get_path(payload: dict[str, Any], dotted: str) -> Any:
    node: Any = payload
    for part in dotted.split("."):
        if not isinstance(node, dict) or part not in node:
            raise KeyError(dotted)
        node = node[part]
    return node


def _nested_comparison_consistency_failures(
    value: Any,
    *,
    path: str,
) -> list[str]:
    failures: list[str] = []
    if isinstance(value, dict):
        if "pass" in value and value["pass"] is not True:
            failures.append(f"nested_comparison_pass_not_true:{path}")
        if "dependency_gate_pass" in value and value["dependency_gate_pass"] is not True:
            failures.append(f"nested_comparison_dependency_gate_not_true:{path}")
        for field in ("failures", "blockers", "mismatches"):
            if field in value and value[field] != []:
                failures.append(
                    f"nested_comparison_{field}_nonempty:{path}"
                )
        if "mismatch_count" in value and value["mismatch_count"] != 0:
            failures.append(
                f"nested_comparison_mismatch_count_nonzero:{path}"
            )
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else str(key)
            failures.extend(
                _nested_comparison_consistency_failures(
                    child,
                    path=child_path,
                )
            )
    elif isinstance(value, list):
        for index, child in enumerate(value):
            failures.extend(
                _nested_comparison_consistency_failures(
                    child,
                    path=f"{path}[{index}]",
                )
            )
    return failures


def _comparison_failures(
    contract: dict[str, Any],
    evidence: dict[str, Any],
) -> list[str]:
    failures: list[str] = []
    expected = contract["comparison_evidence_contract"]
    if not isinstance(expected, dict):
        return ["invalid_construction_contract_comparison_evidence_contract"]

    for dotted, expected_value in expected.items():
        try:
            actual = _get_path(evidence, dotted)
        except KeyError:
            failures.append(f"missing_comparison_evidence_field:{dotted}")
            continue
        if actual != expected_value:
            failures.append(f"comparison_evidence_value_mismatch:{dotted}")

    audited_head = evidence.get("audited_head")
    if not isinstance(audited_head, str) or SHA40_RE.fullmatch(audited_head) is None:
        failures.append("invalid_comparison_evidence_audited_head")

    recovery_hash = evidence.get(
        "stage9_5_1_recovery_report_canonical_sha256"
    )
    if (
        not isinstance(recovery_hash, str)
        or SHA256_RE.fullmatch(recovery_hash) is None
    ):
        failures.append(
            "invalid_stage9_5_1_recovery_report_canonical_sha256"
        )

    embedded_hash = evidence.get("canonical_sha256")
    if not isinstance(embedded_hash, str) or SHA256_RE.fullmatch(
        embedded_hash
    ) is None:
        failures.append("invalid_comparison_evidence_canonical_sha256")
    else:
        core = dict(evidence)
        core.pop("canonical_sha256", None)
        if _canonical_sha256(core) != embedded_hash:
            failures.append("comparison_evidence_canonical_sha256_mismatch")

    failures.extend(
        _nested_comparison_consistency_failures(
            evidence,
            path="comparison_evidence",
        )
    )
    return failures


def _build_report(
    contract: dict[str, Any],
    evidence: dict[str, Any],
    validation_failures: list[str],
) -> dict[str, Any]:
    construction = contract["deterministic_producer"]
    if not isinstance(construction, dict):
        raise TypeError("deterministic_producer must be an object")

    embedded_hash = evidence.get("canonical_sha256")
    comparison_hash = (
        embedded_hash
        if isinstance(embedded_hash, str)
        and SHA256_RE.fullmatch(embedded_hash) is not None
        else None
    )
    mismatch_count = evidence.get("mismatch_count")
    mismatch_value = mismatch_count if isinstance(mismatch_count, int) else -1
    pass_state = not validation_failures

    phase_a = evidence.get("phase_a")
    phase_b = evidence.get("phase_b")
    phase_c = evidence.get("phase_c")
    historical_heads = evidence.get("historical_heads")
    if not isinstance(phase_a, dict):
        phase_a = {}
    if not isinstance(phase_b, dict):
        phase_b = {}
    if not isinstance(phase_c, dict):
        phase_c = {}
    if not isinstance(historical_heads, dict):
        historical_heads = {}

    report: dict[str, Any] = {
        "audit_id": "stage9.5-6-clean-deterministic-full-seed-rerun-v1",
        "status": "pass" if pass_state else "blocked",
        "pass": pass_state,
        "audited_head": evidence.get("audited_head"),
        "failures": list(validation_failures),
        "blockers": [] if pass_state else ["comparison_evidence_not_accepted"],
        "construction": {
            "contract_id": contract["contract_id"],
            "producer_id": construction["producer_id"],
            "comparator_id": construction["comparator_id"],
            "finalizer_id": construction["finalizer_id"],
            "manual_success_report_permitted": False,
            "deterministic_comparison_complete": bool(
                evidence.get("comparison_complete") is True and pass_state
            ),
            "source_evidence_complete": bool(
                evidence.get("source_evidence_complete") is True and pass_state
            ),
            "mismatch_count": mismatch_value,
            "comparison_evidence_canonical_sha256": comparison_hash,
            "stage1_reconstruction_report_canonical_sha256": evidence.get(
                "stage1_reconstruction_report_canonical_sha256"
            ),
            "stage9_5_1_recovery_report_canonical_sha256": evidence.get(
                "stage9_5_1_recovery_report_canonical_sha256"
            ),
        },
        "replay_equivalence": {
            "protocol_id": contract["replay_protocol_id"],
            "pass": pass_state,
            "rerun_seed": phase_c.get("rerun_seed"),
            "phase_a_complete_seeds": phase_a.get("complete_seeds"),
            "phase_b_complete_seeds": phase_b.get("complete_seeds"),
            "original_phase_c_v1_seed0_failure_lineage_preserved": phase_c.get(
                "original_failure_lineage_preserved"
            ),
            "corrected_phase_c_seed0_rerun_complete": phase_c.get(
                "corrected_rerun_complete"
            ),
            "accepted_maintenance_archive_verified": evidence.get(
                "accepted_maintenance_archive_verified"
            ),
            "stage1_reconstructed_under_historical_environment": evidence.get(
                "stage1_reconstructed_under_historical_environment"
            ),
            "regenerated_correction_config_all_scientific_blocks_equal": evidence.get(
                "regenerated_correction_config_all_scientific_blocks_equal"
            ),
            "historical_heads": historical_heads,
            "accepted_correction_manifest_sha256": evidence.get(
                "accepted_correction_manifest_sha256"
            ),
            "accepted_stage8_evidence_commit": evidence.get(
                "accepted_stage8_evidence_commit"
            ),
        },
        "unresolved_class_a": evidence.get("unresolved_class_a"),
        "scientific_objects_modified": evidence.get("scientific_objects_modified"),
        "stage10_outcomes_accessed": evidence.get("stage10_outcomes_accessed"),
    }
    report["canonical_sha256"] = _canonical_sha256(report)
    return report


def run(
    comparison_evidence_path: Path,
    output_dir: Path,
    *,
    contract_path: Path = CONTRACT_PATH,
) -> dict[str, Any]:
    if not contract_path.is_absolute():
        contract_path = PROJECT_ROOT / contract_path
    contract = _load_json(contract_path)
    evidence = _load_json(comparison_evidence_path)
    failures = _comparison_failures(contract, evidence)
    report = _build_report(contract, evidence, failures)

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / OUTPUT_NAME).write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Finalize Stage 9.5-6 replay-equivalence comparison evidence"
    )
    parser.add_argument("--comparison-evidence", type=Path, required=True)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("results/audits/stage9_5_full_seed_rerun_v1"),
    )
    parser.add_argument("--contract", type=Path, default=CONTRACT_PATH)
    args = parser.parse_args()

    report = run(
        args.comparison_evidence,
        args.output_dir,
        contract_path=args.contract,
    )
    if not report["pass"]:
        raise SystemExit(
            "Stage 9.5-6 replay finalization blocked: "
            + "; ".join(str(item) for item in report["failures"])
        )


if __name__ == "__main__":
    main()
