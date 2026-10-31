"""Only synthetic escrow and append checks; no original source/model imports."""
from __future__ import annotations

import inspect
import json

import pytest
from tools.stage10 import stage10a_escrow_append_synthetic as e
from tools.stage10 import stage10a_escrow_append_synthetic_audit as a


@pytest.fixture(autouse=True)
def fast_test_fsync(monkeypatch):
    # Tests observe calls; this deliberately does not prove physical durability.
    monkeypatch.setattr(e.os, "fsync", lambda fd: None)


def test_five_seed_fixture_never_claims_release(tmp_path):
    for seed in e.SEEDS:
        e.write_fixture(tmp_path, seed, e.LATENCY + 1)
    out = a.audit_all(tmp_path)
    assert out["fixture_only_pass"] is True
    assert out["seeds"] == list(e.SEEDS)
    assert out["stage10a_release_ready"] is False
    assert out["production_label_escrow_enforced"] is False


def test_first_mature_label_follows_committed_prediction(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(e.os, "fsync", lambda fd: calls.append(fd))
    seal = e.write_fixture(tmp_path, 0)
    events = [json.loads(s) for s in (tmp_path/"seed-0/events.jsonl").read_text().splitlines()]
    assert len(calls) >= len(events)  # also attempt and final seal fsyncs
    assert events[-2]["kind"] == "prediction_commit"
    assert events[-1]["kind"] == "mature_label_grant"
    assert events[-1]["origin_index"] == 0
    assert seal["event_count"] == e.LATENCY + 2
    assert a.audit_seed(tmp_path, 0)["fixture_verified"] is True


def test_failure_of_prediction_fsync_blocks_label(tmp_path, monkeypatch):
    witness = e.AppendWitness(tmp_path/"seed-0", 0, e.LATENCY + 1)
    escrow = e.FixtureEscrow(0)
    for index in range(e.LATENCY):
        witness.prediction(index)
    real = e.os.fsync
    monkeypatch.setattr(e.os, "fsync", lambda fd: (_ for _ in ()).throw(OSError("fsync failed")))
    with pytest.raises(OSError, match="fsync failed"):
        witness.prediction(e.LATENCY)
    # A failed write is never an authenticated prediction acknowledgement.
    with pytest.raises(ValueError):
        witness.release(e.LATENCY, escrow)
    monkeypatch.setattr(e.os, "fsync", real)
    witness._file.close()


def test_escrow_blocks_early_cross_seed_duplicate_and_without_current_ack(tmp_path):
    w = e.AppendWitness(tmp_path/"seed-0", 0, e.LATENCY+1)
    esc = e.FixtureEscrow(0)
    w.prediction(0)
    with pytest.raises(ValueError, match="matured"):
        w.release(0, esc)
    with pytest.raises(ValueError, match="Cross-seed"):
        e.FixtureEscrow(1)._mature_label(w, e.LATENCY, 0)
    for i in range(1, e.LATENCY+1):
        w.prediction(i)
    w.release(e.LATENCY, esc)
    with pytest.raises(ValueError, match="Duplicate"):
        w.release(e.LATENCY, esc)
    w.seal()


@pytest.mark.parametrize("alter", ["prediction_label_leak", "boundary", "forged_chain",
                                 "early_label", "missing_event", "reordered", "seal_promote"])
def test_independent_auditor_rejects_forged_events_even_if_seal_rehashed(tmp_path, alter):
    e.write_fixture(tmp_path, 0)
    d = tmp_path/"seed-0"
    path = d/"events.jsonl"
    lines = path.read_bytes().splitlines()
    if alter == "seal_promote":
        seal = json.loads((d/"seal.json").read_bytes())
        seal["stage10a_release_ready"] = True
        (d/"seal.json").write_bytes(e.canonical(seal)+b"\n")
    else:
        first = json.loads(lines[0])
        if alter == "prediction_label_leak":
            first["true_label"] = 1
        elif alter == "boundary":
            first["pre_post"] = "post"
        elif alter == "forged_chain":
            first["event_sha256"] = "f"*64
        elif alter == "early_label":
            first["kind"] = "mature_label_grant"
        if alter == "missing_event":
            lines.pop()
        elif alter == "reordered":
            lines[0], lines[1] = lines[1], lines[0]
        else:
            lines[0] = e.canonical(first)
        path.write_bytes(b"\n".join(lines)+b"\n")
        seal=json.loads((d/"seal.json").read_bytes())
        seal["journal_sha256"]=e.digest(path.read_bytes())
        (d/"seal.json").write_bytes(e.canonical(seal)+b"\n")
    with pytest.raises(ValueError):
        a.audit_seed(tmp_path, 0)


def test_no_duplicate_writer_no_truncation_no_fake_seed(tmp_path):
    e.write_fixture(tmp_path, 0)
    with pytest.raises(FileExistsError):
        e.write_fixture(tmp_path, 0)
    with pytest.raises(ValueError,match="Synthetic fixture"):
        e.write_fixture(tmp_path, 1, 138530)
    with pytest.raises(ValueError,match="five frozen"):
        a.audit_all(tmp_path)
    (tmp_path/"seed-0/events.jsonl").write_bytes(b"")
    with pytest.raises(ValueError,match="Truncated"):
        a.audit_seed(tmp_path,0)


def test_no_real_treatment_or_external_attestation_dependencies():
    src=inspect.getsource(e) + inspect.getsource(a)
    for prohibited in ("import torch", "torch.load(", "read_csv(", "urlopen(",
                       "requests.get(", "subprocess.run(", "checkpoint.pt"):
        assert prohibited not in src
