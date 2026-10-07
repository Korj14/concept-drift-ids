from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import platform
import subprocess
import time
from pathlib import Path
from typing import Any, Sequence

import numpy as np
import torch
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.model_selection import StratifiedShuffleSplit
from sklearn.tree import DecisionTreeClassifier
from torch import nn

from concept_drift_ids.frozen_preprocessing import load_frozen_preprocessing, transform_frame
from concept_drift_ids.neural import (
    binary_metrics,
    mean_ci95,
    predict_probabilities,
    select_mcc_threshold,
)
from concept_drift_ids.scenario_loader import PROJECT_ROOT, load_manifest, load_partition
from concept_drift_ids.scenario_manifest import sha256_file
from concept_drift_ids.symbolic import (
    Condition,
    Rule,
    activation_mask,
    apply_redundancy_and_conflict_policy,
    bootstrap_gate_stability,
    canonical_json_hash,
    canonicalize_conditions,
    fuse_scores,
    infer_symbolic,
    reporting_windows,
    rule_identifier,
    rule_quality,
    stratified_bootstrap_indices,
)
from concept_drift_ids.system_a import (
    SYSTEM_A_CONFIG,
    SYSTEM_A_MANIFEST_PATH,
    _load_checkpoint_model,
    _load_frozen_system_a_manifest,
)


SYSTEM_B_ID = "system_b_static_neuro_symbolic_v1"
RULE_BASE_VERSION = "R0.v1"
MANIFEST_PATH = PROJECT_ROOT / "data" / "manifests" / "system_b_v1.json"
RULE_DIR = PROJECT_ROOT / "data" / "rules" / "system_b_r0_v1"
EVALUATION_DIR = PROJECT_ROOT / "results" / "frozen" / "system_b_v1"
EVALUATION_MANIFEST_PATH = EVALUATION_DIR / "evaluation_manifest.json"
ACCEPTED_SYSTEM_B_MANIFEST_SHA256 = (
    "6e3589056d4c252c1a6c7cfd87b891fb8a24f1e30e86b17833b6035ea9ee86a8"
)
LOCK_PATH = PROJECT_ROOT / "requirements-lock.txt"

GOVERNING_SOURCE_HASHES = {
    "MAIN - Concept_Drift_NIDS_Research_Gap_Doctrine.docx":
        "f0700fc28e5c49ee50a6fab73db870725006ba52541a0d9cf4b285ccbe143a8f",
    "Reconciled_Pre-Stage_3_and_Stage_3_Implementation_Plan.docx":
        "83d1e101a525e840a1235743ac5fc050ca560f228df047bee17a84e80cbf3082",
}

SYSTEM_B_CONFIG: dict[str, Any] = {
    "protocol_version": 1,
    "rule_base_version": RULE_BASE_VERSION,
    "seeds": [0, 1, 2, 3, 4],
    "backend": "cpu",
    "development_split": {
        "validation_fraction": 0.60,
        "fusion_fraction": 0.40,
        "random_state": 20261007,
    },
    "shap": {
        "explainer": "DeepExplainer",
        "model_output": "raw_attack_logit",
        "background_per_class": 128,
        "attribution_per_class": 1024,
        "sample_random_state": 20261007,
        "selected_features": 12,
    },
    "surrogate": {
        "criterion": "gini",
        "splitter": "best",
        "max_depth": 4,
        "min_samples_leaf": 1000,
        "target": "frozen_neural_thresholded_decision",
        "class_weighting": "equal_total_weight_neural_predicted_classes",
    },
    "validation": {
        "min_support": 0.001,
        "min_covered": 100,
        "min_class_precision": 0.80,
        "min_neural_fidelity": 0.90,
        "bootstrap_replicates": 100,
        "bootstrap_random_state_base": 20261007,
        "min_stability": 0.90,
        "max_complexity": 4,
        "same_class_redundancy_overlap": 0.95,
        "cross_class_conflict_overlap": 0.50,
    },
    "fusion": {
        "neural_weight_grid": [0.50, 0.60, 0.70, 0.80, 0.90, 1.00],
        "probability_calibration": "none",
        "uncovered": "neural_fallback",
        "conflict": "symbolic_abstention_neural_fallback",
    },
    "reporting_windows": {
        "size": 5000,
        "stride": 5000,
        "minimum_final_remainder": 1000,
        "boundary_aligned": True,
    },
}


class _LogitColumn(nn.Module):
    def __init__(self, model: nn.Module) -> None:
        super().__init__()
        self.model = model

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.model(x).unsqueeze(1)


def _write_json_new(path: Path, payload: object) -> None:
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite accepted artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as file:
        json.dump(payload, file, indent=2, ensure_ascii=False, allow_nan=False)
        file.write("\n")


def _write_csv_new(path: Path, rows: list[dict[str, object]]) -> None:
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite accepted artifact: {path}")
    if not rows:
        raise ValueError(f"Cannot write empty evidence table: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _hash_int64(values: np.ndarray) -> str:
    return hashlib.sha256(np.asarray(values, dtype="<i8").tobytes(order="C")).hexdigest()


def _git_state(*, require_clean: bool = True) -> dict[str, str]:
    def run(*args: str) -> str:
        return subprocess.run(
            ["git", *args], cwd=PROJECT_ROOT, check=True,
            capture_output=True, text=True
        ).stdout.strip()

    status = run("status", "--porcelain")
    if require_clean and status:
        raise RuntimeError(
            "System-B operation requires a clean Git worktree. "
            "Commit the frozen protocol/rule artifacts before continuing."
        )
    return {
        "commit": run("rev-parse", "HEAD"),
        "branch": run("branch", "--show-current"),
        "clean": str(not bool(status)).lower(),
    }


def _runtime() -> dict[str, object]:
    import sklearn
    import shap
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "numpy": np.__version__,
        "torch": torch.__version__,
        "scikit_learn": sklearn.__version__,
        "shap": shap.__version__,
        "cpu_count": os.cpu_count(),
    }


def _require_environment(device_name: str) -> torch.device:
    if platform.python_version() != "3.11.9":
        raise RuntimeError("System B requires Python 3.11.9 exactly.")
    if device_name != "cpu":
        raise ValueError("System-B v1 is frozen to CPU.")
    return torch.device("cpu")


def _balanced_indices(y: np.ndarray, *, per_class: int, random_state: int) -> np.ndarray:
    y = np.asarray(y, dtype=np.int8)
    rng = np.random.default_rng(random_state)
    pieces = []
    for value in (0, 1):
        candidates = np.flatnonzero(y == value)
        if len(candidates) < per_class:
            raise ValueError(f"Class {value} has insufficient rows for frozen SHAP sampling.")
        pieces.append(rng.choice(candidates, size=per_class, replace=False))
    return np.concatenate(pieces)


