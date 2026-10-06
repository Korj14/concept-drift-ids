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

PartitionName = Literal[
    "training",
    "development",
    "pre_drift",
    "post_drift",
]

BASE_METADATA_COLUMNS = (
    "source_file",
    "source_order",
    "row_in_source",
)

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
    """One reconstructed scenario partition with model data and audit metadata."""

    name: PartitionName
    X: pd.DataFrame
    y: pd.Series
    labels: pd.Series
    provenance: pd.DataFrame


@dataclass
class SuddenBenignScenario:
    """Frozen sudden-benign scenario reconstructed from its manifest."""

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

    _validate_manifest_contract(manifest)
    return manifest


def _validate_manifest_contract(manifest: dict) -> None:
    if manifest.get("scenario_id") != "cicids2017_sudden_benign_v1":
        raise ValueError("Unexpected scenario_id in scenario manifest.")

    if manifest.get("scenario_version") != 1:
        raise ValueError("Unexpected scenario_version in scenario manifest.")

    if manifest.get("task") != "binary_intrusion_detection":
        raise ValueError("Unexpected task in scenario manifest.")

    expected_python = manifest.get("environment", {}).get("python_version")
    if expected_python != "3.11.9":
        raise ValueError("Scenario manifest does not freeze Python 3.11.9.")
    if platform.python_version() != expected_python:
        raise RuntimeError(
            "Unexpected Python version for frozen scenario reconstruction.\n"
            f"Expected: {expected_python}\nActual:   {platform.python_version()}"
        )

    target_mapping = manifest.get("binary_target_mapping", {})
    if target_mapping != {"BENIGN": 0, "all_other_labels": 1}:
        raise ValueError("Unexpected binary target mapping in scenario manifest.")

    schema = manifest.get("feature_schema", {})
    feature_columns = schema.get("feature_columns", [])
    expected_count = schema.get("model_feature_count")

    if expected_count != 77 or len(feature_columns) != 77:
        raise ValueError("Scenario manifest must define exactly 77 model features.")

    if len(set(feature_columns)) != 77:
        raise ValueError("Scenario manifest contains duplicate model features.")

    forbidden = {"Label", *BASE_METADATA_COLUMNS}
    leaked = forbidden.intersection(feature_columns)
    if leaked:
        raise ValueError(
            "Target/metadata columns appear in the model feature list: "
            f"{sorted(leaked)}"
        )

    model_excludes = set(schema.get("model_excludes", []))
    if not forbidden.issubset(model_excludes):
        raise ValueError("Scenario manifest does not exclude required metadata/target fields.")

    chronology = manifest.get("chronology", {})
    if chronology.get("type") != "pseudo-chronological":
        raise ValueError("Unexpected chronology contract.")
    if chronology.get("timestamps_available") is not False:
        raise ValueError("The frozen scenario must not claim timestamp availability.")

    construction = manifest.get("construction", {})
    if construction.get("drift_type") != "benign_source_regime_covariate_shift":
        raise ValueError("Unexpected drift construction in scenario manifest.")
    if construction.get("natural_production_drift_claim") is not False:
        raise ValueError("The frozen scenario must not claim natural production drift.")

    policy = manifest.get("data_quality_policy", {})
    duplicates = policy.get("duplicate_rows", {})
    conflicts = policy.get("representation_level_label_conflicts", {})
    if duplicates.get("primary_policy") != "retain":
        raise ValueError("Primary duplicate-row policy must remain 'retain'.")
    if conflicts.get("primary_policy") != "retain_original_rows_and_labels":
        raise ValueError("Primary representation-conflict policy has changed.")


def _interim_path(source_file: str) -> Path:
    return INTERIM_DIR / f"{Path(source_file).stem}.csv.gz"


def _required_columns(manifest: dict) -> list[str]:
    return [
        *BASE_METADATA_COLUMNS,
        *manifest["feature_schema"]["feature_columns"],
        "Label",
    ]


