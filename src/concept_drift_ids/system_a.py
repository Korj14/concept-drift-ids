from __future__ import annotations

import argparse
import hashlib
import json
import math
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


ARTIFACT_DIR = PROJECT_ROOT / "artifacts" / "system_a"
CHECKPOINT_DIR = ARTIFACT_DIR / "checkpoints"
SEED_RECORD_DIR = ARTIFACT_DIR / "seed_records"
SYSTEM_A_MANIFEST_PATH = PROJECT_ROOT / "data" / "manifests" / "system_a_v1.json"
EVALUATION_DIR = PROJECT_ROOT / "results" / "frozen" / "system_a_v1"
EVALUATION_PATH = EVALUATION_DIR / "static_evaluation.json"
EVALUATION_MANIFEST_PATH = EVALUATION_DIR / "evaluation_manifest.json"

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

    devices = {str(record["device"]) for record in manifest["seed_records"]}
    if len(devices) != 1:
        raise ValueError(
            f"System-A seeds used inconsistent device backends: {sorted(devices)}"
        )

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
        train_system_a(device_name=args.device, seeds=args.seeds)
    else:
        evaluate_system_a(device_name=args.device)


if __name__ == "__main__":
    main()
