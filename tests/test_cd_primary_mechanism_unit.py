from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pytest

import concept_drift_ids.cd_primary_mechanism as mechanism
from concept_drift_ids.cd_implementation_preflight import PROJECT_ROOT


def test_authority_state_partition() -> None:
    assert mechanism._authority_state(True, False) == "withdrawal"
    assert mechanism._authority_state(False, True) == "addition"
    assert mechanism._authority_state(True, True) == "retained_authority"
    assert mechanism._authority_state(False, False) == "neither_authoritative"


def test_mcc_shapley_efficiency_and_endpoints() -> None:
    y = np.asarray([0, 0, 1, 1, 0, 1, 0, 1], dtype=np.int8)
    c = np.asarray([0, 1, 0, 1, 0, 0, 1, 1], dtype=np.int8)
    t = np.asarray([0, 0, 1, 1, 1, 0, 0, 1], dtype=np.int8)
    state = np.asarray(
        [
            "neither_authoritative",
            "withdrawal",
            "addition",
            "retained_authority",
            "withdrawal",
            "addition",
            "retained_authority",
            "neither_authoritative",
        ],
        dtype=object,
    )

    result = mechanism._shapley_mcc(y=y, c=c, t=t, state=state)
    assert math.isclose(
        result["c_mcc"],
        mechanism.matthews_corrcoef(y, c),
        abs_tol=1e-12,
    )
    assert math.isclose(
        result["target_mcc"],
        mechanism.matthews_corrcoef(y, t),
        abs_tol=1e-12,
    )
    assert math.isclose(
        sum(result["shapley_mcc_contribution"].values()),
        result["total_mcc_difference"],
        abs_tol=1e-12,
    )


def test_stratum_rescue_harm_accounting() -> None:
    y = np.asarray([0, 1, 0, 1], dtype=np.int8)
    c = np.asarray([1, 0, 0, 1], dtype=np.int8)
    t = np.asarray([0, 1, 1, 1], dtype=np.int8)
    state = np.asarray(
        ["withdrawal", "withdrawal", "withdrawal", "retained_authority"],
        dtype=object,
    )
    zeros = np.zeros(4, dtype=bool)

    summary = mechanism._stratum_summary(
        y=y,
        c=c,
        t=t,
        state=state,
        c_uncovered=zeros,
        c_conflict=zeros,
        t_uncovered=zeros,
        t_conflict=zeros,
        name="withdrawal",
    )
    assert summary["row_count"] == 3
    assert summary["rescue_count"] == 2
    assert summary["harm_count"] == 1
    assert summary["same_correct_count"] == 0
    assert summary["same_wrong_count"] == 0
    assert summary["net_corrected_decisions"] == 1
    assert (
        summary["rescue_count"]
        + summary["harm_count"]
        + summary["same_correct_count"]
        + summary["same_wrong_count"]
        == summary["row_count"]
    )


def test_mechanism_config_is_absent_or_uses_frozen_identity() -> None:
    if not mechanism.CONFIG_PATH.is_file():
        return
    config = mechanism.load_mechanism_config()
    assert config["parent_evidence_commit"] == mechanism.PARENT_EVIDENCE_COMMIT
    assert (
        config["parent_compact_export_manifest_sha256"]
        == mechanism.PARENT_COMPACT_EXPORT_MANIFEST_SHA256
    )
    assert tuple(config["seeds"]) == mechanism.SEEDS
    assert tuple(config["target_arms"]) == mechanism.TARGET_ARMS
    assert tuple(config["mechanisms"]) == mechanism.MECHANISMS


def test_root_runner_exposes_mechanism_audit() -> None:
    text = (PROJECT_ROOT / "run.py").read_text(encoding="utf-8")
    assert '"cd-primary-mechanism-audit"' in text
    assert "run_primary_mechanism_audit" in text



