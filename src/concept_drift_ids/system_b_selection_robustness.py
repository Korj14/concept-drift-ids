from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

import numpy as np
import torch
from sklearn.model_selection import StratifiedShuffleSplit

from concept_drift_ids.frozen_preprocessing import load_frozen_preprocessing, transform_frame
from concept_drift_ids.neural import predict_probabilities
from concept_drift_ids.scenario_loader import PROJECT_ROOT, load_partition
from concept_drift_ids.scenario_manifest import sha256_file
from concept_drift_ids.symbolic import (
    Condition,
    Rule,
    activation_mask,
    apply_redundancy_and_conflict_policy,
    bootstrap_gate_stability,
    canonical_json_hash,
    canonicalize_conditions,
    infer_symbolic,
    rule_identifier,
    rule_quality,
    stratified_bootstrap_indices,
)
from concept_drift_ids.system_a import (
    SYSTEM_A_CONFIG,
    _load_checkpoint_model,
    _load_frozen_system_a_manifest,
)
from concept_drift_ids.system_b import (
    SYSTEM_B_CONFIG,
    _fit_surrogate,
    _git_state,
    _record_for_seed,
    _require_environment,
    _select_global_fusion,
    _tree_paths,
    _write_json_new,
)
from concept_drift_ids.system_b_r0_v2 import (
    ACCEPTED_SYSTEM_B_V2_MANIFEST_SHA256,
    load_accepted_r0_v2_manifest,
    weighted_leaf_consequent,
)


SELECTION_ID = "system_b_selection_robustness_v1"
OUTPUT_DIR = PROJECT_ROOT / "data" / "robustness" / SELECTION_ID
MANIFEST_PATH = OUTPUT_DIR / "manifest.json"
VARIANT_DIR = OUTPUT_DIR / "variants"

PRIMARY_SPLIT_SEED = 20261007
ALT_SPLIT_SEEDS = (20261008, 20261009, 20261010, 20261011)


@dataclass(frozen=True)
class VariantSpec:
    variant_id: str
    family: str
    development_split_seed: int = PRIMARY_SPLIT_SEED
    selected_feature_policy: str = "primary"
    gate_override_key: str | None = None
    gate_override_value: float | int | None = None


def _variant_specs() -> tuple[VariantSpec, ...]:
    specs = [
        VariantSpec(
            "destination_port_excluded",
            "destination_port",
            selected_feature_policy="exclude_destination_port",
        ),
        VariantSpec(
            "shap_global_mean_abs",
            "shap_aggregation",
            selected_feature_policy="global_mean_abs",
        ),
        VariantSpec(
            "shap_equal_class_normalized",
            "shap_aggregation",
            selected_feature_policy="equal_class_normalized",
        ),
    ]
    specs.extend(
        VariantSpec(
            f"development_split_{seed}",
            "development_split",
            development_split_seed=seed,
        )
        for seed in ALT_SPLIT_SEEDS
    )
    gate_variants = {
        "min_support": (0.0005, 0.002),
        "min_class_precision": (0.75, 0.85),
        "min_neural_fidelity": (0.85, 0.95),
        "min_stability": (0.80, 0.95),
        "max_complexity": (3, 5),
    }
    for key, values in gate_variants.items():
        for value in values:
            token = str(value).replace(".", "p")
            specs.append(
                VariantSpec(
                    f"gate_{key}_{token}",
                    "rule_gate",
                    gate_override_key=key,
                    gate_override_value=value,
                )
            )
    return tuple(specs)


def _split_development(y: np.ndarray, random_state: int) -> tuple[np.ndarray, np.ndarray]:
    splitter = StratifiedShuffleSplit(
        n_splits=1,
        test_size=float(SYSTEM_B_CONFIG["development_split"]["fusion_fraction"]),
        random_state=int(random_state),
    )
    validation, fusion = next(splitter.split(np.zeros(len(y)), y))
    return np.asarray(validation, dtype=np.int64), np.asarray(fusion, dtype=np.int64)


