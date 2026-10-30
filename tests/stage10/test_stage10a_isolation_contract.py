"""Synthetic-only Stage-10A matched-isolation oracle, no treatment execution."""
from __future__ import annotations

import copy
import json
from dataclasses import replace
from pathlib import Path

import pytest

from tools.stage10.stage10a_isolation_contract import (
    ARMS, SEEDS, SHARED_FIELDS, ArmEvidence, verify_all_seeds,
    verify_preoutcome_configuration, verify_seed,
)


ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def frozen() -> tuple[dict, dict, dict]:
    master = json.loads((ROOT / "data/manifests/stage10_plus_master_replication_sensitivity_v1_1.json").read_text())
    stage10a = json.loads((ROOT / "data/manifests/stage10a_goldeneye_attack_pattern_v1.json").read_text())
    primary = json.loads((ROOT / "data/manifests/cd_primary_run_config_v1_1.json").read_text())
    return master, stage10a, primary


def _trace(seed: int, arm: str, primary: dict) -> ArmEvidence:
    shared = {name: "b" * 64 for name in SHARED_FIELDS}
    shared.update({
        "source_sha256": "893c27dc968bf7a8adef1689f90be55ca4a4dc3088fb63d6ff247ac56856df2a",
        "ordered_rows_sha256": "81924f3c39cb49adfaebea11d9aef045ab73804dd61faee49dcfbd2dd5f33f25",
        "preprocessing_sha256": primary["scenario"]["preprocessing_state_hash"],
        "initial_checkpoint_sha256":
            primary["system_a"]["checkpoint_sha256_by_seed"][str(seed)],
        "r0_v2_manifest_sha256": primary["r0_v2"]["manifest_sha256"],
    })
    events = (
        {"event_type": "prediction", "logical_clock": 0,
         "origin_index": 0, "prediction_committed": True,
         "neural_probability": 0.33},
        {"event_type": "label_release", "logical_clock": 5000,
         "origin_index": 0, "maturity_index": 5000},
        {"event_type": "detector_observation", "logical_clock": 5000,
         "origin_index": 0},
        {"event_type": "replay_transaction", "logical_clock": 5000,
         "used_label_origins": [0]},
        {"event_type": "neural_publication", "logical_clock": 5000,
         "publication_effective_index": 5001, "neural_state_sha256": "a" * 64},
    )
    return ArmEvidence(seed=seed, arm=arm, shared=shared, events=events)


def _trio(primary: dict, seed: int = 0) -> tuple[ArmEvidence, ...]:
    return tuple(_trace(seed, arm, primary) for arm in ARMS)


def test_master_and_stage10a_derived_config_stay_frozen(frozen) -> None:
    verify_preoutcome_configuration(*frozen)


def test_frozen_config_refuses_release_flag_and_retuning(frozen) -> None:
    master, stage10a, primary = copy.deepcopy(frozen)
    master["hard_gate"]["stage10_execution_permitted"] = True
    with pytest.raises(ValueError, match="hard gate"):
        verify_preoutcome_configuration(master, stage10a, primary)
    master["hard_gate"]["stage10_execution_permitted"] = False
    stage10a["adaptive_mechanism"]["adwin_delta"] = 0.01
    with pytest.raises(ValueError, match="diverges"):
        verify_preoutcome_configuration(master, stage10a, primary)
    stage10a["adaptive_mechanism"]["adwin_delta"] = 0.002
    stage10a["information_timing"]["label_latency_rows"] = 0
    with pytest.raises(ValueError, match="timing"):
        verify_preoutcome_configuration(master, stage10a, primary)


def test_symbolic_difference_allowed_but_shared_state_identical(frozen) -> None:
    primary = frozen[2]
    a, b, c = _trio(primary)
    b = replace(b, symbolic_events=({"symbolic_version": "v2"},))
    c = replace(c, symbolic_events=({"symbolic_version": "periodic"},))
    assert len(verify_seed(0, (a, b, c), primary)) == 64


