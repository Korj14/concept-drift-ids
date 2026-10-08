from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import torch
from sklearn.metrics import average_precision_score
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

from concept_drift_ids.evaluation_tables import (
    write_evaluation_tables,
    write_training_history_table,
)
from concept_drift_ids.frozen_preprocessing import (
    FrozenPreprocessing,
    load_frozen_preprocessing,
    transform_frame,
)
from concept_drift_ids.neural import (
    BinaryMLP,
    binary_metrics,
    mean_ci95,
    predict_probabilities,
    resolve_device,
    select_mcc_threshold,
    set_reproducible_seed,
)
from concept_drift_ids.scenario_loader import (
    PROJECT_ROOT,
    load_manifest,
    load_partition,
)
from concept_drift_ids.scenario_manifest import sha256_file
from concept_drift_ids.symbolic import reporting_windows


ARTIFACT_DIR = PROJECT_ROOT / "artifacts" / "system_a"
CHECKPOINT_DIR = ARTIFACT_DIR / "checkpoints"
SEED_RECORD_DIR = ARTIFACT_DIR / "seed_records"
SYSTEM_A_MANIFEST_PATH = PROJECT_ROOT / "data" / "manifests" / "system_a_v1.json"
EVALUATION_DIR = PROJECT_ROOT / "results" / "frozen" / "system_a_v1"
EVALUATION_PATH = EVALUATION_DIR / "static_evaluation.json"
EVALUATION_MANIFEST_PATH = EVALUATION_DIR / "evaluation_manifest.json"
SUPPLEMENT_DIR = PROJECT_ROOT / "results" / "frozen" / "system_a_v1_supplement_v1"
SUPPLEMENT_MANIFEST_PATH = SUPPLEMENT_DIR / "supplement_manifest.json"
LONGITUDINAL_DIR = PROJECT_ROOT / "results" / "frozen" / "system_a_v1_longitudinal_v1"
LONGITUDINAL_MANIFEST_PATH = LONGITUDINAL_DIR / "evaluation_manifest.json"

SYSTEM_A_CONFIG: dict[str, Any] = {
    "protocol_version": 1,
    "input_features": 77,
    "hidden_layers": [128, 64],
    "activation": "ReLU",
    "dropout": 0.10,
    "weight_initialization": "kaiming_uniform_relu",
    "loss": "BCEWithLogitsLoss",
    "positive_class_weight": "training_benign/training_attack",
    "optimizer": "Adam",
    "learning_rate": 0.001,
    "weight_decay": 0.00001,
    "batch_size": 4096,
    "max_epochs": 20,
    "early_stopping_metric": "development_average_precision",
    "early_stopping_patience": 3,
    "early_stopping_min_delta": 0.0001,
    "threshold_objective": "MCC",
    "threshold_tiebreak": ["F1", "lower_FPR", "closest_to_0.5"],
    "probability_calibration": "none",
    "num_workers": 0,
    "seeds": [0, 1, 2, 3, 4],
}


@dataclass
class PreparedData:
    X_train: np.ndarray
    y_train: np.ndarray
    X_dev: np.ndarray
    y_dev: np.ndarray
    preprocessing: FrozenPreprocessing
    manifest: dict


def _json_hash(payload: Any) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as file:
        json.dump(payload, file, indent=2, ensure_ascii=False, allow_nan=False)
        file.write("\n")


def _new_model() -> BinaryMLP:
    return BinaryMLP(
        input_features=int(SYSTEM_A_CONFIG["input_features"]),
        hidden_layers=tuple(SYSTEM_A_CONFIG["hidden_layers"]),
        dropout=float(SYSTEM_A_CONFIG["dropout"]),
    )


def prepare_train_dev() -> PreparedData:
    """Load only train/dev; pre/post are intentionally unavailable here."""
    manifest = load_manifest()
    preprocessing = load_frozen_preprocessing()

    if (
        preprocessing.scenario_id != manifest["scenario_id"]
        or preprocessing.scenario_version != int(manifest["scenario_version"])
    ):
        raise ValueError("Frozen preprocessing and scenario manifest do not match.")

    training = load_partition("training")
    X_train = transform_frame(training.X, preprocessing, dtype=np.dtype("float32"))
    y_train = training.y.to_numpy(dtype=np.float32, copy=True)
    del training

    development = load_partition("development")
    X_dev = transform_frame(
        development.X,
        preprocessing,
        dtype=np.dtype("float32"),
    )
    y_dev = development.y.to_numpy(dtype=np.float32, copy=True)
    del development

    return PreparedData(
        X_train=X_train,
        y_train=y_train,
        X_dev=X_dev,
        y_dev=y_dev,
        preprocessing=preprocessing,
        manifest=manifest,
    )


