from __future__ import annotations

import hashlib
import json
import platform
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler

from concept_drift_ids.scenario_loader import (
    DEFAULT_MANIFEST_PATH,
    PROJECT_ROOT,
    ScenarioPartition,
    SuddenBenignScenario,
    load_scenario,
)
from concept_drift_ids.scenario_manifest import (
    sha256_canonical_json,
    sha256_file,
    sha256_normalized_text,
)


DEFAULT_STATE_PATH = (
    PROJECT_ROOT
    / "data"
    / "manifests"
    / "sudden_benign_v1_preprocessing_v1.json"
)
REQUIREMENTS_LOCK_PATH = PROJECT_ROOT / "requirements-lock.txt"


@dataclass
class FittedPreprocessor:
    """Training-fitted preprocessing state shared by every system."""

    scenario_id: str
    scenario_version: int
    feature_columns: tuple[str, ...]
    training_rows: int
    imputer: SimpleImputer
    scaler: StandardScaler


def _assert_python_contract(expected_version: str) -> None:
    actual = platform.python_version()
    if expected_version != "3.11.9":
        raise RuntimeError(
            "The scenario manifest no longer freezes Python 3.11.9. "
            f"Found: {expected_version}"
        )
    if actual != expected_version:
        raise RuntimeError(
            "Unexpected Python version for frozen Stage-3 preprocessing.\n"
            f"Expected: {expected_version}\n"
            f"Actual:   {actual}"
        )


def _assert_feature_contract(
    frame: pd.DataFrame,
    feature_columns: tuple[str, ...],
    *,
    context: str,
) -> None:
    actual = tuple(str(column) for column in frame.columns)
    if actual != feature_columns:
        raise ValueError(
            f"{context} feature columns/order do not match the frozen 77-feature contract."
        )

    if len(actual) != 77:
        raise ValueError(
            f"{context} must contain exactly 77 model features; found {len(actual)}."
        )


def _working_matrix(
    frame: pd.DataFrame,
    feature_columns: tuple[str, ...],
    *,
    context: str,
) -> np.ndarray:
    _assert_feature_contract(
        frame,
        feature_columns,
        context=context,
    )

    matrix = frame.to_numpy(
        dtype=np.float64,
        copy=True,
    )

    if matrix.ndim != 2 or matrix.shape[1] != 77:
        raise ValueError(
            f"{context} produced an unexpected feature matrix shape: {matrix.shape}."
        )

    if np.isinf(matrix).any():
        raise ValueError(
            f"{context} contains infinity. Stage-1 structural preprocessing "
            "must convert +/- infinity to NaN before Stage 3."
        )

    return matrix


def fit_scenario_preprocessor(
    scenario: SuddenBenignScenario,
) -> FittedPreprocessor:
    """
    Fit the initial imputer and scaler using the frozen training partition only.

    No development, pre-drift, or post-drift values are consulted.
    """
    manifest = scenario.manifest
    expected_python = manifest["environment"]["python_version"]
    _assert_python_contract(expected_python)

    training = scenario.training
    feature_columns = tuple(manifest["feature_schema"]["feature_columns"])

    if training.name != "training":
        raise ValueError("Preprocessing must be fitted from the training partition.")

    matrix = _working_matrix(
        training.X,
        feature_columns,
        context="training",
    )

    all_missing_mask = np.isnan(matrix).all(axis=0)
    if all_missing_mask.any():
        missing_features = [
            feature_columns[index]
            for index in np.flatnonzero(all_missing_mask)
        ]
        raise ValueError(
            "Training contains all-missing model features; refusing to fit "
            f"the median imputer: {missing_features}"
        )

    # copy=False is an implementation/memory choice only. The working matrix
    # above is already an isolated float64 copy, so no scenario DataFrame is
    # mutated.
    imputer = SimpleImputer(
        strategy="median",
        copy=False,
        add_indicator=False,
        keep_empty_features=False,
    )

    imputed = imputer.fit_transform(matrix)
    if imputed.dtype != np.float64:
        imputed = np.asarray(imputed, dtype=np.float64)

    if imputed.shape != matrix.shape:
        raise AssertionError(
            "Median imputation changed the frozen feature dimensionality."
        )

    if not np.isfinite(imputed).all():
        raise AssertionError(
            "Training matrix is not finite after median imputation."
        )

    scaler = StandardScaler(
        copy=False,
        with_mean=True,
        with_std=True,
    )
    scaler.fit(imputed)

    if int(scaler.n_features_in_) != 77:
        raise AssertionError("Scaler was not fitted on exactly 77 features.")

    if not (
        np.isfinite(np.asarray(scaler.mean_, dtype=np.float64)).all()
        and np.isfinite(np.asarray(scaler.var_, dtype=np.float64)).all()
        and np.isfinite(np.asarray(scaler.scale_, dtype=np.float64)).all()
    ):
        raise AssertionError("Scaler fitted state contains non-finite values.")

    return FittedPreprocessor(
        scenario_id=str(manifest["scenario_id"]),
        scenario_version=int(manifest["scenario_version"]),
        feature_columns=feature_columns,
        training_rows=len(training.X),
        imputer=imputer,
        scaler=scaler,
    )


