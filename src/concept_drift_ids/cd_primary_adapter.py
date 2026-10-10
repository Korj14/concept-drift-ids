from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import torch

from concept_drift_ids.cd_control_plane import (
    ANCHOR_SEED,
    PRIMARY_ANCHOR_CAPACITY,
    SYSTEM_A_MONITOR_THRESHOLDS,
    canonical_sha256,
    select_uniform_anchor_ids,
)
from concept_drift_ids.cd_implementation_preflight import (
    EXPECTED_PREPROCESSING_STATE_HASH,
    EXPECTED_SYSTEM_A_CHECKPOINT_SHA256,
    EXPECTED_SYSTEM_A_MANIFEST_SHA256,
)
from concept_drift_ids.cd_shared_runner import AnchorRow, StreamRow
from concept_drift_ids.frozen_preprocessing import (
    FrozenPreprocessing,
    load_frozen_preprocessing,
    transform_frame,
)
from concept_drift_ids.neural import BinaryMLP
from concept_drift_ids.scenario_loader import (
    PROJECT_ROOT,
    load_partition,
)
from concept_drift_ids.scenario_manifest import sha256_file
from concept_drift_ids.system_a import SYSTEM_A_CONFIG


EXPECTED_PRE_ROWS = 69_260
EXPECTED_POST_ROWS = 69_270
EXPECTED_STREAM_ROWS = EXPECTED_PRE_ROWS + EXPECTED_POST_ROWS


@dataclass(frozen=True)
class PrimaryInputBundle:
    seed: int
    model: BinaryMLP
    initial_checkpoint_sha256: str
    monitor_threshold: float
    preprocessing_state_hash: str
    feature_names: tuple[str, ...]
    anchor_rows: tuple[AnchorRow, ...]
    stream_rows: tuple[StreamRow, ...]
    audit_identity: dict[str, Any]


def _system_a_manifest(
    *,
    project_root: Path = PROJECT_ROOT,
) -> dict[str, Any]:
    path = project_root / "data" / "manifests" / "system_a_v1.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    stored = manifest.get("manifest_sha256")
    core = dict(manifest)
    core.pop("manifest_sha256", None)
    if canonical_sha256(core) != stored:
        raise ValueError("System-A manifest canonical hash mismatch.")
    if stored != EXPECTED_SYSTEM_A_MANIFEST_SHA256:
        raise ValueError("System-A manifest is not the accepted identity.")
    return manifest


def load_accepted_system_a_model(
    seed: int,
    *,
    preprocessing: FrozenPreprocessing,
    project_root: Path = PROJECT_ROOT,
) -> tuple[BinaryMLP, str]:
    if seed not in EXPECTED_SYSTEM_A_CHECKPOINT_SHA256:
        raise ValueError(f"Unsupported primary seed: {seed}")
    manifest = _system_a_manifest(project_root=project_root)
    records = {
        int(item["seed"]): item for item in manifest["seed_records"]
    }
    record = records[seed]
    expected_file_hash = EXPECTED_SYSTEM_A_CHECKPOINT_SHA256[seed]
    if record["checkpoint_sha256"] != expected_file_hash:
        raise ValueError("Accepted System-A checkpoint identity changed.")

    checkpoint_path = project_root / str(record["checkpoint_file"])
    if sha256_file(checkpoint_path) != expected_file_hash:
        raise ValueError("System-A checkpoint file hash mismatch.")
    checkpoint = torch.load(
        checkpoint_path,
        map_location="cpu",
        weights_only=False,
    )
    if int(checkpoint["seed"]) != seed:
        raise ValueError("System-A checkpoint seed mismatch.")
    if checkpoint["preprocessing_state_hash"] != preprocessing.state_hash:
        raise ValueError("System-A checkpoint preprocessing hash mismatch.")
    if preprocessing.state_hash != EXPECTED_PREPROCESSING_STATE_HASH:
        raise ValueError("Frozen preprocessing identity changed.")
    if checkpoint["config_sha256"] != canonical_sha256(SYSTEM_A_CONFIG):
        raise ValueError("System-A checkpoint config hash mismatch.")
    if float(checkpoint["threshold"]) != float(
        SYSTEM_A_MONITOR_THRESHOLDS[seed]
    ):
        raise ValueError("System-A checkpoint threshold mismatch.")

    model = BinaryMLP(
        input_features=int(SYSTEM_A_CONFIG["input_features"]),
        hidden_layers=tuple(SYSTEM_A_CONFIG["hidden_layers"]),
        dropout=float(SYSTEM_A_CONFIG["dropout"]),
    )
    model.load_state_dict(checkpoint["model_state_dict"])
    model.cpu().eval()
    return model, expected_file_hash


