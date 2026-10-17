from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

import tools.stage9_5.parameter_scan as parameter_scan
from tools.stage9_5.parameter_scan import (
    _LITERAL_EVAL_FAILED,
    _canonical_sha256,
    _literal_eval_or_failed,
    _registered_ids,
    run,
)


def _minimal_repo(tmp_path: Path) -> None:
    (tmp_path / "data/manifests").mkdir(parents=True)
    (tmp_path / "src/concept_drift_ids").mkdir(parents=True)
    (tmp_path / "STAGE8_PRIMARY_EXECUTION_PROTOCOL.md").write_text(
        "threshold 0.5\n", encoding="utf-8"
    )
    (tmp_path / "STAGE9_PRESPECIFIED_ROBUSTNESS_PROTOCOL.md").write_text(
        "latency 5000\n", encoding="utf-8"
    )
    (tmp_path / "Q1_ADVERSARIAL_AUDIT_REGISTER.md").write_text(
        "boundary 69260\n", encoding="utf-8"
    )
    (tmp_path / "METHODOLOGY_LEDGER.md").write_text(
        "five seeds 0 1 2 3 4\n", encoding="utf-8"
    )
    (tmp_path / "STAGE9_5_Q1_INDEPENDENT_ASSURANCE_PROTOCOL.md").write_text(
        "lambda 1\n", encoding="utf-8"
    )


def test_registered_value_matching_is_source_scoped() -> None:
    register = {
        "entries": [
            {
                "id": "x",
                "source_locations": ["a.py"],
                "accepted_value": {"threshold": 0.5},
            }
        ]
    }
    assert _registered_ids(register, "a.py", "threshold", 0.5) == ("x",)
    assert _registered_ids(register, "b.py", "threshold", 0.5) == ()


def test_canonical_hash_is_order_independent_for_mapping() -> None:
    assert _canonical_sha256({"a": 1, "b": 2}) == _canonical_sha256({"b": 2, "a": 1})


def test_scan_blocks_unregistered_high_leverage_constant(tmp_path: Path) -> None:
    _minimal_repo(tmp_path)
    source = tmp_path / "src/concept_drift_ids/example.py"
    source.write_text("LABEL_LATENCY = 5000\n", encoding="utf-8")
    for name in ["a.json", "b.json", "c.json", "d.json"]:
        (tmp_path / "data/manifests" / name).write_text("{}\n", encoding="utf-8")

    register = {
        "protocol_id": "stage9.5-q1-assurance-v1",
        "upstream_closure_head": "head",
        "entries": [],
        "scan_roots": {
            "scientific_source": ["src/concept_drift_ids/example.py"],
            "manifests": [f"data/manifests/{x}" for x in ["a.json","b.json","c.json","d.json"]],
            "protocols": [
                "STAGE8_PRIMARY_EXECUTION_PROTOCOL.md",
                "STAGE9_PRESPECIFIED_ROBUSTNESS_PROTOCOL.md",
                "Q1_ADVERSARIAL_AUDIT_REGISTER.md",
                "METHODOLOGY_LEDGER.md",
                "STAGE9_5_Q1_INDEPENDENT_ASSURANCE_PROTOCOL.md",
            ],
        },
    }
    path = tmp_path / "data/manifests/stage9_5_parameter_register_v1_11.json"
    path.write_text(json.dumps(register), encoding="utf-8")

    try:
        run(tmp_path, tmp_path / "out", fail_on_unclassified_high=True)
    except SystemExit as exc:
        assert "blocked" in str(exc).lower()
    else:
        raise AssertionError("expected fail-closed scan")


def test_scan_passes_when_high_leverage_constant_is_registered(tmp_path: Path) -> None:
    _minimal_repo(tmp_path)
    source = tmp_path / "src/concept_drift_ids/example.py"
    source.write_text("LABEL_LATENCY = 5000\n", encoding="utf-8")
    for name in ["a.json", "b.json", "c.json", "d.json"]:
        (tmp_path / "data/manifests" / name).write_text("{}\n", encoding="utf-8")

    register = {
        "protocol_id": "stage9.5-q1-assurance-v1",
        "upstream_closure_head": "head",
        "entries": [
            {
                "id": "timing.label_latency",
                "source_locations": ["src/concept_drift_ids/example.py"],
                "accepted_value": 5000,
            }
        ],
        "scan_roots": {
            "scientific_source": ["src/concept_drift_ids/example.py"],
            "manifests": [f"data/manifests/{x}" for x in ["a.json","b.json","c.json","d.json"]],
            "protocols": [],
        },
    }
    path = tmp_path / "data/manifests/stage9_5_parameter_register_v1_11.json"
    path.write_text(json.dumps(register), encoding="utf-8")

    report = run(tmp_path, tmp_path / "out", fail_on_unclassified_high=True)
    assert report["pass"] is True
    assert report["counts"]["unclassified_high_leverage_candidates"] == 0