def _selected_features(
    artifact: dict[str, Any],
    policy: str,
) -> list[str]:
    ranking = list(artifact["shap_ranking"])
    k = int(SYSTEM_B_CONFIG["shap"]["selected_features"])
    if policy == "primary":
        return list(artifact["selected_features"])
    if policy == "exclude_destination_port":
        out = [
            str(row["feature"])
            for row in ranking
            if str(row["feature"]) != "Destination Port"
        ][:k]
        if len(out) != k:
            raise ValueError("Insufficient SHAP-ranked features after Destination Port exclusion.")
        return out
    if policy == "global_mean_abs":
        ordered = sorted(
            enumerate(ranking),
            key=lambda item: (
                -float(item[1]["mean_abs_shap_global"]),
                int(item[0]),
            ),
        )
        return [str(row["feature"]) for _, row in ordered[:k]]
    if policy == "equal_class_normalized":
        benign = np.asarray(
            [float(row["mean_abs_shap_benign"]) for row in ranking],
            dtype=np.float64,
        )
        attack = np.asarray(
            [float(row["mean_abs_shap_attack"]) for row in ranking],
            dtype=np.float64,
        )
        b = benign / benign.max() if benign.max() > 0 else np.zeros_like(benign)
        a = attack / attack.max() if attack.max() > 0 else np.zeros_like(attack)
        score = 0.5 * b + 0.5 * a
        order = sorted(range(len(ranking)), key=lambda i: (-float(score[i]), i))
        return [str(ranking[i]["feature"]) for i in order[:k]]
    raise ValueError(f"Unknown selected-feature policy: {policy}")


def _gates(spec: VariantSpec) -> dict[str, Any]:
    gates = copy.deepcopy(SYSTEM_B_CONFIG["validation"])
    if spec.gate_override_key is not None:
        gates[spec.gate_override_key] = spec.gate_override_value
    return gates


def _candidate_rules(
    tree,
    *,
    seed: int,
    variant_id: str,
    X_validation: np.ndarray,
    y_validation: np.ndarray,
    validation_neural: np.ndarray,
    feature_names: Sequence[str],
    selected: Sequence[str],
    means: np.ndarray,
    scales: np.ndarray,
    gates: dict[str, Any],
    split_seed: int,
) -> tuple[list[Rule], list[dict[str, Any]], list[dict[str, object]]]:
    bootstrap = stratified_bootstrap_indices(
        y_validation,
        replicates=int(gates["bootstrap_replicates"]),
        random_state=int(gates["bootstrap_random_state_base"]) + seed + (split_seed - PRIMARY_SPLIT_SEED),
    )
    feature_index = {name: i for i, name in enumerate(feature_names)}
    eligible: list[Rule] = []
    masks: dict[str, np.ndarray] = {}
    candidate_log: list[dict[str, Any]] = []

    for leaf, raw_path in _tree_paths(tree, selected):
        canonical = canonicalize_conditions(raw_path, feature_order=feature_names)
        conditions = tuple(
            Condition(
                item.feature,
                item.operator,
                item.threshold,
                item.threshold * float(scales[feature_index[item.feature]])
                + float(means[feature_index[item.feature]]),
            )
            for item in canonical
        )
        consequent = weighted_leaf_consequent(tree, leaf)
        mask = activation_mask(
            X_validation,
            feature_names=feature_names,
            conditions=conditions,
        )
        quality = rule_quality(
            mask,
            y_true=y_validation,
            neural_decision=validation_neural,
            consequent=consequent,
        )
        stability = bootstrap_gate_stability(
            mask,
            y_true=y_validation,
            neural_decision=validation_neural,
            consequent=consequent,
            bootstrap_indices=bootstrap,
            min_support=float(gates["min_support"]),
            min_covered=int(gates["min_covered"]),
            min_precision=float(gates["min_class_precision"]),
            min_fidelity=float(gates["min_neural_fidelity"]),
        )
        reasons = []
        if float(quality["support"]) < float(gates["min_support"]):
            reasons.append("support")
        if int(quality["covered_count"]) < int(gates["min_covered"]):
            reasons.append("covered_count")
        if float(quality["class_precision"]) < float(gates["min_class_precision"]):
            reasons.append("class_precision")
        if float(quality["neural_fidelity"]) < float(gates["min_neural_fidelity"]):
            reasons.append("neural_fidelity")
        if float(stability) < float(gates["min_stability"]):
            reasons.append("stability")
        if len(conditions) > int(gates["max_complexity"]):
            reasons.append("complexity")
        accepted = not reasons
        candidate_name = f"s{seed}-leaf{leaf}"
        rule_id = rule_identifier(
            seed=seed,
            conditions=conditions,
            consequent=consequent,
        )
        candidate_log.append({
            "candidate": candidate_name,
            "rule_id": rule_id,
            "antecedent": [condition.to_dict() for condition in conditions],
            "consequent": int(consequent),
            **quality,
            "stability": float(stability),
            "complexity": len(conditions),
            "accepted_by_quality_gate": accepted,
            "reasons": reasons,
        })
        if accepted:
            rule = Rule(
                rule_id=rule_id,
                lineage_id=f"{variant_id}:{candidate_name}",
                rule_base_version=f"robustness:{variant_id}",
                seed=seed,
                conditions=conditions,
                consequent=consequent,
                confidence=min(
                    float(quality["class_precision"]),
                    float(quality["neural_fidelity"]),
                ),
                support=float(quality["support"]),
                covered_count=int(quality["covered_count"]),
                class_precision=float(quality["class_precision"]),
                neural_fidelity=float(quality["neural_fidelity"]),
                stability=float(stability),
                complexity=len(conditions),
                lifecycle_state="active",
                source_candidate_id=candidate_name,
                validation_evidence_id=f"development_split_{split_seed}",
            )
            eligible.append(rule)
            masks[rule.rule_id] = mask

    active, decisions = apply_redundancy_and_conflict_policy(
        eligible,
        masks,
        same_class_overlap=float(gates["same_class_redundancy_overlap"]),
        cross_class_overlap=float(gates["cross_class_conflict_overlap"]),
    )
    return active, candidate_log, decisions


