from __future__ import annotations

import json
from typing import Any, Sequence

import numpy as np

from concept_drift_ids.frozen_preprocessing import (
    load_frozen_preprocessing,
    transform_frame,
)
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
    _development_split,
    _fit_surrogate,
    _git_state,
    _record_for_seed,
    _require_environment,
    _tree_paths,
    _write_json_new,
)
from concept_drift_ids.system_b_r0_v2 import (
    ACCEPTED_SYSTEM_B_V2_MANIFEST_SHA256,
    load_accepted_r0_v2_manifest,
    weighted_leaf_consequent,
)


AUDIT_ID = "system_b_r0_v2_dtype_conformance_v1"
AUDIT_PATH = PROJECT_ROOT / "results" / "audits" / (
    "system_b_r0_v2_dtype_conformance_v1.json"
)


def _load_train_dev_only():
    return load_partition("training"), load_partition("development")


def _candidate_signature(path: Sequence[tuple[str, str, float]]) -> tuple[tuple[str, str], ...]:
    return tuple((str(feature), str(operator)) for feature, operator, _ in path)


def _quality_pass(
    quality: dict[str, float | int],
    *,
    stability: float,
    complexity: int,
) -> bool:
    config = SYSTEM_B_CONFIG["validation"]
    return bool(
        float(quality["support"]) >= float(config["min_support"])
        and int(quality["covered_count"]) >= int(config["min_covered"])
        and float(quality["class_precision"]) >= float(config["min_class_precision"])
        and float(quality["neural_fidelity"]) >= float(config["min_neural_fidelity"])
        and float(stability) >= float(config["min_stability"])
        and int(complexity) <= int(config["max_complexity"])
    )


def _candidate_records(
    tree,
    *,
    seed: int,
    X_validation: np.ndarray,
    y_validation: np.ndarray,
    validation_neural: np.ndarray,
    feature_names: Sequence[str],
    selected: Sequence[str],
    means: np.ndarray,
    scales: np.ndarray,
    validation_evidence_id: str,
) -> tuple[list[dict[str, Any]], list[Rule]]:
    config = SYSTEM_B_CONFIG["validation"]
    bootstrap = stratified_bootstrap_indices(
        y_validation,
        replicates=int(config["bootstrap_replicates"]),
        random_state=int(config["bootstrap_random_state_base"]) + seed,
    )
    feature_index = {name: i for i, name in enumerate(feature_names)}
    records: list[dict[str, Any]] = []
    eligible: list[Rule] = []
    masks: dict[str, np.ndarray] = {}

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
            min_support=float(config["min_support"]),
            min_covered=int(config["min_covered"]),
            min_precision=float(config["min_class_precision"]),
            min_fidelity=float(config["min_neural_fidelity"]),
        )
        accepted = _quality_pass(
            quality,
            stability=stability,
            complexity=len(conditions),
        )
        candidate = f"s{seed}-leaf{leaf}"
        record = {
            "candidate": candidate,
            "leaf": int(leaf),
            "path_signature": [list(item) for item in _candidate_signature(raw_path)],
            "antecedent": [condition.to_dict() for condition in conditions],
            "consequent": int(consequent),
            **quality,
            "stability": float(stability),
            "complexity": len(conditions),
            "accepted_by_quality_gate": accepted,
        }
        records.append(record)

        if accepted:
            rule_id = rule_identifier(
                seed=seed,
                conditions=conditions,
                consequent=consequent,
            )
            rule = Rule(
                rule_id=rule_id,
                lineage_id=candidate,
                rule_base_version="R0.v2-dtype-audit",
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
                source_candidate_id=candidate,
                validation_evidence_id=validation_evidence_id,
            )
            eligible.append(rule)
            masks[rule.rule_id] = mask

    active, _ = apply_redundancy_and_conflict_policy(
        eligible,
        masks,
        same_class_overlap=float(config["same_class_redundancy_overlap"]),
        cross_class_overlap=float(config["cross_class_conflict_overlap"]),
    )
    return records, active


def _tree_discrete_topology(tree, selected: Sequence[str]) -> list[dict[str, Any]]:
    structure = tree.tree_
    rows = []
    for node in range(int(structure.node_count)):
        left = int(structure.children_left[node])
        right = int(structure.children_right[node])
        is_leaf = left == right
        rows.append(
            {
                "node": node,
                "is_leaf": is_leaf,
                "left": left,
                "right": right,
                "feature": None if is_leaf else selected[int(structure.feature[node])],
            }
        )
    return rows


