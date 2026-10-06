from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any

os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")

import numpy as np
import torch
from scipy.stats import t
from sklearn.metrics import (
    average_precision_score,
    f1_score,
    matthews_corrcoef,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

from concept_drift_ids.frozen_preprocessing import (
    FrozenPreprocessing,
    load_frozen_preprocessing,
    transform_frame,
)
from concept_drift_ids.scenario_loader import (
    PROJECT_ROOT,
    load_manifest,
    load_partition,
)
from concept_drift_ids.scenario_manifest import sha256_file


ARTIFACT_DIR = PROJECT_ROOT / "artifacts" / "system_a"
CHECKPOINT_DIR = ARTIFACT_DIR / "checkpoints"
SEED_RECORD_DIR = ARTIFACT_DIR / "seed_records"
SYSTEM_A_MANIFEST_PATH = PROJECT_ROOT / "data" / "manifests" / "system_a_v1.json"
EVALUATION_PATH = PROJECT_ROOT / "results" / "system_a" / "static_evaluation.json"

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


class StaticMLP(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        dropout = float(SYSTEM_A_CONFIG["dropout"])
        self.network = nn.Sequential(
            nn.Linear(77, 128),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(64, 1),
        )
        self.reset_parameters()

    def reset_parameters(self) -> None:
        for module in self.modules():
            if isinstance(module, nn.Linear):
                nn.init.kaiming_uniform_(
                    module.weight,
                    nonlinearity="relu",
                )
                nn.init.zeros_(module.bias)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.network(x).squeeze(1)


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


def _set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)

    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)

    torch.use_deterministic_algorithms(True, warn_only=True)
    if hasattr(torch.backends, "cudnn"):
        torch.backends.cudnn.benchmark = False
        torch.backends.cudnn.deterministic = True


def _resolve_device(requested: str) -> torch.device:
    if requested == "auto":
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")

    device = torch.device(requested)
    if device.type == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA was requested but is not available.")
    return device


def prepare_train_dev() -> PreparedData:
    """
    Load only training/development data.

    Pre/post partitions are intentionally inaccessible to this preparation path.
    """
    manifest = load_manifest()
    preprocessing = load_frozen_preprocessing()

    if (
        preprocessing.scenario_id != manifest["scenario_id"]
        or preprocessing.scenario_version != int(manifest["scenario_version"])
    ):
        raise ValueError("Frozen preprocessing and scenario manifest do not match.")

    training = load_partition("training")
    X_train = transform_frame(
        training.X,
        preprocessing,
        dtype=np.dtype("float32"),
    )
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


@torch.inference_mode()
def _predict_probabilities(
    model: nn.Module,
    X: np.ndarray,
    *,
    device: torch.device,
    batch_size: int,
) -> np.ndarray:
    model.eval()
    tensor = torch.from_numpy(X)
    loader = DataLoader(
        TensorDataset(tensor),
        batch_size=batch_size,
        shuffle=False,
        num_workers=0,
    )

    probabilities: list[np.ndarray] = []
    for (batch_X,) in loader:
        logits = model(batch_X.to(device=device, non_blocking=False))
        probabilities.append(
            torch.sigmoid(logits).cpu().numpy()
        )

    return np.concatenate(probabilities).astype(np.float64, copy=False)


def _binary_metrics(
    y_true: np.ndarray,
    probabilities: np.ndarray,
    threshold: float,
) -> dict[str, float]:
    y = np.asarray(y_true, dtype=np.int8)
    probabilities = np.asarray(probabilities, dtype=np.float64)
    prediction = (probabilities >= threshold).astype(np.int8)

    benign = y == 0
    false_positive = int(np.logical_and(prediction == 1, benign).sum())
    true_negative = int(np.logical_and(prediction == 0, benign).sum())
    fpr_denominator = false_positive + true_negative
    fpr = false_positive / fpr_denominator if fpr_denominator else 0.0

    return {
        "precision": float(
            precision_score(y, prediction, zero_division=0)
        ),
        "recall": float(
            recall_score(y, prediction, zero_division=0)
        ),
        "f1": float(
            f1_score(y, prediction, zero_division=0)
        ),
        "fpr": float(fpr),
        "mcc": float(matthews_corrcoef(y, prediction)),
        "roc_auc": float(roc_auc_score(y, probabilities)),
        "average_precision": float(
            average_precision_score(y, probabilities)
        ),
    }


