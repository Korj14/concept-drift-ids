from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from tools.stage9_5.replay_equivalence_comparator import (
    NORMALIZED_DIAGNOSTIC,
    _canonical_sha256,
    _project_phase_a_manifest,
    compare_phase_a_seed,
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
