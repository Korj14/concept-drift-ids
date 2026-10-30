"""Stage-10A source-only adapter. No adaptive model, predictions, or outcomes.

The observation API does not expose source row IDs, labels, or the offline
evaluation boundary. The separate label gate releases each ground-truth label
only after the required prediction commit and 5,000 logical-row latency.
This is an interface-level firewall, not proof of a future matched C/D runner.
"""
from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from concept_drift_ids.frozen_preprocessing import (
    FrozenPreprocessing,
    load_frozen_preprocessing,
    transform_frame,
)
from concept_drift_ids.scenario_loader import DEFAULT_MANIFEST_PATH
from tools.stage10 import stage10a_source_readiness as frozen


@dataclass(frozen=True, slots=True)
class UnlabeledObservation:
    logical_index: int
    features: tuple[float, ...]


@dataclass(frozen=True, slots=True)
class MaturedLabel:
    logical_index: int
    binary_target: int


@dataclass(frozen=True, slots=True)
class SourceOnlyReceipt:
    source_sha256: str
    ordered_row_ids_sha256: str
    retained_rows: int
    protocol_id: str
    treatment_execution_authorized: bool = False


class ObservationStream:
    """Features and logical time only; not a treatment executor."""

    def __init__(self, transformed_features: np.ndarray):
        x = np.array(transformed_features, dtype=np.float32, copy=True)
        if x.ndim != 2 or x.shape[1] != 77 or not np.isfinite(x).all():
            raise ValueError("Expected finite (rows, 77) frozen features.")
        x.setflags(write=False)
        self._features = x

    def __len__(self) -> int:
        return len(self._features)

    def observation(self, logical_index: int) -> UnlabeledObservation:
        if not 0 <= logical_index < len(self):
            raise IndexError("Observation index outside the frozen stream.")
        return UnlabeledObservation(
            logical_index=logical_index,
            features=tuple(float(v) for v in self._features[logical_index]),
        )


class DelayedLabelGate:
    """The future executor must call commit only AFTER persisting prediction.

    A commit cannot release the current row's label or any future label.
    This checks sequential acknowledgements, but cannot independently prove
    that a future treatment runner really persisted a prediction.
    """

    def __init__(self, binary_targets: np.ndarray, *, latency_rows: int = 5000):
        y = np.asarray(binary_targets)
        if y.ndim != 1 or len(y) == 0 or not np.isin(y, [0, 1]).all():
            raise ValueError("Binary labels must be a nonempty 0/1 vector.")
        if latency_rows != 5000:
            raise ValueError("Stage-10A label latency must be exactly 5000.")
        self._targets = tuple(int(v) for v in y)
        self._latency = latency_rows
        self._next_commit = 0

    def commit_prediction(self, logical_index: int) -> tuple[MaturedLabel, ...]:
        if logical_index != self._next_commit:
            raise ValueError("Prediction commits must be in exact stream order.")
        if logical_index >= len(self._targets):
            raise IndexError("Prediction commit exceeds stream length.")
        self._next_commit += 1
        eligible = logical_index - self._latency
        if eligible < 0:
            return ()
        return (MaturedLabel(eligible, self._targets[eligible]),)


@dataclass(frozen=True, slots=True)
class SourceOnlyPackage:
    observations: ObservationStream
    delayed_labels: DelayedLabelGate
    receipt: SourceOnlyReceipt


