from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from concept_drift_ids.cd_control_plane import (
    canonical_sha256,
    write_json_new,
)
from concept_drift_ids.cd_primary_config import (
    PRIMARY_OUTPUT_ROOT,
    PRIMARY_SEEDS,
    PROJECT_ROOT,
    require_clean_worktree,
    verify_primary_run_config_for_execution,
)
from concept_drift_ids.cd_primary_phase_c import (
    ARM_NAMES,
    _phase_b_dir,
    _phase_c_dir,
    _phase_c_root,
    verify_phase_c_seed,
)
from concept_drift_ids.scenario_manifest import sha256_file


COMPACT_EXPORT_ROOT = (
    PROJECT_ROOT / "results" / "frozen" / "cd_primary_v1"
)


def _copy_new(source: Path, target: Path) -> dict[str, str]:
    if target.exists():
        raise FileExistsError(f"Refusing to overwrite compact export: {target}")
    if not source.is_file():
        raise FileNotFoundError(f"Missing primary evidence source: {source}")
    target.parent.mkdir(parents=True, exist_ok=True)
    data = source.read_bytes()
    with target.open("xb") as file:
        file.write(data)
    source_sha = sha256_file(source)
    target_sha = sha256_file(target)
    if source_sha != target_sha:
        raise ValueError("Compact export byte identity changed during copy.")
    return {
        "source_path": source.relative_to(PROJECT_ROOT).as_posix(),
        "export_path": target.relative_to(PROJECT_ROOT).as_posix(),
        "sha256": source_sha,
    }


def _phase_a_compact_files(seed: int) -> tuple[Path, ...]:
    root = (
        PRIMARY_OUTPUT_ROOT
        / "phase_a_shared_control_plane"
        / f"seed-{seed}"
    )
    return (
        root / "run_manifest.json",
        root / "shared_identity.json",
        root / "input_identity.json",
        root / "checkpoint_chain.jsonl",
    )


def _phase_b_compact_files(seed: int) -> tuple[Path, ...]:
    root = _phase_b_dir(seed)
    files: list[Path] = [root / "phase_b_manifest.json"]
    for arm in ARM_NAMES:
        arm_root = root / arm
        files.extend(
            (
                arm_root / "arm_manifest.json",
                arm_root / "initial_state.json",
                arm_root / "final_state.json",
            )
        )
        versions = arm_root / "versions"
        if versions.exists():
            files.extend(sorted(versions.glob("*.json")))
    return tuple(files)


def _phase_c_compact_files(seed: int) -> tuple[Path, ...]:
    root = _phase_c_dir(seed)
    files: list[Path] = [root / "phase_c_seed_manifest.json"]
    files.extend(root / f"{arm}_evaluation.json" for arm in ARM_NAMES)
    return tuple(files)


def export_primary_compact_evidence() -> dict[str, Any]:
    config = verify_primary_run_config_for_execution()
    require_clean_worktree()
    for seed in PRIMARY_SEEDS:
        verify_phase_c_seed(seed)

    confirmatory = _phase_c_root() / "confirmatory_analysis.json"
    if not confirmatory.is_file():
        raise FileNotFoundError(
            "Five-seed confirmatory aggregate must exist before compact export."
        )
    if COMPACT_EXPORT_ROOT.exists():
        raise FileExistsError(
            f"Compact primary export already exists: {COMPACT_EXPORT_ROOT}"
        )

    descriptors: list[dict[str, str]] = []
    for seed in PRIMARY_SEEDS:
        for source in (
            *_phase_a_compact_files(seed),
            *_phase_b_compact_files(seed),
            *_phase_c_compact_files(seed),
        ):
            relative = source.relative_to(PRIMARY_OUTPUT_ROOT)
            target = COMPACT_EXPORT_ROOT / relative
            descriptors.append(_copy_new(source, target))

    descriptors.append(
        _copy_new(
            confirmatory,
            COMPACT_EXPORT_ROOT / "phase_c_offline_evaluation"
            / "confirmatory_analysis.json",
        )
    )

    manifest = {
        "schema_version": 1,
        "status": "complete_primary_compact_evidence_export",
        "primary_config_manifest_sha256": config["manifest_sha256"],
        "files": descriptors,
        "large_artifact_root": "artifacts/cd_primary_v1",
        "large_artifact_archive_required_for_publication": True,
        "large_prediction_traces_in_git": False,
        "adaptive_checkpoint_bytes_in_git": False,
    }
    manifest["manifest_sha256"] = canonical_sha256(manifest)
    write_json_new(
        COMPACT_EXPORT_ROOT / "compact_export_manifest.json",
        manifest,
    )
    return {
        "status": "primary_compact_evidence_export_written",
        "manifest_sha256": manifest["manifest_sha256"],
        "file_count": len(descriptors),
        "next_gate": "review changed files then commit compact evidence",
    }


def verify_primary_compact_export() -> dict[str, Any]:
    path = COMPACT_EXPORT_ROOT / "compact_export_manifest.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    stored_payload = payload.pop("payload_sha256", None)
    if stored_payload is not None and canonical_sha256(payload) != stored_payload:
        raise ValueError("Compact export payload hash mismatch.")
    stored_manifest = payload.pop("manifest_sha256", None)
    if stored_manifest != canonical_sha256(payload):
        raise ValueError("Compact export manifest hash mismatch.")
    for descriptor in payload["files"]:
        source = PROJECT_ROOT / descriptor["source_path"]
        target = PROJECT_ROOT / descriptor["export_path"]
        expected = descriptor["sha256"]
        if sha256_file(source) != expected:
            raise ValueError("Large artifact changed after compact export.")
        if sha256_file(target) != expected:
            raise ValueError("Compact exported file hash mismatch.")
    return {
        "status": "primary_compact_evidence_export_verified",
        "manifest_sha256": stored_manifest,
        "file_count": len(payload["files"]),
    }


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Export or verify compact primary C/D evidence after full evaluation."
    )
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    result = (
        verify_primary_compact_export()
        if args.verify_only
        else export_primary_compact_evidence()
    )
    print(json.dumps(result, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