def _candidate_map(records: Sequence[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(row["candidate"]): dict(row) for row in records}


def audit_dtype_conformance(*, device_name: str) -> None:
    device = _require_environment(device_name)
    if AUDIT_PATH.exists():
        raise FileExistsError(f"Audit artifact already exists; refusing overwrite: {AUDIT_PATH}")

    git = _git_state(require_clean=True)
    manifest = load_accepted_r0_v2_manifest()
    if manifest["manifest_sha256"] != ACCEPTED_SYSTEM_B_V2_MANIFEST_SHA256:
        raise ValueError("Wrong accepted R0.v2 identity.")
    frozen_a = _load_frozen_system_a_manifest()
    preprocessing = load_frozen_preprocessing()

    training, development = _load_train_dev_only()
    X_train_64 = transform_frame(
        training.X,
        preprocessing,
        dtype=np.dtype("float64"),
    )
    X_dev_64 = transform_frame(
        development.X,
        preprocessing,
        dtype=np.dtype("float64"),
    )
    X_train_32 = X_train_64.astype(np.float32)
    X_dev_32 = X_dev_64.astype(np.float32)
    y_train = training.y.to_numpy(dtype=np.int8, copy=True)
    y_dev = development.y.to_numpy(dtype=np.int8, copy=True)
    dev_rows = development.provenance["scenario_row"].to_numpy(dtype=np.int64)
    del training, development

    validation_idx, _ = _development_split(y_dev)
    validation_evidence_id = __import__("hashlib").sha256(
        np.asarray(dev_rows[validation_idx], dtype="<i8").tobytes(order="C")
    ).hexdigest()

    seed_records: list[dict[str, Any]] = []
    totals = {
        "seed_count": 0,
        "topology_mismatch_seed_count": 0,
        "training_leaf_assignment_mismatch_rows": 0,
        "validation_leaf_assignment_mismatch_rows": 0,
        "candidate_path_signature_mismatch_count": 0,
        "consequent_mismatch_count": 0,
        "quality_gate_mismatch_count": 0,
        "active_candidate_set_mismatch_seed_count": 0,
    }

    for seed in SYSTEM_B_CONFIG["seeds"]:
        artifact_entry = manifest["rule_artifacts"][str(seed)]
        artifact = json.loads(
            (PROJECT_ROOT / artifact_entry["path"]).read_text(encoding="utf-8")
        )
        selected = list(artifact["selected_features"])
        lookup = {name: i for i, name in enumerate(preprocessing.feature_columns)}
        selected_columns = [lookup[name] for name in selected]

        record = _record_for_seed(frozen_a, seed)
        model = _load_checkpoint_model(
            record,
            device=device,
            preprocessing_hash=preprocessing.state_hash,
        )
        train_prob = predict_probabilities(
            model,
            X_train_32,
            device=device,
            batch_size=SYSTEM_A_CONFIG["batch_size"],
        )
        dev_prob = predict_probabilities(
            model,
            X_dev_32,
            device=device,
            batch_size=SYSTEM_A_CONFIG["batch_size"],
        )
        threshold = float(record["threshold"])
        train_neural = (train_prob >= threshold).astype(np.int8)
        dev_neural = (dev_prob >= threshold).astype(np.int8)

        tree32, _ = _fit_surrogate(
            X_train_32,
            train_neural,
            feature_names=preprocessing.feature_columns,
            selected=selected,
            seed=seed,
        )
        tree64, _ = _fit_surrogate(
            X_train_64,
            train_neural,
            feature_names=preprocessing.feature_columns,
            selected=selected,
            seed=seed,
        )

        topology32 = _tree_discrete_topology(tree32, selected)
        topology64 = _tree_discrete_topology(tree64, selected)
        topology_mismatch = topology32 != topology64

        train_leaf32 = tree32.apply(X_train_32[:, selected_columns])
        train_leaf64 = tree64.apply(X_train_64[:, selected_columns])
        val_leaf32 = tree32.apply(X_dev_32[validation_idx][:, selected_columns])
        val_leaf64 = tree64.apply(X_dev_64[validation_idx][:, selected_columns])
        train_assignment_mismatch = int(np.sum(train_leaf32 != train_leaf64))
        val_assignment_mismatch = int(np.sum(val_leaf32 != val_leaf64))

        records32, active32 = _candidate_records(
            tree32,
            seed=seed,
            X_validation=X_dev_32[validation_idx],
            y_validation=y_dev[validation_idx],
            validation_neural=dev_neural[validation_idx],
            feature_names=preprocessing.feature_columns,
            selected=selected,
            means=preprocessing.means,
            scales=preprocessing.scales,
            validation_evidence_id=validation_evidence_id,
        )
        records64, active64 = _candidate_records(
            tree64,
            seed=seed,
            X_validation=X_dev_64[validation_idx],
            y_validation=y_dev[validation_idx],
            validation_neural=dev_neural[validation_idx],
            feature_names=preprocessing.feature_columns,
            selected=selected,
            means=preprocessing.means,
            scales=preprocessing.scales,
            validation_evidence_id=validation_evidence_id,
        )
        map32 = _candidate_map(records32)
        map64 = _candidate_map(records64)
        names = sorted(set(map32) | set(map64))

        path_mismatch = 0
        consequent_mismatch = 0
        gate_mismatch = 0
        threshold_deltas: list[float] = []
        raw_threshold_deltas: list[float] = []
        candidate_comparisons = []
        for name in names:
            left = map32.get(name)
            right = map64.get(name)
            if left is None or right is None:
                path_mismatch += 1
                candidate_comparisons.append(
                    {"candidate": name, "present_float32": left is not None, "present_float64": right is not None}
                )
                continue
            sig_mismatch = left["path_signature"] != right["path_signature"]
            path_mismatch += int(sig_mismatch)
            cons_mismatch = int(left["consequent"]) != int(right["consequent"])
            consequent_mismatch += int(cons_mismatch)
            gate_changed = bool(left["accepted_by_quality_gate"]) != bool(
                right["accepted_by_quality_gate"]
            )
            gate_mismatch += int(gate_changed)

            left_ant = left["antecedent"]
            right_ant = right["antecedent"]
            if len(left_ant) == len(right_ant):
                for la, ra in zip(left_ant, right_ant):
                    if la["feature"] == ra["feature"] and la["operator"] == ra["operator"]:
                        threshold_deltas.append(abs(float(la["threshold"]) - float(ra["threshold"])))
                        raw_threshold_deltas.append(
                            abs(float(la["raw_threshold"]) - float(ra["raw_threshold"]))
                        )
            candidate_comparisons.append(
                {
                    "candidate": name,
                    "path_signature_mismatch": sig_mismatch,
                    "consequent_float32": int(left["consequent"]),
                    "consequent_float64": int(right["consequent"]),
                    "consequent_mismatch": cons_mismatch,
                    "accepted_float32": bool(left["accepted_by_quality_gate"]),
                    "accepted_float64": bool(right["accepted_by_quality_gate"]),
                    "gate_mismatch": gate_changed,
                    "covered_count_float32": int(left["covered_count"]),
                    "covered_count_float64": int(right["covered_count"]),
                    "class_precision_float32": float(left["class_precision"]),
                    "class_precision_float64": float(right["class_precision"]),
                    "neural_fidelity_float32": float(left["neural_fidelity"]),
                    "neural_fidelity_float64": float(right["neural_fidelity"]),
                    "stability_float32": float(left["stability"]),
                    "stability_float64": float(right["stability"]),
                }
            )

        active_candidates32 = sorted(rule.source_candidate_id for rule in active32)
        active_candidates64 = sorted(rule.source_candidate_id for rule in active64)
        active_set_mismatch = active_candidates32 != active_candidates64

        seed_record = {
            "seed": seed,
            "selected_features": selected,
            "topology_mismatch": topology_mismatch,
            "training_leaf_assignment_mismatch_rows": train_assignment_mismatch,
            "validation_leaf_assignment_mismatch_rows": val_assignment_mismatch,
            "candidate_path_signature_mismatch_count": path_mismatch,
            "consequent_mismatch_count": consequent_mismatch,
            "quality_gate_mismatch_count": gate_mismatch,
            "active_candidates_float32": active_candidates32,
            "active_candidates_float64": active_candidates64,
            "active_candidate_set_mismatch": active_set_mismatch,
            "max_standardized_threshold_abs_delta": max(threshold_deltas, default=0.0),
            "max_raw_threshold_abs_delta": max(raw_threshold_deltas, default=0.0),
            "candidate_comparisons": candidate_comparisons,
        }
        seed_records.append(seed_record)
        totals["seed_count"] += 1
        totals["topology_mismatch_seed_count"] += int(topology_mismatch)
        totals["training_leaf_assignment_mismatch_rows"] += train_assignment_mismatch
        totals["validation_leaf_assignment_mismatch_rows"] += val_assignment_mismatch
        totals["candidate_path_signature_mismatch_count"] += path_mismatch
        totals["consequent_mismatch_count"] += consequent_mismatch
        totals["quality_gate_mismatch_count"] += gate_mismatch
        totals["active_candidate_set_mismatch_seed_count"] += int(active_set_mismatch)
        del model, train_prob, dev_prob

    discrete_keys = (
        "topology_mismatch_seed_count",
        "training_leaf_assignment_mismatch_rows",
        "validation_leaf_assignment_mismatch_rows",
        "candidate_path_signature_mismatch_count",
        "consequent_mismatch_count",
        "quality_gate_mismatch_count",
        "active_candidate_set_mismatch_seed_count",
    )
    realized_effect = any(int(totals[key]) != 0 for key in discrete_keys)
    decision = (
        "versioned_correction_required_before_c_d"
        if realized_effect
        else "numerically_inert_no_r0_version_change"
    )

    payload = {
        "audit_format_version": 1,
        "audit_id": AUDIT_ID,
        "source_system_b_v2_manifest_sha256": manifest["manifest_sha256"],
        "audit_git": git,
        "data_access": {
            "training_used": True,
            "development_used": True,
            "pre_drift_used": False,
            "post_drift_used": False,
        },
        "comparison": {
            "frozen_stage3a_shared_output_dtype": "float64",
            "realized_system_b_surrogate_input_dtype": "float32",
            "neural_teacher_input_dtype": "float32_in_both_arms",
            "selected_features": "accepted_r0_v2_features_reused_exactly",
            "shap_recomputed": False,
            "decision_rule": (
                "A versioned correction is required only if float64 changes discrete "
                "surrogate topology/row assignment, weighted leaf consequent, validation "
                "gate outcome, or final active candidate set. Threshold roundoff alone "
                "does not trigger replacement of accepted R0.v2."
            ),
        },
        "summary": totals,
        "realized_scientific_effect": realized_effect,
        "decision": decision,
        "seed_records": seed_records,
    }
    payload["artifact_sha256"] = canonical_json_hash(payload)
    _write_json_new(AUDIT_PATH, payload)
    print(f"audit_artifact={AUDIT_PATH}")
    print(f"artifact_hash={payload['artifact_sha256']}")
    for key in discrete_keys:
        print(f"{key}={totals[key]}")
    print(f"realized_scientific_effect={str(realized_effect).lower()}")
    print(f"decision={decision}")
    print("pre_post_partitions_loaded=false")


def verify_dtype_conformance_audit() -> None:
    if not AUDIT_PATH.is_file():
        raise FileNotFoundError(f"Missing dtype conformance audit: {AUDIT_PATH}")
    payload = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
    stored = payload.get("artifact_sha256")
    core = dict(payload)
    core.pop("artifact_sha256", None)
    if canonical_json_hash(core) != stored:
        raise ValueError("Dtype conformance audit canonical hash mismatch.")
    if payload.get("source_system_b_v2_manifest_sha256") != ACCEPTED_SYSTEM_B_V2_MANIFEST_SHA256:
        raise ValueError("Dtype audit references the wrong R0.v2 identity.")
    if payload.get("data_access") != {
        "training_used": True,
        "development_used": True,
        "pre_drift_used": False,
        "post_drift_used": False,
    }:
        raise ValueError("Dtype conformance audit data-access contract mismatch.")
    print(f"audit_artifact={AUDIT_PATH}")
    print(f"artifact_file_sha256={sha256_file(AUDIT_PATH)}")
    print(f"artifact_hash={stored}")
    print(f"decision={payload['decision']}")
    print("pre_post_partitions_loaded=false")
    print("status=verified")