def _read_source(manifest: dict, source_file: str) -> pd.DataFrame:
    path = _interim_path(source_file)
    if not path.exists():
        raise FileNotFoundError(
            "Required structurally preprocessed CICIDS2017 file not found:\n"
            f"{path}\n"
            "Run the frozen Stage-1 structural preprocessing first."
        )

    frame = pd.read_csv(
        path,
        usecols=_required_columns(manifest),
        low_memory=False,
    )

    expected_columns = _required_columns(manifest)
    missing = set(expected_columns).difference(frame.columns)
    if missing:
        raise ValueError(
            f"Required columns missing from {source_file}: {sorted(missing)}"
        )

    # read_csv/usecols does not guarantee requested-order output across all
    # pandas versions. Reorder explicitly to the frozen contract.
    frame = frame.loc[:, expected_columns]

    if frame["source_file"].astype(str).nunique(dropna=False) != 1:
        raise ValueError(f"Mixed source_file values found in {source_file}.")
    if frame["source_file"].astype(str).iloc[0] != source_file:
        raise ValueError(f"source_file metadata mismatch for {source_file}.")

    row_ids = frame["row_in_source"].to_numpy(dtype=np.int64, copy=False)
    expected_ids = np.arange(len(frame), dtype=np.int64)
    if not np.array_equal(row_ids, expected_ids):
        raise ValueError(f"row_in_source is not contiguous for {source_file}.")

    if frame["Label"].isna().any():
        raise ValueError(f"Missing labels found in {source_file}.")

    return frame


def _slice_source(
    manifest: dict,
    *,
    source_file: str,
    source_order: int,
    start: int,
    end: int,
) -> pd.DataFrame:
    frame = _read_source(manifest, source_file)

    if start < 0 or end < start or end > len(frame):
        raise ValueError(
            f"Invalid slice [{start}:{end}) for {source_file} with {len(frame)} rows."
        )

    source_orders = frame["source_order"].unique()
    if len(source_orders) != 1 or int(source_orders[0]) != int(source_order):
        raise ValueError(f"source_order metadata mismatch for {source_file}.")

    sliced = frame.iloc[start:end].copy()
    del frame
    return sliced


def _make_provenance(
    frame: pd.DataFrame,
    *,
    partition_name: PartitionName,
    template: pd.DataFrame | None = None,
    synthetic_replacement: np.ndarray | None = None,
) -> pd.DataFrame:
    provenance = frame.loc[:, list(BASE_METADATA_COLUMNS)].copy()
    provenance.insert(0, "scenario_row", np.arange(len(frame), dtype=np.int64))
    provenance.insert(0, "scenario_partition", partition_name)

    if template is None:
        template = frame

    if len(template) != len(frame):
        raise ValueError("Template and reconstructed frame lengths differ.")

    provenance["template_source_file"] = template["source_file"].astype(str).to_numpy()
    provenance["template_source_order"] = template["source_order"].to_numpy(
        dtype=np.int64,
        copy=False,
    )
    provenance["template_row_in_source"] = template["row_in_source"].to_numpy(
        dtype=np.int64,
        copy=False,
    )

    if synthetic_replacement is None:
        synthetic_replacement = np.zeros(len(frame), dtype=bool)

    if len(synthetic_replacement) != len(frame):
        raise ValueError("synthetic_replacement length does not match partition rows.")

    provenance["synthetic_replacement"] = np.asarray(
        synthetic_replacement,
        dtype=bool,
    )

    return provenance.loc[:, list(PROVENANCE_COLUMNS)]


def _to_partition(
    manifest: dict,
    *,
    name: PartitionName,
    frame: pd.DataFrame,
    template: pd.DataFrame | None = None,
    synthetic_replacement: np.ndarray | None = None,
) -> ScenarioPartition:
    feature_columns = manifest["feature_schema"]["feature_columns"]

    X = frame.loc[:, feature_columns].copy()
    labels = frame["Label"].astype("string").copy()
    labels.name = "Label"

    y = labels.ne("BENIGN").astype(np.int8)
    y.name = "binary_target"

    provenance = _make_provenance(
        frame,
        partition_name=name,
        template=template,
        synthetic_replacement=synthetic_replacement,
    )

    partition = ScenarioPartition(
        name=name,
        X=X,
        y=y,
        labels=labels,
        provenance=provenance,
    )
    _validate_partition(manifest, partition)
    return partition


