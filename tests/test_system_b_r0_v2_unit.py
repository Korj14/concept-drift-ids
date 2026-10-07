from __future__ import annotations

import inspect

import numpy as np
from sklearn.tree import DecisionTreeClassifier

import concept_drift_ids.system_b_r0_v2 as correction


def test_weighted_leaf_consequent_uses_fitted_cart_mass() -> None:
    X = np.zeros((4, 1), dtype=np.float64)
    y = np.array([0, 0, 0, 1], dtype=np.int8)
    weights = np.array([1.0, 1.0, 1.0, 10.0])
    tree = DecisionTreeClassifier(max_depth=1, random_state=0)
    tree.fit(X, y, sample_weight=weights)
    assert int(np.argmax(np.bincount(y, minlength=2))) == 0
    assert correction.weighted_leaf_consequent(tree, 0) == 1


def test_v2_config_is_narrow_correction_of_v1() -> None:
    assert correction.V2_CONFIG["rule_base_version"] == "R0.v2"
    assert correction.V2_CONFIG["correction"]["consequent_semantics"] == (
        "weighted_cart_leaf_argmax"
    )
    assert correction.V2_CONFIG["correction"]["shap_recomputed"] is False
    assert correction.V2_CONFIG["correction"]["held_out_evidence_used"] is False


def test_v2_build_partition_loader_excludes_held_out(monkeypatch) -> None:
    calls: list[str] = []
    monkeypatch.setattr(
        correction,
        "load_partition",
        lambda name: calls.append(name) or name,
    )
    assert correction._load_correction_partitions() == ("training", "development")
    assert calls == ["training", "development"]


def test_v2_builder_has_no_held_out_partition_request() -> None:
    source = inspect.getsource(correction.build_and_freeze_r0_v2)
    assert 'load_partition("pre_drift")' not in source
    assert 'load_partition("post_drift")' not in source


def test_v2_pins_frozen_protocol_audit() -> None:
    assert correction.AUDIT_FILE_SHA256 == (
        "abfcb3af93531369427489fc27773f41e500a57279b0fa752b946c3985ebbf32"
    )
    assert correction.EXPECTED_AUDIT_SUMMARY["protocol_mismatch_count"] == 7
    assert correction.EXPECTED_AUDIT_SUMMARY["active_r0_protocol_mismatch_count"] == 4