def _surrogate_fidelity(tree, X: np.ndarray, target: np.ndarray, columns: Sequence[int]) -> float:
    return float(np.mean(tree.predict(X[:, columns]).astype(np.int8) == target))


def build_selection_robustness(*, device_name: str) -> None:
    device = _require_environment(device_name)
    if OUTPUT_DIR.exists():
        raise FileExistsError(f"Robustness selection artifacts already exist: {OUTPUT_DIR}")
    git = _git_state(require_clean=True)
    manifest_b = load_accepted_r0_v2_manifest()
    if manifest_b["manifest_sha256"] != ACCEPTED_SYSTEM_B_V2_MANIFEST_SHA256:
        raise ValueError("Wrong accepted R0.v2 identity.")
    frozen_a = _load_frozen_system_a_manifest()
    preprocessing = load_frozen_preprocessing()

    training = load_partition("training")
    development = load_partition("development")
    X_train = transform_frame(training.X, preprocessing, dtype=np.dtype("float32"))
    X_dev = transform_frame(development.X, preprocessing, dtype=np.dtype("float32"))
    y_train = training.y.to_numpy(dtype=np.int8, copy=True)
    y_dev = development.y.to_numpy(dtype=np.int8, copy=True)
    del training, development

    specs = _variant_specs()
    variant_state: dict[str, dict[str, Any]] = {
        spec.variant_id: {
            "spec": spec,
            "seed_payloads": {},
            "fusion_inputs": {},
        }
        for spec in specs
    }
    teacher_cache: dict[int, dict[str, Any]] = {}

    for seed in SYSTEM_B_CONFIG["seeds"]:
        source_entry = manifest_b["rule_artifacts"][str(seed)]
        source_artifact = json.loads(
            (PROJECT_ROOT / source_entry["path"]).read_text(encoding="utf-8")
        )
        record = _record_for_seed(frozen_a, seed)
        model = _load_checkpoint_model(
            record,
            device=device,
            preprocessing_hash=preprocessing.state_hash,
        )
        train_prob = predict_probabilities(
            model,
            X_train,
            device=device,
            batch_size=SYSTEM_A_CONFIG["batch_size"],
        )
        dev_prob = predict_probabilities(
            model,
            X_dev,
            device=device,
            batch_size=SYSTEM_A_CONFIG["batch_size"],
        )
        threshold_a = float(record["threshold"])
        train_neural = (train_prob >= threshold_a).astype(np.int8)
        dev_neural = (dev_prob >= threshold_a).astype(np.int8)
        teacher_cache[seed] = {
            "dev_prob": dev_prob,
            "train_neural": train_neural,
            "dev_neural": dev_neural,
        }

        tree_cache: dict[tuple[str, ...], Any] = {}
        for spec in specs:
            selected = _selected_features(source_artifact, spec.selected_feature_policy)
            key = tuple(selected)
            if key not in tree_cache:
                tree, _ = _fit_surrogate(
                    X_train,
                    train_neural,
                    feature_names=preprocessing.feature_columns,
                    selected=selected,
                    seed=seed,
                )
                tree_cache[key] = tree
            tree = tree_cache[key]
            validation_idx, fusion_idx = _split_development(
                y_dev, spec.development_split_seed
            )
            gates = _gates(spec)
            rules, candidate_log, policy_decisions = _candidate_rules(
                tree,
                seed=seed,
                variant_id=spec.variant_id,
                X_validation=X_dev[validation_idx],
                y_validation=y_dev[validation_idx],
                validation_neural=dev_neural[validation_idx],
                feature_names=preprocessing.feature_columns,
                selected=selected,
                means=preprocessing.means,
                scales=preprocessing.scales,
                gates=gates,
                split_seed=spec.development_split_seed,
            )
            if not rules:
                symbolic = infer_symbolic(
                    X_dev[fusion_idx],
                    feature_names=preprocessing.feature_columns,
                    rules=[],
                )
            else:
                symbolic = infer_symbolic(
                    X_dev[fusion_idx],
                    feature_names=preprocessing.feature_columns,
                    rules=rules,
                )
            lookup = {name: i for i, name in enumerate(preprocessing.feature_columns)}
            columns = [lookup[name] for name in selected]
            variant_state[spec.variant_id]["seed_payloads"][seed] = {
                "seed": seed,
                "selected_features": selected,
                "development_split_seed": spec.development_split_seed,
                "gates": gates,
                "surrogate_training_neural_fidelity": _surrogate_fidelity(
                    tree, X_train, train_neural, columns
                ),
                "candidate_log": candidate_log,
                "policy_decisions": policy_decisions,
                "rules": [rule.to_dict() for rule in rules],
                "active_candidate_ids": sorted(rule.source_candidate_id for rule in rules),
                "active_rule_ids": sorted(rule.rule_id for rule in rules),
                "source_r0_v2_active_rule_ids": sorted(
                    str(rule["rule_id"]) for rule in source_artifact["rules"]
                ),
            }
            variant_state[spec.variant_id]["fusion_inputs"][seed] = (
                y_dev[fusion_idx],
                dev_prob[fusion_idx],
                symbolic,
            )
        del model, train_prob

    OUTPUT_DIR.mkdir(parents=True, exist_ok=False)
    VARIANT_DIR.mkdir(parents=True, exist_ok=False)
    variant_inventory: dict[str, Any] = {}
    for spec in specs:
        state = variant_state[spec.variant_id]
        selected_weight, per_seed, grid = _select_global_fusion(state["fusion_inputs"])
        seed_inventory = {}
        variant_path = VARIANT_DIR / spec.variant_id
        variant_path.mkdir(parents=True, exist_ok=False)
        for seed in SYSTEM_B_CONFIG["seeds"]:
            payload = {
                "artifact_format_version": 1,
                "selection_id": SELECTION_ID,
                "variant_id": spec.variant_id,
                "family": spec.family,
                "source_system_b_v2_manifest_sha256": manifest_b["manifest_sha256"],
                **state["seed_payloads"][seed],
                "selected_neural_weight": float(selected_weight),
                "fused_threshold": float(per_seed[seed]["threshold"]),
            }
            payload["artifact_sha256"] = canonical_json_hash(payload)
            path = variant_path / f"seed_{seed}.json"
            _write_json_new(path, payload)
            seed_inventory[str(seed)] = {
                "path": path.relative_to(PROJECT_ROOT).as_posix(),
                "sha256": sha256_file(path),
                "artifact_sha256": payload["artifact_sha256"],
                "active_rule_count": len(payload["rules"]),
            }
        variant_inventory[spec.variant_id] = {
            "family": spec.family,
            "spec": {
                "development_split_seed": spec.development_split_seed,
                "selected_feature_policy": spec.selected_feature_policy,
                "gate_override_key": spec.gate_override_key,
                "gate_override_value": spec.gate_override_value,
            },
            "selected_neural_weight": float(selected_weight),
            "per_seed_thresholds": {
                str(seed): float(per_seed[seed]["threshold"])
                for seed in SYSTEM_B_CONFIG["seeds"]
            },
            "development_grid_records": grid,
            "seeds": seed_inventory,
        }

    manifest = {
        "manifest_format_version": 1,
        "selection_id": SELECTION_ID,
        "evidence_status": "posthoc_robustness_selection_not_model_selection",
        "source_system_b_v2_manifest_sha256": manifest_b["manifest_sha256"],
        "build_git": git,
        "data_access": {
            "training_used": True,
            "development_used": True,
            "pre_drift_used": False,
            "post_drift_used": False,
        },
        "variant_count": len(specs),
        "variant_inventory": variant_inventory,
        "interpretation_firewall": (
            "Variants are frozen from training/development only and may not replace "
            "R0.v2 based on later held-out performance. Held-out robustness evaluation "
            "is a separate write-once step after this manifest is committed."
        ),
    }
    manifest["manifest_sha256"] = canonical_json_hash(manifest)
    _write_json_new(MANIFEST_PATH, manifest)

    print(f"robustness_manifest={MANIFEST_PATH}")
    print(f"manifest_hash={manifest['manifest_sha256']}")
    print(f"variant_count={len(specs)}")
    print("pre_post_partitions_loaded=false")
    print("next_gate=commit_selection_robustness_before_held_out_rescore")


