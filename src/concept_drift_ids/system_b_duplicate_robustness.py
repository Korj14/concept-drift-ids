from __future__ import annotations

import json
from collections import defaultdict
from typing import Any, Sequence

import numpy as np
import pandas as pd
import torch

from concept_drift_ids.frozen_preprocessing import load_frozen_preprocessing, transform_frame
from concept_drift_ids.neural import predict_probabilities
from concept_drift_ids.retrospective_scenario_audit import (
    _canonical_row_signature,
    _feature_hashes,
)
from concept_drift_ids.scenario_loader import PROJECT_ROOT, load_partition
from concept_drift_ids.scenario_manifest import sha256_file
from concept_drift_ids.symbolic import (
    Condition,
    activation_mask,
    canonical_json_hash,
)
from concept_drift_ids.system_a import (
    SYSTEM_A_CONFIG,
    _load_checkpoint_model,
    _load_frozen_system_a_manifest,
)
from concept_drift_ids.system_b import (
    SYSTEM_B_CONFIG,
    _development_split,
    _git_state,
    _record_for_seed,
    _write_csv_new,
    _write_json_new,
)
from concept_drift_ids.system_b_r0_v2 import load_accepted_r0_v2_manifest


ANALYSIS_ID = "system_b_duplicate_aware_validation_v1"
OUTPUT_DIR = PROJECT_ROOT / "results" / "robustness" / ANALYSIS_ID
MANIFEST_PATH = OUTPUT_DIR / "analysis_manifest.json"
ROWS_PATH = OUTPUT_DIR / "candidate_pattern_revalidation.csv"
SUMMARY_PATH = OUTPUT_DIR / "analysis_summary.json"


def _exact_pattern_group_ids(frame: pd.DataFrame) -> np.ndarray:
    hashes = _feature_hashes(frame)
    values = frame.to_numpy(dtype=np.float64, copy=False)
    by_hash: dict[int, list[int]] = defaultdict(list)
    for index, value in enumerate(hashes):
        by_hash[int(value)].append(index)

    group_ids = np.empty(len(frame), dtype=np.int64)
    next_group = 0
    for indices in by_hash.values():
        if len(indices) == 1:
            group_ids[indices[0]] = next_group
            next_group += 1
            continue
        signature_to_group: dict[bytes, int] = {}
        for index in indices:
            signature = _canonical_row_signature(values[index])
            if signature not in signature_to_group:
                signature_to_group[signature] = next_group
                next_group += 1
            group_ids[index] = signature_to_group[signature]
    return group_ids


def _pattern_quality(
    mask: np.ndarray,
    *,
    y_true: np.ndarray,
    neural_decision: np.ndarray,
    consequent: int,
    group_ids: np.ndarray,
) -> dict[str, float | int | np.ndarray]:
    mask = np.asarray(mask, dtype=bool)
    y = np.asarray(y_true, dtype=np.int8)
    neural = np.asarray(neural_decision, dtype=np.int8)
    groups = np.asarray(group_ids, dtype=np.int64)
    unique_groups = np.unique(groups)
    active = np.zeros(len(unique_groups), dtype=bool)
    label_correct = np.zeros(len(unique_groups), dtype=np.float64)
    neural_correct = np.zeros(len(unique_groups), dtype=np.float64)

    for position, group in enumerate(unique_groups):
        rows = groups == group
        activation_values = np.unique(mask[rows])
        if len(activation_values) != 1:
            raise ValueError("Exact feature pattern has inconsistent rule activation.")
        active[position] = bool(activation_values[0])
        label_correct[position] = float(np.mean(y[rows] == consequent))
        neural_correct[position] = float(np.mean(neural[rows] == consequent))

    covered = int(np.sum(active))
    support = float(covered / len(unique_groups)) if len(unique_groups) else 0.0
    precision = float(np.mean(label_correct[active])) if covered else 0.0
    fidelity = float(np.mean(neural_correct[active])) if covered else 0.0
    return {
        "support": support,
        "covered_count": covered,
        "class_precision": precision,
        "neural_fidelity": fidelity,
        "group_active": active,
        "group_label_correct": label_correct,
        "group_neural_correct": neural_correct,
        "group_count": len(unique_groups),
    }


def _group_bootstrap_stability(
    quality: dict[str, Any],
    *,
    replicates: int,
    random_state: int,
    min_support: float,
    min_covered: int,
    min_precision: float,
    min_fidelity: float,
) -> float:
    active = np.asarray(quality["group_active"], dtype=bool)
    label_correct = np.asarray(quality["group_label_correct"], dtype=np.float64)
    neural_correct = np.asarray(quality["group_neural_correct"], dtype=np.float64)
    groups = len(active)
    if groups == 0:
        return 0.0
    rng = np.random.default_rng(random_state)
    passes = 0
    for _ in range(replicates):
        idx = rng.integers(0, groups, size=groups)
        sampled_active = active[idx]
        covered = int(np.sum(sampled_active))
        support = covered / groups
        precision = (
            float(np.mean(label_correct[idx][sampled_active]))
            if covered
            else 0.0
        )
        fidelity = (
            float(np.mean(neural_correct[idx][sampled_active]))
            if covered
            else 0.0
        )
        passes += int(
            support >= min_support
            and covered >= min_covered
            and precision >= min_precision
            and fidelity >= min_fidelity
        )
    return float(passes / replicates)


