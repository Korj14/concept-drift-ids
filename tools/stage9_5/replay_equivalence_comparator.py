from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONSTRUCTION_CONTRACT_PATH = (
    PROJECT_ROOT
    / "data"
    / "manifests"
    / "stage9_5_6_replay_report_construction_v1.json"
)
SEEDS = (0, 1, 2, 3, 4)
PHASE_A_SUBDIR = "phase_a_shared_control_plane"
NORMALIZED_DIAGNOSTIC = "<stage9.5-6-diagnostic-normalized>"
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


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_head() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _verify_run_manifest_hashes(
    manifest: dict[str, Any],
    *,
    label: str,
) -> list[str]:
    failures: list[str] = []
    payload_hash = manifest.get("payload_sha256")
    manifest_hash = manifest.get("manifest_sha256")
    if not isinstance(payload_hash, str) or SHA256_RE.fullmatch(payload_hash) is None:
        failures.append(f"{label}:invalid_payload_sha256")
    if not isinstance(manifest_hash, str) or SHA256_RE.fullmatch(manifest_hash) is None:
        failures.append(f"{label}:invalid_manifest_sha256")

    payload_core = dict(manifest)
    payload_core.pop("payload_sha256", None)
    if (
        isinstance(payload_hash, str)
        and SHA256_RE.fullmatch(payload_hash) is not None
        and _canonical_sha256(payload_core) != payload_hash
    ):
        failures.append(f"{label}:payload_sha256_mismatch")

    manifest_core = dict(payload_core)
    manifest_core.pop("manifest_sha256", None)
    if (
        isinstance(manifest_hash, str)
        and SHA256_RE.fullmatch(manifest_hash) is not None
        and _canonical_sha256(manifest_core) != manifest_hash
    ):
        failures.append(f"{label}:manifest_sha256_mismatch")
    return failures


def _verify_manifest_files(
    root: Path,
    manifest: dict[str, Any],
    *,
    label: str,
) -> list[str]:
    failures: list[str] = []
    files = manifest.get("files")
    if not isinstance(files, dict):
        return [f"{label}:files_not_object"]

    resolved_root = root.resolve()
    for name, descriptor in sorted(files.items()):
        if not isinstance(name, str) or not isinstance(descriptor, dict):
            failures.append(f"{label}:invalid_file_descriptor:{name}")
            continue
        relative = descriptor.get("path")
        expected_sha = descriptor.get("sha256")
        if not isinstance(relative, str):
            failures.append(f"{label}:invalid_file_path:{name}")
            continue
        if not isinstance(expected_sha, str) or SHA256_RE.fullmatch(expected_sha) is None:
            failures.append(f"{label}:invalid_file_sha256:{name}")
            continue

        relative_path = Path(relative)
        if relative_path.is_absolute():
            failures.append(f"{label}:absolute_file_path:{name}")
            continue
        path = (resolved_root / relative_path).resolve()
        if not path.is_relative_to(resolved_root):
            failures.append(f"{label}:file_path_escape:{name}")
            continue
        if not path.is_file():
            failures.append(f"{label}:missing_file:{name}")
            continue
        actual_sha = _sha256_file(path)
        if actual_sha != expected_sha:
            failures.append(f"{label}:file_sha256_mismatch:{name}")
    return failures


def _project_phase_a_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    projected = copy.deepcopy(manifest)

    # Both hashes are first verified against the raw manifest. They are then
    # removed from the replay projection because each transitively depends on
    # the predeclared diagnostic runtime fields normalized below.
    projected.pop("payload_sha256", None)
    projected.pop("manifest_sha256", None)

    runtime = projected.get("runtime")
    if not isinstance(runtime, dict):
        raise TypeError("Phase-A run manifest runtime must be an object")

    if "platform" in runtime:
        runtime["platform"] = NORMALIZED_DIAGNOSTIC
    if "processor" in runtime:
        runtime["processor"] = NORMALIZED_DIAGNOSTIC

    threadpool = runtime.get("threadpool_info")
    if not isinstance(threadpool, list):
        raise TypeError("Phase-A runtime.threadpool_info must be a list")
    for item in threadpool:
        if not isinstance(item, dict):
            raise TypeError("Phase-A threadpool_info entries must be objects")
        if "filepath" in item:
            item["filepath"] = NORMALIZED_DIAGNOSTIC
    return projected


