from __future__ import annotations

import numpy as np
import pandas as pd

from concept_drift_ids.retrospective_scenario_audit import (
    _canonical_row_signature,
    _deterministic_positions,
    _exact_duplicate_excess,
    _training_seen_mask,
)


def test_deterministic_positions_cover_requested_range() -> None:
    out = _deterministic_positions(10, 4)
    np.testing.assert_array_equal(out, np.array([0, 2, 5, 7], dtype=np.int64))


def test_canonical_signature_treats_nan_as_equal_and_normalizes_zero() -> None:
    a = np.array([np.nan, -0.0, 1.0])
    b = np.array([np.nan, 0.0, 1.0])
    assert _canonical_row_signature(a) == _canonical_row_signature(b)


def test_exact_duplicate_excess_verifies_patterns() -> None:
    frame = pd.DataFrame({
        "a": [1.0, 1.0, 2.0, 2.0, 2.0],
        "b": [3.0, 3.0, 4.0, 4.0, 5.0],
    })
    excess, _ = _exact_duplicate_excess(frame)
    assert excess == 2


def test_training_seen_mask_is_exact_feature_pattern_based() -> None:
    training = pd.DataFrame({"a": [1.0, 2.0], "b": [3.0, np.nan]})
    target = pd.DataFrame({"a": [1.0, 2.0, 2.0], "b": [3.0, np.nan, 4.0]})
    np.testing.assert_array_equal(
        _training_seen_mask(training, target),
        np.array([True, True, False]),
    )
