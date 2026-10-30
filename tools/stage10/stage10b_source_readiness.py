from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from tools.stage10.stage10a_source_readiness import (
    PROJECT_ROOT,
    _canonical_sha256,
    _git_blob_sha1,
    _git_state,
    _sha256_file,
    _sha256_int64_array,
    _sha256_int64_pairs,
)

PROTOCOL_PATH = PROJECT_ROOT / "STAGE10B_GRADUAL_BENIGN_SOURCE_REPLICATION_PROTOCOL_V1.md"
MANIFEST_PATH = PROJECT_ROOT / "data/manifests/stage10b_gradual_benign_source_v1.json"
AUDIT_PATH = PROJECT_ROOT / "data/manifests/stage10b_gradual_benign_source_audit_v1.json"
PREPROCESSING_PATH = PROJECT_ROOT / "data/manifests/sudden_benign_v1_preprocessing_v1.json"
SYSTEM_A_PATH = PROJECT_ROOT / "data/manifests/system_a_v1.json"
PRIMARY_CONFIG_PATH = PROJECT_ROOT / "data/manifests/cd_primary_run_config_v1_1.json"

WEDNESDAY = "Wednesday-workingHours.pcap_ISCX.csv"
THURSDAY = "Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv"
PRE_START, PRE_END = 554_162, 623_433
POST_START, POST_END = 623_433, 692_703
RAMP_ROWS = 50_000
SALT = "stage10b-gradual-benign-v1"

EXPECTED_PREPROCESSING_STATE = "4527f77220f2cf6063108a7d71d80aaa0e82099ad282ff25408a2d9ce3488b1e"
EXPECTED_SYSTEM_A_MANIFEST = "42004b5ed100b690023b9998bdc959fac41ab947b996fb7c58e44cee5e8dc6de"
EXPECTED_R0_V2_MANIFEST = "131027d2f136494eb388183f18dcb7eb0e9d7e9fe786f22dba25f4e1624c1483"


def _read_json(path: Path) -> dict[str, Any]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise ValueError(f"JSON object required: {path}")
    return obj


def _embedded_sha_ok(payload: dict[str, Any]) -> bool:
    core = dict(payload)
    embedded = core.pop("canonical_sha256", None)
    return isinstance(embedded, str) and _canonical_sha256(core) == embedded


def _read_labels(path: Path) -> np.ndarray:
    # Labels are used only for source-construction verification, not
    # neural predictions, detector updates, treatment, or evaluation scoring.
    series = pd.read_csv(
        path,
        usecols=lambda name: name.strip() == "Label",
        low_memory=False,
    )
    if series.shape[1] != 1:
        raise ValueError("Exactly one raw Label column is required")
    return series.iloc[:, 0].astype(str).str.strip().to_numpy()


def _selected_thursday_candidates(
    eligible_thursday_rows: np.ndarray,
    n_benign_slots: int,
) -> np.ndarray:
    n_eligible = len(eligible_thursday_rows)
    ordinals = np.arange(n_benign_slots, dtype=np.int64)
    return eligible_thursday_rows[
        (ordinals * n_eligible) // n_benign_slots
    ]


def _deterministic_replacement_mask(
    benign_slot_row_ids: np.ndarray,
    *,
    post_start: int = POST_START,
    ramp_rows: int = RAMP_ROWS,
    salt: str = SALT,
) -> np.ndarray:
    if ramp_rows <= 0:
        raise ValueError("ramp_rows must be positive")
    result = np.zeros(len(benign_slot_row_ids), dtype=bool)
    denominator = 2 * ramp_rows
    range_u64 = 1 << 64
    for j, row_id in enumerate(benign_slot_row_ids):
        t = int(row_id) - post_start
        if t < 0:
            raise ValueError("A BENIGN template row precedes post start")
        if t >= ramp_rows:
            result[j] = True
            continue
        digest = hashlib.sha256(
            f"{salt}:slot:{int(row_id)}".encode("utf-8")
        ).digest()
        u64 = int.from_bytes(digest[:8], byteorder="big", signed=False)
        result[j] = (denominator * u64) < ((2 * t + 1) * range_u64)
    return result


