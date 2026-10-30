"""Pre-outcome Stage-10A matched-arm *evidence contract*, not a treatment runner.

This module consumes supplied identity records and synthetic timeline fixtures.
It never loads checkpoints, data, or predictions itself. A successful check
cannot certify that an actual executor produced the claimed records: future
release must bind every digest to independently verified write-once evidence.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

ARMS = ("c_frozen_symbolic", "d_drift", "d_periodic")
SEEDS = (0, 1, 2, 3, 4)
LATENCY = 5000
ROW_COUNT = 138530
SOURCE_SHA256 = "893c27dc968bf7a8adef1689f90be55ca4a4dc3088fb63d6ff247ac56856df2a"
SHARED_FIELDS = (
    "source_sha256", "ordered_rows_sha256", "preprocessing_sha256",
    "initial_checkpoint_sha256", "initial_neural_state_sha256",
    "r0_v2_manifest_sha256", "observation_trace_sha256",
    "neural_prediction_trace_sha256", "label_release_trace_sha256",
    "detector_configuration_sha256", "detector_events_sha256",
    "replay_policy_sha256", "replay_rows_sha256",
    "reservoir_state_trace_sha256", "rng_trace_sha256",
    "optimizer_configuration_sha256", "neural_update_trace_sha256",
    "neural_checkpoint_chain_sha256", "fusion_configuration_sha256",
    "window_grid_sha256",
)
ALLOWED_SHARED_EVENTS = frozenset((
    "prediction", "label_release", "detector_observation", "drift_event",
    "replay_transaction", "neural_publication",
))
SHA256 = re.compile(r"^[0-9a-f]{64}$")


def canonical_sha256(obj: Any) -> str:
    return hashlib.sha256(json.dumps(
        obj, ensure_ascii=False, allow_nan=False, sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ArmEvidence:
    seed: int
    arm: str
    shared: Mapping[str, str]
    events: tuple[Mapping[str, Any], ...]
    symbolic_events: tuple[Mapping[str, Any], ...] = ()


def verify_preoutcome_configuration(
    master: Mapping[str, Any],
    stage10a: Mapping[str, Any],
    primary: Mapping[str, Any],
) -> None:
    """Read-only guard against deviating from frozen source and primary knobs."""
    if master["hard_gate"]["stage10_execution_permitted"] is not False:
        raise ValueError("Stage-10 execution hard gate is not locked.")
    if master["stage10_treatment_outcomes_accessed"] is not False:
        raise ValueError("Stage-10 treatment outcomes already accessed.")
    if len(master["stage_specific_pre_outcome_freeze_required"]) != 19:
        raise ValueError("19-field master freeze contract changed.")
    if len(master["master_obligations"]) != 16:
        raise ValueError("Master obligation count changed.")
    if stage10a["stage10_treatment_execution_authorized"] is not False:
        raise ValueError("Stage-10A treatment is not permitted.")
    if stage10a["stage10_treatment_outcomes_accessed_during_freeze"] is not False:
        raise ValueError("Stage-10A frozen source had outcome access.")
    if stage10a["protocol_id"] != "stage10a-goldeneye-attack-pattern-v1":
        raise ValueError("Stage-10A protocol identity changed.")
    if stage10a["raw_source"]["sha256"] != SOURCE_SHA256:
        raise ValueError("Stage-10A source identity changed.")
    if tuple(stage10a["inherited_identities"]["seeds"]) != SEEDS:
        raise ValueError("Stage-10A paired seed identities changed.")
    if tuple(stage10a["primary_arms"]) != ARMS:
        raise ValueError("Stage-10A arm definitions changed.")
    if tuple(stage10a["primary_endpoints"]) != (
        "E1_post_mcc_d_drift_minus_c",
        "E2_post_mcsc_d_drift_minus_c",
        "E3_post_mcsc_d_drift_minus_d_periodic",
    ):
        raise ValueError("Stage-10A endpoint family changed.")
    if stage10a["information_timing"] != {
        "label_latency_rows": LATENCY,
        "prediction_before_label_release": True,
    }:
        raise ValueError("Stage-10A information timing changed.")
    if stage10a["scenario"]["boundary_index"] != 69260 or (
        stage10a["scenario"]["boundary_role"]
        != "offline_evaluator_scoring_and_diagnostics_only"
    ):
        raise ValueError("Evaluator-only boundary changed.")
    if stage10a["scenario"]["stream_row_ids_sha256"] != (
        "81924f3c39cb49adfaebea11d9aef045ab73804dd61faee49dcfbd2dd5f33f25"
    ):
        raise ValueError("Stage-10A stream row ordering changed.")
    adv = stage10a["adaptive_mechanism"]
    control = primary["primary_control_plane"]
    control_config = control["config"]
    updates = control_config["neural_update"]
    symbolic = primary["primary_symbolic_operator"]
    pairs = (
        (adv["adwin_clock"], control["adwin"]["clock"]),
        (adv["adwin_delta"], control["adwin"]["delta"]),
        (adv["current_window_rows"], control_config["current_window"]),
        (adv["anchor_memory_capacity"], control_config["reservoir_capacity"]),
        (adv["update_anchor_rows"], control_config["replay_anchor_rows"]),
        (adv["update_online_rows"], control_config["replay_online_rows"]),
        (adv["neural_batch_size"], updates["batch_size"]),
        (adv["neural_epochs"], updates["epochs"]),
        (adv["neural_learning_rate"], updates["learning_rate"]),
        (adv["neural_weight_decay"], updates["weight_decay"]),
        (adv["fusion_lambda"], primary["fusion"]["primary_neural_weight"]),
        (adv["maximum_symbolic_opportunities"],
         symbolic["maximum_opportunities_per_seed"]),
        (adv["validation_window_rows"], symbolic["config"]["validation_rows"]),
        (adv["generation_window_rows"], 10000),
    )
    if any(value != original for value, original in pairs):
        raise ValueError("Stage-10A mechanism diverges from frozen primary.")
    if tuple(symbolic["periodic_clocks"]) != (27706, 55412, 83118, 110824):
        raise ValueError("Inherited periodic comparator changed.")
    if (stage10a["inherited_identities"]["r0_v2_manifest_sha256"]
        != primary["r0_v2"]["manifest_sha256"]):
        raise ValueError("R0.v2 starting symbolic identity changed.")
    if (stage10a["inherited_identities"]["system_a_manifest_sha256"]
        != primary["system_a"]["manifest_sha256"]):
        raise ValueError("Accepted System-A manifest identity changed.")
    if (stage10a["inherited_identities"]["preprocessing_core_state_sha256"]
        != primary["scenario"]["preprocessing_state_hash"]):
        raise ValueError("Accepted preprocessing identity changed.")


def _assert_shared_identity(trace: ArmEvidence, primary: Mapping[str, Any]) -> None:
    if set(trace.shared) != set(SHARED_FIELDS):
        raise ValueError("Missing or unauthorized shared identity fields.")
    if not all(isinstance(s, str) and SHA256.fullmatch(s)
               for s in trace.shared.values()):
        raise ValueError("Malformed shared evidence SHA-256.")
    if trace.shared["source_sha256"] != SOURCE_SHA256:
        raise ValueError("Shared source identity incorrect.")
    if trace.shared["ordered_rows_sha256"] != (
        "81924f3c39cb49adfaebea11d9aef045ab73804dd61faee49dcfbd2dd5f33f25"
    ):
        raise ValueError("Shared row identity incorrect.")
    if trace.shared["preprocessing_sha256"] != (
        primary["scenario"]["preprocessing_state_hash"]
    ):
        raise ValueError("Shared preprocessing identity incorrect.")
    if trace.shared["initial_checkpoint_sha256"] != (
        primary["system_a"]["checkpoint_sha256_by_seed"][str(trace.seed)]
    ):
        raise ValueError("Shared initial checkpoint differs from historical seed.")
    if trace.shared["r0_v2_manifest_sha256"] != (
        primary["r0_v2"]["manifest_sha256"]
    ):
        raise ValueError("Shared symbolic R0 identity incorrect.")


def _assert_timing(events: Sequence[Mapping[str, Any]]) -> None:
    if not events:
        raise ValueError("No shared trajectory evidence.")
    predicted: set[int] = set()
    labels: set[int] = set()
    detected: set[int] = set()
    last_clock = -1
    for e in events:
        kind = e.get("event_type")
        clock = e.get("logical_clock")
        if kind not in ALLOWED_SHARED_EVENTS or type(clock) is not int:
            raise ValueError("Unrecognized shared event or logical clock.")
        if clock < last_clock or clock < 0:
            raise ValueError("Out-of-order shared event.")
        last_clock = clock
        if "symbolic_state" in e or "boundary_index" in e:
            raise ValueError("Arm-specific or evaluator-only state leaked.")
        origin = e.get("origin_index")
        if kind == "prediction":
            if type(origin) is not int or origin != clock or origin in predicted:
                raise ValueError("Nonsequential or repeated prediction event.")
            if e.get("prediction_committed") is not True:
                raise ValueError("Prediction was not committed before label use.")
            predicted.add(origin)
        elif kind == "label_release":
            if type(origin) is not int or origin not in predicted or origin in labels:
                raise ValueError("Label not tied to a prior unique prediction.")
            if e.get("maturity_index") != origin + LATENCY or clock < origin + LATENCY:
                raise ValueError("Future/unmatured label release.")
            labels.add(origin)
        elif kind == "detector_observation":
            if type(origin) is not int or origin not in labels or origin in detected:
                raise ValueError("Detector observed a future or repeated label.")
            detected.add(origin)
        elif kind == "drift_event":
            if type(origin) is not int or origin not in detected:
                raise ValueError("Drift trigger without admitted mature evidence.")
        elif kind == "replay_transaction":
            origins = e.get("used_label_origins")
            if not isinstance(origins, (list, tuple)) or any(
                type(i) is not int or i not in labels for i in origins
            ):
                raise ValueError("Replay uses immature labels or unknown origins.")
        elif kind == "neural_publication":
            if e.get("publication_effective_index") != clock + 1:
                raise ValueError("Neural state published before next logical row.")
            if not isinstance(e.get("neural_state_sha256"), str) or not (
                SHA256.fullmatch(e["neural_state_sha256"])
            ):
                raise ValueError("Missing neural state digest.")
    if not predicted:
        raise ValueError("Shared evidence lacks prediction commits.")


def verify_seed(
    seed: int,
    traces: Sequence[ArmEvidence],
    primary: Mapping[str, Any],
    *,
    required_prediction_count: int | None = None,
) -> str:
    """Verify supplied per-arm shared evidence, not execute any treatments.

    A real release MUST also verify each claimed digest from raw evidence,
    require 138530 contiguous predictions, and establish the common writer.
    """
    if seed not in SEEDS or len(traces) != len(ARMS):
        raise ValueError("Required seed/arm count missing.")
    if tuple(t.arm for t in traces) != ARMS or any(t.seed != seed for t in traces):
        raise ValueError("Wrong, duplicate, reordered or cross-seed arm.")
    reference = traces[0]
    _assert_shared_identity(reference, primary)
    _assert_timing(reference.events)
    if required_prediction_count is not None:
        positions = [e["origin_index"] for e in reference.events
                     if e.get("event_type") == "prediction"]
        if positions != list(range(required_prediction_count)):
            raise ValueError("Missing or noncontiguous prediction sequence.")
    reference_event_hash = canonical_sha256(reference.events)
    for current in traces[1:]:
        _assert_shared_identity(current, primary)
        _assert_timing(current.events)
        if dict(current.shared) != dict(reference.shared):
            raise ValueError("Class-A mismatch: shared C/D neural or control state.")
        if canonical_sha256(current.events) != reference_event_hash:
            raise ValueError("Class-A mismatch: shared C/D event sequence.")
    return canonical_sha256({
        "seed": seed,
        "shared": dict(reference.shared),
        "shared_events_sha256": reference_event_hash,
    })


def verify_all_seeds(
    traces: Sequence[ArmEvidence],
    primary: Mapping[str, Any],
) -> dict[int, str]:
    if len(traces) != len(SEEDS) * len(ARMS):
        raise ValueError("Five paired three-arm seeds required.")
    by_seed = {seed: [] for seed in SEEDS}
    for trace in traces:
        if trace.seed not in by_seed:
            raise ValueError("Unfrozen seed present.")
        by_seed[trace.seed].append(trace)
    return {
        seed: verify_seed(seed, tuple(by_seed[seed]), primary)
        for seed in SEEDS
    }
