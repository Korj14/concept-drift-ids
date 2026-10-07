from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import torch
from sklearn.metrics import average_precision_score
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

from concept_drift_ids.frozen_preprocessing import load_frozen_preprocessing, transform_frame
from concept_drift_ids.neural import (
    predict_probabilities,
    select_mcc_threshold,
    set_reproducible_seed,
)
from concept_drift_ids.scenario_loader import PROJECT_ROOT, load_partition
from concept_drift_ids.scenario_manifest import sha256_file
from concept_drift_ids.system_a import (
    SYSTEM_A_CONFIG,
    SYSTEM_A_MANIFEST_PATH,
    _json_hash,
    _new_model,
)
from concept_drift_ids.system_b import _git_state, _hash_int64, _write_json_new
from concept_drift_ids.system_b_duplicate_robustness import _exact_pattern_group_ids


ROBUSTNESS_ID = "system_a_pattern_dedup_training_v1"
ARTIFACT_DIR = PROJECT_ROOT / "artifacts" / "robustness" / ROBUSTNESS_ID
CHECKPOINT_DIR = ARTIFACT_DIR / "checkpoints"
MANIFEST_PATH = PROJECT_ROOT / "data" / "robustness" / ROBUSTNESS_ID / "manifest.json"


def _deduplicated_training_indices(raw_X, y: np.ndarray) -> np.ndarray:
    groups = _exact_pattern_group_ids(raw_X)
    y = np.asarray(y, dtype=np.int8)
    if len(groups) != len(y):
        raise ValueError("Feature groups and labels differ in length.")
    seen: set[tuple[int, int]] = set()
    keep: list[int] = []
    for index, (group, label) in enumerate(zip(groups, y, strict=True)):
        key = (int(group), int(label))
        if key not in seen:
            seen.add(key)
            keep.append(index)
    return np.asarray(keep, dtype=np.int64)


def _train_seed(
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_dev: np.ndarray,
    y_dev: np.ndarray,
    *,
    seed: int,
    preprocessing_hash: str,
) -> dict[str, Any]:
    set_reproducible_seed(seed)
    device = torch.device("cpu")
    model = _new_model().to(device)
    benign = int(np.sum(y_train == 0))
    attack = int(np.sum(y_train == 1))
    if benign == 0 or attack == 0:
        raise ValueError("Deduplicated training must retain both classes.")
    pos_weight_value = benign / attack

    criterion = nn.BCEWithLogitsLoss(
        pos_weight=torch.tensor(pos_weight_value, dtype=torch.float32, device=device)
    )
    optimizer = torch.optim.Adam(
        model.parameters(),
        lr=float(SYSTEM_A_CONFIG["learning_rate"]),
        weight_decay=float(SYSTEM_A_CONFIG["weight_decay"]),
    )
    generator = torch.Generator().manual_seed(seed)
    loader = DataLoader(
        TensorDataset(torch.from_numpy(X_train), torch.from_numpy(y_train)),
        batch_size=int(SYSTEM_A_CONFIG["batch_size"]),
        shuffle=True,
        num_workers=int(SYSTEM_A_CONFIG["num_workers"]),
        generator=generator,
        drop_last=False,
    )

    best_ap = -math.inf
    best_epoch = -1
    best_state: dict[str, torch.Tensor] | None = None
    stale_epochs = 0
    history: list[dict[str, float | int]] = []
    patience = int(SYSTEM_A_CONFIG["early_stopping_patience"])
    min_delta = float(SYSTEM_A_CONFIG["early_stopping_min_delta"])

    for epoch in range(1, int(SYSTEM_A_CONFIG["max_epochs"]) + 1):
        model.train()
        total_loss = 0.0
        seen_rows = 0
        for batch_X, batch_y in loader:
            batch_X = batch_X.to(device)
            batch_y = batch_y.to(device)
            optimizer.zero_grad(set_to_none=True)
            loss = criterion(model(batch_X), batch_y)
            loss.backward()
            optimizer.step()
            count = len(batch_X)
            total_loss += float(loss.detach().cpu()) * count
            seen_rows += count

        dev_prob = predict_probabilities(
            model,
            X_dev,
            device=device,
            batch_size=int(SYSTEM_A_CONFIG["batch_size"]),
        )
        dev_ap = float(average_precision_score(y_dev, dev_prob))
        history.append({
            "epoch": epoch,
            "training_loss": total_loss / seen_rows,
            "development_average_precision": dev_ap,
        })
        if dev_ap > best_ap + min_delta:
            best_ap = dev_ap
            best_epoch = epoch
            best_state = {
                key: value.detach().cpu().clone()
                for key, value in model.state_dict().items()
            }
            stale_epochs = 0
        else:
            stale_epochs += 1
            if stale_epochs >= patience:
                break

    if best_state is None:
        raise RuntimeError("Alternate teacher training produced no checkpoint.")
    model.load_state_dict(best_state)
    dev_prob = predict_probabilities(
        model,
        X_dev,
        device=device,
        batch_size=int(SYSTEM_A_CONFIG["batch_size"]),
    )
    threshold, metrics = select_mcc_threshold(y_dev, dev_prob)

    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    checkpoint_path = CHECKPOINT_DIR / f"seed_{seed}.pt"
    if checkpoint_path.exists():
        raise FileExistsError(f"Refusing overwrite: {checkpoint_path}")
    torch.save({
        "robustness_id": ROBUSTNESS_ID,
        "source_system_a_config_sha256": _json_hash(SYSTEM_A_CONFIG),
        "seed": seed,
        "preprocessing_state_hash": preprocessing_hash,
        "best_epoch": best_epoch,
        "threshold": threshold,
        "model_state_dict": best_state,
    }, checkpoint_path)

    return {
        "seed": seed,
        "best_epoch": best_epoch,
        "threshold": float(threshold),
        "development_metrics": metrics,
        "positive_class_weight": float(pos_weight_value),
        "epochs_ran": len(history),
        "history": history,
        "checkpoint_file": checkpoint_path.relative_to(PROJECT_ROOT).as_posix(),
        "checkpoint_sha256": sha256_file(checkpoint_path),
        "device": "cpu",
        "torch_version": str(torch.__version__),
    }


