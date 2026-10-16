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
PHASE_B_SUBDIR = "phase_b_symbolic_arms"
ARM_NAMES = ("c_frozen_symbolic", "d_drift", "d_periodic")
NORMALIZED_DIAGNOSTIC = "<stage9.5-6-diagnostic-normalized>"
PHASE_B_RECORD_TIMING_FIELDS = (
    "shap_seconds",
    "surrogate_seconds",
    "lifecycle_seconds",
)
PHASE_B_SUMMARY_TIMING_FIELDS = (
    "compute_seconds",
    "shap_seconds",
    "surrogate_seconds",
    "lifecycle_seconds",
    "compute_seconds_per_opportunity",
    "compute_seconds_per_publication",
)
PHASE_C_FAILED_SUBDIR = "phase_c_offline_evaluation"
PHASE_C_CORRECTION_MANIFEST_SHA256 = (
    "d380fce5f9db8f0b639dc999298a263b10a10a3d02e35def226a121d098e2222"
)
PHASE_C_CORRECTION_SOURCE_HEAD = "79ddc4c6d6dea52c7cabc55a6d082448fc24fcf9"
PHASE_C_TRANSITIVE_IDENTITY = "<stage9.5-6-upstream-identity-normalized>"
PHASE_C_FROZEN_SCIENTIFIC_BLOCKS = (
    "governing_source_hashes",
    "scenario",
    "system_a",
    "r0_v2",
    "primary_control_plane",
    "primary_symbolic_operator",
    "fusion",
    "analysis",
)
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



def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        if not line.strip():
            continue
        try:
            payload = json.loads(line, object_pairs_hook=_reject_duplicate_pairs)
        except (json.JSONDecodeError, ValueError) as exc:
            raise ValueError(
                f"Invalid JSONL record at {path}:{line_number}: {exc}"
            ) from exc
        if not isinstance(payload, dict):
            raise TypeError(
                f"Expected JSON object at {path}:{line_number}"
            )
        records.append(payload)
    return records


def _safe_descriptor_path(
    root: Path,
    descriptor: dict[str, Any],
) -> Path:
    relative = descriptor.get("path")
    if not isinstance(relative, str):
        raise TypeError("Descriptor path must be a string")
    relative_path = Path(relative)
    if relative_path.is_absolute():
        raise ValueError("Descriptor path must be repository-relative")
    resolved_root = root.resolve()
    path = (resolved_root / relative_path).resolve()
    if not path.is_relative_to(resolved_root):
        raise ValueError("Descriptor path escapes its artifact root")
    return path


def _project_phase_b_maintenance_record(
    record: dict[str, Any],
) -> dict[str, Any]:
    projected = copy.deepcopy(record)
    for field in PHASE_B_RECORD_TIMING_FIELDS:
        projected.pop(field, None)
    generation = projected.get("generation_payload")
    if isinstance(generation, dict):
        generation.pop("timing_seconds", None)
    elif generation is not None:
        raise TypeError("generation_payload must be an object or null")
    return projected


def _project_phase_b_arm_manifest(
    manifest: dict[str, Any],
) -> dict[str, Any]:
    projected = copy.deepcopy(manifest)
    projected.pop("payload_sha256", None)
    projected.pop("manifest_sha256", None)

    summary = projected.get("maintenance_summary")
    if not isinstance(summary, dict):
        raise TypeError("Phase-B maintenance_summary must be an object")
    for field in PHASE_B_SUMMARY_TIMING_FIELDS:
        summary.pop(field, None)

    files = projected.get("files")
    if not isinstance(files, dict):
        raise TypeError("Phase-B arm files must be an object")
    maintenance = files.get("maintenance")
    if not isinstance(maintenance, dict):
        raise TypeError("Phase-B maintenance descriptor must be an object")
    # Raw bytes are verified before projection. This hash is removed only
    # because the maintenance JSONL byte identity transitively depends on the
    # predeclared timing fields projected from each record.
    maintenance.pop("sha256", None)
    return projected


