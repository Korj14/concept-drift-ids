from __future__ import annotations

import math

import numpy as np

import concept_drift_ids.cd_primary_mechanism as mechanism
from concept_drift_ids.cd_implementation_preflight import PROJECT_ROOT


def test_authority_state_partition() -> None:
    assert mechanism._authority_state(True, False) == "withdrawal"
    assert mechanism._authority_state(False, True) == "addition"
    assert mechanism._authority_state(True, True) == "revision"
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
            "revision",
            "withdrawal",
            "addition",
            "revision",
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
        ["withdrawal", "withdrawal", "withdrawal", "revision"],
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
    assert summary["net_corrected_decisions"] == 1


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