def _development_split(y: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    splitter = StratifiedShuffleSplit(
        n_splits=1,
        test_size=SYSTEM_B_CONFIG["development_split"]["fusion_fraction"],
        random_state=SYSTEM_B_CONFIG["development_split"]["random_state"],
    )
    validation, fusion = next(splitter.split(np.zeros(len(y)), y))
    return np.asarray(validation, dtype=np.int64), np.asarray(fusion, dtype=np.int64)


def _load_build_partitions():
    return load_partition("training"), load_partition("development")


def _record_for_seed(frozen_a: dict[str, Any], seed: int) -> dict[str, Any]:
    rows = [row for row in frozen_a["seed_records"] if int(row["seed"]) == seed]
    if len(rows) != 1:
        raise ValueError(f"Expected one System-A seed record for {seed}.")
    return rows[0]


def _select_shap_features(
    model: nn.Module,
    X: np.ndarray,
    y: np.ndarray,
    *,
    feature_names: Sequence[str],
    background_idx: np.ndarray,
    attribution_idx: np.ndarray,
) -> tuple[list[str], list[dict[str, object]], float]:
    import shap

    started = time.perf_counter()
    wrapped = _LogitColumn(model).eval()
    background = torch.from_numpy(X[background_idx]).to(dtype=torch.float32)
    explained = torch.from_numpy(X[attribution_idx]).to(dtype=torch.float32)
    explainer = shap.DeepExplainer(wrapped, background)
    values = np.asarray(explainer.shap_values(explained, check_additivity=True), dtype=np.float64)
    if values.ndim == 3 and values.shape[-1] == 1:
        values = values[..., 0]
    if values.shape != (len(attribution_idx), len(feature_names)):
        raise ValueError(f"Unexpected SHAP output shape: {values.shape}")
    if not np.isfinite(values).all():
        raise ValueError("SHAP returned non-finite values.")

    absolute = np.abs(values)
    sampled_y = np.asarray(y, dtype=np.int8)[attribution_idx]
    vectors = [
        absolute.mean(axis=0),
        absolute[sampled_y == 0].mean(axis=0),
        absolute[sampled_y == 1].mean(axis=0),
    ]
    normalized = []
    for vector in vectors:
        maximum = float(vector.max())
        normalized.append(vector / maximum if maximum > 0 else np.zeros_like(vector))
    score = np.maximum.reduce(normalized)
    order = sorted(range(len(feature_names)), key=lambda i: (-float(score[i]), i))
    selected = [str(feature_names[i]) for i in order[:SYSTEM_B_CONFIG["shap"]["selected_features"]]]
    ranking = [
        {
            "rank": rank + 1,
            "feature": str(feature_names[i]),
            "selection_score": float(score[i]),
            "mean_abs_shap_global": float(vectors[0][i]),
            "mean_abs_shap_benign": float(vectors[1][i]),
            "mean_abs_shap_attack": float(vectors[2][i]),
        }
        for rank, i in enumerate(order)
    ]
    return selected, ranking, time.perf_counter() - started


def _fit_surrogate(
    X: np.ndarray,
    neural_decision: np.ndarray,
    *,
    feature_names: Sequence[str],
    selected: Sequence[str],
    seed: int,
) -> tuple[DecisionTreeClassifier, float]:
    lookup = {name: i for i, name in enumerate(feature_names)}
    columns = [lookup[name] for name in selected]
    target = np.asarray(neural_decision, dtype=np.int8)
    counts = np.bincount(target, minlength=2)
    if np.any(counts == 0):
        raise ValueError("Both frozen neural decision classes are required for surrogate fitting.")
    sample_weight = np.where(target == 0, len(target) / (2 * counts[0]), len(target) / (2 * counts[1]))
    tree = DecisionTreeClassifier(
        criterion="gini",
        splitter="best",
        max_depth=4,
        min_samples_leaf=1000,
        random_state=seed,
    )
    started = time.perf_counter()
    tree.fit(X[:, columns], target, sample_weight=sample_weight)
    return tree, time.perf_counter() - started


def _tree_paths(tree: DecisionTreeClassifier, selected: Sequence[str]):
    structure = tree.tree_
    out = []
    def walk(node: int, conditions: list[tuple[str, str, float]]) -> None:
        left = int(structure.children_left[node])
        right = int(structure.children_right[node])
        if left == right:
            out.append((node, list(conditions)))
            return
        feature = selected[int(structure.feature[node])]
        threshold = float(structure.threshold[node])
        walk(left, [*conditions, (feature, "<=", threshold)])
        walk(right, [*conditions, (feature, ">", threshold)])
    walk(0, [])
    return out


def _validate_candidates(
    tree: DecisionTreeClassifier,
    *,
    seed: int,
    X_train: np.ndarray,
    train_neural: np.ndarray,
    X_validation: np.ndarray,
    y_validation: np.ndarray,
    validation_neural: np.ndarray,
    feature_names: Sequence[str],
    selected: Sequence[str],
    means: np.ndarray,
    scales: np.ndarray,
    validation_evidence_id: str,
) -> tuple[list[Rule], list[dict[str, object]], float]:
    config = SYSTEM_B_CONFIG["validation"]
    bootstrap = stratified_bootstrap_indices(
        y_validation,
        replicates=config["bootstrap_replicates"],
        random_state=config["bootstrap_random_state_base"] + seed,
    )
    feature_index = {name: i for i, name in enumerate(feature_names)}
    eligible: list[Rule] = []
    masks: dict[str, np.ndarray] = {}
    log: list[dict[str, object]] = []
    started = time.perf_counter()

    for leaf, path in _tree_paths(tree, selected):
        canonical = canonicalize_conditions(path, feature_order=feature_names)
        conditions = tuple(
            Condition(
                c.feature,
                c.operator,
                c.threshold,
                c.threshold * float(scales[feature_index[c.feature]]) + float(means[feature_index[c.feature]]),
            )
            for c in canonical
        )
        train_mask = activation_mask(X_train, feature_names=feature_names, conditions=conditions)
        if not np.any(train_mask):
            log.append({"candidate": f"s{seed}-leaf{leaf}", "accepted": False, "reasons": ["zero_training_coverage"]})
            continue
        consequent = int(np.argmax(np.bincount(train_neural[train_mask], minlength=2)))
        rule_id = rule_identifier(seed=seed, conditions=conditions, consequent=consequent)
        mask = activation_mask(X_validation, feature_names=feature_names, conditions=conditions)
        quality = rule_quality(
            mask, y_true=y_validation, neural_decision=validation_neural, consequent=consequent
        )
        stability = bootstrap_gate_stability(
            mask,
            y_true=y_validation,
            neural_decision=validation_neural,
            consequent=consequent,
            bootstrap_indices=bootstrap,
            min_support=config["min_support"],
            min_covered=config["min_covered"],
            min_precision=config["min_class_precision"],
            min_fidelity=config["min_neural_fidelity"],
        )
        reasons = []
        if quality["support"] < config["min_support"]: reasons.append("support")
        if quality["covered_count"] < config["min_covered"]: reasons.append("covered_count")
        if quality["class_precision"] < config["min_class_precision"]: reasons.append("class_precision")
        if quality["neural_fidelity"] < config["min_neural_fidelity"]: reasons.append("neural_fidelity")
        if stability < config["min_stability"]: reasons.append("stability")
        if len(conditions) > config["max_complexity"]: reasons.append("complexity")
        accepted = not reasons
        log.append({
            "candidate": f"s{seed}-leaf{leaf}",
            "rule_id": rule_id,
            "antecedent": [condition.to_dict() for condition in conditions],
            "consequent": consequent,
            **quality,
            "stability": stability,
            "complexity": len(conditions),
            "accepted_by_quality_gate": accepted,
            "reasons": reasons,
        })
        if accepted:
            rule = Rule(
                rule_id=rule_id,
                lineage_id=rule_id,
                rule_base_version=RULE_BASE_VERSION,
                seed=seed,
                conditions=conditions,
                consequent=consequent,
                confidence=min(float(quality["class_precision"]), float(quality["neural_fidelity"])),
                support=float(quality["support"]),
                covered_count=int(quality["covered_count"]),
                class_precision=float(quality["class_precision"]),
                neural_fidelity=float(quality["neural_fidelity"]),
                stability=float(stability),
                complexity=len(conditions),
                lifecycle_state="active",
                source_candidate_id=f"s{seed}-leaf{leaf}",
                validation_evidence_id=validation_evidence_id,
            )
            eligible.append(rule)
            masks[rule.rule_id] = mask

    active, decisions = apply_redundancy_and_conflict_policy(
        eligible,
        masks,
        same_class_overlap=config["same_class_redundancy_overlap"],
        cross_class_overlap=config["cross_class_conflict_overlap"],
    )
    for decision in decisions:
        log.append({"policy_decision": decision})
    return active, log, time.perf_counter() - started


def _select_global_fusion(
    inputs: dict[int, tuple[np.ndarray, np.ndarray, dict[str, np.ndarray]]]
) -> tuple[float, dict[int, dict[str, object]], list[dict[str, object]]]:
    rows = []
    by_weight: dict[float, dict[int, dict[str, object]]] = {}
    for weight in SYSTEM_B_CONFIG["fusion"]["neural_weight_grid"]:
        seed_results = {}
        for seed, (y, neural, symbolic) in inputs.items():
            fused = fuse_scores(neural, symbolic, neural_weight=float(weight))
            threshold, metrics = select_mcc_threshold(y, fused)
            seed_results[seed] = {"threshold": float(threshold), "metrics": metrics}
            rows.append({"weight": float(weight), "seed": seed, "threshold": float(threshold), **metrics})
        by_weight[float(weight)] = seed_results

    def rank(weight: float):
        results = by_weight[weight].values()
        mcc = np.mean([r["metrics"]["mcc"] for r in results])
        f1 = np.mean([r["metrics"]["f1"] for r in results])
        fpr = np.mean([r["metrics"]["fpr"] for r in results])
        return (mcc, f1, -fpr, weight)

    selected = max(by_weight, key=rank)
    return selected, by_weight[selected], rows


def _rule_from_dict(payload: dict[str, Any]) -> Rule:
    return Rule(
        rule_id=payload["rule_id"],
        lineage_id=payload["lineage_id"],
        rule_base_version=payload["rule_base_version"],
        seed=int(payload["seed"]),
        conditions=tuple(
            Condition(
                item["feature"], item["operator"], float(item["threshold"]),
                None if item.get("raw_threshold") is None else float(item["raw_threshold"])
            )
            for item in payload["antecedent"]
        ),
        consequent=int(payload["consequent"]),
        confidence=float(payload["confidence"]),
        support=float(payload["support"]),
        covered_count=int(payload["covered_count"]),
        class_precision=float(payload["class_precision"]),
        neural_fidelity=float(payload["neural_fidelity"]),
        stability=float(payload["stability"]),
        complexity=int(payload["complexity"]),
        lifecycle_state=payload["lifecycle_state"],
        source_candidate_id=payload["source_candidate_id"],
        validation_evidence_id=payload["validation_evidence_id"],
        relations=tuple(payload.get("relations", [])),
    )


def build_and_freeze_system_b(*, device_name: str) -> None:
    device = _require_environment(device_name)
    if MANIFEST_PATH.exists() or RULE_DIR.exists():
        raise FileExistsError("System-B freeze artifacts already exist; refusing overwrite.")
    git = _git_state(require_clean=True)
    frozen_a = _load_frozen_system_a_manifest()
    preprocessing = load_frozen_preprocessing()
    scenario = load_manifest()

    training, development = _load_build_partitions()
    X_train = transform_frame(training.X, preprocessing, dtype=np.dtype("float32"))
    y_train = training.y.to_numpy(dtype=np.int8, copy=True)
    X_dev = transform_frame(development.X, preprocessing, dtype=np.dtype("float32"))
    y_dev = development.y.to_numpy(dtype=np.int8, copy=True)
    train_rows = training.provenance["scenario_row"].to_numpy(dtype=np.int64)
    dev_rows = development.provenance["scenario_row"].to_numpy(dtype=np.int64)
    del training, development

    validation_idx, fusion_idx = _development_split(y_dev)
    background_idx = _balanced_indices(
        y_train,
        per_class=SYSTEM_B_CONFIG["shap"]["background_per_class"],
        random_state=SYSTEM_B_CONFIG["shap"]["sample_random_state"],
    )
    attribution_idx = _balanced_indices(
        y_train,
        per_class=SYSTEM_B_CONFIG["shap"]["attribution_per_class"],
        random_state=SYSTEM_B_CONFIG["shap"]["sample_random_state"],
    )
    validation_id = _hash_int64(dev_rows[validation_idx])

    generated: dict[int, dict[str, Any]] = {}
    fusion_inputs = {}

    for seed in SYSTEM_B_CONFIG["seeds"]:
        record = _record_for_seed(frozen_a, seed)
        model = _load_checkpoint_model(
            record, device=device, preprocessing_hash=preprocessing.state_hash
        )
        selected, ranking, shap_seconds = _select_shap_features(
            model, X_train, y_train,
            feature_names=preprocessing.feature_columns,
            background_idx=background_idx,
            attribution_idx=attribution_idx,
        )
        train_prob = predict_probabilities(
            model, X_train, device=device, batch_size=SYSTEM_A_CONFIG["batch_size"]
        )
        dev_prob = predict_probabilities(
            model, X_dev, device=device, batch_size=SYSTEM_A_CONFIG["batch_size"]
        )
        threshold_a = float(record["threshold"])
        train_neural = (train_prob >= threshold_a).astype(np.int8)
        dev_neural = (dev_prob >= threshold_a).astype(np.int8)
        tree, tree_seconds = _fit_surrogate(
            X_train, train_neural,
            feature_names=preprocessing.feature_columns,
            selected=selected,
            seed=seed,
        )
        rules, candidate_log, validation_seconds = _validate_candidates(
            tree,
            seed=seed,
            X_train=X_train,
            train_neural=train_neural,
            X_validation=X_dev[validation_idx],
            y_validation=y_dev[validation_idx],
            validation_neural=dev_neural[validation_idx],
            feature_names=preprocessing.feature_columns,
            selected=selected,
            means=preprocessing.means,
            scales=preprocessing.scales,
            validation_evidence_id=validation_id,
        )
        if not rules:
            raise RuntimeError(
                f"Seed {seed} produced no validated active R0 rules. "
                "Do not relax gates using pre/post evidence; prospectively version the protocol."
            )
        symbolic = infer_symbolic(
            X_dev[fusion_idx], feature_names=preprocessing.feature_columns, rules=rules
        )
        fusion_inputs[seed] = (y_dev[fusion_idx], dev_prob[fusion_idx], symbolic)
        generated[seed] = {
            "seed": seed,
            "system_a_checkpoint_file": record["checkpoint_file"],
            "system_a_checkpoint_sha256": record["checkpoint_sha256"],
            "system_a_threshold": threshold_a,
            "selected_features": selected,
            "shap_ranking": ranking,
            "candidate_log": candidate_log,
            "rules": [rule.to_dict() for rule in rules],
            "timing_seconds": {
                "shap": shap_seconds,
                "surrogate_fit": tree_seconds,
                "candidate_validation": validation_seconds,
            },
        }
        del model, train_prob, dev_prob

    selected_weight, selected_seed_results, fusion_rows = _select_global_fusion(fusion_inputs)

    RULE_DIR.mkdir(parents=True, exist_ok=False)
    rule_inventory = {}
    for seed in SYSTEM_B_CONFIG["seeds"]:
        path = RULE_DIR / f"seed_{seed}.json"
        payload = {
            "artifact_format_version": 1,
            "system_id": SYSTEM_B_ID,
            "rule_base_version": RULE_BASE_VERSION,
            **generated[seed],
        }
        payload["artifact_sha256"] = canonical_json_hash(payload)
        _write_json_new(path, payload)
        rule_inventory[str(seed)] = {
            "path": path.relative_to(PROJECT_ROOT).as_posix(),
            "sha256": sha256_file(path),
            "artifact_sha256": payload["artifact_sha256"],
            "active_rule_count": len(payload["rules"]),
        }

    manifest = {
        "manifest_format_version": 1,
        "system_id": SYSTEM_B_ID,
        "rule_base_version": RULE_BASE_VERSION,
        "scenario_id": scenario["scenario_id"],
        "scenario_version": scenario["scenario_version"],
        "preprocessing_state_hash": preprocessing.state_hash,
        "system_a_manifest_sha256": frozen_a["manifest_sha256"],
        "system_a_manifest_file_sha256": sha256_file(SYSTEM_A_MANIFEST_PATH),
        "requirements_lock_sha256": sha256_file(LOCK_PATH),
        "governing_source_hashes": GOVERNING_SOURCE_HASHES,
        "config": SYSTEM_B_CONFIG,
        "config_sha256": canonical_json_hash(SYSTEM_B_CONFIG),
        "build_git": git,
        "runtime": _runtime(),
        "data_access": {
            "training_used": True,
            "development_used": True,
            "pre_drift_used": False,
            "post_drift_used": False,
        },
        "row_identities": {
            "training_scenario_rows_sha256": _hash_int64(train_rows),
            "development_validation_rows_sha256": _hash_int64(dev_rows[validation_idx]),
            "development_fusion_rows_sha256": _hash_int64(dev_rows[fusion_idx]),
            "shap_background_training_rows_sha256": _hash_int64(train_rows[background_idx]),
            "shap_attribution_training_rows_sha256": _hash_int64(train_rows[attribution_idx]),
        },
        "fusion": {
            "selected_neural_weight": selected_weight,
            "per_seed_thresholds": {
                str(seed): float(selected_seed_results[seed]["threshold"])
                for seed in SYSTEM_B_CONFIG["seeds"]
            },
            "development_grid_records": fusion_rows,
        },
        "rule_artifacts": rule_inventory,
    }
    manifest["manifest_sha256"] = canonical_json_hash(manifest)
    _write_json_new(MANIFEST_PATH, manifest)
    print(f"system_b_manifest={MANIFEST_PATH}")
    print(f"manifest_hash={manifest['manifest_sha256']}")
    print(f"selected_neural_weight={selected_weight:.2f}")
    for seed in SYSTEM_B_CONFIG["seeds"]:
        print(
            f"seed={seed} active_rules={rule_inventory[str(seed)]['active_rule_count']} "
            f"threshold={manifest['fusion']['per_seed_thresholds'][str(seed)]:.12g}"
        )
    print("pre_post_partitions_loaded=false")
    print("next_gate=commit_rule_artifacts_and_manifest_before_evaluation")


def _load_manifest_b(*, require_checkpoints: bool) -> dict[str, Any]:
    if not MANIFEST_PATH.exists():
        raise FileNotFoundError("System B is not frozen; run system-b build first.")
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    stored = manifest.get("manifest_sha256")
    core = dict(manifest)
    core.pop("manifest_sha256", None)
    if canonical_json_hash(core) != stored:
        raise ValueError("System-B manifest hash mismatch.")
    if stored != ACCEPTED_SYSTEM_B_MANIFEST_SHA256:
        raise ValueError(
            "System-B manifest is internally valid but is not the accepted R0.v1 identity."
        )
    if manifest["config_sha256"] != canonical_json_hash(SYSTEM_B_CONFIG):
        raise ValueError("System-B config no longer matches frozen manifest.")
    preprocessing = load_frozen_preprocessing()
    if manifest["preprocessing_state_hash"] != preprocessing.state_hash:
        raise ValueError("System-B preprocessing identity mismatch.")
    scenario = load_manifest()
    if manifest["scenario_id"] != scenario["scenario_id"]:
        raise ValueError("System-B scenario identity mismatch.")
    frozen_a = _load_frozen_system_a_manifest() if require_checkpoints else json.loads(
        SYSTEM_A_MANIFEST_PATH.read_text(encoding="utf-8")
    )
    if manifest["system_a_manifest_sha256"] != frozen_a["manifest_sha256"]:
        raise ValueError("System-B System-A manifest identity mismatch.")
    for seed, entry in manifest["rule_artifacts"].items():
        path = PROJECT_ROOT / entry["path"]
        if sha256_file(path) != entry["sha256"]:
            raise ValueError(f"Rule artifact hash mismatch for seed {seed}.")
        payload = json.loads(path.read_text(encoding="utf-8"))
        stored_artifact = payload.get("artifact_sha256")
        artifact_core = dict(payload)
        artifact_core.pop("artifact_sha256", None)
        if canonical_json_hash(artifact_core) != stored_artifact:
            raise ValueError(f"Rule artifact canonical hash mismatch for seed {seed}.")
        if stored_artifact != entry["artifact_sha256"]:
            raise ValueError(f"Rule artifact identity mismatch for seed {seed}.")
        if int(payload["seed"]) != int(seed):
            raise ValueError(f"Rule artifact seed mismatch for seed {seed}.")
        if len(payload["rules"]) != int(entry["active_rule_count"]):
            raise ValueError(f"Rule artifact active-count mismatch for seed {seed}.")
    return manifest


def _load_and_verify_evaluation_manifest_b(
    system_manifest: dict[str, Any],
) -> dict[str, Any]:
    if not EVALUATION_MANIFEST_PATH.exists():
        raise FileNotFoundError(
            f"Missing frozen System-B evaluation manifest: {EVALUATION_MANIFEST_PATH}"
        )
    evaluation = json.loads(EVALUATION_MANIFEST_PATH.read_text(encoding="utf-8"))
    stored = evaluation.get("manifest_sha256")
    core = dict(evaluation)
    core.pop("manifest_sha256", None)
    if canonical_json_hash(core) != stored:
        raise ValueError("System-B evaluation manifest hash mismatch.")
    if evaluation.get("system_manifest_sha256") != system_manifest["manifest_sha256"]:
        raise ValueError("System-B evaluation references the wrong R0 manifest.")
    files = evaluation.get("files")
    if not isinstance(files, dict) or not files:
        raise ValueError("System-B evaluation manifest has no file inventory.")
    for name, entry in files.items():
        path = PROJECT_ROOT / entry["path"]
        if not path.exists():
            raise FileNotFoundError(
                f"Missing frozen System-B evaluation artifact {name!r}: {path}"
            )
        if sha256_file(path) != entry["sha256"]:
            raise ValueError(
                f"Frozen System-B evaluation artifact hash mismatch for {name!r}."
            )
    return evaluation


def verify_system_b() -> None:
    manifest = _load_manifest_b(require_checkpoints=True)
    print(f"system_b_manifest={MANIFEST_PATH}")
    print(f"manifest_hash={manifest['manifest_sha256']}")
    if EVALUATION_MANIFEST_PATH.exists():
        evaluation = _load_and_verify_evaluation_manifest_b(manifest)
        print(f"evaluation_manifest={EVALUATION_MANIFEST_PATH}")
        print(f"evaluation_manifest_hash={evaluation['manifest_sha256']}")
        print("evaluation_status=verified")
    else:
        print("evaluation_status=not_present")
    print("pre_post_partitions_loaded=false")
    print("status=verified")


def _load_rules(manifest: dict[str, Any], seed: int) -> list[Rule]:
    entry = manifest["rule_artifacts"][str(seed)]
    payload = json.loads((PROJECT_ROOT / entry["path"]).read_text(encoding="utf-8"))
    return [_rule_from_dict(item) for item in payload["rules"]]


def _confusion(y: np.ndarray, scores: np.ndarray, threshold: float) -> dict[str, int | float]:
    y = np.asarray(y, dtype=np.int8)
    predicted = np.asarray(scores) >= threshold
    tn = int(np.sum((y == 0) & ~predicted))
    fp = int(np.sum((y == 0) & predicted))
    fn = int(np.sum((y == 1) & ~predicted))
    tp = int(np.sum((y == 1) & predicted))
    return {
        "sample_count": len(y),
        "benign_count": int(np.sum(y == 0)),
        "attack_count": int(np.sum(y == 1)),
        "attack_prevalence": float(np.mean(y == 1)),
        "tn": tn, "fp": fp, "fn": fn, "tp": tp,
    }


def _safe_window_metrics(y: np.ndarray, scores: np.ndarray, threshold: float) -> dict[str, object]:
    y = np.asarray(y, dtype=np.int8)
    scores = np.asarray(scores, dtype=np.float64)
    if len(np.unique(y)) >= 2:
        return binary_metrics(y, scores, threshold)

    predicted = (scores >= threshold).astype(np.int8)
    tn = int(np.sum((y == 0) & (predicted == 0)))
    fp = int(np.sum((y == 0) & (predicted == 1)))
    fn = int(np.sum((y == 1) & (predicted == 0)))
    tp = int(np.sum((y == 1) & (predicted == 1)))
    accuracy = float(np.mean(predicted == y))
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    fpr = fp / (fp + tn) if fp + tn else 0.0
    if np.all(y == 0):
        balanced_accuracy = tn / (tn + fp) if tn + fp else 0.0
    else:
        balanced_accuracy = tp / (tp + fn) if tp + fn else 0.0
    return {
        "accuracy": accuracy,
        "balanced_accuracy": float(balanced_accuracy),
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
        "fpr": float(fpr),
        "mcc": 0.0,
        "roc_auc": None,
        "average_precision": None,
    }


def _symbolic_summary(
    symbolic: dict[str, np.ndarray],
    neural: np.ndarray,
) -> dict[str, float | None]:
    covered = symbolic["covered"]
    symbolic_class = symbolic["symbolic_class"]
    return {
        "resolved_coverage": float(np.mean(covered)),
        "raw_activation_coverage": float(np.mean(symbolic["raw_activated"])),
        "uncovered_rate": float(np.mean(symbolic["uncovered"])),
        "conflict_abstention_rate": float(np.mean(symbolic["conflict_abstain"])),
        "symbolic_neural_fidelity": (
            float(np.mean(symbolic_class[covered] == neural[covered]))
            if np.any(covered) else None
        ),
    }


EVIDENCE_METRICS = (
    "accuracy",
    "balanced_accuracy",
    "precision",
    "recall",
    "f1",
    "fpr",
    "mcc",
    "roc_auc",
    "average_precision",
    "resolved_coverage",
    "raw_activation_coverage",
    "uncovered_rate",
    "conflict_abstention_rate",
    "symbolic_neural_fidelity",
)

RULE_STALENESS_METRICS = (
    "support",
    "covered_count",
    "class_precision",
    "neural_fidelity",
    "stability",
    "activation_rate",
)


def _build_metric_tables(
    detection_rows: list[dict[str, object]],
    *,
    scenario_version: int,
    metric_names: Sequence[str] = EVIDENCE_METRICS,
) -> tuple[
    list[dict[str, object]],
    list[dict[str, object]],
    list[dict[str, object]],
    list[dict[str, object]],
]:
    if not detection_rows:
        raise ValueError("Detection evidence is empty.")
    system_id = str(detection_rows[0]["system_id"])
    scenario_id = str(detection_rows[0]["scenario_id"])
    by_partition_seed = {
        (str(row["partition"]), int(row["seed"])): row
        for row in detection_rows
    }

    metric_rows: list[dict[str, object]] = []
    aggregate_rows: list[dict[str, object]] = []
    for partition in ("pre_drift", "post_drift"):
        partition_rows = [
            by_partition_seed[(partition, seed)]
            for seed in SYSTEM_B_CONFIG["seeds"]
        ]
        for row in partition_rows:
            for metric in metric_names:
                value = row[metric]
                if value is None:
                    continue
                metric_rows.append(
                    {
                        "system_id": system_id,
                        "scenario_id": scenario_id,
                        "scenario_version": scenario_version,
                        "partition": partition,
                        "seed": int(row["seed"]),
                        "threshold": float(row["threshold"]),
                        "metric": metric,
                        "value": float(value),
                    }
                )
        for metric in metric_names:
            values = [
                float(row[metric])
                for row in partition_rows
                if row[metric] is not None
            ]
            if not values:
                continue
            summary = mean_ci95(values)
            aggregate_rows.append(
                {
                    "system_id": system_id,
                    "scenario_id": scenario_id,
                    "scenario_version": scenario_version,
                    "partition": partition,
                    "metric": metric,
                    "n_seeds": summary["n"],
                    "mean": summary["mean"],
                    "std": summary["std"],
                    "ci95_low": summary["ci95_low"],
                    "ci95_high": summary["ci95_high"],
                }
            )

    paired_rows: list[dict[str, object]] = []
    aggregate_paired_rows: list[dict[str, object]] = []
    for metric in metric_names:
        deltas: list[float] = []
        for seed in SYSTEM_B_CONFIG["seeds"]:
            pre = by_partition_seed[("pre_drift", seed)][metric]
            post = by_partition_seed[("post_drift", seed)][metric]
            if pre is None or post is None:
                continue
            delta = float(post) - float(pre)
            deltas.append(delta)
            paired_rows.append(
                {
                    "system_id": system_id,
                    "scenario_id": scenario_id,
                    "scenario_version": scenario_version,
                    "from_partition": "pre_drift",
                    "to_partition": "post_drift",
                    "seed": seed,
                    "metric": metric,
                    "delta": delta,
                }
            )
        if deltas:
            summary = mean_ci95(deltas)
            aggregate_paired_rows.append(
                {
                    "system_id": system_id,
                    "scenario_id": scenario_id,
                    "scenario_version": scenario_version,
                    "from_partition": "pre_drift",
                    "to_partition": "post_drift",
                    "metric": metric,
                    "n_seeds": summary["n"],
                    "mean_delta": summary["mean"],
                    "std_delta": summary["std"],
                    "ci95_low": summary["ci95_low"],
                    "ci95_high": summary["ci95_high"],
                }
            )
    return metric_rows, aggregate_rows, paired_rows, aggregate_paired_rows


def _rule_gate_pass(row: dict[str, object]) -> bool:
    return bool(
        float(row["support"]) >= SYSTEM_B_CONFIG["validation"]["min_support"]
        and int(row["covered_count"]) >= SYSTEM_B_CONFIG["validation"]["min_covered"]
        and float(row["class_precision"]) >= SYSTEM_B_CONFIG["validation"]["min_class_precision"]
        and float(row["neural_fidelity"]) >= SYSTEM_B_CONFIG["validation"]["min_neural_fidelity"]
        and float(row["stability"]) >= SYSTEM_B_CONFIG["validation"]["min_stability"]
        and int(row["complexity"]) <= SYSTEM_B_CONFIG["validation"]["max_complexity"]
    )


def _rule_staleness_deltas(
    rule_rows: list[dict[str, object]],
    *,
    scenario_version: int,
    system_id: str = SYSTEM_B_ID,
) -> list[dict[str, object]]:
    by_key = {
        (str(row["partition"]), int(row["seed"]), str(row["rule_id"])): row
        for row in rule_rows
    }
    pre_keys = {
        (seed, rule_id)
        for partition, seed, rule_id in by_key
        if partition == "pre_drift"
    }
    post_keys = {
        (seed, rule_id)
        for partition, seed, rule_id in by_key
        if partition == "post_drift"
    }
    if pre_keys != post_keys:
        raise ValueError("Pre/post rule identities differ; cannot compute staleness deltas.")

    rows: list[dict[str, object]] = []
    for seed, rule_id in sorted(pre_keys):
        pre = by_key[("pre_drift", seed, rule_id)]
        post = by_key[("post_drift", seed, rule_id)]
        pre_pass = _rule_gate_pass(pre)
        post_pass = _rule_gate_pass(post)
        out: dict[str, object] = {
            "system_id": system_id,
            "scenario_id": str(pre["scenario_id"]),
            "scenario_version": scenario_version,
            "seed": seed,
            "rule_id": rule_id,
            "consequent": int(pre["consequent"]),
            "complexity": int(pre["complexity"]),
            "pre_gate_pass": pre_pass,
            "post_gate_pass": post_pass,
            "gate_transition": (
                ("pass" if pre_pass else "fail")
                + "_to_"
                + ("pass" if post_pass else "fail")
            ),
        }
        for metric in RULE_STALENESS_METRICS:
            pre_value = float(pre[metric])
            post_value = float(post[metric])
            out[f"pre_{metric}"] = pre_value
            out[f"post_{metric}"] = post_value
            out[f"delta_{metric}"] = post_value - pre_value
        rows.append(out)
    return rows


def evaluate_system_b(*, device_name: str) -> None:
    device = _require_environment(device_name)
    if EVALUATION_MANIFEST_PATH.exists() or EVALUATION_DIR.exists():
        raise FileExistsError("Frozen System-B evaluation already exists; refusing overwrite.")
    evaluation_git = _git_state(require_clean=True)
    manifest = _load_manifest_b(require_checkpoints=True)
    frozen_a = _load_frozen_system_a_manifest()
    preprocessing = load_frozen_preprocessing()
    neural_weight = float(manifest["fusion"]["selected_neural_weight"])
    evaluation_runtime = _runtime()

    detection_rows: list[dict[str, object]] = []
    rule_rows: list[dict[str, object]] = []
    window_rows: list[dict[str, object]] = []

    for partition_name in ("pre_drift", "post_drift"):
        partition = load_partition(partition_name)
        X = transform_frame(partition.X, preprocessing, dtype=np.dtype("float32"))
        y = partition.y.to_numpy(dtype=np.int8, copy=True)
        del partition

        for seed in SYSTEM_B_CONFIG["seeds"]:
            record = _record_for_seed(frozen_a, seed)
            model = _load_checkpoint_model(
                record, device=device, preprocessing_hash=preprocessing.state_hash
            )
            neural_prob = predict_probabilities(
                model, X, device=device, batch_size=SYSTEM_A_CONFIG["batch_size"]
            )
            neural_decision = (neural_prob >= float(record["threshold"])).astype(np.int8)
            rules = _load_rules(manifest, seed)
            started = time.perf_counter()
            symbolic = infer_symbolic(X, feature_names=preprocessing.feature_columns, rules=rules)
            fused = fuse_scores(neural_prob, symbolic, neural_weight=neural_weight)
            inference_seconds = time.perf_counter() - started
            threshold = float(manifest["fusion"]["per_seed_thresholds"][str(seed)])
            metrics = binary_metrics(y, fused, threshold)
            detection_rows.append({
                "system_id": SYSTEM_B_ID,
                "scenario_id": manifest["scenario_id"],
                "partition": partition_name,
                "seed": seed,
                "threshold": threshold,
                "neural_weight": neural_weight,
                **_confusion(y, fused, threshold),
                **metrics,
                **_symbolic_summary(symbolic, neural_decision),
                "symbolic_inference_seconds": inference_seconds,
            })

            bootstrap = stratified_bootstrap_indices(
                y,
                replicates=SYSTEM_B_CONFIG["validation"]["bootstrap_replicates"],
                random_state=SYSTEM_B_CONFIG["validation"]["bootstrap_random_state_base"] + seed,
            )
            for rule_index, rule in enumerate(rules):
                mask = symbolic["activation_matrix"][:, rule_index]
                quality = rule_quality(
                    mask, y_true=y, neural_decision=neural_decision, consequent=rule.consequent
                )
                stability = bootstrap_gate_stability(
                    mask,
                    y_true=y,
                    neural_decision=neural_decision,
                    consequent=rule.consequent,
                    bootstrap_indices=bootstrap,
                    min_support=SYSTEM_B_CONFIG["validation"]["min_support"],
                    min_covered=SYSTEM_B_CONFIG["validation"]["min_covered"],
                    min_precision=SYSTEM_B_CONFIG["validation"]["min_class_precision"],
                    min_fidelity=SYSTEM_B_CONFIG["validation"]["min_neural_fidelity"],
                )
                rule_rows.append({
                    "system_id": SYSTEM_B_ID,
                    "scenario_id": manifest["scenario_id"],
                    "partition": partition_name,
                    "seed": seed,
                    "rule_id": rule.rule_id,
                    "consequent": rule.consequent,
                    **quality,
                    "stability": stability,
                    "complexity": rule.complexity,
                    "activation_rate": float(np.mean(mask)),
                })

            for window_index, (start, stop) in enumerate(reporting_windows(len(y))):
                sy = y[start:stop]
                ss = fused[start:stop]
                s_symbolic = {
                    key: value[start:stop]
                    for key, value in symbolic.items()
                    if key != "activation_matrix"
                }
                window_rows.append({
                    "system_id": SYSTEM_B_ID,
                    "scenario_id": manifest["scenario_id"],
                    "partition": partition_name,
                    "seed": seed,
                    "window_index": window_index,
                    "row_start": start,
                    "row_end": stop,
                    **_confusion(sy, ss, threshold),
                    **_safe_window_metrics(sy, ss, threshold),
                    **_symbolic_summary(s_symbolic, neural_decision[start:stop]),
                })
            del model, neural_prob, neural_decision, symbolic, fused

    (
        metric_rows,
        aggregate_metric_rows,
        paired_delta_rows,
        aggregate_paired_delta_rows,
    ) = _build_metric_tables(
        detection_rows,
        scenario_version=int(manifest["scenario_version"]),
    )
    staleness_rows = _rule_staleness_deltas(
        rule_rows,
        scenario_version=int(manifest["scenario_version"]),
    )

    EVALUATION_DIR.mkdir(parents=True, exist_ok=False)
    detection_path = EVALUATION_DIR / "detection_by_seed.csv"
    metric_path = EVALUATION_DIR / "metrics_by_seed.csv"
    aggregate_metric_path = EVALUATION_DIR / "aggregate_metrics.csv"
    paired_delta_path = EVALUATION_DIR / "paired_deltas_by_seed.csv"
    aggregate_paired_delta_path = EVALUATION_DIR / "aggregate_paired_deltas.csv"
    rule_path = EVALUATION_DIR / "rule_quality_by_seed_partition.csv"
    staleness_path = EVALUATION_DIR / "rule_staleness_deltas.csv"
    window_path = EVALUATION_DIR / "window_metrics.csv"
    _write_csv_new(detection_path, detection_rows)
    _write_csv_new(metric_path, metric_rows)
    _write_csv_new(aggregate_metric_path, aggregate_metric_rows)
    _write_csv_new(paired_delta_path, paired_delta_rows)
    _write_csv_new(aggregate_paired_delta_path, aggregate_paired_delta_rows)
    _write_csv_new(rule_path, rule_rows)
    _write_csv_new(staleness_path, staleness_rows)
    _write_csv_new(window_path, window_rows)

    summary = {
        "evaluation_format_version": 1,
        "system_id": SYSTEM_B_ID,
        "system_manifest_sha256": manifest["manifest_sha256"],
        "scenario_id": manifest["scenario_id"],
        "scenario_version": manifest["scenario_version"],
        "evaluation_git": evaluation_git,
        "runtime": evaluation_runtime,
        "data_access": {"pre_drift_used": True, "post_drift_used": True},
        "metric_roles": {
            "detection": [
                "precision", "recall", "f1", "fpr", "mcc",
                "roc_auc", "average_precision",
            ],
            "secondary_detection": ["accuracy", "balanced_accuracy"],
            "symbolic_aggregate": [
                "resolved_coverage", "raw_activation_coverage",
                "uncovered_rate", "conflict_abstention_rate",
                "symbolic_neural_fidelity",
            ],
            "rule_staleness": list(RULE_STALENESS_METRICS),
        },
        "rows": {
            "detection": len(detection_rows),
            "metrics_by_seed": len(metric_rows),
            "aggregate_metrics": len(aggregate_metric_rows),
            "paired_deltas": len(paired_delta_rows),
            "aggregate_paired_deltas": len(aggregate_paired_delta_rows),
            "rule_quality": len(rule_rows),
            "rule_staleness_deltas": len(staleness_rows),
            "windows": len(window_rows),
        },
    }
    summary_path = EVALUATION_DIR / "system_b_evaluation.json"
    _write_json_new(summary_path, summary)

    files = {
        "summary": summary_path,
        "detection_by_seed": detection_path,
        "metrics_by_seed": metric_path,
        "aggregate_metrics": aggregate_metric_path,
        "paired_deltas_by_seed": paired_delta_path,
        "aggregate_paired_deltas": aggregate_paired_delta_path,
        "rule_quality": rule_path,
        "rule_staleness_deltas": staleness_path,
        "window_metrics": window_path,
    }
    evaluation_manifest = {
        "manifest_format_version": 1,
        "evaluation_id": "system_b_static_evaluation_v1",
        "system_id": SYSTEM_B_ID,
        "system_manifest_sha256": manifest["manifest_sha256"],
        "scenario_id": manifest["scenario_id"],
        "scenario_version": manifest["scenario_version"],
        "preprocessing_state_hash": preprocessing.state_hash,
        "evaluation_git": evaluation_git,
        "runtime": evaluation_runtime,
        "files": {
            name: {
                "path": path.relative_to(PROJECT_ROOT).as_posix(),
                "sha256": sha256_file(path),
            }
            for name, path in files.items()
        },
    }
    evaluation_manifest["manifest_sha256"] = canonical_json_hash(evaluation_manifest)
    _write_json_new(EVALUATION_MANIFEST_PATH, evaluation_manifest)
    print(f"evaluation_manifest={EVALUATION_MANIFEST_PATH}")
    print(f"evaluation_manifest_hash={evaluation_manifest['manifest_sha256']}")
    print("status=frozen_system_b_evaluation_written")


def main() -> None:
    parser = argparse.ArgumentParser(description="System B static neuro-symbolic baseline")
    subparsers = parser.add_subparsers(dest="command", required=True)
    build = subparsers.add_parser("build")
    build.add_argument("--device", default="cpu")
    subparsers.add_parser("verify")
    evaluate = subparsers.add_parser("evaluate")
    evaluate.add_argument("--device", default="cpu")
    subparsers.add_parser("supplement")
    subparsers.add_parser("verify-supplement")
    subparsers.add_parser("audit-r0-protocol")
    subparsers.add_parser("semantic-analysis")
    subparsers.add_parser("verify-semantic-analysis")
    build_v2 = subparsers.add_parser("build-r0-v2")
    build_v2.add_argument("--device", default="cpu")
    subparsers.add_parser("verify-r0-v2")
    evaluate_v2 = subparsers.add_parser("evaluate-r0-v2")
    evaluate_v2.add_argument("--device", default="cpu")
    subparsers.add_parser("verify-r0-v2-evaluation")
    dtype_audit = subparsers.add_parser("audit-dtype-conformance")
    dtype_audit.add_argument("--device", default="cpu")
    subparsers.add_parser("verify-dtype-conformance-audit")
    subparsers.add_parser("audit-scenario-assumptions")
    subparsers.add_parser("verify-scenario-assumption-audit")
    seen_unseen = subparsers.add_parser("analyze-seen-unseen")
    seen_unseen.add_argument("--device", default="cpu")
    subparsers.add_parser("verify-seen-unseen")
    selection_robustness = subparsers.add_parser("build-selection-robustness")
    selection_robustness.add_argument("--device", default="cpu")
    subparsers.add_parser("verify-selection-robustness")
    eval_robustness = subparsers.add_parser("evaluate-selection-robustness")
    eval_robustness.add_argument("--device", default="cpu")
    subparsers.add_parser("verify-selection-robustness-evaluation")
    duplicate_aware = subparsers.add_parser("analyze-duplicate-aware-validation")
    duplicate_aware.add_argument("--device", default="cpu")
    subparsers.add_parser("verify-duplicate-aware-validation")
    fusion_robustness = subparsers.add_parser("build-fusion-authority-robustness")
    fusion_robustness.add_argument("--device", default="cpu")
    subparsers.add_parser("verify-fusion-authority-robustness")
    eval_fusion_robustness = subparsers.add_parser("evaluate-fusion-authority-robustness")
    eval_fusion_robustness.add_argument("--device", default="cpu")
    subparsers.add_parser("verify-fusion-authority-robustness-evaluation")
    dedup_teacher_r0 = subparsers.add_parser("build-pattern-dedup-teacher-r0")
    dedup_teacher_r0.add_argument("--device", default="cpu")
    subparsers.add_parser("verify-pattern-dedup-teacher-r0")
    args = parser.parse_args()
    if args.command == "build":
        build_and_freeze_system_b(device_name=args.device)
    elif args.command == "verify":
        verify_system_b()
    elif args.command == "evaluate":
        evaluate_system_b(device_name=args.device)
    elif args.command == "supplement":
        from concept_drift_ids.system_b_evidence import build_system_b_supplement
        build_system_b_supplement()
    elif args.command == "verify-supplement":
        from concept_drift_ids.system_b_evidence import verify_system_b_supplement
        verify_system_b_supplement()
    elif args.command == "audit-r0-protocol":
        from concept_drift_ids.system_b_audit import audit_frozen_r0_protocol
        audit_frozen_r0_protocol()
    elif args.command == "semantic-analysis":
        from concept_drift_ids.system_b_semantic_analysis import build_semantic_analysis
        build_semantic_analysis()
    elif args.command == "verify-semantic-analysis":
        from concept_drift_ids.system_b_semantic_analysis import verify_semantic_analysis
        verify_semantic_analysis()
    elif args.command == "build-r0-v2":
        from concept_drift_ids.system_b_r0_v2 import build_and_freeze_r0_v2
        build_and_freeze_r0_v2(device_name=args.device)
    elif args.command == "verify-r0-v2":
        from concept_drift_ids.system_b_r0_v2 import verify_r0_v2
        verify_r0_v2()
    elif args.command == "evaluate-r0-v2":
        from concept_drift_ids.system_b_v2_evaluation import evaluate_r0_v2
        evaluate_r0_v2(device_name=args.device)
    elif args.command == "verify-r0-v2-evaluation":
        from concept_drift_ids.system_b_v2_evaluation import verify_r0_v2_evaluation
        verify_r0_v2_evaluation()
    elif args.command == "audit-dtype-conformance":
        from concept_drift_ids.system_b_dtype_audit import audit_dtype_conformance
        audit_dtype_conformance(device_name=args.device)
    elif args.command == "verify-dtype-conformance-audit":
        from concept_drift_ids.system_b_dtype_audit import verify_dtype_conformance_audit
        verify_dtype_conformance_audit()
    elif args.command == "audit-scenario-assumptions":
        from concept_drift_ids.retrospective_scenario_audit import build_retrospective_scenario_audit
        build_retrospective_scenario_audit()
    elif args.command == "verify-scenario-assumption-audit":
        from concept_drift_ids.retrospective_scenario_audit import verify_retrospective_scenario_audit
        verify_retrospective_scenario_audit()
    elif args.command == "analyze-seen-unseen":
        from concept_drift_ids.system_ab_seen_unseen import build_seen_unseen_analysis
        build_seen_unseen_analysis(device_name=args.device)
    elif args.command == "verify-seen-unseen":
        from concept_drift_ids.system_ab_seen_unseen import verify_seen_unseen_analysis
        verify_seen_unseen_analysis()
    elif args.command == "build-selection-robustness":
        from concept_drift_ids.system_b_selection_robustness import build_selection_robustness
        build_selection_robustness(device_name=args.device)
    elif args.command == "verify-selection-robustness":
        from concept_drift_ids.system_b_selection_robustness import verify_selection_robustness
        verify_selection_robustness()
    elif args.command == "evaluate-selection-robustness":
        from concept_drift_ids.system_b_selection_robustness_evaluation import evaluate_selection_robustness
        evaluate_selection_robustness(device_name=args.device)
    elif args.command == "verify-selection-robustness-evaluation":
        from concept_drift_ids.system_b_selection_robustness_evaluation import verify_selection_robustness_evaluation
        verify_selection_robustness_evaluation()
    elif args.command == "analyze-duplicate-aware-validation":
        from concept_drift_ids.system_b_duplicate_robustness import build_duplicate_aware_validation
        build_duplicate_aware_validation(device_name=args.device)
    elif args.command == "verify-duplicate-aware-validation":
        from concept_drift_ids.system_b_duplicate_robustness import verify_duplicate_aware_validation
        verify_duplicate_aware_validation()
    elif args.command == "build-fusion-authority-robustness":
        from concept_drift_ids.system_b_fusion_robustness import build_fusion_authority_selection
        build_fusion_authority_selection(device_name=args.device)
    elif args.command == "verify-fusion-authority-robustness":
        from concept_drift_ids.system_b_fusion_robustness import verify_fusion_authority_selection
        verify_fusion_authority_selection()
    elif args.command == "evaluate-fusion-authority-robustness":
        from concept_drift_ids.system_b_fusion_robustness_evaluation import evaluate_fusion_authority
        evaluate_fusion_authority(device_name=args.device)
    elif args.command == "verify-fusion-authority-robustness-evaluation":
        from concept_drift_ids.system_b_fusion_robustness_evaluation import verify_fusion_authority_evaluation
        verify_fusion_authority_evaluation()
    elif args.command == "build-pattern-dedup-teacher-r0":
        from concept_drift_ids.system_b_dedup_teacher_robustness import build_pattern_dedup_teacher_r0
        build_pattern_dedup_teacher_r0(device_name=args.device)
    elif args.command == "verify-pattern-dedup-teacher-r0":
        from concept_drift_ids.system_b_dedup_teacher_robustness import verify_pattern_dedup_teacher_r0
        verify_pattern_dedup_teacher_r0()
    else:
        raise ValueError(f"Unhandled System-B command: {args.command}")


if __name__ == "__main__":
    main()
