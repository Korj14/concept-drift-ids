from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import ks_2samp


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROTOCOL_PATH = PROJECT_ROOT / "STAGE10A_GOLDENEYE_ATTACK_PATTERN_REPLICATION_PROTOCOL_V1.md"
MANIFEST_PATH = PROJECT_ROOT / "data/manifests/stage10a_goldeneye_attack_pattern_v1.json"
SOURCE_AUDIT_PATH = PROJECT_ROOT / "data/manifests/stage10a_goldeneye_source_audit_v1.json"
PRIMARY_SCENARIO_PATH = PROJECT_ROOT / "data/manifests/sudden_benign_v1.json"
PREPROCESSING_PATH = PROJECT_ROOT / "data/manifests/sudden_benign_v1_preprocessing_v1.json"
SYSTEM_A_PATH = PROJECT_ROOT / "data/manifests/system_a_v1.json"
PRIMARY_CONFIG_PATH = PROJECT_ROOT / "data/manifests/cd_primary_run_config_v1_1.json"

SOURCE_FILE = "Wednesday-workingHours.pcap_ISCX.csv"
EXPECTED_SOURCE_SHA256 = "893c27dc968bf7a8adef1689f90be55ca4a4dc3088fb63d6ff247ac56856df2a"
EXPECTED_SOURCE_SIZE = 225_166_395
PRE_START, PRE_END = 554_162, 623_433
POST_START, POST_END = 623_433, 692_703
BOUNDARY_INDEX = 69_260

EXPECTED_PRE_COUNTS = {"BENIGN": 65_671, "DoS GoldenEye": 3_589}
EXPECTED_POST_COUNTS = {"BENIGN": 65_697, "DoS GoldenEye": 3_573}
EXPECTED_PRE_EXCLUDED = {"Heartbleed": 11}

EXPECTED_ROW_HASHES = {
    "pre_included_row_ids": "ef7773f88374c82a663723c0c1125f4a8bfee75a58fe4d8e35355b492e07b354",
    "post_included_row_ids": "186aec7f816faca89484c537b77ed8e729a9ac55982a7e1bec6f37750c1c30d8",
    "pre_benign_row_ids": "0a9b395d897b7843f44ff6ec78c87b806e1f99710fad4c404cd1b174311b92f1",
    "post_benign_row_ids": "e393262d5ba7f02dd167aee8575e4980fa108b9471cef8034bb069a1340f5527",
    "pre_goldeneye_row_ids": "15fd308926f6fda0d74639fc9e55176ab4f97b51ec575f7763512a080a5ae5f2",
    "post_goldeneye_row_ids": "bc584d69c0fdb7040a2a40ef105eea4cb514555872719718abeb21ee3c837646",
    "stream_row_ids": "81924f3c39cb49adfaebea11d9aef045ab73804dd61faee49dcfbd2dd5f33f25",
    "stream_source_order_row_pairs": "b6c3b7a14a08be6c6b186ed339a1f205cdff49d48de6fa16ce44cc776796c6a7",
}
EXPECTED_PREPROCESSING_STATE = "4527f77220f2cf6063108a7d71d80aaa0e82099ad282ff25408a2d9ce3488b1e"
EXPECTED_SYSTEM_A_MANIFEST = "42004b5ed100b690023b9998bdc959fac41ab947b996fb7c58e44cee5e8dc6de"
EXPECTED_R0_V2_MANIFEST = "131027d2f136494eb388183f18dcb7eb0e9d7e9fe786f22dba25f4e1624c1483"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_blob_sha1(path: Path) -> str:
    raw = path.read_bytes()
    header = f"blob {len(raw)}\\0".encode("ascii")
    return hashlib.sha1(header + raw).hexdigest()


def _canonical_sha256(payload: object) -> str:
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _embedded_hash_ok(payload: dict[str, Any]) -> bool:
    observed = payload.get("canonical_sha256")
    core = dict(payload)
    core.pop("canonical_sha256", None)
    return isinstance(observed, str) and observed == _canonical_sha256(core)