def _verify_phase_b_arm_descriptor(
    seed_root: Path,
    descriptor: dict[str, Any],
    *,
    arm: str,
    label: str,
) -> list[str]:
    failures: list[str] = []
    raw_sha = descriptor.get("sha256")
    manifest_sha = descriptor.get("manifest_sha256")
    if not isinstance(raw_sha, str) or SHA256_RE.fullmatch(raw_sha) is None:
        failures.append(f"{label}:{arm}:invalid_arm_file_sha256")
    if (
        not isinstance(manifest_sha, str)
        or SHA256_RE.fullmatch(manifest_sha) is None
    ):
        failures.append(f"{label}:{arm}:invalid_arm_manifest_sha256")
    try:
        path = _safe_descriptor_path(seed_root, descriptor)
    except (TypeError, ValueError) as exc:
        failures.append(
            f"{label}:{arm}:invalid_arm_manifest_path:"
            f"{type(exc).__name__}"
        )
        return failures
    if not path.is_file():
        failures.append(f"{label}:{arm}:missing_arm_manifest")
        return failures
    if (
        isinstance(raw_sha, str)
        and SHA256_RE.fullmatch(raw_sha) is not None
        and _sha256_file(path) != raw_sha
    ):
        failures.append(f"{label}:{arm}:arm_manifest_file_sha256_mismatch")
    try:
        payload = _load_json(path)
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        failures.append(
            f"{label}:{arm}:arm_manifest_invalid:{type(exc).__name__}"
        )
        return failures
    if payload.get("manifest_sha256") != manifest_sha:
        failures.append(f"{label}:{arm}:arm_manifest_identity_mismatch")
    return failures


