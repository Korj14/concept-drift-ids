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
    PROJECT_ROOT / "data" / "manifests" / "sudden_benign_v1_preprocessing_v1.json"
)


@dataclass
class FittedPreprocessor:
    scenario_id: str
    scenario_version: int
    feature_columns: tuple[str, ...]
    training_rows: int
    imputer: SimpleImputer
    scaler: StandardScaler


def _require_python_3119(expected: str) -> None:
    actual = platform.python_version()
    if expected != "3.11.9" or actual != "3.11.9":
        raise RuntimeError(
            "Stage 3 requires Python 3.11.9 exactly.\n"
            f"Manifest: {expected}\nRuntime:  {actual}"
        )


def _matrix(
    frame: pd.DataFrame,
    features: tuple[str, ...],
    *,
    context: str,
) -> np.ndarray:
    if tuple(map(str, frame.columns)) != features or len(features) != 77:
        raise ValueError(
            f"{context} feature columns/order do not match the frozen 77-feature contract."
        )

    matrix = frame.to_numpy(dtype=np.float64, copy=True)
    if matrix.shape[1] != 77:
        raise ValueError(f"{context} has unexpected shape {matrix.shape}.")
    if np.isinf(matrix).any():
        raise ValueError(
            f"{context} contains infinity; Stage 1 must convert infinity to NaN."
        )
    return matrix


def fit_scenario_preprocessor(
    scenario: SuddenBenignScenario,
) -> FittedPreprocessor:
    """Fit median imputation and StandardScaler on training only."""
    manifest = scenario.manifest
    _require_python_3119(manifest["environment"]["python_version"])

    features = tuple(manifest["feature_schema"]["feature_columns"])
    matrix = _matrix(scenario.training.X, features, context="training")

    all_missing = np.isnan(matrix).all(axis=0)
    if all_missing.any():
        names = [features[i] for i in np.flatnonzero(all_missing)]
        raise ValueError(f"Training contains all-missing features: {names}")

    imputer = SimpleImputer(
        strategy="median",
        copy=False,
        add_indicator=False,
        keep_empty_features=False,
    )
    imputed = np.asarray(imputer.fit_transform(matrix), dtype=np.float64)
    if imputed.shape != matrix.shape or not np.isfinite(imputed).all():
        raise AssertionError("Training imputation changed shape or left non-finite values.")

    scaler = StandardScaler(copy=False, with_mean=True, with_std=True)
    scaler.fit(imputed)

    for name, values in {
        "mean_": scaler.mean_,
        "var_": scaler.var_,
        "scale_": scaler.scale_,
    }.items():
        if not np.isfinite(np.asarray(values, dtype=np.float64)).all():
            raise AssertionError(f"Scaler {name} contains non-finite values.")

    if int(scaler.n_features_in_) != 77:
        raise AssertionError("Scaler was not fitted on exactly 77 features.")

    return FittedPreprocessor(
        scenario_id=str(manifest["scenario_id"]),
        scenario_version=int(manifest["scenario_version"]),
        feature_columns=features,
        training_rows=len(scenario.training.X),
        imputer=imputer,
        scaler=scaler,
    )


def transform_features(
    preprocessor: FittedPreprocessor,
    frame: pd.DataFrame,
    *,
    context: str,
) -> np.ndarray:
    """Apply frozen training-fitted preprocessing and return float64."""
    matrix = _matrix(frame, preprocessor.feature_columns, context=context)
    transformed = preprocessor.imputer.transform(matrix)
    transformed = preprocessor.scaler.transform(transformed)
    transformed = np.ascontiguousarray(transformed, dtype=np.float64)

    if transformed.shape != matrix.shape or not np.isfinite(transformed).all():
        raise AssertionError(
            f"{context} preprocessing changed shape or left non-finite values."
        )
    return transformed


def transform_partition(
    preprocessor: FittedPreprocessor,
    partition: ScenarioPartition,
) -> np.ndarray:
    return transform_features(preprocessor, partition.X, context=partition.name)


def validate_frozen_transforms(
    preprocessor: FittedPreprocessor,
    scenario: SuddenBenignScenario,
) -> dict[str, dict[str, Any]]:
    """Transform partitions serially so validation does not retain large copies."""
    summary: dict[str, dict[str, Any]] = {}
    for name in ("training", "development", "pre_drift", "post_drift"):
        transformed = transform_partition(preprocessor, scenario.partition(name))
        summary[name] = {
            "rows": int(transformed.shape[0]),
            "features": int(transformed.shape[1]),
            "dtype": str(transformed.dtype),
            "all_finite": bool(np.isfinite(transformed).all()),
        }
        del transformed
    return summary


