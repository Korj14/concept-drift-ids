from __future__ import annotations

import copy
import json
import shutil
from pathlib import Path
from typing import Any

import pytest

from tools.stage9_5.regenerated_correction_config_verifier import (
    ACCEPTED_CORRECTION_CONFIG_PATH,
    ACCEPTED_CORRECTION_MANIFEST_SHA256,
    ACCEPTED_STAGE8_EVIDENCE_COMMIT,
    CORRECTION_SOURCE_HEAD,
    FROZEN_SCIENTIFIC_BLOCKS,
    HISTORICAL_PHASE_A_B_HEAD,
    PHASE_A_SUBDIR,
    PHASE_B_SUBDIR,
    PROJECT_ROOT,
    SEEDS,
    _canonical_sha256,
    verify_regenerated_correction_config,
)


def _accepted_config() -> dict[str, Any]:
    path = PROJECT_ROOT / ACCEPTED_CORRECTION_CONFIG_PATH
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _rehash(payload: dict[str, Any]) -> dict[str, Any]:
    updated = copy.deepcopy(payload)
    updated.pop("payload_sha256", None)
    updated.pop("manifest_sha256", None)
    updated["manifest_sha256"] = _canonical_sha256(updated)
    payload_core = dict(updated)
    updated["payload_sha256"] = _canonical_sha256(payload_core)
    return updated


def _write_config(tmp_path: Path, payload: dict[str, Any]) -> Path:
    path = tmp_path / "cd_primary_run_config_v1_1.json"
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path


def _compact_root() -> Path:
    return PROJECT_ROOT / "results" / "frozen" / "cd_primary_v1"


def _copy_upstream_manifests(tmp_path: Path) -> Path:
    source_root = _compact_root()
    target_root = tmp_path / "fresh-artifacts"
    for seed in SEEDS:
        for subdir, name in (
            (PHASE_A_SUBDIR, "run_manifest.json"),
            (PHASE_B_SUBDIR, "phase_b_manifest.json"),
        ):
            source = source_root / subdir / f"seed-{seed}" / name
            target = target_root / subdir / f"seed-{seed}" / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
    return target_root


def test_valid_regenerated_correction_config_is_accepted(tmp_path: Path) -> None:
    config_path = _write_config(tmp_path, _accepted_config())

    report = verify_regenerated_correction_config(
        config_path,
        _compact_root(),
    )

    assert report["pass"] is True
    assert report["status"] == "pass"
    assert report["failures"] == []
    assert report["scientific_blocks_equal"] is True
    assert report["scientific_block_mismatches"] == []
    assert report["bindings"] == {
        "historical_phase_a_b_head": HISTORICAL_PHASE_A_B_HEAD,
        "correction_source_head": CORRECTION_SOURCE_HEAD,
        "accepted_correction_manifest_sha256": (
            ACCEPTED_CORRECTION_MANIFEST_SHA256
        ),
        "accepted_stage8_evidence_commit": ACCEPTED_STAGE8_EVIDENCE_COMMIT,
    }
    assert report["post_outcome_scientific_field_changes_permitted"] is False
    assert report["phase_c_outcomes_accessed"] is False
    assert report["stage10_outcomes_accessed"] is False


@pytest.mark.parametrize("block", FROZEN_SCIENTIFIC_BLOCKS)
def test_each_frozen_scientific_block_mutation_is_rejected(
    tmp_path: Path,
    block: str,
) -> None:
    config = _accepted_config()
    mutated = copy.deepcopy(config)
    value = mutated[block]
    assert isinstance(value, dict)
    value["__stage9_5_scientific_mutation__"] = block
    config_path = _write_config(tmp_path, _rehash(mutated))

    report = verify_regenerated_correction_config(
        config_path,
        _compact_root(),
    )

    assert report["pass"] is False
    assert report["scientific_blocks_equal"] is False
    assert block in report["scientific_block_mismatches"]
    assert f"scientific_block_mismatch:{block}" in report["failures"]


def test_regenerated_correction_source_head_mutation_is_rejected(
    tmp_path: Path,
) -> None:
    config = _accepted_config()
    mutated = copy.deepcopy(config)
    ready = mutated["implementation_ready"]
    assert isinstance(ready, dict)
    ready["prepared_from_git_commit"] = "0" * 40
    config_path = _write_config(tmp_path, _rehash(mutated))

    report = verify_regenerated_correction_config(
        config_path,
        _compact_root(),
    )

    assert report["pass"] is False
    assert "regenerated_correction_source_head_mismatch" in report["failures"]


def test_regenerated_phase_a_manifest_must_bind_historical_head(
    tmp_path: Path,
) -> None:
    artifact_root = _copy_upstream_manifests(tmp_path)
    config = _accepted_config()

    manifest_path = (
        artifact_root
        / PHASE_A_SUBDIR
        / "seed-0"
        / "run_manifest.json"
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert isinstance(manifest, dict)
    manifest["git_commit"] = "0" * 40
    manifest = _rehash(manifest)
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    correction = config["correction"]
    assert isinstance(correction, dict)
    reused = correction["reused_upstream_artifacts"]
    assert isinstance(reused, dict)
    phase_a = reused["phase_a"]
    assert isinstance(phase_a, dict)
    seed_zero = phase_a["0"]
    assert isinstance(seed_zero, dict)
    seed_zero["run_manifest_sha256"] = manifest["manifest_sha256"]
    config_path = _write_config(tmp_path, _rehash(config))

    report = verify_regenerated_correction_config(
        config_path,
        artifact_root,
    )

    assert report["pass"] is False
    assert "regenerated_phase_a_head_mismatch:0" in report["failures"]


def test_wrong_accepted_stage8_evidence_identity_is_rejected(
    tmp_path: Path,
) -> None:
    config_path = _write_config(tmp_path, _accepted_config())

    report = verify_regenerated_correction_config(
        config_path,
        _compact_root(),
        accepted_evidence_commit="f" * 40,
    )

    assert report["pass"] is False
    assert any(
        item.startswith("accepted_stage8_evidence_commit_missing:")
        for item in report["failures"]
    )


def test_wrong_accepted_correction_manifest_identity_is_rejected(
    tmp_path: Path,
) -> None:
    config_path = _write_config(tmp_path, _accepted_config())

    report = verify_regenerated_correction_config(
        config_path,
        _compact_root(),
        accepted_correction_manifest_sha256="f" * 64,
    )

    assert report["pass"] is False
    assert "accepted_correction_manifest_identity_mismatch" in report["failures"]