def compare_phase_b_arm(
    *,
    accepted_arm_root: Path,
    fresh_arm_root: Path,
    seed: int,
    arm: str,
) -> dict[str, Any]:
    failures: list[str] = []
    try:
        accepted = _load_json(accepted_arm_root / "arm_manifest.json")
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        return {
            "seed": seed,
            "arm": arm,
            "pass": False,
            "failures": [f"accepted_arm_manifest_invalid:{type(exc).__name__}"],
            "mismatch_count": 0,
            "mismatches": [],
        }
    try:
        fresh = _load_json(fresh_arm_root / "arm_manifest.json")
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        return {
            "seed": seed,
            "arm": arm,
            "pass": False,
            "failures": [f"fresh_arm_manifest_invalid:{type(exc).__name__}"],
            "mismatch_count": 0,
            "mismatches": [],
        }

    failures.extend(
        _verify_run_manifest_hashes(accepted, label="accepted_arm")
    )
    failures.extend(_verify_run_manifest_hashes(fresh, label="fresh_arm"))
    failures.extend(
        _verify_manifest_files(
            accepted_arm_root,
            accepted,
            label="accepted_arm",
        )
    )
    failures.extend(
        _verify_manifest_files(
            fresh_arm_root,
            fresh,
            label="fresh_arm",
        )
    )

    accepted_files = accepted.get("files")
    fresh_files = fresh.get("files")
    if not isinstance(accepted_files, dict) or not isinstance(fresh_files, dict):
        failures.append("arm_files_not_objects")
        accepted_files = {}
        fresh_files = {}

    if set(accepted_files) != set(fresh_files):
        failures.append("arm_file_descriptor_keys_mismatch")

    # All non-maintenance files are scientific/state evidence and remain exact.
    for name in sorted(set(accepted_files) & set(fresh_files)):
        if name == "maintenance":
            continue
        if accepted_files[name] != fresh_files[name]:
            failures.append(f"nonmaintenance_file_descriptor_mismatch:{name}")

    maintenance_mismatches: list[str] = []
    accepted_projected_maintenance_sha256: str | None = None
    fresh_projected_maintenance_sha256: str | None = None
    try:
        accepted_desc = accepted_files["maintenance"]
        fresh_desc = fresh_files["maintenance"]
        if not isinstance(accepted_desc, dict) or not isinstance(fresh_desc, dict):
            raise TypeError("maintenance descriptors must be objects")
        accepted_records = _load_jsonl(
            _safe_descriptor_path(accepted_arm_root, accepted_desc)
        )
        fresh_records = _load_jsonl(
            _safe_descriptor_path(fresh_arm_root, fresh_desc)
        )
        accepted_projected_records = [
            _project_phase_b_maintenance_record(item)
            for item in accepted_records
        ]
        fresh_projected_records = [
            _project_phase_b_maintenance_record(item)
            for item in fresh_records
        ]
        accepted_projected_maintenance_sha256 = _canonical_sha256(
            accepted_projected_records
        )
        fresh_projected_maintenance_sha256 = _canonical_sha256(
            fresh_projected_records
        )
        if (
            accepted_projected_maintenance_sha256
            != fresh_projected_maintenance_sha256
        ):
            maintenance_mismatches = _difference_paths(
                accepted_projected_records,
                fresh_projected_records,
                "maintenance",
            )
    except (
        KeyError,
        OSError,
        json.JSONDecodeError,
        TypeError,
        ValueError,
    ) as exc:
        failures.append(
            f"maintenance_projection_invalid:{type(exc).__name__}:{exc}"
        )

    arm_mismatches: list[str] = []
    accepted_projected_arm_sha256: str | None = None
    fresh_projected_arm_sha256: str | None = None
    try:
        accepted_projection = _project_phase_b_arm_manifest(accepted)
        fresh_projection = _project_phase_b_arm_manifest(fresh)
        accepted_projected_arm_sha256 = _canonical_sha256(
            accepted_projection
        )
        fresh_projected_arm_sha256 = _canonical_sha256(fresh_projection)
        if accepted_projected_arm_sha256 != fresh_projected_arm_sha256:
            arm_mismatches = _difference_paths(
                accepted_projection,
                fresh_projection,
                "arm_manifest",
            )
    except (TypeError, ValueError) as exc:
        failures.append(
            f"arm_projection_invalid:{type(exc).__name__}:{exc}"
        )

    mismatches = maintenance_mismatches + arm_mismatches
    return {
        "seed": seed,
        "arm": arm,
        "pass": not failures and not mismatches,
        "failures": failures,
        "mismatch_count": len(mismatches),
        "mismatches": mismatches,
        "accepted_projected_maintenance_sha256": (
            accepted_projected_maintenance_sha256
        ),
        "fresh_projected_maintenance_sha256": (
            fresh_projected_maintenance_sha256
        ),
        "accepted_projected_arm_sha256": accepted_projected_arm_sha256,
        "fresh_projected_arm_sha256": fresh_projected_arm_sha256,
    }


def _project_phase_b_seed_manifest(
    manifest: dict[str, Any],
) -> dict[str, Any]:
    projected = copy.deepcopy(manifest)
    projected.pop("payload_sha256", None)
    projected.pop("manifest_sha256", None)
    arms = projected.get("arms")
    if not isinstance(arms, dict):
        raise TypeError("Phase-B seed arms must be an object")
    for arm in ARM_NAMES:
        descriptor = arms.get(arm)
        if not isinstance(descriptor, dict):
            raise TypeError(f"Missing Phase-B arm descriptor: {arm}")
        # These are transitively timing-dependent through each arm manifest.
        # Raw identities and projected arm equality are verified separately.
        descriptor.pop("sha256", None)
        descriptor.pop("manifest_sha256", None)
    return projected


