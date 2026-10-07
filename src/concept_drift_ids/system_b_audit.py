from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Sequence

import numpy as np
from sklearn.tree import DecisionTreeClassifier

from concept_drift_ids.frozen_preprocessing import load_frozen_preprocessing, transform_frame
from concept_drift_ids.neural import predict_probabilities
from concept_drift_ids.scenario_loader import PROJECT_ROOT, load_partition
from concept_drift_ids.system_a import SYSTEM_A_CONFIG, _load_checkpoint_model, _load_frozen_system_a_manifest
from concept_drift_ids.system_b import (
    ACCEPTED_SYSTEM_B_MANIFEST_SHA256,
    MANIFEST_PATH,
    SYSTEM_B_CONFIG,
    _balanced_indices,
    _fit_surrogate,
    _git_state,
    _hash_int64,
    _record_for_seed,
    _runtime,
    _tree_paths,
    _write_json_new,
)
from concept_drift_ids.symbolic import canonicalize_conditions


AUDIT_ID = "system_b_r0_protocol_audit_v1"
AUDIT_DIR = PROJECT_ROOT / "results" / "audits"
AUDIT_PATH = AUDIT_DIR / f"{AUDIT_ID}.json"


def weighted_leaf_consequent(tree: DecisionTreeClassifier, leaf: int) -> int:
    values = np.asarray(tree.tree_.value[int(leaf)], dtype=np.float64).reshape(-1)
    if values.size != len(tree.classes_):
        raise ValueError("Unexpected surrogate leaf-value shape.")
    return int(np.asarray(tree.classes_)[int(np.argmax(values))])


def _antecedent_matches(
    stored: Sequence[dict[str, object]],
    rebuilt: Sequence[tuple[str, str, float]],
) -> bool:
    if len(stored) != len(rebuilt):
        return False
    for item, (feature, operator, threshold) in zip(stored, rebuilt):
        if item.get("feature") != feature or item.get("operator") != operator:
            return False
        if not np.isclose(
            float(item["threshold"]),
            float(threshold),
            rtol=0.0,
            atol=0.0,
        ):
            return False
    return True