def _train_one_seed(
    data: PreparedData,
    *,
    seed: int,
    device: torch.device,
) -> dict[str, Any]:
    set_reproducible_seed(seed)

    model = _new_model().to(device)
    benign = int((data.y_train == 0).sum())
    attack = int((data.y_train == 1).sum())
    pos_weight_value = benign / attack

    criterion = nn.BCEWithLogitsLoss(
        pos_weight=torch.tensor(
            pos_weight_value,
            dtype=torch.float32,
            device=device,
        )
    )
    optimizer = torch.optim.Adam(
        model.parameters(),
        lr=float(SYSTEM_A_CONFIG["learning_rate"]),
        weight_decay=float(SYSTEM_A_CONFIG["weight_decay"]),
    )

    generator = torch.Generator().manual_seed(seed)
    loader = DataLoader(
        TensorDataset(
            torch.from_numpy(data.X_train),
            torch.from_numpy(data.y_train),
        ),
        batch_size=int(SYSTEM_A_CONFIG["batch_size"]),
        shuffle=True,
        num_workers=0,
        generator=generator,
        drop_last=False,
    )

    best_ap = -math.inf
    best_epoch = -1
    best_state: dict[str, torch.Tensor] | None = None
    stale_epochs = 0
    history: list[dict[str, float | int]] = []

    max_epochs = int(SYSTEM_A_CONFIG["max_epochs"])
    patience = int(SYSTEM_A_CONFIG["early_stopping_patience"])
    min_delta = float(SYSTEM_A_CONFIG["early_stopping_min_delta"])
    batch_size = int(SYSTEM_A_CONFIG["batch_size"])

    for epoch in range(1, max_epochs + 1):
        model.train()
        total_loss = 0.0
        seen = 0

        for batch_X, batch_y in loader:
            batch_X = batch_X.to(device)
            batch_y = batch_y.to(device)

            optimizer.zero_grad(set_to_none=True)
            loss = criterion(model(batch_X), batch_y)
            loss.backward()
            optimizer.step()

            rows = len(batch_X)
            total_loss += float(loss.detach().cpu()) * rows
            seen += rows

        dev_probabilities = predict_probabilities(
            model,
            data.X_dev,
            device=device,
            batch_size=batch_size,
        )
        dev_ap = float(
            average_precision_score(data.y_dev, dev_probabilities)
        )
        history.append(
            {
                "epoch": epoch,
                "training_loss": total_loss / seen,
                "development_average_precision": dev_ap,
            }
        )

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
        raise RuntimeError("Training failed to produce a best checkpoint.")

    model.load_state_dict(best_state)
    model.to(device)

    dev_probabilities = predict_probabilities(
        model,
        data.X_dev,
        device=device,
        batch_size=batch_size,
    )
    threshold, dev_metrics = select_mcc_threshold(
        data.y_dev,
        dev_probabilities,
    )

    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    checkpoint_path = CHECKPOINT_DIR / f"seed_{seed}.pt"
    torch.save(
        {
            "protocol_version": SYSTEM_A_CONFIG["protocol_version"],
            "config_sha256": _json_hash(SYSTEM_A_CONFIG),
            "seed": seed,
            "preprocessing_state_hash": data.preprocessing.state_hash,
            "best_epoch": best_epoch,
            "threshold": threshold,
            "model_state_dict": best_state,
        },
        checkpoint_path,
    )

    record = {
        "seed": seed,
        "best_epoch": best_epoch,
        "threshold": threshold,
        "development_metrics": dev_metrics,
        "positive_class_weight": pos_weight_value,
        "epochs_ran": len(history),
        "history": history,
        "checkpoint_file": checkpoint_path.relative_to(PROJECT_ROOT).as_posix(),
        "checkpoint_sha256": sha256_file(checkpoint_path),
        "device": str(device),
        "torch_version": str(torch.__version__),
    }
    _write_json(SEED_RECORD_DIR / f"seed_{seed}.json", record)
    return record


