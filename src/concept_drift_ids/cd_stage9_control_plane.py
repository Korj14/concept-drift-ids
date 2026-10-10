from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
import torch

from concept_drift_ids.cd_control_plane import (
    ONLINE_RESERVOIR_SEED,
    PRIMARY_CURRENT_WINDOW,
    PRIMARY_ONLINE_RESERVOIR_CAPACITY,
    DelayedLabelQueue,
    MatureLabelRecord,
    NeuralUpdateConfig,
    ReservoirItem,
    UniformReservoir,
    adapt_neural_checkpoint,
    canonical_sha256,
    row_ids_sha256,
    select_recent_current_evidence,
    select_replay_ids,
    state_dict_sha256,
    write_checkpoint_new,
)
from concept_drift_ids.cd_evidence import (
    build_checkpoint_record,
    build_event,
    build_shared_identity,
    records_sha256,
    verify_checkpoint_chain,
)
from concept_drift_ids.cd_shared_runner import (
    AnchorRow,
    SharedTrajectory,
    StreamRow,
    verify_shared_trajectory,
)
from concept_drift_ids.cd_stage9_config import PAGE_HINKLEY_CONFIG
from concept_drift_ids.neural import BinaryMLP


DETECTOR_KINDS = (
    "adwin_hard_error",
    "page_hinkley_hard_error",
    "adwin_brier",
)
REPLAY_MODES = ("primary", "none")


@dataclass(frozen=True)
class Stage9ControlPlaneConfig:
    label_latency: int = 5_000
    current_window: int = PRIMARY_CURRENT_WINDOW
    reservoir_capacity: int = PRIMARY_ONLINE_RESERVOIR_CAPACITY
    replay_mode: str = "primary"
    detector_kind: str = "adwin_hard_error"
    neural_update: NeuralUpdateConfig = field(default_factory=NeuralUpdateConfig)

    def validate(self) -> None:
        if self.label_latency < 0:
            raise ValueError("label_latency must be non-negative")
        if self.current_window != PRIMARY_CURRENT_WINDOW:
            raise ValueError("Stage-9 current mature window must remain 10,000 rows.")
        if self.reservoir_capacity != PRIMARY_ONLINE_RESERVOIR_CAPACITY:
            raise ValueError("Stage-9 reservoir capacity must remain primary.")
        if self.replay_mode not in REPLAY_MODES:
            raise ValueError(f"Unsupported replay mode: {self.replay_mode}")
        if self.detector_kind not in DETECTOR_KINDS:
            raise ValueError(f"Unsupported detector kind: {self.detector_kind}")
        if self.neural_update != NeuralUpdateConfig():
            raise ValueError("Stage-9 neural optimizer/update budget must remain primary.")

    @property
    def replay_anchor_rows(self) -> int:
        return 5_000 if self.replay_mode == "primary" else 0

    @property
    def replay_online_rows(self) -> int:
        return 5_000 if self.replay_mode == "primary" else 0


@dataclass(frozen=True)
class Stage9DetectorObservation:
    row_id: str
    origin_index: int
    maturity_index: int
    epoch_id: int
    epoch_checkpoint_sha256: str
    prediction_checkpoint_sha256: str
    signal_kind: str
    signal: float | None
    hard_error: int | None
    admitted: bool
    drift_detected: bool
    reason: str


