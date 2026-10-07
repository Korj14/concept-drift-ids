from __future__ import annotations

import inspect

from concept_drift_ids import system_b


def test_fusion_authority_commands_are_explicitly_dispatched() -> None:
    source = inspect.getsource(system_b.main)

    expected = {
        '"build-fusion-authority-robustness"': (
            "concept_drift_ids.system_b_fusion_robustness",
            "build_fusion_authority_selection",
        ),
        '"verify-fusion-authority-robustness"': (
            "concept_drift_ids.system_b_fusion_robustness",
            "verify_fusion_authority_selection",
        ),
        '"evaluate-fusion-authority-robustness"': (
            "concept_drift_ids.system_b_fusion_robustness_evaluation",
            "evaluate_fusion_authority",
        ),
        '"verify-fusion-authority-robustness-evaluation"': (
            "concept_drift_ids.system_b_fusion_robustness_evaluation",
            "verify_fusion_authority_evaluation",
        ),
    }

    for command, (module_name, function_name) in expected.items():
        assert command in source
        assert module_name in source
        assert function_name in source

    assert 'raise ValueError(f"Unhandled System-B command: {args.command}")' in source


def test_duplicate_aware_verifier_is_not_catch_all_dispatch() -> None:
    source = inspect.getsource(system_b.main)
    assert 'elif args.command == "verify-duplicate-aware-validation":' in source
    assert "else:\n        from concept_drift_ids.system_b_duplicate_robustness" not in source


def test_pattern_dedup_teacher_r0_commands_are_explicitly_dispatched() -> None:
    source = inspect.getsource(system_b.main)

    expected = {
        '"build-pattern-dedup-teacher-r0"': (
            "concept_drift_ids.system_b_dedup_teacher_robustness",
            "build_pattern_dedup_teacher_r0",
        ),
        '"verify-pattern-dedup-teacher-r0"': (
            "concept_drift_ids.system_b_dedup_teacher_robustness",
            "verify_pattern_dedup_teacher_r0",
        ),
    }

    for command, (module_name, function_name) in expected.items():
        assert command in source
        assert module_name in source
        assert function_name in source


def test_pattern_dedup_chain_evaluation_commands_are_explicitly_dispatched() -> None:
    source = inspect.getsource(system_b.main)

    expected = {
        '"evaluate-pattern-dedup-chain"': (
            "concept_drift_ids.system_b_dedup_teacher_evaluation",
            "evaluate_pattern_dedup_training_chain",
        ),
        '"verify-pattern-dedup-chain-evaluation"': (
            "concept_drift_ids.system_b_dedup_teacher_evaluation",
            "verify_pattern_dedup_training_chain_evaluation",
        ),
    }

    for command, (module_name, function_name) in expected.items():
        assert command in source
        assert module_name in source
        assert function_name in source