def select_threshold(
    y_true: np.ndarray,
    probabilities: np.ndarray,
) -> tuple[float, dict[str, float]]:
    """Select a dev-only threshold by MCC with deterministic tie-breaking."""
    y = np.asarray(y_true, dtype=np.int8)
    probabilities = np.asarray(probabilities, dtype=np.float64)

    fpr, tpr, thresholds = roc_curve(
        y,
        probabilities,
        drop_intermediate=False,
    )
    finite = np.isfinite(thresholds)
    fpr = fpr[finite]
    tpr = tpr[finite]
    thresholds = thresholds[finite]

    positives = int((y == 1).sum())
    negatives = int((y == 0).sum())

    tp = tpr * positives
    fn = positives - tp
    fp = fpr * negatives
    tn = negatives - fp

    denominator = np.sqrt(
        (tp + fp)
        * (tp + fn)
        * (tn + fp)
        * (tn + fn)
    )
    numerator = tp * tn - fp * fn
    mcc = np.divide(
        numerator,
        denominator,
        out=np.zeros_like(numerator),
        where=denominator != 0,
    )

    precision_denominator = tp + fp
    precision = np.divide(
        tp,
        precision_denominator,
        out=np.zeros_like(tp),
        where=precision_denominator != 0,
    )
    recall = np.divide(
        tp,
        tp + fn,
        out=np.zeros_like(tp),
        where=(tp + fn) != 0,
    )
    f1_denominator = precision + recall
    f1 = np.divide(
        2.0 * precision * recall,
        f1_denominator,
        out=np.zeros_like(precision),
        where=f1_denominator != 0,
    )

    best = max(
        range(len(thresholds)),
        key=lambda index: (
            float(mcc[index]),
            float(f1[index]),
            -float(fpr[index]),
            -abs(float(thresholds[index]) - 0.5),
        ),
    )
    threshold = float(np.clip(thresholds[best], 0.0, 1.0))
    return threshold, _binary_metrics(y, probabilities, threshold)