def test_markdown_scanner_normalizes_comma_values_and_ignores_heading_numbers(tmp_path: Path) -> None:
    from tools.stage9_5.parameter_scan import _markdown_candidates

    p = tmp_path / "protocol.md"
    p.write_text(
        "# Stage 9 section 6\n"
        "- D-periodic uses the exact clocks 27,706 / 55,412 / 83,118 / 110,824;\n",
        encoding="utf-8",
    )
    register = {
        "entries": [
            {
                "id": "trigger.periodic_clocks",
                "source_locations": ["protocol.md"],
                "accepted_value": [27706, 55412, 83118, 110824],
                "locator_patterns": ["exact clocks"],
            }
        ]
    }
    found, excluded = _markdown_candidates(tmp_path, "protocol.md", register)
    assert [item.value for item in found] == [27706, 55412, 83118, 110824]
    assert all(item.registered_ids == ("trigger.periodic_clocks",) for item in found)
    assert not excluded


def test_v1_3_blocks_unclassified_material_even_when_not_high_leverage(tmp_path: Path) -> None:
    _minimal_repo(tmp_path)
    source = tmp_path / "src/concept_drift_ids/example.py"
    source.write_text("BATCH_SIZE = 4096\n", encoding="utf-8")
    register = {
        "protocol_id": "stage9.5-q1-assurance-v1",
        "upstream_closure_head": "head",
        "entries": [],
        "scan_roots": {
            "scientific_source": ["src/concept_drift_ids/example.py"],
            "manifests": [],
            "protocols": [],
        },
    }
    path = tmp_path / "data/manifests/stage9_5_parameter_register_v1_11.json"
    path.write_text(json.dumps(register), encoding="utf-8")
    try:
        run(tmp_path, tmp_path / "out", fail_on_unclassified_high=True)
    except SystemExit as exc:
        assert "unclassified material" in str(exc)
    else:
        raise AssertionError("v1.3 must block any unclassified material candidate")


def test_v1_4_scans_material_row_arm_phase_and_weight_constants(tmp_path: Path) -> None:
    from tools.stage9_5.parameter_scan import _python_candidates

    (tmp_path / "src/concept_drift_ids").mkdir(parents=True)
    p = tmp_path / "src/concept_drift_ids/example.py"
    p.write_text(
        "EXPECTED_PRE_ROWS = 69260\n"
        "EXPECTED_POST_ROWS = 69270\n"
        "PRIMARY_PHASES = ('phase_a', 'phase_b', 'phase_c')\n"
        "PRIMARY_ARMS = ('c', 'd_drift', 'd_periodic')\n"
        "PRIMARY_WEIGHTS = (0.5, 0.7, 0.9, 1.0)\n"
        "PRIMARY_NEURAL_WEIGHT = 0.5\n",
        encoding="utf-8",
    )
    register = {
        "entries": [
            {"id":"rows","source_locations":["src/concept_drift_ids/example.py"],"accepted_value":[69260,69270]},
            {"id":"phases","source_locations":["src/concept_drift_ids/example.py"],"accepted_value":["phase_a","phase_b","phase_c"]},
            {"id":"arms","source_locations":["src/concept_drift_ids/example.py"],"accepted_value":["c","d_drift","d_periodic"]},
            {"id":"weights","source_locations":["src/concept_drift_ids/example.py"],"accepted_value":[0.5,0.7,0.9,1.0]},
        ]
    }
    found, _ = _python_candidates(tmp_path, "src/concept_drift_ids/example.py", register)
    locators = {item.locator for item in found}
    assert {"EXPECTED_PRE_ROWS","EXPECTED_POST_ROWS","PRIMARY_PHASES","PRIMARY_ARMS","PRIMARY_WEIGHTS","PRIMARY_NEURAL_WEIGHT"} <= locators
    assert all(item.registered_ids for item in found)