def compare_phase_b_seed(
    *,
    accepted_seed_root: Path,
    fresh_seed_root: Path,
    seed: int,
) -> dict[str, Any]:
    failures: list[str] = []
    try:
        accepted = _load_json(accepted_seed_root / "phase_b_manifest.json")
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        return {
            "seed": seed,
            "pass": False,
            "failures": [f"accepted_phase_b_manifest_invalid:{type(exc).__name__}"],
            "mismatch_count": 0,
            "mismatches": [],
            "arm_results": [],
        }
    try:
        fresh = _load_json(fresh_seed_root / "phase_b_manifest.json")
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        return {
            "seed": seed,
            "pass": False,
            "failures": [f"fresh_phase_b_manifest_invalid:{type(exc).__name__}"],
            "mismatch_count": 0,
            "mismatches": [],
            "arm_results": [],
        }

    failures.extend(
        _verify_run_manifest_hashes(accepted, label="accepted_phase_b")
    )
    failures.extend(
        _verify_run_manifest_hashes(fresh, label="fresh_phase_b")
    )

    accepted_arms = accepted.get("arms")
    fresh_arms = fresh.get("arms")
    if not isinstance(accepted_arms, dict) or not isinstance(fresh_arms, dict):
        failures.append("phase_b_arms_not_objects")
        accepted_arms = {}
        fresh_arms = {}

    arm_results: list[dict[str, Any]] = []
    for arm in ARM_NAMES:
        accepted_desc = accepted_arms.get(arm)
        fresh_desc = fresh_arms.get(arm)
        if not isinstance(accepted_desc, dict):
            failures.append(f"accepted:missing_arm_descriptor:{arm}")
            continue
        if not isinstance(fresh_desc, dict):
            failures.append(f"fresh:missing_arm_descriptor:{arm}")
            continue
        failures.extend(
            _verify_phase_b_arm_descriptor(
                accepted_seed_root,
                accepted_desc,
                arm=arm,
                label="accepted",
            )
        )
        failures.extend(
            _verify_phase_b_arm_descriptor(
                fresh_seed_root,
                fresh_desc,
                arm=arm,
                label="fresh",
            )
        )
        arm_results.append(
            compare_phase_b_arm(
                accepted_arm_root=accepted_seed_root / arm,
                fresh_arm_root=fresh_seed_root / arm,
                seed=seed,
                arm=arm,
            )
        )

    seed_mismatches: list[str] = []
    accepted_projected_sha256: str | None = None
    fresh_projected_sha256: str | None = None
    try:
        accepted_projection = _project_phase_b_seed_manifest(accepted)
        fresh_projection = _project_phase_b_seed_manifest(fresh)
        accepted_projected_sha256 = _canonical_sha256(accepted_projection)
        fresh_projected_sha256 = _canonical_sha256(fresh_projection)
        if accepted_projected_sha256 != fresh_projected_sha256:
            seed_mismatches = _difference_paths(
                accepted_projection,
                fresh_projection,
                "phase_b_manifest",
            )
    except (TypeError, ValueError) as exc:
        failures.append(
            f"phase_b_projection_invalid:{type(exc).__name__}:{exc}"
        )

    arm_mismatches = [
        f"{item['arm']}:{path}"
        for item in arm_results
        for path in item["mismatches"]
    ]
    failures.extend(
        f"{item['arm']}:{failure}"
        for item in arm_results
        for failure in item["failures"]
    )
    mismatches = arm_mismatches + seed_mismatches
    arms_complete = (
        len(arm_results) == len(ARM_NAMES)
        and all(item["pass"] is True for item in arm_results)
    )
    return {
        "seed": seed,
        "pass": arms_complete and not failures and not mismatches,
        "failures": failures,
        "mismatch_count": len(mismatches),
        "mismatches": mismatches,
        "arm_results": arm_results,
        "accepted_projected_sha256": accepted_projected_sha256,
        "fresh_projected_sha256": fresh_projected_sha256,
    }


