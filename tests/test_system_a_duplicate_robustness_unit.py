from __future__ import annotations

import inspect

import numpy as np
import pandas as pd

from concept_drift_ids.system_a_duplicate_robustness import (
    _deduplicated_training_indices,
    build_pattern_dedup_teacher,
)


def test_dedup_indices_preserve_binary_label_conflicts() -> None:
    X = pd.DataFrame({
        "a": [1.0, 1.0, 1.0, 2.0],
        "b": [3.0, 3.0, 3.0, 4.0],
    })
    y = np.array([0, 0, 1, 0], dtype=np.int8)
    keep = _deduplicated_training_indices(X, y)
    np.testing.assert_array_equal(keep, np.array([0, 2, 3], dtype=np.int64))


def test_dedup_teacher_builder_does_not_request_held_out_partitions() -> None:
    source = inspect.getsource(build_pattern_dedup_teacher)
    assert 'load_partition("training")' in source
    assert 'load_partition("development")' in source
    assert "pre_drift" not in source
    assert "post_drift" not in source