def test_exact_five_seed_arm_structure(frozen) -> None:
    primary = frozen[2]
    records = [trace for seed in SEEDS for trace in _trio(primary, seed)]
    result = verify_all_seeds(records, primary)
    assert tuple(result) == SEEDS
    with pytest.raises(ValueError, match="Five paired"):
        verify_all_seeds(records[:-1], primary)
    with pytest.raises(ValueError, match="unfrozen"):
        verify_all_seeds(records[:-1] + [replace(records[-1], seed=5)], primary)


@pytest.mark.parametrize("field", [
    "observation_trace_sha256", "neural_prediction_trace_sha256",
    "label_release_trace_sha256", "detector_events_sha256",
    "replay_rows_sha256", "optimizer_configuration_sha256",
    "rng_trace_sha256", "neural_checkpoint_chain_sha256",
    "window_grid_sha256", "fusion_configuration_sha256",
])
def test_any_shared_digest_mismatch_fails_closed(field: str, frozen) -> None:
    primary = frozen[2]
    a, b, c = _trio(primary)
    b = replace(b, shared={**b.shared, field: "c" * 64})
    with pytest.raises(ValueError, match="Class-A mismatch"):
        verify_seed(0, (a, b, c), primary)


def test_historical_seed_checkpoint_tampering_is_rejected(frozen) -> None:
    primary = frozen[2]
    a, b, c = _trio(primary)
    c = replace(c, shared={**c.shared, "initial_checkpoint_sha256": "0" * 64})
    with pytest.raises(ValueError, match="historical seed"):
        verify_seed(0, (a, b, c), primary)


def test_arm_order_and_duplicate_seed_are_rejected(frozen) -> None:
    primary = frozen[2]
    a, b, c = _trio(primary)
    with pytest.raises(ValueError, match="Wrong, duplicate"):
        verify_seed(0, (a, c, b), primary)
    with pytest.raises(ValueError, match="Wrong, duplicate"):
        verify_seed(0, (a, b, replace(c, seed=1)), primary)


@pytest.mark.parametrize("mutation,error", [
    ({"logical_clock": 4999}, "unmatured"),
    ({"maturity_index": 4999}, "unmatured"),
    ({"origin_index": 1}, "prior unique prediction"),
])
def test_future_label_access_fails_closed(mutation: dict, error: str, frozen) -> None:
    primary = frozen[2]
    trace = _trio(primary)[0]
    events = list(copy.deepcopy(trace.events))
    events[1].update(mutation)
    altered = replace(trace, events=tuple(events))
    with pytest.raises(ValueError, match=error):
        verify_seed(0, (altered, *_trio(primary)[1:]), primary)


def test_replay_with_unmatured_label_and_early_publication_fail(frozen) -> None:
    primary = frozen[2]
    trio = _trio(primary)
    for index, edit, error in (
        (3, {"used_label_origins": [100]}, "immature"),
        (4, {"publication_effective_index": 5000}, "next logical row"),
    ):
        events = list(copy.deepcopy(trio[0].events))
        events[index].update(edit)
        with pytest.raises(ValueError, match=error):
            verify_seed(0, (replace(trio[0], events=tuple(events)), *trio[1:]), primary)


def test_cross_arm_shared_event_mutation_and_boundary_leak_rejected(frozen) -> None:
    primary = frozen[2]
    a, b, c = _trio(primary)
    events = list(copy.deepcopy(b.events))
    events[0]["neural_probability"] = 0.9
    b = replace(b, events=tuple(events))
    with pytest.raises(ValueError, match="Class-A mismatch"):
        verify_seed(0, (a, b, c), primary)
    events = list(copy.deepcopy(a.events))
    events[0]["boundary_index"] = 69260
    with pytest.raises(ValueError, match="evaluator-only"):
        verify_seed(0, (replace(a, events=tuple(events)), *_trio(primary)[1:]), primary)


def test_required_full_stream_count_cannot_be_claimed_from_sparse_fixture(frozen) -> None:
    primary = frozen[2]
    with pytest.raises(ValueError, match="noncontiguous prediction"):
        verify_seed(0, _trio(primary), primary, required_prediction_count=138530)
