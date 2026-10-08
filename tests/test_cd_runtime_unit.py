from __future__ import annotations

import pytest

from concept_drift_ids.cd_runtime import (
    PRIMARY_THREAD_ENV,
    require_primary_environment,
)


def test_primary_runtime_environment_requires_every_frozen_value(
    monkeypatch,
) -> None:
    for key, value in PRIMARY_THREAD_ENV.items():
        monkeypatch.setenv(key, value)
    require_primary_environment()

    monkeypatch.setenv("OMP_NUM_THREADS", "2")
    with pytest.raises(RuntimeError, match="OMP_NUM_THREADS"):
        require_primary_environment()


def test_primary_runtime_environment_rejects_missing_hash_seed(
    monkeypatch,
) -> None:
    for key, value in PRIMARY_THREAD_ENV.items():
        monkeypatch.setenv(key, value)
    monkeypatch.delenv("PYTHONHASHSEED")
    with pytest.raises(RuntimeError, match="PYTHONHASHSEED"):
        require_primary_environment()
