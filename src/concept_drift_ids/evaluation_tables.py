from __future__ import annotations

import csv
from pathlib import Path
from typing import Any


def _write_csv(
    path: Path,
    fieldnames: list[str],
    rows: list[dict[str, Any]],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_evaluation_tables(
    results: dict[str, Any],
    output_dir: Path,
) -> dict[str, Path]:
    """
    Write plot-ready long/tidy tables from a system evaluation result.

    The schema is intentionally generic so later Systems B/C/D can append
    equivalent rows without reshaping System-A-specific JSON.
    """
    system_id = str(results["system_id"])
    scenario_id = str(results["scenario_id"])
    scenario_version = int(results["scenario_version"])

    seed_rows: list[dict[str, Any]] = []
    aggregate_rows: list[dict[str, Any]] = []

    for partition, payload in results["partitions"].items():
        for seed_result in payload["seed_results"]:
            for metric, value in seed_result["metrics"].items():
                seed_rows.append(
                    {
                        "system_id": system_id,
                        "scenario_id": scenario_id,
                        "scenario_version": scenario_version,
                        "partition": partition,
                        "seed": int(seed_result["seed"]),
                        "threshold": float(seed_result["threshold"]),
                        "metric": metric,
                        "value": float(value),
                    }
                )

        for metric, summary in payload["aggregate"].items():
            aggregate_rows.append(
                {
                    "system_id": system_id,
                    "scenario_id": scenario_id,
                    "scenario_version": scenario_version,
                    "partition": partition,
                    "metric": metric,
                    "n_seeds": int(summary["n"]),
                    "mean": float(summary["mean"]),
                    "std": float(summary["std"]),
                    "ci95_low": float(summary["ci95_low"]),
                    "ci95_high": float(summary["ci95_high"]),
                }
            )

    delta_rows: list[dict[str, Any]] = []
    for seed_delta in results["post_minus_pre"]["seed_deltas"]:
        for metric, value in seed_delta["metrics"].items():
            delta_rows.append(
                {
                    "system_id": system_id,
                    "scenario_id": scenario_id,
                    "scenario_version": scenario_version,
                    "from_partition": "pre_drift",
                    "to_partition": "post_drift",
                    "seed": int(seed_delta["seed"]),
                    "metric": metric,
                    "delta": float(value),
                }
            )

    aggregate_delta_rows: list[dict[str, Any]] = []
    for metric, summary in results["post_minus_pre"]["aggregate"].items():
        aggregate_delta_rows.append(
            {
                "system_id": system_id,
                "scenario_id": scenario_id,
                "scenario_version": scenario_version,
                "from_partition": "pre_drift",
                "to_partition": "post_drift",
                "metric": metric,
                "n_seeds": int(summary["n"]),
                "mean_delta": float(summary["mean"]),
                "std_delta": float(summary["std"]),
                "ci95_low": float(summary["ci95_low"]),
                "ci95_high": float(summary["ci95_high"]),
            }
        )

    paths = {
        "metrics_by_seed": output_dir / "metrics_by_seed.csv",
        "aggregate_metrics": output_dir / "aggregate_metrics.csv",
        "paired_deltas_by_seed": output_dir / "paired_deltas_by_seed.csv",
        "aggregate_paired_deltas": output_dir / "aggregate_paired_deltas.csv",
    }

    _write_csv(
        paths["metrics_by_seed"],
        [
            "system_id",
            "scenario_id",
            "scenario_version",
            "partition",
            "seed",
            "threshold",
            "metric",
            "value",
        ],
        seed_rows,
    )
    _write_csv(
        paths["aggregate_metrics"],
        [
            "system_id",
            "scenario_id",
            "scenario_version",
            "partition",
            "metric",
            "n_seeds",
            "mean",
            "std",
            "ci95_low",
            "ci95_high",
        ],
        aggregate_rows,
    )
    _write_csv(
        paths["paired_deltas_by_seed"],
        [
            "system_id",
            "scenario_id",
            "scenario_version",
            "from_partition",
            "to_partition",
            "seed",
            "metric",
            "delta",
        ],
        delta_rows,
    )
    _write_csv(
        paths["aggregate_paired_deltas"],
        [
            "system_id",
            "scenario_id",
            "scenario_version",
            "from_partition",
            "to_partition",
            "metric",
            "n_seeds",
            "mean_delta",
            "std_delta",
            "ci95_low",
            "ci95_high",
        ],
        aggregate_delta_rows,
    )
    return paths


def write_training_history_table(
    system_manifest: dict[str, Any],
    output_dir: Path,
) -> Path:
    """Write frozen development/training history in long reusable form."""
    rows: list[dict[str, Any]] = []

    for record in system_manifest["seed_records"]:
        seed = int(record["seed"])
        best_epoch = int(record["best_epoch"])
        for epoch_record in record["history"]:
            rows.append(
                {
                    "system_id": str(system_manifest["system_id"]),
                    "scenario_id": str(system_manifest["scenario_id"]),
                    "scenario_version": int(system_manifest["scenario_version"]),
                    "seed": seed,
                    "epoch": int(epoch_record["epoch"]),
                    "training_loss": float(epoch_record["training_loss"]),
                    "development_average_precision": float(
                        epoch_record["development_average_precision"]
                    ),
                    "is_best_epoch": int(epoch_record["epoch"]) == best_epoch,
                }
            )

    path = output_dir / "training_history.csv"
    _write_csv(
        path,
        [
            "system_id",
            "scenario_id",
            "scenario_version",
            "seed",
            "epoch",
            "training_loss",
            "development_average_precision",
            "is_best_epoch",
        ],
        rows,
    )
    return path