def transform_features(
    preprocessor: FittedPreprocessor,
    frame: pd.DataFrame,
    *,
    context: str,
) -> np.ndarray:
    """
    Apply frozen training-fitted preprocessing to one feature frame.

    Returns a new C-contiguous float64 NumPy array. The input DataFrame and
    fitted state are not modified.
    """
    matrix = _working_matrix(
        frame,
        preprocessor.feature_columns,
        context=context,
    )

    transformed = preprocessor.imputer.transform(matrix)
    transformed = preprocessor.scaler.transform(transformed)
    transformed = np.ascontiguousarray(
        transformed,
        dtype=np.float64,
    )

    if transformed.shape != matrix.shape:
        raise AssertionError(
            f"{context} preprocessing changed row or feature count."
        )

    if not np.isfinite(transformed).all():
        raise AssertionError(
            f"{context} contains non-finite values after frozen preprocessing."
        )

    return transformed


def transform_partition(
    preprocessor: FittedPreprocessor,
    partition: ScenarioPartition,
) -> np.ndarray:
    return transform_features(
        preprocessor,
        partition.X,
        context=partition.name,
    )


def validate_frozen_transforms(
    preprocessor: FittedPreprocessor,
    scenario: SuddenBenignScenario,
) -> dict[str, dict[str, Any]]:
    """
    Transform each partition serially to keep peak memory bounded.

    The returned summary contains only small structural facts; transformed
    matrices are intentionally not retained.
    """
    summary: dict[str, dict[str, Any]] = {}

    for partition_name in (
        "training",
        "development",
        "pre_drift",
        "post_drift",
    ):
        partition = scenario.partition(partition_name)
        transformed = transform_partition(
            preprocessor,
            partition,
        )

        summary[partition_name] = {
            "rows": int(transformed.shape[0]),
            "features": int(transformed.shape[1]),
            "dtype": str(transformed.dtype),
            "all_finite": bool(np.isfinite(transformed).all()),
        }

        del transformed

    return summary


def _canonical_json_sha256(payload: Any) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")

    return hashlib.sha256(encoded).hexdigest()


def _json_number_or_list(value: Any) -> int | float | list[int] | list[float]:
    array = np.asarray(value)

    if array.ndim == 0:
        scalar = array.item()
        if isinstance(scalar, (np.integer, int)):
            return int(scalar)
        return float(scalar)

    if np.issubdtype(array.dtype, np.integer):
        return [int(item) for item in array.reshape(-1)]
    return [float(item) for item in array.astype(np.float64).reshape(-1)]


def _finite_float_list(values: Any, *, field: str) -> list[float]:
    array = np.asarray(values, dtype=np.float64).reshape(-1)
    if not np.isfinite(array).all():
        raise ValueError(f"Cannot serialize non-finite fitted state: {field}.")
    return [float(value) for value in array]


def _display_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(PROJECT_ROOT.resolve()).as_posix()
    except ValueError:
        return resolved.as_posix()


