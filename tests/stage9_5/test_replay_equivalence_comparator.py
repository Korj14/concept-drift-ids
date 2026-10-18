from __future__ import annotations

import copy
import gzip
import hashlib
import json
from pathlib import Path
from typing import Any

import tools.stage9_5.replay_equivalence_comparator as comparator_module
from tools.stage9_5.replay_equivalence_comparator import (
    ARM_NAMES,
    NORMALIZED_DIAGNOSTIC,
    PHASE_B_RECORD_TIMING_FIELDS,
    PHASE_C_BOUNDARY_INDEX,
    PHASE_C_STREAM_ROWS,
    _blocked_phase_c_output_for_dependencies,
    _canonical_sha256,
    _project_phase_a_manifest,
    _project_phase_b_maintenance_record,
    _git_head,
    _verify_phase_c_failed_lineage,
    _verify_stage1_reconstruction_report,
    _verify_stage9_5_1_recovery_report,
    compare_phase_a_seed,
    compare_phase_b,
    compare_phase_b_arm,
    compare_phase_b_maintenance_jsonl,
    compare_phase_b_seed,
    compare_phase_c_corrected_output,
    compare_phase_c_preconditions,
    run_integrated,
)


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_phase_a_fixture(
    root: Path,
    *,
    platform: str = "platform-a",
    processor: str = "processor-a",
    filepath: str = "C:/env/lib.dll",
    python_version: str = "3.11.9",
    file_bytes: bytes = b'{"row":1}\n',
) -> dict[str, Any]:
    root.mkdir(parents=True)
    data_path = root / "predictions.jsonl"
    data_path.write_bytes(file_bytes)

    core: dict[str, Any] = {
        "schema_version": 1,
        "run_id": "cd-primary-v1-phase-a-seed-0",
        "seed": 0,
        "arm": "shared_control_plane",
        "git_commit": "bfa14b942e4a5b2fbfa8aa3c43728a7f1cd81645",
        "protocol_hashes": {"protocol": "a" * 64},
        "runtime": {
            "platform": platform,
            "processor": processor,
            "python_implementation": "CPython",
            "python_version": python_version,
            "thread_environment": {
                "OMP_NUM_THREADS": "1",
            },
            "threadpool_info": [
                {
                    "filepath": filepath,
                    "internal_api": "openblas",
                    "num_threads": 1,
                    "version": "0.3.31",
                }
            ],
        },
        "scenario_identity": {
            "primary_config_manifest_sha256": "b" * 64,
            "adaptive_runner_received_boundary_metadata": False,
        },
        "initial_checkpoint_sha256": "c" * 64,
        "preprocessing_sha256": "d" * 64,
        "files": {
            "predictions": {
                "path": "predictions.jsonl",
                "sha256": _sha256_file(data_path),
            }
        },
        "status": "complete_unscored_shared_trajectory",
    }
    body = dict(core)
    body["manifest_sha256"] = _canonical_sha256(core)
    body["payload_sha256"] = _canonical_sha256(body)
    (root / "run_manifest.json").write_text(
        json.dumps(body, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return body


def test_phase_a_projection_normalizes_only_frozen_runtime_diagnostics(
    tmp_path: Path,
) -> None:
    accepted = _write_phase_a_fixture(
        tmp_path / "accepted",
        platform="Windows-A",
        processor="CPU-A",
        filepath="C:/accepted/lib.dll",
    )
    fresh = _write_phase_a_fixture(
        tmp_path / "fresh",
        platform="Windows-B",
        processor="CPU-B",
        filepath="D:/fresh/lib.dll",
    )

    result = compare_phase_a_seed(
        accepted_seed_root=tmp_path / "accepted",
        fresh_seed_root=tmp_path / "fresh",
        seed=0,
    )

    assert result["pass"] is True
    assert result["mismatch_count"] == 0
    assert result["failures"] == []
    assert (
        result["accepted_projected_sha256"]
        == result["fresh_projected_sha256"]
    )
    projected = _project_phase_a_manifest(accepted)
    assert projected["runtime"]["platform"] == NORMALIZED_DIAGNOSTIC
    assert projected["runtime"]["processor"] == NORMALIZED_DIAGNOSTIC
    assert (
        projected["runtime"]["threadpool_info"][0]["filepath"]
        == NORMALIZED_DIAGNOSTIC
    )
    assert "manifest_sha256" not in projected
    assert "payload_sha256" not in projected


def test_phase_a_projection_rejects_non_diagnostic_runtime_change(
    tmp_path: Path,
) -> None:
    _write_phase_a_fixture(tmp_path / "accepted", python_version="3.11.9")
    _write_phase_a_fixture(tmp_path / "fresh", python_version="3.11.10")

    result = compare_phase_a_seed(
        accepted_seed_root=tmp_path / "accepted",
        fresh_seed_root=tmp_path / "fresh",
        seed=0,
    )

    assert result["pass"] is False
    assert "runtime.python_version" in result["mismatches"]


def test_phase_a_comparator_rejects_descriptor_linked_byte_mismatch(
    tmp_path: Path,
) -> None:
    _write_phase_a_fixture(tmp_path / "accepted")
    _write_phase_a_fixture(tmp_path / "fresh")
    (tmp_path / "fresh" / "predictions.jsonl").write_bytes(b"tampered\n")

    result = compare_phase_a_seed(
        accepted_seed_root=tmp_path / "accepted",
        fresh_seed_root=tmp_path / "fresh",
        seed=0,
    )

    assert result["pass"] is False
    assert "fresh:file_sha256_mismatch:predictions" in result["failures"]


def test_phase_a_comparator_rejects_forged_manifest_self_hash(
    tmp_path: Path,
) -> None:
    _write_phase_a_fixture(tmp_path / "accepted")
    fresh = _write_phase_a_fixture(tmp_path / "fresh")
    fresh["manifest_sha256"] = "e" * 64
    fresh["payload_sha256"] = _canonical_sha256(
        {k: v for k, v in fresh.items() if k != "payload_sha256"}
    )
    (tmp_path / "fresh" / "run_manifest.json").write_text(
        json.dumps(fresh, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = compare_phase_a_seed(
        accepted_seed_root=tmp_path / "accepted",
        fresh_seed_root=tmp_path / "fresh",
        seed=0,
    )

    assert result["pass"] is False
    assert "fresh:manifest_sha256_mismatch" in result["failures"]

def _write_json_bytes(path: Path, payload: dict[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return _sha256_file(path)


def _phase_a_shared_identity_map() -> dict[str, str]:
    return {str(seed): str(seed + 1) * 64 for seed in range(5)}


def _verified_phase_a_result() -> dict[str, Any]:
    return {
        "pass": True,
        "complete_seeds": [0, 1, 2, 3, 4],
        "mismatch_count": 0,
        "failures": [],
        "shared_identity_by_seed": _phase_a_shared_identity_map(),
    }


def _write_phase_b_arm_fixture(
    root: Path,
    *,
    arm: str,
    seed: int = 0,
    timing_scale: float = 1.0,
    scientific_value: str = "stable",
    state_value: str = "same-state",
    shared_identity_sha256: str = "1" * 64,
) -> dict[str, Any]:
    root.mkdir(parents=True, exist_ok=True)
    initial_sha = _write_json_bytes(
        root / "initial_state.json",
        {"state": state_value},
    )
    final_sha = _write_json_bytes(
        root / "final_state.json",
        {"state": state_value},
    )
    maintenance_records = [
        {
            "arm": arm,
            "opportunity_id": 1,
            "opportunity_clock": 100,
            "status": scientific_value,
            "neural_checkpoint_sha256": "a" * 64,
            "generation_evidence_id": "b" * 64,
            "generation_row_ids": ["r1", "r2"],
            "validation_row_ids": ["r3"],
            "validation_completion_clock": 120,
            "symbolic_publication_effective_index": 121,
            "parent_rule_base_version_id": "r0",
            "result_rule_base_version_id": "r1",
            "parent_rule_base_sha256": "c" * 64,
            "result_rule_base_sha256": "d" * 64,
            "history_sha256": "e" * 64,
            "candidate_count": 2,
            "shap_seconds": 1.0 * timing_scale,
            "surrogate_seconds": 2.0 * timing_scale,
            "lifecycle_seconds": 3.0 * timing_scale,
            "validation_wait_rows": 20,
            "generation_payload": {
                "generation_evidence_id": "b" * 64,
                "scientific_value": "same",
                "timing_seconds": {
                    "shap": 1.0 * timing_scale,
                    "surrogate": 2.0 * timing_scale,
                },
            },
            "lifecycle": None,
        }
    ]
    maintenance_path = root / "maintenance.jsonl"
    maintenance_path.write_text(
        "".join(
            json.dumps(item, sort_keys=True, separators=(",", ":")) + "\n"
            for item in maintenance_records
        ),
        encoding="utf-8",
    )
    maintenance_sha = _sha256_file(maintenance_path)

    compute = 6.0 * timing_scale
    core: dict[str, Any] = {
        "schema_version": 1,
        "seed": seed,
        "arm": arm,
        "operator_config_sha256": "f" * 64,
        "shared_identity_sha256": shared_identity_sha256,
        "initial_rule_base_version_id": "r0",
        "initial_rule_base_sha256": "2" * 64,
        "final_rule_base_version_id": "r1",
        "final_rule_base_sha256": "3" * 64,
        "final_history_sha256": "4" * 64,
        "publications": [],
        "maintenance_summary": {
            "opportunity_count": 1,
            "completed_validation_count": 1,
            "publication_count": 1,
            "no_op_count": 0,
            "censored_or_blocked_count": 0,
            "candidate_count": 2,
            "publication_per_opportunity": 1.0,
            "compute_seconds": compute,
            "shap_seconds": 1.0 * timing_scale,
            "surrogate_seconds": 2.0 * timing_scale,
            "lifecycle_seconds": 3.0 * timing_scale,
            "compute_seconds_per_opportunity": compute,
            "compute_seconds_per_publication": compute,
            "mean_validation_wait_rows": 20.0,
            "lifecycle_decision_counts": {"retained": 1},
        },
        "files": {
            "initial_state": {
                "path": "initial_state.json",
                "sha256": initial_sha,
            },
            "final_state": {
                "path": "final_state.json",
                "sha256": final_sha,
            },
            "maintenance": {
                "path": "maintenance.jsonl",
                "sha256": maintenance_sha,
            },
        },
    }
    body = dict(core)
    body["manifest_sha256"] = _canonical_sha256(core)
    body["payload_sha256"] = _canonical_sha256(body)
    _write_json_bytes(root / "arm_manifest.json", body)
    return body


def _rewrite_phase_b_arm_manifest(
    root: Path,
    payload: dict[str, Any],
) -> dict[str, Any]:
    body = copy.deepcopy(payload)
    body.pop("payload_sha256", None)
    body.pop("manifest_sha256", None)
    body["manifest_sha256"] = _canonical_sha256(body)
    body["payload_sha256"] = _canonical_sha256(body)
    _write_json_bytes(root / "arm_manifest.json", body)
    return body


def _read_phase_b_maintenance_records(root: Path) -> list[dict[str, Any]]:
    path = root / "maintenance.jsonl"
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line
    ]


def _write_phase_b_maintenance_records(
    root: Path,
    payload: dict[str, Any],
    records: list[dict[str, Any]],
    *,
    recompute_manifest_hash: bool,
) -> dict[str, Any]:
    path = root / "maintenance.jsonl"
    path.write_text(
        "".join(
            json.dumps(item, sort_keys=True, separators=(",", ":")) + "\n"
            for item in records
        ),
        encoding="utf-8",
    )
    body = copy.deepcopy(payload)
    files = body["files"]
    assert isinstance(files, dict)
    maintenance = files["maintenance"]
    assert isinstance(maintenance, dict)
    maintenance["sha256"] = _sha256_file(path)

    if recompute_manifest_hash:
        return _rewrite_phase_b_arm_manifest(root, body)

    # Deliberately preserve the stale manifest_sha256 to test the frozen
    # transitive dependency from maintenance bytes into the arm manifest.
    body["payload_sha256"] = _canonical_sha256(
        {key: value for key, value in body.items() if key != "payload_sha256"}
    )
    _write_json_bytes(root / "arm_manifest.json", body)
    return body


def _add_phase_b_version_descriptor(
    root: Path,
    payload: dict[str, Any],
    *,
    rule_value: str,
) -> dict[str, Any]:
    version_path = root / "versions" / "0001-d-s0-v0001.json"
    version_sha = _write_json_bytes(
        version_path,
        {"effective_index": 100, "state": {"rule": rule_value}},
    )
    body = copy.deepcopy(payload)
    files = body["files"]
    assert isinstance(files, dict)
    files["version_0001"] = {
        "path": "versions/0001-d-s0-v0001.json",
        "sha256": version_sha,
    }
    return _rewrite_phase_b_arm_manifest(root, body)


def _write_phase_b_seed_fixture(
    root: Path,
    *,
    seed: int = 0,
    timing_scale: float = 1.0,
    arm_isolation_sha256: str = "5" * 64,
) -> dict[str, Any]:
    root.mkdir(parents=True, exist_ok=True)
    phase_a_map = _phase_a_shared_identity_map()
    shared_identity_sha256 = phase_a_map[str(seed)]
    arms: dict[str, dict[str, str]] = {}
    for arm in ("c_frozen_symbolic", "d_drift", "d_periodic"):
        manifest = _write_phase_b_arm_fixture(
            root / arm,
            arm=arm,
            seed=seed,
            timing_scale=timing_scale,
            shared_identity_sha256=shared_identity_sha256,
        )
        arm_path = root / arm / "arm_manifest.json"
        arms[arm] = {
            "path": f"{arm}/arm_manifest.json",
            "sha256": _sha256_file(arm_path),
            "manifest_sha256": str(manifest["manifest_sha256"]),
        }

    core: dict[str, Any] = {
        "schema_version": 1,
        "run_id": f"cd-primary-v1-phase-b-seed-{seed}",
        "seed": seed,
        "git_commit": "bfa14b942e4a5b2fbfa8aa3c43728a7f1cd81645",
        "status": "complete_unscored_symbolic_trajectories",
        "primary_config_manifest_sha256": "6" * 64,
        "shared_identity_sha256": shared_identity_sha256,
        "all_phase_a_shared_identity_sha256": phase_a_map,
        "operator_config_sha256": "f" * 64,
        "arm_isolation_sha256": arm_isolation_sha256,
        "arms": arms,
        "primary_boundary_scored": False,
    }
    body = dict(core)
    body["manifest_sha256"] = _canonical_sha256(core)
    body["payload_sha256"] = _canonical_sha256(body)
    _write_json_bytes(root / "phase_b_manifest.json", body)
    return body


def test_phase_b_arm_accepts_only_predeclared_timing_differences(
    tmp_path: Path,
) -> None:
    _write_phase_b_arm_fixture(
        tmp_path / "accepted",
        arm="d_drift",
        timing_scale=1.0,
    )
    _write_phase_b_arm_fixture(
        tmp_path / "fresh",
        arm="d_drift",
        timing_scale=9.0,
    )

    result = compare_phase_b_arm(
        accepted_arm_root=tmp_path / "accepted",
        fresh_arm_root=tmp_path / "fresh",
        seed=0,
        arm="d_drift",
    )

    assert result["pass"] is True
    assert result["mismatch_count"] == 0
    assert result["failures"] == []


def test_phase_b_arm_rejects_scientific_maintenance_change(
    tmp_path: Path,
) -> None:
    _write_phase_b_arm_fixture(
        tmp_path / "accepted",
        arm="d_drift",
        scientific_value="same",
    )
    _write_phase_b_arm_fixture(
        tmp_path / "fresh",
        arm="d_drift",
        scientific_value="changed",
    )

    result = compare_phase_b_arm(
        accepted_arm_root=tmp_path / "accepted",
        fresh_arm_root=tmp_path / "fresh",
        seed=0,
        arm="d_drift",
    )

    assert result["pass"] is False
    assert any(
        path.endswith(".status")
        for path in result["mismatches"]
    )


def test_phase_b_arm_rejects_nonmaintenance_state_change(
    tmp_path: Path,
) -> None:
    _write_phase_b_arm_fixture(
        tmp_path / "accepted",
        arm="d_periodic",
        state_value="accepted",
    )
    _write_phase_b_arm_fixture(
        tmp_path / "fresh",
        arm="d_periodic",
        state_value="fresh",
    )

    result = compare_phase_b_arm(
        accepted_arm_root=tmp_path / "accepted",
        fresh_arm_root=tmp_path / "fresh",
        seed=0,
        arm="d_periodic",
    )

    assert result["pass"] is False
    assert (
        "nonmaintenance_file_descriptor_mismatch:initial_state"
        in result["failures"]
    )


def test_phase_b_arm_rejects_forged_manifest_self_hash_before_projection(
    tmp_path: Path,
) -> None:
    _write_phase_b_arm_fixture(
        tmp_path / "accepted",
        arm="d_drift",
    )
    fresh = _write_phase_b_arm_fixture(
        tmp_path / "fresh",
        arm="d_drift",
    )
    fresh["manifest_sha256"] = "9" * 64
    fresh["payload_sha256"] = _canonical_sha256(
        {key: value for key, value in fresh.items() if key != "payload_sha256"}
    )
    _write_json_bytes(tmp_path / "fresh" / "arm_manifest.json", fresh)

    result = compare_phase_b_arm(
        accepted_arm_root=tmp_path / "accepted",
        fresh_arm_root=tmp_path / "fresh",
        seed=0,
        arm="d_drift",
    )

    assert result["pass"] is False
    assert "fresh_arm:manifest_sha256_mismatch" in result["failures"]


def test_phase_b_arm_keeps_version_descriptor_hash_exact(
    tmp_path: Path,
) -> None:
    accepted_root = tmp_path / "accepted"
    fresh_root = tmp_path / "fresh"
    accepted = _write_phase_b_arm_fixture(
        accepted_root,
        arm="d_drift",
    )
    fresh = _write_phase_b_arm_fixture(
        fresh_root,
        arm="d_drift",
    )

    accepted_version = accepted_root / "versions" / "0001-d-s0-v0001.json"
    fresh_version = fresh_root / "versions" / "0001-d-s0-v0001.json"
    accepted_sha = _write_json_bytes(
        accepted_version,
        {"effective_index": 100, "state": {"rule": "accepted"}},
    )
    fresh_sha = _write_json_bytes(
        fresh_version,
        {"effective_index": 100, "state": {"rule": "fresh"}},
    )

    accepted_files = accepted["files"]
    fresh_files = fresh["files"]
    assert isinstance(accepted_files, dict)
    assert isinstance(fresh_files, dict)
    accepted_files["version_0001"] = {
        "path": "versions/0001-d-s0-v0001.json",
        "sha256": accepted_sha,
    }
    fresh_files["version_0001"] = {
        "path": "versions/0001-d-s0-v0001.json",
        "sha256": fresh_sha,
    }
    _rewrite_phase_b_arm_manifest(accepted_root, accepted)
    _rewrite_phase_b_arm_manifest(fresh_root, fresh)

    result = compare_phase_b_arm(
        accepted_arm_root=accepted_root,
        fresh_arm_root=fresh_root,
        seed=0,
        arm="d_drift",
    )

    assert result["pass"] is False
    assert (
        "nonmaintenance_file_descriptor_mismatch:version_0001"
        in result["failures"]
    )


def test_phase_b_seed_removes_only_timing_dependent_arm_hashes(
    tmp_path: Path,
) -> None:
    _write_phase_b_seed_fixture(
        tmp_path / "accepted",
        timing_scale=1.0,
    )
    _write_phase_b_seed_fixture(
        tmp_path / "fresh",
        timing_scale=7.0,
    )

    result = compare_phase_b_seed(
        accepted_seed_root=tmp_path / "accepted",
        fresh_seed_root=tmp_path / "fresh",
        seed=0,
        phase_a_result=_verified_phase_a_result(),
    )

    assert result["pass"] is True
    assert result["mismatch_count"] == 0
    assert result["failures"] == []


def test_phase_b_seed_keeps_arm_isolation_identity_exact(
    tmp_path: Path,
) -> None:
    _write_phase_b_seed_fixture(
        tmp_path / "accepted",
        arm_isolation_sha256="5" * 64,
    )
    _write_phase_b_seed_fixture(
        tmp_path / "fresh",
        arm_isolation_sha256="7" * 64,
    )

    result = compare_phase_b_seed(
        accepted_seed_root=tmp_path / "accepted",
        fresh_seed_root=tmp_path / "fresh",
        seed=0,
        phase_a_result=_verified_phase_a_result(),
    )

    assert result["pass"] is False
    assert "phase_b_manifest.arm_isolation_sha256" in result["mismatches"]

def _rewrite_phase_b_seed_manifest(
    root: Path,
    payload: dict[str, Any],
) -> None:
    body = dict(payload)
    body.pop("payload_sha256", None)
    body.pop("manifest_sha256", None)
    body["manifest_sha256"] = _canonical_sha256(body)
    body["payload_sha256"] = _canonical_sha256(body)
    _write_json_bytes(root / "phase_b_manifest.json", body)


def test_phase_b_seed_rejects_forged_arm_manifest_identity(
    tmp_path: Path,
) -> None:
    _write_phase_b_seed_fixture(tmp_path / "accepted")
    fresh = _write_phase_b_seed_fixture(tmp_path / "fresh")
    arms = fresh["arms"]
    assert isinstance(arms, dict)
    descriptor = arms["d_drift"]
    assert isinstance(descriptor, dict)
    descriptor["manifest_sha256"] = "9" * 64
    _rewrite_phase_b_seed_manifest(tmp_path / "fresh", fresh)

    result = compare_phase_b_seed(
        accepted_seed_root=tmp_path / "accepted",
        fresh_seed_root=tmp_path / "fresh",
        seed=0,
        phase_a_result=_verified_phase_a_result(),
    )

    assert result["pass"] is False
    assert (
        "fresh:d_drift:arm_manifest_identity_mismatch"
        in result["failures"]
    )


def test_phase_b_seed_rejects_redirected_arm_descriptor_path(
    tmp_path: Path,
) -> None:
    _write_phase_b_seed_fixture(tmp_path / "accepted")
    fresh = _write_phase_b_seed_fixture(tmp_path / "fresh")
    arms = fresh["arms"]
    assert isinstance(arms, dict)
    descriptor = arms["d_drift"]
    assert isinstance(descriptor, dict)
    redirected = tmp_path / "fresh" / "d_periodic" / "arm_manifest.json"
    redirected_payload = json.loads(redirected.read_text(encoding="utf-8"))
    descriptor["path"] = "d_periodic/arm_manifest.json"
    descriptor["sha256"] = _sha256_file(redirected)
    descriptor["manifest_sha256"] = str(
        redirected_payload["manifest_sha256"]
    )
    _rewrite_phase_b_seed_manifest(tmp_path / "fresh", fresh)

    result = compare_phase_b_seed(
        accepted_seed_root=tmp_path / "accepted",
        fresh_seed_root=tmp_path / "fresh",
        seed=0,
        phase_a_result=_verified_phase_a_result(),
    )

    assert result["pass"] is False
    assert "phase_b_manifest.arms.d_drift.path" in result["mismatches"]

def test_phase_b_seed_rejects_missing_required_arm(
    tmp_path: Path,
) -> None:
    _write_phase_b_seed_fixture(tmp_path / "accepted")
    fresh = _write_phase_b_seed_fixture(tmp_path / "fresh")
    arms = fresh["arms"]
    assert isinstance(arms, dict)
    arms.pop("d_periodic")
    _rewrite_phase_b_seed_manifest(tmp_path / "fresh", fresh)

    result = compare_phase_b_seed(
        accepted_seed_root=tmp_path / "accepted",
        fresh_seed_root=tmp_path / "fresh",
        seed=0,
        phase_a_result=_verified_phase_a_result(),
    )

    assert result["pass"] is False
    assert "fresh:arm_key_set_mismatch" in result["failures"]
    assert "fresh:missing_arm_descriptor:d_periodic" in result["failures"]


def test_phase_b_seed_rejects_extra_arm(
    tmp_path: Path,
) -> None:
    _write_phase_b_seed_fixture(tmp_path / "accepted")
    fresh = _write_phase_b_seed_fixture(tmp_path / "fresh")
    arms = fresh["arms"]
    assert isinstance(arms, dict)
    arms["unexpected_arm"] = copy.deepcopy(arms["c_frozen_symbolic"])
    _rewrite_phase_b_seed_manifest(tmp_path / "fresh", fresh)

    result = compare_phase_b_seed(
        accepted_seed_root=tmp_path / "accepted",
        fresh_seed_root=tmp_path / "fresh",
        seed=0,
        phase_a_result=_verified_phase_a_result(),
    )

    assert result["pass"] is False
    assert "fresh:arm_key_set_mismatch" in result["failures"]


def test_phase_b_seed_rejects_incomplete_phase_a_aggregate(
    tmp_path: Path,
) -> None:
    _write_phase_b_seed_fixture(tmp_path / "accepted")
    _write_phase_b_seed_fixture(tmp_path / "fresh")
    phase_a = _verified_phase_a_result()
    phase_a["complete_seeds"] = [0, 1, 2, 3]

    result = compare_phase_b_seed(
        accepted_seed_root=tmp_path / "accepted",
        fresh_seed_root=tmp_path / "fresh",
        seed=0,
        phase_a_result=phase_a,
    )

    assert result["pass"] is False
    assert "verified_phase_a_complete_seeds_mismatch" in result["failures"]


def test_phase_b_seed_rejects_phase_a_shared_identity_mismatch(
    tmp_path: Path,
) -> None:
    _write_phase_b_seed_fixture(tmp_path / "accepted")
    fresh = _write_phase_b_seed_fixture(tmp_path / "fresh")
    fresh["shared_identity_sha256"] = "a" * 64
    _rewrite_phase_b_seed_manifest(tmp_path / "fresh", fresh)

    result = compare_phase_b_seed(
        accepted_seed_root=tmp_path / "accepted",
        fresh_seed_root=tmp_path / "fresh",
        seed=0,
        phase_a_result=_verified_phase_a_result(),
    )

    assert result["pass"] is False
    assert "fresh:phase_a_shared_identity_binding_mismatch" in result["failures"]


def test_phase_b_seed_requires_accepted_maintenance_archive_no_summary_fallback(
    tmp_path: Path,
) -> None:
    _write_phase_b_seed_fixture(tmp_path / "accepted")
    _write_phase_b_seed_fixture(tmp_path / "fresh")
    (tmp_path / "accepted" / "d_drift" / "maintenance.jsonl").unlink()

    result = compare_phase_b_seed(
        accepted_seed_root=tmp_path / "accepted",
        fresh_seed_root=tmp_path / "fresh",
        seed=0,
        phase_a_result=_verified_phase_a_result(),
    )

    assert result["pass"] is False
    assert any(
        "d_drift:accepted_arm:missing_file:maintenance" in failure
        or "d_drift:maintenance:accepted_maintenance_invalid" in failure
        for failure in result["failures"]
    )


def test_phase_b_all_five_seeds_integrate_three_verified_arms(
    tmp_path: Path,
) -> None:
    accepted_root = tmp_path / "accepted"
    fresh_root = tmp_path / "fresh"
    for seed in range(5):
        _write_phase_b_seed_fixture(
            accepted_root / "phase_b_symbolic_arms" / f"seed-{seed}",
            seed=seed,
            timing_scale=1.0,
        )
        _write_phase_b_seed_fixture(
            fresh_root / "phase_b_symbolic_arms" / f"seed-{seed}",
            seed=seed,
            timing_scale=9.0,
        )

    result = compare_phase_b(
        accepted_root=accepted_root,
        fresh_root=fresh_root,
        phase_a_result=_verified_phase_a_result(),
    )

    assert result["pass"] is True
    assert result["complete_seeds"] == [0, 1, 2, 3, 4]
    assert result["accepted_maintenance_archive_verified"] is True
    assert all(
        set(item["verified_projected_arm_sha256"]) == set(ARM_NAMES)
        for item in result["seed_results"]
    )


def test_phase_b_all_five_seeds_fail_closed_when_one_seed_missing(
    tmp_path: Path,
) -> None:
    accepted_root = tmp_path / "accepted"
    fresh_root = tmp_path / "fresh"
    for seed in range(5):
        _write_phase_b_seed_fixture(
            accepted_root / "phase_b_symbolic_arms" / f"seed-{seed}",
            seed=seed,
        )
        if seed != 4:
            _write_phase_b_seed_fixture(
                fresh_root / "phase_b_symbolic_arms" / f"seed-{seed}",
                seed=seed,
            )

    result = compare_phase_b(
        accepted_root=accepted_root,
        fresh_root=fresh_root,
        phase_a_result=_verified_phase_a_result(),
    )

    assert result["pass"] is False
    assert result["complete_seeds"] == [0, 1, 2, 3]
    assert result["accepted_maintenance_archive_verified"] is False
    assert any(
        failure.startswith("seed4:fresh_phase_b_manifest_invalid:FileNotFoundError")
        for failure in result["failures"]
    )


REPO_ROOT = Path(__file__).resolve().parents[2]
ACCEPTED_CORRECTION_CONFIG = (
    REPO_ROOT / "data" / "manifests" / "cd_primary_run_config_v1_1.json"
)
ACCEPTED_FAILED_PHASE_C = (
    REPO_ROOT
    / "results"
    / "frozen"
    / "cd_primary_v1"
    / "phase_c_failed_v1"
    / "seed-0"
)


def _rewrite_hashed_json(path: Path, payload: dict[str, Any]) -> None:
    body = copy.deepcopy(payload)
    body.pop("payload_sha256", None)
    body.pop("manifest_sha256", None)
    body["manifest_sha256"] = _canonical_sha256(body)
    body["payload_sha256"] = _canonical_sha256(body)
    path.write_text(
        json.dumps(body, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _fresh_correction_config() -> dict[str, Any]:
    payload = json.loads(ACCEPTED_CORRECTION_CONFIG.read_text(encoding="utf-8"))
    reused = payload["correction"]["reused_upstream_artifacts"]
    for seed in range(5):
        key = str(seed)
        reused["phase_a"][key]["run_manifest_sha256"] = hashlib.sha256(
            f"fresh-phase-a-{seed}".encode()
        ).hexdigest()
        reused["phase_b"][key]["phase_b_manifest_sha256"] = hashlib.sha256(
            f"fresh-phase-b-{seed}".encode()
        ).hexdigest()
    return payload


def _write_phase_c_upstream_bindings(
    root: Path,
    config: dict[str, Any],
) -> None:
    reused = config["correction"]["reused_upstream_artifacts"]
    for seed in range(5):
        key = str(seed)
        a_root = root / "phase_a_shared_control_plane" / f"seed-{seed}"
        b_root = root / "phase_b_symbolic_arms" / f"seed-{seed}"
        a_root.mkdir(parents=True, exist_ok=True)
        b_root.mkdir(parents=True, exist_ok=True)
        (a_root / "run_manifest.json").write_text(
            json.dumps(
                {
                    "manifest_sha256": reused["phase_a"][key][
                        "run_manifest_sha256"
                    ]
                }
            )
            + "\n",
            encoding="utf-8",
        )
        (b_root / "phase_b_manifest.json").write_text(
            json.dumps(
                {
                    "manifest_sha256": reused["phase_b"][key][
                        "phase_b_manifest_sha256"
                    ]
                }
            )
            + "\n",
            encoding="utf-8",
        )


def _copy_failed_phase_c_lineage(root: Path) -> None:
    target = root / "phase_c_offline_evaluation" / "seed-0"
    target.mkdir(parents=True, exist_ok=True)
    for name in ("attempt.json", "failure.json"):
        (target / name).write_bytes((ACCEPTED_FAILED_PHASE_C / name).read_bytes())


def _failed_lineage_expected_identity() -> dict[str, Any]:
    config = json.loads(
        ACCEPTED_CORRECTION_CONFIG.read_text(encoding="utf-8")
    )
    return copy.deepcopy(config["correction"]["failed_phase_c_v1"])


def _rewrite_failed_lineage_payload(
    roots: tuple[Path, Path],
    *,
    name: str,
    mutate: dict[str, Any],
    expected_identity: dict[str, Any],
) -> None:
    for root in roots:
        path = root / "phase_c_offline_evaluation" / "seed-0" / name
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload.update(mutate)
        payload.pop("payload_sha256", None)
        payload["payload_sha256"] = _canonical_sha256(payload)
        path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    stem = name.removesuffix(".json")
    reference = (
        roots[0] / "phase_c_offline_evaluation" / "seed-0" / name
    )
    reference_payload = json.loads(reference.read_text(encoding="utf-8"))
    expected_identity[f"{stem}_payload_sha256"] = reference_payload[
        "payload_sha256"
    ]
    expected_identity[f"{stem}_file_sha256"] = _sha256_file(reference)


def _direct_failed_lineage_fixture(
    tmp_path: Path,
) -> tuple[Path, Path, dict[str, Any]]:
    accepted_root = tmp_path / "accepted"
    fresh_root = tmp_path / "fresh"
    _copy_failed_phase_c_lineage(accepted_root)
    _copy_failed_phase_c_lineage(fresh_root)
    return accepted_root, fresh_root, _failed_lineage_expected_identity()


def _phase_c_precondition_fixture(
    tmp_path: Path,
) -> tuple[Path, Path, Path]:
    accepted = json.loads(
        ACCEPTED_CORRECTION_CONFIG.read_text(encoding="utf-8")
    )
    fresh = _fresh_correction_config()

    accepted_root = tmp_path / "accepted"
    fresh_root = tmp_path / "fresh"
    _write_phase_c_upstream_bindings(accepted_root, accepted)
    _write_phase_c_upstream_bindings(fresh_root, fresh)
    _copy_failed_phase_c_lineage(accepted_root)
    _copy_failed_phase_c_lineage(fresh_root)

    fresh_config_path = tmp_path / "fresh_config.json"
    _rewrite_hashed_json(fresh_config_path, fresh)
    return accepted_root, fresh_root, fresh_config_path


def test_phase_c_failed_v1_lineage_accepts_exact_frozen_identity(
    tmp_path: Path,
) -> None:
    accepted_root, fresh_root, expected_identity = _direct_failed_lineage_fixture(
        tmp_path
    )

    result = _verify_phase_c_failed_lineage(
        accepted_root=accepted_root,
        fresh_root=fresh_root,
        expected_identity=expected_identity,
    )

    assert result["pass"] is True
    assert result["failures"] == []
    assert result["frozen_identity"] == {
        "seed": 0,
        "original_config_manifest_sha256": (
            "3e3f768b5aa32f469440bb334508f747bbf2f7f5b08d9570a7aef2dbb9cb0257"
        ),
        "phase": "offline_boundary_aware_evaluation",
        "adaptive_components_received_boundary": False,
        "exception_type": "NameError",
        "message": "name 'read_jsonl' is not defined",
        "successful_scoring_artifacts_present": False,
        "entries": ["attempt.json", "failure.json"],
    }


def test_phase_c_failed_v1_lineage_rejects_wrong_original_config_even_with_rehashed_files(
    tmp_path: Path,
) -> None:
    accepted_root, fresh_root, expected_identity = _direct_failed_lineage_fixture(
        tmp_path
    )
    _rewrite_failed_lineage_payload(
        (accepted_root, fresh_root),
        name="attempt.json",
        mutate={"primary_config_manifest_sha256": "f" * 64},
        expected_identity=expected_identity,
    )

    result = _verify_phase_c_failed_lineage(
        accepted_root=accepted_root,
        fresh_root=fresh_root,
        expected_identity=expected_identity,
    )

    assert result["pass"] is False
    assert "accepted:attempt:original_config_identity_mismatch" in result["failures"]
    assert "fresh:attempt:original_config_identity_mismatch" in result["failures"]


def test_phase_c_failed_v1_lineage_rejects_seed_phase_and_boundary_mutation(
    tmp_path: Path,
) -> None:
    accepted_root, fresh_root, expected_identity = _direct_failed_lineage_fixture(
        tmp_path
    )
    _rewrite_failed_lineage_payload(
        (accepted_root, fresh_root),
        name="attempt.json",
        mutate={
            "seed": 1,
            "phase": "different_phase",
            "adaptive_components_received_boundary": True,
        },
        expected_identity=expected_identity,
    )

    result = _verify_phase_c_failed_lineage(
        accepted_root=accepted_root,
        fresh_root=fresh_root,
        expected_identity=expected_identity,
    )

    assert result["pass"] is False
    for label in ("accepted", "fresh"):
        assert f"{label}:attempt:seed_mismatch" in result["failures"]
        assert f"{label}:attempt:phase_mismatch" in result["failures"]
        assert f"{label}:attempt:boundary_metadata_not_false" in result["failures"]


def test_phase_c_failed_v1_lineage_rejects_wrong_nameerror_identity(
    tmp_path: Path,
) -> None:
    accepted_root, fresh_root, expected_identity = _direct_failed_lineage_fixture(
        tmp_path
    )
    _rewrite_failed_lineage_payload(
        (accepted_root, fresh_root),
        name="failure.json",
        mutate={
            "exception_type": "ValueError",
            "message": "different failure",
            "adaptive_components_received_boundary": True,
        },
        expected_identity=expected_identity,
    )

    result = _verify_phase_c_failed_lineage(
        accepted_root=accepted_root,
        fresh_root=fresh_root,
        expected_identity=expected_identity,
    )

    assert result["pass"] is False
    for label in ("accepted", "fresh"):
        assert f"{label}:failure:exception_type_mismatch" in result["failures"]
        assert f"{label}:failure:message_mismatch" in result["failures"]
        assert f"{label}:failure:boundary_metadata_not_false" in result["failures"]


def test_phase_c_failed_v1_lineage_rejects_successful_or_extra_outcome_file(
    tmp_path: Path,
) -> None:
    accepted_root, fresh_root, expected_identity = _direct_failed_lineage_fixture(
        tmp_path
    )
    extra = (
        fresh_root
        / "phase_c_offline_evaluation"
        / "seed-0"
        / "c_frozen_symbolic_evaluation.json"
    )
    extra.write_text("{}\n", encoding="utf-8")

    result = _verify_phase_c_failed_lineage(
        accepted_root=accepted_root,
        fresh_root=fresh_root,
        expected_identity=expected_identity,
    )

    assert result["pass"] is False
    assert "fresh:failed_lineage_entries_mismatch" in result["failures"]
    assert (
        "fresh:unexpected_outcome_bearing_file:c_frozen_symbolic_evaluation.json"
        in result["failures"]
    )


def test_phase_c_preconditions_accept_only_rebound_upstream_manifest_hashes(
    tmp_path: Path,
) -> None:
    accepted_root, fresh_root, fresh_config_path = _phase_c_precondition_fixture(
        tmp_path
    )

    result = compare_phase_c_preconditions(
        accepted_root=accepted_root,
        fresh_root=fresh_root,
        accepted_config_path=ACCEPTED_CORRECTION_CONFIG,
        fresh_config_path=fresh_config_path,
    )

    assert result["pass"] is True
    assert result["failures"] == []
    assert result["mismatch_count"] == 0
    assert result["failed_lineage_preserved"] is True
    assert result["scientific_blocks_equal"] is True


def test_phase_c_preconditions_reject_scientific_block_change(
    tmp_path: Path,
) -> None:
    accepted_root, fresh_root, fresh_config_path = _phase_c_precondition_fixture(
        tmp_path
    )
    fresh = json.loads(fresh_config_path.read_text(encoding="utf-8"))
    fresh["fusion"]["primary_neural_weight"] = 0.7
    _rewrite_hashed_json(fresh_config_path, fresh)

    result = compare_phase_c_preconditions(
        accepted_root=accepted_root,
        fresh_root=fresh_root,
        accepted_config_path=ACCEPTED_CORRECTION_CONFIG,
        fresh_config_path=fresh_config_path,
    )

    assert result["pass"] is False
    assert "scientific_block_mismatch:fusion" in result["failures"]


def test_phase_c_preconditions_reject_unbound_fresh_upstream_hash(
    tmp_path: Path,
) -> None:
    accepted_root, fresh_root, fresh_config_path = _phase_c_precondition_fixture(
        tmp_path
    )
    wrong = fresh_root / "phase_a_shared_control_plane" / "seed-2" / "run_manifest.json"
    wrong.write_text(
        json.dumps({"manifest_sha256": "f" * 64}) + "\n",
        encoding="utf-8",
    )

    result = compare_phase_c_preconditions(
        accepted_root=accepted_root,
        fresh_root=fresh_root,
        accepted_config_path=ACCEPTED_CORRECTION_CONFIG,
        fresh_config_path=fresh_config_path,
    )

    assert result["pass"] is False
    assert (
        "fresh_correction:phase_a_upstream_manifest_mismatch:2"
        in result["failures"]
    )


def test_phase_c_preconditions_reject_extra_failed_lineage_file(
    tmp_path: Path,
) -> None:
    accepted_root, fresh_root, fresh_config_path = _phase_c_precondition_fixture(
        tmp_path
    )
    extra = fresh_root / "phase_c_offline_evaluation" / "seed-0" / "extra.json"
    extra.write_text("{}\n", encoding="utf-8")

    result = compare_phase_c_preconditions(
        accepted_root=accepted_root,
        fresh_root=fresh_root,
        accepted_config_path=ACCEPTED_CORRECTION_CONFIG,
        fresh_config_path=fresh_config_path,
    )

    assert result["pass"] is False
    assert "fresh:failed_lineage_entries_mismatch" in result["failures"]

def _write_phase_a_shared_identity_fixture(
    root: Path,
    *,
    identity_sha256: str = "1" * 64,
) -> None:
    core: dict[str, Any] = {
        "schema_version": 1,
        "seed": 0,
        "shared_identity": {
            "identity_sha256": identity_sha256,
        },
    }
    body = dict(core)
    body["payload_sha256"] = _canonical_sha256(core)
    _write_json_bytes(root / "shared_identity.json", body)


def _write_correction_config_fixture(
    path: Path,
    *,
    tag: str,
    stream_rows: int = PHASE_C_STREAM_ROWS,
) -> dict[str, Any]:
    core: dict[str, Any] = {
        "schema_version": 1,
        "tag": tag,
        "scenario": {
            "stream_rows": stream_rows,
        },
    }
    body = dict(core)
    body["manifest_sha256"] = _canonical_sha256(core)
    body["payload_sha256"] = _canonical_sha256(body)
    _write_json_bytes(path, body)
    return body


_PHASE_C_TRACE_RAW = (
    b'{"row_id":"r0","decision":0}\n' * PHASE_C_STREAM_ROWS
)
_PHASE_C_TRACE_COMPRESSED = gzip.compress(
    _PHASE_C_TRACE_RAW,
    compresslevel=9,
    mtime=0,
)


def _write_phase_c_trace(path: Path) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_PHASE_C_TRACE_COMPRESSED)
    return {
        "path": path.name,
        "row_count": PHASE_C_STREAM_ROWS,
        "sha256": hashlib.sha256(_PHASE_C_TRACE_COMPRESSED).hexdigest(),
        "canonical_jsonl_sha256": hashlib.sha256(_PHASE_C_TRACE_RAW).hexdigest(),
    }


def _phase_c_metric_row(metric_value: float) -> dict[str, Any]:
    return {
        "accuracy": metric_value,
        "balanced_accuracy": metric_value,
        "precision": metric_value,
        "recall": metric_value,
        "f1": metric_value,
        "fpr": 0.0,
        "mcc": metric_value,
        "roc_auc": metric_value,
        "average_precision": metric_value,
        "tp": 1,
        "tn": 1,
        "fp": 0,
        "fn": 0,
    }


def _phase_c_explanation_row() -> dict[str, Any]:
    return {
        "benign_rows": 1,
        "benign_coverage": 1.0,
        "benign_symbolic_correctness_on_covered": 1.0,
        "benign_correct_symbolic_coverage": 1.0,
        "attack_rows": 1,
        "attack_coverage": 1.0,
        "attack_symbolic_correctness_on_covered": 1.0,
        "attack_correct_symbolic_coverage": 1.0,
        "mcsc": 1.0,
        "resolved_coverage": 1.0,
        "uncovered_rate": 0.0,
        "conflict_abstain_rate": 0.0,
    }


def _phase_c_window_row(start: int, end: int) -> dict[str, Any]:
    return {
        "start_index": start,
        "end_index_exclusive": end,
        "row_count": end - start,
        "mcc": 0.9,
        "fpr": 0.0,
        "f1": 0.9,
        "mcsc": 0.9,
        "resolved_coverage": 1.0,
        "conflict_abstain_rate": 0.0,
    }


def _write_phase_c_evaluation_fixture(
    output_root: Path,
    *,
    arm: str,
    config_sha256: str,
    phase_b_arm_manifest: dict[str, Any],
    metric_value: float = 0.9,
) -> dict[str, Any]:
    trace = _write_phase_c_trace(
        output_root / f"{arm}_prediction_trace.jsonl.gz"
    )
    metrics = {
        weight: {
            domain: _phase_c_metric_row(metric_value)
            for domain in ("full", "pre", "post")
        }
        for weight in ("0.5", "0.7", "0.9", "1.0")
    }
    explanation = {
        domain: _phase_c_explanation_row()
        for domain in ("full", "pre", "post")
    }
    core: dict[str, Any] = {
        "seed": 0,
        "arm": arm,
        "primary_config_manifest_sha256": config_sha256,
        "phase_b_arm_manifest_sha256": phase_b_arm_manifest[
            "manifest_sha256"
        ],
        "shared_identity_sha256": "1" * 64,
        "metrics_by_neural_weight": metrics,
        "explanation": explanation,
        "primary_windows": {
            "pre": [_phase_c_window_row(0, 5_000)],
            "post": [
                _phase_c_window_row(
                    PHASE_C_BOUNDARY_INDEX,
                    PHASE_C_BOUNDARY_INDEX + 5_000,
                )
            ],
        },
        "primary_recovery": {
            metric: {
                "available": False,
                "reason": "undefined_window_metric",
            }
            for metric in ("mcc", "mcsc", "fpr")
        },
        "maintenance_summary": copy.deepcopy(
            phase_b_arm_manifest["maintenance_summary"]
        ),
        "prediction_trace": trace,
    }
    body = dict(core)
    body["summary_sha256"] = _canonical_sha256(core)
    body["payload_sha256"] = _canonical_sha256(body)
    _write_json_bytes(
        output_root / f"{arm}_evaluation.json",
        body,
    )
    return body


def _phase_c_retention_metrics() -> dict[str, Any]:
    metrics: dict[str, Any] = {}
    for prefix in ("development_", "pre_reference_"):
        for name in (
            "accuracy",
            "balanced_accuracy",
            "precision",
            "recall",
            "f1",
            "fpr",
            "mcc",
            "roc_auc",
            "average_precision",
        ):
            metrics[f"{prefix}{name}"] = {
                "value": 0.9,
                "delta_from_initial": 0.0,
                "descriptive_forgetting": 0.0,
            }
    return metrics


def _write_phase_c_attempt_fixture(
    output_root: Path,
    *,
    config_sha256: str,
) -> dict[str, Any]:
    core = {
        "seed": 0,
        "primary_config_manifest_sha256": config_sha256,
        "phase": "offline_boundary_aware_evaluation",
        "adaptive_components_received_boundary": False,
    }
    body = dict(core)
    body["payload_sha256"] = _canonical_sha256(core)
    _write_json_bytes(output_root / "attempt.json", body)
    return body


def _write_phase_c_seed_manifest_fixture(
    output_root: Path,
    *,
    config_sha256: str,
    phase_a_manifest_sha256: str,
    phase_b_manifest_sha256: str,
    arm_summaries: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    core: dict[str, Any] = {
        "schema_version": 1,
        "seed": 0,
        "status": "complete_offline_evaluation",
        "primary_config_manifest_sha256": config_sha256,
        "phase_a_run_manifest_sha256": phase_a_manifest_sha256,
        "phase_b_seed_manifest_sha256": phase_b_manifest_sha256,
        "arm_summary_sha256": {
            arm: summary["summary_sha256"]
            for arm, summary in arm_summaries.items()
        },
        "lambda_one_predictive_equality": True,
        "trigger_diagnostics": {
            "detector_event_count": 1,
            "pre_reference_alarm_count": 0,
            "pre_reference_alarm_clocks": [],
            "post_reference_event_count": 1,
            "first_post_reference_confirmation_clock": PHASE_C_BOUNDARY_INDEX,
            "first_post_reference_confirmation_delay_rows": 0,
            "latency_adjusted_excess_delay_rows": 0,
            "repeated_post_reference_events": 0,
            "neural_publication_count": 1,
        },
        "neural_retention_probes": [
            {
                "sequence": 0,
                "checkpoint_file_sha256": "2" * 64,
                "publication_effective_index": 0,
                "metrics": _phase_c_retention_metrics(),
            }
        ],
        "boundary_index": PHASE_C_BOUNDARY_INDEX,
        "adaptive_components_received_boundary": False,
    }
    body = dict(core)
    body["manifest_sha256"] = _canonical_sha256(core)
    body["payload_sha256"] = _canonical_sha256(body)
    _write_json_bytes(output_root / "phase_c_seed_manifest.json", body)
    return body


def _rewrite_phase_c_evaluation(
    path: Path,
    payload: dict[str, Any],
) -> dict[str, Any]:
    body = copy.deepcopy(payload)
    body.pop("payload_sha256", None)
    body.pop("summary_sha256", None)
    body["summary_sha256"] = _canonical_sha256(body)
    body["payload_sha256"] = _canonical_sha256(body)
    _write_json_bytes(path, body)
    return body


def _rewrite_phase_c_seed_manifest(
    path: Path,
    payload: dict[str, Any],
) -> dict[str, Any]:
    body = copy.deepcopy(payload)
    body.pop("payload_sha256", None)
    body.pop("manifest_sha256", None)
    body["manifest_sha256"] = _canonical_sha256(body)
    body["payload_sha256"] = _canonical_sha256(body)
    _write_json_bytes(path, body)
    return body


def _phase_c_corrected_output_fixture(
    tmp_path: Path,
) -> tuple[Path, Path, Path, Path]:
    accepted_root = tmp_path / "accepted"
    fresh_root = tmp_path / "fresh"

    accepted_phase_a = _write_phase_a_fixture(
        accepted_root / "phase_a_shared_control_plane" / "seed-0",
        platform="accepted-platform",
        processor="accepted-cpu",
        filepath="C:/accepted/lib.dll",
    )
    fresh_phase_a = _write_phase_a_fixture(
        fresh_root / "phase_a_shared_control_plane" / "seed-0",
        platform="fresh-platform",
        processor="fresh-cpu",
        filepath="D:/fresh/lib.dll",
    )
    _write_phase_a_shared_identity_fixture(
        accepted_root / "phase_a_shared_control_plane" / "seed-0"
    )
    _write_phase_a_shared_identity_fixture(
        fresh_root / "phase_a_shared_control_plane" / "seed-0"
    )

    accepted_phase_b = _write_phase_b_seed_fixture(
        accepted_root / "phase_b_symbolic_arms" / "seed-0",
        timing_scale=1.0,
    )
    fresh_phase_b = _write_phase_b_seed_fixture(
        fresh_root / "phase_b_symbolic_arms" / "seed-0",
        timing_scale=9.0,
    )

    accepted_config_path = tmp_path / "accepted_phase_c_config.json"
    fresh_config_path = tmp_path / "fresh_phase_c_config.json"
    accepted_config = _write_correction_config_fixture(
        accepted_config_path,
        tag="accepted",
    )
    fresh_config = _write_correction_config_fixture(
        fresh_config_path,
        tag="fresh",
    )

    for root, config, phase_a, phase_b in (
        (
            accepted_root,
            accepted_config,
            accepted_phase_a,
            accepted_phase_b,
        ),
        (
            fresh_root,
            fresh_config,
            fresh_phase_a,
            fresh_phase_b,
        ),
    ):
        output_root = (
            root / "phase_c_offline_evaluation_v1_1" / "seed-0"
        )
        output_root.mkdir(parents=True, exist_ok=True)
        _write_phase_c_attempt_fixture(
            output_root,
            config_sha256=str(config["manifest_sha256"]),
        )
        summaries: dict[str, dict[str, Any]] = {}
        for arm in ("c_frozen_symbolic", "d_drift", "d_periodic"):
            arm_manifest = json.loads(
                (
                    root
                    / "phase_b_symbolic_arms"
                    / "seed-0"
                    / arm
                    / "arm_manifest.json"
                ).read_text(encoding="utf-8")
            )
            summaries[arm] = _write_phase_c_evaluation_fixture(
                output_root,
                arm=arm,
                config_sha256=str(config["manifest_sha256"]),
                phase_b_arm_manifest=arm_manifest,
            )
        _write_phase_c_seed_manifest_fixture(
            output_root,
            config_sha256=str(config["manifest_sha256"]),
            phase_a_manifest_sha256=str(phase_a["manifest_sha256"]),
            phase_b_manifest_sha256=str(phase_b["manifest_sha256"]),
            arm_summaries=summaries,
        )

    return (
        accepted_root,
        fresh_root,
        accepted_config_path,
        fresh_config_path,
    )


def test_phase_c_corrected_output_accepts_only_transitive_identity_and_timing(
    tmp_path: Path,
) -> None:
    (
        accepted_root,
        fresh_root,
        accepted_config_path,
        fresh_config_path,
    ) = _phase_c_corrected_output_fixture(tmp_path)

    result = compare_phase_c_corrected_output(
        accepted_root=accepted_root,
        fresh_root=fresh_root,
        accepted_config_path=accepted_config_path,
        fresh_config_path=fresh_config_path,
    )

    assert result["pass"] is True
    assert result["failures"] == []
    assert result["mismatch_count"] == 0


def test_phase_c_corrected_output_rejects_scientific_metric_change(
    tmp_path: Path,
) -> None:
    (
        accepted_root,
        fresh_root,
        accepted_config_path,
        fresh_config_path,
    ) = _phase_c_corrected_output_fixture(tmp_path)
    output_root = (
        fresh_root / "phase_c_offline_evaluation_v1_1" / "seed-0"
    )
    path = output_root / "d_drift_evaluation.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["metrics_by_neural_weight"]["0.5"]["post"]["mcc"] = 0.1
    rewritten = _rewrite_phase_c_evaluation(path, payload)

    seed_path = output_root / "phase_c_seed_manifest.json"
    seed_payload = json.loads(seed_path.read_text(encoding="utf-8"))
    seed_payload["arm_summary_sha256"]["d_drift"] = rewritten[
        "summary_sha256"
    ]
    _rewrite_phase_c_seed_manifest(seed_path, seed_payload)

    result = compare_phase_c_corrected_output(
        accepted_root=accepted_root,
        fresh_root=fresh_root,
        accepted_config_path=accepted_config_path,
        fresh_config_path=fresh_config_path,
    )

    assert result["pass"] is False
    assert any(
        "metrics_by_neural_weight" in path
        for path in result["mismatches"]
    )


def test_phase_c_corrected_output_rejects_prediction_trace_byte_tamper(
    tmp_path: Path,
) -> None:
    (
        accepted_root,
        fresh_root,
        accepted_config_path,
        fresh_config_path,
    ) = _phase_c_corrected_output_fixture(tmp_path)
    trace = (
        fresh_root
        / "phase_c_offline_evaluation_v1_1"
        / "seed-0"
        / "d_drift_prediction_trace.jsonl.gz"
    )
    trace.write_bytes(trace.read_bytes() + b"tamper")

    result = compare_phase_c_corrected_output(
        accepted_root=accepted_root,
        fresh_root=fresh_root,
        accepted_config_path=accepted_config_path,
        fresh_config_path=fresh_config_path,
    )

    assert result["pass"] is False
    assert (
        "fresh:d_drift:prediction_trace_file_sha256_mismatch"
        in result["failures"]
    )


def test_phase_c_corrected_output_rejects_shared_identity_rebinding(
    tmp_path: Path,
) -> None:
    (
        accepted_root,
        fresh_root,
        accepted_config_path,
        fresh_config_path,
    ) = _phase_c_corrected_output_fixture(tmp_path)
    shared_path = (
        fresh_root
        / "phase_a_shared_control_plane"
        / "seed-0"
        / "shared_identity.json"
    )
    shared = json.loads(shared_path.read_text(encoding="utf-8"))
    shared["shared_identity"]["identity_sha256"] = "9" * 64
    shared.pop("payload_sha256", None)
    shared["payload_sha256"] = _canonical_sha256(shared)
    _write_json_bytes(shared_path, shared)

    result = compare_phase_c_corrected_output(
        accepted_root=accepted_root,
        fresh_root=fresh_root,
        accepted_config_path=accepted_config_path,
        fresh_config_path=fresh_config_path,
    )

    assert result["pass"] is False
    assert (
        "fresh:d_drift:shared_identity_binding_mismatch"
        in result["failures"]
    )


def test_phase_c_corrected_output_rejects_seed_control_change(
    tmp_path: Path,
) -> None:
    (
        accepted_root,
        fresh_root,
        accepted_config_path,
        fresh_config_path,
    ) = _phase_c_corrected_output_fixture(tmp_path)
    seed_path = (
        fresh_root
        / "phase_c_offline_evaluation_v1_1"
        / "seed-0"
        / "phase_c_seed_manifest.json"
    )
    seed_payload = json.loads(seed_path.read_text(encoding="utf-8"))
    seed_payload["lambda_one_predictive_equality"] = False
    _rewrite_phase_c_seed_manifest(seed_path, seed_payload)

    result = compare_phase_c_corrected_output(
        accepted_root=accepted_root,
        fresh_root=fresh_root,
        accepted_config_path=accepted_config_path,
        fresh_config_path=fresh_config_path,
    )

    assert result["pass"] is False
    assert "fresh:phase_c_lambda_one_control_failed" in result["failures"]

def test_phase_c_corrected_output_rejects_extra_success_surface_file(
    tmp_path: Path,
) -> None:
    accepted_root, fresh_root, accepted_config_path, fresh_config_path = (
        _phase_c_corrected_output_fixture(tmp_path)
    )
    output_root = (
        fresh_root / "phase_c_offline_evaluation_v1_1" / "seed-0"
    )
    (output_root / "failure.json").write_text("{}\n", encoding="utf-8")

    result = compare_phase_c_corrected_output(
        accepted_root=accepted_root,
        fresh_root=fresh_root,
        accepted_config_path=accepted_config_path,
        fresh_config_path=fresh_config_path,
    )

    assert result["pass"] is False
    assert "fresh:corrected_output_file_set_mismatch" in result["failures"]


def test_phase_c_corrected_output_rejects_attempt_boundary_contamination(
    tmp_path: Path,
) -> None:
    accepted_root, fresh_root, accepted_config_path, fresh_config_path = (
        _phase_c_corrected_output_fixture(tmp_path)
    )
    path = (
        fresh_root
        / "phase_c_offline_evaluation_v1_1"
        / "seed-0"
        / "attempt.json"
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["adaptive_components_received_boundary"] = True
    payload.pop("payload_sha256", None)
    payload["payload_sha256"] = _canonical_sha256(payload)
    _write_json_bytes(path, payload)

    result = compare_phase_c_corrected_output(
        accepted_root=accepted_root,
        fresh_root=fresh_root,
        accepted_config_path=accepted_config_path,
        fresh_config_path=fresh_config_path,
    )

    assert result["pass"] is False
    assert "fresh:attempt_boundary_contamination_flag" in result["failures"]


def test_phase_c_corrected_output_rejects_boundary_index_change(
    tmp_path: Path,
) -> None:
    accepted_root, fresh_root, accepted_config_path, fresh_config_path = (
        _phase_c_corrected_output_fixture(tmp_path)
    )
    path = (
        fresh_root
        / "phase_c_offline_evaluation_v1_1"
        / "seed-0"
        / "phase_c_seed_manifest.json"
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["boundary_index"] = PHASE_C_BOUNDARY_INDEX + 1
    _rewrite_phase_c_seed_manifest(path, payload)

    result = compare_phase_c_corrected_output(
        accepted_root=accepted_root,
        fresh_root=fresh_root,
        accepted_config_path=accepted_config_path,
        fresh_config_path=fresh_config_path,
    )

    assert result["pass"] is False
    assert "fresh:phase_c_boundary_index_mismatch" in result["failures"]


def test_phase_c_corrected_output_rejects_metric_schema_change(
    tmp_path: Path,
) -> None:
    accepted_root, fresh_root, accepted_config_path, fresh_config_path = (
        _phase_c_corrected_output_fixture(tmp_path)
    )
    output_root = (
        fresh_root / "phase_c_offline_evaluation_v1_1" / "seed-0"
    )
    path = output_root / "d_drift_evaluation.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    del payload["metrics_by_neural_weight"]["0.5"]["post"]["roc_auc"]
    rewritten = _rewrite_phase_c_evaluation(path, payload)
    seed_path = output_root / "phase_c_seed_manifest.json"
    seed_payload = json.loads(seed_path.read_text(encoding="utf-8"))
    seed_payload["arm_summary_sha256"]["d_drift"] = rewritten["summary_sha256"]
    _rewrite_phase_c_seed_manifest(seed_path, seed_payload)

    result = compare_phase_c_corrected_output(
        accepted_root=accepted_root,
        fresh_root=fresh_root,
        accepted_config_path=accepted_config_path,
        fresh_config_path=fresh_config_path,
    )

    assert result["pass"] is False
    assert (
        "fresh:d_drift:metrics_field_set_mismatch:0.5:post"
        in result["failures"]
    )


def test_phase_c_corrected_output_rejects_retention_schema_change(
    tmp_path: Path,
) -> None:
    accepted_root, fresh_root, accepted_config_path, fresh_config_path = (
        _phase_c_corrected_output_fixture(tmp_path)
    )
    path = (
        fresh_root
        / "phase_c_offline_evaluation_v1_1"
        / "seed-0"
        / "phase_c_seed_manifest.json"
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    del payload["neural_retention_probes"][0]["metrics"][
        "development_roc_auc"
    ]
    _rewrite_phase_c_seed_manifest(path, payload)

    result = compare_phase_c_corrected_output(
        accepted_root=accepted_root,
        fresh_root=fresh_root,
        accepted_config_path=accepted_config_path,
        fresh_config_path=fresh_config_path,
    )

    assert result["pass"] is False
    assert (
        "fresh:retention_probe_metric_key_set_mismatch:0"
        in result["failures"]
    )


def test_phase_c_dependency_gate_requires_verified_phase_a_b_and_preconditions() -> None:
    blocked = _blocked_phase_c_output_for_dependencies(
        phase_a_pass=True,
        phase_b_pass=False,
        preconditions_pass=True,
    )
    assert blocked["pass"] is False
    assert blocked["dependency_gate_pass"] is False
    assert blocked["failures"] == [
        "phase_c_dependency_gate:phase_b_not_verified"
    ]


def _write_stage1_contract_and_report(
    tmp_path: Path,
    *,
    repository_head: str,
    status: str = "pass",
) -> tuple[Path, Path]:
    verifier_path = tmp_path / "stage1_verifier.py"
    verifier_path.write_text("# frozen toy verifier\n", encoding="utf-8")
    contract = {
        "contract_id": "stage9.5-6-stage1-reconstruction-evidence-v1",
        "verifier_implementation": {
            "verifier_id": "stage9.5-6-stage1-reconstruction-verifier-v1",
            "tool_path": "stage1_verifier.py",
        },
        "required_report": {
            "path": "stage1_reconstruction_report.json",
            "audit_id": "stage9.5-6-stage1-reconstruction-v1",
            "required_success_values": {
                "status": "pass",
                "pass": True,
                "raw_file_count_verified": 8,
                "interim_table_count_verified": 8,
                "preprocessing_manifest_canonical_sha256": "d" * 64,
                "semantic_mismatch_count": 0,
                "failures": [],
                "blockers": [],
            },
        },
    }
    contract_path = tmp_path / "stage1_contract.json"
    contract_path.write_text(
        json.dumps(contract, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    report = {
        "audit_id": "stage9.5-6-stage1-reconstruction-v1",
        "contract_id": contract["contract_id"],
        "contract_canonical_sha256": _canonical_sha256(contract),
        "verifier_id": contract["verifier_implementation"]["verifier_id"],
        "verifier_source_sha256": _sha256_file(verifier_path),
        "status": status,
        "pass": status == "pass",
        "repository_head": repository_head,
        "manual_success_override_permitted": False,
        "raw_file_count_verified": 8,
        "interim_table_count_verified": 8,
        "preprocessing_manifest_canonical_sha256": "d" * 64,
        "semantic_mismatch_count": 0,
        "failures": [] if status == "pass" else ["toy_failure"],
        "blockers": [],
        "scientific_objects_modified": False,
        "stage10_outcomes_accessed": False,
    }
    report["canonical_sha256"] = _canonical_sha256(report)
    report_path = tmp_path / "stage1_reconstruction_report.json"
    report_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return contract_path, report_path


def test_stage1_report_binding_accepts_canonical_ancestor_report(
    tmp_path: Path,
) -> None:
    contract_path, report_path = _write_stage1_contract_and_report(
        tmp_path,
        repository_head=_git_head(),
    )

    result = _verify_stage1_reconstruction_report(
        report_path,
        contract_path=contract_path,
        expected_root=tmp_path,
    )

    assert result["pass"] is True
    assert result["failures"] == []
    assert result["canonical_sha256"] is not None


def test_stage1_report_binding_rejects_resealed_semantic_failure(
    tmp_path: Path,
) -> None:
    contract_path, report_path = _write_stage1_contract_and_report(
        tmp_path,
        repository_head=_git_head(),
        status="blocked",
    )

    result = _verify_stage1_reconstruction_report(
        report_path,
        contract_path=contract_path,
        expected_root=tmp_path,
    )

    assert result["pass"] is False
    assert "stage1_report_success_value_mismatch:status" in result["failures"]
    assert "stage1_report_success_value_mismatch:pass" in result["failures"]
    assert "stage1_report_success_value_mismatch:failures" in result["failures"]


def test_stage1_report_binding_rejects_unrelated_repository_head(
    tmp_path: Path,
) -> None:
    contract_path, report_path = _write_stage1_contract_and_report(
        tmp_path,
        repository_head="f" * 40,
    )

    result = _verify_stage1_reconstruction_report(
        report_path,
        contract_path=contract_path,
        expected_root=tmp_path,
    )

    assert result["pass"] is False
    assert "stage1_report_repository_head_not_ancestor" in result["failures"]

def test_stage1_report_binding_rejects_wrong_contract_identity(
    tmp_path: Path,
) -> None:
    contract_path, report_path = _write_stage1_contract_and_report(
        tmp_path,
        repository_head=_git_head(),
    )
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["contract_canonical_sha256"] = "0" * 64
    report.pop("canonical_sha256", None)
    report["canonical_sha256"] = _canonical_sha256(report)
    report_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = _verify_stage1_reconstruction_report(
        report_path,
        contract_path=contract_path,
        expected_root=tmp_path,
    )

    assert result["pass"] is False
    assert (
        "stage1_report_contract_canonical_sha256_mismatch"
        in result["failures"]
    )


def test_stage1_report_binding_rejects_wrong_verifier_source_identity(
    tmp_path: Path,
) -> None:
    contract_path, report_path = _write_stage1_contract_and_report(
        tmp_path,
        repository_head=_git_head(),
    )
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["verifier_source_sha256"] = "0" * 64
    report.pop("canonical_sha256", None)
    report["canonical_sha256"] = _canonical_sha256(report)
    report_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = _verify_stage1_reconstruction_report(
        report_path,
        contract_path=contract_path,
        expected_root=tmp_path,
    )

    assert result["pass"] is False
    assert (
        "stage1_report_verifier_source_sha256_mismatch"
        in result["failures"]
    )

def test_committed_stage1_reconstruction_report_passes_binding() -> None:
    report_path = (
        Path(__file__).resolve().parents[2]
        / "results"
        / "audits"
        / "stage9_5_full_seed_rerun_v1"
        / "stage1_reconstruction_report.json"
    )
    assert report_path.is_file()

    result = _verify_stage1_reconstruction_report(report_path)

    assert result["pass"] is True
    assert result["failures"] == []
    assert (
        result["canonical_sha256"]
        == "4bafa772f9737d934f40c90bf7be8d80a62108cf89a9c74895fbe5c12c4a88af"
    )

def _project_phase_b_record_sequence(
    records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return [_project_phase_b_maintenance_record(record) for record in records]


def test_phase_b_record_projection_contract_matches_frozen_v1_1_surface() -> None:
    root = Path(__file__).resolve().parents[2]
    contract_path = (
        root
        / "data"
        / "manifests"
        / "stage9_5_6_phase_b_maintenance_record_projection_v1.json"
    )
    contract = json.loads(contract_path.read_text(encoding="utf-8"))

    assert contract["contract_id"] == (
        "stage9.5-6-phase-b-maintenance-record-projection-v1"
    )
    assert contract["permitted_record_projection"]["top_level_fields_removed"] == [
        "shap_seconds",
        "surrogate_seconds",
        "lifecycle_seconds",
    ]
    assert contract["permitted_record_projection"]["nested_direct_child_removed"] == [
        "generation_payload.timing_seconds"
    ]
    assert tuple(PHASE_B_RECORD_TIMING_FIELDS) == (
        "shap_seconds",
        "surrogate_seconds",
        "lifecycle_seconds",
    )
    assert contract["permitted_record_projection"]["diagnostic_exclusion_set_closed"] is True
    assert contract["permitted_record_projection"]["no_name_pattern_matching"] is True
    assert contract["permitted_record_projection"]["no_recursive_timing_field_removal"] is True
    assert contract["arm_manifest_transitive_hash_handling_frozen_by_this_contract"] is False
    assert contract["seed_manifest_transitive_hash_handling_frozen_by_this_contract"] is False


def test_phase_b_record_projection_ignores_exactly_predeclared_timing_paths() -> None:
    accepted = {
        "record_id": "r-1",
        "scientific_value": {"score": 0.75},
        "shap_seconds": 1.0,
        "surrogate_seconds": 2.0,
        "lifecycle_seconds": 3.0,
        "generation_payload": {
            "generation_evidence_id": "a" * 64,
            "scientific_value": {"kept": True},
            "timing_seconds": {
                "shap": 1.25,
                "surrogate": 2.25,
            },
            "timing_seconds_extra": "must-remain-exact",
            "nested": {"timing_seconds": "also-must-remain-exact"},
        },
        "other": {"timing_seconds": "must-remain-exact"},
    }
    fresh = copy.deepcopy(accepted)
    fresh["shap_seconds"] = 100.0
    fresh["surrogate_seconds"] = 200.0
    fresh["lifecycle_seconds"] = 300.0
    fresh["generation_payload"]["timing_seconds"] = [
        "different",
        {"shape": "entire-direct-child-is-diagnostic"},
    ]

    assert _project_phase_b_maintenance_record(accepted) == (
        _project_phase_b_maintenance_record(fresh)
    )


def test_phase_b_record_projection_preserves_non_timing_generation_payload_fields() -> None:
    accepted = {
        "record_id": "r-1",
        "generation_payload": {
            "generation_evidence_id": "a" * 64,
            "timing_seconds": {"shap": 1.0},
            "nested": {"timing_seconds": "scientific-here"},
        },
    }
    fresh = copy.deepcopy(accepted)
    fresh["generation_payload"]["nested"]["timing_seconds"] = "changed"

    assert _project_phase_b_maintenance_record(accepted) != (
        _project_phase_b_maintenance_record(fresh)
    )


def test_phase_b_record_projection_preserves_generation_payload_parent_semantics() -> None:
    missing = {"record_id": "r-1"}
    null = {"record_id": "r-1", "generation_payload": None}
    object_value = {
        "record_id": "r-1",
        "generation_payload": {"timing_seconds": 1.0},
    }

    missing_projected = _project_phase_b_maintenance_record(missing)
    null_projected = _project_phase_b_maintenance_record(null)
    object_projected = _project_phase_b_maintenance_record(object_value)

    assert "generation_payload" not in missing_projected
    assert null_projected["generation_payload"] is None
    assert object_projected["generation_payload"] == {}
    assert missing_projected != null_projected
    assert null_projected != object_projected
    assert missing_projected != object_projected


def test_phase_b_record_projection_rejects_non_object_generation_payload() -> None:
    try:
        _project_phase_b_maintenance_record(
            {"record_id": "r-1", "generation_payload": "invalid"}
        )
    except TypeError as exc:
        assert "generation_payload must be an object or null" in str(exc)
    else:
        raise AssertionError("Non-object generation_payload must fail closed")


def test_phase_b_record_sequence_missing_added_and_reordered_records_fail_closed() -> None:
    accepted = [
        {"record_id": "r-1", "scientific_value": 1, "shap_seconds": 1.0},
        {"record_id": "r-2", "scientific_value": 2, "shap_seconds": 2.0},
    ]
    missing = [copy.deepcopy(accepted[0])]
    added = copy.deepcopy(accepted) + [
        {"record_id": "r-3", "scientific_value": 3, "shap_seconds": 3.0}
    ]
    reordered = [copy.deepcopy(accepted[1]), copy.deepcopy(accepted[0])]

    accepted_projected = _project_phase_b_record_sequence(accepted)
    missing_projected = _project_phase_b_record_sequence(missing)
    added_projected = _project_phase_b_record_sequence(added)
    reordered_projected = _project_phase_b_record_sequence(reordered)

    assert accepted_projected != missing_projected
    assert accepted_projected != added_projected
    assert accepted_projected != reordered_projected
    assert _canonical_sha256(accepted_projected) != _canonical_sha256(missing_projected)
    assert _canonical_sha256(accepted_projected) != _canonical_sha256(added_projected)
    assert _canonical_sha256(accepted_projected) != _canonical_sha256(reordered_projected)


def test_phase_b_record_sequence_non_timing_change_fails_closed() -> None:
    accepted = [
        {
            "record_id": "r-1",
            "scientific_value": {"decision": "publish"},
            "generation_payload": {
                "generation_evidence_id": "a" * 64,
                "timing_seconds": {"shap": 1.0},
            },
        }
    ]
    fresh = copy.deepcopy(accepted)
    fresh[0]["scientific_value"]["decision"] = "retire"

    assert _project_phase_b_record_sequence(accepted) != (
        _project_phase_b_record_sequence(fresh)
    )

def _write_maintenance_jsonl(
    path: Path,
    records: list[dict[str, Any]],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(
            json.dumps(record, sort_keys=True) + "\n"
            for record in records
        ),
        encoding="utf-8",
    )


def _maintenance_records() -> list[dict[str, Any]]:
    return [
        {
            "record_id": "r-1",
            "scientific_value": {"decision": "publish", "score": 0.75},
            "shap_seconds": 1.0,
            "surrogate_seconds": 2.0,
            "lifecycle_seconds": 3.0,
            "generation_payload": {
                "generation_evidence_id": "a" * 64,
                "timing_seconds": {"shap": 1.25, "surrogate": 2.25},
                "scientific_value": {"kept": True},
            },
        },
        {
            "record_id": "r-2",
            "scientific_value": {"decision": "retire", "score": 0.25},
            "shap_seconds": 4.0,
            "surrogate_seconds": 5.0,
            "lifecycle_seconds": 6.0,
            "generation_payload": None,
        },
    ]


def test_phase_b_maintenance_comparator_timing_only_differences_pass(
    tmp_path: Path,
) -> None:
    accepted = _maintenance_records()
    fresh = copy.deepcopy(accepted)
    fresh[0]["shap_seconds"] = 101.0
    fresh[0]["surrogate_seconds"] = 202.0
    fresh[0]["lifecycle_seconds"] = 303.0
    generation = fresh[0]["generation_payload"]
    assert isinstance(generation, dict)
    generation["timing_seconds"] = {
        "shap": 1001.0,
        "surrogate": 2002.0,
    }
    fresh[1]["shap_seconds"] = 404.0
    fresh[1]["surrogate_seconds"] = 505.0
    fresh[1]["lifecycle_seconds"] = 606.0

    accepted_path = tmp_path / "accepted" / "maintenance.jsonl"
    fresh_path = tmp_path / "fresh" / "maintenance.jsonl"
    _write_maintenance_jsonl(accepted_path, accepted)
    _write_maintenance_jsonl(fresh_path, fresh)

    result = compare_phase_b_maintenance_jsonl(
        accepted_path=accepted_path,
        fresh_path=fresh_path,
    )

    assert result["pass"] is True
    assert result["failures"] == []
    assert result["mismatches"] == []
    assert result["accepted_record_count"] == 2
    assert result["fresh_record_count"] == 2
    assert (
        result["accepted_projected_sha256"]
        == result["fresh_projected_sha256"]
    )


def test_phase_b_maintenance_comparator_non_timing_scientific_change_fails(
    tmp_path: Path,
) -> None:
    accepted = _maintenance_records()
    fresh = copy.deepcopy(accepted)
    fresh[0]["scientific_value"]["decision"] = "retire"

    accepted_path = tmp_path / "accepted" / "maintenance.jsonl"
    fresh_path = tmp_path / "fresh" / "maintenance.jsonl"
    _write_maintenance_jsonl(accepted_path, accepted)
    _write_maintenance_jsonl(fresh_path, fresh)

    result = compare_phase_b_maintenance_jsonl(
        accepted_path=accepted_path,
        fresh_path=fresh_path,
    )

    assert result["pass"] is False
    assert result["failures"] == []
    assert (
        "maintenance[0].scientific_value.decision"
        in result["mismatches"]
    )


def test_phase_b_maintenance_comparator_record_count_change_fails(
    tmp_path: Path,
) -> None:
    accepted = _maintenance_records()
    fresh = copy.deepcopy(accepted[:1])

    accepted_path = tmp_path / "accepted" / "maintenance.jsonl"
    fresh_path = tmp_path / "fresh" / "maintenance.jsonl"
    _write_maintenance_jsonl(accepted_path, accepted)
    _write_maintenance_jsonl(fresh_path, fresh)

    result = compare_phase_b_maintenance_jsonl(
        accepted_path=accepted_path,
        fresh_path=fresh_path,
    )

    assert result["pass"] is False
    assert result["accepted_record_count"] == 2
    assert result["fresh_record_count"] == 1
    assert result["mismatches"] == ["maintenance.length"]


def test_phase_b_maintenance_comparator_record_order_change_fails(
    tmp_path: Path,
) -> None:
    accepted = _maintenance_records()
    fresh = [copy.deepcopy(accepted[1]), copy.deepcopy(accepted[0])]

    accepted_path = tmp_path / "accepted" / "maintenance.jsonl"
    fresh_path = tmp_path / "fresh" / "maintenance.jsonl"
    _write_maintenance_jsonl(accepted_path, accepted)
    _write_maintenance_jsonl(fresh_path, fresh)

    result = compare_phase_b_maintenance_jsonl(
        accepted_path=accepted_path,
        fresh_path=fresh_path,
    )

    assert result["pass"] is False
    assert result["accepted_record_count"] == 2
    assert result["fresh_record_count"] == 2
    assert "maintenance[0].record_id" in result["mismatches"]
    assert "maintenance[1].record_id" in result["mismatches"]


def test_phase_b_maintenance_comparator_malformed_and_duplicate_key_fail_closed(
    tmp_path: Path,
) -> None:
    accepted_path = tmp_path / "accepted" / "maintenance.jsonl"
    _write_maintenance_jsonl(accepted_path, _maintenance_records())

    malformed_path = tmp_path / "fresh-malformed" / "maintenance.jsonl"
    malformed_path.parent.mkdir(parents=True)
    malformed_path.write_text('{"record_id": "r-1"\n', encoding="utf-8")
    malformed = compare_phase_b_maintenance_jsonl(
        accepted_path=accepted_path,
        fresh_path=malformed_path,
    )
    assert malformed["pass"] is False
    assert any(
        failure.startswith("fresh_maintenance_invalid:ValueError:")
        for failure in malformed["failures"]
    )

    duplicate_path = tmp_path / "fresh-duplicate" / "maintenance.jsonl"
    duplicate_path.parent.mkdir(parents=True)
    duplicate_path.write_text(
        '{"record_id":"r-1","record_id":"r-2"}\n',
        encoding="utf-8",
    )
    duplicate = compare_phase_b_maintenance_jsonl(
        accepted_path=accepted_path,
        fresh_path=duplicate_path,
    )
    assert duplicate["pass"] is False
    assert any(
        failure.startswith("fresh_maintenance_invalid:ValueError:")
        for failure in duplicate["failures"]
    )


def test_phase_b_maintenance_comparator_rejects_noncanonical_nan_before_projection(
    tmp_path: Path,
) -> None:
    accepted_path = tmp_path / "accepted" / "maintenance.jsonl"
    fresh_path = tmp_path / "fresh" / "maintenance.jsonl"
    _write_maintenance_jsonl(accepted_path, _maintenance_records())
    fresh_path.parent.mkdir(parents=True)
    fresh_path.write_text(
        '{"record_id":"r-1","scientific_value":{"decision":"publish","score":0.75},'
        '"shap_seconds":NaN,"surrogate_seconds":2.0,"lifecycle_seconds":3.0,'
        '"generation_payload":{"generation_evidence_id":"'
        + "a" * 64
        + '","timing_seconds":{"shap":1.25,"surrogate":2.25},'
        '"scientific_value":{"kept":true}}}\n',
        encoding="utf-8",
    )

    result = compare_phase_b_maintenance_jsonl(
        accepted_path=accepted_path,
        fresh_path=fresh_path,
    )

    assert result["pass"] is False
    assert any(
        failure.startswith("fresh_maintenance_invalid:ValueError:")
        and "Non-canonical JSON constant: NaN" in failure
        for failure in result["failures"]
    )


def test_phase_b_maintenance_comparator_missing_accepted_evidence_fails_closed(
    tmp_path: Path,
) -> None:
    accepted_path = tmp_path / "accepted-missing" / "maintenance.jsonl"
    fresh_path = tmp_path / "fresh" / "maintenance.jsonl"
    _write_maintenance_jsonl(fresh_path, _maintenance_records())

    result = compare_phase_b_maintenance_jsonl(
        accepted_path=accepted_path,
        fresh_path=fresh_path,
    )

    assert result["pass"] is False
    assert result["accepted_record_count"] is None
    assert any(
        failure.startswith(
            "accepted_maintenance_invalid:FileNotFoundError:"
        )
        for failure in result["failures"]
    )

def test_phase_b_arm_valid_timing_only_variation_all_frozen_arms(
    tmp_path: Path,
) -> None:
    for arm in ARM_NAMES:
        accepted_root = tmp_path / arm / "accepted"
        fresh_root = tmp_path / arm / "fresh"
        _write_phase_b_arm_fixture(
            accepted_root,
            arm=arm,
            timing_scale=1.0,
        )
        _write_phase_b_arm_fixture(
            fresh_root,
            arm=arm,
            timing_scale=7.0,
        )

        result = compare_phase_b_arm(
            accepted_arm_root=accepted_root,
            fresh_arm_root=fresh_root,
            seed=0,
            arm=arm,
        )

        assert result["pass"] is True
        assert result["failures"] == []
        assert result["mismatch_count"] == 0
        assert (
            result["maintenance_comparator"]
            == "stage9.5-6-phase-b-maintenance-record-projection-v1"
        )
        assert (
            result["arm_manifest_projection"]
            == "stage9.5-6-phase-b-arm-manifest-projection-v1"
        )


def test_phase_b_arm_rejects_altered_lifecycle_scientific_field(
    tmp_path: Path,
) -> None:
    accepted_root = tmp_path / "accepted"
    fresh_root = tmp_path / "fresh"
    _write_phase_b_arm_fixture(accepted_root, arm="d_drift")
    fresh = _write_phase_b_arm_fixture(fresh_root, arm="d_drift")

    records = _read_phase_b_maintenance_records(fresh_root)
    records[0]["lifecycle"] = {
        "decision": "retire",
        "rule_id": "changed-rule",
    }
    _write_phase_b_maintenance_records(
        fresh_root,
        fresh,
        records,
        recompute_manifest_hash=True,
    )

    result = compare_phase_b_arm(
        accepted_arm_root=accepted_root,
        fresh_arm_root=fresh_root,
        seed=0,
        arm="d_drift",
    )

    assert result["pass"] is False
    assert any(
        path.startswith("maintenance[0].lifecycle")
        for path in result["mismatches"]
    )


def test_phase_b_arm_rejects_altered_initial_or_final_state(
    tmp_path: Path,
) -> None:
    for descriptor_name in ("initial_state", "final_state"):
        accepted_root = tmp_path / descriptor_name / "accepted"
        fresh_root = tmp_path / descriptor_name / "fresh"
        _write_phase_b_arm_fixture(
            accepted_root,
            arm="d_periodic",
        )
        fresh = _write_phase_b_arm_fixture(
            fresh_root,
            arm="d_periodic",
        )

        files = fresh["files"]
        assert isinstance(files, dict)
        descriptor = files[descriptor_name]
        assert isinstance(descriptor, dict)
        state_path = fresh_root / str(descriptor["path"])
        descriptor["sha256"] = _write_json_bytes(
            state_path,
            {"state": f"altered-{descriptor_name}"},
        )
        _rewrite_phase_b_arm_manifest(fresh_root, fresh)

        result = compare_phase_b_arm(
            accepted_arm_root=accepted_root,
            fresh_arm_root=fresh_root,
            seed=0,
            arm="d_periodic",
        )

        assert result["pass"] is False
        assert (
            f"nonmaintenance_file_descriptor_mismatch:{descriptor_name}"
            in result["failures"]
        )


def test_phase_b_arm_rejects_altered_rule_version_file(
    tmp_path: Path,
) -> None:
    accepted_root = tmp_path / "accepted"
    fresh_root = tmp_path / "fresh"
    accepted = _write_phase_b_arm_fixture(
        accepted_root,
        arm="d_drift",
    )
    fresh = _write_phase_b_arm_fixture(
        fresh_root,
        arm="d_drift",
    )
    _add_phase_b_version_descriptor(
        accepted_root,
        accepted,
        rule_value="same-rule",
    )
    fresh = _add_phase_b_version_descriptor(
        fresh_root,
        fresh,
        rule_value="same-rule",
    )

    files = fresh["files"]
    assert isinstance(files, dict)
    version = files["version_0001"]
    assert isinstance(version, dict)
    version_path = fresh_root / str(version["path"])
    version["sha256"] = _write_json_bytes(
        version_path,
        {"effective_index": 100, "state": {"rule": "altered-rule"}},
    )
    _rewrite_phase_b_arm_manifest(fresh_root, fresh)

    result = compare_phase_b_arm(
        accepted_arm_root=accepted_root,
        fresh_arm_root=fresh_root,
        seed=0,
        arm="d_drift",
    )

    assert result["pass"] is False
    assert (
        "nonmaintenance_file_descriptor_mismatch:version_0001"
        in result["failures"]
    )


def test_phase_b_arm_rejects_altered_descriptor_linked_bytes(
    tmp_path: Path,
) -> None:
    accepted_root = tmp_path / "accepted"
    fresh_root = tmp_path / "fresh"
    _write_phase_b_arm_fixture(
        accepted_root,
        arm="c_frozen_symbolic",
    )
    _write_phase_b_arm_fixture(
        fresh_root,
        arm="c_frozen_symbolic",
    )
    (fresh_root / "initial_state.json").write_text(
        '{"state":"tampered-after-freeze"}\n',
        encoding="utf-8",
    )

    result = compare_phase_b_arm(
        accepted_arm_root=accepted_root,
        fresh_arm_root=fresh_root,
        seed=0,
        arm="c_frozen_symbolic",
    )

    assert result["pass"] is False
    assert (
        "fresh_arm:file_sha256_mismatch:initial_state"
        in result["failures"]
    )


def test_phase_b_arm_rejects_incorrect_transitive_manifest_hash(
    tmp_path: Path,
) -> None:
    accepted_root = tmp_path / "accepted"
    fresh_root = tmp_path / "fresh"
    _write_phase_b_arm_fixture(
        accepted_root,
        arm="d_drift",
        timing_scale=1.0,
    )
    fresh = _write_phase_b_arm_fixture(
        fresh_root,
        arm="d_drift",
        timing_scale=1.0,
    )

    records = _read_phase_b_maintenance_records(fresh_root)
    records[0]["shap_seconds"] = 11.0
    records[0]["surrogate_seconds"] = 12.0
    records[0]["lifecycle_seconds"] = 13.0
    generation = records[0]["generation_payload"]
    assert isinstance(generation, dict)
    generation["timing_seconds"] = {"shap": 11.0, "surrogate": 12.0}
    _write_phase_b_maintenance_records(
        fresh_root,
        fresh,
        records,
        recompute_manifest_hash=False,
    )

    result = compare_phase_b_arm(
        accepted_arm_root=accepted_root,
        fresh_arm_root=fresh_root,
        seed=0,
        arm="d_drift",
    )

    assert result["pass"] is False
    assert "fresh_arm:manifest_sha256_mismatch" in result["failures"]
    assert result["mismatch_count"] == 0

def _write_stage9_5_1_recovery_fixture(
    tmp_path: Path,
    *,
    system_a_verified: bool = True,
    stage8_verified: bool = True,
) -> Path:
    blockers: list[str] = []
    if not system_a_verified:
        blockers.append("system_a_checkpoint_bytes_missing")
    if not stage8_verified:
        blockers.append("stage8_large_artifact_archive_missing")
    report: dict[str, Any] = {
        "audit_id": "stage9.5-1-fresh-clone-reconstruction-v1_2",
        "status": "pass" if not blockers else "blocked",
        "pass": not blockers,
        "repository_head": _git_head(),
        "failures": [],
        "blockers": blockers,
        "external_artifacts": {
            "system_a_checkpoints": {
                "required": True,
                "verified_seeds": (
                    [0, 1, 2, 3, 4]
                    if system_a_verified
                    else [0, 1, 2, 3]
                ),
                "missing": (
                    []
                    if system_a_verified
                    else [{"seed": 4, "path": "seed_4.pt"}]
                ),
                "mismatches": [],
            },
            "stage8_large_artifact_archive": {
                "required": True,
                "requirement_count": 145,
                "verified_count": 145 if stage8_verified else 144,
                "missing": (
                    []
                    if stage8_verified
                    else [{"path": "phase_b/seed-4/maintenance.jsonl"}]
                ),
                "mismatches": [],
            },
        },
    }
    report["canonical_sha256"] = _canonical_sha256(report)
    path = tmp_path / "fresh_clone_reconstruction_report.json"
    path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path


def _synthetic_phase_a_result() -> dict[str, Any]:
    return {
        "pass": True,
        "complete_seeds": [0, 1, 2, 3, 4],
        "mismatch_count": 0,
        "failures": [],
        "seed_results": [
            {"seed": seed, "mismatches": []}
            for seed in range(5)
        ],
        "shared_identity_by_seed": {
            str(seed): f"{seed + 1:064x}" for seed in range(5)
        },
    }


def _synthetic_phase_b_result() -> dict[str, Any]:
    return {
        "pass": True,
        "complete_seeds": [0, 1, 2, 3, 4],
        "mismatch_count": 0,
        "failures": [],
        "seed_results": [
            {"seed": seed, "mismatches": []}
            for seed in range(5)
        ],
        "accepted_maintenance_archive_verified": True,
    }


def _synthetic_phase_c_preconditions() -> dict[str, Any]:
    return {
        "pass": True,
        "failures": [],
        "mismatch_count": 0,
        "mismatches": [],
        "failed_lineage_preserved": True,
        "scientific_blocks_equal": True,
    }


def _synthetic_phase_c_output() -> dict[str, Any]:
    return {
        "pass": True,
        "failures": [],
        "mismatch_count": 0,
        "mismatches": [],
    }


def _patch_synthetic_integrated_components(monkeypatch: Any) -> None:
    monkeypatch.setattr(
        comparator_module,
        "compare_phase_a",
        lambda **_: _synthetic_phase_a_result(),
    )
    monkeypatch.setattr(
        comparator_module,
        "compare_phase_b",
        lambda **_: _synthetic_phase_b_result(),
    )
    monkeypatch.setattr(
        comparator_module,
        "compare_phase_c_preconditions",
        lambda **_: _synthetic_phase_c_preconditions(),
    )
    monkeypatch.setattr(
        comparator_module,
        "compare_phase_c_corrected_output",
        lambda **_: _synthetic_phase_c_output(),
    )
    monkeypatch.setattr(
        comparator_module,
        "_verify_stage1_reconstruction_report",
        lambda *_args, **_kwargs: {
            "pass": True,
            "failures": [],
            "canonical_sha256": "a" * 64,
            "repository_head": _git_head(),
        },
    )
    monkeypatch.setattr(
        comparator_module,
        "_verify_accepted_stage8_archive_root",
        lambda *_args, **_kwargs: {
            "pass": True,
            "failures": [],
            "requirement_count": 145,
            "verified_count": 145,
            "inventory_sha256": "9" * 64,
        },
    )


def _run_synthetic_integrated_pipeline(
    tmp_path: Path,
    recovery_report: Path,
) -> dict[str, Any]:
    return run_integrated(
        accepted_root=tmp_path / "accepted",
        fresh_root=tmp_path / "fresh",
        accepted_correction_config_path=tmp_path / "accepted_config.json",
        fresh_correction_config_path=tmp_path / "fresh_config.json",
        stage1_report_path=tmp_path / "stage1_report.json",
        stage9_5_1_recovery_report_path=recovery_report,
        output_path=tmp_path / "replay_comparison_evidence.json",
        finalizer_output_dir=tmp_path / "finalized",
    )


def test_integrated_pipeline_binds_recovery_comparator_and_finalizer(
    monkeypatch: Any,
    tmp_path: Path,
) -> None:
    _patch_synthetic_integrated_components(monkeypatch)
    recovery_path = _write_stage9_5_1_recovery_fixture(tmp_path)

    integrated = _run_synthetic_integrated_pipeline(
        tmp_path,
        recovery_path,
    )

    evidence = integrated["comparison_evidence"]
    report = integrated["replay_report"]
    assert evidence["comparison_complete"] is True
    assert evidence["source_evidence_complete"] is True
    assert evidence["stage9_5_1_recovery_verified"] is True
    assert evidence["accepted_stage8_archive_identity_verified"] is True
    assert evidence["accepted_maintenance_archive_verified"] is True
    assert evidence["unresolved_class_a"] == []
    assert report["pass"] is True
    assert (
        report["construction"][
            "comparison_evidence_canonical_sha256"
        ]
        == evidence["canonical_sha256"]
    )
    assert (
        report["construction"][
            "stage9_5_1_recovery_report_canonical_sha256"
        ]
        == evidence["stage9_5_1_recovery_report_canonical_sha256"]
    )
    assert (tmp_path / "replay_comparison_evidence.json").is_file()
    assert (
        tmp_path
        / "finalized"
        / "replay_equivalence_report.json"
    ).is_file()


def test_integrated_pipeline_blocks_substituted_accepted_archive_root(
    monkeypatch: Any,
    tmp_path: Path,
) -> None:
    _patch_synthetic_integrated_components(monkeypatch)
    monkeypatch.setattr(
        comparator_module,
        "_verify_accepted_stage8_archive_root",
        lambda *_args, **_kwargs: {
            "pass": False,
            "failures": [
                "accepted_stage8_archive_sha256_mismatch:"
                "phase_a_shared_control_plane/seed-0/predictions.jsonl"
            ],
            "requirement_count": 145,
            "verified_count": 144,
            "inventory_sha256": "9" * 64,
        },
    )
    recovery_path = _write_stage9_5_1_recovery_fixture(tmp_path)

    integrated = _run_synthetic_integrated_pipeline(
        tmp_path,
        recovery_path,
    )

    evidence = integrated["comparison_evidence"]
    assert evidence["stage9_5_1_recovery_verified"] is True
    assert evidence["accepted_stage8_archive_identity_verified"] is False
    assert evidence["comparison_complete"] is False
    assert (
        "accepted_stage8_archive_identity_not_verified"
        in evidence["blockers"]
    )
    assert (
        "accepted_stage8_archive_identity_not_verified"
        in evidence["unresolved_class_a"]
    )
    assert integrated["replay_report"]["pass"] is False


def test_integrated_pipeline_blocks_each_missing_external_family(
    monkeypatch: Any,
    tmp_path: Path,
) -> None:
    _patch_synthetic_integrated_components(monkeypatch)
    cases = (
        (
            False,
            True,
            "system_a_checkpoint_family_not_verified",
        ),
        (
            True,
            False,
            "stage8_large_artifact_archive_not_verified",
        ),
    )
    for index, (system_ok, archive_ok, expected_blocker) in enumerate(cases):
        case_root = tmp_path / f"case-{index}"
        case_root.mkdir()
        recovery_path = _write_stage9_5_1_recovery_fixture(
            case_root,
            system_a_verified=system_ok,
            stage8_verified=archive_ok,
        )
        integrated = _run_synthetic_integrated_pipeline(
            case_root,
            recovery_path,
        )
        evidence = integrated["comparison_evidence"]
        assert evidence["comparison_complete"] is False
        assert evidence["stage9_5_1_recovery_verified"] is False
        assert expected_blocker in evidence["blockers"]
        assert "stage9_5_1_recovery_not_verified" in evidence[
            "unresolved_class_a"
        ]
        assert integrated["replay_report"]["pass"] is False


def test_integrated_pipeline_blocks_incomplete_phase_b_and_maintenance(
    monkeypatch: Any,
    tmp_path: Path,
) -> None:
    _patch_synthetic_integrated_components(monkeypatch)
    monkeypatch.setattr(
        comparator_module,
        "compare_phase_b",
        lambda **_: {
            "pass": False,
            "complete_seeds": [0, 1, 2, 3],
            "mismatch_count": 0,
            "failures": [
                "seed4:accepted_maintenance_invalid:FileNotFoundError"
            ],
            "seed_results": [
                {"seed": seed, "mismatches": []}
                for seed in range(4)
            ],
            "accepted_maintenance_archive_verified": False,
        },
    )
    recovery_path = _write_stage9_5_1_recovery_fixture(tmp_path)

    integrated = _run_synthetic_integrated_pipeline(
        tmp_path,
        recovery_path,
    )

    evidence = integrated["comparison_evidence"]
    assert evidence["comparison_complete"] is False
    assert "phase_b_comparison_failed" in evidence["blockers"]
    assert (
        "accepted_phase_b_maintenance_records_not_verified"
        in evidence["blockers"]
    )
    assert (
        "accepted_phase_b_maintenance_records_not_verified"
        in evidence["unresolved_class_a"]
    )
    assert integrated["replay_report"]["pass"] is False


def test_integrated_pipeline_blocks_failure_lineage_or_correction_mismatch(
    monkeypatch: Any,
    tmp_path: Path,
) -> None:
    _patch_synthetic_integrated_components(monkeypatch)
    monkeypatch.setattr(
        comparator_module,
        "compare_phase_c_preconditions",
        lambda **_: {
            "pass": False,
            "failures": [
                "accepted:failure.json:accepted_file_identity_mismatch",
                "scientific_block_mismatch:fusion",
            ],
            "mismatch_count": 1,
            "mismatches": ["correction_config.fusion"],
            "failed_lineage_preserved": False,
            "scientific_blocks_equal": False,
        },
    )
    recovery_path = _write_stage9_5_1_recovery_fixture(tmp_path)

    integrated = _run_synthetic_integrated_pipeline(
        tmp_path,
        recovery_path,
    )

    evidence = integrated["comparison_evidence"]
    assert evidence["comparison_complete"] is False
    assert evidence["phase_c"]["original_failure_lineage_preserved"] is False
    assert (
        evidence[
            "regenerated_correction_config_all_scientific_blocks_equal"
        ]
        is False
    )
    assert "phase_c_preconditions_failed" in evidence["blockers"]
    assert "replay_equivalence_comparison_incomplete" in evidence[
        "unresolved_class_a"
    ]
    assert integrated["replay_report"]["pass"] is False


def test_recovery_report_verifier_rejects_unverified_external_families(
    tmp_path: Path,
) -> None:
    system_missing = _write_stage9_5_1_recovery_fixture(
        tmp_path,
        system_a_verified=False,
    )
    system_result = _verify_stage9_5_1_recovery_report(system_missing)
    assert system_result["pass"] is False
    assert (
        "system_a_checkpoint_family_not_verified"
        in system_result["blockers"]
    )

    archive_root = tmp_path / "archive-case"
    archive_root.mkdir()
    archive_missing = _write_stage9_5_1_recovery_fixture(
        archive_root,
        stage8_verified=False,
    )
    archive_result = _verify_stage9_5_1_recovery_report(archive_missing)
    assert archive_result["pass"] is False
    assert (
        "stage8_large_artifact_archive_not_verified"
        in archive_result["blockers"]
    )

