from __future__ import annotations

import copy
import json
import time
from typing import Any, Sequence

import numpy as np

from concept_drift_ids.frozen_preprocessing import load_frozen_preprocessing, transform_frame
from concept_drift_ids.neural import predict_probabilities
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
    infer_symbolic,
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
from concept_drift_ids.system_b import (
    ACCEPTED_SYSTEM_B_MANIFEST_SHA256,
    GOVERNING_SOURCE_HASHES,
    LOCK_PATH,
    MANIFEST_PATH,
    SYSTEM_B_CONFIG,
    _development_split,
    _fit_surrogate,
    _git_state,
    _hash_int64,
    _load_manifest_b,
    _record_for_seed,
    _require_environment,
    _runtime,
    _select_global_fusion,
    _tree_paths,
    _write_json_new,
)


SYSTEM_B_V2_ID = "system_b_static_neuro_symbolic_v2_corrected"
RULE_BASE_V2 = "R0.v2"
V2_MANIFEST_PATH = PROJECT_ROOT / "data" / "manifests" / "system_b_v2.json"
V2_RULE_DIR = PROJECT_ROOT / "data" / "rules" / "system_b_r0_v2"
AUDIT_PATH = PROJECT_ROOT / "results" / "audits" / "system_b_r0_protocol_audit_v1.json"
AUDIT_FILE_SHA256 = "abfcb3af93531369427489fc27773f41e500a57279b0fa752b946c3985ebbf32"
ACCEPTED_SYSTEM_B_V2_MANIFEST_SHA256 = (
    "131027d2f136494eb388183f18dcb7eb0e9d7e9fe786f22dba25f4e1624c1483"
)
EXPECTED_AUDIT_SUMMARY = {
    "total_leaf_count": 62,
    "protocol_mismatch_count": 7,
    "active_r0_protocol_mismatch_count": 4,
    "path_rebuild_mismatch_count": 0,
    "stored_unweighted_semantics_mismatch_count": 0,
}

V2_CONFIG = copy.deepcopy(SYSTEM_B_CONFIG)
V2_CONFIG["rule_base_version"] = RULE_BASE_V2
V2_CONFIG["correction"] = {
    "source_rule_base_version": "R0.v1",
    "source_system_manifest_sha256": ACCEPTED_SYSTEM_B_MANIFEST_SHA256,
    "source_protocol_audit_file_sha256": AUDIT_FILE_SHA256,
    "consequent_semantics": "weighted_cart_leaf_argmax",
    "shap_recomputed": False,
    "selected_features_inherited_from_r0_v1": True,
    "held_out_evidence_used": False,
}


def weighted_leaf_consequent(tree, leaf: int) -> int:
    values = np.asarray(tree.tree_.value[int(leaf)], dtype=np.float64).reshape(-1)
    classes = np.asarray(tree.classes_)
    if values.size != classes.size:
        raise ValueError("Unexpected surrogate leaf-value shape.")
    return int(classes[int(np.argmax(values))])


def _load_audit() -> dict[str, Any]:
    if not AUDIT_PATH.is_file():
        raise FileNotFoundError(f"Missing frozen R0 protocol audit: {AUDIT_PATH}")
    if sha256_file(AUDIT_PATH) != AUDIT_FILE_SHA256:
        raise ValueError("Frozen R0 protocol audit file hash mismatch.")
    audit = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
    if audit.get("source_system_manifest_sha256") != ACCEPTED_SYSTEM_B_MANIFEST_SHA256:
        raise ValueError("R0 protocol audit references the wrong System-B v1 manifest.")
    if audit.get("summary") != EXPECTED_AUDIT_SUMMARY:
        raise ValueError("R0 protocol audit summary differs from the accepted diagnostic.")
    if audit.get("data_access") != {
        "training_used": True,
        "development_used": False,
        "pre_drift_used": False,
        "post_drift_used": False,
    }:
        raise ValueError("R0 protocol audit data-access contract mismatch.")
    return audit