def test_locator_pattern_does_not_bypass_wrong_value() -> None:
    register = {
        "entries": [{
            "id": "latency",
            "source_locations": ["x.py"],
            "accepted_value": 5000,
            "scan_values": [5000],
            "locator_patterns": ["^LABEL_LATENCY$"],
        }]
    }
    assert _registered_ids(register, "x.py", "LABEL_LATENCY", 10000) == ()


def test_string_matching_is_exact_not_substring() -> None:
    register = {
        "entries": [{
            "id": "arm",
            "source_locations": ["x.py"],
            "accepted_value": ["d_periodic"],
        }]
    }
    assert _registered_ids(register, "x.py", "arm", "d_periodic") == ("arm",)
    assert _registered_ids(register, "x.py", "arm", "periodic") == ()


def test_ambiguous_material_mapping_blocks_pass(tmp_path: Path) -> None:
    _minimal_repo(tmp_path)
    source = tmp_path / "src/concept_drift_ids/example.py"
    source.write_text("LABEL_LATENCY = 5000\n", encoding="utf-8")
    register = {
        "protocol_id": "stage9.5-q1-assurance-v1",
        "upstream_closure_head": "head",
        "entries": [
            {"id":"a","source_locations":["src/concept_drift_ids/example.py"],"accepted_value":5000},
            {"id":"b","source_locations":["src/concept_drift_ids/example.py"],"accepted_value":5000},
        ],
        "scan_roots": {"scientific_source":["src/concept_drift_ids/example.py"],"manifests":[],"protocols":[]},
    }
    (tmp_path / "data/manifests/stage9_5_parameter_register_v1_11.json").write_text(json.dumps(register), encoding="utf-8")
    report = run(tmp_path, tmp_path / "out", fail_on_unclassified_high=False)
    assert report["pass"] is False
    assert report["counts"]["ambiguous_material_candidates"] == 1


def test_expression_literal_discovers_hidden_generation_budget(tmp_path: Path) -> None:
    from tools.stage9_5.parameter_scan import _python_candidates
    (tmp_path / "src/concept_drift_ids").mkdir(parents=True)
    p = tmp_path / "src/concept_drift_ids/example.py"
    p.write_text(
        "def _periodic_generation_ids(rows):\n"
        "    if len(rows) < 10_000:\n"
        "        return None\n"
        "    return rows[-10_000:]\n",
        encoding="utf-8",
    )
    register = {"entries":[]}
    found, _ = _python_candidates(tmp_path, "src/concept_drift_ids/example.py", register)
    assert any(item.value == 10000 and item.source_kind == "python_expression" for item in found)


def test_hash_bound_test_file_is_excluded_as_verification_fixture(tmp_path: Path) -> None:
    from tools.stage9_5.parameter_scan import _python_candidates
    (tmp_path / "tests").mkdir(parents=True)
    p = tmp_path / "tests/test_example.py"
    p.write_text("LABEL_LATENCY = 999999\n", encoding="utf-8")
    found, excluded = _python_candidates(tmp_path, "tests/test_example.py", {"entries":[]})
    assert found == []
    assert len(excluded) == 1
    assert excluded[0].source_kind == "python_test_fixture"


def test_anonymous_lambda_index_is_not_scientific_lambda(tmp_path: Path) -> None:
    from tools.stage9_5.parameter_scan import _python_candidates
    (tmp_path / "src/concept_drift_ids").mkdir(parents=True)
    p = tmp_path / "src/concept_drift_ids/example.py"
    p.write_text(
        "def sort_rows(rows):\n"
        "    return sorted(rows, key=lambda item: item[1])\n",
        encoding="utf-8",
    )
    found, _ = _python_candidates(tmp_path, "src/concept_drift_ids/example.py", {"entries":[]})
    assert not any(item.value == 1 for item in found)


def test_probability_zero_fallback_is_excluded(tmp_path: Path) -> None:
    from tools.stage9_5.parameter_scan import _python_candidates
    (tmp_path / "src/concept_drift_ids").mkdir(parents=True)
    p = tmp_path / "src/concept_drift_ids/example.py"
    p.write_text(
        "def threshold_probability(x):\n"
        "    return float(x) if x else 0.0\n",
        encoding="utf-8",
    )
    found, excluded = _python_candidates(tmp_path, "src/concept_drift_ids/example.py", {"entries":[]})
    assert not any(item.value == 0.0 for item in found)
    assert any("zero fallback" in str(item.exclusion_reason) for item in excluded)


