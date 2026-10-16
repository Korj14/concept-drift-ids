from __future__ import annotations

import json
import subprocess
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
                    "replay_equivalence.rerun_seed": 0,
                    "replay_equivalence.historical_heads.phase_a_b": "bfa14b942e4a5b2fbfa8aa3c43728a7f1cd81645",
                    "replay_equivalence.historical_heads.correction_source": "79ddc4c6d6dea52c7cabc55a6d082448fc24fcf9",
                    "replay_equivalence.accepted_correction_manifest_sha256": "d380fce5f9db8f0b639dc999298a263b10a10a3d02e35def226a121d098e2222",
                    "replay_equivalence.accepted_stage8_evidence_commit": "c2ded83b8195b9321e715626c1f305f9627936e8",
                    "replay_equivalence.stage1_reconstructed_under_historical_environment": True,
                    "replay_equivalence.regenerated_correction_config_all_scientific_blocks_equal": True,
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
                "required_sha40_fields": [
                    "audited_head",
                    "same_head_stage9.head_sha",
                    "replay_equivalence.historical_heads.phase_a_b",
                    "replay_equivalence.historical_heads.correction_source",
                    "replay_equivalence.accepted_stage8_evidence_commit",
                ],
                "required_equal_fields": [
                    ["audited_head", "same_head_stage9.head_sha"]
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
        "audited_head": "b" * 40,
        "stage9_5_1": {
            "status": "closed",
            "identity_failures": 0,
            "external_artifact_blockers": 0,
        },
        "same_head_stage9": {"conclusion": "success", "head_sha": "b" * 40},
        "replay_equivalence": {
            "protocol_id": "stage9.5-6-replay-equivalence-correction-v1_1",
            "rerun_seed": 0,
            "historical_heads": {
                "phase_a_b": "bfa14b942e4a5b2fbfa8aa3c43728a7f1cd81645",
                "correction_source": "79ddc4c6d6dea52c7cabc55a6d082448fc24fcf9",
            },
            "accepted_correction_manifest_sha256": "d380fce5f9db8f0b639dc999298a263b10a10a3d02e35def226a121d098e2222",
            "accepted_stage8_evidence_commit": "c2ded83b8195b9321e715626c1f305f9627936e8",
            "stage1_reconstructed_under_historical_environment": True,
            "regenerated_correction_config_all_scientific_blocks_equal": True,
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

def test_same_head_mismatch_remains_locked(tmp_path: Path) -> None:
    closure = tmp_path / "closure.md"
    success_path = tmp_path / "success.json"
    payload = _success()
    payload["same_head_stage9"] = {
        "conclusion": "success",
        "head_sha": "c" * 40,
    }
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
    assert (
        "success_field_mismatch:audited_head!=same_head_stage9.head_sha"
        in report["failures"]
    )


def test_historical_replay_identity_mismatch_remains_locked(tmp_path: Path) -> None:
    closure = tmp_path / "closure.md"
    success_path = tmp_path / "success.json"
    payload = _success()
    replay = payload["replay_equivalence"]
    assert isinstance(replay, dict)
    replay["accepted_stage8_evidence_commit"] = "d" * 40
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
    assert (
        "success_value_mismatch:"
        "replay_equivalence.accepted_stage8_evidence_commit"
        in report["failures"]
    )

def test_git_ancestor_binding_accepts_current_head(tmp_path: Path) -> None:
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    contract_path = _contract(tmp_path)
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    contract["required_git_ancestor_fields"] = ["audited_head"]
    contract_path.write_text(json.dumps(contract), encoding="utf-8")

    closure = tmp_path / "closure.md"
    success_path = tmp_path / "success.json"
    payload = _success()
    payload["audited_head"] = head
    same_head = payload["same_head_stage9"]
    assert isinstance(same_head, dict)
    same_head["head_sha"] = head
    success_path.write_text(json.dumps(payload), encoding="utf-8")
    closure.write_text(
        "success.json\nstage9.5-6-replay-equivalence-correction-v1_1\n"
        + "a" * 64
        + "\n",
        encoding="utf-8",
    )

    report = evaluate(
        contract_path=contract_path,
        closure_doc=closure,
        success_json=success_path,
    )
    assert report["later_packages_unlocked"] is True
    assert report["failures"] == []


def test_git_ancestor_binding_rejects_unknown_sha(tmp_path: Path) -> None:
    contract_path = _contract(tmp_path)
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    contract["required_git_ancestor_fields"] = ["audited_head"]
    contract_path.write_text(json.dumps(contract), encoding="utf-8")

    closure = tmp_path / "closure.md"
    success_path = tmp_path / "success.json"
    payload = _success()
    unknown = "f" * 40
    payload["audited_head"] = unknown
    same_head = payload["same_head_stage9"]
    assert isinstance(same_head, dict)
    same_head["head_sha"] = unknown
    success_path.write_text(json.dumps(payload), encoding="utf-8")
    closure.write_text(
        "success.json\nstage9.5-6-replay-equivalence-correction-v1_1\n"
        + "a" * 64
        + "\n",
        encoding="utf-8",
    )

    report = evaluate(
        contract_path=contract_path,
        closure_doc=closure,
        success_json=success_path,
    )
    assert report["later_packages_unlocked"] is False
    assert "audited_head_not_ancestor:audited_head" in report["failures"]