def _train_one_seed(
    data: PreparedData,
    *,
    seed: int,
    device: torch.device,
) -> dict[str, Any]:
    _set_seed(seed)

    model = StaticMLP().to(device)
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

    X_tensor = torch.from_numpy(data.X_train)
    y_tensor = torch.from_numpy(data.y_train)

    generator = torch.Generator()
    generator.manual_seed(seed)

    loader = DataLoader(
        TensorDataset(X_tensor, y_tensor),
        batch_size=int(SYSTEM_A_CONFIG["batch_size"]),
        shuffle=True,
        num_workers=int(SYSTEM_A_CONFIG["num_workers"]),
        generator=generator,
        drop_last=False,
    )

    best_ap = -math.inf
    best_epoch = -1
    best_state: dict[str, torch.Tensor] | None = None
    epochs_without_improvement = 0
    history: list[dict[str, float | int]] = []

    max_epochs = int(SYSTEM_A_CONFIG["max_epochs"])
    patience = int(SYSTEM_A_CONFIG["early_stopping_patience"])
    min_delta = float(SYSTEM_A_CONFIG["early_stopping_min_delta"])

    for epoch in range(1, max_epochs + 1):
        model.train()
        running_loss = 0.0
        seen = 0

        for batch_X, batch_y in loader:
            batch_X = batch_X.to(device)
            batch_y = batch_y.to(device)

            optimizer.zero_grad(set_to_none=True)
            logits = model(batch_X)
            loss = criterion(logits, batch_y)
            loss.backward()
            optimizer.step()

            rows = len(batch_X)
            running_loss += float(loss.detach().cpu()) * rows
            seen += rows

        dev_probabilities = _predict_probabilities(
            model,
            data.X_dev,
            device=device,
            batch_size=int(SYSTEM_A_CONFIG["batch_size"]),
        )
        dev_ap = float(
            average_precision_score(data.y_dev, dev_probabilities)
        )
        history.append(
            {
                "epoch": epoch,
                "training_loss": running_loss / seen,
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
            epochs_without_improvement = 0
        else:
            epochs_without_improvement += 1
            if epochs_without_improvement >= patience:
                break

    if best_state is None:
        raise RuntimeError("Training failed to produce a best checkpoint.")

    model.load_state_dict(best_state)
    model.to(device)

    dev_probabilities = _predict_probabilities(
        model,
        data.X_dev,
        device=device,
        batch_size=int(SYSTEM_A_CONFIG["batch_size"]),
    )
    threshold, dev_metrics = select_threshold(
        data.y_dev,
        dev_probabilities,
    )

    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    checkpoint_path = CHECKPOINT_DIR / f"seed_{seed}.pt"

    checkpoint = {
        "protocol_version": SYSTEM_A_CONFIG["protocol_version"],
        "config_sha256": _json_hash(SYSTEM_A_CONFIG),
        "seed": seed,
        "preprocessing_state_hash": data.preprocessing.state_hash,
        "best_epoch": best_epoch,
        "threshold": threshold,
        "model_state_dict": best_state,
    }
    torch.save(checkpoint, checkpoint_path)

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
        "torch_version": torch.__version__,
    }

    record_path = SEED_RECORD_DIR / f"seed_{seed}.json"
    _write_json(record_path, record)
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
            raise FileNotFoundError(
                f"Missing System-A checkpoint: {checkpoint_path}"
            )
        if sha256_file(checkpoint_path) != record["checkpoint_sha256"]:
            raise ValueError(
                f"Checkpoint hash mismatch for seed {seed}."
            )
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


def train_system_a(
    *,
    device_name: str,
    seeds: list[int],
) -> None:
    invalid = sorted(set(seeds).difference(SYSTEM_A_CONFIG["seeds"]))
    if invalid:
        raise ValueError(
            f"Seeds not allowed by frozen protocol: {invalid}"
        )

    data = prepare_train_dev()
    device = _resolve_device(device_name)

    print(
        f"System A training | device={device} | "
        f"preprocessing={data.preprocessing.state_hash}"
    )

    for seed in seeds:
        record = _train_one_seed(
            data,
            seed=seed,
            device=device,
        )
        print(
            f"seed={seed} best_epoch={record['best_epoch']} "
            f"dev_AP={record['development_metrics']['average_precision']:.6f} "
            f"threshold={record['threshold']:.6f} "
            f"dev_MCC={record['development_metrics']['mcc']:.6f}"
        )

    complete = all(
        (SEED_RECORD_DIR / f"seed_{seed}.json").exists()
        for seed in SYSTEM_A_CONFIG["seeds"]
    )
    if complete:
        manifest = freeze_system_a_manifest(
            data.preprocessing,
            data.manifest,
        )
        print(f"frozen_manifest={SYSTEM_A_MANIFEST_PATH}")
        print(f"manifest_hash={manifest['manifest_sha256']}")
    else:
        missing = [
            seed
            for seed in SYSTEM_A_CONFIG["seeds"]
            if not (SEED_RECORD_DIR / f"seed_{seed}.json").exists()
        ]
        print(f"remaining_seeds={missing}")


def _load_frozen_system_a_manifest() -> dict[str, Any]:
    if not SYSTEM_A_MANIFEST_PATH.exists():
        raise FileNotFoundError(
            "System A is not frozen. Complete all five training seeds first."
        )
    with SYSTEM_A_MANIFEST_PATH.open("r", encoding="utf-8") as file:
        manifest = json.load(file)

    stored = manifest.get("manifest_sha256")
    core = dict(manifest)
    core.pop("manifest_sha256", None)
    if not isinstance(stored, str) or _json_hash(core) != stored:
        raise ValueError("System-A manifest hash mismatch.")
    if manifest.get("config_sha256") != _json_hash(SYSTEM_A_CONFIG):
        raise ValueError("System-A frozen config no longer matches code.")

    for record in manifest["seed_records"]:
        checkpoint_path = PROJECT_ROOT / record["checkpoint_file"]
        if sha256_file(checkpoint_path) != record["checkpoint_sha256"]:
            raise ValueError(
                f"Checkpoint hash mismatch for seed {record['seed']}."
            )
    return manifest


def _load_checkpoint_model(
    record: dict[str, Any],
    *,
    device: torch.device,
) -> StaticMLP:
    checkpoint_path = PROJECT_ROOT / record["checkpoint_file"]
    checkpoint = torch.load(
        checkpoint_path,
        map_location="cpu",
        weights_only=False,
    )

    if checkpoint["config_sha256"] != _json_hash(SYSTEM_A_CONFIG):
        raise ValueError("Checkpoint config hash mismatch.")
    if checkpoint["preprocessing_state_hash"] != load_frozen_preprocessing().state_hash:
        raise ValueError("Checkpoint preprocessing-state hash mismatch.")

    model = StaticMLP()
    model.load_state_dict(checkpoint["model_state_dict"])
    model.to(device)
    model.eval()
    return model


def _mean_ci95(values: list[float]) -> dict[str, float]:
    array = np.asarray(values, dtype=np.float64)
    mean = float(array.mean())
    if len(array) < 2:
        return {"mean": mean, "ci95_low": mean, "ci95_high": mean}

    sem = float(array.std(ddof=1) / math.sqrt(len(array)))
    margin = float(t.ppf(0.975, df=len(array) - 1) * sem)
    return {
        "mean": mean,
        "ci95_low": mean - margin,
        "ci95_high": mean + margin,
    }


def evaluate_system_a(
    *,
    device_name: str,
) -> None:
    frozen = _load_frozen_system_a_manifest()
    preprocessing = load_frozen_preprocessing()
    device = _resolve_device(device_name)

    results: dict[str, Any] = {
        "system_id": frozen["system_id"],
        "system_manifest_sha256": frozen["manifest_sha256"],
        "preprocessing_state_hash": preprocessing.state_hash,
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
            )
            probabilities = _predict_probabilities(
                model,
                X,
                device=device,
                batch_size=int(SYSTEM_A_CONFIG["batch_size"]),
            )
            metrics = _binary_metrics(
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

        metric_names = list(seed_results[0]["metrics"])
        aggregate = {
            metric: _mean_ci95(
                [
                    float(seed_result["metrics"][metric])
                    for seed_result in seed_results
                ]
            )
            for metric in metric_names
        }

        results["partitions"][partition_name] = {
            "seed_results": seed_results,
            "aggregate": aggregate,
        }
        del X, y

    pre_by_seed = {
        result["seed"]: result["metrics"]
        for result in results["partitions"]["pre_drift"]["seed_results"]
    }
    post_by_seed = {
        result["seed"]: result["metrics"]
        for result in results["partitions"]["post_drift"]["seed_results"]
    }

    results["post_minus_pre"] = {
        metric: _mean_ci95(
            [
                float(post_by_seed[seed][metric] - pre_by_seed[seed][metric])
                for seed in SYSTEM_A_CONFIG["seeds"]
            ]
        )
        for metric in pre_by_seed[SYSTEM_A_CONFIG["seeds"][0]]
    }

    _write_json(EVALUATION_PATH, results)
    print(f"evaluation={EVALUATION_PATH}")

    for partition_name in ("pre_drift", "post_drift"):
        aggregate = results["partitions"][partition_name]["aggregate"]
        print(
            f"{partition_name}: "
            f"F1={aggregate['f1']['mean']:.6f} "
            f"MCC={aggregate['mcc']['mean']:.6f} "
            f"FPR={aggregate['fpr']['mean']:.6f} "
            f"AP={aggregate['average_precision']['mean']:.6f}"
        )


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

    args = parser.parse_args()

    if args.command == "train":
        train_system_a(
            device_name=args.device,
            seeds=args.seeds,
        )
    else:
        evaluate_system_a(device_name=args.device)


if __name__ == "__main__":
    main()
