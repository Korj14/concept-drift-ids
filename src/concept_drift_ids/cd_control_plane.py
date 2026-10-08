from __future__ import annotations

import copy
import hashlib
import json
import random
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

from concept_drift_ids.neural import BinaryMLP, set_reproducible_seed
from concept_drift_ids.scenario_manifest import sha256_file


PRIMARY_LABEL_LATENCY = 5_000
PRIMARY_CURRENT_WINDOW = 10_000
PRIMARY_ANCHOR_CAPACITY = 10_000
PRIMARY_ONLINE_RESERVOIR_CAPACITY = 10_000
PRIMARY_REPLAY_ROWS = 10_000
PRIMARY_REPLAY_ANCHOR_ROWS = 5_000
PRIMARY_REPLAY_ONLINE_ROWS = 5_000
PRIMARY_POS_WEIGHT = 4.138247558496975
PRIMARY_LEARNING_RATE = 1e-4
PRIMARY_WEIGHT_DECAY = 1e-5
PRIMARY_BATCH_SIZE = 1_024
PRIMARY_EPOCHS = 5

ANCHOR_SEED = 20261008
ONLINE_RESERVOIR_SEED = 20261009
REPLAY_SAMPLE_SEED_BASE = 20261010
ADAPTATION_SHUFFLE_SEED_BASE = 20261011

ADWIN_CONFIG = {
    "delta": 0.002,
    "clock": 32,
    "max_buckets": 5,
    "min_window_length": 5,
    "grace_period": 10,
}

SYSTEM_A_MONITOR_THRESHOLDS = {
    0: 0.939024031162262,
    1: 0.9333740472793579,
    2: 0.9121250510215759,
    3: 0.9789621233940125,
    4: 0.954619288444519,
}

PROHIBITED_ADAPTIVE_KEYS = {
    "boundary",
    "boundary_flag",
    "is_post_drift",
    "post_drift",
    "pre_drift",
    "pre_post",
    "synthetic_boundary",
}


