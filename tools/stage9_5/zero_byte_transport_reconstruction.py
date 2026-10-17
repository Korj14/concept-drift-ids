from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = (
    PROJECT_ROOT
    / "data"
    / "manifests"
    / "stage9_5_1_zero_byte_transport_reconstruction_v1.json"
)
DEFAULT_REPORT_PATH = (
    PROJECT_ROOT
    / "results"
    / "audits"
    / "stage9_5_full_seed_rerun_v1"
    / "zero_byte_transport_reconstruction_report.json"
)
EMPTY_SHA256 = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
GIT_SHA1_RE = re.compile(r"^[0-9a-f]{40}$")
ZERO_SUMMARY_FIELDS = (
    "opportunity_count",
    "publication_count",
    "candidate_count",
    "compute_seconds",
    "shap_seconds",
    "surrogate_seconds",
    "lifecycle_seconds",
)


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
    data = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_blob_sha1_bytes(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data, usedforsecurity=False).hexdigest()


def _git_blob_bytes(blob_sha1: str) -> bytes:
    if GIT_SHA1_RE.fullmatch(blob_sha1) is None:
        raise ValueError(f"Invalid Git blob SHA-1: {blob_sha1}")
    completed = subprocess.run(
        ["git", "cat-file", "blob", blob_sha1],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
    )
    if completed.returncode != 0:
        raise FileNotFoundError(f"Pinned Git blob unavailable: {blob_sha1}")
    data = completed.stdout
    if _git_blob_sha1_bytes(data) != blob_sha1:
        raise ValueError(f"Pinned Git blob identity mismatch: {blob_sha1}")
    return data


def _load_json_bytes(data: bytes, *, label: str) -> dict[str, Any]:
    payload = json.loads(
        data.decode("utf-8"),
        object_pairs_hook=_reject_duplicate_pairs,
    )
    if not isinstance(payload, dict):
        raise TypeError(f"Expected JSON object: {label}")
    return payload


def _verify_manifest_self_hashes(
    manifest: dict[str, Any],
    *,
    label: str,
) -> list[str]:
    failures: list[str] = []
    payload_sha = manifest.get("payload_sha256")
    manifest_sha = manifest.get("manifest_sha256")
    if not isinstance(payload_sha, str):
        failures.append(f"{label}:payload_sha256_missing")
        return failures
    if not isinstance(manifest_sha, str):
        failures.append(f"{label}:manifest_sha256_missing")
        return failures

    payload_core = dict(manifest)
    payload_core.pop("payload_sha256", None)
    if _canonical_sha256(payload_core) != payload_sha:
        failures.append(f"{label}:payload_sha256_mismatch")

    manifest_core = dict(payload_core)
    manifest_core.pop("manifest_sha256", None)
    if _canonical_sha256(manifest_core) != manifest_sha:
        failures.append(f"{label}:manifest_sha256_mismatch")
    return failures


def _safe_relative(root: Path, relative: str) -> Path:
    rel = Path(relative)
    if rel.is_absolute():
        raise ValueError(f"Absolute path not allowed: {relative}")
    resolved_root = root.resolve()
    resolved = (resolved_root / rel).resolve()
    if not resolved.is_relative_to(resolved_root):
        raise ValueError(f"Path escapes archive root: {relative}")
    return resolved


