"""Read only the sealed Stage-10A feature vault for the real neural writer.

No raw CSV, true label, source provenance row index, escrow vault, or evaluator
boundary enters this module. This is an input adapter, NOT an execution command.
The separate trusted launcher and escrow service remain release requirements.
"""
from __future__ import annotations

import hashlib
import io
import os
from pathlib import Path
from typing import Sequence

import numpy as np

from concept_drift_ids.stage10a_control_runner import UnlabeledStreamRow

FROZEN_ROWS = 138_530
FROZEN_FEATURES = 77


class SealedStage10AFeatureRows(Sequence[UnlabeledStreamRow]):
    """Immutable logical stream from a previously sealed custody output."""

    def __init__(self, feature_path: Path, *, expected_sha256: str):
        if (type(expected_sha256) is not str or len(expected_sha256) != 64
            or any(c not in "0123456789abcdef" for c in expected_sha256)):
            raise ValueError("Expected independently pinned SHA-256 required")
        path = Path(feature_path)
        if path.is_symlink():
            raise ValueError("Symlink feature vault prohibited")
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | os.O_CLOEXEC
        fd = os.open(path, flags)
        with os.fdopen(fd, "rb") as stream:
            raw = stream.read()
        if hashlib.sha256(raw).hexdigest() != expected_sha256:
            raise ValueError("Sealed feature vault byte hash mismatch")
        array = np.load(io.BytesIO(raw), allow_pickle=False)
        if (array.shape != (FROZEN_ROWS, FROZEN_FEATURES)
            or array.dtype != np.dtype("float32")
            or not np.isfinite(array).all()):
            raise ValueError("Unexpected frozen Stage-10A feature tensor")
        array.setflags(write=False)
        self._features = array

    def __len__(self) -> int:
        return FROZEN_ROWS

    def __getitem__(self, index: int) -> UnlabeledStreamRow:
        if type(index) is not int:
            raise TypeError("Only individual logical rows may be requested")
        if not 0 <= index < FROZEN_ROWS:
            raise IndexError("Stage-10A logical row outside frozen stream")
        return UnlabeledStreamRow(
            row_id=f"stage10a-logical-{index:06d}",
            features=self._features[index],
        )