def test_mechanism_config_preparation_does_not_read_heavy_traces(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(mechanism, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(mechanism, "CONFIG_PATH", tmp_path / "config.json")
    monkeypatch.setattr(
        mechanism,
        "_historical_v1_identity",
        lambda: {
            "config_manifest_sha256": (
                mechanism.HISTORICAL_V1_CONFIG_MANIFEST_SHA256
            ),
            "output_present": False,
            "output_files": [],
        },
    )
    monkeypatch.setattr(
        mechanism,
        "_verify_parent_compact_evidence",
        lambda: {
            "compact_export_manifest_sha256": (
                mechanism.PARENT_COMPACT_EXPORT_MANIFEST_SHA256
            ),
            "confirmatory_aggregate_sha256": (
                mechanism.PARENT_CONFIRMATORY_AGGREGATE_SHA256
            ),
        },
    )
    monkeypatch.setattr(
        mechanism, "_require_clean_for_v1_2_preparation", lambda: None
    )
    monkeypatch.setattr(
        mechanism,
        "_git_output",
        lambda *args, **kwargs: "source-commit",
    )
    monkeypatch.setattr(
        mechanism,
        "_trace_summary",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("row-level trace path must not be touched")
        ),
    )

    files = {
        mechanism.PROTOCOL_PATH: b"protocol",
        mechanism.CORRECTION_PROTOCOL_PATH: b"correction",
        "src/concept_drift_ids/cd_primary_mechanism.py": b"source",
        "run.py": b"runner",
        "tests/test_cd_primary_mechanism_unit.py": b"tests",
    }
    for relative, data in files.items():
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    monkeypatch.setattr(
        mechanism,
        "_historical_v1_1_identity",
        lambda: {
            "config_manifest_sha256": (
                mechanism.HISTORICAL_V1_1_CONFIG_MANIFEST_SHA256
            ),
            "output_root_exists": False,
            "output_files": [],
        },
    )

    payload = mechanism.build_mechanism_config()
    assert payload["source_commit"] == "source-commit"
    assert payload["row_level_mechanism_trace_accessed_during_v1_2_preparation"] is False
    assert payload["analysis_classification"].startswith(
        "exploratory_descriptive_post_primary"
    )


def test_mechanism_config_contains_frozen_decomposition_identity(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(mechanism, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(
        mechanism,
        "_historical_v1_identity",
        lambda: {
            "config_manifest_sha256": (
                mechanism.HISTORICAL_V1_CONFIG_MANIFEST_SHA256
            ),
            "output_present": False,
            "output_files": [],
        },
    )
    monkeypatch.setattr(
        mechanism,
        "_verify_parent_compact_evidence",
        lambda: {
            "compact_export_manifest_sha256": (
                mechanism.PARENT_COMPACT_EXPORT_MANIFEST_SHA256
            ),
            "confirmatory_aggregate_sha256": (
                mechanism.PARENT_CONFIRMATORY_AGGREGATE_SHA256
            ),
        },
    )
    monkeypatch.setattr(
        mechanism, "_require_clean_for_v1_2_preparation", lambda: None
    )
    monkeypatch.setattr(
        mechanism,
        "_git_output",
        lambda *args, **kwargs: "source-commit",
    )
    files = {
        mechanism.PROTOCOL_PATH: b"protocol",
        mechanism.CORRECTION_PROTOCOL_PATH: b"correction",
        "src/concept_drift_ids/cd_primary_mechanism.py": b"source",
        "run.py": b"runner",
        "tests/test_cd_primary_mechanism_unit.py": b"tests",
    }
    for relative, data in files.items():
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    monkeypatch.setattr(
        mechanism,
        "_historical_v1_1_identity",
        lambda: {
            "config_manifest_sha256": (
                mechanism.HISTORICAL_V1_1_CONFIG_MANIFEST_SHA256
            ),
            "output_root_exists": False,
            "output_files": [],
        },
    )

    payload = mechanism.build_mechanism_config()
    assert tuple(payload["mechanisms"]) == mechanism.MECHANISMS
    assert tuple(payload["domains"]) == mechanism.DOMAINS
    assert payload["boundary_index"] == mechanism.BOUNDARY_INDEX
    assert payload["stream_rows"] == mechanism.STREAM_ROWS
    assert payload["primary_decision_key"] == mechanism.PRIMARY_DECISION_KEY



def test_postwrite_config_verifier_uses_tracked_only_clean_gate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = {"full": 0, "tracked": 0}

    monkeypatch.setattr(
        mechanism,
        "require_clean_worktree",
        lambda **kwargs: calls.__setitem__("full", calls["full"] + 1),
    )
    monkeypatch.setattr(
        mechanism,
        "_require_no_tracked_worktree_changes",
        lambda: calls.__setitem__("tracked", calls["tracked"] + 1),
    )

    # Stop after the cleanliness branch, before any real config/Git reads.
    monkeypatch.setattr(
        mechanism,
        "load_mechanism_config",
        lambda: (_ for _ in ()).throw(RuntimeError("stop")),
    )

    with pytest.raises(RuntimeError, match="stop"):
        mechanism.verify_mechanism_config_for_execution(
            require_fully_clean=False
        )
    assert calls == {"full": 0, "tracked": 1}


def test_preexecution_config_verifier_requires_fully_clean_gate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = {"full": 0, "tracked": 0}

    monkeypatch.setattr(
        mechanism,
        "require_clean_worktree",
        lambda **kwargs: calls.__setitem__("full", calls["full"] + 1),
    )
    monkeypatch.setattr(
        mechanism,
        "_require_no_tracked_worktree_changes",
        lambda: calls.__setitem__("tracked", calls["tracked"] + 1),
    )
    monkeypatch.setattr(
        mechanism,
        "load_mechanism_config",
        lambda: (_ for _ in ()).throw(RuntimeError("stop")),
    )

    with pytest.raises(RuntimeError, match="stop"):
        mechanism.verify_mechanism_config_for_execution()
    assert calls == {"full": 1, "tracked": 0}



def test_historical_v1_config_identity_is_immutable() -> None:
    payload = mechanism._read_verified_json(
        mechanism.HISTORICAL_V1_CONFIG_PATH
    )
    stored = payload.pop("manifest_sha256")
    assert stored == mechanism.HISTORICAL_V1_CONFIG_MANIFEST_SHA256
    assert mechanism.canonical_sha256(payload) == stored
    assert tuple(payload["mechanisms"]) == (
        "withdrawal",
        "addition",
        "revision",
    )


def test_v1_1_identities_remain_bound_as_historical_inputs() -> None:
    assert (
        mechanism.HISTORICAL_V1_1_CONFIG_PATH.name
        == "cd_primary_mechanism_audit_v1_1.json"
    )
    assert mechanism.HISTORICAL_V1_1_OUTPUT_ROOT.name == "cd_primary_mechanism_v1_1"
    assert mechanism.HISTORICAL_V1_1_CONFIG_PATH != mechanism.HISTORICAL_V1_CONFIG_PATH
    assert mechanism.HISTORICAL_V1_1_OUTPUT_ROOT != mechanism.HISTORICAL_V1_OUTPUT_ROOT



def test_v1_2_preparation_allows_only_historical_mechanism_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        mechanism,
        "_git_output",
        lambda *args, **kwargs: (
            "?? results/frozen/cd_primary_mechanism_v1/seed-0.json\n"
            "?? results/frozen/cd_primary_mechanism_v1_1/failure.json"
        ),
    )
    mechanism._require_clean_for_v1_2_preparation()

    monkeypatch.setattr(
        mechanism,
        "_git_output",
        lambda *args, **kwargs: (
            "?? results/frozen/cd_primary_mechanism_v1_1/failure.json\n"
            " M src/concept_drift_ids/cd_primary_mechanism.py"
        ),
    )
    with pytest.raises(RuntimeError, match="Disallowed status"):
        mechanism._require_clean_for_v1_2_preparation()


def test_phase_b_arm_manifest_verification_preserves_manifest_identity(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    seed = 0
    arm = "d_drift"
    root = tmp_path / "results" / "frozen" / "cd_primary_v1"
    arm_dir = (
        root
        / "phase_b_symbolic_arms"
        / f"seed-{seed}"
        / arm
    )
    arm_dir.mkdir(parents=True, exist_ok=True)

    core = {
        "schema_version": 1,
        "seed": seed,
        "arm": arm,
        "initial_rule_base_version_id": "d-s0-r0v2",
        "final_rule_base_version_id": "d-s0-v0001",
        "publications": [],
    }
    payload = dict(core)
    payload["manifest_sha256"] = mechanism.canonical_sha256(core)
    path = arm_dir / "arm_manifest.json"
    path.write_text(
        mechanism.json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(mechanism, "COMPACT_ROOT", root)
    loaded = mechanism._phase_b_arm_manifest(seed, arm)

    assert loaded["manifest_sha256"] == payload["manifest_sha256"]
    assert loaded["initial_rule_base_version_id"] == "d-s0-r0v2"
    assert loaded["final_rule_base_version_id"] == "d-s0-v0001"


def test_v1_2_uses_new_config_and_output_identities() -> None:
    assert mechanism.CONFIG_PATH.name == "cd_primary_mechanism_audit_v1_2.json"
    assert mechanism.OUTPUT_ROOT.name == "cd_primary_mechanism_v1_2"
    assert mechanism.CONFIG_PATH != mechanism.HISTORICAL_V1_1_CONFIG_PATH
    assert mechanism.OUTPUT_ROOT != mechanism.HISTORICAL_V1_1_OUTPUT_ROOT