def _sha256_int64_array(values: np.ndarray) -> str:
    return hashlib.sha256(np.asarray(values, dtype="<i8").tobytes()).hexdigest()


def _sha256_int64_pairs(left: np.ndarray, right: np.ndarray) -> str:
    pairs = np.column_stack((left, right)).astype("<i8", copy=False)
    return hashlib.sha256(pairs.tobytes()).hexdigest()


def _git_state() -> dict[str, Any]:
    try:
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=PROJECT_ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        branch = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=PROJECT_ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=PROJECT_ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        return {"available": False, "error": type(exc).__name__, "clean": False}
    return {
        "available": True,
        "head": head,
        "branch": branch,
        "clean": not status,
        "status": status,
    }


def _extract_source_rows(path: Path) -> pd.DataFrame:
    parts: list[pd.DataFrame] = []
    offset = 0
    for chunk in pd.read_csv(path, chunksize=100_000, low_memory=False):
        size = len(chunk)
        lo = max(0, PRE_START - offset)
        hi = min(size, POST_END - offset)
        if lo < hi:
            selected = chunk.iloc[lo:hi].copy()
            selected["__row_in_source__"] = np.arange(
                offset + lo,
                offset + hi,
                dtype=np.int64,
            )
            parts.append(selected)
        offset += size
    if offset < POST_END or not parts:
        raise ValueError("Wednesday source does not contain the frozen Stage-10A range.")
    return pd.concat(parts, ignore_index=True)


def _ks_summary(
    frame: pd.DataFrame,
    features: list[str],
    left_mask: np.ndarray,
    right_mask: np.ndarray,
) -> dict[str, Any]:
    values: list[float] = []
    for feature in features:
        left = pd.to_numeric(frame.loc[left_mask, feature], errors="coerce")
        right = pd.to_numeric(frame.loc[right_mask, feature], errors="coerce")
        left = left.replace([np.inf, -np.inf], np.nan).dropna().to_numpy()
        right = right.replace([np.inf, -np.inf], np.nan).dropna().to_numpy()
        if not len(left) or not len(right):
            raise ValueError(f"No finite values for KS feature: {feature}")
        values.append(float(ks_2samp(left, right, method="auto").statistic))
    arr = np.asarray(values, dtype=float)
    return {
        "features_evaluated": int(len(arr)),
        "mean_ks": float(arr.mean()),
        "median_ks": float(np.median(arr)),
        "p90_ks": float(np.quantile(arr, 0.9)),
        "max_ks": float(arr.max()),
        "features_ks_ge_0_10": int((arr >= 0.10).sum()),
        "features_ks_ge_0_20": int((arr >= 0.20).sum()),
        "features_ks_ge_0_30": int((arr >= 0.30).sum()),
    }


def _final_report(
    failures: list[str],
    git_state: dict[str, Any],
    source: dict[str, Any] | None,
    scenario: dict[str, Any] | None,
) -> dict[str, Any]:
    report: dict[str, Any] = {
        "audit_id": "stage10a-source-readiness-v1",
        "status": "pass" if not failures else "blocked",
        "pass": not failures,
        "failures": failures,
        "git": git_state,
        "source": source,
        "scenario": scenario,
        "stage10_treatment_outcomes_accessed": False,
        "stage10_treatment_execution_authorized": False,
        "next_permitted_action": (
            "preserve_protocol_and_wait_for_stage9_5_hard_gate"
            if not failures
            else "correct_preoutcome_source_or_identity_failure_only"
        ),
        "prohibited_next_action": (
            "stage10a_c_d_or_d_periodic_treatment_execution_before_stage9_5_closure"
        ),
    }
    report["canonical_sha256"] = _canonical_sha256(report)
    return report