def _validate_partition(manifest: dict, partition: ScenarioPartition) -> None:
    spec = manifest["partitions"][partition.name]
    expected_rows = int(spec["rows"])

    lengths = {
        len(partition.X),
        len(partition.y),
        len(partition.labels),
        len(partition.provenance),
    }
    if lengths != {expected_rows}:
        raise AssertionError(
            f"{partition.name} reconstructed lengths do not match {expected_rows}: {lengths}"
        )

    expected_features = manifest["feature_schema"]["feature_columns"]
    if list(partition.X.columns) != expected_features:
        raise AssertionError(f"{partition.name} feature order changed.")

    forbidden = {"Label", *BASE_METADATA_COLUMNS, *PROVENANCE_COLUMNS}
    leaked = forbidden.intersection(partition.X.columns)
    if leaked:
        raise AssertionError(
            f"{partition.name} metadata/target leakage into X: {sorted(leaked)}"
        )

    actual_label_counts = {
        str(label): int(count)
        for label, count in partition.labels.value_counts().sort_index().items()
    }
    expected_label_counts = {
        str(label): int(count)
        for label, count in sorted(spec["label_counts"].items())
    }
    if actual_label_counts != expected_label_counts:
        raise AssertionError(
            f"{partition.name} label counts changed.\n"
            f"Expected: {expected_label_counts}\nActual:   {actual_label_counts}"
        )

    actual_binary = {
        "benign": int((partition.y == 0).sum()),
        "attack": int((partition.y == 1).sum()),
        "total": int(len(partition.y)),
    }
    expected_binary = {key: int(value) for key, value in spec["binary_counts"].items()}
    if actual_binary != expected_binary:
        raise AssertionError(
            f"{partition.name} binary counts changed.\n"
            f"Expected: {expected_binary}\nActual:   {actual_binary}"
        )

    scenario_rows = partition.provenance["scenario_row"].to_numpy(
        dtype=np.int64,
        copy=False,
    )
    if not np.array_equal(scenario_rows, np.arange(expected_rows, dtype=np.int64)):
        raise AssertionError(f"{partition.name} scenario_row is not contiguous.")


def _load_training(manifest: dict) -> ScenarioPartition:
    components = []
    for component in manifest["partitions"]["training"]["components"]:
        components.append(
            _slice_source(
                manifest,
                source_file=component["source_file"],
                source_order=int(component["source_order"]),
                start=int(component["row_start_inclusive"]),
                end=int(component["row_end_exclusive"]),
            )
        )

    frame = pd.concat(components, axis=0, ignore_index=True, copy=False)
    del components
    return _to_partition(manifest, name="training", frame=frame)


def _load_simple_partition(
    manifest: dict,
    name: Literal["development", "pre_drift"],
) -> ScenarioPartition:
    spec = manifest["partitions"][name]
    frame = _slice_source(
        manifest,
        source_file=spec["source_file"],
        source_order=int(spec["source_order"]),
        start=int(spec["row_start_inclusive"]),
        end=int(spec["row_end_exclusive"]),
    )

    if name == "pre_drift":
        excluded = spec.get("excluded_labels", {})
        for label, expected_count in excluded.items():
            actual_count = int(frame["Label"].eq(label).sum())
            if actual_count != int(expected_count):
                raise AssertionError(
                    f"Excluded-label count changed for {label}: "
                    f"expected {expected_count}, got {actual_count}."
                )
        if excluded:
            frame = frame.loc[~frame["Label"].isin(excluded)].copy()

    return _to_partition(manifest, name=name, frame=frame)


