from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
import torch

from concept_drift_ids.cd_control_plane import (
    ONLINE_RESERVOIR_SEED,
    PRIMARY_ANCHOR_CAPACITY,
    PRIMARY_CURRENT_WINDOW,
    PRIMARY_LABEL_LATENCY,
    PRIMARY_ONLINE_RESERVOIR_CAPACITY,
    PRIMARY_REPLAY_ANCHOR_ROWS,
    PRIMARY_REPLAY_ONLINE_ROWS,
    DelayedLabelQueue,
    MatureLabelRecord,
    NeuralUpdateConfig,
    ReservoirItem,
    SYSTEM_A_MONITOR_THRESHOLDS,
    UniformReservoir,
    adapt_neural_checkpoint,
    canonical_sha256,
    row_ids_sha256,
    select_recent_current_evidence,
    select_replay_ids,
    state_dict_sha256,
    write_checkpoint_new,
    write_json_new,
)
from concept_drift_ids.cd_evidence import (
    build_checkpoint_record,
    build_event,
    build_shared_identity,
    records_sha256,
    verify_checkpoint_chain,
    write_jsonl_new,
)
from concept_drift_ids.neural import BinaryMLP
from concept_drift_ids.cd_stage9_monitor import Stage9DriftMonitor


@dataclass(frozen=True)
class StreamRow:
    row_id: str
    features: np.ndarray
    label: int


@dataclass(frozen=True)
class AnchorRow:
    row_id: str
    features: np.ndarray
    label: int


@dataclass(frozen=True)
class Stage9ControlPlaneConfig:
    label_latency: int = PRIMARY_LABEL_LATENCY
    current_window: int = PRIMARY_CURRENT_WINDOW
    reservoir_capacity: int = PRIMARY_ONLINE_RESERVOIR_CAPACITY
    replay_anchor_rows: int = PRIMARY_REPLAY_ANCHOR_ROWS
    replay_online_rows: int = PRIMARY_REPLAY_ONLINE_ROWS
    detector_family: str = "adwin"
    detector_signal: str = "hard_error"
    detector_config: Mapping[str, Any] | None = None
    replay_enabled: bool = True
    neural_update: NeuralUpdateConfig = field(default_factory=NeuralUpdateConfig)

    def validate(self) -> None:
        if self.label_latency < 0:
            raise ValueError("label_latency must be non-negative")
        if self.current_window <= 0:
            raise ValueError("current_window must be positive")
        if self.reservoir_capacity <= 0:
            raise ValueError("reservoir_capacity must be positive")
        if self.replay_anchor_rows < 0 or self.replay_online_rows < 0:
            raise ValueError("replay row budgets must be non-negative")
        if self.detector_family not in {"adwin", "page_hinkley"}:
            raise ValueError("unsupported detector_family")
        if self.detector_signal not in {"hard_error", "brier"}:
            raise ValueError("unsupported detector_signal")
        if self.detector_family == "page_hinkley" and self.detector_signal != "hard_error":
            raise ValueError("PageHinkley robustness is frozen to hard_error")
        if not self.replay_enabled and (self.replay_anchor_rows != 0 or self.replay_online_rows != 0):
            raise ValueError("no-replay condition must set both replay budgets to zero")


@dataclass(frozen=True)
class SharedTrajectory:
    seed: int
    config_sha256: str
    predictions: tuple[dict[str, Any], ...]
    label_schedule: tuple[dict[str, Any], ...]
    detector_observations: tuple[dict[str, Any], ...]
    events: tuple[dict[str, Any], ...]
    replay_transactions: tuple[dict[str, Any], ...]
    checkpoint_chain: tuple[dict[str, Any], ...]
    shared_identity: Mapping[str, str]
    final_checkpoint_sha256: str
    final_state_sha256: str
    pending_labels: int
    pending_neural_transaction: Mapping[str, Any] | None


