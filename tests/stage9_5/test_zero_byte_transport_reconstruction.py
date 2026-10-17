from __future__ import annotations

import json
import shutil
from pathlib import Path

from tools.stage9_5.zero_byte_transport_reconstruction import (
    CONTRACT_PATH,
    EMPTY_SHA256,
    PROJECT_ROOT,
    _canonical_sha256,
    _validate_forensic_basis,
    run,
)



def test_forensic_basis_resolves_pinned_git_blobs_not_live_worktree() -> None:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    assert _validate_forensic_basis(contract) == []

def _materialized_archive(tmp_path: Path) -> Path:
    root = tmp_path / "cd_primary_v1"
    for seed in range(5):
        relative = (
            Path("phase_b_symbolic_arms")
            / f"seed-{seed}"
            / "c_frozen_symbolic"
        )
        target_dir = root / relative
        target_dir.mkdir(parents=True, exist_ok=True)
        source = (
            PROJECT_ROOT
            / "results"
            / "frozen"
            / "cd_primary_v1"
            / relative
            / "arm_manifest.json"
        )
        shutil.copyfile(source, target_dir / "arm_manifest.json")
    return root


def test_reconstructs_exactly_five_manifest_bound_empty_files(
    tmp_path: Path,
) -> None:
    root = _materialized_archive(tmp_path)
    output = tmp_path / "report.json"

    report = run(stage8_archive_root=root, output_path=output)

    assert report["pass"] is True
    assert report["reconstructed_count"] == 5
    assert report["preexisting_verified_count"] == 0
    assert report["failures"] == []
    for seed in range(5):
        path = (
            root
            / "phase_b_symbolic_arms"
            / f"seed-{seed}"
            / "c_frozen_symbolic"
            / "maintenance.jsonl"
        )
        assert path.is_file()
        assert path.read_bytes() == b""
    core = dict(report)
    observed = core.pop("canonical_sha256")
    assert observed == _canonical_sha256(core)


def test_bad_materialized_arm_manifest_prevents_all_writes(
    tmp_path: Path,
) -> None:
    root = _materialized_archive(tmp_path)
    bad = (
        root
        / "phase_b_symbolic_arms"
        / "seed-2"
        / "c_frozen_symbolic"
        / "arm_manifest.json"
    )
    bad.write_text("{}\n", encoding="utf-8")

    report = run(
        stage8_archive_root=root,
        output_path=tmp_path / "report.json",
    )

    assert report["pass"] is False
    assert "seed2:materialized_arm_manifest_byte_mismatch" in report["failures"]
    for seed in range(5):
        path = (
            root
            / "phase_b_symbolic_arms"
            / f"seed-{seed}"
            / "c_frozen_symbolic"
            / "maintenance.jsonl"
        )
        assert not path.exists()


def test_preexisting_correct_empty_file_is_preserved_not_recreated(
    tmp_path: Path,
) -> None:
    root = _materialized_archive(tmp_path)
    existing = (
        root
        / "phase_b_symbolic_arms"
        / "seed-0"
        / "c_frozen_symbolic"
        / "maintenance.jsonl"
    )
    existing.touch()
    before = existing.stat().st_mtime_ns

    report = run(
        stage8_archive_root=root,
        output_path=tmp_path / "report.json",
    )

    assert report["pass"] is True
    assert report["preexisting_verified_count"] == 1
    assert report["reconstructed_count"] == 4
    assert existing.stat().st_mtime_ns == before
    item0 = next(item for item in report["items"] if item["seed"] == 0)
    assert item0["state_before"] == "preexisting_verified"
    assert item0["state_after"] == "preexisting_verified"


def test_nonempty_preexisting_target_is_rejected_without_other_writes(
    tmp_path: Path,
) -> None:
    root = _materialized_archive(tmp_path)
    bad_target = (
        root
        / "phase_b_symbolic_arms"
        / "seed-4"
        / "c_frozen_symbolic"
        / "maintenance.jsonl"
    )
    bad_target.write_bytes(b"not-empty")

    report = run(
        stage8_archive_root=root,
        output_path=tmp_path / "report.json",
    )

    assert report["pass"] is False
    assert "seed4:preexisting_target_not_empty" in report["failures"]
    assert "seed4:preexisting_target_sha_mismatch" in report["failures"]
    for seed in range(4):
        path = (
            root
            / "phase_b_symbolic_arms"
            / f"seed-{seed}"
            / "c_frozen_symbolic"
            / "maintenance.jsonl"
        )
        assert not path.exists()
    assert bad_target.read_bytes() == b"not-empty"


def test_all_reconstructed_files_match_frozen_empty_sha(tmp_path: Path) -> None:
    root = _materialized_archive(tmp_path)
    report = run(
        stage8_archive_root=root,
        output_path=tmp_path / "report.json",
    )
    assert report["pass"] is True
    for item in report["items"]:
        target = Path(item["target_path"])
        import hashlib

        assert hashlib.sha256(target.read_bytes()).hexdigest() == EMPTY_SHA256


def test_report_never_claims_original_dropbox_object_recovery(
    tmp_path: Path,
) -> None:
    root = _materialized_archive(tmp_path)
    report = run(
        stage8_archive_root=root,
        output_path=tmp_path / "report.json",
    )

    assert report["pass"] is True
    assert report["original_dropbox_objects_recovered"] is False
    assert report["transport_reconstruction_explicit"] is True
    assert report["governing_verifier_unchanged"] is True
    written = json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))
    assert written == report