def _load_v1_manifest() -> dict[str, Any]:
    # Reuse the accepted v1 verifier so the correction cannot be built from a
    # self-consistent manifest whose source rule artifacts/checkpoints differ.
    manifest = _load_manifest_b(require_checkpoints=True)
    if manifest["manifest_sha256"] != ACCEPTED_SYSTEM_B_MANIFEST_SHA256:
        raise ValueError("System-B v1 manifest is not the accepted source identity.")
    return manifest


def _load_correction_partitions():
    return load_partition("training"), load_partition("development")


def _antecedent_equal(stored: Sequence[dict[str, object]], corrected: Sequence[Condition]) -> bool:
    if len(stored) != len(corrected):
        return False
    for left, right in zip(stored, corrected):
        if left.get("feature") != right.feature or left.get("operator") != right.operator:
            return False
        if float(left["threshold"]) != float(right.threshold):
            return False
    return True


def _assert_unaffected_candidate_reproduced(
    source: dict[str, object],
    *,
    quality: dict[str, float | int],
    stability: float,
    complexity: int,
    accepted: bool,
) -> None:
    expected = {
        "support": float(source["support"]),
        "covered_count": int(source["covered_count"]),
        "class_precision": float(source["class_precision"]),
        "neural_fidelity": float(source["neural_fidelity"]),
        "stability": float(source["stability"]),
        "complexity": int(source["complexity"]),
        "accepted_by_quality_gate": bool(source["accepted_by_quality_gate"]),
    }
    observed = {
        "support": float(quality["support"]),
        "covered_count": int(quality["covered_count"]),
        "class_precision": float(quality["class_precision"]),
        "neural_fidelity": float(quality["neural_fidelity"]),
        "stability": float(stability),
        "complexity": int(complexity),
        "accepted_by_quality_gate": bool(accepted),
    }
    if observed != expected:
        raise ValueError(
            "An unaffected R0.v1 candidate did not reproduce exactly under the "
            "R0.v2 correction build."
        )


