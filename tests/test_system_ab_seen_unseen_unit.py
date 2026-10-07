from __future__ import annotations

import inspect

import numpy as np

from concept_drift_ids.system_ab_seen_unseen import (
    _load_analysis_partitions,
    _symbolic_subset,
)


def test_seen_unseen_loader_does_not_load_development() -> None:
    source = inspect.getsource(_load_analysis_partitions)
    assert 'load_partition("training")' in source
    assert 'load_partition("pre_drift")' in source
    assert 'load_partition("post_drift")' in source
    assert "development" not in source


def test_symbolic_subset_reports_resolved_fidelity() -> None:
    symbolic = {
        "covered": np.array([True, False, True]),
        "symbolic_class": np.array([0, -1, 1], dtype=np.int8),
    }
    neural = np.array([0, 0, 0], dtype=np.int8)
    out = _symbolic_subset(
        symbolic,
        neural,
        np.array([True, False, True]),
    )
    assert out["resolved_coverage"] == 1.0
    assert out["symbolic_neural_fidelity"] == 0.5