def _load_seed_record(seed: int) -> dict[str, Any]:
    path = SEED_RECORD_DIR / f"seed_{seed}.json"
    if not path.exists():
        raise FileNotFoundError(f"Missing System-A seed record: {path}")
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def freeze_system_a_manifest(
    preprocessing: FrozenPreprocessing,
    scenario_manifest: dict,
) -> dict[str, Any]:
    records = []
    for seed in SYSTEM_A_CONFIG["seeds"]:
        record = _load_seed_record(int(seed))
        checkpoint_path = PROJECT_ROOT / record["checkpoint_file"]

        if not checkpoint_path.exists():
            raise FileNotFoundError(f"Missing System-A checkpoint: {checkpoint_path}")
        if sha256_file(checkpoint_path) != record["checkpoint_sha256"]:
            raise ValueError(f"Checkpoint hash mismatch for seed {seed}.")
        records.append(record)

    manifest = {
        "manifest_format_version": 1,
        "system_id": "system_a_static_neural_v1",
        "scenario_id": scenario_manifest["scenario_id"],
        "scenario_version": scenario_manifest["scenario_version"],
        "preprocessing_state_hash": preprocessing.state_hash,
        "config": SYSTEM_A_CONFIG,
        "config_sha256": _json_hash(SYSTEM_A_CONFIG),
        "training_partition_used": True,
        "development_partition_used": True,
        "pre_drift_used_for_model_development": False,
        "post_drift_used_for_model_development": False,
        "seed_records": records,
    }
    manifest["manifest_sha256"] = _json_hash(manifest)
    _write_json(SYSTEM_A_MANIFEST_PATH, manifest)
    return manifest


def train_system_a(*, device_name: str, seeds: list[int]) -> None:
    invalid = sorted(set(seeds).difference(SYSTEM_A_CONFIG["seeds"]))
    if invalid:
        raise ValueError(f"Seeds not allowed by frozen protocol: {invalid}")

    data = prepare_train_dev()
    device = resolve_device(device_name)

    print(
        f"System A training | device={device} | "
        f"preprocessing={data.preprocessing.state_hash}"
    )

    for seed in seeds:
        record = _train_one_seed(data, seed=seed, device=device)
        print(
            f"seed={seed} best_epoch={record['best_epoch']} "
            f"dev_AP={record['development_metrics']['average_precision']:.6f} "
            f"threshold={record['threshold']:.6f} "
            f"dev_MCC={record['development_metrics']['mcc']:.6f}"
        )

    missing = [
        seed
        for seed in SYSTEM_A_CONFIG["seeds"]
        if not (SEED_RECORD_DIR / f"seed_{seed}.json").exists()
    ]
    if missing:
        print(f"remaining_seeds={missing}")
        return

    manifest = freeze_system_a_manifest(data.preprocessing, data.manifest)
    print(f"frozen_manifest={SYSTEM_A_MANIFEST_PATH}")
    print(f"manifest_hash={manifest['manifest_sha256']}")


def _load_frozen_system_a_manifest() -> dict[str, Any]:
    if not SYSTEM_A_MANIFEST_PATH.exists():
        raise FileNotFoundError(
            "System A is not frozen. Complete all five training seeds first."
        )

    with SYSTEM_A_MANIFEST_PATH.open("r", encoding="utf-8") as file:
        manifest = json.load(file)

    stored_hash = manifest.get("manifest_sha256")
    core = dict(manifest)
    core.pop("manifest_sha256", None)

    if not isinstance(stored_hash, str) or _json_hash(core) != stored_hash:
        raise ValueError("System-A manifest hash mismatch.")
    if manifest.get("config_sha256") != _json_hash(SYSTEM_A_CONFIG):
        raise ValueError("System-A frozen config no longer matches code.")

    records = manifest.get("seed_records")
    if not isinstance(records, list):
        raise ValueError("System-A manifest seed_records must be a list.")

    expected_seeds = [int(seed) for seed in SYSTEM_A_CONFIG["seeds"]]
    observed_seeds = [int(record["seed"]) for record in records]
    if len(observed_seeds) != len(set(observed_seeds)):
        raise ValueError("System-A manifest contains duplicate seed records.")
    if sorted(observed_seeds) != sorted(expected_seeds):
        raise ValueError(
            "System-A manifest seed set does not match the frozen protocol."
        )

    devices = {str(record["device"]) for record in records}
    if len(devices) != 1:
        raise ValueError(
            f"System-A seeds used inconsistent device backends: {sorted(devices)}"
        )

    max_epochs = int(SYSTEM_A_CONFIG["max_epochs"])
    for record in records:
        threshold = float(record["threshold"])
        if not math.isfinite(threshold) or not 0.0 <= threshold <= 1.0:
            raise ValueError(
                f"Invalid frozen threshold for seed {record['seed']}: {threshold}"
            )
        best_epoch = int(record["best_epoch"])
        if not 1 <= best_epoch <= max_epochs:
            raise ValueError(
                f"Invalid best epoch for seed {record['seed']}: {best_epoch}"
            )

        checkpoint_path = PROJECT_ROOT / record["checkpoint_file"]
        if not checkpoint_path.exists():
            raise FileNotFoundError(
                f"Missing System-A checkpoint for seed {record['seed']}: "
                f"{checkpoint_path}"
            )
        if sha256_file(checkpoint_path) != record["checkpoint_sha256"]:
            raise ValueError(
                f"Checkpoint hash mismatch for seed {record['seed']}."
            )
    return manifest


