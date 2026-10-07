from __future__ import annotations

import numpy as np
import pandas as pd

from concept_drift_ids.system_b_duplicate_robustness import (
    _exact_pattern_group_ids,
    _group_bootstrap_stability,
    _pattern_quality,
)


def test_exact_pattern_groups_preserve_nan_equality() -> None:
    frame = pd.DataFrame({
        "a": [1.0, 1.0, 2.0, 2.0],
        "b": [np.nan, np.nan, 3.0, 4.0],
    })
    groups = _exact_pattern_group_ids(frame)
    assert groups[0] == groups[1]
    assert groups[2] != groups[3]


def test_pattern_quality_equal_weights_unique_patterns_and_preserves_conflict() -> None:
    mask = np.array([True, True, True, False])
    y = np.array([0, 1, 1, 0], dtype=np.int8)
    neural = np.array([0, 0, 1, 0], dtype=np.int8)
    groups = np.array([0, 0, 1, 2], dtype=np.int64)
    out = _pattern_quality(
        mask,
        y_true=y,
        neural_decision=neural,
        consequent=1,
        group_ids=groups,
    )
    assert out["covered_count"] == 2
    assert out["support"] == 2 / 3
    # group 0 contributes 0.5 correctness, group 1 contributes 1.0
    assert out["class_precision"] == 0.75
    # group 0 neural correctness is 0; group 1 is 1
    assert out["neural_fidelity"] == 0.5


def test_group_bootstrap_stability_is_bounded() -> None:
    quality = {
        "group_active": np.array([True, True, False]),
        "group_label_correct": np.array([1.0, 1.0, 0.0]),
        "group_neural_correct": np.array([1.0, 1.0, 0.0]),
    }
    stability = _group_bootstrap_stability(
        quality,
        replicates=20,
        random_state=1,
        min_support=0.1,
        min_covered=1,
        min_precision=0.5,
        min_fidelity=0.5,
    )
    assert 0.0 <= stability <= 1.0