def verify_selection_robustness() -> None:
    if not MANIFEST_PATH.is_file():
        raise FileNotFoundError(f"Missing selection robustness manifest: {MANIFEST_PATH}")
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    stored = manifest.get("manifest_sha256")
    core = dict(manifest)
    core.pop("manifest_sha256", None)
    if canonical_json_hash(core) != stored:
        raise ValueError("Selection robustness manifest canonical hash mismatch.")
    if manifest.get("source_system_b_v2_manifest_sha256") != ACCEPTED_SYSTEM_B_V2_MANIFEST_SHA256:
        raise ValueError("Selection robustness references wrong R0.v2.")
    if manifest.get("data_access") != {
        "training_used": True,
        "development_used": True,
        "pre_drift_used": False,
        "post_drift_used": False,
    }:
        raise ValueError("Selection robustness data-access contract mismatch.")
    for variant, entry in manifest["variant_inventory"].items():
        for seed, seed_entry in entry["seeds"].items():
            path = PROJECT_ROOT / seed_entry["path"]
            if sha256_file(path) != seed_entry["sha256"]:
                raise ValueError(f"Robustness artifact hash mismatch: {variant}/seed {seed}")
            payload = json.loads(path.read_text(encoding="utf-8"))
            artifact_hash = payload.get("artifact_sha256")
            artifact_core = dict(payload)
            artifact_core.pop("artifact_sha256", None)
            if canonical_json_hash(artifact_core) != artifact_hash:
                raise ValueError(f"Robustness canonical artifact mismatch: {variant}/seed {seed}")
            if artifact_hash != seed_entry["artifact_sha256"]:
                raise ValueError(f"Robustness artifact identity mismatch: {variant}/seed {seed}")
    print(f"robustness_manifest={MANIFEST_PATH}")
    print(f"manifest_hash={stored}")
    print("pre_post_partitions_loaded=false")
    print("status=verified")