class Stage9SharedControlPlaneRunner:
    """Dataset-agnostic shared detector/neural trajectory generator.

    The runner has no scenario loader and cannot inspect pre/post boundary metadata.
    Callers provide already ordered feature/label rows and an exact frozen anchor.
    """

    def __init__(
        self,
        *,
        seed: int,
        initial_model: BinaryMLP,
        initial_checkpoint_sha256: str,
        monitor_threshold: float,
        anchor_rows: Sequence[AnchorRow],
        checkpoint_dir: Path,
        run_id: str,
        git_commit: str,
        config: Stage9ControlPlaneConfig = Stage9ControlPlaneConfig(),
    ) -> None:
        config.validate()
        if not anchor_rows:
            raise ValueError("anchor_rows must not be empty")
        anchor_ids = [row.row_id for row in anchor_rows]
        if len(set(anchor_ids)) != len(anchor_ids):
            raise ValueError("anchor row IDs must be unique")
        if config.replay_enabled and len(anchor_rows) < (
            config.replay_anchor_rows + config.replay_online_rows
        ):
            raise ValueError(
                "Anchor evidence must be large enough to fill a complete replay "
                "budget if online replay is unavailable."
            )

        self.seed = int(seed)
        self.initial_model = initial_model.cpu()
        self.initial_checkpoint_sha256 = str(initial_checkpoint_sha256)
        self.monitor_threshold = float(monitor_threshold)
        self.anchor_rows = tuple(anchor_rows)
        self.anchor_by_id = {row.row_id: row for row in anchor_rows}
        self.checkpoint_dir = Path(checkpoint_dir)
        self.run_id = str(run_id)
        self.git_commit = str(git_commit)
        self.config = config
        self.config_sha256 = canonical_sha256(
            {
                "seed": self.seed,
                "monitor_threshold": self.monitor_threshold,
                "control_plane": asdict(config),
            }
        )

    @staticmethod
    @torch.inference_mode()
    def _predict_one(model: BinaryMLP, features: np.ndarray) -> float:
        array = np.asarray(features, dtype=np.float32)
        if array.ndim != 1:
            raise ValueError("Each stream row must contain one feature vector.")
        if not np.isfinite(array).all():
            raise ValueError("Stream features must be finite.")
        model.eval()
        tensor = torch.from_numpy(array[None, :])
        probability = torch.sigmoid(model(tensor)).item()
        return float(probability)

    def run(self, rows: Sequence[StreamRow]) -> SharedTrajectory:
        stream_ids = [row.row_id for row in rows]
        if len(set(stream_ids)) != len(stream_ids):
            raise ValueError("stream row IDs must be unique")
        if set(stream_ids).intersection(self.anchor_by_id):
            raise ValueError(
                "Anchor and stream row IDs must use disjoint audit namespaces."
            )

        queue = DelayedLabelQueue(self.config.label_latency)
        monitor = Stage9DriftMonitor(
            family=self.config.detector_family,
            signal=self.config.detector_signal,
            monitor_threshold=self.monitor_threshold,
            detector_config=self.config.detector_config,
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
            if row.label not in (0, 1):
                raise ValueError("Stream labels must be binary.")
            stream_features_by_id[row.row_id] = np.asarray(
                row.features, dtype=np.float32
            ).copy()

            probability = self._predict_one(
                active_model, stream_features_by_id[row.row_id]
            )
            prediction = queue.commit_prediction(
                row_id=row.row_id,
                origin_index=logical_clock,
                checkpoint_sha256=active_checkpoint_sha256,
                neural_probability=probability,
                true_label=row.label,
            )
            predictions.append(
                {
                    **prediction.public_prediction_payload(),
                    "logical_clock": logical_clock,
                }
            )
            label_schedule.append(
                {
                    "row_id": row.row_id,
                    "origin_index": logical_clock,
                    "maturity_index": prediction.maturity_index,
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
                    maturity_index=prediction.maturity_index,
                    neural_checkpoint_sha256=active_checkpoint_sha256,
                    config_sha256=self.config_sha256,
                    git_commit=self.git_commit,
                    payload={"neural_probability": probability},
                )
            )

            released = queue.release_after_prediction(logical_clock)
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
                            "signal_name": observed.signal_name,
                            "signal_value": observed.signal_value,
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
            replay_ids = (
                select_replay_ids(
                    anchor_ids=[row.row_id for row in self.anchor_rows],
                    online_items=reservoir.items(),
                    current_row_ids=current_ids,
                    event_id=int(pending["event_id"]),
                    anchor_rows=self.config.replay_anchor_rows,
                    online_rows=self.config.replay_online_rows,
                )
                if self.config.replay_enabled
                else ()
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
            if replay_pairs:
                replay_X = np.stack([pair[0] for pair in replay_pairs])
                replay_y = np.asarray([pair[1] for pair in replay_pairs], dtype=np.int8)
            else:
                replay_X = np.empty((0, current_X.shape[1]), dtype=np.float32)
                replay_y = np.empty((0,), dtype=np.int8)

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
                "replay_enabled": self.config.replay_enabled,
                "detector_family": self.config.detector_family,
                "detector_signal": self.config.detector_signal,
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
            pending_labels=queue.pending_count(),
            pending_neural_transaction=(
                dict(pending) if pending is not None else None
            ),
        )



def freeze_stage9_shared_trajectory(
    output_dir: Path,
    trajectory: SharedTrajectory,
) -> dict[str, dict[str, str]]:
    """Freeze one shared trajectory as non-overwriting compact evidence."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    payloads: dict[str, Sequence[Mapping[str, Any]]] = {
        "predictions": trajectory.predictions,
        "label_schedule": trajectory.label_schedule,
        "detector_observations": trajectory.detector_observations,
        "events": trajectory.events,
        "replay_transactions": trajectory.replay_transactions,
        "checkpoint_chain": trajectory.checkpoint_chain,
    }
    files: dict[str, dict[str, str]] = {}
    for name, records in payloads.items():
        path = output_dir / f"{name}.jsonl"
        digest = write_jsonl_new(
            path,
            list(records),
            validate=(name == "events"),
        )
        files[name] = {
            "path": path.name,
            "sha256": digest,
        }

    identity_path = output_dir / "shared_identity.json"
    digest = write_json_new(
        identity_path,
        {
            "schema_version": 1,
            "seed": trajectory.seed,
            "config_sha256": trajectory.config_sha256,
            "shared_identity": dict(trajectory.shared_identity),
            "final_checkpoint_sha256": trajectory.final_checkpoint_sha256,
            "final_state_sha256": trajectory.final_state_sha256,
            "pending_labels": trajectory.pending_labels,
            "pending_neural_transaction": (
                dict(trajectory.pending_neural_transaction)
                if trajectory.pending_neural_transaction is not None
                else None
            ),
        },
    )
    files["shared_identity"] = {
        "path": identity_path.name,
        "sha256": digest,
    }
    return files



def verify_stage9_shared_trajectory(
    trajectory: SharedTrajectory,
    *,
    label_latency: int,
) -> None:
    if len(trajectory.predictions) != len(trajectory.label_schedule):
        raise ValueError("Prediction/label-schedule length mismatch.")

    for expected_index, (prediction, schedule) in enumerate(
        zip(trajectory.predictions, trajectory.label_schedule)
    ):
        if int(prediction["origin_index"]) != expected_index:
            raise ValueError("Prediction origin indices are not contiguous.")
        if int(schedule["origin_index"]) != expected_index:
            raise ValueError("Label schedule origin indices are not contiguous.")
        if schedule["row_id"] != prediction["row_id"]:
            raise ValueError("Prediction/label-schedule row identity mismatch.")
        expected_maturity = expected_index + int(label_latency)
        if int(schedule["maturity_index"]) != expected_maturity:
            raise ValueError("Label maturity schedule violates frozen latency.")
        if int(prediction["maturity_index"]) != expected_maturity:
            raise ValueError("Prediction record maturity index mismatch.")

    for observation in trajectory.detector_observations:
        if observation["admitted"] and (
            observation["prediction_checkpoint_sha256"]
            != observation["epoch_checkpoint_sha256"]
        ):
            raise ValueError("Checkpoint-impure detector observation admitted.")
        if int(observation["maturity_index"]) < int(
            observation["origin_index"]
        ):
            raise ValueError("Detector observation maturity precedes origin.")

    for event in trajectory.events:
        if event["event_type"] in {"label_release", "detector_observation"}:
            if int(event["maturity_index"]) > int(event["logical_clock"]):
                raise ValueError("Label-dependent event precedes maturity.")
        if event["event_type"] == "neural_publication":
            effective = int(event["payload"]["publication_effective_index"])
            if effective != int(event["logical_clock"]) + 1:
                raise ValueError(
                    "Neural publication must become effective next logical row."
                )

    verify_checkpoint_chain(trajectory.checkpoint_chain)

    expected_identity = build_shared_identity(
        label_schedule_sha256=records_sha256(trajectory.label_schedule),
        detector_events_sha256=records_sha256(
            trajectory.detector_observations
        ),
        replay_evidence_sha256=records_sha256(
            trajectory.replay_transactions
        ),
        checkpoint_chain_sha256=records_sha256(
            trajectory.checkpoint_chain
        ),
    )
    if dict(trajectory.shared_identity) != expected_identity:
        raise ValueError("Shared trajectory identity hash mismatch.")

    if trajectory.checkpoint_chain:
        final = trajectory.checkpoint_chain[-1]
        if final["checkpoint_file_sha256"] != trajectory.final_checkpoint_sha256:
            raise ValueError("Final checkpoint file identity mismatch.")
        if final["child_state_sha256"] != trajectory.final_state_sha256:
            raise ValueError("Final checkpoint state identity mismatch.")


def verify_stage9_control_plane_configuration(
    *,
    seed: int,
    monitor_threshold: float,
    anchor_row_count: int,
    config: Stage9ControlPlaneConfig,
) -> None:
    config.validate()
    if seed not in SYSTEM_A_MONITOR_THRESHOLDS:
        raise ValueError(f"Unsupported frozen seed: {seed}")
    expected = SYSTEM_A_MONITOR_THRESHOLDS[seed]
    if float(monitor_threshold) != float(expected):
        raise ValueError("Monitor threshold differs from the frozen seed threshold.")
    if int(anchor_row_count) != PRIMARY_ANCHOR_CAPACITY:
        raise ValueError("Training anchor row count differs from frozen capacity.")
    if config.current_window != PRIMARY_CURRENT_WINDOW:
        raise ValueError("Stage-9 current-window budget must match the primary.")
    if config.reservoir_capacity != PRIMARY_ONLINE_RESERVOIR_CAPACITY:
        raise ValueError("Stage-9 reservoir capacity must match the primary.")
    if config.replay_enabled:
        if config.replay_anchor_rows != PRIMARY_REPLAY_ANCHOR_ROWS:
            raise ValueError("Replay anchor budget changed outside no-replay ablation.")
        if config.replay_online_rows != PRIMARY_REPLAY_ONLINE_ROWS:
            raise ValueError("Replay online budget changed outside no-replay ablation.")
    else:
        if config.replay_anchor_rows != 0 or config.replay_online_rows != 0:
            raise ValueError("No-replay must have zero replay rows.")
