"""Stage-10A gated shared control runner: isolated from the frozen Stage-8 source.

The inherited cd_shared_runner.py and its frozen source hash MUST NOT change.
This subclass reuses its frozen constructor, model predictor and control-plane
primitives. Its run loop is a reviewed Stage-10A variant with a mandatory
external durable-commit/mature-label interface. No executable launch is offered.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Protocol, Sequence

import numpy as np

from concept_drift_ids.cd_shared_runner import (
    ONLINE_RESERVOIR_SEED,
    DelayedLabelQueue,
    MatureLabelRecord,
    ReservoirItem,
    SharedControlPlaneRunner,
    SharedErrorDriftMonitor,
    SharedTrajectory,
    UniformReservoir,
    adapt_neural_checkpoint,
    build_checkpoint_record,
    build_event,
    build_shared_identity,
    canonical_sha256,
    records_sha256,
    row_ids_sha256,
    select_recent_current_evidence,
    select_replay_ids,
    state_dict_sha256,
    verify_checkpoint_chain,
    write_checkpoint_new,
)


@dataclass(frozen=True)
class UnlabeledStreamRow:
    """Stage-10A feature input with no future target or evaluator boundary."""
    row_id: str
    features: np.ndarray


@dataclass(frozen=True)
class Stage10ALabelGrant:
    """Matured ground truth returned by an external label custodian."""
    origin_index: int
    binary_target: int


class Stage10APredictionGateway(Protocol):
    """The independent future production daemon must implement this call.

    Its ACK must follow durable append and independent observation of the
    prediction. Host identity, custody, fsync, replay protection and OS
    isolation must be established separately before production G2 acceptance.
    """
    def commit_prediction(
        self,
        *,
        seed: int,
        run_id: str,
        row_id: str,
        origin_index: int,
        maturity_index: int,
        checkpoint_sha256: str,
        neural_probability: float,
    ) -> Stage10ALabelGrant | None: ...


class Stage10AControlPlaneRunner(SharedControlPlaneRunner):
    """No inherited scientific source modification; gateway is mandatory."""

    def run(
        self,
        rows: Sequence[StreamRow] | Sequence[UnlabeledStreamRow],
        *,
        label_gateway: Stage10APredictionGateway | None = None,
    ) -> SharedTrajectory:
        if label_gateway is None:
            raise ValueError("Stage-10A external prediction gateway is mandatory")
        # A distinct Stage-10A input contract. The inherited Stage-8 path is
        # unchanged when label_gateway is absent.
        if label_gateway is not None:
            if self.config.label_latency != 5_000:
                raise ValueError("Stage-10A external label latency must be 5000")
            if any(type(row) is not UnlabeledStreamRow for row in rows):
                raise ValueError("Stage-10A gateway only accepts label-free rows")
        stream_ids = [row.row_id for row in rows]
        if len(set(stream_ids)) != len(stream_ids):
            raise ValueError("stream row IDs must be unique")
        if set(stream_ids).intersection(self.anchor_by_id):
            raise ValueError(
                "Anchor and stream row IDs must use disjoint audit namespaces."
            )

        queue = (
            DelayedLabelQueue(self.config.label_latency)
            if label_gateway is None else None
        )
        external_committed: dict[int, dict[str, Any]] = {}
        external_release_count = 0
        monitor = SharedErrorDriftMonitor(
            monitor_threshold=self.monitor_threshold
        )
        active_model = self.initial_model
        active_checkpoint_sha256 = self.initial_checkpoint_sha256
        active_state_sha256 = state_dict_sha256(active_model)
        monitor.start_initial_epoch(active_checkpoint_sha256)

        reservoir = UniformReservoir(
            capacity=self.config.reservoir_capacity,
            seed=ONLINE_RESERVOIR_SEED,
        )

        stream_features_by_id: dict[str, np.ndarray] = {}
        mature_history: list[MatureLabelRecord] = []
        predictions: list[dict[str, Any]] = []
        label_schedule: list[dict[str, Any]] = []
        detector_observations: list[dict[str, Any]] = []
        events: list[dict[str, Any]] = []
        replay_transactions: list[dict[str, Any]] = []

        checkpoint_chain = [
            build_checkpoint_record(
                sequence=0,
                parent_state_sha256=None,
                child_state_sha256=active_state_sha256,
                checkpoint_file_sha256=active_checkpoint_sha256,
                event_id="initial",
                evidence_sha256=canonical_sha256({"source": "accepted_initial"}),
                config_sha256=self.config_sha256,
                publication_effective_index=0,
            )
        ]

        pending: dict[str, Any] | None = None

        for logical_clock, row in enumerate(rows):
            if label_gateway is None and row.label not in (0, 1):
                raise ValueError("Stream labels must be binary.")
            stream_features_by_id[row.row_id] = np.asarray(
                row.features, dtype=np.float32
            ).copy()

            probability = self._predict_one(
                active_model, stream_features_by_id[row.row_id]
            )
            if label_gateway is None:
                assert queue is not None
                prediction = queue.commit_prediction(
                    row_id=row.row_id,
                    origin_index=logical_clock,
                    checkpoint_sha256=active_checkpoint_sha256,
                    neural_probability=probability,
                    true_label=row.label,
                )
                public_prediction = prediction.public_prediction_payload()
            else:
                # No true label exists in this address space at prediction time.
                # An external service must persist and observe the prediction
                # BEFORE returning the one matured label, if any.
                public_prediction = {
                    "row_id": row.row_id,
                    "origin_index": logical_clock,
                    "maturity_index": logical_clock + self.config.label_latency,
                    "checkpoint_sha256": active_checkpoint_sha256,
                    "neural_probability": probability,
                }
                grant = label_gateway.commit_prediction(
                    seed=self.seed,
                    run_id=self.run_id,
                    **public_prediction,
                )
                external_committed[logical_clock] = public_prediction
                expected_origin = logical_clock - self.config.label_latency
                if expected_origin < 0:
                    if grant is not None:
                        raise ValueError("External label arrived before maturity")
                    externally_released: list[MatureLabelRecord] = []
                else:
                    if (type(grant) is not Stage10ALabelGrant
                        or type(grant.origin_index) is not int
                        or grant.origin_index != expected_origin
                        or type(grant.binary_target) is not int
                        or grant.binary_target not in (0, 1)):
                        raise ValueError("External label grant missing, early or forged")
                    committed = external_committed.pop(expected_origin)
                    externally_released = [MatureLabelRecord(
                        row_id=str(committed["row_id"]),
                        origin_index=expected_origin,
                        maturity_index=logical_clock,
                        checkpoint_sha256=str(committed["checkpoint_sha256"]),
                        neural_probability=float(committed["neural_probability"]),
                        true_label=grant.binary_target,
                    )]
                    external_release_count += 1
            predictions.append(
                {
                    **public_prediction,
                    "logical_clock": logical_clock,
                }
            )
            label_schedule.append(
                {
                    "row_id": row.row_id,
                    "origin_index": logical_clock,
                    "maturity_index": public_prediction["maturity_index"],
                }
            )
            events.append(
                build_event(
                    run_id=self.run_id,
                    seed=self.seed,
                    event_type="prediction",
                    event_id=f"prediction-{logical_clock}",
                    logical_clock=logical_clock,
                    status="committed",
                    origin_index=logical_clock,
                    maturity_index=int(public_prediction["maturity_index"]),
                    neural_checkpoint_sha256=active_checkpoint_sha256,
                    config_sha256=self.config_sha256,
                    git_commit=self.git_commit,
                    payload={"neural_probability": probability},
                )
            )

            if label_gateway is None:
                assert queue is not None
                released = queue.release_after_prediction(logical_clock)
            else:
                released = externally_released
            for record in released:
                mature_history.append(record)
                reservoir.consider(
                    ReservoirItem(
                        row_id=record.row_id,
                        origin_index=record.origin_index,
                        maturity_index=record.maturity_index,
                        checkpoint_sha256=record.checkpoint_sha256,
                        label=record.true_label,
                    )
                )
                events.append(
                    build_event(
                        run_id=self.run_id,
                        seed=self.seed,
                        event_type="label_release",
                        event_id=f"label-{record.origin_index}",
                        logical_clock=logical_clock,
                        status="mature",
                        origin_index=record.origin_index,
                        maturity_index=record.maturity_index,
                        neural_checkpoint_sha256=record.checkpoint_sha256,
                        config_sha256=self.config_sha256,
                        git_commit=self.git_commit,
                    )
                )

                observed = monitor.observe(record)
                observed_payload = asdict(observed)
                detector_observations.append(observed_payload)
                events.append(
                    build_event(
                        run_id=self.run_id,
                        seed=self.seed,
                        event_type="detector_observation",
                        event_id=(
                            f"detector-e{observed.epoch_id}-"
                            f"origin{observed.origin_index}"
                        ),
                        logical_clock=logical_clock,
                        status=observed.reason,
                        origin_index=record.origin_index,
                        maturity_index=record.maturity_index,
                        neural_checkpoint_sha256=record.checkpoint_sha256,
                        config_sha256=self.config_sha256,
                        git_commit=self.git_commit,
                        payload={
                            "epoch_id": observed.epoch_id,
                            "epoch_checkpoint_sha256": (
                                observed.epoch_checkpoint_sha256
                            ),
                            "admitted": observed.admitted,
                            "error": observed.error,
                            "drift_detected": observed.drift_detected,
                        },
                    )
                )

                if observed.drift_detected:
                    if pending is not None:
                        raise AssertionError(
                            "A detector event occurred while a neural transaction "
                            "was already outstanding."
                        )
                    event_id = monitor.event_count
                    pending = {
                        "event_id": event_id,
                        "confirmation_clock": logical_clock,
                        "parent_checkpoint_sha256": active_checkpoint_sha256,
                        "parent_state_sha256": active_state_sha256,
                    }
                    events.append(
                        build_event(
                            run_id=self.run_id,
                            seed=self.seed,
                            event_type="drift_event",
                            event_id=f"drift-{event_id}",
                            logical_clock=logical_clock,
                            status="confirmed",
                            origin_index=record.origin_index,
                            maturity_index=record.maturity_index,
                            neural_checkpoint_sha256=active_checkpoint_sha256,
                            config_sha256=self.config_sha256,
                            git_commit=self.git_commit,
                        )
                    )

            if pending is None:
                continue

            current = select_recent_current_evidence(
                mature_history,
                parent_checkpoint_sha256=pending[
                    "parent_checkpoint_sha256"
                ],
                action_clock=logical_clock,
                window_size=self.config.current_window,
            )
            if current is None:
                continue

            current_ids = [record.row_id for record in current]
            replay_ids = select_replay_ids(
                anchor_ids=[row.row_id for row in self.anchor_rows],
                online_items=reservoir.items(),
                current_row_ids=current_ids,
                event_id=int(pending["event_id"]),
                anchor_rows=self.config.replay_anchor_rows,
                online_rows=self.config.replay_online_rows,
            )

            def lookup(row_id: str) -> tuple[np.ndarray, int]:
                if row_id in self.anchor_by_id:
                    anchor = self.anchor_by_id[row_id]
                    return np.asarray(anchor.features, dtype=np.float32), int(
                        anchor.label
                    )
                features = stream_features_by_id[row_id]
                record = next(
                    item for item in mature_history if item.row_id == row_id
                )
                return np.asarray(features, dtype=np.float32), int(
                    record.true_label
                )

            current_X = np.stack(
                [
                    np.asarray(
                        stream_features_by_id[record.row_id], dtype=np.float32
                    )
                    for record in current
                ]
            )
            current_y = np.asarray(
                [record.true_label for record in current],
                dtype=np.int8,
            )
            replay_pairs = [lookup(row_id) for row_id in replay_ids]
            replay_X = np.stack([pair[0] for pair in replay_pairs])
            replay_y = np.asarray([pair[1] for pair in replay_pairs], dtype=np.int8)

            evidence = {
                "event_id": int(pending["event_id"]),
                "action_clock": logical_clock,
                "parent_checkpoint_sha256": pending[
                    "parent_checkpoint_sha256"
                ],
                "current_row_ids": current_ids,
                "current_row_ids_sha256": row_ids_sha256(current_ids),
                "replay_row_ids": list(replay_ids),
                "replay_row_ids_sha256": row_ids_sha256(replay_ids),
                "reservoir_identity_sha256": reservoir.identity_sha256(),
            }
            evidence_sha256 = canonical_sha256(evidence)

            update = adapt_neural_checkpoint(
                active_model,
                X_current=current_X,
                y_current=current_y,
                X_replay=replay_X,
                y_replay=replay_y,
                seed=self.seed,
                event_id=int(pending["event_id"]),
                config=self.config.neural_update,
            )

            checkpoint_path = self.checkpoint_dir / (
                f"seed-{self.seed}-event-{pending['event_id']}.pt"
            )
            checkpoint_info = write_checkpoint_new(
                checkpoint_path,
                model=update.child_model,
                metadata={
                    "run_id": self.run_id,
                    "seed": self.seed,
                    "event_id": int(pending["event_id"]),
                    "parent_checkpoint_sha256": pending[
                        "parent_checkpoint_sha256"
                    ],
                    "parent_state_sha256": pending["parent_state_sha256"],
                    "evidence_sha256": evidence_sha256,
                    "config_sha256": self.config_sha256,
                    "shuffle_seed": update.shuffle_seed,
                    "epoch_losses": list(update.epoch_losses),
                    "publication_effective_index": logical_clock + 1,
                },
            )

            active_model = update.child_model
            active_checkpoint_sha256 = checkpoint_info["file_sha256"]
            active_state_sha256 = checkpoint_info["state_sha256"]
            monitor.publish_child_checkpoint(active_checkpoint_sha256)

            checkpoint_chain.append(
                build_checkpoint_record(
                    sequence=len(checkpoint_chain),
                    parent_state_sha256=pending["parent_state_sha256"],
                    child_state_sha256=active_state_sha256,
                    checkpoint_file_sha256=active_checkpoint_sha256,
                    event_id=f"drift-{pending['event_id']}",
                    evidence_sha256=evidence_sha256,
                    config_sha256=self.config_sha256,
                    publication_effective_index=logical_clock + 1,
                )
            )
            replay_transactions.append(
                {
                    **evidence,
                    "evidence_sha256": evidence_sha256,
                    "child_checkpoint_sha256": active_checkpoint_sha256,
                    "child_state_sha256": active_state_sha256,
                    "publication_effective_index": logical_clock + 1,
                    "epoch_losses": list(update.epoch_losses),
                }
            )
            events.append(
                build_event(
                    run_id=self.run_id,
                    seed=self.seed,
                    event_type="neural_publication",
                    event_id=f"publication-{pending['event_id']}",
                    logical_clock=logical_clock,
                    status="published",
                    parent_event_id=f"drift-{pending['event_id']}",
                    neural_checkpoint_sha256=active_checkpoint_sha256,
                    evidence_sha256=evidence_sha256,
                    config_sha256=self.config_sha256,
                    git_commit=self.git_commit,
                    payload={
                        "publication_effective_index": logical_clock + 1,
                        "child_state_sha256": active_state_sha256,
                    },
                )
            )
            pending = None

        if pending is not None:
            events.append(
                build_event(
                    run_id=self.run_id,
                    seed=self.seed,
                    event_type="neural_transaction",
                    event_id=f"censored-{pending['event_id']}",
                    logical_clock=max(0, len(rows) - 1),
                    status="right_censored",
                    parent_event_id=f"drift-{pending['event_id']}",
                    neural_checkpoint_sha256=pending[
                        "parent_checkpoint_sha256"
                    ],
                    config_sha256=self.config_sha256,
                    git_commit=self.git_commit,
                    reason="insufficient_mature_current_evidence_before_stream_end",
                )
            )

        verify_checkpoint_chain(checkpoint_chain)

        label_schedule_sha256 = records_sha256(label_schedule)
        detector_events_sha256 = records_sha256(detector_observations)
        replay_evidence_sha256 = records_sha256(replay_transactions)
        checkpoint_chain_sha256 = records_sha256(checkpoint_chain)
        shared_identity = build_shared_identity(
            label_schedule_sha256=label_schedule_sha256,
            detector_events_sha256=detector_events_sha256,
            replay_evidence_sha256=replay_evidence_sha256,
            checkpoint_chain_sha256=checkpoint_chain_sha256,
        )

        return SharedTrajectory(
            seed=self.seed,
            config_sha256=self.config_sha256,
            predictions=tuple(predictions),
            label_schedule=tuple(label_schedule),
            detector_observations=tuple(detector_observations),
            events=tuple(events),
            replay_transactions=tuple(replay_transactions),
            checkpoint_chain=tuple(checkpoint_chain),
            shared_identity=shared_identity,
            final_checkpoint_sha256=active_checkpoint_sha256,
            final_state_sha256=active_state_sha256,
            pending_labels=(
                queue.pending_count() if queue is not None
                else len(rows) - external_release_count
            ),
            pending_neural_transaction=(
                dict(pending) if pending is not None else None
            ),
        )