def _select_rows(
    source_frame: pd.DataFrame,
    *,
    pre_start: int,
    pre_end: int,
    post_end: int,
) -> tuple[pd.DataFrame, np.ndarray, np.ndarray]:
    """Private pure selector, parameterized solely for synthetic fixture tests.

    Public production entrypoint below always uses manifest-locked constants.
    """
    if not 0 <= pre_start < pre_end < post_end:
        raise ValueError("Invalid strictly ordered source ranges.")
    frame = source_frame.copy()
    if "__row_in_source__" not in frame:
        raise ValueError("Source IDs absent.")
    ids = frame["__row_in_source__"].to_numpy()
    if not np.issubdtype(ids.dtype, np.integer):
        raise ValueError("Source IDs must be integers.")
    expected = np.arange(pre_start, post_end, dtype=np.int64)
    if not np.array_equal(ids, expected):
        raise ValueError("Source range is missing, reordered, or duplicated.")
    headers = [str(c).strip() for c in frame.columns]
    if len(set(headers)) != len(headers):
        raise ValueError("Whitespace-normalized source columns collide.")
    frame.columns = headers
    if "Label" not in frame:
        raise ValueError("Raw multiclass Label is missing.")
    labels = frame["Label"].astype(str).str.strip().to_numpy()
    pre_len = pre_end - pre_start
    pre_labels, post_labels = labels[:pre_len], labels[pre_len:]
    if set(pre_labels) - {"BENIGN", "DoS GoldenEye", "Heartbleed"}:
        raise ValueError("Unfrozen pre-regime label.")
    if set(post_labels) - {"BENIGN", "DoS GoldenEye"}:
        raise ValueError("Unfrozen post-regime label or post exclusion.")
    retain = np.ones(len(frame), dtype=bool)
    retain[:pre_len] = pre_labels != "Heartbleed"
    retained = frame.loc[retain].reset_index(drop=True)
    retained_ids = ids[retain].astype(np.int64, copy=False)
    target = (labels[retain] != "BENIGN").astype(np.int8)
    return retained, retained_ids, target


def _frozen_transform(
    selected: pd.DataFrame, preprocessing: FrozenPreprocessing
) -> np.ndarray:
    """Use only inherited training-fitted median/scaler; never call fit."""
    features = tuple(preprocessing.feature_columns)
    if len(features) != 77 or len(set(features)) != 77:
        raise ValueError("Frozen feature order must contain 77 unique columns.")
    forbidden = {"Label", "source_file", "source_order", "row_in_source",
                 "__row_in_source__", "scenario_partition", "scenario_row"}
    if set(features) & forbidden:
        raise ValueError("Source metadata or labels cannot enter features.")
    if not set(features).issubset(selected.columns):
        raise ValueError("Frozen feature columns missing.")
    numeric = selected.loc[:, list(features)].apply(
        pd.to_numeric, errors="raise"
    ).replace([np.inf, -np.inf], np.nan)
    result = transform_frame(numeric, preprocessing, dtype=np.dtype("float32"))
    if result.shape != (len(selected), 77) or not np.isfinite(result).all():
        raise ValueError("Frozen transform is not finite/shape-preserving.")
    return result