def load_primary_training_anchor(
    *,
    preprocessing: FrozenPreprocessing,
) -> tuple[AnchorRow, ...]:
    training = load_partition("training")
    positions = tuple(
        int(value)
        for value in select_uniform_anchor_ids(
            range(len(training.X)),
            capacity=PRIMARY_ANCHOR_CAPACITY,
            seed=ANCHOR_SEED,
        )
    )
    if len(positions) != PRIMARY_ANCHOR_CAPACITY:
        raise AssertionError("Primary training anchor size changed.")
    if len(set(positions)) != PRIMARY_ANCHOR_CAPACITY:
        raise AssertionError("Primary training anchor positions are not unique.")

    selected_X = training.X.iloc[list(positions)].copy()
    transformed = transform_frame(
        selected_X,
        preprocessing,
        dtype=np.dtype("float32"),
    )
    labels = training.y.iloc[list(positions)].to_numpy(
        dtype=np.int8,
        copy=True,
    )
    rows = tuple(
        AnchorRow(
            row_id=f"anchor:{position:07d}",
            features=transformed[index],
            label=int(labels[index]),
        )
        for index, position in enumerate(positions)
    )
    if {row.label for row in rows} != {0, 1}:
        raise ValueError("Primary training anchor lost binary class diversity.")
    return rows


def _neutral_stream_rows(
    *,
    X_pre: np.ndarray,
    y_pre: np.ndarray,
    X_post: np.ndarray,
    y_post: np.ndarray,
) -> tuple[StreamRow, ...]:
    if len(X_pre) != EXPECTED_PRE_ROWS or len(y_pre) != EXPECTED_PRE_ROWS:
        raise ValueError("Primary pre-reference row count changed.")
    if len(X_post) != EXPECTED_POST_ROWS or len(y_post) != EXPECTED_POST_ROWS:
        raise ValueError("Primary post-reference row count changed.")
    X = np.concatenate((X_pre, X_post), axis=0)
    y = np.concatenate((y_pre, y_post), axis=0)
    if len(X) != EXPECTED_STREAM_ROWS or len(y) != EXPECTED_STREAM_ROWS:
        raise AssertionError("Primary stream length changed.")
    return tuple(
        StreamRow(
            row_id=f"stream:{index:06d}",
            features=X[index],
            label=int(y[index]),
        )
        for index in range(EXPECTED_STREAM_ROWS)
    )


def load_primary_stream(
    *,
    preprocessing: FrozenPreprocessing,
) -> tuple[StreamRow, ...]:
    pre = load_partition("pre_drift")
    X_pre = transform_frame(
        pre.X,
        preprocessing,
        dtype=np.dtype("float32"),
    )
    y_pre = pre.y.to_numpy(dtype=np.int8, copy=True)
    del pre

    post = load_partition("post_drift")
    X_post = transform_frame(
        post.X,
        preprocessing,
        dtype=np.dtype("float32"),
    )
    y_post = post.y.to_numpy(dtype=np.int8, copy=True)
    del post

    return _neutral_stream_rows(
        X_pre=X_pre,
        y_pre=y_pre,
        X_post=X_post,
        y_post=y_post,
    )


def build_primary_input_bundle(seed: int) -> PrimaryInputBundle:
    preprocessing = load_frozen_preprocessing()
    if preprocessing.state_hash != EXPECTED_PREPROCESSING_STATE_HASH:
        raise ValueError("Frozen preprocessing state identity changed.")
    model, checkpoint_sha256 = load_accepted_system_a_model(
        seed,
        preprocessing=preprocessing,
    )
    anchor_rows = load_primary_training_anchor(
        preprocessing=preprocessing,
    )
    stream_rows = load_primary_stream(
        preprocessing=preprocessing,
    )
    if set(row.row_id for row in anchor_rows).intersection(
        row.row_id for row in stream_rows
    ):
        raise AssertionError("Anchor/stream audit namespaces overlap.")

    audit_identity = {
        "seed": int(seed),
        "training_anchor_rows": len(anchor_rows),
        "training_anchor_row_ids_sha256": canonical_sha256(
            [row.row_id for row in anchor_rows]
        ),
        "stream_rows": len(stream_rows),
        "stream_row_ids_sha256": canonical_sha256(
            [row.row_id for row in stream_rows]
        ),
        "stream_layout": {
            "pre_reference_rows": EXPECTED_PRE_ROWS,
            "post_reference_rows": EXPECTED_POST_ROWS,
            "boundary_index": EXPECTED_PRE_ROWS,
            "boundary_visibility_to_adaptive_runner": False,
        },
        "feature_count": len(preprocessing.feature_columns),
        "preprocessing_state_hash": preprocessing.state_hash,
        "initial_checkpoint_sha256": checkpoint_sha256,
        "monitor_threshold": float(SYSTEM_A_MONITOR_THRESHOLDS[seed]),
    }
    audit_identity["identity_sha256"] = canonical_sha256(audit_identity)

    return PrimaryInputBundle(
        seed=seed,
        model=model,
        initial_checkpoint_sha256=checkpoint_sha256,
        monitor_threshold=float(SYSTEM_A_MONITOR_THRESHOLDS[seed]),
        preprocessing_state_hash=preprocessing.state_hash,
        feature_names=preprocessing.feature_columns,
        anchor_rows=anchor_rows,
        stream_rows=stream_rows,
        audit_identity=audit_identity,
    )