def _difference_paths(left: Any, right: Any, prefix: str = "") -> list[str]:
    if type(left) is not type(right):
        return [prefix or "<root>"]
    if isinstance(left, dict):
        paths: list[str] = []
        keys = sorted(set(left) | set(right))
        for key in keys:
            child = f"{prefix}.{key}" if prefix else str(key)
            if key not in left or key not in right:
                paths.append(child)
                continue
            paths.extend(_difference_paths(left[key], right[key], child))
        return paths
    if isinstance(left, list):
        if len(left) != len(right):
            return [f"{prefix}.length"]
        paths = []
        for index, (lval, rval) in enumerate(zip(left, right)):
            child = f"{prefix}[{index}]"
            paths.extend(_difference_paths(lval, rval, child))
        return paths
    return [] if left == right else [prefix or "<root>"]


def compare_phase_a_seed(
    *,
    accepted_seed_root: Path,
    fresh_seed_root: Path,
    seed: int,
) -> dict[str, Any]:
    accepted_manifest_path = accepted_seed_root / "run_manifest.json"
    fresh_manifest_path = fresh_seed_root / "run_manifest.json"

    failures: list[str] = []
    try:
        accepted = _load_json(accepted_manifest_path)
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        return {
            "seed": seed,
            "pass": False,
            "failures": [f"accepted_manifest_invalid:{type(exc).__name__}"],
            "mismatch_count": 0,
            "mismatches": [],
        }
    try:
        fresh = _load_json(fresh_manifest_path)
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        return {
            "seed": seed,
            "pass": False,
            "failures": [f"fresh_manifest_invalid:{type(exc).__name__}"],
            "mismatch_count": 0,
            "mismatches": [],
        }

    failures.extend(_verify_run_manifest_hashes(accepted, label="accepted"))
    failures.extend(_verify_run_manifest_hashes(fresh, label="fresh"))
    failures.extend(
        _verify_manifest_files(accepted_seed_root, accepted, label="accepted")
    )
    failures.extend(_verify_manifest_files(fresh_seed_root, fresh, label="fresh"))

    try:
        accepted_projection = _project_phase_a_manifest(accepted)
        fresh_projection = _project_phase_a_manifest(fresh)
    except (TypeError, ValueError) as exc:
        failures.append(f"projection_invalid:{type(exc).__name__}:{exc}")
        accepted_projection = None
        fresh_projection = None

    mismatches: list[str] = []
    accepted_projected_sha256: str | None = None
    fresh_projected_sha256: str | None = None
    if accepted_projection is not None and fresh_projection is not None:
        accepted_projected_sha256 = _canonical_sha256(accepted_projection)
        fresh_projected_sha256 = _canonical_sha256(fresh_projection)
        if accepted_projected_sha256 != fresh_projected_sha256:
            mismatches = _difference_paths(accepted_projection, fresh_projection)

    return {
        "seed": seed,
        "pass": not failures and not mismatches,
        "failures": failures,
        "mismatch_count": len(mismatches),
        "mismatches": mismatches,
        "accepted_projected_sha256": accepted_projected_sha256,
        "fresh_projected_sha256": fresh_projected_sha256,
        "projection": {
            "normalized_runtime_fields": [
                "runtime.platform",
                "runtime.processor",
                "runtime.threadpool_info[*].filepath",
            ],
            "raw_hashes_verified_before_projection": [
                "payload_sha256",
                "manifest_sha256",
            ],
            "derived_hash_fields_removed_after_verification": [
                "payload_sha256",
                "manifest_sha256",
            ],
            "all_file_descriptors_verified_against_bytes": True,
        },
    }


