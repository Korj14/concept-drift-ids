from __future__ import annotations

import json
from typing import Any

import numpy as np
import torch

from concept_drift_ids.frozen_preprocessing import load_frozen_preprocessing, transform_frame
from concept_drift_ids.neural import predict_probabilities, select_mcc_threshold
from concept_drift_ids.scenario_loader import PROJECT_ROOT, load_partition
from concept_drift_ids.scenario_manifest import sha256_file
from concept_drift_ids.symbolic import canonical_json_hash, fuse_scores, infer_symbolic
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
    _rule_from_dict,
    _write_csv_new,
    _write_json_new,
)
from concept_drift_ids.system_b_r0_v2 import (
    ACCEPTED_SYSTEM_B_V2_MANIFEST_SHA256,
    load_accepted_r0_v2_manifest,
)


SELECTION_ID = "system_b_fusion_authority_v1"
OUTPUT_DIR = PROJECT_ROOT / "data" / "robustness" / SELECTION_ID
MANIFEST_PATH = OUTPUT_DIR / "manifest.json"
ROWS_PATH = OUTPUT_DIR / "development_thresholds.csv"
SENSITIVITY_WEIGHTS = (0.70, 0.90, 1.00)


def _load_development_only():
    return load_partition("development")


def _load_rules(manifest: dict[str, Any], seed: int):
    entry = manifest["rule_artifacts"][str(seed)]
    payload = json.loads((PROJECT_ROOT / entry["path"]).read_text(encoding="utf-8"))
    return [_rule_from_dict(row) for row in payload["rules"]]


