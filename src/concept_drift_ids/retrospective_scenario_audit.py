from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import ks_2samp

from concept_drift_ids.scenario_loader import PROJECT_ROOT, load_manifest, load_partition
from concept_drift_ids.scenario_manifest import sha256_file
from concept_drift_ids.symbolic import canonical_json_hash
from concept_drift_ids.system_b import _git_state, _write_csv_new, _write_json_new


AUDIT_ID = "sudden_benign_v1_retrospective_assumption_audit_v1"
AUDIT_DIR = PROJECT_ROOT / "results" / "audits" / AUDIT_ID
MANIFEST_PATH = AUDIT_DIR / "audit_manifest.json"
SUMMARY_PATH = AUDIT_DIR / "audit_summary.json"
PATTERN_PATH = AUDIT_DIR / "exact_pattern_dependence.csv"
REGIME_PATH = AUDIT_DIR / "regime_shift_by_feature.csv"
MAX_BENIGN_KS_ROWS = 50_000


def _deterministic_positions(total_rows: int, requested_rows: int) -> np.ndarray:
    if requested_rows <= 0 or requested_rows > total_rows:
        raise ValueError("requested_rows must be in 1..total_rows")
    return (
        np.arange(requested_rows, dtype=np.int64)
        * int(total_rows)
        // int(requested_rows)
    )


def _feature_hashes(frame: pd.DataFrame) -> np.ndarray:
    return pd.util.hash_pandas_object(frame, index=False).to_numpy(
        dtype=np.uint64,
        copy=True,
    )


def _canonical_row_signature(values: np.ndarray) -> bytes:
    row = np.asarray(values, dtype=np.float64).copy()
    missing = np.isnan(row)
    row[missing] = 0.0
    row[row == 0.0] = 0.0  # normalize -0.0 to +0.0
    return np.packbits(missing, bitorder="little").tobytes() + row.astype(
        "<f8", copy=False
    ).tobytes(order="C")


def _candidate_signature_sets(
    frame: pd.DataFrame,
    hashes: np.ndarray,
    candidate_hashes: set[int],
) -> dict[int, set[bytes]]:
    out: dict[int, set[bytes]] = defaultdict(set)
    if not candidate_hashes:
        return out
    values = frame.to_numpy(dtype=np.float64, copy=False)
    for index in np.flatnonzero(np.isin(hashes, np.fromiter(candidate_hashes, dtype=np.uint64))):
        out[int(hashes[index])].add(_canonical_row_signature(values[index]))
    return out


def _exact_duplicate_excess(frame: pd.DataFrame) -> tuple[int, int]:
    hashes = _feature_hashes(frame)
    unique, counts = np.unique(hashes, return_counts=True)
    duplicated_hashes = {int(value) for value in unique[counts > 1]}
    signatures = _candidate_signature_sets(frame, hashes, duplicated_hashes)
    candidate_rows = int(sum(count for value, count in zip(unique, counts) if int(value) in duplicated_hashes))
    distinct_candidate_patterns = int(sum(len(items) for items in signatures.values()))
    return candidate_rows - distinct_candidate_patterns, distinct_candidate_patterns


def _training_seen_mask(
    training: pd.DataFrame,
    target: pd.DataFrame,
) -> np.ndarray:
    train_hash = _feature_hashes(training)
    target_hash = _feature_hashes(target)
    train_unique = set(map(int, np.unique(train_hash)))
    candidate_hashes = {int(value) for value in np.unique(target_hash) if int(value) in train_unique}
    training_signatures = _candidate_signature_sets(training, train_hash, candidate_hashes)
    target_values = target.to_numpy(dtype=np.float64, copy=False)
    seen = np.zeros(len(target), dtype=bool)
    for index, value in enumerate(target_hash):
        bucket = training_signatures.get(int(value))
        if bucket and _canonical_row_signature(target_values[index]) in bucket:
            seen[index] = True
    return seen