def _load_post_drift(manifest: dict) -> ScenarioPartition:
    spec = manifest["partitions"]["post_drift"]
    template_spec = spec["template"]
    replacement_spec = spec["benign_replacement"]

    template = _slice_source(
        manifest,
        source_file=template_spec["source_file"],
        source_order=int(template_spec["source_order"]),
        start=int(template_spec["row_start_inclusive"]),
        end=int(template_spec["row_end_exclusive"]),
    ).reset_index(drop=True)

    retained_attack_label = template_spec["retained_attack_label"]
    benign_label = replacement_spec["eligible_label"]
    expected_template_labels = {benign_label, retained_attack_label}
    actual_template_labels = set(template["Label"].astype(str).unique())
    if actual_template_labels != expected_template_labels:
        raise AssertionError(
            "Post-drift template label set changed. "
            f"Expected {expected_template_labels}, got {actual_template_labels}."
        )

    benign_positions = np.flatnonzero(template["Label"].eq(benign_label).to_numpy())
    expected_replacements = int(replacement_spec["selected_rows"])
    if len(benign_positions) != expected_replacements:
        raise AssertionError(
            "Post-template BENIGN slot count changed. "
            f"Expected {expected_replacements}, got {len(benign_positions)}."
        )

    source = _read_source(manifest, replacement_spec["source_file"])
    source_orders = source["source_order"].unique()
    if (
        len(source_orders) != 1
        or int(source_orders[0]) != int(replacement_spec["source_order"])
    ):
        raise AssertionError("Post-drift replacement source_order changed.")

    eligible = source.loc[source["Label"].eq(benign_label)].reset_index(drop=True)
    del source

    if len(eligible) != int(replacement_spec["eligible_rows"]):
        raise AssertionError(
            "Post-drift eligible replacement-row count changed. "
            f"Expected {replacement_spec['eligible_rows']}, got {len(eligible)}."
        )

    selection_positions = deterministic_positions(
        total_rows=len(eligible),
        requested_rows=expected_replacements,
    )
    selected = eligible.iloc[selection_positions].reset_index(drop=True)
    del eligible

    selected_source_ids = selected["row_in_source"].to_numpy(
        dtype=np.int64,
        copy=True,
    )
    template_slot_ids = template.loc[
        benign_positions,
        "row_in_source",
    ].to_numpy(dtype=np.int64, copy=True)

    selected_hash = sha256_int64_array(selected_source_ids)
    slot_hash = sha256_int64_array(template_slot_ids)
    mapping_hash = sha256_int64_pairs(template_slot_ids, selected_source_ids)

    expected_hashes = {
        "selected_source_row_id_sha256": selected_hash,
        "template_benign_slot_row_id_sha256": slot_hash,
        "slot_to_source_row_id_mapping_sha256": mapping_hash,
    }
    for field, actual in expected_hashes.items():
        if actual != replacement_spec[field]:
            raise AssertionError(
                f"Frozen post-drift mapping invariant failed for {field}.\n"
                f"Expected: {replacement_spec[field]}\nActual:   {actual}"
            )

    reconstructed = template.copy()
    for column_index, column in enumerate(reconstructed.columns):
        reconstructed.iloc[benign_positions, column_index] = (
            selected[column].to_numpy(copy=False)
        )

    synthetic_replacement = np.zeros(len(template), dtype=bool)
    synthetic_replacement[benign_positions] = True

    return _to_partition(
        manifest,
        name="post_drift",
        frame=reconstructed,
        template=template,
        synthetic_replacement=synthetic_replacement,
    )


def load_partition(
    name: PartitionName,
    *,
    manifest_path: Path = DEFAULT_MANIFEST_PATH,
) -> ScenarioPartition:
    """Reconstruct one frozen scenario partition from Stage-1 interim data."""

    manifest = load_manifest(manifest_path)

    if name == "training":
        return _load_training(manifest)
    if name in {"development", "pre_drift"}:
        return _load_simple_partition(manifest, name)
    if name == "post_drift":
        return _load_post_drift(manifest)

    raise ValueError(f"Unknown scenario partition: {name}")


def load_scenario(
    *,
    manifest_path: Path = DEFAULT_MANIFEST_PATH,
) -> SuddenBenignScenario:
    """Reconstruct all four frozen partitions using one manifest contract."""

    manifest = load_manifest(manifest_path)
    return SuddenBenignScenario(
        manifest=manifest,
        feature_columns=tuple(manifest["feature_schema"]["feature_columns"]),
        training=_load_training(manifest),
        development=_load_simple_partition(manifest, "development"),
        pre_drift=_load_simple_partition(manifest, "pre_drift"),
        post_drift=_load_post_drift(manifest),
    )