def test_markdown_seed_range_is_not_parsed_as_decimal(tmp_path: Path) -> None:
    from tools.stage9_5.parameter_scan import _markdown_candidates
    p = tmp_path / "protocol.md"
    p.write_text("primary seeds <0..4> are frozen\n", encoding="utf-8")
    found, _ = _markdown_candidates(tmp_path, "protocol.md", {"entries":[]})
    assert not any(item.value == 0.4 for item in found)


def test_runtime_state_sentinel_is_logged_exclusion(tmp_path: Path) -> None:
    from tools.stage9_5.parameter_scan import _python_candidates
    (tmp_path / "src/concept_drift_ids").mkdir(parents=True)
    p = tmp_path / "src/concept_drift_ids/example.py"
    p.write_text("drift_detected = False\nbest_epoch = -1\n", encoding="utf-8")
    found, excluded = _python_candidates(tmp_path, "src/concept_drift_ids/example.py", {"entries":[]})
    assert not any(item.locator in {"drift_detected","best_epoch"} for item in found)
    assert sum("runtime state/sentinel" in str(item.exclusion_reason) for item in excluded) == 2


def test_binary_file_mode_is_logged_exclusion(tmp_path: Path) -> None:
    from tools.stage9_5.parameter_scan import _python_candidates
    (tmp_path / "src/concept_drift_ids").mkdir(parents=True)
    p = tmp_path / "src/concept_drift_ids/example.py"
    p.write_text("mode = 'wb'\n", encoding="utf-8")
    found, excluded = _python_candidates(tmp_path, "src/concept_drift_ids/example.py", {"entries":[]})
    assert found == []
    assert any("file I/O mode" in str(item.exclusion_reason) for item in excluded)


def test_v1_9_material_name_coverage_for_detector_and_r0_constants(tmp_path: Path) -> None:
    from tools.stage9_5.parameter_scan import _python_candidates

    (tmp_path / "src/concept_drift_ids").mkdir(parents=True)
    p = tmp_path / "src/concept_drift_ids/example.py"
    p.write_text(
        "ADWIN_CONFIG = (0.002, 32, 5, 5, 10)\n"
        "PAGE_HINKLEY_CONFIG = (30, 0.005, 50.0, 0.9999, 'both')\n"
        "EXPECTED_ACTIVE_COUNTS = {0: 7, 1: 6, 2: 7, 3: 6, 4: 6}\n",
        encoding="utf-8",
    )
    register = {
        "entries": [
            {
                "id":"adwin",
                "source_locations":["src/concept_drift_ids/example.py"],
                "accepted_value":[0.002,32,5,10],
                "scan_values":[0.002,32,5,10],
                "locator_patterns":["^ADWIN_CONFIG$"],
            },
            {
                "id":"ph",
                "source_locations":["src/concept_drift_ids/example.py"],
                "accepted_value":[30,0.005,50,0.9999,"both"],
                "scan_values":[30,0.005,50,0.9999,"both"],
                "locator_patterns":["^PAGE_HINKLEY_CONFIG$"],
            },
            {
                "id":"r0_counts",
                "source_locations":["src/concept_drift_ids/example.py"],
                "accepted_value":[6,7],
                "scan_values":[6,7],
                "locator_patterns":["^EXPECTED_ACTIVE_COUNTS$"],
            },
        ]
    }
    found, excluded = _python_candidates(tmp_path, "src/concept_drift_ids/example.py", register)
    material_locators = {item.locator for item in found}
    assert {"ADWIN_CONFIG","PAGE_HINKLEY_CONFIG","EXPECTED_ACTIVE_COUNTS"} <= material_locators
    assert all(item.registered_ids for item in found if item.locator in material_locators)
    assert not any(item.locator in material_locators for item in excluded)


