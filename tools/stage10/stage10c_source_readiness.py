from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import ks_2samp

from tools.stage10.stage10a_source_readiness import (
    PROJECT_ROOT,
    _canonical_sha256,
    _git_blob_sha1,
    _git_state,
    _sha256_file,
    _sha256_int64_array,
    _sha256_int64_pairs,
)

MANIFEST_PATH = PROJECT_ROOT / "data/manifests/stage10c_unseen_bot_v1.json"
AUDIT_PATH = PROJECT_ROOT / "data/manifests/stage10c_unseen_bot_source_audit_v1.json"
PROTOCOL_PATH = PROJECT_ROOT / "STAGE10C_UNSEEN_BOT_FAMILY_REPLICATION_PROTOCOL_V1.md"
PRIMARY_SCENARIO = PROJECT_ROOT / "data/manifests/sudden_benign_v1.json"
PREPROCESSING_PATH = PROJECT_ROOT / "data/manifests/sudden_benign_v1_preprocessing_v1.json"
SYSTEM_A_PATH = PROJECT_ROOT / "data/manifests/system_a_v1.json"
PRIMARY_CONFIG_PATH = PROJECT_ROOT / "data/manifests/cd_primary_run_config_v1_1.json"
WEDNESDAY = "Wednesday-workingHours.pcap_ISCX.csv"
FRIDAY = "Friday-WorkingHours-Morning.pcap_ISCX.csv"
WED_START, WED_END = 554_162, 623_433
PRE_ROWS, POST_ROWS, ATTACK_ROWS = 69_260, 69_270, 1_966

EXPECTED_INIT = {
    "preprocessing_core_state_sha256": "4527f77220f2cf6063108a7d71d80aaa0e82099ad282ff25408a2d9ce3488b1e",
    "system_a_manifest_sha256": "42004b5ed100b690023b9998bdc959fac41ab947b996fb7c58e44cee5e8dc6de",
    "r0_v2_manifest_sha256": "131027d2f136494eb388183f18dcb7eb0e9d7e9fe786f22dba25f4e1624c1483",
    "seeds": [0, 1, 2, 3, 4],
}


def _read_object(path: Path) -> dict[str, Any]:
    result = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(result, dict):
        raise ValueError(f"JSON object required: {path}")
    return result


def _embedded_sha_ok(obj: dict[str, Any]) -> bool:
    core = dict(obj)
    actual = core.pop("canonical_sha256", None)
    return isinstance(actual, str) and _canonical_sha256(core) == actual


def _labels(path: Path) -> np.ndarray:
    frame = pd.read_csv(
        path, usecols=lambda name: name.strip() == "Label", low_memory=False
    )
    if frame.shape[1] != 1:
        raise ValueError("Raw source must have exactly one Label column")
    return frame.iloc[:, 0].astype(str).str.strip().to_numpy()


def _evenly_select(source_rows: np.ndarray, required: int) -> np.ndarray:
    if required <= 0 or len(source_rows) < required:
        raise ValueError("Source pool insufficient for without-replacement sample")
    indices = (
        np.arange(required, dtype=np.int64) * len(source_rows)
    ) // required
    selected = source_rows[indices]
    if len(np.unique(selected)) != required:
        raise ValueError("Source selection contains a duplicate row ID")
    return selected


def _attack_slots(rows: int, attacks: int) -> np.ndarray:
    if attacks <= 0 or rows <= attacks:
        raise ValueError("Attack slot count requires rows > attacks > 0")
    slots = (
        (2 * np.arange(attacks, dtype=np.int64) + 1) * rows
    ) // (2 * attacks)
    if len(np.unique(slots)) != attacks or slots[0] < 0 or slots[-1] >= rows:
        raise ValueError("Attack slot schedule invalid")
    return slots


def _assemble(
    benign_rows: np.ndarray,
    attack_rows: np.ndarray,
    attack_source_order: int,
    regime_rows: int,
) -> dict[str, np.ndarray]:
    k = len(attack_rows)
    if len(benign_rows) != regime_rows - k:
        raise ValueError("BENIGN count does not equal non-attack slots")
    attack_slots = _attack_slots(regime_rows, k)
    attack_mask = np.zeros(regime_rows, dtype=bool)
    attack_mask[attack_slots] = True
    source_order = np.full(regime_rows, 5, dtype=np.int64)
    source_order[attack_mask] = attack_source_order
    row_ids = np.empty(regime_rows, dtype=np.int64)
    row_ids[attack_mask] = attack_rows
    row_ids[~attack_mask] = benign_rows
    return {
        "source_order": source_order,
        "source_row_ids": row_ids,
        "attack_slots": attack_slots,
    }