def _load_and_verify_evaluation_manifest(
    frozen: dict[str, Any],
    *,
    preprocessing_hash: str,
) -> dict[str, Any]:
    if not EVALUATION_MANIFEST_PATH.exists():
        raise FileNotFoundError(
            f"Missing frozen System-A evaluation manifest: "
            f"{EVALUATION_MANIFEST_PATH}"
        )

    with EVALUATION_MANIFEST_PATH.open("r", encoding="utf-8") as file:
        manifest = json.load(file)

    stored_hash = manifest.get("manifest_sha256")
    core = dict(manifest)
    core.pop("manifest_sha256", None)
    if not isinstance(stored_hash, str) or _json_hash(core) != stored_hash:
        raise ValueError("System-A evaluation manifest hash mismatch.")

    if manifest.get("system_manifest_sha256") != frozen["manifest_sha256"]:
        raise ValueError(
            "Evaluation manifest does not reference the frozen System-A manifest."
        )
    if manifest.get("preprocessing_state_hash") != preprocessing_hash:
        raise ValueError(
            "Evaluation manifest preprocessing hash does not match the "
            "accepted preprocessing state."
        )

    files = manifest.get("files")
    if not isinstance(files, dict) or not files:
        raise ValueError("Evaluation manifest has no file inventory.")

    for name, entry in files.items():
        relative_path = entry.get("path")
        expected_hash = entry.get("sha256")
        if not isinstance(relative_path, str) or not isinstance(
            expected_hash, str
        ):
            raise ValueError(
                f"Invalid evaluation-manifest entry for {name!r}."
            )
        path = PROJECT_ROOT / relative_path
        if not path.exists():
            raise FileNotFoundError(
                f"Missing frozen evaluation artifact {name!r}: {path}"
            )
        if sha256_file(path) != expected_hash:
            raise ValueError(
                f"Frozen evaluation artifact hash mismatch for {name!r}."
            )
    return manifest


def _load_and_verify_supplement_manifest() -> dict[str, Any]:
    if not SUPPLEMENT_MANIFEST_PATH.exists():
        raise FileNotFoundError(
            f"Missing System-A evidence supplement manifest: "
            f"{SUPPLEMENT_MANIFEST_PATH}"
        )

    with SUPPLEMENT_MANIFEST_PATH.open("r", encoding="utf-8") as file:
        manifest = json.load(file)

    stored_hash = manifest.get("manifest_sha256")
    core = dict(manifest)
    core.pop("manifest_sha256", None)
    if not isinstance(stored_hash, str) or _json_hash(core) != stored_hash:
        raise ValueError("System-A supplement manifest hash mismatch.")

    files = manifest.get("files")
    if not isinstance(files, dict) or not files:
        raise ValueError("System-A supplement manifest has no file inventory.")

    for name, entry in files.items():
        relative_path = entry.get("path")
        expected_hash = entry.get("sha256")
        if not isinstance(relative_path, str) or not isinstance(
            expected_hash, str
        ):
            raise ValueError(
                f"Invalid supplement-manifest entry for {name!r}."
            )
        path = PROJECT_ROOT / relative_path
        if not path.exists():
            raise FileNotFoundError(
                f"Missing supplement artifact {name!r}: {path}"
            )
        if sha256_file(path) != expected_hash:
            raise ValueError(
                f"Supplement artifact hash mismatch for {name!r}."
            )
    return manifest