def compare_phase_b(
    *,
    accepted_root: Path,
    fresh_root: Path,
) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    for seed in SEEDS:
        accepted_seed_root = accepted_root / PHASE_B_SUBDIR / f"seed-{seed}"
        fresh_seed_root = fresh_root / PHASE_B_SUBDIR / f"seed-{seed}"
        results.append(
            compare_phase_b_seed(
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


def _project_phase_c_correction_config(
    config: dict[str, Any],
) -> dict[str, Any]:
    projected = copy.deepcopy(config)
    projected.pop("payload_sha256", None)
    projected.pop("manifest_sha256", None)

    correction = projected.get("correction")
    if not isinstance(correction, dict):
        raise TypeError("Correction config correction block must be an object")
    reused = correction.get("reused_upstream_artifacts")
    if not isinstance(reused, dict):
        raise TypeError("Correction config reused_upstream_artifacts must be an object")
    phase_a = reused.get("phase_a")
    phase_b = reused.get("phase_b")
    if not isinstance(phase_a, dict) or not isinstance(phase_b, dict):
        raise TypeError("Correction config upstream Phase-A/B maps must be objects")

    for seed in SEEDS:
        key = str(seed)
        a = phase_a.get(key)
        b = phase_b.get(key)
        if not isinstance(a, dict) or not isinstance(b, dict):
            raise TypeError(f"Correction config lacks upstream seed {seed}")
        if "run_manifest_sha256" not in a:
            raise KeyError(f"phase_a.{key}.run_manifest_sha256")
        if "phase_b_manifest_sha256" not in b:
            raise KeyError(f"phase_b.{key}.phase_b_manifest_sha256")
        a["run_manifest_sha256"] = PHASE_C_TRANSITIVE_IDENTITY
        b["phase_b_manifest_sha256"] = PHASE_C_TRANSITIVE_IDENTITY
    return projected


def _verify_phase_c_config_upstream_bindings(
    config: dict[str, Any],
    *,
    artifact_root: Path,
    label: str,
) -> list[str]:
    failures: list[str] = []
    correction = config.get("correction")
    reused = correction.get("reused_upstream_artifacts") if isinstance(correction, dict) else None
    if not isinstance(reused, dict):
        return [f"{label}:invalid_reused_upstream_artifacts"]
    phase_a = reused.get("phase_a")
    phase_b = reused.get("phase_b")
    if not isinstance(phase_a, dict) or not isinstance(phase_b, dict):
        return [f"{label}:invalid_upstream_phase_maps"]

    for seed in SEEDS:
        key = str(seed)
        a = phase_a.get(key)
        b = phase_b.get(key)
        if not isinstance(a, dict):
            failures.append(f"{label}:missing_phase_a_upstream_seed:{seed}")
        else:
            try:
                manifest = _load_json(
                    artifact_root / PHASE_A_SUBDIR / f"seed-{seed}" / "run_manifest.json"
                )
            except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
                failures.append(
                    f"{label}:phase_a_manifest_invalid:{seed}:{type(exc).__name__}"
                )
            else:
                if a.get("run_manifest_sha256") != manifest.get("manifest_sha256"):
                    failures.append(
                        f"{label}:phase_a_upstream_manifest_mismatch:{seed}"
                    )

        if not isinstance(b, dict):
            failures.append(f"{label}:missing_phase_b_upstream_seed:{seed}")
        else:
            try:
                manifest = _load_json(
                    artifact_root / PHASE_B_SUBDIR / f"seed-{seed}" / "phase_b_manifest.json"
                )
            except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
                failures.append(
                    f"{label}:phase_b_manifest_invalid:{seed}:{type(exc).__name__}"
                )
            else:
                if b.get("phase_b_manifest_sha256") != manifest.get("manifest_sha256"):
                    failures.append(
                        f"{label}:phase_b_upstream_manifest_mismatch:{seed}"
                    )
    return failures


def _verify_phase_c_failed_lineage(
    *,
    accepted_root: Path,
    fresh_root: Path,
    expected_identity: dict[str, Any],
) -> dict[str, Any]:
    accepted_dir = accepted_root / PHASE_C_FAILED_SUBDIR / "seed-0"
    fresh_dir = fresh_root / PHASE_C_FAILED_SUBDIR / "seed-0"
    expected_entries = ["attempt.json", "failure.json"]
    failures: list[str] = []

    expected_files = {
        "attempt.json": (
            expected_identity.get("attempt_file_sha256"),
            expected_identity.get("attempt_payload_sha256"),
        ),
        "failure.json": (
            expected_identity.get("failure_file_sha256"),
            expected_identity.get("failure_payload_sha256"),
        ),
    }

    for label, root in (("accepted", accepted_dir), ("fresh", fresh_dir)):
        if not root.is_dir():
            failures.append(f"{label}:failed_lineage_directory_missing")
            continue
        entries = sorted(path.name for path in root.iterdir())
        if entries != expected_entries:
            failures.append(f"{label}:failed_lineage_entries_mismatch")
            continue
        for name in expected_entries:
            path = root / name
            expected_file_sha, expected_payload_sha = expected_files[name]
            if (
                not isinstance(expected_file_sha, str)
                or SHA256_RE.fullmatch(expected_file_sha) is None
                or _sha256_file(path) != expected_file_sha
            ):
                failures.append(f"{label}:{name}:accepted_file_identity_mismatch")
            try:
                payload = _load_json(path)
            except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
                failures.append(
                    f"{label}:{name}:invalid:{type(exc).__name__}"
                )
                continue
            payload_hash = payload.get("payload_sha256")
            core = dict(payload)
            core.pop("payload_sha256", None)
            actual_payload_sha = _canonical_sha256(core)
            if (
                not isinstance(payload_hash, str)
                or SHA256_RE.fullmatch(payload_hash) is None
                or actual_payload_sha != payload_hash
            ):
                failures.append(f"{label}:{name}:payload_sha256_mismatch")
            if (
                not isinstance(expected_payload_sha, str)
                or SHA256_RE.fullmatch(expected_payload_sha) is None
                or actual_payload_sha != expected_payload_sha
            ):
                failures.append(f"{label}:{name}:accepted_payload_identity_mismatch")

    return {
        "pass": not failures,
        "failures": failures,
        "entries": expected_entries,
    }


def compare_phase_c_preconditions(
    *,
    accepted_root: Path,
    fresh_root: Path,
    accepted_config_path: Path,
    fresh_config_path: Path,
) -> dict[str, Any]:
    failures: list[str] = []
    try:
        accepted = _load_json(accepted_config_path)
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        return {
            "pass": False,
            "failures": [f"accepted_correction_config_invalid:{type(exc).__name__}"],
            "mismatch_count": 0,
            "mismatches": [],
        }
    try:
        fresh = _load_json(fresh_config_path)
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        return {
            "pass": False,
            "failures": [f"fresh_correction_config_invalid:{type(exc).__name__}"],
            "mismatch_count": 0,
            "mismatches": [],
        }

    failures.extend(_verify_run_manifest_hashes(accepted, label="accepted_correction"))
    failures.extend(_verify_run_manifest_hashes(fresh, label="fresh_correction"))
    if accepted.get("manifest_sha256") != PHASE_C_CORRECTION_MANIFEST_SHA256:
        failures.append("accepted_correction_manifest_identity_mismatch")

    accepted_ready = accepted.get("implementation_ready")
    fresh_ready = fresh.get("implementation_ready")
    if (
        not isinstance(accepted_ready, dict)
        or accepted_ready.get("prepared_from_git_commit") != PHASE_C_CORRECTION_SOURCE_HEAD
    ):
        failures.append("accepted_correction_source_head_mismatch")
    if (
        not isinstance(fresh_ready, dict)
        or fresh_ready.get("prepared_from_git_commit") != PHASE_C_CORRECTION_SOURCE_HEAD
    ):
        failures.append("fresh_correction_source_head_mismatch")

    for block in PHASE_C_FROZEN_SCIENTIFIC_BLOCKS:
        if accepted.get(block) != fresh.get(block):
            failures.append(f"scientific_block_mismatch:{block}")

    failures.extend(
        _verify_phase_c_config_upstream_bindings(
            accepted,
            artifact_root=accepted_root,
            label="accepted_correction",
        )
    )
    failures.extend(
        _verify_phase_c_config_upstream_bindings(
            fresh,
            artifact_root=fresh_root,
            label="fresh_correction",
        )
    )

    accepted_correction = accepted.get("correction")
    expected_failed = (
        accepted_correction.get("failed_phase_c_v1")
        if isinstance(accepted_correction, dict)
        else None
    )
    if not isinstance(expected_failed, dict):
        failures.append("accepted_correction_failed_lineage_identity_missing")
        expected_failed = {}

    lineage = _verify_phase_c_failed_lineage(
        accepted_root=accepted_root,
        fresh_root=fresh_root,
        expected_identity=expected_failed,
    )
    failures.extend(lineage["failures"])

    mismatches: list[str] = []
    accepted_projected_sha256: str | None = None
    fresh_projected_sha256: str | None = None
    try:
        accepted_projection = _project_phase_c_correction_config(accepted)
        fresh_projection = _project_phase_c_correction_config(fresh)
        accepted_projected_sha256 = _canonical_sha256(accepted_projection)
        fresh_projected_sha256 = _canonical_sha256(fresh_projection)
        if accepted_projected_sha256 != fresh_projected_sha256:
            mismatches = _difference_paths(
                accepted_projection,
                fresh_projection,
                "correction_config",
            )
    except (KeyError, TypeError, ValueError) as exc:
        failures.append(
            f"correction_projection_invalid:{type(exc).__name__}:{exc}"
        )

    return {
        "pass": not failures and not mismatches,
        "failures": failures,
        "mismatch_count": len(mismatches),
        "mismatches": mismatches,
        "failed_lineage_preserved": lineage["pass"],
        "scientific_blocks_equal": not any(
            item.startswith("scientific_block_mismatch:") for item in failures
        ),
        "accepted_projected_sha256": accepted_projected_sha256,
        "fresh_projected_sha256": fresh_projected_sha256,
        "projection": {
            "normalized_upstream_fields": [
                "correction.reused_upstream_artifacts.phase_a.*.run_manifest_sha256",
                "correction.reused_upstream_artifacts.phase_b.*.phase_b_manifest_sha256",
            ],
            "derived_hash_fields_removed_after_verification": [
                "payload_sha256",
                "manifest_sha256",
            ],
            "accepted_manifest_sha256": PHASE_C_CORRECTION_MANIFEST_SHA256,
            "correction_source_head": PHASE_C_CORRECTION_SOURCE_HEAD,
            "frozen_scientific_blocks": list(PHASE_C_FROZEN_SCIENTIFIC_BLOCKS),
        },
    }


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
    phase_b = compare_phase_b(accepted_root=accepted_root, fresh_root=fresh_root)
    mismatches = [
        {
            "phase": "phase_a",
            "seed": item["seed"],
            "paths": item["mismatches"],
        }
        for item in phase_a["seed_results"]
        if item["mismatches"]
    ]
    mismatches.extend(
        {
            "phase": "phase_b",
            "seed": item["seed"],
            "paths": item["mismatches"],
        }
        for item in phase_b["seed_results"]
        if item["mismatches"]
    )
    failures = list(phase_a["failures"]) + list(phase_b["failures"])
    blockers = ["phase_c_comparator_not_implemented"]

    evidence: dict[str, Any] = {
        "audit_id": "stage9.5-6-replay-equivalence-comparison-v1",
        "schema_version": 1,
        "producer_id": "stage9.5-6-replay-equivalence-comparator-v1",
        "audited_head": _git_head(),
        "manual_override_used": False,
        "comparison_complete": False,
        "source_evidence_complete": False,
        "mismatch_count": int(
            phase_a["mismatch_count"] + phase_b["mismatch_count"]
        ),
        "mismatches": mismatches,
        "failures": failures,
        "blockers": blockers,
        "phase_a": {
            "complete_seeds": phase_a["complete_seeds"],
            "pass": phase_a["pass"],
            "seed_results": phase_a["seed_results"],
        },
        "phase_b": {
            "complete_seeds": phase_b["complete_seeds"],
            "pass": phase_b["pass"],
            "seed_results": phase_b["seed_results"],
        },
        "phase_c": {
            "rerun_seed": 0,
            "original_failure_lineage_preserved": False,
            "corrected_rerun_complete": False,
            "pass": False,
            "status": "not_implemented_blocked",
        },
        "accepted_maintenance_archive_verified": phase_b["pass"],
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
    if not evidence["phase_b"]["pass"]:
        raise SystemExit("Stage 9.5-6 Phase-B replay comparison failed.")
    raise SystemExit(
        "Stage 9.5-6 remains blocked: Phase-C comparator implementation "
        "is not yet frozen."
    )


if __name__ == "__main__":
    main()
