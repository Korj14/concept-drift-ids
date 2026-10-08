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



def test_locked_distribution_versions_match_frozen_environment() -> None:
    from concept_drift_ids.cd_runtime import (
        _distribution_identity,
        verify_locked_distributions,
    )

    versions = verify_locked_distributions()
    assert versions["numpy"] == "2.4.6"
    assert versions["torch"] == "2.14.1"
    assert versions["river"] == "0.26.1"
    assert versions["shap"] == "0.51.0"
    assert len(_distribution_identity(versions)) == 64
