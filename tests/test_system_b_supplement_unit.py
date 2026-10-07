from __future__ import annotations

import inspect

import concept_drift_ids.system_b_evidence as evidence


def test_supplement_is_derived_from_frozen_evidence_only() -> None:
    source = inspect.getsource(evidence.build_system_b_supplement)
    assert "load_partition" not in source
    assert "_load_checkpoint_model" not in source
    assert "predict_probabilities" not in source
    assert "detection_by_seed" in source
    assert "rule_quality" in source


def test_supplement_pins_first_system_b_evaluation_identity() -> None:
    assert evidence.ORIGINAL_EVALUATION_MANIFEST_SHA256 == (
        "f44cad2ed9674bcb7118f05f174f845b5dfb135f95e2cb2b4a230f0f998c3e42"
    )