class Stage9DriftMonitor:
    """Checkpoint-pure delayed detector for the frozen Stage-9 variants."""

    def __init__(self, *, monitor_threshold: float, detector_kind: str) -> None:
        if not 0.0 <= monitor_threshold <= 1.0:
            raise ValueError("monitor_threshold must be in [0,1]")
        if detector_kind not in DETECTOR_KINDS:
            raise ValueError(f"Unsupported detector kind: {detector_kind}")
        self.monitor_threshold = float(monitor_threshold)
        self.detector_kind = str(detector_kind)
        self.epoch_id = 0
        self.epoch_checkpoint_sha256: str | None = None
        self.disarmed = True
        self.event_count = 0
        self.input_count = 0
        self._detector: Any = None

    def _new_detector(self) -> Any:
        if self.detector_kind in {"adwin_hard_error", "adwin_brier"}:
            from river.drift import ADWIN

            return ADWIN(
                delta=0.002,
                clock=32,
                max_buckets=5,
                min_window_length=5,
                grace_period=10,
            )
        from river.drift import PageHinkley

        return PageHinkley(**PAGE_HINKLEY_CONFIG)

    def start_initial_epoch(self, checkpoint_sha256: str) -> None:
        if self.epoch_checkpoint_sha256 is not None:
            raise RuntimeError("Initial detector epoch already started.")
        self.epoch_id = 1
        self.epoch_checkpoint_sha256 = str(checkpoint_sha256)
        self._detector = self._new_detector()
        self.disarmed = False
        self.input_count = 0

    def publish_child_checkpoint(self, checkpoint_sha256: str) -> None:
        if not self.disarmed:
            raise RuntimeError(
                "Child checkpoint may start a detector epoch only after prior detection."
            )
        self.epoch_id += 1
        self.epoch_checkpoint_sha256 = str(checkpoint_sha256)
        self._detector = self._new_detector()
        self.disarmed = False
        self.input_count = 0

    def _signals(self, record: MatureLabelRecord) -> tuple[float, int]:
        decision = int(record.neural_probability >= self.monitor_threshold)
        hard_error = int(decision != record.true_label)
        if self.detector_kind == "adwin_brier":
            signal = float(
                (float(record.neural_probability) - float(record.true_label)) ** 2
            )
        else:
            signal = float(hard_error)
        return signal, hard_error

    def observe(self, record: MatureLabelRecord) -> Stage9DetectorObservation:
        if self.epoch_checkpoint_sha256 is None:
            raise RuntimeError("Detector epoch has not been initialized.")

        common = {
            "row_id": record.row_id,
            "origin_index": record.origin_index,
            "maturity_index": record.maturity_index,
            "epoch_id": self.epoch_id,
            "epoch_checkpoint_sha256": self.epoch_checkpoint_sha256,
            "prediction_checkpoint_sha256": record.checkpoint_sha256,
            "signal_kind": self.detector_kind,
        }
        if self.disarmed:
            return Stage9DetectorObservation(
                **common,
                signal=None,
                hard_error=None,
                admitted=False,
                drift_detected=False,
                reason="detector_disarmed",
            )
        if record.checkpoint_sha256 != self.epoch_checkpoint_sha256:
            return Stage9DetectorObservation(
                **common,
                signal=None,
                hard_error=None,
                admitted=False,
                drift_detected=False,
                reason="stale_checkpoint_observation",
            )

        signal, hard_error = self._signals(record)
        if not 0.0 <= signal <= 1.0:
            raise AssertionError("Frozen detector signal must lie in [0,1].")
        self._detector.update(signal)
        self.input_count += 1
        detected = bool(self._detector.drift_detected)
        if detected:
            self.event_count += 1
            self.disarmed = True
        return Stage9DetectorObservation(
            **common,
            signal=signal,
            hard_error=hard_error,
            admitted=True,
            drift_detected=detected,
            reason="drift_detected" if detected else "admitted",
        )