def _build_schedule(
    wednesday_labels: np.ndarray,
    thursday_labels: np.ndarray,
) -> dict[str, Any]:
    if len(wednesday_labels) != POST_END:
        raise ValueError("Wednesday row count does not match frozen source")
    if len(thursday_labels) != 170_366:
        raise ValueError("Thursday-morning row count does not match frozen source")
    if PRE_END != POST_START:
        raise ValueError("Frozen Wednesday ranges not contiguous")

    pre_raw = np.arange(PRE_START, PRE_END, dtype=np.int64)
    excluded = wednesday_labels[pre_raw] == "Heartbleed"
    pre = pre_raw[~excluded]
    post = np.arange(POST_START, POST_END, dtype=np.int64)
    post_labels = wednesday_labels[post]
    benign_slots = post[post_labels == "BENIGN"]
    thursday_benign = np.flatnonzero(thursday_labels == "BENIGN").astype(np.int64)
    candidates = _selected_thursday_candidates(thursday_benign, len(benign_slots))
    replacement = _deterministic_replacement_mask(benign_slots)
    replaced_slots = benign_slots[replacement]
    replaced_source = candidates[replacement]

    window_slots: list[int] = []
    window_replacements: list[int] = []
    window_ends: list[int] = []
    for start in range(0, POST_END - POST_START, 5000):
        end = min(start + 5000, POST_END - POST_START)
        eligible = (benign_slots >= POST_START + start) & (
            benign_slots < POST_START + end
        )
        window_slots.append(int(eligible.sum()))
        window_replacements.append(int((replacement & eligible).sum()))
        window_ends.append(end)

    hashes = {
        "pre_ids": _sha256_int64_array(pre),
        "post_ids": _sha256_int64_array(post),
        "benign_slots": _sha256_int64_array(benign_slots),
        "full_candidate_thursday_benign": _sha256_int64_array(candidates),
        "replaced_slot_ids": _sha256_int64_array(replaced_slots),
        "replaced_thursday_source_ids": _sha256_int64_array(replaced_source),
        "replacement_mapping": _sha256_int64_pairs(
            replaced_slots, replaced_source
        ),
        "packed_replacement_mask_lsb": hashlib.sha256(
            np.packbits(replacement.astype(np.uint8), bitorder="little").tobytes()
        ).hexdigest(),
    }
    def count_labels(labels: np.ndarray) -> dict[str, int]:
        values, counts = np.unique(labels, return_counts=True)
        return {str(value): int(count) for value, count in zip(values, counts)}

    ramp_mask = (benign_slots - POST_START) < RAMP_ROWS
    return {
        "pre_rows": int(len(pre)),
        "post_rows": int(len(post)),
        "pre_label_counts": count_labels(wednesday_labels[pre]),
        "post_label_counts": count_labels(post_labels),
        "pre_excluded_heartbleed": int(excluded.sum()),
        "thursday_benign_rows": int(len(thursday_benign)),
        "replacement": {
            "nominal_ramp_rows": RAMP_ROWS,
            "eligible_benign_slots": int(len(benign_slots)),
            "replaced": int(replacement.sum()),
            "retained": int((~replacement).sum()),
            "ramp_replaced": int((replacement & ramp_mask).sum()),
            "plateau_replaced": int((replacement & ~ramp_mask).sum()),
        },
        "hashes": hashes,
        "window_benign_slots": window_slots,
        "window_replacements": window_replacements,
        "window_post_end_exclusive": window_ends,
    }


def _report(
    failures: list[str],
    git: dict[str, Any],
    sources: dict[str, Any],
    source_construction: dict[str, Any] | None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "audit_id": "stage10b-source-readiness-v1",
        "status": "pass" if not failures else "blocked",
        "pass": not failures,
        "failures": failures,
        "git": git,
        "sources": sources,
        "source_construction": source_construction,
        "source_only_feature_ks_recomputed": False,
        "stage10_treatment_outcomes_accessed": False,
        "stage10_treatment_execution_authorized": False,
        "next_permitted_action": (
            "preserve_protocol_and_wait_for_stage9_5_hard_gate"
            if not failures
            else "correct_source_only_identity_failure_before_any_treatment"
        ),
        "prohibited_next_action": "stage10b_treatment_execution_before_stage9_5_closure",
    }
    payload["canonical_sha256"] = _canonical_sha256(payload)
    return payload