def _ks_rows(
    *,
    before: pd.DataFrame,
    after: pd.DataFrame,
    feature_names: list[str],
    comparison: str,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for feature in feature_names:
        left = before[feature].dropna().to_numpy(dtype=np.float64, copy=False)
        right = after[feature].dropna().to_numpy(dtype=np.float64, copy=False)
        if len(left) == 0 or len(right) == 0:
            rows.append({
                "comparison": comparison,
                "feature": feature,
                "before_n": len(left),
                "after_n": len(right),
                "ks_statistic": None,
                "ks_pvalue": None,
            })
            continue
        result = ks_2samp(left, right, alternative="two-sided", method="asymp")
        rows.append({
            "comparison": comparison,
            "feature": feature,
            "before_n": len(left),
            "after_n": len(right),
            "ks_statistic": float(result.statistic),
            "ks_pvalue": float(result.pvalue),
        })
    return rows


def _ks_summary(rows: list[dict[str, object]]) -> dict[str, object]:
    values = np.asarray(
        [float(row["ks_statistic"]) for row in rows if row["ks_statistic"] is not None],
        dtype=np.float64,
    )
    return {
        "features_evaluated": int(len(values)),
        "mean_ks": float(np.mean(values)),
        "median_ks": float(np.median(values)),
        "p90_ks": float(np.percentile(values, 90)),
        "max_ks": float(np.max(values)),
        "features_ks_ge_0_10": int(np.sum(values >= 0.10)),
        "features_ks_ge_0_20": int(np.sum(values >= 0.20)),
        "features_ks_ge_0_30": int(np.sum(values >= 0.30)),
    }


def build_retrospective_scenario_audit() -> None:
    if AUDIT_DIR.exists():
        raise FileExistsError(f"Audit directory already exists; refusing overwrite: {AUDIT_DIR}")
    git = _git_state(require_clean=True)
    scenario = load_manifest()
    features = list(scenario["feature_schema"]["feature_columns"])

    training = load_partition("training")
    development = load_partition("development")
    pre = load_partition("pre_drift")
    post = load_partition("post_drift")

    duplicate_excess, duplicate_candidate_unique = _exact_duplicate_excess(training.X)
    pattern_rows: list[dict[str, object]] = [{
        "partition": "training",
        "rows": len(training.X),
        "training_seen_rows": len(training.X),
        "training_seen_fraction": 1.0,
        "training_seen_benign_rows": int(np.sum(training.y.to_numpy() == 0)),
        "training_seen_attack_rows": int(np.sum(training.y.to_numpy() == 1)),
        "exact_duplicate_excess_rows": duplicate_excess,
        "exact_duplicate_excess_fraction": float(duplicate_excess / len(training.X)),
    }]

    target_masks: dict[str, np.ndarray] = {}
    for name, part in (
        ("development", development),
        ("pre_drift", pre),
        ("post_drift", post),
    ):
        seen = _training_seen_mask(training.X, part.X)
        target_masks[name] = seen
        y = part.y.to_numpy(dtype=np.int8, copy=False)
        pattern_rows.append({
            "partition": name,
            "rows": len(part.X),
            "training_seen_rows": int(np.sum(seen)),
            "training_seen_fraction": float(np.mean(seen)),
            "training_seen_benign_rows": int(np.sum(seen & (y == 0))),
            "training_seen_attack_rows": int(np.sum(seen & (y == 1))),
            "exact_duplicate_excess_rows": None,
            "exact_duplicate_excess_fraction": None,
        })

    pre_y = pre.y.to_numpy(dtype=np.int8, copy=False)
    post_y = post.y.to_numpy(dtype=np.int8, copy=False)
    pre_benign = pre.X.loc[pre_y == 0].reset_index(drop=True)
    post_benign = post.X.loc[post_y == 0].reset_index(drop=True)
    n_benign = min(MAX_BENIGN_KS_ROWS, len(pre_benign), len(post_benign))
    pre_benign = pre_benign.iloc[
        _deterministic_positions(len(pre_benign), n_benign)
    ].reset_index(drop=True)
    post_benign = post_benign.iloc[
        _deterministic_positions(len(post_benign), n_benign)
    ].reset_index(drop=True)
    pre_attack = pre.X.loc[pre_y == 1].reset_index(drop=True)
    post_attack = post.X.loc[post_y == 1].reset_index(drop=True)

    benign_ks = _ks_rows(
        before=pre_benign,
        after=post_benign,
        feature_names=features,
        comparison="pre_benign_vs_post_benign",
    )
    attack_ks = _ks_rows(
        before=pre_attack,
        after=post_attack,
        feature_names=features,
        comparison="pre_goldeneye_vs_post_goldeneye",
    )
    regime_rows = [*benign_ks, *attack_ks]

    summary = {
        "audit_format_version": 1,
        "audit_id": AUDIT_ID,
        "evidence_status": "posthoc_retrospective_diagnostic_not_model_selection",
        "scenario_id": scenario["scenario_id"],
        "scenario_version": scenario["scenario_version"],
        "audit_git": git,
        "data_access": {
            "training_used": True,
            "development_used": True,
            "pre_drift_used": True,
            "post_drift_used": True,
        },
        "exact_pattern_dependence": {
            row["partition"]: {
                key: value for key, value in row.items() if key != "partition"
            }
            for row in pattern_rows
        },
        "training_duplicate_candidate_distinct_patterns": duplicate_candidate_unique,
        "regime_shift": {
            "benign_source_regime": _ks_summary(benign_ks),
            "goldeneye_temporal_movement": _ks_summary(attack_ks),
            "benign_ks_sample_size_each": n_benign,
            "pre_attack_rows": len(pre_attack),
            "post_attack_rows": len(post_attack),
        },
        "interpretation": {
            "attack_family_invariant_claim": False,
            "recommended_scenario_wording": (
                "controlled BENIGN-source-regime-dominant composite shift with "
                "smaller nonzero GoldenEye temporal movement"
            ),
            "seen_pattern_claim": (
                "training-seen exact feature-pattern reporting is required as a "
                "descriptive robustness stratification; it does not change the frozen "
                "primary full-stream evaluation"
            ),
        },
    }

    AUDIT_DIR.mkdir(parents=True, exist_ok=False)
    _write_csv_new(PATTERN_PATH, pattern_rows)
    _write_csv_new(REGIME_PATH, regime_rows)
    summary["artifact_sha256"] = canonical_json_hash(summary)
    _write_json_new(SUMMARY_PATH, summary)
    manifest = {
        "manifest_format_version": 1,
        "audit_id": AUDIT_ID,
        "scenario_id": scenario["scenario_id"],
        "summary_artifact_sha256": summary["artifact_sha256"],
        "files": {
            "summary": {
                "path": SUMMARY_PATH.relative_to(PROJECT_ROOT).as_posix(),
                "sha256": sha256_file(SUMMARY_PATH),
            },
            "exact_pattern_dependence": {
                "path": PATTERN_PATH.relative_to(PROJECT_ROOT).as_posix(),
                "sha256": sha256_file(PATTERN_PATH),
            },
            "regime_shift_by_feature": {
                "path": REGIME_PATH.relative_to(PROJECT_ROOT).as_posix(),
                "sha256": sha256_file(REGIME_PATH),
            },
        },
    }
    manifest["manifest_sha256"] = canonical_json_hash(manifest)
    _write_json_new(MANIFEST_PATH, manifest)

    print(f"audit_manifest={MANIFEST_PATH}")
    print(f"manifest_hash={manifest['manifest_sha256']}")
    print(f"training_duplicate_excess_rows={duplicate_excess}")
    for row in pattern_rows[1:]:
        print(
            f"{row['partition']}_training_seen_rows={row['training_seen_rows']} "
            f"attack_seen_rows={row['training_seen_attack_rows']}"
        )
    print(
        "benign_mean_ks="
        f"{summary['regime_shift']['benign_source_regime']['mean_ks']:.12g}"
    )
    print(
        "goldeneye_mean_ks="
        f"{summary['regime_shift']['goldeneye_temporal_movement']['mean_ks']:.12g}"
    )
    print("status=retrospective_diagnostic_written")


def verify_retrospective_scenario_audit() -> None:
    if not MANIFEST_PATH.is_file():
        raise FileNotFoundError(f"Missing retrospective scenario audit: {MANIFEST_PATH}")
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    stored = manifest.get("manifest_sha256")
    core = dict(manifest)
    core.pop("manifest_sha256", None)
    if canonical_json_hash(core) != stored:
        raise ValueError("Retrospective scenario audit manifest hash mismatch.")
    for name, entry in manifest["files"].items():
        path = PROJECT_ROOT / entry["path"]
        if not path.is_file():
            raise FileNotFoundError(f"Missing audit file {name!r}: {path}")
        if sha256_file(path) != entry["sha256"]:
            raise ValueError(f"Audit file hash mismatch for {name!r}.")
    summary = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
    summary_hash = summary.get("artifact_sha256")
    summary_core = dict(summary)
    summary_core.pop("artifact_sha256", None)
    if canonical_json_hash(summary_core) != summary_hash:
        raise ValueError("Retrospective audit summary canonical hash mismatch.")
    if summary_hash != manifest["summary_artifact_sha256"]:
        raise ValueError("Retrospective audit summary identity mismatch.")
    print(f"audit_manifest={MANIFEST_PATH}")
    print(f"manifest_hash={stored}")
    print("status=verified")