def _build_selection(w_labels: np.ndarray, f_labels: np.ndarray) -> dict[str, Any]:
    if len(w_labels) != 692_703 or len(f_labels) != 191_033:
        raise ValueError("Frozen raw source row count mismatch")

    eligible_range = np.arange(WED_START, WED_END, dtype=np.int64)
    goldeneye = eligible_range[w_labels[eligible_range] == "DoS GoldenEye"]
    friday_benign = np.flatnonzero(f_labels == "BENIGN").astype(np.int64)
    bot = np.flatnonzero(f_labels == "Bot").astype(np.int64)
    if len(goldeneye) != 3_589:
        raise ValueError("Frozen eligible GoldenEye source pool mismatch")
    if len(friday_benign) != 189_067 or len(bot) != ATTACK_ROWS:
        raise ValueError("Frozen Friday benign/Bot label population mismatch")

    pre_attack = _evenly_select(goldeneye, ATTACK_ROWS)
    even = friday_benign[::2]
    odd = friday_benign[1::2]
    pre_benign = _evenly_select(even, PRE_ROWS - ATTACK_ROWS)
    post_benign = _evenly_select(odd, POST_ROWS - ATTACK_ROWS)
    if np.intersect1d(pre_benign, post_benign).size:
        raise ValueError("Pre/post BENIGN source identities overlap")
    if np.any(w_labels[pre_attack] != "DoS GoldenEye"):
        raise ValueError("Pre attack source pool contains non-GoldenEye label")
    if np.any(f_labels[bot] != "Bot"):
        raise ValueError("Post attack source pool contains non-Bot label")

    pre = _assemble(pre_benign, pre_attack, 2, PRE_ROWS)
    post = _assemble(post_benign, bot, 5, POST_ROWS)
    all_order = np.r_[pre["source_order"], post["source_order"]]
    all_rows = np.r_[pre["source_row_ids"], post["source_row_ids"]]

    hashed = {
        "selected_seen_goldeneye_row_ids": _sha256_int64_array(pre_attack),
        "all_unseen_bot_row_ids": _sha256_int64_array(bot),
        "pre_benign_friday_row_ids": _sha256_int64_array(pre_benign),
        "post_benign_friday_row_ids": _sha256_int64_array(post_benign),
        "pre_injected_attack_slots": _sha256_int64_array(pre["attack_slots"]),
        "post_injected_attack_slots": _sha256_int64_array(post["attack_slots"]),
        "pre_stream_source_order": _sha256_int64_array(pre["source_order"]),
        "pre_stream_source_row_ids": _sha256_int64_array(pre["source_row_ids"]),
        "post_stream_source_order": _sha256_int64_array(post["source_order"]),
        "post_stream_source_row_ids": _sha256_int64_array(post["source_row_ids"]),
        "full_stream_source_order": _sha256_int64_array(all_order),
        "full_stream_source_row_ids": _sha256_int64_array(all_rows),
        "pre_stream_source_pairs": _sha256_int64_pairs(
            pre["source_order"], pre["source_row_ids"]
        ),
        "post_stream_source_pairs": _sha256_int64_pairs(
            post["source_order"], post["source_row_ids"]
        ),
        "full_stream_source_pairs": _sha256_int64_pairs(all_order, all_rows),
    }

    def windows(slots: np.ndarray, count: int) -> list[int]:
        return [
            int(((slots >= start) & (slots < min(start + 5000, count))).sum())
            for start in range(0, count, 5000)
        ]

    return {
        "hashes": hashed,
        "attack_windows": {
            "pre": windows(pre["attack_slots"], PRE_ROWS),
            "post": windows(post["attack_slots"], POST_ROWS),
        },
        "pre_attack": pre_attack,
        "post_attack": bot,
        "pre_benign": pre_benign,
        "post_benign": post_benign,
        "pre_rows": PRE_ROWS,
        "post_rows": POST_ROWS,
        "attack_per_regime": ATTACK_ROWS,
        "friday_benign_source_total": len(friday_benign),
        "goldeneye_eligible_total": len(goldeneye),
    }