def test_v1_9_1_literal_container_keys_are_not_expression_candidates(tmp_path: Path) -> None:
    from tools.stage9_5.parameter_scan import _python_candidates

    (tmp_path / "src/concept_drift_ids").mkdir(parents=True)
    p = tmp_path / "src/concept_drift_ids/example.py"
    p.write_text(
        "EXPECTED_ACTIVE_COUNTS = {0: 7, 1: 6, 2: 7, 3: 6, 4: 6}\n",
        encoding="utf-8",
    )
    register = {
        "entries": [{
            "id":"r0_counts",
            "source_locations":["src/concept_drift_ids/example.py"],
            "accepted_value":[6,7],
            "scan_values":[6,7],
            "locator_patterns":["^EXPECTED_ACTIVE_COUNTS$"],
        }]
    }
    found, excluded = _python_candidates(tmp_path, "src/concept_drift_ids/example.py", register)
    assert {item.value for item in found if item.locator == "EXPECTED_ACTIVE_COUNTS"} == {6, 7}
    assert all(item.registered_ids == ("r0_counts",) for item in found)
    assert not any(
        item.source_kind == "python_expression" and item.value in {0,1,2,3,4}
        for item in found + excluded
    )


def test_v1_10_source_specific_detector_and_lifecycle_controls_are_material(tmp_path: Path) -> None:
    from tools.stage9_5.parameter_scan import _python_candidates

    (tmp_path / "src/concept_drift_ids").mkdir(parents=True)

    detector = tmp_path / "src/concept_drift_ids/cd_stage9_shared_runner.py"
    detector.write_text(
        "detector_family = 'adwin'\n"
        "detector_signal = 'hard_error'\n",
        encoding="utf-8",
    )
    detector_register = {
        "entries": [{
            "id":"primary_detector",
            "source_locations":["src/concept_drift_ids/cd_stage9_shared_runner.py"],
            "accepted_value":["adwin","hard_error"],
            "scan_values":["adwin","hard_error"],
            "locator_patterns":["^detector_(family|signal)$"],
        }]
    }
    found, excluded = _python_candidates(
        tmp_path, "src/concept_drift_ids/cd_stage9_shared_runner.py", detector_register
    )
    assert {(item.locator, item.value) for item in found} == {
        ("detector_family","adwin"), ("detector_signal","hard_error")
    }
    assert all(item.registered_ids == ("primary_detector",) for item in found)
    assert not excluded

    lifecycle = tmp_path / "src/concept_drift_ids/cd_symbolic_lifecycle.py"
    lifecycle.write_text(
        "status = 'evidence_insufficient'\n"
        "transition = 'demoted'\n"
        "next_state = 'retired'\n"
        "streak = 1\n",
        encoding="utf-8",
    )
    lifecycle_register = {
        "entries": [{
            "id":"state_machine",
            "source_locations":["src/concept_drift_ids/cd_symbolic_lifecycle.py"],
            "accepted_value":["evidence_insufficient","demoted","retired",1],
            "scan_values":["evidence_insufficient","demoted","retired",1],
            "locator_patterns":["^(status|transition|next_state|streak)$"],
        }]
    }
    found, excluded = _python_candidates(
        tmp_path, "src/concept_drift_ids/cd_symbolic_lifecycle.py", lifecycle_register
    )
    assert {(item.locator, item.value) for item in found} == {
        ("status","evidence_insufficient"), ("transition","demoted"),
        ("next_state","retired"), ("streak",1)
    }
    assert all(item.registered_ids == ("state_machine",) for item in found)
    assert not excluded