def canonical_json_bytes(payload: Any) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def canonical_sha256(payload: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


def row_ids_sha256(row_ids: Iterable[str]) -> str:
    return canonical_sha256(list(row_ids))


def write_json_new(path: Path, payload: Mapping[str, Any]) -> str:
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite existing artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    body = dict(payload)
    body.setdefault("payload_sha256", canonical_sha256(body))
    path.write_text(
        json.dumps(body, sort_keys=True, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return sha256_file(path)


@dataclass(frozen=True)
class PredictionRecord:
    row_id: str
    origin_index: int
    maturity_index: int
    checkpoint_sha256: str
    neural_probability: float
    true_label: int

    def public_prediction_payload(self) -> dict[str, Any]:
        return {
            "row_id": self.row_id,
            "origin_index": self.origin_index,
            "maturity_index": self.maturity_index,
            "checkpoint_sha256": self.checkpoint_sha256,
            "neural_probability": self.neural_probability,
        }


@dataclass(frozen=True)
class MatureLabelRecord:
    row_id: str
    origin_index: int
    maturity_index: int
    checkpoint_sha256: str
    neural_probability: float
    true_label: int


class DelayedLabelQueue:
    """Prediction-first label release under a fixed logical-row latency."""

    def __init__(self, latency: int = PRIMARY_LABEL_LATENCY) -> None:
        if latency < 0:
            raise ValueError("latency must be non-negative")
        self.latency = int(latency)
        self._records: dict[int, PredictionRecord] = {}
        self._committed_clocks: set[int] = set()
        self._released_origins: set[int] = set()

    def commit_prediction(
        self,
        *,
        row_id: str,
        origin_index: int,
        checkpoint_sha256: str,
        neural_probability: float,
        true_label: int,
    ) -> PredictionRecord:
        if origin_index in self._records:
            raise ValueError(f"Duplicate prediction origin_index={origin_index}")
        if true_label not in (0, 1):
            raise ValueError("true_label must be binary")
        if not np.isfinite(neural_probability) or not 0.0 <= neural_probability <= 1.0:
            raise ValueError("neural_probability must be finite in [0,1]")
        record = PredictionRecord(
            row_id=str(row_id),
            origin_index=int(origin_index),
            maturity_index=int(origin_index) + self.latency,
            checkpoint_sha256=str(checkpoint_sha256),
            neural_probability=float(neural_probability),
            true_label=int(true_label),
        )
        self._records[record.origin_index] = record
        self._committed_clocks.add(record.origin_index)
        return record

    def release_after_prediction(self, logical_clock: int) -> list[MatureLabelRecord]:
        if logical_clock not in self._committed_clocks:
            raise RuntimeError(
                "Label release requires the prediction at the same logical clock "
                "to be committed first."
            )
        released: list[MatureLabelRecord] = []
        for origin_index in sorted(self._records):
            record = self._records[origin_index]
            if record.maturity_index != logical_clock:
                continue
            if origin_index in self._released_origins:
                continue
            self._released_origins.add(origin_index)
            released.append(
                MatureLabelRecord(
                    row_id=record.row_id,
                    origin_index=record.origin_index,
                    maturity_index=record.maturity_index,
                    checkpoint_sha256=record.checkpoint_sha256,
                    neural_probability=record.neural_probability,
                    true_label=record.true_label,
                )
            )
        return released

    def pending_count(self) -> int:
        return len(self._records) - len(self._released_origins)

    def pending_origin_indices(self) -> list[int]:
        return sorted(set(self._records) - self._released_origins)


@dataclass(frozen=True)
class ReservoirItem:
    row_id: str
    origin_index: int
    maturity_index: int
    checkpoint_sha256: str
    label: int


class UniformReservoir:
    """Treatment-independent uniform reservoir over mature stream rows."""

    def __init__(self, *, capacity: int, seed: int) -> None:
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        self.capacity = int(capacity)
        self.seed = int(seed)
        self._rng = random.Random(self.seed)
        self._seen = 0
        self._items: list[ReservoirItem] = []

    @property
    def seen(self) -> int:
        return self._seen

    def consider(self, item: ReservoirItem) -> None:
        self._seen += 1
        if len(self._items) < self.capacity:
            self._items.append(item)
            return
        slot = self._rng.randrange(self._seen)
        if slot < self.capacity:
            self._items[slot] = item

    def items(self) -> tuple[ReservoirItem, ...]:
        return tuple(self._items)

    def row_ids(self) -> tuple[str, ...]:
        return tuple(item.row_id for item in self._items)

    def identity_sha256(self) -> str:
        return canonical_sha256(
            {
                "capacity": self.capacity,
                "seed": self.seed,
                "seen": self._seen,
                "items": [asdict(item) for item in self._items],
            }
        )


def select_uniform_anchor_ids(
    row_ids: Sequence[str],
    *,
    capacity: int = PRIMARY_ANCHOR_CAPACITY,
    seed: int = ANCHOR_SEED,
) -> tuple[str, ...]:
    unique_position_ids = list(row_ids)
    if len(unique_position_ids) < capacity:
        raise ValueError(
            f"Need at least {capacity} training rows for the primary anchor."
        )
    rng = random.Random(seed)
    indices = rng.sample(range(len(unique_position_ids)), capacity)
    return tuple(unique_position_ids[index] for index in indices)


def select_recent_current_evidence(
    records: Sequence[MatureLabelRecord],
    *,
    parent_checkpoint_sha256: str,
    action_clock: int,
    window_size: int = PRIMARY_CURRENT_WINDOW,
) -> tuple[MatureLabelRecord, ...] | None:
    eligible = [
        record
        for record in records
        if record.checkpoint_sha256 == parent_checkpoint_sha256
        and record.origin_index <= action_clock
        and record.maturity_index <= action_clock
    ]
    eligible.sort(key=lambda item: (item.maturity_index, item.origin_index, item.row_id))
    if len(eligible) < window_size:
        return None
    return tuple(eligible[-window_size:])


def select_replay_ids(
    *,
    anchor_ids: Sequence[str],
    online_items: Sequence[ReservoirItem],
    current_row_ids: Iterable[str],
    event_id: int,
    anchor_rows: int = PRIMARY_REPLAY_ANCHOR_ROWS,
    online_rows: int = PRIMARY_REPLAY_ONLINE_ROWS,
) -> tuple[str, ...]:
    current = set(current_row_ids)
    anchor_pool = [row_id for row_id in anchor_ids if row_id not in current]
    online_pool = [
        item.row_id for item in online_items if item.row_id not in current
    ]
    if len(anchor_pool) < anchor_rows:
        raise ValueError("Insufficient eligible anchor rows for replay.")

    rng = random.Random(REPLAY_SAMPLE_SEED_BASE + int(event_id))
    chosen_online = (
        rng.sample(online_pool, min(online_rows, len(online_pool)))
        if online_pool
        else []
    )
    anchor_needed = anchor_rows + (online_rows - len(chosen_online))
    if len(anchor_pool) < anchor_needed:
        raise ValueError("Insufficient anchor rows to fill replay deficit.")
    chosen_anchor = rng.sample(anchor_pool, anchor_needed)
    replay = tuple(chosen_anchor + chosen_online)
    if len(set(replay).intersection(current)):
        raise AssertionError("Replay/current evidence overlap detected.")
    if len(replay) != anchor_rows + online_rows:
        raise AssertionError("Replay budget mismatch.")
    return replay


@dataclass(frozen=True)
class DetectorObservation:
    row_id: str
    origin_index: int
    maturity_index: int
    epoch_id: int
    epoch_checkpoint_sha256: str
    prediction_checkpoint_sha256: str
    error: int | None
    admitted: bool
    drift_detected: bool
    reason: str


class SharedErrorDriftMonitor:
    """ADWIN monitor over checkpoint-pure delayed neural hard errors."""

    def __init__(self, *, monitor_threshold: float) -> None:
        if not 0.0 <= monitor_threshold <= 1.0:
            raise ValueError("monitor_threshold must be in [0,1]")
        self.monitor_threshold = float(monitor_threshold)
        self.epoch_id = 0
        self.epoch_checkpoint_sha256: str | None = None
        self.disarmed = True
        self.event_count = 0
        self.input_count = 0
        self._adwin: Any = None

    @staticmethod
    def _new_adwin() -> Any:
        from river.drift import ADWIN

        return ADWIN(**ADWIN_CONFIG)

    def start_initial_epoch(self, checkpoint_sha256: str) -> None:
        if self.epoch_checkpoint_sha256 is not None:
            raise RuntimeError("Initial detector epoch already started.")
        self.epoch_id = 1
        self.epoch_checkpoint_sha256 = str(checkpoint_sha256)
        self._adwin = self._new_adwin()
        self.disarmed = False
        self.input_count = 0

    def publish_child_checkpoint(self, checkpoint_sha256: str) -> None:
        if not self.disarmed:
            raise RuntimeError(
                "A child checkpoint may start a new detector epoch only after "
                "the prior epoch has closed."
            )
        self.epoch_id += 1
        self.epoch_checkpoint_sha256 = str(checkpoint_sha256)
        self._adwin = self._new_adwin()
        self.disarmed = False
        self.input_count = 0

    def observe(self, record: MatureLabelRecord) -> DetectorObservation:
        if self.epoch_checkpoint_sha256 is None:
            raise RuntimeError("Detector epoch has not been initialized.")

        if self.disarmed:
            return DetectorObservation(
                row_id=record.row_id,
                origin_index=record.origin_index,
                maturity_index=record.maturity_index,
                epoch_id=self.epoch_id,
                epoch_checkpoint_sha256=self.epoch_checkpoint_sha256,
                prediction_checkpoint_sha256=record.checkpoint_sha256,
                error=None,
                admitted=False,
                drift_detected=False,
                reason="detector_disarmed",
            )

        if record.checkpoint_sha256 != self.epoch_checkpoint_sha256:
            return DetectorObservation(
                row_id=record.row_id,
                origin_index=record.origin_index,
                maturity_index=record.maturity_index,
                epoch_id=self.epoch_id,
                epoch_checkpoint_sha256=self.epoch_checkpoint_sha256,
                prediction_checkpoint_sha256=record.checkpoint_sha256,
                error=None,
                admitted=False,
                drift_detected=False,
                reason="stale_checkpoint_error",
            )

        decision = int(record.neural_probability >= self.monitor_threshold)
        error = int(decision != record.true_label)
        self._adwin.update(error)
        self.input_count += 1
        detected = bool(self._adwin.drift_detected)
        if detected:
            self.event_count += 1
            self.disarmed = True

        return DetectorObservation(
            row_id=record.row_id,
            origin_index=record.origin_index,
            maturity_index=record.maturity_index,
            epoch_id=self.epoch_id,
            epoch_checkpoint_sha256=self.epoch_checkpoint_sha256,
            prediction_checkpoint_sha256=record.checkpoint_sha256,
            error=error,
            admitted=True,
            drift_detected=detected,
            reason="drift_detected" if detected else "admitted",
        )


@dataclass(frozen=True)
class NeuralUpdateConfig:
    learning_rate: float = PRIMARY_LEARNING_RATE
    weight_decay: float = PRIMARY_WEIGHT_DECAY
    batch_size: int = PRIMARY_BATCH_SIZE
    epochs: int = PRIMARY_EPOCHS
    pos_weight: float = PRIMARY_POS_WEIGHT


@dataclass(frozen=True)
class NeuralUpdateResult:
    child_model: nn.Module
    epoch_losses: tuple[float, ...]
    state_sha256: str
    shuffle_seed: int


def state_dict_sha256(model: nn.Module) -> str:
    digest = hashlib.sha256()
    state = model.state_dict()
    for name in sorted(state):
        tensor = state[name].detach().cpu().contiguous()
        array = tensor.numpy()
        digest.update(name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(array.dtype).encode("ascii"))
        digest.update(b"\0")
        digest.update(canonical_json_bytes(list(array.shape)))
        digest.update(b"\0")
        digest.update(array.tobytes(order="C"))
    return digest.hexdigest()


def adapt_neural_checkpoint(
    parent_model: BinaryMLP,
    *,
    X_current: np.ndarray,
    y_current: np.ndarray,
    X_replay: np.ndarray,
    y_replay: np.ndarray,
    seed: int,
    event_id: int,
    config: NeuralUpdateConfig = NeuralUpdateConfig(),
) -> NeuralUpdateResult:
    X_current = np.asarray(X_current, dtype=np.float32)
    X_replay = np.asarray(X_replay, dtype=np.float32)
    y_current = np.asarray(y_current, dtype=np.float32)
    y_replay = np.asarray(y_replay, dtype=np.float32)

    if X_current.ndim != 2 or X_replay.ndim != 2:
        raise ValueError("Adaptation features must be two-dimensional.")
    if X_current.shape[1] != X_replay.shape[1]:
        raise ValueError("Current and replay feature dimensions must match.")
    if len(X_current) != len(y_current) or len(X_replay) != len(y_replay):
        raise ValueError("Feature/label row counts must match.")
    if not np.isfinite(X_current).all() or not np.isfinite(X_replay).all():
        raise ValueError("Adaptation features must be finite.")
    if not np.isin(y_current, [0.0, 1.0]).all() or not np.isin(
        y_replay, [0.0, 1.0]
    ).all():
        raise ValueError("Adaptation labels must be binary.")

    shuffle_seed = ADAPTATION_SHUFFLE_SEED_BASE + 1000 * int(seed) + int(event_id)
    set_reproducible_seed(shuffle_seed)
    torch.set_num_threads(1)

    child = copy.deepcopy(parent_model).cpu()
    child.train()

    X = np.concatenate((X_current, X_replay), axis=0)
    y = np.concatenate((y_current, y_replay), axis=0)

    dataset = TensorDataset(torch.from_numpy(X), torch.from_numpy(y))
    generator = torch.Generator(device="cpu")
    generator.manual_seed(shuffle_seed)
    loader = DataLoader(
        dataset,
        batch_size=int(config.batch_size),
        shuffle=True,
        num_workers=0,
        generator=generator,
    )

    optimizer = torch.optim.Adam(
        child.parameters(),
        lr=float(config.learning_rate),
        weight_decay=float(config.weight_decay),
    )
    loss_fn = torch.nn.BCEWithLogitsLoss(
        pos_weight=torch.tensor(float(config.pos_weight), dtype=torch.float32)
    )

    losses: list[float] = []
    for _ in range(int(config.epochs)):
        total_loss = 0.0
        total_rows = 0
        for batch_X, batch_y in loader:
            optimizer.zero_grad(set_to_none=True)
            logits = child(batch_X)
            loss = loss_fn(logits, batch_y)
            if not torch.isfinite(loss):
                raise RuntimeError("Non-finite neural adaptation loss.")
            loss.backward()
            optimizer.step()
            rows = int(len(batch_X))
            total_loss += float(loss.detach().cpu()) * rows
            total_rows += rows
        losses.append(total_loss / total_rows)

    for parameter in child.parameters():
        if not torch.isfinite(parameter).all():
            raise RuntimeError("Non-finite parameter after neural adaptation.")

    return NeuralUpdateResult(
        child_model=child,
        epoch_losses=tuple(losses),
        state_sha256=state_dict_sha256(child),
        shuffle_seed=shuffle_seed,
    )


def write_checkpoint_new(
    path: Path,
    *,
    model: nn.Module,
    metadata: Mapping[str, Any],
) -> dict[str, str]:
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite checkpoint: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "metadata": dict(metadata),
        "state_dict": model.state_dict(),
        "state_sha256": state_dict_sha256(model),
    }
    torch.save(payload, path)
    return {
        "path": str(path),
        "file_sha256": sha256_file(path),
        "state_sha256": payload["state_sha256"],
    }


def verify_information_timing(events: Sequence[Mapping[str, Any]]) -> None:
    for event in events:
        clock = int(event["logical_clock"])
        origin = event.get("origin_index")
        maturity = event.get("maturity_index")
        if origin is not None and int(origin) > clock:
            raise ValueError("Future observation used before arrival.")
        if event.get("label_required", False):
            if maturity is None:
                raise ValueError("Label-dependent event lacks maturity_index.")
            if int(maturity) > clock:
                raise ValueError("Pending label used before maturity.")


def verify_checkpoint_purity(
    observations: Sequence[DetectorObservation],
) -> None:
    for observation in observations:
        if observation.admitted and (
            observation.prediction_checkpoint_sha256
            != observation.epoch_checkpoint_sha256
        ):
            raise ValueError("Checkpoint-impure detector input admitted.")


def verify_shared_control_plane_identity(
    left: Mapping[str, Any],
    right: Mapping[str, Any],
) -> None:
    required = (
        "label_schedule_sha256",
        "detector_events_sha256",
        "replay_evidence_sha256",
        "checkpoint_chain_sha256",
    )
    for key in required:
        if key not in left or key not in right:
            raise ValueError(f"Missing shared-control-plane identity field: {key}")
        if left[key] != right[key]:
            raise ValueError(f"Shared control-plane divergence at {key}")


def assert_no_boundary_contamination(payload: Any) -> None:
    def visit(value: Any) -> None:
        if isinstance(value, Mapping):
            for key, child in value.items():
                normalized = str(key).strip().lower()
                if normalized in PROHIBITED_ADAPTIVE_KEYS:
                    raise ValueError(
                        f"Prohibited synthetic-boundary field in adaptive payload: {key}"
                    )
                visit(child)
        elif isinstance(value, (list, tuple)):
            for child in value:
                visit(child)

    visit(payload)
