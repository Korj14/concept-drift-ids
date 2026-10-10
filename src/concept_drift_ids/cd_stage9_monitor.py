from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from concept_drift_ids.cd_control_plane import ADWIN_CONFIG, MatureLabelRecord
from concept_drift_ids.cd_stage9_config import PAGE_HINKLEY_CONFIG


@dataclass(frozen=True)
class Stage9DetectorObservation:
    row_id: str
    origin_index: int
    maturity_index: int
    epoch_id: int
    epoch_checkpoint_sha256: str
    prediction_checkpoint_sha256: str
    signal_name: str
    signal_value: float | None
    admitted: bool
    drift_detected: bool
    reason: str


class Stage9DriftMonitor:
    """Checkpoint-pure delayed monitor with a frozen family/signal contract."""

    def __init__(
        self,
        *,
        family: str,
        signal: str,
        monitor_threshold: float,
        detector_config: Mapping[str, Any] | None = None,
    ) -> None:
        if family not in {"adwin", "page_hinkley"}:
            raise ValueError(f"Unsupported Stage-9 detector family: {family}")
        if signal not in {"hard_error", "brier"}:
            raise ValueError(f"Unsupported Stage-9 detector signal: {signal}")
        if family == "page_hinkley" and signal != "hard_error":
            raise ValueError("Frozen Stage-9 PageHinkley condition uses hard_error only.")
        if family == "adwin" and signal == "brier":
            expected = dict(ADWIN_CONFIG)
            if detector_config is not None and dict(detector_config) != expected:
                raise ValueError("ADWIN-Brier must retain primary ADWIN structural parameters.")
        if family == "page_hinkley":
            expected = dict(PAGE_HINKLEY_CONFIG)
            if detector_config is not None and dict(detector_config) != expected:
                raise ValueError("PageHinkley parameters differ from the frozen Stage-9 values.")
        if not 0.0 <= monitor_threshold <= 1.0:
            raise ValueError("monitor_threshold must be in [0,1]")

        self.family = family
        self.signal = signal
        self.monitor_threshold = float(monitor_threshold)
        self.detector_config = (
            dict(detector_config)
            if detector_config is not None
            else (dict(PAGE_HINKLEY_CONFIG) if family == "page_hinkley" else dict(ADWIN_CONFIG))
        )
        self.epoch_id = 0
        self.epoch_checkpoint_sha256: str | None = None
        self.disarmed = True
        self.event_count = 0
        self.input_count = 0
        self._detector: Any = None

    def _new_detector(self) -> Any:
        if self.family == "adwin":
            from river.drift import ADWIN

            return ADWIN(**ADWIN_CONFIG)
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
                "A child checkpoint may start a new detector epoch only after "
                "the prior epoch has closed."
            )
        self.epoch_id += 1
        self.epoch_checkpoint_sha256 = str(checkpoint_sha256)
        self._detector = self._new_detector()
        self.disarmed = False
        self.input_count = 0

    def _signal_value(self, record: MatureLabelRecord) -> float:
        probability = float(record.neural_probability)
        label = int(record.true_label)
        if self.signal == "hard_error":
            decision = int(probability >= self.monitor_threshold)
            return float(int(decision != label))
        return float((probability - label) ** 2)

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
            "signal_name": self.signal,
        }

        if self.disarmed:
            return Stage9DetectorObservation(
                **common,
                signal_value=None,
                admitted=False,
                drift_detected=False,
                reason="detector_disarmed",
            )

        if record.checkpoint_sha256 != self.epoch_checkpoint_sha256:
            return Stage9DetectorObservation(
                **common,
                signal_value=None,
                admitted=False,
                drift_detected=False,
                reason="stale_checkpoint_signal",
            )

        value = self._signal_value(record)
        self._detector.update(value)
        self.input_count += 1
        detected = bool(self._detector.drift_detected)
        if detected:
            self.event_count += 1
            self.disarmed = True

        return Stage9DetectorObservation(
            **common,
            signal_value=value,
            admitted=True,
            drift_detected=detected,
            reason="drift_detected" if detected else "admitted",
        )
