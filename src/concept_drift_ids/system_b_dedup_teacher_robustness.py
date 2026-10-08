from __future__ import annotations

import copy
import json
from typing import Any

import numpy as np
import torch

from concept_drift_ids.frozen_preprocessing import load_frozen_preprocessing, transform_frame
from concept_drift_ids.neural import predict_probabilities
from concept_drift_ids.scenario_loader import PROJECT_ROOT, load_partition
from concept_drift_ids.scenario_manifest import sha256_file
from concept_drift_ids.symbolic import canonical_json_hash, infer_symbolic
from concept_drift_ids.system_a import SYSTEM_A_CONFIG, _load_checkpoint_model
from concept_drift_ids.system_a_duplicate_robustness import (
    MANIFEST_PATH as TEACHER_MANIFEST_PATH,
    _deduplicated_training_indices,
    verify_pattern_dedup_teacher,
)
from concept_drift_ids.system_b import (
    SYSTEM_B_CONFIG,
    _balanced_indices,
    _development_split,
    _fit_surrogate,
    _git_state,
    _hash_int64,
    _select_global_fusion,
    _select_shap_features,
    _write_json_new,
)
from concept_drift_ids.system_b_selection_robustness import _candidate_rules


ROBUSTNESS_ID = "system_b_pattern_dedup_teacher_r0_v1"
OUTPUT_DIR = PROJECT_ROOT / "data" / "robustness" / ROBUSTNESS_ID
MANIFEST_PATH = OUTPUT_DIR / "manifest.json"
RULE_DIR = OUTPUT_DIR / "rules"


def _load_train_dev_only():
    return load_partition("training"), load_partition("development")


def _teacher_record(manifest: dict[str, Any], seed: int) -> dict[str, Any]:
    rows = [row for row in manifest["seed_records"] if int(row["seed"]) == seed]
    if len(rows) != 1:
        raise ValueError(f"Expected one alternate-teacher record for seed {seed}.")
    return rows[0]