def verify_system_a() -> None:
    """Verify frozen System-A artifacts without loading pre/post partitions."""
    frozen = _load_frozen_system_a_manifest()
    preprocessing = load_frozen_preprocessing()
    scenario = load_manifest()

    if (
        frozen.get("scenario_id") != scenario["scenario_id"]
        or int(frozen.get("scenario_version")) != int(
            scenario["scenario_version"]
        )
    ):
        raise ValueError(
            "System-A manifest scenario identity no longer matches "
            "the frozen scenario manifest."
        )
    if frozen.get("preprocessing_state_hash") != preprocessing.state_hash:
        raise ValueError(
            "System-A manifest preprocessing state no longer matches "
            "the accepted frozen preprocessing."
        )

    evaluation = _load_and_verify_evaluation_manifest(
        frozen,
        preprocessing_hash=preprocessing.state_hash,
    )
    supplement = _load_and_verify_supplement_manifest()

    if (
        supplement.get("source_evaluation_manifest_sha256")
        != evaluation["manifest_sha256"]
    ):
        raise ValueError(
            "System-A supplement does not reference the accepted "
            "evaluation manifest."
        )

    print(f"system_manifest={SYSTEM_A_MANIFEST_PATH}")
    print(f"system_manifest_hash={frozen['manifest_sha256']}")
    print(f"evaluation_manifest={EVALUATION_MANIFEST_PATH}")
    print(f"evaluation_manifest_hash={evaluation['manifest_sha256']}")
    print(f"supplement_manifest={SUPPLEMENT_MANIFEST_PATH}")
    print(f"supplement_manifest_hash={supplement['manifest_sha256']}")
    print(f"verified_seeds={','.join(str(seed) for seed in SYSTEM_A_CONFIG['seeds'])}")
    print("pre_post_partitions_loaded=false")
    print("status=verified")


def _load_checkpoint_model(
    record: dict[str, Any],
    *,
    device: torch.device,
    preprocessing_hash: str,
) -> BinaryMLP:
    checkpoint_path = PROJECT_ROOT / record["checkpoint_file"]
    checkpoint = torch.load(
        checkpoint_path,
        map_location="cpu",
        weights_only=False,
    )

    if checkpoint["config_sha256"] != _json_hash(SYSTEM_A_CONFIG):
        raise ValueError("Checkpoint config hash mismatch.")
    if checkpoint["preprocessing_state_hash"] != preprocessing_hash:
        raise ValueError("Checkpoint preprocessing-state hash mismatch.")

    model = _new_model()
    model.load_state_dict(checkpoint["model_state_dict"])
    model.to(device)
    model.eval()
    return model


