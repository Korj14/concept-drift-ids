from __future__ import annotations

from pathlib import Path

import tools.stage9_5.phase_c_pre_rerun_verifier as verifier


def _phase_a_pass() -> dict:
    return {
        "pass": True,
        "complete_seeds": [0, 1, 2, 3, 4],
        "seed_results": [],
    }


def _phase_b_pass() -> dict:
    return {
        "pass": True,
        "accepted_maintenance_archive_verified": True,
        "seed_results": [
            {
                "seed": seed,
                "pass": True,
                "arm_results": [
                    {"arm": arm, "pass": True}
                    for arm in verifier.ARMS
                ],
            }
            for seed in verifier.SEEDS
        ],
    }


def _recovery_pass() -> dict:
    return {
        "pass": True,
        "failures": [],
        "blockers": [],
        "canonical_sha256": "a" * 64,
    }


def _archive_pass() -> dict:
    return {"pass": True, "failures": []}


def _preconditions_pass() -> dict:
    return {
        "pass": True,
        "failures": [],
        "mismatch_count": 0,
        "mismatches": [],
        "failed_lineage_preserved": True,
        "scientific_blocks_equal": True,
    }


def _regenerated_pass() -> dict:
    return {
        "pass": True,
        "failures": [],
        "scientific_blocks_equal": True,
        "phase_c_outcomes_accessed": False,
        "stage10_outcomes_accessed": False,
        "canonical_sha256": "b" * 64,
    }


def _patch_success(monkeypatch) -> None:
    monkeypatch.setattr(verifier, "_git_head", lambda: "c" * 40)
    monkeypatch.setattr(
        verifier,
        "_verify_stage9_5_1_recovery_report",
        lambda _: _recovery_pass(),
    )
    monkeypatch.setattr(
        verifier,
        "_verify_accepted_stage8_archive_root",
        lambda _: _archive_pass(),
    )
    monkeypatch.setattr(
        verifier,
        "compare_phase_a",
        lambda **_: _phase_a_pass(),
    )
    monkeypatch.setattr(
        verifier,
        "compare_phase_b",
        lambda **_: _phase_b_pass(),
    )
    monkeypatch.setattr(
        verifier,
        "compare_phase_c_preconditions",
        lambda **_: _preconditions_pass(),
    )
    monkeypatch.setattr(
        verifier,
        "verify_regenerated_correction_config",
        lambda *_args, **_kwargs: _regenerated_pass(),
    )


def test_successful_pre_rerun_verification_stops_before_corrected_phase_c(
    monkeypatch,
    tmp_path: Path,
) -> None:
    _patch_success(monkeypatch)

    report = verifier.verify_pre_rerun_state(
        accepted_root=tmp_path / "accepted",
        fresh_root=tmp_path / "fresh",
        accepted_correction_config=tmp_path / "accepted.json",
        regenerated_correction_config=tmp_path / "fresh.json",
        stage9_5_1_recovery_report=tmp_path / "recovery.json",
    )

    assert report["pass"] is True
    assert report["status"] == "pass"
    assert report["hard_prerequisites_pass"] is True
    assert report["original_phase_c_v1_seed0_failure_lineage_verified"] is True
    assert report["regenerated_correction_config_scientific_blocks_equal"] is True
    assert report["corrected_phase_c_seed0_output_absent"] is True
    assert report["corrected_phase_c_seed0_rerun_executed_by_this_tool"] is False
    assert report["stage10_outcomes_accessed"] is False
    assert report["next_authorized_step"] == "corrected_phase_c_seed0_rerun"

    core = dict(report)
    observed = core.pop("canonical_sha256")
    assert observed == verifier._canonical_sha256(core)


def test_failed_hard_prerequisite_prevents_phase_c_inspection(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(verifier, "_git_head", lambda: "c" * 40)
    monkeypatch.setattr(
        verifier,
        "_verify_stage9_5_1_recovery_report",
        lambda _: {"pass": False, "failures": ["blocked"], "blockers": ["x"]},
    )
    monkeypatch.setattr(
        verifier,
        "_verify_accepted_stage8_archive_root",
        lambda _: _archive_pass(),
    )
    monkeypatch.setattr(
        verifier,
        "compare_phase_a",
        lambda **_: _phase_a_pass(),
    )
    monkeypatch.setattr(
        verifier,
        "compare_phase_b",
        lambda **_: _phase_b_pass(),
    )
    monkeypatch.setattr(
        verifier,
        "compare_phase_c_preconditions",
        lambda **_: (_ for _ in ()).throw(
            AssertionError("Phase-C preconditions must not be inspected")
        ),
    )
    monkeypatch.setattr(
        verifier,
        "verify_regenerated_correction_config",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("Regenerated config must not be inspected")
        ),
    )

    report = verifier.verify_pre_rerun_state(
        accepted_root=tmp_path / "accepted",
        fresh_root=tmp_path / "fresh",
        accepted_correction_config=tmp_path / "accepted.json",
        regenerated_correction_config=tmp_path / "fresh.json",
        stage9_5_1_recovery_report=tmp_path / "recovery.json",
    )

    assert report["pass"] is False
    assert report["hard_prerequisites_pass"] is False
    assert (
        "hard_prerequisite:stage9_5_1_v1_2_verifier_not_passed"
        in report["failures"]
    )
    assert report["phase_c_preconditions"] is None
    assert report["regenerated_correction_config_verification"] is None


def test_preexisting_corrected_phase_c_output_forces_stop_boundary(
    monkeypatch,
    tmp_path: Path,
) -> None:
    _patch_success(monkeypatch)
    corrected = (
        tmp_path
        / "fresh"
        / verifier.PHASE_C_CORRECTED_SUBDIR
        / "seed-0"
    )
    corrected.mkdir(parents=True)
    (corrected / "attempt.json").write_text("{}\n", encoding="utf-8")

    report = verifier.verify_pre_rerun_state(
        accepted_root=tmp_path / "accepted",
        fresh_root=tmp_path / "fresh",
        accepted_correction_config=tmp_path / "accepted.json",
        regenerated_correction_config=tmp_path / "fresh.json",
        stage9_5_1_recovery_report=tmp_path / "recovery.json",
    )

    assert report["pass"] is False
    assert (
        "stop_boundary:corrected_phase_c_seed0_output_already_present"
        in report["failures"]
    )
    assert report["corrected_phase_c_seed0_output_absent"] is False
    assert report["corrected_phase_c_seed0_existing_entries"] == ["attempt.json"]


def test_phase_b_shape_requires_all_seeds_and_all_arms() -> None:
    payload = _phase_b_pass()
    assert verifier._phase_b_shape_passed(payload) is True

    payload["seed_results"][0]["arm_results"] = [
        {"arm": "c_frozen_symbolic", "pass": True},
        {"arm": "d_drift", "pass": True},
    ]
    assert verifier._phase_b_shape_passed(payload) is False