class Stage9SharedControlPlaneRunner:
    """Shared Stage-9 neural trajectory with no symbolic feedback path."""

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
        condition_id: str,
        config: Stage9ControlPlaneConfig,
    ) -> None:
        config.validate()
        if not anchor_rows:
            raise ValueError("anchor_rows must not be empty")
        anchor_ids = [row.row_id for row in anchor_rows]
        if len(set(anchor_ids)) != len(anchor_ids):
            raise ValueError("anchor row IDs must be unique")
        if config.replay_mode == "primary" and len(anchor_rows) < 10_000:
            raise ValueError("Primary replay mode requires the frozen 10,000-row anchor.")

        self.seed = int(seed)
        self.initial_model = initial_model.cpu()
        self.initial_checkpoint_sha256 = str(initial_checkpoint_sha256)
        self.monitor_threshold = float(monitor_threshold)
        self.anchor_rows = tuple(anchor_rows)
        self.anchor_by_id = {row.row_id: row for row in anchor_rows}
        self.checkpoint_dir = Path(checkpoint_dir)
        self.run_id = str(run_id)
        self.git_commit = str(git_commit)
        self.condition_id = str(condition_id)
        self.config = config
        self.config_sha256 = canonical_sha256(
            {
                "seed": self.seed,
                "condition_id": self.condition_id,
                "monitor_threshold": self.monitor_threshold,
                "control_plane": asdict(config),
            }
        )

    @staticmethod
    @torch.inference_mode()
    def _predict_one(model: BinaryMLP, features: np.ndarray) -> float:
        array = np.asarray(features, dtype=np.float32)
        if array.ndim != 1 or not np.isfinite(array).all():
            raise ValueError("Each Stage-9 stream row requires one finite feature vector.")
        model.eval()
        return float(torch.sigmoid(model(torch.from_numpy(array[None, :]))).item())

    def run(self, rows: Sequence[StreamRow]) -> SharedTrajectory:
        stream_ids = [row.row_id for row in rows]
        if len(set(stream_ids)) != len(stream_ids):
            raise ValueError("stream row IDs must be unique")
        if set(stream_ids).intersection(self.anchor_by_id):
            raise ValueError("Anchor and stream row IDs must be disjoint.")

        queue = DelayedLabelQueue(self.config.label_latency)
        monitor = Stage9DriftMonitor(
            monitor_threshold=self.monitor_threshold,
            detector_kind=self.config.detector_kind,
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
                evidence_sha256=canonical_sha256(
                    {
                        "source": "accepted_initial",
                        "stage9_condition_id": self.condition_id,
                    }
                ),
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
                active_model,
                stream_features_by_id[row.row_id],
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
                    payload={
                        "neural_probability": probability,
                        "stage9_condition_id": self.condition_id,
                    },
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
                        payload={"stage9_condition_id": self.condition_id},
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
                            "stage9_condition_id": self.condition_id,
                            "detector_kind": self.config.detector_kind,
                            "epoch_id": observed.epoch_id,
                            "epoch_checkpoint_sha256": (
                                observed.epoch_checkpoint_sha256
                            ),
                            "admitted": observed.admitted,
                            "signal": observed.signal,
                            "hard_error": observed.hard_error,
                            "drift_detected": observed.drift_detected,
                        },
                    )
                )

                if observed.drift_detected:
                    if pending is not None:
                        raise AssertionError(
                            "Detector event occurred with an outstanding neural transaction."
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
                            payload={
                                "stage9_condition_id": self.condition_id,
                                "detector_kind": self.config.detector_kind,
                            },
                        )
                    )

            if pending is None:
                continue

            current = select_recent_current_evidence(
                mature_history,
                parent_checkpoint_sha256=pending["parent_checkpoint_sha256"],
                action_clock=logical_clock,
                window_size=self.config.current_window,
            )
            if current is None:
                continue

            current_ids = [record.row_id for record in current]
            if self.config.replay_mode == "primary":
                replay_ids = select_replay_ids(
                    anchor_ids=[row.row_id for row in self.anchor_rows],
                    online_items=reservoir.items(),
                    current_row_ids=current_ids,
                    event_id=int(pending["event_id"]),
                    anchor_rows=5_000,
                    online_rows=5_000,
                )
            else:
                replay_ids = ()
            if self.config.replay_mode == "none" and replay_ids:
                raise AssertionError("No-replay condition selected replay rows.")

            def lookup(row_id: str) -> tuple[np.ndarray, int]:
                if row_id in self.anchor_by_id:
                    anchor = self.anchor_by_id[row_id]
                    return np.asarray(anchor.features, dtype=np.float32), int(anchor.label)
                features = stream_features_by_id[row_id]
                matched = next(
                    item for item in mature_history if item.row_id == row_id
                )
                return np.asarray(features, dtype=np.float32), int(matched.true_label)

            current_X = np.stack(
                [
                    np.asarray(stream_features_by_id[record.row_id], dtype=np.float32)
                    for record in current
                ]
            )
            current_y = np.asarray(
                [record.true_label for record in current],
                dtype=np.int8,
            )

            if replay_ids:
                replay_pairs = [lookup(row_id) for row_id in replay_ids]
                replay_X = np.stack([pair[0] for pair in replay_pairs])
                replay_y = np.asarray([pair[1] for pair in replay_pairs], dtype=np.int8)
            else:
                replay_X = np.empty(
                    (0, int(current_X.shape[1])),
                    dtype=np.float32,
                )
                replay_y = np.empty((0,), dtype=np.int8)

            evidence = {
                "condition_id": self.condition_id,
                "detector_kind": self.config.detector_kind,
                "replay_mode": self.config.replay_mode,
                "event_id": int(pending["event_id"]),
                "confirmation_clock": int(pending["confirmation_clock"]),
                "action_clock": logical_clock,
                "parent_checkpoint_sha256": pending["parent_checkpoint_sha256"],
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
                    "condition_id": self.condition_id,
                    "seed": self.seed,
                    "event_id": int(pending["event_id"]),
                    "parent_checkpoint_sha256": pending["parent_checkpoint_sha256"],
                    "parent_state_sha256": pending["parent_state_sha256"],
                    "evidence_sha256": evidence_sha256,
                    "config_sha256": self.config_sha256,
                    "shuffle_seed": update.shuffle_seed,
                    "epoch_losses": list(update.epoch_losses),
                    "publication_effective_index": logical_clock + 1,
                    "replay_mode": self.config.replay_mode,
                    "detector_kind": self.config.detector_kind,
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
                        "stage9_condition_id": self.condition_id,
                        "publication_effective_index": logical_clock + 1,
                        "child_state_sha256": active_state_sha256,
                        "replay_mode": self.config.replay_mode,
                        "detector_kind": self.config.detector_kind,
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
                    neural_checkpoint_sha256=pending["parent_checkpoint_sha256"],
                    config_sha256=self.config_sha256,
                    git_commit=self.git_commit,
                    reason="insufficient_mature_current_evidence_before_stream_end",
                    payload={"stage9_condition_id": self.condition_id},
                )
            )

        verify_checkpoint_chain(checkpoint_chain)
        shared_identity = build_shared_identity(
            label_schedule_sha256=records_sha256(label_schedule),
            detector_events_sha256=records_sha256(detector_observations),
            replay_evidence_sha256=records_sha256(replay_transactions),
            checkpoint_chain_sha256=records_sha256(checkpoint_chain),
        )
        trajectory = SharedTrajectory(
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
            pending_neural_transaction=(dict(pending) if pending is not None else None),
        )
        verify_stage9_shared_trajectory(
            trajectory,
            config=self.config,
            condition_id=self.condition_id,
        )
        return trajectory


