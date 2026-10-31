"""Fail-closed synthetic-only shared writer witness tests (no models/datasets)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.stage10.stage10a_shared_writer_synthetic import (
    ARMS, FIXTURE, LATENCY, MAX_COUNT, SEEDS,
    bind_readonly_arm, verify_bound_all_seeds, verify_bound_seed,
    verify_shared_fixture, write_shared_fixture,
)


@pytest.fixture(autouse=True)
def mocked_fsync(monkeypatch):
    # Verify fsync invocation without host-disk latency for thousands of fixture records.
    calls = []
    monkeypatch.setattr("tools.stage10.stage10a_shared_writer_synthetic.os.fsync",
                        lambda descriptor: calls.append(descriptor))
    return calls


def test_writer_fsyncs_before_mature_label_event(tmp_path, mocked_fsync):
    _one(tmp_path)
    assert len(mocked_fsync) >= LATENCY + 3


def _one(tmp_path: Path, seed: int = 0) -> Path:
    write_shared_fixture(tmp_path, seed=seed)
    for arm in ARMS:
        bind_readonly_arm(tmp_path, seed=seed, arm=arm)
    return tmp_path / f"seed-{seed}"


def _patch_json(path: Path, change):
    obj = json.loads(path.read_bytes())
    change(obj)
    path.write_text(json.dumps(obj, sort_keys=True, separators=(",", ":")) + "\n")


def test_shared_writer_only_one_seed_and_three_readonly_bindings(tmp_path):
    _one(tmp_path)
    sha = verify_bound_seed(tmp_path, seed=0)
    assert len(sha) == 64
    with pytest.raises(FileExistsError):
        write_shared_fixture(tmp_path, seed=0)
    with pytest.raises(FileExistsError):
        bind_readonly_arm(tmp_path, seed=0, arm=ARMS[0])


def test_prediction_committed_before_delayed_synthetic_label(tmp_path):
    directory = _one(tmp_path)
    records = [json.loads(line) for line in (directory / "shared.jsonl").read_text().splitlines()]
    assert len(records) == LATENCY + 2
    assert [r["event_type"] for r in records[-3:]] == [
        "prediction", "prediction", "label_release",
    ]
    assert records[-1]["logical_clock"] == LATENCY
    assert records[-1]["origin_index"] == 0
    assert records[-1]["maturity_index"] == LATENCY
    assert all("synthetic_binary_label" not in r and "boundary_index" not in r
               for r in records if r["event_type"] == "prediction")


def test_exact_five_seeds_one_writer_each(tmp_path):
    for seed in SEEDS:
        _one(tmp_path, seed)
    evidence = verify_bound_all_seeds(tmp_path)
    assert evidence["seeds"] == list(SEEDS)
    assert len(set(evidence["seed_shared_journal_sha256"].values())) == 5
    assert evidence["real_neural_control_trajectory_verified"] is False
    assert evidence["model_loaded_or_predicted"] is False
    assert evidence["stage10a_release_ready"] is False


def test_missing_seed_or_arm_fails_closed(tmp_path):
    _one(tmp_path)
    with pytest.raises(ValueError, match="five frozen seed writers"):
        verify_bound_all_seeds(tmp_path)
    p = tmp_path / "seed-0" / f"arm-{ARMS[-1]}.json"
    p.unlink()
    with pytest.raises(ValueError, match="Missing or unauthorized"):
        verify_bound_seed(tmp_path, seed=0)


def test_cross_seed_arm_reference_rejected(tmp_path):
    _one(tmp_path, 0)
    _one(tmp_path, 1)
    p = tmp_path / "seed-0" / f"arm-{ARMS[1]}.json"
    _patch_json(p, lambda x: x.update(seed=1))
    with pytest.raises(ValueError, match="Arm diverged"):
        verify_bound_seed(tmp_path, seed=0)


@pytest.mark.parametrize("mutation", [
    "early_label", "prediction_label_leak", "boundary_leak", "tamper_neural_token",
    "truncate", "extra_event", "swap_event", "noncanonical_json",
])
def test_independent_raw_shared_journal_recomputation_rejects_tampering(tmp_path, mutation):
    directory = _one(tmp_path)
    p = directory / "shared.jsonl"
    lines = p.read_bytes().splitlines(keepends=True)
    if mutation == "early_label":
        lines[0] = b'{"event_type":"label_release"}\n'
    elif mutation in ("prediction_label_leak", "boundary_leak", "tamper_neural_token"):
        rec = json.loads(lines[0])
        if mutation == "prediction_label_leak":
            rec["synthetic_binary_label"] = 1
        elif mutation == "boundary_leak":
            rec["boundary_index"] = 69260
        else:
            rec["synthetic_neural_token_sha256"] = "0" * 64
        lines[0] = (json.dumps(rec, sort_keys=True, separators=(",", ":")) + "\n").encode()
    elif mutation == "truncate":
        lines = lines[:-1]
    elif mutation == "extra_event":
        lines.append(lines[-1])
    elif mutation == "swap_event":
        lines[0], lines[1] = lines[1], lines[0]
    elif mutation == "noncanonical_json":
        lines[0] = b"  " + lines[0]
    p.write_bytes(b"".join(lines))
    with pytest.raises(ValueError, match="Synthetic writer|incomplete|omitted"):
        verify_bound_seed(tmp_path, seed=0)


def test_shared_manifest_hash_substitution_rejected(tmp_path):
    directory = _one(tmp_path)
    _patch_json(directory / "sealed.json", lambda x: x.update(journal_sha256="0" * 64))
    with pytest.raises(ValueError, match="seal"):
        verify_bound_seed(tmp_path, seed=0)


def test_arm_cannot_claim_second_neural_writer(tmp_path):
    directory = _one(tmp_path)
    _patch_json(directory / f"arm-{ARMS[0]}.json", lambda x: x.update(neural_writer_invocations=1))
    with pytest.raises(ValueError, match="Arm diverged"):
        verify_bound_seed(tmp_path, seed=0)


def test_arm_cannot_swap_shared_digest_or_symbolic_identity(tmp_path):
    directory = _one(tmp_path)
    p = directory / f"arm-{ARMS[2]}.json"
    _patch_json(p, lambda x: x.update(shared_journal_sha256="a" * 64))
    with pytest.raises(ValueError, match="Arm diverged"):
        verify_bound_seed(tmp_path, seed=0)


def test_unknown_arm_and_invalid_counts_rejected_before_writes(tmp_path):
    with pytest.raises(ValueError, match="bounded synthetic"):
        write_shared_fixture(tmp_path, seed=0, count=LATENCY)
    with pytest.raises(ValueError, match="bounded synthetic"):
        write_shared_fixture(tmp_path, seed=0, count=138530)
    with pytest.raises(ValueError, match="five frozen"):
        write_shared_fixture(tmp_path, seed=5)
    assert not list(tmp_path.iterdir())
    write_shared_fixture(tmp_path, seed=0)
    with pytest.raises(ValueError, match="Unknown frozen arm"):
        bind_readonly_arm(tmp_path, seed=0, arm="extra_treatment")


def test_reject_unexpected_neural_or_checkpoint_artifact(tmp_path):
    directory = _one(tmp_path)
    (directory / "checkpoint.pt").write_bytes(b"synthetic-not-a-checkpoint")
    with pytest.raises(ValueError, match="Missing or unauthorized"):
        verify_bound_seed(tmp_path, seed=0)


def test_writer_has_no_real_model_or_dataset_interfaces():
    from tools.stage10 import stage10a_shared_writer_synthetic as module
    import inspect
    src = inspect.getsource(module)
    for forbidden in ("torch.load(", "pickle.load(", "model.predict(",
                      "requests.get(", "urlopen(", "pandas.read_csv("):
        assert forbidden not in src
    assert FIXTURE.endswith("synthetic-only-v1")