def build_fusion_authority_selection(*, device_name: str) -> None:
    if device_name != "cpu":
        raise ValueError("Fusion-authority sensitivity is frozen to CPU.")
    if OUTPUT_DIR.exists():
        raise FileExistsError(f"Fusion-authority selection already exists: {OUTPUT_DIR}")

    git = _git_state(require_clean=True)
    manifest_b = load_accepted_r0_v2_manifest()
    if manifest_b["manifest_sha256"] != ACCEPTED_SYSTEM_B_V2_MANIFEST_SHA256:
        raise ValueError("Fusion sensitivity is not using accepted R0.v2.")
    frozen_a = _load_frozen_system_a_manifest()
    preprocessing = load_frozen_preprocessing()
    development = _load_development_only()
    X_dev = transform_frame(
        development.X,
        preprocessing,
        dtype=np.dtype("float32"),
    )
    y_dev = development.y.to_numpy(dtype=np.int8, copy=True)
    _, fusion_idx = _development_split(y_dev)
    fusion_rows = development.provenance["scenario_row"].to_numpy(dtype=np.int64)[
        fusion_idx
    ]
    del development

    rows: list[dict[str, object]] = []
    thresholds: dict[str, dict[str, float]] = {
        f"{weight:.2f}": {} for weight in SENSITIVITY_WEIGHTS
    }

    for seed in SYSTEM_B_CONFIG["seeds"]:
        record = _record_for_seed(frozen_a, seed)
        model = _load_checkpoint_model(
            record,
            device=torch.device("cpu"),
            preprocessing_hash=preprocessing.state_hash,
        )
        neural_prob = predict_probabilities(
            model,
            X_dev,
            device=torch.device("cpu"),
            batch_size=int(SYSTEM_A_CONFIG["batch_size"]),
        )
        rules = _load_rules(manifest_b, seed)
        symbolic = infer_symbolic(
            X_dev[fusion_idx],
            feature_names=preprocessing.feature_columns,
            rules=rules,
        )
        y = y_dev[fusion_idx]
        neural = neural_prob[fusion_idx]

        for weight in SENSITIVITY_WEIGHTS:
            fused = fuse_scores(neural, symbolic, neural_weight=float(weight))
            threshold, metrics = select_mcc_threshold(y, fused)
            key = f"{weight:.2f}"
            thresholds[key][str(seed)] = float(threshold)
            rows.append({
                "neural_weight": float(weight),
                "seed": int(seed),
                "threshold": float(threshold),
                **metrics,
            })
        del model, neural_prob

    summary = {
        "manifest_format_version": 1,
        "selection_id": SELECTION_ID,
        "evidence_status": "posthoc_fusion_authority_sensitivity_not_model_selection",
        "source_system_b_v2_manifest_sha256": manifest_b["manifest_sha256"],
        "build_git": git,
        "data_access": {
            "training_used": False,
            "development_used": True,
            "pre_drift_used": False,
            "post_drift_used": False,
        },
        "source_rule_state": "accepted_R0.v2_reused_without_rebuild",
        "source_primary_neural_weight": float(
            manifest_b["fusion"]["selected_neural_weight"]
        ),
        "sensitivity_neural_weights": list(SENSITIVITY_WEIGHTS),
        "threshold_selection": {
            "partition": "original_R0.v2_development_fusion_slice",
            "objective": "MCC",
            "tie_break": ["F1", "lower_FPR", "closest_to_0.5"],
        },
        "development_fusion_rows_sha256": manifest_b["row_identities"][
            "development_fusion_rows_sha256"
        ],
        "per_weight_seed_thresholds": thresholds,
        "interpretation_firewall": (
            "These weights are prespecified authority sensitivities. Held-out outcomes "
            "cannot select a replacement lambda or alter accepted R0.v2."
        ),
    }
    from concept_drift_ids.system_b import _hash_int64
    if _hash_int64(fusion_rows) != summary["development_fusion_rows_sha256"]:
        raise ValueError("Fusion-authority sensitivity reconstructed the wrong development slice.")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=False)
    _write_csv_new(ROWS_PATH, rows)
    manifest = {
        **summary,
        "files": {
            "development_thresholds": {
                "path": ROWS_PATH.relative_to(PROJECT_ROOT).as_posix(),
                "sha256": sha256_file(ROWS_PATH),
            }
        },
    }
    manifest["manifest_sha256"] = canonical_json_hash(manifest)
    _write_json_new(MANIFEST_PATH, manifest)
    print(f"fusion_authority_manifest={MANIFEST_PATH}")
    print(f"manifest_hash={manifest['manifest_sha256']}")
    print("rules_rebuilt=false")
    print("training_loaded=false")
    print("pre_post_partitions_loaded=false")
    print("next_gate=commit_fusion_authority_selection_before_held_out_rescore")


def verify_fusion_authority_selection() -> None:
    if not MANIFEST_PATH.is_file():
        raise FileNotFoundError(f"Missing fusion-authority manifest: {MANIFEST_PATH}")
    source = load_accepted_r0_v2_manifest()
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    stored = manifest.get("manifest_sha256")
    core = dict(manifest)
    core.pop("manifest_sha256", None)
    if canonical_json_hash(core) != stored:
        raise ValueError("Fusion-authority manifest canonical hash mismatch.")
    if manifest.get("source_system_b_v2_manifest_sha256") != source["manifest_sha256"]:
        raise ValueError("Fusion-authority sensitivity references wrong R0.v2.")
    if manifest.get("data_access") != {
        "training_used": False,
        "development_used": True,
        "pre_drift_used": False,
        "post_drift_used": False,
    }:
        raise ValueError("Fusion-authority data-access contract mismatch.")
    if tuple(float(x) for x in manifest["sensitivity_neural_weights"]) != SENSITIVITY_WEIGHTS:
        raise ValueError("Fusion-authority weight set mismatch.")
    for name, entry in manifest["files"].items():
        path = PROJECT_ROOT / entry["path"]
        if not path.is_file() or sha256_file(path) != entry["sha256"]:
            raise ValueError(f"Fusion-authority artifact mismatch: {name}")
    print(f"fusion_authority_manifest={MANIFEST_PATH}")
    print(f"manifest_hash={stored}")
    print("pre_post_partitions_loaded=false")
    print("status=verified")