def verify_source_readiness(data_root: Path) -> dict[str, Any]:
    failures: list[str] = []
    git = _git_state()
    if git.get("available") is not True:
        failures.append("git_unavailable")
    elif git.get("clean") is not True:
        failures.append("git_worktree_not_clean")

    manifest = _read_json(MANIFEST_PATH)
    audit = _read_json(AUDIT_PATH)
    preprocessing = _read_json(PREPROCESSING_PATH)
    system_a = _read_json(SYSTEM_A_PATH)
    original_config = _read_json(PRIMARY_CONFIG_PATH)

    if not _embedded_sha_ok(manifest):
        failures.append("protocol_canonical_sha256_mismatch")
    if not _embedded_sha_ok(audit):
        failures.append("source_audit_canonical_sha256_mismatch")
    if _git_blob_sha1(PROTOCOL_PATH) != manifest["protocol_document"]["git_blob_sha1"]:
        failures.append("protocol_document_git_blob_identity_mismatch")
    if _git_blob_sha1(AUDIT_PATH) != manifest["source_audit"]["git_blob_sha1"]:
        failures.append("source_audit_git_blob_identity_mismatch")
    if audit["canonical_sha256"] != manifest["source_audit"]["canonical_sha256"]:
        failures.append("source_audit_manifest_canonical_binding_mismatch")

    if preprocessing.get("core_state_sha256") != EXPECTED_PREPROCESSING_STATE:
        failures.append("inherited_preprocessing_state_mismatch")
    if system_a.get("manifest_sha256") != EXPECTED_SYSTEM_A_MANIFEST:
        failures.append("inherited_system_a_manifest_mismatch")
    if original_config.get("r0_v2", {}).get("manifest_sha256") != EXPECTED_R0_V2_MANIFEST:
        failures.append("inherited_r0_v2_manifest_mismatch")
    if manifest.get("stage10_treatment_execution_authorized") is not False:
        failures.append("protocol_treatment_gate_incorrect")
    if manifest.get("stage9_5_hard_gate_required") is not True:
        failures.append("stage9_5_hard_gate_missing")

    sources: dict[str, Any] = {}
    paths = {
        "Wednesday": data_root / WEDNESDAY,
        "Thursday_morning": data_root / THURSDAY,
    }
    for name, path in paths.items():
        if not path.is_file():
            failures.append(f"missing_source:{name}")
            continue
        source_hash = _sha256_file(path)
        source_size = path.stat().st_size
        sources[name] = {"sha256": source_hash, "size": source_size}
        if sources[name] != audit["source"][name]:
            failures.append(f"source_exact_byte_identity_mismatch:{name}")
    if len(sources) != 2 or any(
        str(value).startswith("source_exact_byte_identity_mismatch:")
        for value in failures
    ):
        return _report(failures, git, sources, None)

    try:
        construction = _build_schedule(
            _read_labels(paths["Wednesday"]),
            _read_labels(paths["Thursday_morning"]),
        )
    except (ValueError, KeyError, IndexError) as exc:
        failures.append(f"source_construction_error:{type(exc).__name__}:{exc}")
        return _report(failures, git, sources, None)

    for field in (
        "pre_rows", "post_rows", "pre_label_counts", "post_label_counts",
        "replacement", "hashes", "window_benign_slots",
        "window_replacements", "window_post_end_exclusive",
    ):
        if construction[field] != audit[field]:
            failures.append(f"source_construction_mismatch:{field}")
    if construction["pre_excluded_heartbleed"] != 11:
        failures.append("heartbleed_exclusion_not_11")
    if construction["thursday_benign_rows"] != 168186:
        failures.append("thursday_benign_population_not_168186")

    return _report(failures, git, sources, construction)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Stage-10B source-only gradual stream audit, never treatment execution"
    )
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = verify_source_readiness(args.data_root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, sort_keys=True, indent=2))
    if not result["pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
