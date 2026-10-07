from __future__ import annotations

import json

import numpy as np
import pytest

import concept_drift_ids.system_b as system_b


def _uncovered(n: int) -> dict[str, np.ndarray]:
    return {
        "p_rule_attack": np.full(n, np.nan),
        "covered": np.zeros(n, dtype=bool),
        "uncovered": np.ones(n, dtype=bool),
        "conflict_abstain": np.zeros(n, dtype=bool),
        "raw_activated": np.zeros(n, dtype=bool),
        "symbolic_class": np.full(n, -1, dtype=np.int8),
        "activation_matrix": np.zeros((n, 0), dtype=bool),
    }


def test_build_partition_loader_can_only_request_training_and_development(monkeypatch) -> None:
    calls: list[str] = []
    def fake_load(name: str):
        calls.append(name)
        return name
    monkeypatch.setattr(system_b, "load_partition", fake_load)
    assert system_b._load_build_partitions() == ("training", "development")
    assert calls == ["training", "development"]
    assert "pre_drift" not in calls and "post_drift" not in calls


def test_global_lambda_tie_prefers_more_neural_weight() -> None:
    y = np.array([0, 0, 1, 1], dtype=np.int8)
    neural = np.array([0.1, 0.2, 0.8, 0.9], dtype=np.float64)
    inputs = {
        seed: (y, neural, _uncovered(len(y)))
        for seed in system_b.SYSTEM_B_CONFIG["seeds"]
    }
    selected, results, rows = system_b._select_global_fusion(inputs)
    assert selected == 1.0
    assert len(results) == 5
    assert len(rows) == 30


def test_system_b_v1_forbids_calibration_and_freezes_cpu_backend() -> None:
    assert system_b.SYSTEM_B_CONFIG["fusion"]["probability_calibration"] == "none"
    assert system_b.SYSTEM_B_CONFIG["backend"] == "cpu"


def test_environment_rejects_non_cpu_before_data_access() -> None:
    with pytest.raises(ValueError, match="CPU"):
        system_b._require_environment("cuda")


def test_json_writer_refuses_overwrite(tmp_path) -> None:
    path = tmp_path / "frozen.json"
    system_b._write_json_new(path, {"a": 1})
    assert json.loads(path.read_text(encoding="utf-8")) == {"a": 1}
    with pytest.raises(FileExistsError, match="overwrite"):
        system_b._write_json_new(path, {"a": 2})


def test_development_split_is_deterministic_and_disjoint() -> None:
    y = np.array([0] * 90 + [1] * 10, dtype=np.int8)
    va, fu = system_b._development_split(y)
    va2, fu2 = system_b._development_split(y)
    np.testing.assert_array_equal(va, va2)
    np.testing.assert_array_equal(fu, fu2)
    assert not set(va).intersection(fu)
    assert len(va) + len(fu) == len(y)
