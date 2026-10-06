from __future__ import annotations

import json
import platform
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import numpy as np
import pandas as pd

from concept_drift_ids.scenario_manifest import (
    deterministic_positions,
    sha256_int64_array,
    sha256_int64_pairs,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
INTERIM_DIR = PROJECT_ROOT / "data" / "interim" / "cicids2017"
DEFAULT_MANIFEST_PATH = (
    PROJECT_ROOT / "data" / "manifests" / "sudden_benign_v1.json"
)

PartitionName = Literal["training", "development", "pre_drift", "post_drift"]

BASE_METADATA_COLUMNS = ("source_file", "source_order", "row_in_source")
PROVENANCE_COLUMNS = (
    "scenario_partition",
    "scenario_row",
    "source_file",
    "source_order",
    "row_in_source",
    "template_source_file",
    "template_source_order",
    "template_row_in_source",
    "synthetic_replacement",
)


@dataclass
class ScenarioPartition:
    name: PartitionName
    X: pd.DataFrame
    y: pd.Series
    labels: pd.Series
    provenance: pd.DataFrame


@dataclass
class SuddenBenignScenario:
    manifest: dict
    feature_columns: tuple[str, ...]
    training: ScenarioPartition
    development: ScenarioPartition
    pre_drift: ScenarioPartition
    post_drift: ScenarioPartition

    def partition(self, name: PartitionName) -> ScenarioPartition:
        return getattr(self, name)


def load_manifest(path: Path = DEFAULT_MANIFEST_PATH) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Scenario manifest not found:\n{path}")

    with path.open("r", encoding="utf-8") as file:
        manifest = json.load(file)

    _validate_manifest(manifest)
    return manifest


def _validate_manifest(manifest: dict) -> None:
    if manifest.get("scenario_id") != "cicids2017_sudden_benign_v1":
        raise ValueError("Unexpected scenario_id.")
    if manifest.get("scenario_version") != 1:
        raise ValueError("Unexpected scenario_version.")
    if manifest.get("task") != "binary_intrusion_detection":
        raise ValueError("Unexpected scenario task.")

    expected_python = manifest.get("environment", {}).get("python_version")
    actual_python = platform.python_version()
    if expected_python != "3.11.9" or actual_python != "3.11.9":
        raise RuntimeError(
            "Frozen scenario reconstruction requires Python 3.11.9 exactly.\n"
            f"Manifest: {expected_python}\nRuntime:  {actual_python}"
        )

    if manifest.get("binary_target_mapping") != {
        "BENIGN": 0,
        "all_other_labels": 1,
    }:
        raise ValueError("Unexpected binary target mapping.")

    schema = manifest.get("feature_schema", {})
    features = schema.get("feature_columns", [])
    if schema.get("model_feature_count") != 77 or len(features) != 77:
        raise ValueError("Scenario manifest must define exactly 77 model features.")
    if len(set(features)) != 77:
        raise ValueError("Scenario manifest contains duplicate model features.")

    forbidden = {"Label", *BASE_METADATA_COLUMNS}
    if forbidden.intersection(features):
        raise ValueError("Target/metadata fields appear in model features.")
    if not forbidden.issubset(set(schema.get("model_excludes", []))):
        raise ValueError("Scenario manifest does not exclude required metadata/target fields.")

    chronology = manifest.get("chronology", {})
    if (
        chronology.get("type") != "pseudo-chronological"
        or chronology.get("timestamps_available") is not False
    ):
        raise ValueError("Unexpected chronology contract.")

    construction = manifest.get("construction", {})
    if (
        construction.get("drift_type") != "benign_source_regime_covariate_shift"
        or construction.get("natural_production_drift_claim") is not False
    ):
        raise ValueError("Unexpected drift-construction contract.")

    policy = manifest.get("data_quality_policy", {})
    if policy.get("duplicate_rows", {}).get("primary_policy") != "retain":
        raise ValueError("Duplicate-row policy changed.")
    if (
        policy.get("representation_level_label_conflicts", {}).get("primary_policy")
        != "retain_original_rows_and_labels"
    ):
        raise ValueError("Representation-conflict policy changed.")


def _required_columns(manifest: dict) -> list[str]:
    return [
        *BASE_METADATA_COLUMNS,
        *manifest["feature_schema"]["feature_columns"],
        "Label",
    ]


def _read_source(manifest: dict, source_file: str) -> pd.DataFrame:
    path = INTERIM_DIR / f"{Path(source_file).stem}.csv.gz"
    if not path.exists():
        raise FileNotFoundError(
            f"Required Stage-1 interim file not found:\n{path}\n"
            "Run the frozen Stage-1 structural preprocessing first."
        )

    columns = _required_columns(manifest)
    frame = pd.read_csv(path, usecols=columns, low_memory=False).loc[:, columns]

    if (
        frame["source_file"].astype(str).nunique(dropna=False) != 1
        or frame["source_file"].astype(str).iloc[0] != source_file
    ):
        raise ValueError(f"source_file metadata mismatch for {source_file}.")

    row_ids = frame["row_in_source"].to_numpy(dtype=np.int64, copy=False)
    if not np.array_equal(row_ids, np.arange(len(frame), dtype=np.int64)):
        raise ValueError(f"row_in_source is not contiguous for {source_file}.")
    if frame["Label"].isna().any():
        raise ValueError(f"Missing labels found in {source_file}.")
    return frame


def _slice(
    manifest: dict,
    *,
    source_file: str,
    source_order: int,
    start: int,
    end: int,
) -> pd.DataFrame:
    frame = _read_source(manifest, source_file)
    if start < 0 or end < start or end > len(frame):
        raise ValueError(f"Invalid slice [{start}:{end}) for {source_file}.")

    orders = frame["source_order"].unique()
    if len(orders) != 1 or int(orders[0]) != int(source_order):
        raise ValueError(f"source_order metadata mismatch for {source_file}.")
    return frame.iloc[start:end].copy()


def _provenance(
    frame: pd.DataFrame,
    *,
    name: PartitionName,
    template: pd.DataFrame | None = None,
    synthetic: np.ndarray | None = None,
) -> pd.DataFrame:
    template = frame if template is None else template
    if len(template) != len(frame):
        raise ValueError("Template and reconstructed partition lengths differ.")

    synthetic = (
        np.zeros(len(frame), dtype=bool)
        if synthetic is None
        else np.asarray(synthetic, dtype=bool)
    )
    if len(synthetic) != len(frame):
        raise ValueError("Synthetic-replacement mask length mismatch.")

    result = pd.DataFrame(
        {
            "scenario_partition": name,
            "scenario_row": np.arange(len(frame), dtype=np.int64),
            "source_file": frame["source_file"].astype(str).to_numpy(),
            "source_order": frame["source_order"].to_numpy(dtype=np.int64),
            "row_in_source": frame["row_in_source"].to_numpy(dtype=np.int64),
            "template_source_file": template["source_file"].astype(str).to_numpy(),
            "template_source_order": template["source_order"].to_numpy(
                dtype=np.int64
            ),
            "template_row_in_source": template["row_in_source"].to_numpy(
                dtype=np.int64
            ),
            "synthetic_replacement": synthetic,
        }
    )
    return result.loc[:, list(PROVENANCE_COLUMNS)]


def _partition(
    manifest: dict,
    *,
    name: PartitionName,
    frame: pd.DataFrame,
    template: pd.DataFrame | None = None,
    synthetic: np.ndarray | None = None,
) -> ScenarioPartition:
    features = manifest["feature_schema"]["feature_columns"]
    labels = frame["Label"].astype("string").copy()
    labels.name = "Label"
    y = labels.ne("BENIGN").astype(np.int8)
    y.name = "binary_target"

    partition = ScenarioPartition(
        name=name,
        X=frame.loc[:, features].copy(),
        y=y,
        labels=labels,
        provenance=_provenance(
            frame,
            name=name,
            template=template,
            synthetic=synthetic,
        ),
    )
    _validate_partition(manifest, partition)
    return partition


def _validate_partition(manifest: dict, partition: ScenarioPartition) -> None:
    spec = manifest["partitions"][partition.name]
    expected_rows = int(spec["rows"])

    if {
        len(partition.X),
        len(partition.y),
        len(partition.labels),
        len(partition.provenance),
    } != {expected_rows}:
        raise AssertionError(f"{partition.name} row count changed.")

    features = manifest["feature_schema"]["feature_columns"]
    if list(partition.X.columns) != features:
        raise AssertionError(f"{partition.name} feature order changed.")

    expected_labels = {str(k): int(v) for k, v in spec["label_counts"].items()}
    actual_labels = {
        str(k): int(v) for k, v in partition.labels.value_counts().items()
    }
    if actual_labels != expected_labels:
        raise AssertionError(
            f"{partition.name} label counts changed.\n"
            f"Expected: {expected_labels}\nActual:   {actual_labels}"
        )

    expected_binary = {k: int(v) for k, v in spec["binary_counts"].items()}
    actual_binary = {
        "benign": int((partition.y == 0).sum()),
        "attack": int((partition.y == 1).sum()),
        "total": len(partition.y),
    }
    if actual_binary != expected_binary:
        raise AssertionError(f"{partition.name} binary counts changed.")

    scenario_rows = partition.provenance["scenario_row"].to_numpy(dtype=np.int64)
    if not np.array_equal(scenario_rows, np.arange(expected_rows, dtype=np.int64)):
        raise AssertionError(f"{partition.name} scenario_row is not contiguous.")


def _training(manifest: dict) -> ScenarioPartition:
    frames = [
        _slice(
            manifest,
            source_file=part["source_file"],
            source_order=int(part["source_order"]),
            start=int(part["row_start_inclusive"]),
            end=int(part["row_end_exclusive"]),
        )
        for part in manifest["partitions"]["training"]["components"]
    ]
    return _partition(
        manifest,
        name="training",
        frame=pd.concat(frames, ignore_index=True, copy=False),
    )


def _simple(
    manifest: dict,
    name: Literal["development", "pre_drift"],
) -> ScenarioPartition:
    spec = manifest["partitions"][name]
    frame = _slice(
        manifest,
        source_file=spec["source_file"],
        source_order=int(spec["source_order"]),
        start=int(spec["row_start_inclusive"]),
        end=int(spec["row_end_exclusive"]),
    )

    if name == "pre_drift":
        for label, expected in spec.get("excluded_labels", {}).items():
            actual = int(frame["Label"].eq(label).sum())
            if actual != int(expected):
                raise AssertionError(
                    f"Excluded-label count changed for {label}: "
                    f"expected {expected}, got {actual}."
                )
        frame = frame.loc[
            ~frame["Label"].isin(spec.get("excluded_labels", {}))
        ].copy()

    return _partition(manifest, name=name, frame=frame)


def _post_drift(manifest: dict) -> ScenarioPartition:
    spec = manifest["partitions"]["post_drift"]
    template_spec = spec["template"]
    replacement_spec = spec["benign_replacement"]

    template = _slice(
        manifest,
        source_file=template_spec["source_file"],
        source_order=int(template_spec["source_order"]),
        start=int(template_spec["row_start_inclusive"]),
        end=int(template_spec["row_end_exclusive"]),
    ).reset_index(drop=True)

    benign_label = replacement_spec["eligible_label"]
    attack_label = template_spec["retained_attack_label"]
    if set(template["Label"].astype(str).unique()) != {benign_label, attack_label}:
        raise AssertionError("Post-drift template label set changed.")

    benign_positions = np.flatnonzero(template["Label"].eq(benign_label).to_numpy())
    selected_rows = int(replacement_spec["selected_rows"])
    if len(benign_positions) != selected_rows:
        raise AssertionError("Post-template BENIGN slot count changed.")

    source = _read_source(manifest, replacement_spec["source_file"])
    orders = source["source_order"].unique()
    if len(orders) != 1 or int(orders[0]) != int(replacement_spec["source_order"]):
        raise AssertionError("Replacement source_order changed.")

    eligible = source.loc[source["Label"].eq(benign_label)].reset_index(drop=True)
    if len(eligible) != int(replacement_spec["eligible_rows"]):
        raise AssertionError("Eligible replacement-row count changed.")

    positions = deterministic_positions(len(eligible), selected_rows)
    selected = eligible.iloc[positions].reset_index(drop=True)

    selected_ids = selected["row_in_source"].to_numpy(dtype=np.int64, copy=True)
    template_ids = template.loc[
        benign_positions, "row_in_source"
    ].to_numpy(dtype=np.int64, copy=True)

    hashes = {
        "selected_source_row_id_sha256": sha256_int64_array(selected_ids),
        "template_benign_slot_row_id_sha256": sha256_int64_array(template_ids),
        "slot_to_source_row_id_mapping_sha256": sha256_int64_pairs(
            template_ids, selected_ids
        ),
    }
    for field, actual in hashes.items():
        if actual != replacement_spec[field]:
            raise AssertionError(
                f"Frozen post-drift mapping failed for {field}.\n"
                f"Expected: {replacement_spec[field]}\nActual:   {actual}"
            )

    reconstructed = template.copy()
    for column in reconstructed.columns:
        reconstructed.iloc[
            benign_positions,
            reconstructed.columns.get_loc(column),
        ] = selected[column].to_numpy(copy=False)

    synthetic = np.zeros(len(template), dtype=bool)
    synthetic[benign_positions] = True

    return _partition(
        manifest,
        name="post_drift",
        frame=reconstructed,
        template=template,
        synthetic=synthetic,
    )


def load_partition(
    name: PartitionName,
    *,
    manifest_path: Path = DEFAULT_MANIFEST_PATH,
) -> ScenarioPartition:
    manifest = load_manifest(manifest_path)
    if name == "training":
        return _training(manifest)
    if name in {"development", "pre_drift"}:
        return _simple(manifest, name)
    if name == "post_drift":
        return _post_drift(manifest)
    raise ValueError(f"Unknown scenario partition: {name}")


def load_scenario(
    *,
    manifest_path: Path = DEFAULT_MANIFEST_PATH,
) -> SuddenBenignScenario:
    manifest = load_manifest(manifest_path)
    return SuddenBenignScenario(
        manifest=manifest,
        feature_columns=tuple(manifest["feature_schema"]["feature_columns"]),
        training=_training(manifest),
        development=_simple(manifest, "development"),
        pre_drift=_simple(manifest, "pre_drift"),
        post_drift=_post_drift(manifest),
    )