def test_v1_11_small_material_expressions_and_replay_dict_values(tmp_path: Path) -> None:
    from tools.stage9_5.parameter_scan import _python_candidates

    (tmp_path / "src/concept_drift_ids").mkdir(parents=True)

    cfg = tmp_path / "src/concept_drift_ids/cd_stage9_config.py"
    cfg.write_text(
        "def specs():\n"
        "    return {'label_latency': 0, 'replay_enabled': False}\n",
        encoding="utf-8",
    )
    cfg_register = {
        "entries": [
            {
                "id":"latency",
                "source_locations":["src/concept_drift_ids/cd_stage9_config.py"],
                "accepted_value":[0,10000],
                "scan_values":[0,10000],
                "locator_patterns":["label_latency.*(?:0|10000)"],
            },
            {
                "id":"no_replay",
                "source_locations":["src/concept_drift_ids/cd_stage9_config.py"],
                "accepted_value":False,
                "scan_values":[False],
                "locator_patterns":["^replay_enabled$"],
            },
        ]
    }
    found, _ = _python_candidates(tmp_path, "src/concept_drift_ids/cd_stage9_config.py", cfg_register)
    assert any(item.value == 0 and item.registered_ids == ("latency",) for item in found)
    assert any(
        item.locator == "replay_enabled"
        and item.value is False
        and item.registered_ids == ("no_replay",)
        for item in found
    )

    life = tmp_path / "src/concept_drift_ids/cd_symbolic_lifecycle.py"
    life.write_text(
        "def apply_lifecycle_maintenance(\n"
        "    same_class_redundancy: float = 0.95,\n"
        "    refinement_overlap: float = 0.50,\n"
        "    cross_class_overlap: float = 0.50,\n"
        "):\n"
        "    streak = failure_streak + 1\n"
        "    return streak\n",
        encoding="utf-8",
    )
    life_register = {
        "entries": [
            {
                "id":"overlap",
                "source_locations":["src/concept_drift_ids/cd_symbolic_lifecycle.py"],
                "accepted_value":[0.95,0.5],
                "scan_values":[0.95,0.5],
                "locator_patterns":["same_class_redundancy|refinement_overlap|cross_class_overlap"],
            },
            {
                "id":"state_machine",
                "source_locations":["src/concept_drift_ids/cd_symbolic_lifecycle.py"],
                "accepted_value":[1],
                "scan_values":[1],
                "locator_patterns":["failure_streak|\\bstreak\\b"],
            },
        ]
    }
    found, _ = _python_candidates(tmp_path, "src/concept_drift_ids/cd_symbolic_lifecycle.py", life_register)
    assert {item.value for item in found if item.registered_ids == ("overlap",)} == {0.5,0.95}
    assert any(item.value == 1 and item.registered_ids == ("state_machine",) for item in found)


def test_v1_11_1_validation_guards_excluded_but_latency_zero_treatment_material(tmp_path: Path) -> None:
    from tools.stage9_5.parameter_scan import _python_candidates

    (tmp_path / "src/concept_drift_ids").mkdir(parents=True)

    shared = tmp_path / "src/concept_drift_ids/cd_stage9_shared_runner.py"
    shared.write_text(
        "def validate(label_latency):\n"
        "    if label_latency < 0:\n"
        "        raise ValueError('non-negative')\n",
        encoding="utf-8",
    )
    found, excluded = _python_candidates(
        tmp_path, "src/concept_drift_ids/cd_stage9_shared_runner.py", {"entries":[]}
    )
    assert not any(item.value == 0 for item in found)
    assert any(
        item.value == 0 and item.exclusion_reason == "latency non-negativity validation lower bound"
        for item in excluded
    )

    correction = tmp_path / "src/concept_drift_ids/cd_primary_correction.py"
    correction.write_text(
        "def _failed_attempt_identity(attempt, failure):\n"
        "    if int(attempt['seed']) != 0 or int(failure['seed']) != 0:\n"
        "        raise ValueError('changed')\n",
        encoding="utf-8",
    )
    found, excluded = _python_candidates(
        tmp_path, "src/concept_drift_ids/cd_primary_correction.py", {"entries":[]}
    )
    assert not any(item.value == 0 for item in found)
    assert sum(
        item.value == 0 and item.exclusion_reason == "preserved failed-run seed identity/provenance check"
        for item in excluded
    ) == 2

    cfg = tmp_path / "src/concept_drift_ids/cd_stage9_config.py"
    cfg.write_text(
        "def specs():\n"
        "    return {'label_latency': 0}\n",
        encoding="utf-8",
    )
    register = {
        "entries":[{
            "id":"latency",
            "source_locations":["src/concept_drift_ids/cd_stage9_config.py"],
            "accepted_value":[0,10000],
            "scan_values":[0,10000],
            "locator_patterns":["label_latency.*(?:0|10000)"],
        }]
    }
    found, _ = _python_candidates(tmp_path, "src/concept_drift_ids/cd_stage9_config.py", register)
    assert any(item.value == 0 and item.registered_ids == ("latency",) for item in found)


def test_literal_eval_expected_nonliteral_is_skipped() -> None:
    node = ast.Name(id="runtime_value", ctx=ast.Load())
    assert _literal_eval_or_failed(node) is _LITERAL_EVAL_FAILED


def test_literal_eval_unexpected_exception_propagates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def unexpected(_: ast.AST) -> object:
        raise RuntimeError("unexpected scanner defect")

    monkeypatch.setattr(parameter_scan.ast, "literal_eval", unexpected)
    with pytest.raises(RuntimeError, match="unexpected scanner defect"):
        _literal_eval_or_failed(ast.Constant(value=1))
