from __future__ import annotations

import numpy as np
from sklearn.tree import DecisionTreeClassifier

import concept_drift_ids.system_b_audit as audit


def test_weighted_leaf_consequent_can_differ_from_unweighted_majority() -> None:
    X = np.arange(6, dtype=np.float64).reshape(-1, 1)
    y = np.array([0, 0, 0, 0, 1, 1], dtype=np.int8)
    # Force a single leaf. Unweighted majority is class 0 (4 vs 2),
    # but weighted mass favors class 1 (6 vs 4).
    weights = np.array([1, 1, 1, 1, 3, 3], dtype=np.float64)
    tree = DecisionTreeClassifier(min_samples_split=10, random_state=0)
    tree.fit(X, y, sample_weight=weights)

    assert int(np.argmax(np.bincount(y, minlength=2))) == 0
    assert audit.weighted_leaf_consequent(tree, 0) == 1