def compare_phase_a(
    *,
    accepted_root: Path,
    fresh_root: Path,
) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    for seed in SEEDS:
        accepted_seed_root = accepted_root / PHASE_A_SUBDIR / f"seed-{seed}"
        fresh_seed_root = fresh_root / PHASE_A_SUBDIR / f"seed-{seed}"
        results.append(
            compare_phase_a_seed(
                accepted_seed_root=accepted_seed_root,
                fresh_seed_root=fresh_seed_root,
                seed=seed,
            )
        )
    complete = [int(item["seed"]) for item in results if item["pass"] is True]
    mismatch_count = sum(int(item["mismatch_count"]) for item in results)
    failures = [
        f"seed{item['seed']}:{failure}"
        for item in results
        for failure in item["failures"]
    ]
    return {
        "pass": len(complete) == len(SEEDS) and mismatch_count == 0 and not failures,
        "complete_seeds": complete,
        "mismatch_count": mismatch_count,
        "failures": failures,
        "seed_results": results,
    }


def run(
    *,
    accepted_root: Path,
    fresh_root: Path,
    output_path: Path,
) -> dict[str, Any]:
    contract = _load_json(CONSTRUCTION_CONTRACT_PATH)
    phase_a = compare_phase_a(accepted_root=accepted_root, fresh_root=fresh_root)
    mismatches = [
        {
            "phase": "phase_a",
            "seed": item["seed"],
            "paths": item["mismatches"],
        }
        for item in phase_a["seed_results"]
        if item["mismatches"]
    ]
    failures = list(phase_a["failures"])
    blockers = [
        "phase_b_comparator_not_implemented",
        "phase_c_comparator_not_implemented",
    ]

    evidence: dict[str, Any] = {
        "audit_id": "stage9.5-6-replay-equivalence-comparison-v1",
        "schema_version": 1,
        "producer_id": "stage9.5-6-replay-equivalence-comparator-v1",
        "audited_head": _git_head(),
        "manual_override_used": False,
        "comparison_complete": False,
        "source_evidence_complete": False,
        "mismatch_count": int(phase_a["mismatch_count"]),
        "mismatches": mismatches,
        "failures": failures,
        "blockers": blockers,
        "phase_a": {
            "complete_seeds": phase_a["complete_seeds"],
            "pass": phase_a["pass"],
            "seed_results": phase_a["seed_results"],
        },
        "phase_b": {
            "complete_seeds": [],
            "pass": False,
            "status": "not_implemented_blocked",
        },
        "phase_c": {
            "rerun_seed": 0,
            "original_failure_lineage_preserved": False,
            "corrected_rerun_complete": False,
            "pass": False,
            "status": "not_implemented_blocked",
        },
        "accepted_maintenance_archive_verified": False,
        "stage1_reconstructed_under_historical_environment": False,
        "regenerated_correction_config_all_scientific_blocks_equal": False,
        "historical_heads": {
            "phase_a_b": "bfa14b942e4a5b2fbfa8aa3c43728a7f1cd81645",
            "correction_source": "79ddc4c6d6dea52c7cabc55a6d082448fc24fcf9",
        },
        "accepted_correction_manifest_sha256": (
            "d380fce5f9db8f0b639dc999298a263b10a10a3d02e35def226a121d098e2222"
        ),
        "accepted_stage8_evidence_commit": (
            "c2ded83b8195b9321e715626c1f305f9627936e8"
        ),
        "unresolved_class_a": [
            "replay_equivalence_comparator_phase_b_not_implemented",
            "replay_equivalence_comparator_phase_c_not_implemented",
        ],
        "scientific_objects_modified": False,
        "stage10_outcomes_accessed": False,
        "construction_contract_id": contract["contract_id"],
    }
    evidence["canonical_sha256"] = _canonical_sha256(evidence)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(evidence, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return evidence


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Stage 9.5-6 deterministic replay-equivalence comparator"
    )
    parser.add_argument("--accepted-root", type=Path, required=True)
    parser.add_argument("--fresh-root", type=Path, required=True)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(
            "results/audits/stage9_5_full_seed_rerun_v1/"
            "replay_comparison_evidence.json"
        ),
    )
    args = parser.parse_args()

    evidence = run(
        accepted_root=args.accepted_root,
        fresh_root=args.fresh_root,
        output_path=args.output,
    )
    if not evidence["phase_a"]["pass"]:
        raise SystemExit("Stage 9.5-6 Phase-A replay comparison failed.")
    raise SystemExit(
        "Stage 9.5-6 remains blocked: Phase-B and Phase-C comparator "
        "implementation is not yet frozen."
    )


if __name__ == "__main__":
    main()