def audit_frozen_r0_protocol() -> None:
    if AUDIT_PATH.exists():
        raise FileExistsError(f"Audit artifact already exists; refusing overwrite: {AUDIT_PATH}")

    git = _git_state(require_clean=True)
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    if manifest.get("manifest_sha256") != ACCEPTED_SYSTEM_B_MANIFEST_SHA256:
        raise ValueError("System-B manifest is not the accepted R0.v1 identity.")

    preprocessing = load_frozen_preprocessing()
    frozen_a = _load_frozen_system_a_manifest()

    # Intentionally training-only. Development/pre/post are not required to determine
    # the fitted CART leaf class and therefore are forbidden in this diagnostic.
    training = load_partition("training")
    X_train = transform_frame(training.X, preprocessing, dtype=np.dtype("float32"))
    y_train = training.y.to_numpy(dtype=np.int8, copy=True)
    training_rows = training.provenance["scenario_row"].to_numpy(dtype=np.int64)
    del training

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
    expected_rows = manifest["row_identities"]
    sampling = {
        "background_hash_matches_manifest": (
            _hash_int64(training_rows[background_idx])
            == expected_rows["shap_background_training_rows_sha256"]
        ),
        "attribution_hash_matches_manifest": (
            _hash_int64(training_rows[attribution_idx])
            == expected_rows["shap_attribution_training_rows_sha256"]
        ),
        "background_attribution_overlap_count": int(
            len(np.intersect1d(background_idx, attribution_idx))
        ),
        "background_count": int(len(background_idx)),
        "attribution_count": int(len(attribution_idx)),
    }

    seed_records: list[dict[str, object]] = []
    total_mismatches = 0
    active_mismatches = 0
    path_mismatches = 0
    stored_semantics_mismatches = 0

    for seed in SYSTEM_B_CONFIG["seeds"]:
        system_a_record = _record_for_seed(frozen_a, seed)
        rule_entry = manifest["rule_artifacts"][str(seed)]
        rule_artifact = json.loads(
            (PROJECT_ROOT / rule_entry["path"]).read_text(encoding="utf-8")
        )
        selected = list(rule_artifact["selected_features"])

        model = _load_checkpoint_model(
            system_a_record,
            device=np_to_torch_cpu(),
            preprocessing_hash=preprocessing.state_hash,
        )
        probabilities = predict_probabilities(
            model,
            X_train,
            device=np_to_torch_cpu(),
            batch_size=SYSTEM_A_CONFIG["batch_size"],
        )
        threshold = float(system_a_record["threshold"])
        neural_decision = (probabilities >= threshold).astype(np.int8)

        tree, _ = _fit_surrogate(
            X_train,
            neural_decision,
            feature_names=preprocessing.feature_columns,
            selected=selected,
            seed=seed,
        )

        candidate_by_name = {
            str(row["candidate"]): row
            for row in rule_artifact["candidate_log"]
            if "candidate" in row and "rule_id" in row
        }
        active_ids = {str(row["rule_id"]) for row in rule_artifact["rules"]}
        lookup = {name: i for i, name in enumerate(preprocessing.feature_columns)}

        comparisons: list[dict[str, object]] = []
        for leaf, path in _tree_paths(tree, selected):
            name = f"s{seed}-leaf{leaf}"
            if name not in candidate_by_name:
                raise ValueError(f"Frozen candidate log is missing rebuilt leaf {name}.")
            stored = candidate_by_name[name]
            canonical = canonicalize_conditions(
                path, feature_order=preprocessing.feature_columns
            )
            rebuilt_antecedent = [
                (condition.feature, condition.operator, float(condition.threshold))
                for condition in canonical
            ]
            stored_antecedent = list(stored.get("antecedent", []))
            path_match = _antecedent_matches(stored_antecedent, rebuilt_antecedent)
            path_mismatches += int(not path_match)

            weighted = weighted_leaf_consequent(tree, leaf)

            train_mask = np.ones(len(X_train), dtype=bool)
            for feature, operator, value in rebuilt_antecedent:
                column = X_train[:, lookup[feature]]
                if operator == "<=":
                    train_mask &= column <= value
                else:
                    train_mask &= column > value
            if not np.any(train_mask):
                raise ValueError(f"Rebuilt surrogate leaf {name} has zero training coverage.")
            unweighted = int(
                np.argmax(np.bincount(neural_decision[train_mask], minlength=2))
            )
            stored_consequent = int(stored["consequent"])
            if stored_consequent != unweighted:
                stored_semantics_mismatches += 1

            mismatch = stored_consequent != weighted
            total_mismatches += int(mismatch)
            is_active = str(stored["rule_id"]) in active_ids
            active_mismatches += int(mismatch and is_active)

            values = np.asarray(tree.tree_.value[int(leaf)], dtype=np.float64).reshape(-1)
            comparisons.append(
                {
                    "candidate": name,
                    "rule_id": stored["rule_id"],
                    "quality_gate_accepted": bool(stored["accepted_by_quality_gate"]),
                    "active_in_r0": is_active,
                    "path_matches_frozen_candidate": path_match,
                    "stored_consequent": stored_consequent,
                    "rebuilt_unweighted_majority_consequent": unweighted,
                    "protocol_weighted_leaf_consequent": weighted,
                    "protocol_mismatch": mismatch,
                    "weighted_leaf_class_mass": {
                        str(int(tree.classes_[i])): float(values[i])
                        for i in range(len(values))
                    },
                    "training_covered_count": int(train_mask.sum()),
                }
            )

        seed_records.append(
            {
                "seed": seed,
                "checkpoint_sha256": system_a_record["checkpoint_sha256"],
                "selected_features": selected,
                "rebuilt_leaf_count": len(comparisons),
                "frozen_candidate_count": len(candidate_by_name),
                "protocol_mismatch_count": int(
                    sum(bool(row["protocol_mismatch"]) for row in comparisons)
                ),
                "active_protocol_mismatch_count": int(
                    sum(
                        bool(row["protocol_mismatch"]) and bool(row["active_in_r0"])
                        for row in comparisons
                    )
                ),
                "comparisons": comparisons,
            }
        )
        del model, probabilities, neural_decision

    payload: dict[str, Any] = {
        "audit_format_version": 1,
        "audit_id": AUDIT_ID,
        "purpose": (
            "Post-evaluation protocol-conformance diagnostic. It tests whether the "
            "frozen R0 candidate consequents equal the class predicted by the weighted "
            "CART leaf required by the prospectively frozen System-B protocol."
        ),
        "source_system_manifest_sha256": manifest["manifest_sha256"],
        "audit_git": git,
        "runtime": _runtime(),
        "data_access": {
            "training_used": True,
            "development_used": False,
            "pre_drift_used": False,
            "post_drift_used": False,
        },
        "sampling_reconstruction": sampling,
        "summary": {
            "total_leaf_count": int(sum(row["rebuilt_leaf_count"] for row in seed_records)),
            "protocol_mismatch_count": int(total_mismatches),
            "active_r0_protocol_mismatch_count": int(active_mismatches),
            "path_rebuild_mismatch_count": int(path_mismatches),
            "stored_unweighted_semantics_mismatch_count": int(
                stored_semantics_mismatches
            ),
        },
        "seed_records": seed_records,
        "interpretation_gate": (
            "If protocol_mismatch_count is zero, the code/protocol discrepancy had "
            "zero realized effect on the frozen candidate consequents. If nonzero, "
            "do not silently replace R0.v1: preserve all evidence and assess a "
            "versioned implementation-defect correction before C/D."
        ),
    }
    _write_json_new(AUDIT_PATH, payload)

    print(f"audit_artifact={AUDIT_PATH}")
    for key, value in payload["summary"].items():
        print(f"{key}={value}")
    print("development_loaded=false")
    print("pre_post_partitions_loaded=false")
    print("status=protocol_diagnostic_written")


def np_to_torch_cpu():
    # Local import keeps the audit's dependency surface explicit and avoids a
    # module-level side effect in repository-only tests.
    import torch
    return torch.device("cpu")