def load_stage10a_source_only(data_root: Path) -> SourceOnlyPackage:
    """Strict production loader: inspect original source and construct no outcomes."""
    project = Path(__file__).resolve().parents[2]
    master = json.loads(
        (project / "data/manifests/stage10_plus_master_replication_sensitivity_v1_1.json")
        .read_text(encoding="utf-8")
    )
    manifest = json.loads(frozen.MANIFEST_PATH.read_text(encoding="utf-8"))
    scenario = json.loads(DEFAULT_MANIFEST_PATH.read_text(encoding="utf-8"))
    if master["hard_gate"]["stage10_execution_permitted"] is not False:
        raise ValueError("Frozen Stage-10 master execution gate changed.")
    if master["stage10_treatment_outcomes_accessed"] is not False:
        raise ValueError("Unexpected Stage-10 outcomes in master.")
    if manifest["stage10_treatment_execution_authorized"] is not False:
        raise ValueError("Source loader cannot operate on a released treatment manifest.")
    if manifest["stage10_treatment_outcomes_accessed_during_freeze"] is not False:
        raise ValueError("Stage-10A outcome-access freeze violated.")
    if not frozen._embedded_hash_ok(manifest):
        raise ValueError("Frozen Stage-10A manifest hash mismatch.")
    if manifest["protocol_id"] != "stage10a-goldeneye-attack-pattern-v1":
        raise ValueError("Wrong frozen protocol.")
    ranges = manifest["scenario"]
    if (ranges["pre"]["range"]["row_start_inclusive"],
        ranges["pre"]["range"]["row_end_exclusive"],
        ranges["post"]["range"]["row_start_inclusive"],
        ranges["post"]["range"]["row_end_exclusive"],
        ranges["boundary_index"]) != (
            frozen.PRE_START, frozen.PRE_END, frozen.POST_START,
            frozen.POST_END, frozen.BOUNDARY_INDEX
        ):
        raise ValueError("Frozen source/boundary range was altered.")
    if ranges["boundary_role"] != "offline_evaluator_scoring_and_diagnostics_only":
        raise ValueError("Boundary leaked from evaluator policy.")
    if scenario["partitions"]["development"]["row_end_exclusive"] != frozen.PRE_START:
        raise ValueError("Stage-10A overlaps the inherited development partition.")
    if manifest["information_timing"] != {
        "label_latency_rows": 5000, "prediction_before_label_release": True
    }:
        raise ValueError("Frozen label timing changed.")
    if manifest["inherited_identities"]["seeds"] != list(range(5)):
        raise ValueError("Frozen paired seeds changed.")
    raw_path = Path(data_root) / frozen.SOURCE_FILE
    if (not raw_path.is_file()
        or raw_path.stat().st_size != frozen.EXPECTED_SOURCE_SIZE
        or frozen._sha256_file(raw_path) != frozen.EXPECTED_SOURCE_SHA256):
        raise ValueError("Original Wednesday source bytes unavailable or mismatched.")
    selected_source = frozen._extract_source_rows(raw_path)
    selected, ids, targets = _select_rows(
        selected_source,
        pre_start=frozen.PRE_START,
        pre_end=frozen.PRE_END,
        post_end=frozen.POST_END,
    )
    pre_count = frozen.BOUNDARY_INDEX
    pre = selected.iloc[:pre_count]
    post = selected.iloc[pre_count:]
    expected_pre = {"BENIGN": ranges["pre"]["BENIGN"],
                    "DoS GoldenEye": ranges["pre"]["DoS GoldenEye"]}
    expected_post = {"BENIGN": ranges["post"]["BENIGN"],
                     "DoS GoldenEye": ranges["post"]["DoS GoldenEye"]}
    if (len(pre) != ranges["pre"]["rows"] or len(post) != ranges["post"]["rows"]
        or Counter(pre["Label"]) != expected_pre
        or Counter(post["Label"]) != expected_post):
        raise ValueError("Frozen Stage-10A counts or exclusion policy differs.")
    if (frozen._sha256_int64_array(ids[:pre_count])
        != ranges["pre"]["ordered_row_ids_sha256"]
        or frozen._sha256_int64_array(ids[pre_count:])
        != ranges["post"]["ordered_row_ids_sha256"]
        or frozen._sha256_int64_array(ids) != ranges["stream_row_ids_sha256"]
        or frozen._sha256_int64_pairs(np.full(len(ids), 2), ids)
        != ranges["stream_source_order_row_pairs_sha256"]):
        raise ValueError("Frozen source row-order identity mismatch.")
    preprocessing = load_frozen_preprocessing()
    if (preprocessing.state_hash
        != manifest["inherited_identities"]["preprocessing_core_state_sha256"]
        or tuple(scenario["feature_schema"]["feature_columns"])
        != tuple(preprocessing.feature_columns)):
        raise ValueError("Inherited training-only feature/preprocessing state changed.")
    x = _frozen_transform(selected, preprocessing)
    return SourceOnlyPackage(
        observations=ObservationStream(x),
        delayed_labels=DelayedLabelGate(targets),
        receipt=SourceOnlyReceipt(
            source_sha256=frozen.EXPECTED_SOURCE_SHA256,
            ordered_row_ids_sha256=ranges["stream_row_ids_sha256"],
            retained_rows=len(ids),
            protocol_id=manifest["protocol_id"],
        ),
    )