def evaluate_system_a(*, device_name: str) -> None:
    if EVALUATION_MANIFEST_PATH.exists():
        raise FileExistsError(
            "Frozen System-A evaluation already exists. "
            "Use 'python run.py system-a verify' for integrity checks; "
            "do not overwrite accepted evidence."
        )

    frozen = _load_frozen_system_a_manifest()
    preprocessing = load_frozen_preprocessing()
    device = resolve_device(device_name)

    results: dict[str, Any] = {
        "evaluation_format_version": 1,
        "system_id": frozen["system_id"],
        "scenario_id": frozen["scenario_id"],
        "scenario_version": frozen["scenario_version"],
        "system_manifest_sha256": frozen["manifest_sha256"],
        "preprocessing_state_hash": preprocessing.state_hash,
        "metric_roles": {
            "primary_detection": [
                "precision",
                "recall",
                "f1",
                "fpr",
                "mcc",
                "roc_auc",
                "average_precision"
            ],
            "secondary_descriptive": [
                "accuracy",
                "balanced_accuracy"
            ]
        },
        "partitions": {},
    }

    for partition_name in ("pre_drift", "post_drift"):
        partition = load_partition(partition_name)
        X = transform_frame(
            partition.X,
            preprocessing,
            dtype=np.dtype("float32"),
        )
        y = partition.y.to_numpy(dtype=np.int8, copy=True)
        del partition

        seed_results = []
        for record in frozen["seed_records"]:
            model = _load_checkpoint_model(
                record,
                device=device,
                preprocessing_hash=preprocessing.state_hash,
            )
            probabilities = predict_probabilities(
                model,
                X,
                device=device,
                batch_size=int(SYSTEM_A_CONFIG["batch_size"]),
            )
            metrics = binary_metrics(
                y,
                probabilities,
                float(record["threshold"]),
            )
            seed_results.append(
                {
                    "seed": int(record["seed"]),
                    "threshold": float(record["threshold"]),
                    "metrics": metrics,
                }
            )
            del model, probabilities

        aggregate = {
            metric: mean_ci95(
                [
                    float(seed_result["metrics"][metric])
                    for seed_result in seed_results
                ]
            )
            for metric in seed_results[0]["metrics"]
        }
        results["partitions"][partition_name] = {
            "seed_results": seed_results,
            "aggregate": aggregate,
        }
        del X, y

    pre = {
        row["seed"]: row["metrics"]
        for row in results["partitions"]["pre_drift"]["seed_results"]
    }
    post = {
        row["seed"]: row["metrics"]
        for row in results["partitions"]["post_drift"]["seed_results"]
    }

    seed_deltas = [
        {
            "seed": seed,
            "metrics": {
                metric: float(post[seed][metric] - pre[seed][metric])
                for metric in pre[seed]
            },
        }
        for seed in SYSTEM_A_CONFIG["seeds"]
    ]
    results["post_minus_pre"] = {
        "seed_deltas": seed_deltas,
        "aggregate": {
            metric: mean_ci95(
                [
                    float(post[seed][metric] - pre[seed][metric])
                    for seed in SYSTEM_A_CONFIG["seeds"]
                ]
            )
            for metric in pre[SYSTEM_A_CONFIG["seeds"][0]]
        },
    }

    _write_json(EVALUATION_PATH, results)
    table_paths = write_evaluation_tables(results, EVALUATION_DIR)
    history_path = write_training_history_table(frozen, EVALUATION_DIR)

    output_paths = {
        "static_evaluation": EVALUATION_PATH,
        "training_history": history_path,
        **table_paths,
    }
    evaluation_manifest = {
        "manifest_format_version": 1,
        "evaluation_id": "system_a_static_evaluation_v1",
        "system_id": frozen["system_id"],
        "scenario_id": frozen["scenario_id"],
        "scenario_version": frozen["scenario_version"],
        "system_manifest_sha256": frozen["manifest_sha256"],
        "preprocessing_state_hash": preprocessing.state_hash,
        "files": {
            name: {
                "path": path.relative_to(PROJECT_ROOT).as_posix(),
                "sha256": sha256_file(path),
            }
            for name, path in output_paths.items()
        },
    }
    evaluation_manifest["manifest_sha256"] = _json_hash(evaluation_manifest)
    _write_json(EVALUATION_MANIFEST_PATH, evaluation_manifest)

    print(f"evaluation_manifest={EVALUATION_MANIFEST_PATH}")
    print(f"evaluation_manifest_hash={evaluation_manifest['manifest_sha256']}")
    for name, path in output_paths.items():
        print(f"{name}={path}")

    for partition_name in ("pre_drift", "post_drift"):
        aggregate = results["partitions"][partition_name]["aggregate"]
        print(
            f"{partition_name}: "
            f"Accuracy={aggregate['accuracy']['mean']:.6f} "
            f"BalancedAccuracy={aggregate['balanced_accuracy']['mean']:.6f} "
            f"F1={aggregate['f1']['mean']:.6f} "
            f"MCC={aggregate['mcc']['mean']:.6f} "
            f"FPR={aggregate['fpr']['mean']:.6f} "
            f"AP={aggregate['average_precision']['mean']:.6f}"
        )


def _write_json_new(path: Path, payload: Any) -> None:
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite accepted artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as file:
        json.dump(payload, file, indent=2, ensure_ascii=False, allow_nan=False)
        file.write("\n")


def _write_csv_new(path: Path, rows: list[dict[str, Any]]) -> None:
    import csv

    if path.exists():
        raise FileExistsError(f"Refusing to overwrite accepted artifact: {path}")
    if not rows:
        raise ValueError("Cannot write empty longitudinal System-A evidence.")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _window_metrics_safe(
    y_true: np.ndarray,
    probabilities: np.ndarray,
    threshold: float,
) -> dict[str, float | None]:
    y = np.asarray(y_true, dtype=np.int8)
    p = np.asarray(probabilities, dtype=np.float64)
    if len(np.unique(y)) >= 2:
        return binary_metrics(y, p, threshold)

    prediction = (p >= threshold).astype(np.int8)
    tn = int(np.sum((y == 0) & (prediction == 0)))
    fp = int(np.sum((y == 0) & (prediction == 1)))
    fn = int(np.sum((y == 1) & (prediction == 0)))
    tp = int(np.sum((y == 1) & (prediction == 1)))
    accuracy = float(np.mean(prediction == y))
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2.0 * precision * recall / (precision + recall) if precision + recall else 0.0
    fpr = fp / (fp + tn) if fp + tn else 0.0
    balanced_accuracy = (
        tn / (tn + fp) if np.all(y == 0) and tn + fp
        else tp / (tp + fn) if tp + fn
        else 0.0
    )
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


