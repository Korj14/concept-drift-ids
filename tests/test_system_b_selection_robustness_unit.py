from __future__ import annotations

import numpy as np

from concept_drift_ids.system_b_selection_robustness import (
    ALT_SPLIT_SEEDS,
    _background_indices,
    _gates,
    _selected_features,
    _split_development,
    _variant_specs,
)


def _artifact():
    rows = [
        {
            "rank": i + 1,
            "feature": feature,
            "mean_abs_shap_global": global_value,
            "mean_abs_shap_benign": benign,
            "mean_abs_shap_attack": attack,
        }
        for i, (feature, global_value, benign, attack) in enumerate([
            ("Destination Port", 10.0, 10.0, 1.0),
            ("a", 9.0, 1.0, 9.0),
            ("b", 8.0, 8.0, 2.0),
            ("c", 7.0, 2.0, 7.0),
            ("d", 6.0, 6.0, 3.0),
            ("e", 5.0, 3.0, 6.0),
            ("f", 4.0, 5.0, 4.0),
            ("g", 3.0, 4.0, 5.0),
            ("h", 2.0, 2.0, 2.0),
            ("i", 1.0, 1.0, 1.0),
            ("j", 0.9, 0.9, 0.9),
            ("k", 0.8, 0.8, 0.8),
            ("l", 0.7, 0.7, 0.7),
        ])
    ]
    return {
        "selected_features": [row["feature"] for row in rows[:12]],
        "shap_ranking": rows,
    }


def test_variant_inventory_contains_prespecified_families() -> None:
    specs = _variant_specs()
    ids = {spec.variant_id for spec in specs}
    assert "destination_port_excluded" in ids
    assert "shap_global_mean_abs" in ids
    assert "shap_equal_class_normalized" in ids
    for seed in ALT_SPLIT_SEEDS:
        assert f"development_split_{seed}" in ids
    assert "gate_min_class_precision_0p75" in ids
    assert "gate_min_class_precision_0p85" in ids


def test_destination_port_exclusion_preserves_feature_count() -> None:
    selected = _selected_features(_artifact(), "exclude_destination_port")
    assert len(selected) == 12
    assert "Destination Port" not in selected
    assert selected[-1] == "l"


def test_global_shap_aggregation_is_deterministic() -> None:
    selected = _selected_features(_artifact(), "global_mean_abs")
    assert selected[:3] == ["Destination Port", "a", "b"]


def test_split_development_is_deterministic_and_disjoint() -> None:
    y = np.array([0] * 100 + [1] * 20, dtype=np.int8)
    a, b = _split_development(y, 20261008)
    c, d = _split_development(y, 20261008)
    np.testing.assert_array_equal(a, c)
    np.testing.assert_array_equal(b, d)
    assert not set(a).intersection(set(b))
    assert len(a) + len(b) == len(y)


def test_gate_override_changes_only_requested_gate() -> None:
    spec = next(
        item for item in _variant_specs()
        if item.variant_id == "gate_min_neural_fidelity_0p95"
    )
    gates = _gates(spec)
    assert gates["min_neural_fidelity"] == 0.95
    assert gates["min_class_precision"] == 0.80
    assert gates["min_covered"] == 100



def test_alternate_split_does_not_redefine_bootstrap_seed_policy() -> None:
    import inspect
    from concept_drift_ids.system_b_selection_robustness import _candidate_rules
    source = inspect.getsource(_candidate_rules)
    assert 'random_state=int(gates["bootstrap_random_state_base"]) + seed' in source
    assert "split_seed - PRIMARY_SPLIT_SEED" not in source



def test_background_variants_are_prespecified() -> None:
    ids = {spec.variant_id for spec in _variant_specs()}
    assert "shap_background_balanced_20261008" in ids
    assert "shap_background_balanced_20261009" in ids
    assert "shap_background_natural_20261007" in ids


def test_balanced_background_has_equal_class_counts() -> None:
    y = np.array([0] * 300 + [1] * 300, dtype=np.int8)
    idx = _background_indices(y, "background_balanced_20261008")
    assert len(idx) == 256
    assert int(np.sum(y[idx] == 0)) == 128
    assert int(np.sum(y[idx] == 1)) == 128


def test_natural_background_is_not_forced_balanced() -> None:
    y = np.array([0] * 550 + [1] * 50, dtype=np.int8)
    idx = _background_indices(y, "background_natural_20261007")
    assert len(idx) == 256
    assert len(np.unique(idx)) == 256