def build_pattern_dedup_teacher() -> None:
    if MANIFEST_PATH.exists() or ARTIFACT_DIR.exists():
        raise FileExistsError(
            "Pattern-deduplicated System-A robustness artifacts already exist."
        )
    git = _git_state(require_clean=True)
    preprocessing = load_frozen_preprocessing()
    primary_a = json.loads(SYSTEM_A_MANIFEST_PATH.read_text(encoding="utf-8"))

    training = load_partition("training")
    development = load_partition("development")
    y_train_full = training.y.to_numpy(dtype=np.int8, copy=True)
    keep = _deduplicated_training_indices(training.X, y_train_full)
    y_train = y_train_full[keep].astype(np.float32)
    X_train = transform_frame(
        training.X.iloc[keep],
        preprocessing,
        dtype=np.dtype("float32"),
    )
    retained_rows = training.provenance["scenario_row"].to_numpy(dtype=np.int64)[keep]
    X_dev = transform_frame(
        development.X,
        preprocessing,
        dtype=np.dtype("float32"),
    )
    y_dev = development.y.to_numpy(dtype=np.float32, copy=True)
    dev_rows = development.provenance["scenario_row"].to_numpy(dtype=np.int64)
    del training, development

    records = [
        _train_seed(
            X_train,
            y_train,
            X_dev,
            y_dev,
            seed=seed,
            preprocessing_hash=preprocessing.state_hash,
        )
        for seed in SYSTEM_A_CONFIG["seeds"]
    ]
    manifest = {
        "manifest_format_version": 1,
        "robustness_id": ROBUSTNESS_ID,
        "evidence_status": "posthoc_training_duplicate_sensitivity_not_replacement",
        "source_system_a_manifest_sha256": primary_a["manifest_sha256"],
        "source_system_a_config_sha256": _json_hash(SYSTEM_A_CONFIG),
        "preprocessing_state_hash": preprocessing.state_hash,
        "build_git": git,
        "data_access": {
            "training_used": True,
            "development_used": True,
            "pre_drift_used": False,
            "post_drift_used": False,
        },
        "deduplication_policy": {
            "unit": "exact_raw_77_feature_pattern_plus_binary_label",
            "keep": "first_occurrence_in_frozen_training_order",
            "binary_label_conflicts_preserved": True,
            "majority_relabeling": False,
            "preprocessing_refit": False,
        },
        "training_rows_original": int(len(y_train_full)),
        "training_rows_retained": int(len(keep)),
        "training_rows_removed": int(len(y_train_full) - len(keep)),
        "original_class_counts": {
            "benign": int(np.sum(y_train_full == 0)),
            "attack": int(np.sum(y_train_full == 1)),
        },
        "retained_class_counts": {
            "benign": int(np.sum(y_train == 0)),
            "attack": int(np.sum(y_train == 1)),
        },
        "retained_training_scenario_rows_sha256": _hash_int64(retained_rows),
        "development_scenario_rows_sha256": _hash_int64(dev_rows),
        "training_protocol": SYSTEM_A_CONFIG,
        "seed_records": records,
        "interpretation_firewall": (
            "This alternate teacher quantifies dependence on training multiplicity. "
            "It cannot replace accepted System A or R0.v2 based on held-out results."
        ),
    }
    manifest["manifest_sha256"] = _json_hash(manifest)
    _write_json_new(MANIFEST_PATH, manifest)
    print(f"robustness_manifest={MANIFEST_PATH}")
    print(f"manifest_hash={manifest['manifest_sha256']}")
    print(f"training_rows_original={manifest['training_rows_original']}")
    print(f"training_rows_retained={manifest['training_rows_retained']}")
    print("pre_post_partitions_loaded=false")
    print("next_gate=commit_teacher_manifest_before_downstream_robustness")


def verify_pattern_dedup_teacher() -> None:
    if not MANIFEST_PATH.is_file():
        raise FileNotFoundError(f"Missing alternate teacher manifest: {MANIFEST_PATH}")
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    stored = manifest.get("manifest_sha256")
    core = dict(manifest)
    core.pop("manifest_sha256", None)
    if _json_hash(core) != stored:
        raise ValueError("Alternate teacher manifest canonical hash mismatch.")
    if manifest.get("data_access") != {
        "training_used": True,
        "development_used": True,
        "pre_drift_used": False,
        "post_drift_used": False,
    }:
        raise ValueError("Alternate teacher data-access contract mismatch.")
    for record in manifest["seed_records"]:
        path = PROJECT_ROOT / record["checkpoint_file"]
        if not path.is_file():
            raise FileNotFoundError(f"Missing robustness checkpoint: {path}")
        if sha256_file(path) != record["checkpoint_sha256"]:
            raise ValueError(f"Robustness checkpoint hash mismatch for seed {record['seed']}")
    print(f"robustness_manifest={MANIFEST_PATH}")
    print(f"manifest_hash={stored}")
    print("pre_post_partitions_loaded=false")
    print("status=verified")
