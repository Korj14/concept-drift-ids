from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from concept_drift_ids.model_preprocessing import (
    DEFAULT_STATE_PATH,
    load_preprocessing_state,
)


@dataclass(frozen=True)
class FrozenPreprocessing:
    feature_columns: tuple[str, ...]
    medians: np.ndarray
    means: np.ndarray
    scales: np.ndarray
    state_hash: str


def load_frozen_preprocessing(
    path: Path = DEFAULT_STATE_PATH,
) -> FrozenPreprocessing:
    """Load the accepted Stage-3A preprocessing state without refitting."""
    state = load_preprocessing_state(path)

    features = tuple(state["feature_schema"]["ordered_columns"])
    medians = np.asarray(state["imputer"]["statistics"], dtype=np.float64)
    means = np.asarray(state["scaler"]["mean"], dtype=np.float64)
    scales = np.asarray(state["scaler"]["scale"], dtype=np.float64)

    if len(features) != 77:
        raise ValueError("Frozen preprocessing must define exactly 77 features.")
    if any(array.shape != (77,) for array in (medians, means, scales)):
        raise ValueError("Frozen preprocessing statistics must each contain 77 values.")
    if not all(np.isfinite(array).all() for array in (medians, means, scales)):
        raise ValueError("Frozen preprocessing statistics contain non-finite values.")
    if np.any(scales <= 0):
        raise ValueError("Frozen preprocessing contains a non-positive scale.")

    return FrozenPreprocessing(
        feature_columns=features,
        medians=medians,
        means=means,
        scales=scales,
        state_hash=str(state["core_state_sha256"]),
    )


def transform_frame(
    frame: pd.DataFrame,
    state: FrozenPreprocessing,
    *,
    dtype: np.dtype = np.dtype("float32"),
    chunk_rows: int = 65_536,
) -> np.ndarray:
    """
    Apply the accepted training-only median/scaler state in bounded memory.

    The transform is mathematically identical to:
        impute NaN with training medians
        (x - training_mean) / training_scale
    """
    if tuple(map(str, frame.columns)) != state.feature_columns:
        raise ValueError("Feature columns/order do not match frozen preprocessing.")
    if chunk_rows <= 0:
        raise ValueError("chunk_rows must be positive.")

    dtype = np.dtype(dtype)
    if dtype not in {np.dtype("float32"), np.dtype("float64")}:
        raise ValueError("Only float32 and float64 outputs are supported.")

    output = np.empty((len(frame), 77), dtype=dtype)

    for start in range(0, len(frame), chunk_rows):
        stop = min(start + chunk_rows, len(frame))
        chunk = frame.iloc[start:stop].to_numpy(dtype=np.float64, copy=True)

        if np.isinf(chunk).any():
            raise ValueError("Input contains infinity; Stage 1 should have converted it to NaN.")

        missing_rows, missing_cols = np.where(np.isnan(chunk))
        if len(missing_rows):
            chunk[missing_rows, missing_cols] = state.medians[missing_cols]

        chunk -= state.means
        chunk /= state.scales

        if not np.isfinite(chunk).all():
            raise ValueError("Frozen preprocessing produced non-finite values.")

        output[start:stop] = chunk.astype(dtype, copy=False)

    return output