def _validate_forensic_basis(contract: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    basis = contract.get("forensic_basis")
    if not isinstance(basis, dict):
        return ["contract:forensic_basis_not_object"]

    checks = (
        (
            "dropbox_discovery_doc",
            "dropbox_discovery_doc_git_blob_sha1",
        ),
        (
            "dropbox_discovery_manifest",
            "dropbox_discovery_manifest_git_blob_sha1",
        ),
        (
            "dropbox_restore_event_forensics_manifest",
            "dropbox_restore_event_forensics_manifest_git_blob_sha1",
        ),
    )
    pinned_blobs: dict[str, bytes] = {}
    for path_field, sha_field in checks:
        relative = basis.get(path_field)
        expected = basis.get(sha_field)
        if not isinstance(relative, str) or not isinstance(expected, str):
            failures.append(f"contract:invalid_forensic_basis:{path_field}")
            continue
        try:
            pinned_blobs[path_field] = _git_blob_bytes(expected)
        except (OSError, ValueError) as exc:
            failures.append(
                f"forensic_basis_blob_unavailable:{relative}:"
                f"{type(exc).__name__}"
            )

    if basis.get("restore_event_history_exhausted") is not True:
        failures.append("forensic_basis:restore_event_history_not_exhausted")
    if basis.get("restore_event_count") != 253:
        failures.append("forensic_basis:restore_event_count_mismatch")
    if basis.get("restore_event_operation_types") != ["ADD"]:
        failures.append("forensic_basis:unexpected_restore_event_operations")
    if basis.get("non_add_event_count") != 0:
        failures.append("forensic_basis:non_add_events_present")
    if basis.get("missing_c_frozen_maintenance_add_event_count") != 0:
        failures.append("forensic_basis:missing_files_have_add_events")

    forensic_path_value = basis.get("dropbox_restore_event_forensics_manifest")
    if isinstance(forensic_path_value, str):
        forensic_blob = pinned_blobs.get(
            "dropbox_restore_event_forensics_manifest"
        )
        if forensic_blob is None:
            failures.append(
                "forensic_basis:restore_event_record_blob_unavailable"
            )
        else:
            try:
                forensic = _load_json_bytes(
                    forensic_blob,
                    label=forensic_path_value,
                )
            except (
                UnicodeDecodeError,
                json.JSONDecodeError,
                TypeError,
                ValueError,
            ) as exc:
                failures.append(
                    "forensic_basis:restore_event_record_invalid:"
                    f"{type(exc).__name__}"
                )
            else:
                if forensic.get("audit_id") != (
                    "stage9.5-1-dropbox-restore-event-forensics-v1"
                ):
                    failures.append(
                        "forensic_basis:"
                        "restore_event_record_audit_id_mismatch"
                    )
                pagination = forensic.get("pagination")
                operations = forensic.get("operation_summary")
                findings = forensic.get("missing_path_event_findings")
                if not isinstance(pagination, dict):
                    failures.append(
                        "forensic_basis:restore_event_pagination_missing"
                    )
                else:
                    if pagination.get("history_exhausted") is not True:
                        failures.append(
                            "forensic_basis:"
                            "restore_event_history_not_exhausted"
                        )
                    if pagination.get("total_events") != 253:
                        failures.append(
                            "forensic_basis:restore_event_total_mismatch"
                        )
                if not isinstance(operations, dict):
                    failures.append(
                        "forensic_basis:"
                        "restore_event_operation_summary_missing"
                    )
                else:
                    if operations.get("observed_operation_types") != ["ADD"]:
                        failures.append(
                            "forensic_basis:"
                            "restore_event_operation_type_mismatch"
                        )
                    if operations.get("non_add_event_count") != 0:
                        failures.append(
                            "forensic_basis:"
                            "restore_event_non_add_present"
                        )
                if not isinstance(findings, dict):
                    failures.append(
                        "forensic_basis:missing_path_findings_missing"
                    )
                elif findings.get("add_event_count") != 0:
                    failures.append(
                        "forensic_basis:missing_path_add_event_present"
                    )
    return failures

def _validate_item(
    *,
    archive_root: Path,
    item: dict[str, Any],
    empty_sha: str,
) -> tuple[dict[str, Any], list[str]]:
    failures: list[str] = []
    seed = item.get("seed")
    relative = item.get("path")
    accepted_manifest_relative = item.get("accepted_arm_manifest_path")
    expected_manifest_sha = item.get("accepted_arm_manifest_sha256")

    if not isinstance(seed, int):
        return {"seed": seed}, ["item:seed_invalid"]
    if not isinstance(relative, str):
        return {"seed": seed}, [f"seed{seed}:path_invalid"]
    if not isinstance(accepted_manifest_relative, str):
        return {"seed": seed, "path": relative}, [
            f"seed{seed}:accepted_manifest_path_invalid"
        ]
    if not isinstance(expected_manifest_sha, str):
        return {"seed": seed, "path": relative}, [
            f"seed{seed}:accepted_manifest_sha_invalid"
        ]
    if item.get("expected_size_bytes") != 0:
        failures.append(f"seed{seed}:expected_size_not_zero")

    accepted_manifest_path = PROJECT_ROOT / accepted_manifest_relative
    if not accepted_manifest_path.is_file():
        failures.append(f"seed{seed}:accepted_manifest_missing")
        return {"seed": seed, "path": relative}, failures

    try:
        accepted_manifest = _load_json(accepted_manifest_path)
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        failures.append(
            f"seed{seed}:accepted_manifest_invalid:{type(exc).__name__}"
        )
        return {"seed": seed, "path": relative}, failures

    failures.extend(
        _verify_manifest_self_hashes(
            accepted_manifest,
            label=f"seed{seed}:accepted_manifest",
        )
    )
    if accepted_manifest.get("manifest_sha256") != expected_manifest_sha:
        failures.append(f"seed{seed}:accepted_manifest_identity_mismatch")
    if accepted_manifest.get("seed") != seed:
        failures.append(f"seed{seed}:accepted_manifest_seed_mismatch")
    if accepted_manifest.get("arm") != "c_frozen_symbolic":
        failures.append(f"seed{seed}:accepted_manifest_arm_mismatch")

    maintenance = accepted_manifest.get("files", {}).get("maintenance")
    if not isinstance(maintenance, dict):
        failures.append(f"seed{seed}:maintenance_descriptor_missing")
    else:
        if maintenance.get("path") != "maintenance.jsonl":
            failures.append(f"seed{seed}:maintenance_path_mismatch")
        if maintenance.get("sha256") != empty_sha:
            failures.append(f"seed{seed}:maintenance_sha_mismatch")

    summary = accepted_manifest.get("maintenance_summary")
    if not isinstance(summary, dict):
        failures.append(f"seed{seed}:maintenance_summary_missing")
    else:
        for field in ZERO_SUMMARY_FIELDS:
            if summary.get(field) != 0:
                failures.append(
                    f"seed{seed}:maintenance_summary_nonzero:{field}"
                )
    if accepted_manifest.get("publications") != []:
        failures.append(f"seed{seed}:publications_not_empty")

    try:
        target = _safe_relative(archive_root, relative)
    except ValueError as exc:
        failures.append(f"seed{seed}:unsafe_target:{exc}")
        return {"seed": seed, "path": relative}, failures

    arm_root = target.parent
    local_manifest_path = arm_root / "arm_manifest.json"
    if not arm_root.is_dir():
        failures.append(f"seed{seed}:arm_root_missing")
    if not local_manifest_path.is_file():
        failures.append(f"seed{seed}:materialized_arm_manifest_missing")
    else:
        accepted_raw_sha = _sha256_file(accepted_manifest_path)
        local_raw_sha = _sha256_file(local_manifest_path)
        if local_raw_sha != accepted_raw_sha:
            failures.append(
                f"seed{seed}:materialized_arm_manifest_byte_mismatch"
            )

    preexisting = target.exists()
    if preexisting:
        if not target.is_file():
            failures.append(f"seed{seed}:target_exists_not_file")
        else:
            if target.stat().st_size != 0:
                failures.append(f"seed{seed}:preexisting_target_not_empty")
            if _sha256_file(target) != empty_sha:
                failures.append(f"seed{seed}:preexisting_target_sha_mismatch")

    result = {
        "seed": seed,
        "path": relative,
        "target_path": str(target),
        "accepted_arm_manifest_path": accepted_manifest_relative,
        "accepted_arm_manifest_manifest_sha256": accepted_manifest.get(
            "manifest_sha256"
        ),
        "accepted_arm_manifest_file_sha256": _sha256_file(
            accepted_manifest_path
        ),
        "state_before": "preexisting_verified" if preexisting else "absent",
    }
    return result, failures


def run(
    *,
    stage8_archive_root: Path,
    output_path: Path = DEFAULT_REPORT_PATH,
    contract_path: Path = CONTRACT_PATH,
) -> dict[str, Any]:
    contract = _load_json(contract_path)
    if contract.get("contract_id") != (
        "stage9.5-1-zero-byte-transport-reconstruction-v1"
    ):
        raise ValueError("Wrong zero-byte transport reconstruction contract.")

    empty_sha = contract.get("empty_file_sha256")
    if empty_sha != EMPTY_SHA256:
        raise ValueError("Contract empty-file SHA-256 is not the frozen identity.")

    failures = _validate_forensic_basis(contract)
    items = contract.get("allowed_reconstructions")
    if not isinstance(items, list) or len(items) != 5:
        failures.append("contract:allowed_reconstructions_not_exactly_five")
        items = []

    archive_root = stage8_archive_root.resolve()
    if not archive_root.is_dir():
        failures.append("stage8_archive_root_missing")

    item_results: list[dict[str, Any]] = []
    if not failures:
        for item in items:
            if not isinstance(item, dict):
                failures.append("contract:reconstruction_item_not_object")
                continue
            result, item_failures = _validate_item(
                archive_root=archive_root,
                item=item,
                empty_sha=empty_sha,
            )
            item_results.append(result)
            failures.extend(item_failures)

    # Two-phase behavior: perform no writes unless every precondition passed.
    reconstructed_count = 0
    preexisting_count = 0
    if not failures:
        for result in item_results:
            target = Path(str(result["target_path"]))
            if result["state_before"] == "preexisting_verified":
                result["state_after"] = "preexisting_verified"
                preexisting_count += 1
                continue
            try:
                with target.open("xb"):
                    pass
            except FileExistsError:
                failures.append(
                    f"seed{result['seed']}:target_appeared_after_preflight"
                )
                result["state_after"] = "write_conflict"
                break
            if target.stat().st_size != 0 or _sha256_file(target) != empty_sha:
                failures.append(
                    f"seed{result['seed']}:reconstructed_target_verification_failed"
                )
                result["state_after"] = "verification_failed"
                break
            result["state_after"] = "transport_reconstructed_zero_bytes"
            reconstructed_count += 1

    report_core: dict[str, Any] = {
        "audit_id": "stage9.5-1-zero-byte-transport-reconstruction-v1",
        "contract_id": contract["contract_id"],
        "status": "pass" if not failures else "failed",
        "pass": not failures,
        "stage8_archive_root": str(archive_root),
        "reconstruction_kind": "manifest_bound_zero_byte_transport_reconstruction",
        "original_dropbox_objects_recovered": False,
        "transport_reconstruction_explicit": True,
        "governing_verifier_unchanged": True,
        "reconstructed_count": reconstructed_count,
        "preexisting_verified_count": preexisting_count,
        "required_path_count": 5,
        "items": item_results,
        "failures": failures,
        "next_authority": (
            "Run unchanged Stage-9.5-1 v1.2 fresh_clone_reconstruction.py "
            "with the materialized checkpoint root and completed Stage-8 archive."
        ),
        "scientific_objects_modified": False,
        "accepted_stage8_9_evidence_replaced": False,
        "stage10_outcomes_accessed": False,
    }
    report = dict(report_core)
    report["canonical_sha256"] = _canonical_sha256(report_core)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Reconstruct only the five manifest-bound zero-byte C-arm "
            "maintenance files omitted by Dropbox transport."
        )
    )
    parser.add_argument("--stage8-archive-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--contract", type=Path, default=CONTRACT_PATH)
    args = parser.parse_args()

    report = run(
        stage8_archive_root=args.stage8_archive_root,
        output_path=args.output,
        contract_path=args.contract,
    )
    if not report["pass"]:
        raise SystemExit(
            "Stage 9.5-1 zero-byte transport reconstruction failed: "
            + "; ".join(str(item) for item in report["failures"])
        )


if __name__ == "__main__":
    main()
