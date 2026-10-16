from __future__ import annotations

import json
import subprocess
from pathlib import Path

from tools.stage9_5.work_package_order_gate import _canonical_json_hash, evaluate


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
                    "stage9_5_1.audit_id": "stage9.5-1-fresh-clone-reconstruction-v1_2",
                    "stage9_5_1.pass": True,
                    "stage9_5_1.system_a_verified_seeds": [0, 1, 2, 3, 4],
                    "stage9_5_1.stage8_archive_requirement_count": 145,
                    "stage9_5_1.stage8_archive_verified_count": 145,
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
                    "artifact.report_canonical_sha256",
                    "stage9_5_1.report_canonical_sha256",
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
                    "recovery_report.json",
                    "replay_report.json",
                    "construction_contract.md",
                    "construction_contract.json",
                ],
                "closure_doc_must_contain_report_canonical_sha256": True,
                "required_canonical_json_reports": [
                    {
                        "path": "recovery_report.json",
                        "success_hash_field": "stage9_5_1.report_canonical_sha256",
                        "embedded_hash_field": "canonical_sha256",
                        "required_values": {
                            "audit_id": "stage9.5-1-fresh-clone-reconstruction-v1_2",
                            "status": "pass",
                            "pass": True,
                            "failures": [],
                            "blockers": [],
                            "external_artifacts.system_a_checkpoints.verified_seeds": [0, 1, 2, 3, 4],
                            "external_artifacts.stage8_large_artifact_archive.requirement_count": 145,
                            "external_artifacts.stage8_large_artifact_archive.verified_count": 145,
                        },
                        "required_report_ancestor_success_fields": [
                            ["repository_head", "audited_head"]
                        ],
                    },
                    {
                        "path": "replay_report.json",
                        "success_hash_field": "artifact.report_canonical_sha256",
                        "embedded_hash_field": "canonical_sha256",
                        "required_values": {
                            "audit_id": "stage9.5-6-clean-deterministic-full-seed-rerun-v1",
                            "status": "pass",
                            "pass": True,
                            "replay_equivalence.protocol_id": "stage9.5-6-replay-equivalence-correction-v1_1",
                            "replay_equivalence.rerun_seed": 0,
                            "replay_equivalence.phase_a_complete_seeds": [0, 1, 2, 3, 4],
                            "replay_equivalence.phase_b_complete_seeds": [0, 1, 2, 3, 4],
                            "replay_equivalence.original_phase_c_v1_seed0_failure_lineage_preserved": True,
                            "replay_equivalence.corrected_phase_c_seed0_rerun_complete": True,
                            "replay_equivalence.accepted_maintenance_archive_verified": True,
                            "replay_equivalence.stage1_reconstructed_under_historical_environment": True,
                            "replay_equivalence.regenerated_correction_config_all_scientific_blocks_equal": True,
                            "unresolved_class_a": [],
                            "scientific_objects_modified": False,
                            "stage10_outcomes_accessed": False,
                            "failures": [],
                            "blockers": [],
                            "construction.contract_id": "stage9.5-6-replay-report-construction-v1",
                            "construction.producer_id": "stage9.5-6-replay-equivalence-assurance-v1",
                            "construction.comparator_id": "stage9.5-6-replay-equivalence-comparator-v1",
                            "construction.finalizer_id": "stage9.5-6-replay-report-finalizer-v1",
                            "construction.manual_success_report_permitted": False,
                            "construction.deterministic_comparison_complete": True,
                            "construction.source_evidence_complete": True,
                            "construction.mismatch_count": 0,
                        },
                        "required_equal_success_fields": [
                            ["audited_head", "audited_head"]
                        ],
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    return path


def _success() -> dict[str, object]:
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    return {
        "audit_id": "stage9.5-6-clean-deterministic-full-seed-rerun-v1-success",
        "status": "accepted_stage9_5_6_closure_evidence",
        "audited_head": head,
        "stage9_5_1": {
            "status": "closed",
            "identity_failures": 0,
            "external_artifact_blockers": 0,
            "audit_id": "stage9.5-1-fresh-clone-reconstruction-v1_2",
            "pass": True,
            "system_a_verified_seeds": [0, 1, 2, 3, 4],
            "stage8_archive_requirement_count": 145,
            "stage8_archive_verified_count": 145,
            "report_canonical_sha256": "a" * 64,
        },
        "same_head_stage9": {"conclusion": "success", "head_sha": head},
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


def _write_recovery_report(
    tmp_path: Path,
    payload: dict[str, object],
    *,
    verified_count: int = 145,
) -> str:
    report: dict[str, object] = {
        "audit_id": "stage9.5-1-fresh-clone-reconstruction-v1_2",
        "status": "pass",
        "pass": True,
        "repository_head": payload["audited_head"],
        "failures": [],
        "blockers": [],
        "external_artifacts": {
            "system_a_checkpoints": {
                "verified_seeds": [0, 1, 2, 3, 4],
            },
            "stage8_large_artifact_archive": {
                "requirement_count": 145,
                "verified_count": verified_count,
            },
        },
    }
    canonical = _canonical_json_hash(report)
    report["canonical_sha256"] = canonical
    (tmp_path / "recovery_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    stage9_5_1 = payload["stage9_5_1"]
    assert isinstance(stage9_5_1, dict)
    stage9_5_1["report_canonical_sha256"] = canonical
    return canonical


def _write_replay_report(tmp_path: Path, payload: dict[str, object]) -> str:
    replay = payload["replay_equivalence"]
    assert isinstance(replay, dict)
    report: dict[str, object] = {
        "audit_id": "stage9.5-6-clean-deterministic-full-seed-rerun-v1",
        "status": "pass",
        "pass": True,
        "audited_head": payload["audited_head"],
        "failures": [],
        "blockers": [],
        "construction": {
            "contract_id": "stage9.5-6-replay-report-construction-v1",
            "producer_id": "stage9.5-6-replay-equivalence-assurance-v1",
            "comparator_id": "stage9.5-6-replay-equivalence-comparator-v1",
            "finalizer_id": "stage9.5-6-replay-report-finalizer-v1",
            "manual_success_report_permitted": False,
            "deterministic_comparison_complete": True,
            "source_evidence_complete": True,
            "mismatch_count": 0,
        },
        "replay_equivalence": json.loads(json.dumps(replay)),
        "unresolved_class_a": [],
        "scientific_objects_modified": False,
        "stage10_outcomes_accessed": False,
    }
    canonical = _canonical_json_hash(report)
    report["canonical_sha256"] = canonical
    (tmp_path / "replay_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    artifact = payload["artifact"]
    assert isinstance(artifact, dict)
    artifact["report_canonical_sha256"] = canonical
    return canonical


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
    recovery_hash = _write_recovery_report(tmp_path, payload)
    replay_hash = _write_replay_report(tmp_path, payload)
    success_path.write_text(json.dumps(payload), encoding="utf-8")
    closure.write_text(
        "success.json\n"
        "stage9.5-6-replay-equivalence-correction-v1_1\n"
        "recovery_report.json\n"
        "replay_report.json\n"
        "construction_contract.md\n"
        "construction_contract.json\n"
        + replay_hash
        + "\n"
        + recovery_hash
        + "\n",
        encoding="utf-8",
    )

    report = evaluate(
        contract_path=_contract(tmp_path),
        closure_doc=closure,
        success_json=success_path,
        evidence_root=tmp_path,
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
    recovery_hash = _write_recovery_report(tmp_path, payload)
    replay_hash = _write_replay_report(tmp_path, payload)
    success_path.write_text(json.dumps(payload), encoding="utf-8")
    closure.write_text(
        "success.json\n"
        "stage9.5-6-replay-equivalence-correction-v1_1\n"
        "recovery_report.json\n"
        "replay_report.json\n"
        "construction_contract.md\n"
        "construction_contract.json\n"
        + replay_hash
        + "\n"
        + recovery_hash
        + "\n",
        encoding="utf-8",
    )

    report = evaluate(
        contract_path=contract_path,
        closure_doc=closure,
        success_json=success_path,
        evidence_root=tmp_path,
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

def test_stage9_5_1_archive_verified_count_mismatch_remains_locked(
    tmp_path: Path,
) -> None:
    closure = tmp_path / "closure.md"
    success_path = tmp_path / "success.json"
    payload = _success()
    stage9_5_1 = payload["stage9_5_1"]
    assert isinstance(stage9_5_1, dict)
    stage9_5_1["stage8_archive_verified_count"] = 144
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
        "success_value_mismatch:stage9_5_1.stage8_archive_verified_count"
        in report["failures"]
    )


def test_unlinked_stage9_5_1_recovery_report_hash_remains_locked(
    tmp_path: Path,
) -> None:
    closure = tmp_path / "closure.md"
    success_path = tmp_path / "success.json"
    payload = _success()
    stage9_5_1 = payload["stage9_5_1"]
    assert isinstance(stage9_5_1, dict)
    stage9_5_1["report_canonical_sha256"] = "b" * 64
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
    assert "closure_doc_missing_report_canonical_sha256" in report["failures"]

def test_tampered_recovery_report_hash_remains_locked(tmp_path: Path) -> None:
    closure = tmp_path / "closure.md"
    success_path = tmp_path / "success.json"
    payload = _success()
    recovery_hash = _write_recovery_report(tmp_path, payload)
    report_path = tmp_path / "recovery_report.json"
    report_payload = json.loads(report_path.read_text(encoding="utf-8"))
    report_payload["status"] = "blocked"
    report_path.write_text(json.dumps(report_payload), encoding="utf-8")
    success_path.write_text(json.dumps(payload), encoding="utf-8")
    closure.write_text(
        "success.json\n"
        "stage9.5-6-replay-equivalence-correction-v1_1\n"
        "recovery_report.json\n"
        + "a" * 64
        + "\n"
        + recovery_hash
        + "\n",
        encoding="utf-8",
    )

    report = evaluate(
        contract_path=_contract(tmp_path),
        closure_doc=closure,
        success_json=success_path,
        evidence_root=tmp_path,
    )
    assert report["later_packages_unlocked"] is False
    assert "required_report_hash_mismatch:recovery_report.json" in report["failures"]


def test_raw_recovery_report_archive_count_mismatch_remains_locked(
    tmp_path: Path,
) -> None:
    closure = tmp_path / "closure.md"
    success_path = tmp_path / "success.json"
    payload = _success()
    recovery_hash = _write_recovery_report(
        tmp_path,
        payload,
        verified_count=144,
    )
    success_path.write_text(json.dumps(payload), encoding="utf-8")
    closure.write_text(
        "success.json\n"
        "stage9.5-6-replay-equivalence-correction-v1_1\n"
        "recovery_report.json\n"
        + "a" * 64
        + "\n"
        + recovery_hash
        + "\n",
        encoding="utf-8",
    )

    report = evaluate(
        contract_path=_contract(tmp_path),
        closure_doc=closure,
        success_json=success_path,
        evidence_root=tmp_path,
    )
    assert report["later_packages_unlocked"] is False
    assert (
        "required_report_value_mismatch:recovery_report.json:"
        "external_artifacts.stage8_large_artifact_archive.verified_count"
        in report["failures"]
    )

def test_missing_replay_report_remains_locked(tmp_path: Path) -> None:
    closure = tmp_path / "closure.md"
    success_path = tmp_path / "success.json"
    payload = _success()
    recovery_hash = _write_recovery_report(tmp_path, payload)
    success_path.write_text(json.dumps(payload), encoding="utf-8")
    closure.write_text(
        "success.json\n"
        "stage9.5-6-replay-equivalence-correction-v1_1\n"
        "recovery_report.json\n"
        "replay_report.json\n"
        + "a" * 64
        + "\n"
        + recovery_hash
        + "\n",
        encoding="utf-8",
    )

    report = evaluate(
        contract_path=_contract(tmp_path),
        closure_doc=closure,
        success_json=success_path,
        evidence_root=tmp_path,
    )
    assert report["later_packages_unlocked"] is False
    assert "required_report_missing:replay_report.json" in report["failures"]


def test_tampered_replay_report_hash_remains_locked(tmp_path: Path) -> None:
    closure = tmp_path / "closure.md"
    success_path = tmp_path / "success.json"
    payload = _success()
    recovery_hash = _write_recovery_report(tmp_path, payload)
    replay_hash = _write_replay_report(tmp_path, payload)
    report_path = tmp_path / "replay_report.json"
    report_payload = json.loads(report_path.read_text(encoding="utf-8"))
    replay = report_payload["replay_equivalence"]
    assert isinstance(replay, dict)
    replay["corrected_phase_c_seed0_rerun_complete"] = False
    report_path.write_text(json.dumps(report_payload), encoding="utf-8")
    success_path.write_text(json.dumps(payload), encoding="utf-8")
    closure.write_text(
        "success.json\n"
        "stage9.5-6-replay-equivalence-correction-v1_1\n"
        "recovery_report.json\n"
        "replay_report.json\n"
        "construction_contract.md\n"
        "construction_contract.json\n"
        + replay_hash
        + "\n"
        + recovery_hash
        + "\n",
        encoding="utf-8",
    )

    report = evaluate(
        contract_path=_contract(tmp_path),
        closure_doc=closure,
        success_json=success_path,
        evidence_root=tmp_path,
    )
    assert report["later_packages_unlocked"] is False
    assert "required_report_hash_mismatch:replay_report.json" in report["failures"]

def test_replay_report_audited_head_mismatch_remains_locked(
    tmp_path: Path,
) -> None:
    closure = tmp_path / "closure.md"
    success_path = tmp_path / "success.json"
    payload = _success()
    recovery_hash = _write_recovery_report(tmp_path, payload)
    replay_hash = _write_replay_report(tmp_path, payload)
    report_path = tmp_path / "replay_report.json"
    report_payload = json.loads(report_path.read_text(encoding="utf-8"))
    report_payload["audited_head"] = "c" * 40
    core = dict(report_payload)
    core.pop("canonical_sha256", None)
    tampered_hash = _canonical_json_hash(core)
    report_payload["canonical_sha256"] = tampered_hash
    report_path.write_text(
        json.dumps(report_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    artifact = payload["artifact"]
    assert isinstance(artifact, dict)
    artifact["report_canonical_sha256"] = tampered_hash
    success_path.write_text(json.dumps(payload), encoding="utf-8")
    closure.write_text(
        "success.json\n"
        "stage9.5-6-replay-equivalence-correction-v1_1\n"
        "recovery_report.json\n"
        "replay_report.json\n"
        + tampered_hash
        + "\n"
        + recovery_hash
        + "\n",
        encoding="utf-8",
    )

    report = evaluate(
        contract_path=_contract(tmp_path),
        closure_doc=closure,
        success_json=success_path,
        evidence_root=tmp_path,
    )
    assert report["later_packages_unlocked"] is False
    assert (
        "report_success_field_mismatch:replay_report.json:"
        "audited_head!=audited_head"
        in report["failures"]
    )


def test_replay_report_hidden_failure_remains_locked(tmp_path: Path) -> None:
    closure = tmp_path / "closure.md"
    success_path = tmp_path / "success.json"
    payload = _success()
    recovery_hash = _write_recovery_report(tmp_path, payload)
    _write_replay_report(tmp_path, payload)
    report_path = tmp_path / "replay_report.json"
    report_payload = json.loads(report_path.read_text(encoding="utf-8"))
    report_payload["failures"] = ["unexpected_replay_mismatch"]
    core = dict(report_payload)
    core.pop("canonical_sha256", None)
    tampered_hash = _canonical_json_hash(core)
    report_payload["canonical_sha256"] = tampered_hash
    report_path.write_text(
        json.dumps(report_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    artifact = payload["artifact"]
    assert isinstance(artifact, dict)
    artifact["report_canonical_sha256"] = tampered_hash
    success_path.write_text(json.dumps(payload), encoding="utf-8")
    closure.write_text(
        "success.json\n"
        "stage9.5-6-replay-equivalence-correction-v1_1\n"
        "recovery_report.json\n"
        "replay_report.json\n"
        + tampered_hash
        + "\n"
        + recovery_hash
        + "\n",
        encoding="utf-8",
    )

    report = evaluate(
        contract_path=_contract(tmp_path),
        closure_doc=closure,
        success_json=success_path,
        evidence_root=tmp_path,
    )
    assert report["later_packages_unlocked"] is False
    assert (
        "required_report_value_mismatch:replay_report.json:failures"
        in report["failures"]
    )

def test_report_path_escape_remains_locked(tmp_path: Path) -> None:
    evidence_root = tmp_path / "repo"
    evidence_root.mkdir()
    contract_path = _contract(evidence_root)
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    bindings = contract["required_canonical_json_reports"]
    assert isinstance(bindings, list)
    replay_binding = bindings[1]
    assert isinstance(replay_binding, dict)
    replay_binding["path"] = "../outside.json"
    contract_path.write_text(json.dumps(contract), encoding="utf-8")

    outside = tmp_path / "outside.json"
    outside.write_text("{}\n", encoding="utf-8")
    closure = evidence_root / "closure.md"
    success_path = evidence_root / "success.json"
    payload = _success()
    success_path.write_text(json.dumps(payload), encoding="utf-8")
    closure.write_text(
        "success.json\n"
        "stage9.5-6-replay-equivalence-correction-v1_1\n"
        "recovery_report.json\n"
        "../outside.json\n"
        + "a" * 64
        + "\n",
        encoding="utf-8",
    )

    report = evaluate(
        contract_path=contract_path,
        closure_doc=closure,
        success_json=success_path,
        evidence_root=evidence_root,
    )
    assert report["later_packages_unlocked"] is False
    assert "report_path_escapes_repository:../outside.json" in report["failures"]

def test_noncanonical_nan_replay_report_remains_locked(
    tmp_path: Path,
) -> None:
    closure = tmp_path / "closure.md"
    success_path = tmp_path / "success.json"
    payload = _success()
    recovery_hash = _write_recovery_report(tmp_path, payload)
    replay_hash = _write_replay_report(tmp_path, payload)

    report_path = tmp_path / "replay_report.json"
    report_payload = json.loads(report_path.read_text(encoding="utf-8"))
    report_payload["diagnostic_nan"] = float("nan")
    report_path.write_text(
        json.dumps(report_payload, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    success_path.write_text(json.dumps(payload), encoding="utf-8")
    closure.write_text(
        "success.json\n"
        "stage9.5-6-replay-equivalence-correction-v1_1\n"
        "recovery_report.json\n"
        "replay_report.json\n"
        "construction_contract.md\n"
        "construction_contract.json\n"
        + replay_hash
        + "\n"
        + recovery_hash
        + "\n",
        encoding="utf-8",
    )

    report = evaluate(
        contract_path=_contract(tmp_path),
        closure_doc=closure,
        success_json=success_path,
        evidence_root=tmp_path,
    )
    assert report["later_packages_unlocked"] is False
    assert (
        "required_report_not_canonicalizable:replay_report.json:ValueError"
        in report["failures"]
    )

def test_duplicate_json_key_replay_report_remains_locked(
    tmp_path: Path,
) -> None:
    closure = tmp_path / "closure.md"
    success_path = tmp_path / "success.json"
    payload = _success()
    recovery_hash = _write_recovery_report(tmp_path, payload)
    replay_hash = _write_replay_report(tmp_path, payload)

    report_path = tmp_path / "replay_report.json"
    raw = report_path.read_text(encoding="utf-8")
    raw = raw.replace(
        '"status": "pass",',
        '"status": "pass",\n  "status": "pass",',
        1,
    )
    report_path.write_text(raw, encoding="utf-8")

    success_path.write_text(json.dumps(payload), encoding="utf-8")
    closure.write_text(
        "success.json\n"
        "stage9.5-6-replay-equivalence-correction-v1_1\n"
        "recovery_report.json\n"
        "replay_report.json\n"
        "construction_contract.md\n"
        "construction_contract.json\n"
        + replay_hash
        + "\n"
        + recovery_hash
        + "\n",
        encoding="utf-8",
    )

    report = evaluate(
        contract_path=_contract(tmp_path),
        closure_doc=closure,
        success_json=success_path,
        evidence_root=tmp_path,
    )
    assert report["later_packages_unlocked"] is False
    assert (
        "required_report_invalid:replay_report.json:ValueError"
        in report["failures"]
    )

def test_recovery_report_head_not_in_replay_lineage_remains_locked(
    tmp_path: Path,
) -> None:
    closure = tmp_path / "closure.md"
    success_path = tmp_path / "success.json"
    payload = _success()
    recovery_hash = _write_recovery_report(tmp_path, payload)
    replay_hash = _write_replay_report(tmp_path, payload)

    report_path = tmp_path / "recovery_report.json"
    report_payload = json.loads(report_path.read_text(encoding="utf-8"))
    report_payload["repository_head"] = "f" * 40
    core = dict(report_payload)
    core.pop("canonical_sha256", None)
    tampered_hash = _canonical_json_hash(core)
    report_payload["canonical_sha256"] = tampered_hash
    report_path.write_text(
        json.dumps(report_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    stage9_5_1 = payload["stage9_5_1"]
    assert isinstance(stage9_5_1, dict)
    stage9_5_1["report_canonical_sha256"] = tampered_hash
    success_path.write_text(json.dumps(payload), encoding="utf-8")
    closure.write_text(
        "success.json\n"
        "stage9.5-6-replay-equivalence-correction-v1_1\n"
        "recovery_report.json\n"
        "replay_report.json\n"
        "construction_contract.md\n"
        "construction_contract.json\n"
        + replay_hash
        + "\n"
        + tampered_hash
        + "\n",
        encoding="utf-8",
    )

    report = evaluate(
        contract_path=_contract(tmp_path),
        closure_doc=closure,
        success_json=success_path,
        evidence_root=tmp_path,
    )
    assert report["later_packages_unlocked"] is False
    assert (
        "report_head_not_ancestor:recovery_report.json:"
        "repository_head->audited_head"
        in report["failures"]
    )

def test_duplicate_key_contract_returns_locked_decision(tmp_path: Path) -> None:
    contract_path = tmp_path / "contract.json"
    contract_path.write_text(
        '{"contract_id":"a","contract_id":"b"}\n',
        encoding="utf-8",
    )

    report = evaluate(
        contract_path=contract_path,
        closure_doc=tmp_path / "closure.md",
        success_json=tmp_path / "success.json",
        evidence_root=tmp_path,
    )
    assert report["later_packages_unlocked"] is False
    assert report["failures"] == ["contract_invalid:ValueError"]


def test_missing_required_contract_path_returns_locked_decision(
    tmp_path: Path,
) -> None:
    contract_path = tmp_path / "contract.json"
    contract_path.write_text(
        json.dumps(
            {
                "contract_id": "test-gate",
                "closure_doc_path": "closure.md",
            }
        ),
        encoding="utf-8",
    )

    report = evaluate(
        contract_path=contract_path,
        evidence_root=tmp_path,
    )
    assert report["later_packages_unlocked"] is False
    assert report["failures"] == ["contract_missing_field:success_json_path"]

def test_contract_required_mapping_wrong_type_returns_locked_decision(
    tmp_path: Path,
) -> None:
    contract_path = _contract(tmp_path)
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    contract["required_success_values"] = []
    contract_path.write_text(json.dumps(contract), encoding="utf-8")

    report = evaluate(
        contract_path=contract_path,
        evidence_root=tmp_path,
    )
    assert report["later_packages_unlocked"] is False
    assert report["failures"] == [
        "contract_invalid_field_type:required_success_values"
    ]


def test_contract_string_list_rejects_non_string_item(
    tmp_path: Path,
) -> None:
    contract_path = _contract(tmp_path)
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    contract["required_success_hash_fields"] = [
        "artifact.report_canonical_sha256",
        7,
    ]
    contract_path.write_text(json.dumps(contract), encoding="utf-8")

    report = evaluate(
        contract_path=contract_path,
        evidence_root=tmp_path,
    )
    assert report["later_packages_unlocked"] is False
    assert report["failures"] == [
        "contract_invalid_list_item:required_success_hash_fields"
    ]

def test_manual_replay_success_override_remains_locked(tmp_path: Path) -> None:
    closure = tmp_path / "closure.md"
    success_path = tmp_path / "success.json"
    payload = _success()
    recovery_hash = _write_recovery_report(tmp_path, payload)
    _write_replay_report(tmp_path, payload)

    report_path = tmp_path / "replay_report.json"
    report_payload = json.loads(report_path.read_text(encoding="utf-8"))
    construction = report_payload["construction"]
    assert isinstance(construction, dict)
    construction["manual_success_report_permitted"] = True
    core = dict(report_payload)
    core.pop("canonical_sha256", None)
    tampered_hash = _canonical_json_hash(core)
    report_payload["canonical_sha256"] = tampered_hash
    report_path.write_text(
        json.dumps(report_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    artifact = payload["artifact"]
    assert isinstance(artifact, dict)
    artifact["report_canonical_sha256"] = tampered_hash
    success_path.write_text(json.dumps(payload), encoding="utf-8")
    closure.write_text(
        "success.json\n"
        "stage9.5-6-replay-equivalence-correction-v1_1\n"
        "recovery_report.json\n"
        "replay_report.json\n"
        "construction_contract.md\n"
        "construction_contract.json\n"
        + tampered_hash
        + "\n"
        + recovery_hash
        + "\n",
        encoding="utf-8",
    )

    report = evaluate(
        contract_path=_contract(tmp_path),
        closure_doc=closure,
        success_json=success_path,
        evidence_root=tmp_path,
    )
    assert report["later_packages_unlocked"] is False
    assert (
        "required_report_value_mismatch:replay_report.json:"
        "construction.manual_success_report_permitted"
        in report["failures"]
    )


def test_nonzero_replay_mismatch_count_remains_locked(tmp_path: Path) -> None:
    closure = tmp_path / "closure.md"
    success_path = tmp_path / "success.json"
    payload = _success()
    recovery_hash = _write_recovery_report(tmp_path, payload)
    _write_replay_report(tmp_path, payload)

    report_path = tmp_path / "replay_report.json"
    report_payload = json.loads(report_path.read_text(encoding="utf-8"))
    construction = report_payload["construction"]
    assert isinstance(construction, dict)
    construction["mismatch_count"] = 1
    core = dict(report_payload)
    core.pop("canonical_sha256", None)
    tampered_hash = _canonical_json_hash(core)
    report_payload["canonical_sha256"] = tampered_hash
    report_path.write_text(
        json.dumps(report_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    artifact = payload["artifact"]
    assert isinstance(artifact, dict)
    artifact["report_canonical_sha256"] = tampered_hash
    success_path.write_text(json.dumps(payload), encoding="utf-8")
    closure.write_text(
        "success.json\n"
        "stage9.5-6-replay-equivalence-correction-v1_1\n"
        "recovery_report.json\n"
        "replay_report.json\n"
        "construction_contract.md\n"
        "construction_contract.json\n"
        + tampered_hash
        + "\n"
        + recovery_hash
        + "\n",
        encoding="utf-8",
    )

    report = evaluate(
        contract_path=_contract(tmp_path),
        closure_doc=closure,
        success_json=success_path,
        evidence_root=tmp_path,
    )
    assert report["later_packages_unlocked"] is False
    assert (
        "required_report_value_mismatch:replay_report.json:"
        "construction.mismatch_count"
        in report["failures"]
    )

