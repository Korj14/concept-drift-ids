from __future__ import annotations

import inspect

from concept_drift_ids.system_b_fusion_robustness import (
    SENSITIVITY_WEIGHTS,
    _load_development_only,
)
from concept_drift_ids.system_b_fusion_robustness_evaluation import (
    _load_evaluation_partitions,
)


def test_fusion_authority_weights_are_prespecified() -> None:
    assert SENSITIVITY_WEIGHTS == (0.70, 0.90, 1.00)


def test_fusion_selection_uses_development_only() -> None:
    source = inspect.getsource(_load_development_only)
    assert 'load_partition("development")' in source
    assert 'load_partition("training")' not in source
    assert 'load_partition("pre_drift")' not in source
    assert 'load_partition("post_drift")' not in source


def test_fusion_held_out_evaluator_uses_only_pre_post() -> None:
    source = inspect.getsource(_load_evaluation_partitions)
    assert 'load_partition("pre_drift")' in source
    assert 'load_partition("post_drift")' in source
    assert 'load_partition("training")' not in source
    assert 'load_partition("development")' not in source