def _conditions(row: dict[str, Any]) -> tuple[Condition, ...]:
    return tuple(
        Condition(
            item["feature"],
            item["operator"],
            float(item["threshold"]),
            None if item.get("raw_threshold") is None else float(item["raw_threshold"]),
        )
        for item in row["antecedent"]
    )


def _passes(
    quality: dict[str, Any],
    *,
    stability: float,
    complexity: int,
) -> bool:
    gates = SYSTEM_B_CONFIG["validation"]
    return bool(
        float(quality["support"]) >= float(gates["min_support"])
        and int(quality["covered_count"]) >= int(gates["min_covered"])
        and float(quality["class_precision"]) >= float(gates["min_class_precision"])
        and float(quality["neural_fidelity"]) >= float(gates["min_neural_fidelity"])
        and stability >= float(gates["min_stability"])
        and complexity <= int(gates["max_complexity"])
    )


def build_duplicate_aware_validation(*, device_name: str) -> None:
    if device_name != "cpu":
        raise ValueError("Duplicate-aware validation is frozen to CPU.")
    if OUTPUT_DIR.exists():
        raise FileExistsError(f"Duplicate-aware analysis already exists: {OUTPUT_DIR}")
    git = _git_state(require_clean=True)
    manifest = load_accepted_r0_v2_manifest()
    frozen_a = _load_frozen_system_a_manifest()
    preprocessing = load_frozen_preprocessing()

    development = load_partition("development")
    X_dev = transform_frame(development.X, preprocessing, dtype=np.dtype("float32"))
    y_dev = development.y.to_numpy(dtype=np.int8, copy=True)
    validation_idx, _ = _development_split(y_dev)
    raw_validation = development.X.iloc[validation_idx].reset_index(drop=True)
    group_ids = _exact_pattern_group_ids(raw_validation)
    y_validation = y_dev[validation_idx]
    X_validation = X_dev[validation_idx]
    del development

    rows: list[dict[str, object]] = []
    seed_summaries: dict[str, Any] = {}

    for seed in SYSTEM_B_CONFIG["seeds"]:
        record = _record_for_seed(frozen_a, seed)
        model = _load_checkpoint_model(
            record,
            device=torch.device("cpu"),
            preprocessing_hash=preprocessing.state_hash,
        )
        dev_prob = predict_probabilities(
            model,
            X_dev,
            device=torch.device("cpu"),
            batch_size=SYSTEM_A_CONFIG["batch_size"],
        )
        neural = (dev_prob >= float(record["threshold"])).astype(np.int8)
        validation_neural = neural[validation_idx]

        entry = manifest["rule_artifacts"][str(seed)]
        artifact = json.loads((PROJECT_ROOT / entry["path"]).read_text(encoding="utf-8"))
        original_active_candidates = {
            str(rule["source_candidate_id"]) for rule in artifact["rules"]
        }
        pattern_pass_candidates: set[str] = set()
        changed = 0

        for candidate in artifact["candidate_log"]:
            if "candidate" not in candidate or "antecedent" not in candidate:
                continue
            mask = activation_mask(
                X_validation,
                feature_names=preprocessing.feature_columns,
                conditions=_conditions(candidate),
            )
            quality = _pattern_quality(
                mask,
                y_true=y_validation,
                neural_decision=validation_neural,
                consequent=int(candidate["consequent"]),
                group_ids=group_ids,
            )
            stability = _group_bootstrap_stability(
                quality,
                replicates=int(SYSTEM_B_CONFIG["validation"]["bootstrap_replicates"]),
                random_state=int(
                    SYSTEM_B_CONFIG["validation"]["bootstrap_random_state_base"]
                ) + seed,
                min_support=float(SYSTEM_B_CONFIG["validation"]["min_support"]),
                min_covered=int(SYSTEM_B_CONFIG["validation"]["min_covered"]),
                min_precision=float(
                    SYSTEM_B_CONFIG["validation"]["min_class_precision"]
                ),
                min_fidelity=float(
                    SYSTEM_B_CONFIG["validation"]["min_neural_fidelity"]
                ),
            )
            pattern_pass = _passes(
                quality,
                stability=stability,
                complexity=int(candidate["complexity"]),
            )
            if pattern_pass:
                pattern_pass_candidates.add(str(candidate["candidate"]))
            original_pass = bool(candidate["accepted_by_quality_gate"])
            changed += int(original_pass != pattern_pass)
            rows.append({
                "seed": seed,
                "candidate": candidate["candidate"],
                "consequent": int(candidate["consequent"]),
                "original_row_support": float(candidate["support"]),
                "pattern_support": float(quality["support"]),
                "original_row_covered_count": int(candidate["covered_count"]),
                "pattern_covered_count": int(quality["covered_count"]),
                "original_row_class_precision": float(candidate["class_precision"]),
                "pattern_class_precision": float(quality["class_precision"]),
                "original_row_neural_fidelity": float(candidate["neural_fidelity"]),
                "pattern_neural_fidelity": float(quality["neural_fidelity"]),
                "original_row_bootstrap_stability": float(candidate["stability"]),
                "pattern_group_bootstrap_stability": stability,
                "original_quality_gate_pass": original_pass,
                "pattern_quality_gate_pass": pattern_pass,
                "gate_decision_changed": original_pass != pattern_pass,
                "active_in_r0_v2": str(candidate["candidate"]) in original_active_candidates,
            })

        seed_summaries[str(seed)] = {
            "candidate_count": sum(
                1 for row in artifact["candidate_log"] if "candidate" in row
            ),
            "original_quality_pass_count": sum(
                1
                for row in artifact["candidate_log"]
                if row.get("accepted_by_quality_gate") is True
            ),
            "pattern_quality_pass_count": len(pattern_pass_candidates),
            "quality_gate_decision_change_count": changed,
            "r0_v2_active_candidate_count": len(original_active_candidates),
            "r0_v2_active_candidates_failing_pattern_gate": sorted(
                original_active_candidates - pattern_pass_candidates
            ),
        }
        del model, dev_prob, neural

    summary = {
        "analysis_format_version": 1,
        "analysis_id": ANALYSIS_ID,
        "evidence_status": "posthoc_duplicate_dependence_robustness",
        "analysis_git": git,
        "source_system_b_v2_manifest_sha256": manifest["manifest_sha256"],
        "data_access": {
            "training_used": False,
            "development_used": True,
            "pre_drift_used": False,
            "post_drift_used": False,
        },
        "validation_rows": len(validation_idx),
        "exact_pattern_groups": int(len(np.unique(group_ids))),
        "duplicate_excess_validation_rows": int(
            len(validation_idx) - len(np.unique(group_ids))
        ),
        "pattern_weighting": (
            "Each exact raw 77-feature pattern has equal total weight. Label "
            "contradictions within a pattern are preserved as correctness proportions."
        ),
        "bootstrap": (
            "Unstratified exact-pattern cluster bootstrap with the original replicate "
            "count and seed-matched RNG. This is a dependence sensitivity, not a "
            "replacement for the primary stratified row bootstrap."
        ),
        "seed_summaries": seed_summaries,
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=False)
    _write_csv_new(ROWS_PATH, rows)
    summary["artifact_sha256"] = canonical_json_hash(summary)
    _write_json_new(SUMMARY_PATH, summary)
    manifest_out = {
        "manifest_format_version": 1,
        "analysis_id": ANALYSIS_ID,
        "summary_artifact_sha256": summary["artifact_sha256"],
        "files": {
            "candidate_pattern_revalidation": {
                "path": ROWS_PATH.relative_to(PROJECT_ROOT).as_posix(),
                "sha256": sha256_file(ROWS_PATH),
            },
            "summary": {
                "path": SUMMARY_PATH.relative_to(PROJECT_ROOT).as_posix(),
                "sha256": sha256_file(SUMMARY_PATH),
            },
        },
    }
    manifest_out["manifest_sha256"] = canonical_json_hash(manifest_out)
    _write_json_new(MANIFEST_PATH, manifest_out)
    print(f"duplicate_aware_manifest={MANIFEST_PATH}")
    print(f"manifest_hash={manifest_out['manifest_sha256']}")
    print(f"validation_rows={len(validation_idx)}")
    print(f"exact_pattern_groups={len(np.unique(group_ids))}")
    print("pre_post_partitions_loaded=false")
    print("status=duplicate_aware_validation_written")


def verify_duplicate_aware_validation() -> None:
    if not MANIFEST_PATH.is_file():
        raise FileNotFoundError(f"Missing duplicate-aware manifest: {MANIFEST_PATH}")
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    stored = manifest.get("manifest_sha256")
    core = dict(manifest)
    core.pop("manifest_sha256", None)
    if canonical_json_hash(core) != stored:
        raise ValueError("Duplicate-aware manifest canonical hash mismatch.")
    for name, entry in manifest["files"].items():
        path = PROJECT_ROOT / entry["path"]
        if not path.is_file():
            raise FileNotFoundError(f"Missing duplicate-aware file {name!r}: {path}")
        if sha256_file(path) != entry["sha256"]:
            raise ValueError(f"Duplicate-aware file hash mismatch: {name!r}")
    print(f"duplicate_aware_manifest={MANIFEST_PATH}")
    print(f"manifest_hash={stored}")
    print("pre_post_partitions_loaded=false")
    print("status=verified")
