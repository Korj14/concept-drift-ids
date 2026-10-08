from __future__ import annotations

import inspect

from concept_drift_ids.system_b_dtype_audit import (
    _candidate_signature,
    _load_train_dev_only,
    _quality_pass,
)


def test_candidate_signature_ignores_numeric_threshold_roundoff() -> None:
    left = [("a", "<=", 0.1), ("b", ">", 1.0)]
    right = [("a", "<=", 0.100000001), ("b", ">", 0.999999999)]
    assert _candidate_signature(left) == _candidate_signature(right)


def test_quality_pass_uses_frozen_system_b_gates() -> None:
    assert _quality_pass(
        {
            "support": 0.01,
            "covered_count": 100,
            "class_precision": 0.80,
            "neural_fidelity": 0.90,
        },
        stability=0.90,
        complexity=4,
    )
    assert not _quality_pass(
        {
            "support": 0.01,
            "covered_count": 99,
            "class_precision": 1.0,
            "neural_fidelity": 1.0,
        },
        stability=1.0,
        complexity=1,
    )


def test_dtype_audit_partition_loader_excludes_held_out() -> None:
    source = inspect.getsource(_load_train_dev_only)
    assert 'load_partition("training")' in source
    assert 'load_partition("development")' in source
    assert "pre_drift" not in source
    assert "post_drift" not in source