def verify_stage9_shared_trajectory(
    trajectory: SharedTrajectory,
    *,
    config: Stage9ControlPlaneConfig,
    condition_id: str,
) -> None:
    config.validate()
    verify_shared_trajectory(
        trajectory,
        label_latency=config.label_latency,
    )

    for observation in trajectory.detector_observations:
        if observation["signal_kind"] != config.detector_kind:
            raise ValueError("Detector signal kind differs from Stage-9 condition.")
        if observation["admitted"]:
            signal = float(observation["signal"])
            if not 0.0 <= signal <= 1.0:
                raise ValueError("Admitted detector signal lies outside [0,1].")
            if config.detector_kind == "adwin_brier":
                # Brier is continuous; equality to hard error is not required.
                pass
            else:
                if signal != float(observation["hard_error"]):
                    raise ValueError("Hard-error detector signal mismatch.")
        else:
            if observation["signal"] is not None:
                raise ValueError("Non-admitted detector observation exposed a signal.")

    for transaction in trajectory.replay_transactions:
        if transaction["condition_id"] != condition_id:
            raise ValueError("Replay transaction condition identity mismatch.")
        if transaction["detector_kind"] != config.detector_kind:
            raise ValueError("Replay transaction detector identity mismatch.")
        if transaction["replay_mode"] != config.replay_mode:
            raise ValueError("Replay transaction replay-mode mismatch.")
        current = set(transaction["current_row_ids"])
        replay = set(transaction["replay_row_ids"])
        if current.intersection(replay):
            raise ValueError("Replay/current evidence overlap.")
        if len(transaction["current_row_ids"]) != PRIMARY_CURRENT_WINDOW:
            raise ValueError("Stage-9 current mature window changed.")
        if config.replay_mode == "none":
            if transaction["replay_row_ids"]:
                raise ValueError("No-replay transaction contains replay rows.")
        elif len(transaction["replay_row_ids"]) != 10_000:
            raise ValueError("Primary replay budget changed.")

    for event in trajectory.events:
        payload = event.get("payload") or {}
        if "boundary" in payload or "boundary_index" in payload:
            raise ValueError("Boundary metadata entered Stage-9 adaptive event payload.")
        if payload.get("stage9_condition_id") not in {None, condition_id}:
            raise ValueError("Stage-9 event condition identity mismatch.")