def _source_features(w_path: Path, f_path: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    # Read only the predeclared Wednesday held-out range, not any Stage-10
    # adaptive trace, checkpoint output, detector event or fused prediction.
    w = pd.read_csv(
        w_path,
        skiprows=range(1, WED_START + 1),
        nrows=WED_END - WED_START,
        low_memory=False,
    )
    w.index = np.arange(WED_START, WED_END)
    f = pd.read_csv(f_path, low_memory=False)
    w.columns = [name.strip() for name in w.columns]
    f.columns = [name.strip() for name in f.columns]
    if len(w) != WED_END - WED_START or len(f) != 191_033:
        raise ValueError("Unexpected source-only feature table row counts")
    return w, f


def _ks_summary(
    left: pd.DataFrame, right: pd.DataFrame, features: list[str]
) -> dict[str, int | float]:
    values: list[float] = []
    for feature in features:
        def numeric(df: pd.DataFrame) -> np.ndarray:
            return (
                pd.to_numeric(df[feature], errors="coerce")
                .replace([np.inf, -np.inf], np.nan)
                .dropna()
                .to_numpy()
            )
        a, b = numeric(left), numeric(right)
        if not len(a) or not len(b):
            raise ValueError(f"Empty finite KS feature: {feature}")
        values.append(float(ks_2samp(a, b, method="auto").statistic))
    z = np.array(values, dtype=float)
    return {
        "mean": float(z.mean()),
        "median": float(np.median(z)),
        "p90": float(np.quantile(z, 0.9)),
        "max": float(z.max()),
        "ge_0_1": int((z >= 0.1).sum()),
        "ge_0_2": int((z >= 0.2).sum()),
        "ge_0_3": int((z >= 0.3).sum()),
    }


def _report(
    failures: list[str], git: dict[str, Any], sources: dict[str, Any],
    construction: dict[str, Any] | None,
    diagnostic: dict[str, Any] | None,
) -> dict[str, Any]:
    report: dict[str, Any] = {
        "audit_id": "stage10c-source-readiness-v1",
        "pass": not failures,
        "status": "pass" if not failures else "blocked",
        "failures": failures,
        "git": git,
        "sources": sources,
        "source_construction": construction,
        "source_only_ks_diagnostics": diagnostic,
        "source_only_feature_ks_recomputed": diagnostic is not None,
        "stage10_treatment_outcomes_accessed": False,
        "stage10_treatment_execution_authorized": False,
        "next_permitted_action": (
            "preserve_source_only_evidence_and_wait_for_stage9_5_closure"
            if not failures else "stop_and_version_correct_source_only_failure"
        ),
        "prohibited_next_action": "any_stage10c_treatment_run_before_stage9_5_closure",
    }
    report["canonical_sha256"] = _canonical_sha256(report)
    return report


def verify_source_readiness(data_root: Path) -> dict[str, Any]:
    failures: list[str] = []
    git = _git_state()
    if git.get("available") is not True:
        failures.append("git_state_unavailable")
    elif git.get("clean") is not True:
        failures.append("git_worktree_not_clean")
    elif git.get("branch") != "stage10c-preoutcome-protocol":
        failures.append("unexpected_stage10c_source_branch")

    manifest = _read_object(MANIFEST_PATH)
    audit = _read_object(AUDIT_PATH)
    primary = _read_object(PRIMARY_SCENARIO)
    preprocess = _read_object(PREPROCESSING_PATH)
    system_a = _read_object(SYSTEM_A_PATH)
    config = _read_object(PRIMARY_CONFIG_PATH)

    if not _embedded_sha_ok(manifest):
        failures.append("stage10c_machine_protocol_canonical_identity_mismatch")
    if not _embedded_sha_ok(audit):
        failures.append("stage10c_source_audit_canonical_identity_mismatch")
    if _git_blob_sha1(PROTOCOL_PATH) != manifest["protocol_document"]["git_blob_sha1"]:
        failures.append("stage10c_protocol_document_git_blob_mismatch")
    if _git_blob_sha1(AUDIT_PATH) != manifest["source_audit"]["git_blob_sha1"]:
        failures.append("stage10c_source_audit_git_blob_mismatch")
    if audit.get("canonical_sha256") != manifest["source_audit"]["canonical_sha256"]:
        failures.append("stage10c_audit_machine_binding_mismatch")

    if manifest.get("inherited_identities") != EXPECTED_INIT:
        failures.append("inherited_initial_identity_contract_mismatch")
    if preprocess.get("core_state_sha256") != EXPECTED_INIT["preprocessing_core_state_sha256"]:
        failures.append("preprocessing_identity_mismatch")
    if system_a.get("manifest_sha256") != EXPECTED_INIT["system_a_manifest_sha256"]:
        failures.append("system_a_identity_mismatch")
    if config.get("r0_v2", {}).get("manifest_sha256") != EXPECTED_INIT["r0_v2_manifest_sha256"]:
        failures.append("r0_v2_identity_mismatch")
    if manifest.get("stage9_5_hard_gate_required") is not True:
        failures.append("stage9_5_hard_gate_not_required")
    if manifest.get("stage10_treatment_execution_authorized") is not False:
        failures.append("stage10c_treatment_gate_bypass")
    train = primary.get("partitions", {}).get("training", {})
    dev = primary.get("partitions", {}).get("development", {})
    if "Bot" in train.get("label_counts", {}) or "Bot" in dev.get("label_counts", {}):
        failures.append("bot_found_in_historical_training_or_development")
    if train.get("components", [{}])[-1].get("row_end_exclusive") != 346352:
        failures.append("historical_training_wednesday_end_mismatch")
    if dev.get("row_end_exclusive") != WED_START:
        failures.append("historical_development_wednesday_end_mismatch")
    if train.get("label_counts", {}).get("DoS GoldenEye") != 1118:
        failures.append("seen_goldeneye_training_count_mismatch")
    if dev.get("label_counts", {}).get("DoS GoldenEye") != 2013:
        failures.append("seen_goldeneye_development_count_mismatch")

    paths = {
        "Wednesday": data_root / WEDNESDAY,
        "FridayMorning": data_root / FRIDAY,
    }
    sources: dict[str, Any] = {}
    for key, path in paths.items():
        if not path.is_file():
            failures.append(f"raw_source_missing:{key}")
            continue
        observed = {"sha256": _sha256_file(path), "size_bytes": path.stat().st_size}
        sources[key] = observed
        expected = audit["source_files"][key]
        if (
            observed["sha256"] != expected["sha256"]
            or observed["size_bytes"] != expected["size_bytes"]
        ):
            failures.append(f"raw_source_exact_bytes_mismatch:{key}")
    if len(sources) != 2 or any(s.startswith("raw_source_exact_bytes_mismatch") for s in failures):
        return _report(failures, git, sources, None, None)

    try:
        selection = _build_selection(
            _labels(paths["Wednesday"]), _labels(paths["FridayMorning"])
        )
        if selection["hashes"] != audit["ordered_int64_le_sha256"]:
            failures.append("frozen_stream_row_identity_mismatch")
        if selection["attack_windows"] != audit["attack_windows"]:
            failures.append("frozen_attack_slot_window_counts_mismatch")
        for key, expected in (
            ("pre_rows", 69260), ("post_rows", 69270),
            ("attack_per_regime", 1966),
            ("friday_benign_source_total", 189067),
            ("goldeneye_eligible_total", 3589),
        ):
            if selection[key] != expected:
                failures.append(f"source_count_mismatch:{key}")

        features = primary.get("feature_schema", {}).get("feature_columns", [])
        if not isinstance(features, list) or len(features) != 77 or len(set(features)) != 77:
            raise ValueError("Frozen 77-feature schema invalid")
        w, f = _source_features(paths["Wednesday"], paths["FridayMorning"])
        if any(feature not in w.columns or feature not in f.columns for feature in features):
            raise ValueError("Frozen feature column missing from raw table")

        observed_ks = {
            "benign_pre_vs_post": _ks_summary(
                f.iloc[selection["pre_benign"]],
                f.iloc[selection["post_benign"]],
                features,
            ),
            "seen_goldeneye_vs_unseen_bot": _ks_summary(
                w.loc[selection["pre_attack"]],
                f.iloc[selection["post_attack"]],
                features,
            ),
        }
        for family, stats in observed_ks.items():
            expected = audit["ks_77_features"][family]
            for key, value in stats.items():
                target = expected[key]
                if isinstance(value, float):
                    if not np.isclose(value, target, atol=1e-12, rtol=0):
                        failures.append(f"source_only_ks_mismatch:{family}:{key}")
                elif value != target:
                    failures.append(f"source_only_ks_mismatch:{family}:{key}")
        construct = {
            "pre_rows": selection["pre_rows"],
            "post_rows": selection["post_rows"],
            "attack_per_regime": selection["attack_per_regime"],
            "hashes": selection["hashes"],
            "attack_windows": selection["attack_windows"],
            "friday_benign_source_total": selection["friday_benign_source_total"],
            "goldeneye_eligible_total": selection["goldeneye_eligible_total"],
        }
        return _report(failures, git, sources, construct, observed_ks)
    except (OSError, ValueError, KeyError, IndexError, TypeError) as exc:
        failures.append(f"source_only_reconstruction_exception:{type(exc).__name__}:{exc}")
        return _report(failures, git, sources, None, None)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Stage-10C unseen Bot source-only verification; no treatment access"
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