def verify_source_readiness(data_root: Path) -> dict[str, Any]:
    failures: list[str] = []
    git_state = _git_state()
    if not git_state.get("available"):
        failures.append("git_state_unavailable")
    elif not git_state.get("clean"):
        failures.append("git_worktree_not_clean_at_verifier_start")

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    source_audit = json.loads(SOURCE_AUDIT_PATH.read_text(encoding="utf-8"))
    primary_scenario = json.loads(PRIMARY_SCENARIO_PATH.read_text(encoding="utf-8"))
    preprocessing = json.loads(PREPROCESSING_PATH.read_text(encoding="utf-8"))
    system_a = json.loads(SYSTEM_A_PATH.read_text(encoding="utf-8"))
    primary_config = json.loads(PRIMARY_CONFIG_PATH.read_text(encoding="utf-8"))

    if not _embedded_hash_ok(manifest):
        failures.append("stage10a_protocol_manifest_canonical_hash_mismatch")
    if not _embedded_hash_ok(source_audit):
        failures.append("stage10a_source_audit_canonical_hash_mismatch")
    if _git_blob_sha1(PROTOCOL_PATH) != manifest["protocol_document"]["git_blob_sha1"]:
        failures.append("stage10a_protocol_document_git_blob_mismatch")
    if _git_blob_sha1(SOURCE_AUDIT_PATH) != manifest["source_audit"]["git_blob_sha1"]:
        failures.append("stage10a_source_audit_git_blob_mismatch")
    if source_audit.get("canonical_sha256") != manifest["source_audit"]["canonical_sha256"]:
        failures.append("stage10a_source_audit_manifest_binding_mismatch")

    if preprocessing.get("core_state_sha256") != EXPECTED_PREPROCESSING_STATE:
        failures.append("inherited_preprocessing_state_mismatch")
    if system_a.get("manifest_sha256") != EXPECTED_SYSTEM_A_MANIFEST:
        failures.append("inherited_system_a_manifest_mismatch")
    if primary_config.get("r0_v2", {}).get("manifest_sha256") != EXPECTED_R0_V2_MANIFEST:
        failures.append("inherited_r0_v2_manifest_mismatch")

    features = primary_scenario.get("feature_schema", {}).get("feature_columns")
    if not isinstance(features, list) or len(features) != 77:
        failures.append("frozen_77_feature_schema_missing")
        features = []

    source_path = data_root / SOURCE_FILE
    if not source_path.exists():
        failures.append("wednesday_raw_source_missing")
        return _final_report(failures, git_state, None, None)

    source_size = source_path.stat().st_size
    source_sha = _sha256_file(source_path)
    if source_size != EXPECTED_SOURCE_SIZE:
        failures.append("wednesday_raw_source_size_mismatch")
    if source_sha != EXPECTED_SOURCE_SHA256:
        failures.append("wednesday_raw_source_sha256_mismatch")

    frame = _extract_source_rows(source_path)
    normalized = {column.strip(): column for column in frame.columns}
    label_column = normalized.get("Label")
    if label_column is None:
        failures.append("label_column_missing")
        return _final_report(
            failures,
            git_state,
            {"size_bytes": source_size, "sha256": source_sha},
            None,
        )

    missing = [feature for feature in features if feature not in normalized]
    if missing:
        failures.append("frozen_feature_columns_missing_from_raw_source")
        return _final_report(
            failures,
            git_state,
            {"size_bytes": source_size, "sha256": source_sha},
            {"missing_features": missing},
        )

    raw_features = [normalized[feature] for feature in features]
    row_ids = frame["__row_in_source__"].to_numpy(dtype=np.int64, copy=False)
    labels = frame[label_column].astype(str).str.strip().to_numpy()

    pre_raw = (row_ids >= PRE_START) & (row_ids < PRE_END)
    post = (row_ids >= POST_START) & (row_ids < POST_END)
    pre = pre_raw & (labels != "Heartbleed")

    pre_labels = pd.Series(labels[pre]).value_counts().to_dict()
    post_labels = pd.Series(labels[post]).value_counts().to_dict()
    excluded = pd.Series(labels[pre_raw & ~pre]).value_counts().to_dict()
    if pre_labels != EXPECTED_PRE_COUNTS:
        failures.append("pre_label_counts_mismatch")
    if post_labels != EXPECTED_POST_COUNTS:
        failures.append("post_label_counts_mismatch")
    if excluded != EXPECTED_PRE_EXCLUDED:
        failures.append("pre_exclusion_counts_mismatch")

    pre_benign = pre & (labels == "BENIGN")
    post_benign = post & (labels == "BENIGN")
    pre_goldeneye = pre & (labels == "DoS GoldenEye")
    post_goldeneye = post & (labels == "DoS GoldenEye")
    pre_ids = row_ids[pre]
    post_ids = row_ids[post]
    stream_ids = np.concatenate((pre_ids, post_ids))

    row_hashes = {
        "pre_included_row_ids": _sha256_int64_array(pre_ids),
        "post_included_row_ids": _sha256_int64_array(post_ids),
        "pre_benign_row_ids": _sha256_int64_array(row_ids[pre_benign]),
        "post_benign_row_ids": _sha256_int64_array(row_ids[post_benign]),
        "pre_goldeneye_row_ids": _sha256_int64_array(row_ids[pre_goldeneye]),
        "post_goldeneye_row_ids": _sha256_int64_array(row_ids[post_goldeneye]),
        "stream_row_ids": _sha256_int64_array(stream_ids),
        "stream_source_order_row_pairs": _sha256_int64_pairs(
            np.full(stream_ids.shape, 2, dtype=np.int64),
            stream_ids,
        ),
    }
    if row_hashes != EXPECTED_ROW_HASHES:
        failures.append("stage10a_ordered_row_identity_mismatch")

    working = frame.rename(columns={raw: raw.strip() for raw in raw_features})
    clean_features = [feature.strip() for feature in raw_features]
    benign_ks = _ks_summary(working, clean_features, pre_benign, post_benign)
    goldeneye_ks = _ks_summary(working, clean_features, pre_goldeneye, post_goldeneye)

    expected_diag = source_audit["class_conditional_shift_diagnostics"]
    for name, observed in (
        ("BENIGN_pre_vs_post", benign_ks),
        ("DoS_GoldenEye_pre_vs_post", goldeneye_ks),
    ):
        expected = expected_diag[name]
        for key, value in observed.items():
            target = expected[key]
            if isinstance(value, float):
                if not np.isclose(value, target, rtol=0.0, atol=1e-12):
                    failures.append(f"source_diagnostic_mismatch:{name}:{key}")
            elif value != target:
                failures.append(f"source_diagnostic_mismatch:{name}:{key}")

    scenario = {
        "pre_rows": int(pre.sum()),
        "post_rows": int(post.sum()),
        "boundary_index": BOUNDARY_INDEX,
        "pre_label_counts": pre_labels,
        "post_label_counts": post_labels,
        "pre_excluded_label_counts": excluded,
        "row_identity_sha256": row_hashes,
        "attack_prevalence": {
            "pre": float(pre_goldeneye.sum() / pre.sum()),
            "post": float(post_goldeneye.sum() / post.sum()),
            "post_minus_pre_percentage_points": float(
                100.0 * (post_goldeneye.sum() / post.sum() - pre_goldeneye.sum() / pre.sum())
            ),
        },
        "BENIGN_pre_vs_post": benign_ks,
        "DoS_GoldenEye_pre_vs_post": goldeneye_ks,
    }
    return _final_report(
        failures,
        git_state,
        {"size_bytes": source_size, "sha256": source_sha},
        scenario,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Verify frozen Stage-10A GoldenEye source construction without "
            "executing or inspecting Stage-10 treatment outcomes."
        )
    )
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = verify_source_readiness(args.data_root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    if not report["pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