def build_pattern_dedup_teacher_r0(*, device_name: str) -> None:
    if device_name != "cpu":
        raise ValueError("Pattern-dedup teacher R0 sensitivity is frozen to CPU.")
    if OUTPUT_DIR.exists():
        raise FileExistsError(f"Alternate-teacher R0 robustness already exists: {OUTPUT_DIR}")

    git = _git_state(require_clean=True)
    verify_pattern_dedup_teacher()
    teacher_manifest = json.loads(TEACHER_MANIFEST_PATH.read_text(encoding="utf-8"))
    preprocessing = load_frozen_preprocessing()

    training, development = _load_train_dev_only()
    y_train_full = training.y.to_numpy(dtype=np.int8, copy=True)
    keep = _deduplicated_training_indices(training.X, y_train_full)
    retained_rows = training.provenance["scenario_row"].to_numpy(dtype=np.int64)[keep]
    if _hash_int64(retained_rows) != teacher_manifest["retained_training_scenario_rows_sha256"]:
        raise ValueError("Alternate R0 reconstructed the wrong deduplicated training rows.")

    X_train = transform_frame(
        training.X.iloc[keep],
        preprocessing,
        dtype=np.dtype("float32"),
    )
    y_train = y_train_full[keep]
    X_dev = transform_frame(
        development.X,
        preprocessing,
        dtype=np.dtype("float32"),
    )
    y_dev = development.y.to_numpy(dtype=np.int8, copy=True)
    dev_rows = development.provenance["scenario_row"].to_numpy(dtype=np.int64)
    if _hash_int64(dev_rows) != teacher_manifest["development_scenario_rows_sha256"]:
        raise ValueError("Alternate R0 reconstructed the wrong development rows.")
    del training, development

    validation_idx, fusion_idx = _development_split(y_dev)
    background_idx = _balanced_indices(
        y_train,
        per_class=int(SYSTEM_B_CONFIG["shap"]["background_per_class"]),
        random_state=int(SYSTEM_B_CONFIG["shap"]["sample_random_state"]),
    )
    attribution_idx = _balanced_indices(
        y_train,
        per_class=int(SYSTEM_B_CONFIG["shap"]["attribution_per_class"]),
        random_state=int(SYSTEM_B_CONFIG["shap"]["sample_random_state"]),
    )
    gates = copy.deepcopy(SYSTEM_B_CONFIG["validation"])
    seed_payloads: dict[int, dict[str, Any]] = {}
    fusion_inputs: dict[int, tuple[np.ndarray, np.ndarray, dict[str, np.ndarray]]] = {}

    for seed in SYSTEM_B_CONFIG["seeds"]:
        record = _teacher_record(teacher_manifest, seed)
        model = _load_checkpoint_model(
            record,
            device=torch.device("cpu"),
            preprocessing_hash=preprocessing.state_hash,
        )
        train_prob = predict_probabilities(
            model,
            X_train,
            device=torch.device("cpu"),
            batch_size=int(SYSTEM_A_CONFIG["batch_size"]),
        )
        dev_prob = predict_probabilities(
            model,
            X_dev,
            device=torch.device("cpu"),
            batch_size=int(SYSTEM_A_CONFIG["batch_size"]),
        )
        threshold_a = float(record["threshold"])
        train_neural = (train_prob >= threshold_a).astype(np.int8)
        dev_neural = (dev_prob >= threshold_a).astype(np.int8)

        selected, ranking, _ = _select_shap_features(
            model,
            X_train,
            y_train,
            feature_names=preprocessing.feature_columns,
            background_idx=background_idx,
            attribution_idx=attribution_idx,
        )
        tree, _ = _fit_surrogate(
            X_train,
            train_neural,
            feature_names=preprocessing.feature_columns,
            selected=selected,
            seed=seed,
        )
        rules, candidate_log, policy_decisions = _candidate_rules(
            tree,
            seed=seed,
            variant_id=ROBUSTNESS_ID,
            X_validation=X_dev[validation_idx],
            y_validation=y_dev[validation_idx],
            validation_neural=dev_neural[validation_idx],
            feature_names=preprocessing.feature_columns,
            selected=selected,
            means=preprocessing.means,
            scales=preprocessing.scales,
            gates=gates,
            split_seed=int(SYSTEM_B_CONFIG["development_split"]["random_state"]),
        )
        symbolic = infer_symbolic(
            X_dev[fusion_idx],
            feature_names=preprocessing.feature_columns,
            rules=rules,
        )
        fusion_inputs[seed] = (y_dev[fusion_idx], dev_prob[fusion_idx], symbolic)
        seed_payloads[seed] = {
            "seed": int(seed),
            "alternate_teacher_checkpoint_file": record["checkpoint_file"],
            "alternate_teacher_checkpoint_sha256": record["checkpoint_sha256"],
            "alternate_teacher_threshold": threshold_a,
            "selected_features": selected,
            "shap_ranking": ranking,
            "candidate_log": candidate_log,
            "policy_decisions": policy_decisions,
            "rules": [rule.to_dict() for rule in rules],
            "active_candidate_ids": sorted(rule.source_candidate_id for rule in rules),
        }
        del model, train_prob, dev_prob, train_neural, dev_neural

    selected_weight, per_seed, grid = _select_global_fusion(fusion_inputs)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=False)
    RULE_DIR.mkdir(parents=True, exist_ok=False)
    inventory: dict[str, Any] = {}
    for seed in SYSTEM_B_CONFIG["seeds"]:
        payload = {
            "artifact_format_version": 1,
            "robustness_id": ROBUSTNESS_ID,
            "source_alternate_teacher_manifest_sha256": teacher_manifest["manifest_sha256"],
            **seed_payloads[seed],
            "selected_neural_weight": float(selected_weight),
            "fused_threshold": float(per_seed[seed]["threshold"]),
        }
        payload["artifact_sha256"] = canonical_json_hash(payload)
        path = RULE_DIR / f"seed_{seed}.json"
        _write_json_new(path, payload)
        inventory[str(seed)] = {
            "path": path.relative_to(PROJECT_ROOT).as_posix(),
            "sha256": sha256_file(path),
            "artifact_sha256": payload["artifact_sha256"],
            "active_rule_count": len(payload["rules"]),
        }

    manifest = {
        "manifest_format_version": 1,
        "robustness_id": ROBUSTNESS_ID,
        "evidence_status": "posthoc_training_duplicate_chain_sensitivity_not_replacement",
        "source_alternate_teacher_manifest_sha256": teacher_manifest["manifest_sha256"],
        "preprocessing_state_hash": preprocessing.state_hash,
        "build_git": git,
        "data_access": {
            "training_used": True,
            "development_used": True,
            "pre_drift_used": False,
            "post_drift_used": False,
        },
        "deduplication_policy": teacher_manifest["deduplication_policy"],
        "preprocessing_refit": False,
        "retained_training_scenario_rows_sha256": teacher_manifest[
            "retained_training_scenario_rows_sha256"
        ],
        "development_scenario_rows_sha256": teacher_manifest[
            "development_scenario_rows_sha256"
        ],
        "system_b_protocol": {
            "weighted_cart_leaf_consequent": True,
            "development_split_reused": True,
            "validation_gates_reused": True,
            "shap_sample_sizes_and_seed_reused": True,
        },
        "fusion": {
            "selected_neural_weight": float(selected_weight),
            "per_seed_thresholds": {
                str(seed): float(per_seed[seed]["threshold"])
                for seed in SYSTEM_B_CONFIG["seeds"]
            },
            "development_grid_records": grid,
        },
        "rule_artifacts": inventory,
        "interpretation_firewall": (
            "This alternate A-to-R0 chain isolates dependence on training multiplicity "
            "while keeping the accepted primary preprocessing fixed. It cannot replace "
            "accepted System A, R0.v2 or corrected B based on held-out outcomes."
        ),
    }
    manifest["manifest_sha256"] = canonical_json_hash(manifest)
    _write_json_new(MANIFEST_PATH, manifest)
    print(f"alternate_teacher_r0_manifest={MANIFEST_PATH}")
    print(f"manifest_hash={manifest['manifest_sha256']}")
    print(f"selected_neural_weight={selected_weight:.2f}")
    print("pre_post_partitions_loaded=false")
    print("next_gate=commit_alternate_teacher_r0_before_held_out_rescore")