def _json_hash(payload: Any) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _float_list(values: Any, *, field: str) -> list[float]:
    array = np.asarray(values, dtype=np.float64).reshape(-1)
    if not np.isfinite(array).all():
        raise ValueError(f"Cannot serialize non-finite fitted state: {field}.")
    return [float(value) for value in array]


def _json_number_or_list(value: Any) -> int | float | list[int] | list[float]:
    array = np.asarray(value)
    if array.ndim == 0:
        scalar = array.item()
        return int(scalar) if isinstance(scalar, (int, np.integer)) else float(scalar)
    if np.issubdtype(array.dtype, np.integer):
        return [int(value) for value in array.reshape(-1)]
    return [float(value) for value in array.astype(np.float64).reshape(-1)]


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
    """Build the small JSON audit artifact for the fitted training-only state."""
    _require_python_3119(manifest["environment"]["python_version"])

    if (
        preprocessor.scenario_id != manifest["scenario_id"]
        or preprocessor.scenario_version != int(manifest["scenario_version"])
    ):
        raise ValueError("Preprocessor and scenario manifest do not match.")

    training_identity = {
        "scenario_id": manifest["scenario_id"],
        "scenario_version": manifest["scenario_version"],
        "rows": manifest["partitions"]["training"]["rows"],
        "components": manifest["partitions"]["training"]["components"],
        "label_counts": manifest["partitions"]["training"]["label_counts"],
        "feature_columns": manifest["feature_schema"]["feature_columns"],
    }

    state: dict[str, Any] = {
        "artifact_format_version": 1,
        "scenario": {
            "scenario_id": manifest["scenario_id"],
            "scenario_version": int(manifest["scenario_version"]),
            "scenario_manifest_file": _display_path(manifest_path),
            "scenario_manifest_sha256": sha256_file(manifest_path),
            "scenario_manifest_canonical_sha256": sha256_canonical_json(manifest_path),
        },
        "training_fit_scope": {
            "partition": "training",
            "rows": int(preprocessor.training_rows),
            "identity_sha256": _json_hash(training_identity),
            "development_used_for_fit": False,
            "pre_drift_used_for_fit": False,
            "post_drift_used_for_fit": False,
        },
        "feature_schema": {
            "count": 77,
            "ordered_columns": list(preprocessor.feature_columns),
        },
        "imputer": {
            "class": "sklearn.impute.SimpleImputer",
            "strategy": "median",
            "add_indicator": False,
            "keep_empty_features": False,
            "statistics": _float_list(
                preprocessor.imputer.statistics_,
                field="imputer.statistics_",
            ),
        },
        "scaler": {
            "class": "sklearn.preprocessing.StandardScaler",
            "with_mean": True,
            "with_std": True,
            "mean": _float_list(preprocessor.scaler.mean_, field="scaler.mean_"),
            "var": _float_list(preprocessor.scaler.var_, field="scaler.var_"),
            "scale": _float_list(preprocessor.scaler.scale_, field="scaler.scale_"),
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
            "requirements_lock_file": manifest["environment"]["requirements_lock_file"],
            "requirements_lock_sha256": manifest["environment"][
                "requirements_lock_sha256"
            ],
            "requirements_lock_normalized_text_sha256": manifest["environment"][
                "requirements_lock_normalized_text_sha256"
            ],
        },
        "implementation": {
            "file": _display_path(Path(__file__)),
            "normalized_text_sha256": sha256_normalized_text(Path(__file__)),
        },
    }
    state["core_state_sha256"] = _json_hash(state)
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
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as file:
        json.dump(state, file, indent=2, ensure_ascii=False, allow_nan=False)
        file.write("\n")
    return state


def load_preprocessing_state(
    path: Path = DEFAULT_STATE_PATH,
) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Preprocessing state artifact not found:\n{path}")

    with path.open("r", encoding="utf-8") as file:
        state = json.load(file)

    stored_hash = state.get("core_state_sha256")
    core = dict(state)
    core.pop("core_state_sha256", None)
    if not isinstance(stored_hash, str) or _json_hash(core) != stored_hash:
        raise ValueError("Preprocessing state artifact content hash mismatch.")
    return state


def main() -> None:
    scenario = load_scenario()
    fitted = fit_scenario_preprocessor(scenario)
    summary = validate_frozen_transforms(fitted, scenario)
    state = persist_preprocessing_state(fitted, scenario.manifest)

    print("Stage 3A preprocessing validation")
    for name, details in summary.items():
        print(
            f"{name:12s} rows={details['rows']:,} "
            f"features={details['features']} dtype={details['dtype']} "
            f"finite={details['all_finite']}"
        )
    print(f"state={DEFAULT_STATE_PATH}")
    print(f"state_hash={state['core_state_sha256']}")


if __name__ == "__main__":
    main()