def build_preprocessing_state(
    preprocessor: FittedPreprocessor,
    manifest: dict,
    *,
    manifest_path: Path = DEFAULT_MANIFEST_PATH,
) -> dict[str, Any]:
    """
    Build the small human-readable audit artifact for fitted preprocessing.

    The JSON is evidence/provenance, not a pickle-based executable object.
    Runtime preprocessing is reconstructed deterministically from code + data.
    """
    _assert_python_contract(manifest["environment"]["python_version"])

    if preprocessor.scenario_id != manifest["scenario_id"]:
        raise ValueError("Preprocessor scenario_id does not match the manifest.")
    if preprocessor.scenario_version != int(manifest["scenario_version"]):
        raise ValueError("Preprocessor scenario_version does not match the manifest.")

    training_identity = {
        "scenario_id": manifest["scenario_id"],
        "scenario_version": manifest["scenario_version"],
        "rows": manifest["partitions"]["training"]["rows"],
        "components": manifest["partitions"]["training"]["components"],
        "label_counts": manifest["partitions"]["training"]["label_counts"],
        "feature_columns": manifest["feature_schema"]["feature_columns"],
    }

    implementation_path = Path(__file__).resolve()

    state: dict[str, Any] = {
        "artifact_format_version": 1,
        "scenario": {
            "scenario_id": manifest["scenario_id"],
            "scenario_version": int(manifest["scenario_version"]),
            "scenario_manifest_file": _display_path(manifest_path),
            "scenario_manifest_sha256": sha256_file(manifest_path),
            "scenario_manifest_canonical_sha256": sha256_canonical_json(
                manifest_path
            ),
        },
        "training_fit_scope": {
            "partition": "training",
            "rows": int(preprocessor.training_rows),
            "identity_sha256": _canonical_json_sha256(training_identity),
            "development_used_for_fit": False,
            "pre_drift_used_for_fit": False,
            "post_drift_used_for_fit": False,
        },
        "feature_schema": {
            "count": len(preprocessor.feature_columns),
            "ordered_columns": list(preprocessor.feature_columns),
        },
        "imputer": {
            "class": "sklearn.impute.SimpleImputer",
            "strategy": "median",
            "add_indicator": False,
            "keep_empty_features": False,
            "statistics": _finite_float_list(
                preprocessor.imputer.statistics_,
                field="imputer.statistics_",
            ),
        },
        "scaler": {
            "class": "sklearn.preprocessing.StandardScaler",
            "with_mean": True,
            "with_std": True,
            "mean": _finite_float_list(
                preprocessor.scaler.mean_,
                field="scaler.mean_",
            ),
            "var": _finite_float_list(
                preprocessor.scaler.var_,
                field="scaler.var_",
            ),
            "scale": _finite_float_list(
                preprocessor.scaler.scale_,
                field="scaler.scale_",
            ),
            "n_features_in": int(preprocessor.scaler.n_features_in_),
            "n_samples_seen": _json_number_or_list(
                preprocessor.scaler.n_samples_seen_
            ),
        },
        "dtype_policy": {
            "shared_preprocessing_output": "float64",
            "pytorch_tensor_boundary": "float32",
        },
        "environment": {
            "python_version": platform.python_version(),
            "requirements_lock_file": manifest["environment"][
                "requirements_lock_file"
            ],
            "requirements_lock_sha256": manifest["environment"][
                "requirements_lock_sha256"
            ],
            "requirements_lock_normalized_text_sha256": manifest[
                "environment"
            ]["requirements_lock_normalized_text_sha256"],
        },
        "implementation": {
            "file": _display_path(implementation_path),
            "normalized_text_sha256": sha256_normalized_text(
                implementation_path
            ),
        },
    }

    state["core_state_sha256"] = _canonical_json_sha256(state)
    return state


def persist_preprocessing_state(
    preprocessor: FittedPreprocessor,
    manifest: dict,
    *,
    path: Path = DEFAULT_STATE_PATH,
    manifest_path: Path = DEFAULT_MANIFEST_PATH,
) -> dict[str, Any]:
    state = build_preprocessing_state(
        preprocessor,
        manifest,
        manifest_path=manifest_path,
    )

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with path.open(
        "w",
        encoding="utf-8",
        newline="\n",
    ) as file:
        json.dump(
            state,
            file,
            indent=2,
            ensure_ascii=False,
            allow_nan=False,
        )
        file.write("\n")

    return state


def load_preprocessing_state(path: Path = DEFAULT_STATE_PATH) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Preprocessing state artifact not found:\n{path}")

    with path.open("r", encoding="utf-8") as file:
        state = json.load(file)

    stored_hash = state.get("core_state_sha256")
    if not isinstance(stored_hash, str):
        raise ValueError("Preprocessing state artifact is missing core_state_sha256.")

    core = dict(state)
    core.pop("core_state_sha256", None)

    actual_hash = _canonical_json_sha256(core)
    if actual_hash != stored_hash:
        raise ValueError(
            "Preprocessing state artifact content hash mismatch.\n"
            f"Expected: {stored_hash}\nActual:   {actual_hash}"
        )

    return state


def main() -> None:
    scenario = load_scenario()

    print("=" * 72)
    print("STAGE 3A TRAINING-ONLY PREPROCESSING")
    print("=" * 72)

    fitted = fit_scenario_preprocessor(scenario)

    print("Validating frozen transforms serially...")
    summary = validate_frozen_transforms(
        fitted,
        scenario,
    )

    print("Persisting preprocessing state...")
    state = persist_preprocessing_state(
        fitted,
        scenario.manifest,
    )

    for partition_name, details in summary.items():
        print(
            f"{partition_name:12s} "
            f"rows={details['rows']:,} "
            f"features={details['features']} "
            f"dtype={details['dtype']} "
            f"finite={details['all_finite']}"
        )

    print(f"State: {DEFAULT_STATE_PATH}")
    print(f"State hash: {state['core_state_sha256']}")


if __name__ == "__main__":
    main()