def verify_pattern_dedup_teacher_r0() -> None:
    if not MANIFEST_PATH.is_file():
        raise FileNotFoundError(f"Missing alternate-teacher R0 manifest: {MANIFEST_PATH}")
    verify_pattern_dedup_teacher()
    teacher = json.loads(TEACHER_MANIFEST_PATH.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    stored = manifest.get("manifest_sha256")
    core = dict(manifest)
    core.pop("manifest_sha256", None)
    if canonical_json_hash(core) != stored:
        raise ValueError("Alternate-teacher R0 manifest canonical hash mismatch.")
    if manifest["source_alternate_teacher_manifest_sha256"] != teacher["manifest_sha256"]:
        raise ValueError("Alternate-teacher R0 references wrong teacher manifest.")
    if manifest["data_access"] != {
        "training_used": True,
        "development_used": True,
        "pre_drift_used": False,
        "post_drift_used": False,
    }:
        raise ValueError("Alternate-teacher R0 data-access contract mismatch.")
    for seed, entry in manifest["rule_artifacts"].items():
        path = PROJECT_ROOT / entry["path"]
        if not path.is_file() or sha256_file(path) != entry["sha256"]:
            raise ValueError(f"Alternate-teacher R0 artifact mismatch for seed {seed}.")
        payload = json.loads(path.read_text(encoding="utf-8"))
        artifact_hash = payload.get("artifact_sha256")
        artifact_core = dict(payload)
        artifact_core.pop("artifact_sha256", None)
        if canonical_json_hash(artifact_core) != artifact_hash:
            raise ValueError(f"Alternate-teacher R0 canonical artifact mismatch for seed {seed}.")
    print(f"alternate_teacher_r0_manifest={MANIFEST_PATH}")
    print(f"manifest_hash={stored}")
    print("pre_post_partitions_loaded=false")
    print("status=verified")