def _longitudinal_git_state() -> dict[str, str]:
    def run(*args: str) -> str:
        return subprocess.run(
            ["git", *args],
            cwd=PROJECT_ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

    status = run("status", "--porcelain")
    if status:
        raise RuntimeError(
            "System-A longitudinal rescoring requires a clean Git worktree."
        )
    return {
        "commit": run("rev-parse", "HEAD"),
        "branch": run("branch", "--show-current"),
        "clean": "true",
    }


def rescore_system_a_longitudinal(*, device_name: str) -> None:
    """Rescore frozen System A on the common reporting grid; no retraining/retuning."""
    if device_name != "cpu":
        raise ValueError("Frozen System-A longitudinal v1 rescoring uses CPU.")
    if LONGITUDINAL_DIR.exists() or LONGITUDINAL_MANIFEST_PATH.exists():
        raise FileExistsError(
            "Frozen System-A longitudinal supplement already exists; refusing overwrite."
        )

    evaluation_git = _longitudinal_git_state()
    frozen = _load_frozen_system_a_manifest()
    preprocessing = load_frozen_preprocessing()
    accepted_eval = _load_and_verify_evaluation_manifest(
        frozen, preprocessing_hash=preprocessing.state_hash
    )
    device = torch.device("cpu")
    rows: list[dict[str, Any]] = []

    for partition_name in ("pre_drift", "post_drift"):
        partition = load_partition(partition_name)
        X = transform_frame(
            partition.X,
            preprocessing,
            dtype=np.dtype("float32"),
        )
        y = partition.y.to_numpy(dtype=np.int8, copy=True)
        del partition

        for record in frozen["seed_records"]:
            model = _load_checkpoint_model(
                record,
                device=device,
                preprocessing_hash=preprocessing.state_hash,
            )
            probabilities = predict_probabilities(
                model,
                X,
                device=device,
                batch_size=int(SYSTEM_A_CONFIG["batch_size"]),
            )
            threshold = float(record["threshold"])

            for window_index, (start, stop) in enumerate(
                reporting_windows(
                    len(y),
                    window_size=5_000,
                    min_remainder=1_000,
                )
            ):
                wy = y[start:stop]
                wp = probabilities[start:stop]
                prediction = (wp >= threshold).astype(np.int8)
                tn = int(np.sum((wy == 0) & (prediction == 0)))
                fp = int(np.sum((wy == 0) & (prediction == 1)))
                fn = int(np.sum((wy == 1) & (prediction == 0)))
                tp = int(np.sum((wy == 1) & (prediction == 1)))
                rows.append(
                    {
                        "system_id": frozen["system_id"],
                        "scenario_id": frozen["scenario_id"],
                        "scenario_version": frozen["scenario_version"],
                        "partition": partition_name,
                        "seed": int(record["seed"]),
                        "threshold": threshold,
                        "window_index": window_index,
                        "row_start": start,
                        "row_end": stop,
                        "sample_count": int(stop - start),
                        "benign_count": int(np.sum(wy == 0)),
                        "attack_count": int(np.sum(wy == 1)),
                        "attack_prevalence": float(np.mean(wy == 1)),
                        "tn": tn,
                        "fp": fp,
                        "fn": fn,
                        "tp": tp,
                        **_window_metrics_safe(wy, wp, threshold),
                    }
                )
            del model, probabilities
        del X, y

    LONGITUDINAL_DIR.mkdir(parents=True, exist_ok=False)
    table_path = LONGITUDINAL_DIR / "window_metrics.csv"
    _write_csv_new(table_path, rows)
    summary_path = LONGITUDINAL_DIR / "longitudinal_rescore.json"
    summary = {
        "format_version": 1,
        "evaluation_id": "system_a_longitudinal_v1",
        "system_id": frozen["system_id"],
        "scenario_id": frozen["scenario_id"],
        "scenario_version": frozen["scenario_version"],
        "system_manifest_sha256": frozen["manifest_sha256"],
        "source_evaluation_manifest_sha256": accepted_eval["manifest_sha256"],
        "preprocessing_state_hash": preprocessing.state_hash,
        "backend": "cpu",
        "evaluation_git": evaluation_git,
        "window_policy": {
            "size": 5000,
            "stride": 5000,
            "minimum_final_remainder": 1000,
            "boundary_aligned": True,
            "partitions_windowed_separately": True,
        },
        "row_count": len(rows),
    }
    _write_json_new(summary_path, summary)

    manifest = {
        "manifest_format_version": 1,
        "evaluation_id": "system_a_longitudinal_v1",
        "system_id": frozen["system_id"],
        "scenario_id": frozen["scenario_id"],
        "scenario_version": frozen["scenario_version"],
        "system_manifest_sha256": frozen["manifest_sha256"],
        "source_evaluation_manifest_sha256": accepted_eval["manifest_sha256"],
        "preprocessing_state_hash": preprocessing.state_hash,
        "evaluation_git": evaluation_git,
        "files": {
            "summary": {
                "path": summary_path.relative_to(PROJECT_ROOT).as_posix(),
                "sha256": sha256_file(summary_path),
            },
            "window_metrics": {
                "path": table_path.relative_to(PROJECT_ROOT).as_posix(),
                "sha256": sha256_file(table_path),
            },
        },
    }
    manifest["manifest_sha256"] = _json_hash(manifest)
    _write_json_new(LONGITUDINAL_MANIFEST_PATH, manifest)
    print(f"longitudinal_manifest={LONGITUDINAL_MANIFEST_PATH}")
    print(f"longitudinal_manifest_hash={manifest['manifest_sha256']}")
    print(f"window_rows={len(rows)}")
    print("retrained=false")
    print("rethresholded=false")
    print("status=frozen_system_a_longitudinal_rescore_written")


def _parse_seeds(value: str) -> list[int]:
    seeds = [int(item.strip()) for item in value.split(",") if item.strip()]
    if not seeds:
        raise argparse.ArgumentTypeError("At least one seed is required.")
    return seeds


def main() -> None:
    parser = argparse.ArgumentParser(description="System A static neural baseline")
    subparsers = parser.add_subparsers(dest="command", required=True)

    train_parser = subparsers.add_parser("train")
    train_parser.add_argument("--device", default="auto")
    train_parser.add_argument(
        "--seeds",
        type=_parse_seeds,
        default=list(SYSTEM_A_CONFIG["seeds"]),
        help="Comma-separated subset of frozen seeds. Default: 0,1,2,3,4",
    )

    evaluate_parser = subparsers.add_parser("evaluate")
    evaluate_parser.add_argument("--device", default="auto")

    subparsers.add_parser(
        "verify",
        help=(
            "Verify frozen System-A checkpoints/manifests/results without "
            "loading pre/post partitions."
        ),
    )

    rescore_parser = subparsers.add_parser(
        "rescore-windows",
        help="Rescore frozen System A on the common 5,000-row reporting grid.",
    )
    rescore_parser.add_argument("--device", default="cpu")

    subparsers.add_parser(
        "build-pattern-dedup-robustness",
        help=(
            "Train the post-hoc exact-pattern+binary-label deduplicated "
            "System-A robustness teacher using training/development only."
        ),
    )
    subparsers.add_parser(
        "verify-pattern-dedup-robustness",
        help="Verify the frozen alternate-teacher robustness manifest/checkpoints.",
    )

    args = parser.parse_args()

    if args.command == "train":
        train_system_a(device_name=args.device, seeds=args.seeds)
    elif args.command == "evaluate":
        evaluate_system_a(device_name=args.device)
    elif args.command == "rescore-windows":
        rescore_system_a_longitudinal(device_name=args.device)
    elif args.command == "build-pattern-dedup-robustness":
        from concept_drift_ids.system_a_duplicate_robustness import (
            build_pattern_dedup_teacher,
        )
        build_pattern_dedup_teacher()
    elif args.command == "verify-pattern-dedup-robustness":
        from concept_drift_ids.system_a_duplicate_robustness import (
            verify_pattern_dedup_teacher,
        )
        verify_pattern_dedup_teacher()
    else:
        verify_system_a()


if __name__ == "__main__":
    main()
