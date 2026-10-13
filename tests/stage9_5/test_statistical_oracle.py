from __future__ import annotations

import ast
import math
from pathlib import Path

from tools.stage9_5.statistical_oracle import (
    _describe,
    _explanation_metric,
    _holm_adjust,
    _metric_from_counts,
    _sign_test_greater,
    _stage8_describe,
)


def test_predictive_metrics_from_confusion_counts() -> None:
    counts = {"tp": 40, "tn": 50, "fp": 10, "fn": 20}
    assert math.isclose(_metric_from_counts("f1", counts), 80 / 110, abs_tol=1e-15)
    assert math.isclose(_metric_from_counts("fpr", counts), 10 / 60, abs_tol=1e-15)
    expected_mcc = (40 * 50 - 10 * 20) / math.sqrt(50 * 60 * 60 * 70)
    assert math.isclose(_metric_from_counts("mcc", counts), expected_mcc, abs_tol=1e-15)


def test_predictive_zero_denominators_are_fail_safe() -> None:
    counts = {"tp": 0, "tn": 0, "fp": 0, "fn": 0}
    assert _metric_from_counts("f1", counts) == 0.0
    assert _metric_from_counts("fpr", counts) == 0.0
    assert _metric_from_counts("mcc", counts) == 0.0


def test_explanation_metrics_from_primitives() -> None:
    explanation = {
        "attack_correct_symbolic_coverage": 0.25,
        "benign_correct_symbolic_coverage": 0.75,
        "uncovered_rate": 0.10,
        "conflict_abstain_rate": 0.05,
    }
    assert _explanation_metric("mcsc", explanation) == 0.5
    assert math.isclose(
        _explanation_metric("resolved_coverage", explanation),
        0.85,
        abs_tol=1e-15,
    )


def test_exact_one_sided_sign_probability() -> None:
    assert _sign_test_greater([1, 1, 1, 1, 1]) == {
        "sign_test_n_effective": 5,
        "sign_test_positive": 5,
        "sign_test_p_one_sided": 0.03125,
    }
    assert _sign_test_greater([-1, -1, -1, -1, 1])["sign_test_p_one_sided"] == 0.96875
    assert _sign_test_greater([0, 0])["sign_test_p_one_sided"] == 1.0


def test_holm_matches_frozen_stage8_family() -> None:
    order = [
        "E1_post_mcc_d_drift_minus_c",
        "E2_post_mcsc_d_drift_minus_c",
        "E3_post_mcsc_d_drift_minus_d_periodic",
    ]
    raw = {
        order[0]: 0.03125,
        order[1]: 0.96875,
        order[2]: 0.8125,
    }
    assert _holm_adjust(raw, order) == {
        order[0]: 0.09375,
        order[1]: 1.0,
        order[2]: 1.0,
    }


def test_summary_uses_sample_sd_and_student_t() -> None:
    summary = _describe([1, 2, 3, 4, 5])
    assert summary["mean"] == 3
    assert summary["median"] == 3
    assert math.isclose(summary["sample_sd"], math.sqrt(2.5), abs_tol=1e-15)
    assert summary["positive"] == 5
    assert summary["negative"] == 0
    assert summary["zero"] == 0
    assert summary["leave_one_seed_out_mean_range"] == [2.5, 3.5]
    assert math.isclose(summary["t95_interval_descriptive"][0], 1.036756838522439, abs_tol=1e-12)
    assert math.isclose(summary["t95_interval_descriptive"][1], 4.9632431614775605, abs_tol=1e-12)


def test_stage8_summary_key_shape() -> None:
    summary = _stage8_describe([1, 2, 3, 4, 5])
    assert "leave_one_seed_out_mean_range" not in summary
    assert "t95_interval_descriptive" not in summary
    assert summary["leave_one_seed_out_mean_min"] == 2.5
    assert summary["leave_one_seed_out_mean_max"] == 3.5
    assert "ci95_low" in summary and "ci95_high" in summary


def test_oracle_does_not_import_production_modules() -> None:
    root = Path(__file__).resolve().parents[2]
    source = (root / "tools/stage9_5/statistical_oracle.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module or "")
    assert not any(name.startswith("concept_drift_ids") for name in imports)