def _corrected_candidates(
    tree,
    *,
    seed: int,
    v1_artifact: dict[str, Any],
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
    v1_candidates = {
        str(row["candidate"]): row
        for row in v1_artifact["candidate_log"]
        if "candidate" in row and "rule_id" in row
    }
    eligible: list[Rule] = []
    masks: dict[str, np.ndarray] = {}
    log: list[dict[str, object]] = []
    started = time.perf_counter()

    for leaf, path in _tree_paths(tree, selected):
        candidate_name = f"s{seed}-leaf{leaf}"
        if candidate_name not in v1_candidates:
            raise ValueError(f"V1 candidate log missing reconstructed {candidate_name}.")
        source = v1_candidates[candidate_name]
        canonical = canonicalize_conditions(path, feature_order=feature_names)
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
        if not _antecedent_equal(source["antecedent"], conditions):
            raise ValueError(f"V2 correction changed the frozen path for {candidate_name}.")

        consequent = weighted_leaf_consequent(tree, leaf)
        corrected_rule_id = rule_identifier(
            seed=seed, conditions=conditions, consequent=consequent
        )
        mask = activation_mask(
            X_validation, feature_names=feature_names, conditions=conditions
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
            min_support=config["min_support"],
            min_covered=config["min_covered"],
            min_precision=config["min_class_precision"],
            min_fidelity=config["min_neural_fidelity"],
        )
        reasons: list[str] = []
        if quality["support"] < config["min_support"]:
            reasons.append("support")
        if quality["covered_count"] < config["min_covered"]:
            reasons.append("covered_count")
        if quality["class_precision"] < config["min_class_precision"]:
            reasons.append("class_precision")
        if quality["neural_fidelity"] < config["min_neural_fidelity"]:
            reasons.append("neural_fidelity")
        if stability < config["min_stability"]:
            reasons.append("stability")
        if len(conditions) > config["max_complexity"]:
            reasons.append("complexity")
        accepted = not reasons
        changed = int(source["consequent"]) != consequent
        if not changed:
            _assert_unaffected_candidate_reproduced(
                source,
                quality=quality,
                stability=stability,
                complexity=len(conditions),
                accepted=accepted,
            )
        log.append({
            "candidate": candidate_name,
            "source_v1_rule_id": source["rule_id"],
            "rule_id": corrected_rule_id,
            "antecedent": [condition.to_dict() for condition in conditions],
            "source_v1_consequent": int(source["consequent"]),
            "consequent": consequent,
            "consequent_changed_by_protocol_correction": changed,
            **quality,
            "stability": stability,
            "complexity": len(conditions),
            "accepted_by_quality_gate": accepted,
            "reasons": reasons,
        })
        if accepted:
            rule = Rule(
                rule_id=corrected_rule_id,
                lineage_id=str(source["rule_id"]),
                rule_base_version=RULE_BASE_V2,
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


def build_and_freeze_r0_v2(*, device_name: str) -> None:
    device = _require_environment(device_name)
    if V2_MANIFEST_PATH.exists() or V2_RULE_DIR.exists():
        raise FileExistsError("R0.v2 correction artifacts already exist; refusing overwrite.")
    git = _git_state(require_clean=True)
    audit = _load_audit()
    v1_manifest = _load_v1_manifest()
    frozen_a = _load_frozen_system_a_manifest()
    preprocessing = load_frozen_preprocessing()
    scenario = load_manifest()

    training, development = _load_correction_partitions()
    X_train = transform_frame(training.X, preprocessing, dtype=np.dtype("float32"))
    y_train = training.y.to_numpy(dtype=np.int8, copy=True)
    train_rows = training.provenance["scenario_row"].to_numpy(dtype=np.int64)
    X_dev = transform_frame(development.X, preprocessing, dtype=np.dtype("float32"))
    y_dev = development.y.to_numpy(dtype=np.int8, copy=True)
    dev_rows = development.provenance["scenario_row"].to_numpy(dtype=np.int64)
    del training, development

    validation_idx, fusion_idx = _development_split(y_dev)
    if _hash_int64(train_rows) != v1_manifest["row_identities"]["training_scenario_rows_sha256"]:
        raise ValueError("R0.v2 training rows differ from R0.v1.")
    if _hash_int64(dev_rows[validation_idx]) != v1_manifest["row_identities"]["development_validation_rows_sha256"]:
        raise ValueError("R0.v2 validation rows differ from R0.v1.")
    if _hash_int64(dev_rows[fusion_idx]) != v1_manifest["row_identities"]["development_fusion_rows_sha256"]:
        raise ValueError("R0.v2 fusion rows differ from R0.v1.")
    validation_id = _hash_int64(dev_rows[validation_idx])

    audit_mismatch_by_seed = {
        int(record["seed"]): {
            str(row["candidate"])
            for row in record["comparisons"]
            if bool(row["protocol_mismatch"])
        }
        for record in audit["seed_records"]
    }
    audit_active_mismatch_ids = {
        str(row["rule_id"])
        for record in audit["seed_records"]
        for row in record["comparisons"]
        if bool(row["protocol_mismatch"]) and bool(row["active_in_r0"])
    }

    generated: dict[int, dict[str, Any]] = {}
    fusion_inputs = {}

    for seed in SYSTEM_B_CONFIG["seeds"]:
        v1_entry = v1_manifest["rule_artifacts"][str(seed)]
        v1_artifact = json.loads(
            (PROJECT_ROOT / v1_entry["path"]).read_text(encoding="utf-8")
        )
        selected = list(v1_artifact["selected_features"])
        record = _record_for_seed(frozen_a, seed)
        model = _load_checkpoint_model(
            record, device=device, preprocessing_hash=preprocessing.state_hash
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
            X_train,
            train_neural,
            feature_names=preprocessing.feature_columns,
            selected=selected,
            seed=seed,
        )
        rules, candidate_log, validation_seconds = _corrected_candidates(
            tree,
            seed=seed,
            v1_artifact=v1_artifact,
            X_validation=X_dev[validation_idx],
            y_validation=y_dev[validation_idx],
            validation_neural=dev_neural[validation_idx],
            feature_names=preprocessing.feature_columns,
            selected=selected,
            means=preprocessing.means,
            scales=preprocessing.scales,
            validation_evidence_id=validation_id,
        )

        changed_candidates = {
            str(row["candidate"])
            for row in candidate_log
            if row.get("consequent_changed_by_protocol_correction") is True
        }
        if changed_candidates != audit_mismatch_by_seed[seed]:
            raise ValueError(
                f"Seed {seed} correction mismatch set differs from the frozen audit."
            )

        source_active_ids = {str(row["rule_id"]) for row in v1_artifact["rules"]}
        expected_active_ids = source_active_ids - audit_active_mismatch_ids
        actual_active_ids = {rule.rule_id for rule in rules}
        if actual_active_ids != expected_active_ids:
            raise ValueError(
                f"Seed {seed} R0.v2 changed active rules beyond the audited defect."
            )

        symbolic = infer_symbolic(
            X_dev[fusion_idx],
            feature_names=preprocessing.feature_columns,
            rules=rules,
        )
        fusion_inputs[seed] = (y_dev[fusion_idx], dev_prob[fusion_idx], symbolic)
        generated[seed] = {
            "seed": seed,
            "system_a_checkpoint_file": record["checkpoint_file"],
            "system_a_checkpoint_sha256": record["checkpoint_sha256"],
            "system_a_threshold": threshold_a,
            "selected_features": selected,
            "selected_features_source": "R0.v1 frozen SHAP selection",
            "shap_ranking": v1_artifact["shap_ranking"],
            "source_v1_rule_artifact_sha256": v1_entry["artifact_sha256"],
            "candidate_log": candidate_log,
            "rules": [rule.to_dict() for rule in rules],
            "timing_seconds": {
                "surrogate_fit": tree_seconds,
                "candidate_validation": validation_seconds,
            },
        }
        del model, train_prob, dev_prob, train_neural, dev_neural

    selected_weight, selected_seed_results, fusion_rows = _select_global_fusion(
        fusion_inputs
    )

    V2_RULE_DIR.mkdir(parents=True, exist_ok=False)
    rule_inventory = {}
    for seed in SYSTEM_B_CONFIG["seeds"]:
        path = V2_RULE_DIR / f"seed_{seed}.json"
        payload = {
            "artifact_format_version": 1,
            "system_id": SYSTEM_B_V2_ID,
            "rule_base_version": RULE_BASE_V2,
            "source_system_b_v1_manifest_sha256": ACCEPTED_SYSTEM_B_MANIFEST_SHA256,
            "source_protocol_audit_sha256": AUDIT_FILE_SHA256,
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
        "system_id": SYSTEM_B_V2_ID,
        "rule_base_version": RULE_BASE_V2,
        "correction_status": "protocol_conformance_correction_after_r0_v1_evaluation",
        "source_system_b_v1_manifest_sha256": ACCEPTED_SYSTEM_B_MANIFEST_SHA256,
        "source_protocol_audit_path": AUDIT_PATH.relative_to(PROJECT_ROOT).as_posix(),
        "source_protocol_audit_file_sha256": AUDIT_FILE_SHA256,
        "scenario_id": scenario["scenario_id"],
        "scenario_version": scenario["scenario_version"],
        "preprocessing_state_hash": preprocessing.state_hash,
        "system_a_manifest_sha256": frozen_a["manifest_sha256"],
        "system_a_manifest_file_sha256": sha256_file(SYSTEM_A_MANIFEST_PATH),
        "requirements_lock_sha256": sha256_file(LOCK_PATH),
        "governing_source_hashes": GOVERNING_SOURCE_HASHES,
        "config": V2_CONFIG,
        "config_sha256": canonical_json_hash(V2_CONFIG),
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
            "shap_background_training_rows_sha256": v1_manifest["row_identities"][
                "shap_background_training_rows_sha256"
            ],
            "shap_attribution_training_rows_sha256": v1_manifest["row_identities"][
                "shap_attribution_training_rows_sha256"
            ],
        },
        "correction_contract": {
            "shap_recomputed": False,
            "selected_features_reused_exactly": True,
            "surrogate_reconstructed_with_original_constraints": True,
            "candidate_paths_must_match_r0_v1": True,
            "candidate_consequent": "weighted_cart_leaf_argmax",
            "validation_gates_unchanged": True,
            "fusion_grid_and_tie_breaks_unchanged": True,
            "unexpected_active_rule_change_forbidden": True,
            "unaffected_candidate_validation_must_reproduce_exactly": True,
            "held_out_evidence_used": False,
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
    _write_json_new(V2_MANIFEST_PATH, manifest)

    print(f"system_b_v2_manifest={V2_MANIFEST_PATH}")
    print(f"manifest_hash={manifest['manifest_sha256']}")
    print(f"selected_neural_weight={selected_weight:.2f}")
    for seed in SYSTEM_B_CONFIG["seeds"]:
        print(
            f"seed={seed} active_rules={rule_inventory[str(seed)]['active_rule_count']} "
            f"threshold={manifest['fusion']['per_seed_thresholds'][str(seed)]:.12g}"
        )
    print("shap_recomputed=false")
    print("pre_post_partitions_loaded=false")
    print("next_gate=commit_r0_v2_before_corrected_evaluation")


def load_accepted_r0_v2_manifest() -> dict[str, Any]:
    if not V2_MANIFEST_PATH.is_file():
        raise FileNotFoundError("R0.v2 is not frozen locally; run build-r0-v2 first.")
    _load_audit()
    v1_manifest = _load_v1_manifest()
    manifest = json.loads(V2_MANIFEST_PATH.read_text(encoding="utf-8"))
    stored = manifest.get("manifest_sha256")
    core = dict(manifest)
    core.pop("manifest_sha256", None)
    if canonical_json_hash(core) != stored:
        raise ValueError("R0.v2 manifest canonical hash mismatch.")
    if stored != ACCEPTED_SYSTEM_B_V2_MANIFEST_SHA256:
        raise ValueError("R0.v2 manifest is not the accepted frozen correction identity.")
    if manifest["source_system_b_v1_manifest_sha256"] != v1_manifest["manifest_sha256"]:
        raise ValueError("R0.v2 references the wrong R0.v1 source.")
    if manifest["source_protocol_audit_file_sha256"] != AUDIT_FILE_SHA256:
        raise ValueError("R0.v2 references the wrong protocol audit.")
    if manifest["config_sha256"] != canonical_json_hash(V2_CONFIG):
        raise ValueError("R0.v2 config hash mismatch.")
    if manifest["data_access"] != {
        "training_used": True,
        "development_used": True,
        "pre_drift_used": False,
        "post_drift_used": False,
    }:
        raise ValueError("R0.v2 data-access firewall mismatch.")

    expected_counts = {0: 7, 1: 6, 2: 7, 3: 6, 4: 6}
    for seed in SYSTEM_B_CONFIG["seeds"]:
        entry = manifest["rule_artifacts"][str(seed)]
        path = PROJECT_ROOT / entry["path"]
        if sha256_file(path) != entry["sha256"]:
            raise ValueError(f"R0.v2 raw rule artifact hash mismatch for seed {seed}.")
        payload = json.loads(path.read_text(encoding="utf-8"))
        artifact_hash = payload.get("artifact_sha256")
        artifact_core = dict(payload)
        artifact_core.pop("artifact_sha256", None)
        if canonical_json_hash(artifact_core) != artifact_hash:
            raise ValueError(
                f"R0.v2 canonical rule artifact hash mismatch for seed {seed}."
            )
        if artifact_hash != entry["artifact_sha256"]:
            raise ValueError(f"R0.v2 rule artifact identity mismatch for seed {seed}.")
        if len(payload["rules"]) != expected_counts[seed]:
            raise ValueError(f"Unexpected R0.v2 active rule count for seed {seed}.")
    return manifest


def verify_r0_v2() -> None:
    manifest = load_accepted_r0_v2_manifest()
    stored = manifest["manifest_sha256"]
    print(f"system_b_v2_manifest={V2_MANIFEST_PATH}")
    print(f"manifest_hash={stored}")
    print("pre_post_partitions_loaded=false")
    print("status=verified")
