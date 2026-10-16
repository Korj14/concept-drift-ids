from __future__ import annotations

import json
from pathlib import Path

from tools.stage9_5.work_package_order_gate import evaluate


def _contract(tmp_path: Path) -> Path:
    path = tmp_path / "contract.json"
    path.write_text(
        json.dumps(
            {
                "contract_id": "test-gate",
                "closure_doc_path": "closure.md",
                "success_json_path": "success.json",
                "required_success_values": {
                    "audit_id": "stage9.5-6-clean-deterministic-full-seed-rerun-v1-success",
                    "status": "accepted_stage9_5_6_closure_evidence",
                    "stage9_5_1.status": "closed",
                    "stage9_5_1.identity_failures": 0,
                    "stage9_5_1.external_artifact_blockers": 0,
                    "same_head_stage9.conclusion": "success",
                    "replay_equivalence.protocol_id": "stage9.5-6-replay-equivalence-correction-v1_1",
                    "replay_equivalence.pass": True,
                    "replay_equivalence.phase_a_complete_seeds": [0, 1, 2, 3, 4],
                    "replay_equivalence.phase_b_complete_seeds": [0, 1, 2, 3, 4],
                    "replay_equivalence.original_phase_c_v1_seed0_failure_lineage_preserved": True,
                    "replay_equivalence.corrected_phase_c_seed0_rerun_complete": True,
                    "replay_equivalence.accepted_maintenance_archive_verified": True,
                    "unresolved_class_a": [],
                    "scientific_objects_modified": False,
                    "stage10_outcomes_accessed": False,
                },
                "required_success_hash_fields": [
                    "artifact.report_canonical_sha256"
                ],
                "closure_doc_must_reference": [
                    "success.json",
                    "stage9.5-6-replay-equivalence-correction-v1_1",
                ],
                "closure_doc_must_contain_report_canonical_sha256": True,
            }
        ),
        encoding="utf-8",
    )
    return path


def _success() -> dict[str, object]:
    return {
        "audit_id": "stage9.5-6-clean-deterministic-full-seed-rerun-v1-success",
        "status": "accepted_stage9_5_6_closure_evidence",
        "stage9_5_1": {
            "status": "closed",
            "identity_failures": 0,
            "external_artifact_blockers": 0,
        },
        "same_head_stage9": {"conclusion": "success"},
        "replay_equivalence": {
            "protocol_id": "stage9.5-6-replay-equivalence-correction-v1_1",
            "pass": True,
            "phase_a_complete_seeds": [0, 1, 2, 3, 4],
            "phase_b_complete_seeds": [0, 1, 2, 3, 4],
            "original_phase_c_v1_seed0_failure_lineage_preserved": True,
            "corrected_phase_c_seed0_rerun_complete": True,
            "accepted_maintenance_archive_verified": True,
        },
        "artifact": {"report_canonical_sha256": "a" * 64},
        "unresolved_class_a": [],
        "scientific_objects_modified": False,
        "stage10_outcomes_accessed": False,
    }


def test_missing_files_remain_locked(tmp_path: Path) -> None:
    report = evaluate(
        contract_path=_contract(tmp_path),
        closure_doc=tmp_path / "closure.md",
        success_json=tmp_path / "success.json",
    )
    assert report["later_packages_unlocked"] is False
    assert report["failures"] == ["closure_doc_missing", "success_json_missing"]


def test_placeholder_pair_does_not_unlock(tmp_path: Path) -> None:
    closure = tmp_path / "closure.md"
    success = tmp_path / "success.json"
    closure.write_text("# placeholder\n", encoding="utf-8")
    success.write_text("{}\n", encoding="utf-8")

    report = evaluate(
        contract_path=_contract(tmp_path),
        closure_doc=closure,
        success_json=success,
    )
    assert report["later_packages_unlocked"] is False
    assert report["failures"]


def test_unresolved_class_a_remains_locked(tmp_path: Path) -> None:
    closure = tmp_path / "closure.md"
    success_path = tmp_path / "success.json"
    payload = _success()
    payload["unresolved_class_a"] = ["A-PROV-01"]
    success_path.write_text(json.dumps(payload), encoding="utf-8")
    closure.write_text(
        "success.json\nstage9.5-6-replay-equivalence-correction-v1_1\n"
        + "a" * 64
        + "\n",
        encoding="utf-8",
    )

    report = evaluate(
        contract_path=_contract(tmp_path),
        closure_doc=closure,
        success_json=success_path,
    )
    assert report["later_packages_unlocked"] is False
    assert "success_value_mismatch:unresolved_class_a" in report["failures"]


def test_complete_linked_success_evidence_unlocks(tmp_path: Path) -> None:
    closure = tmp_path / "closure.md"
    success_path = tmp_path / "success.json"
    payload = _success()
    success_path.write_text(json.dumps(payload), encoding="utf-8")
    closure.write_text(
        "success.json\nstage9.5-6-replay-equivalence-correction-v1_1\n"
        + "a" * 64
        + "\n",
        encoding="utf-8",
    )

    report = evaluate(
        contract_path=_contract(tmp_path),
        closure_doc=closure,
        success_json=success_path,
    )
    assert report["later_packages_unlocked"] is True
    assert report["failures"] == []


def test_unlinked_report_hash_remains_locked(tmp_path: Path) -> None:
    closure = tmp_path / "closure.md"
    success_path = tmp_path / "success.json"
    payload = _success()
    success_path.write_text(json.dumps(payload), encoding="utf-8")
    closure.write_text(
        "success.json\nstage9.5-6-replay-equivalence-correction-v1_1\n",
        encoding="utf-8",
    )

    report = evaluate(
        contract_path=_contract(tmp_path),
        closure_doc=closure,
        success_json=success_path,
    )
    assert report["later_packages_unlocked"] is False
    assert "closure_doc_missing_report_canonical_sha256" in report["failures"]
