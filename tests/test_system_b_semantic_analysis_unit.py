from __future__ import annotations

import inspect

import concept_drift_ids.system_b_semantic_analysis as analysis


def test_semantic_analysis_is_frozen_evidence_only() -> None:
    source = inspect.getsource(analysis.build_semantic_analysis)
    assert "load_partition" not in source
    assert "_load_checkpoint_model" not in source
    assert "predict_probabilities" not in source
    assert "detection_by_seed" in source
    assert "rule_quality" in source


def test_exact_class_count_reconstruction() -> None:
    assert analysis._exact_class_counts(100, 0.97) == (97, 3)


def test_semantic_analysis_pins_accepted_supplement() -> None:
    assert analysis.ACCEPTED_SUPPLEMENT_MANIFEST_SHA256 == (
        "70d41b210ed54f2fa2269ec738ccd94100148d701bb5a2ae79d8d30839e9d190"
    )
