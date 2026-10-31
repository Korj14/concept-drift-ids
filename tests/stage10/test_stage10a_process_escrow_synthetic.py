"""Actual subprocess synthetic-only proof of protocol sequencing; no science."""
from __future__ import annotations

import inspect
import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest
from tools.stage10 import stage10a_process_escrow_synthetic as w
from tools.stage10 import stage10a_process_escrow_audit as a


@pytest.fixture(scope="module")
def all_seed_root(tmp_path_factory):
    root = tmp_path_factory.mktemp("stage10a-five-process-witnesses")
    for seed in w.SEEDS:
        result = w.generate_fixture(root, seed)
        assert result["writer_pid"] != result["escrow_pid"]
        assert result["release_signed"] is False
    return root


@pytest.fixture(scope="module")
def original(all_seed_root):
    assert a.audit_seed(all_seed_root, 0)["cross_process_fixture_verified"] is True
    return all_seed_root / "seed-0"


def _copy(original: Path, tmp_path: Path) -> Path:
    d = tmp_path / "seed-0"
    shutil.copytree(original, d)
    return d


def _rewrite_doc(path: Path, modify):
    value = json.loads(path.read_bytes())
    modify(value)
    path.write_bytes(w.canonical(value)+b"\n")


def _direct_worker(tmp_path: Path, *, request: dict, record: dict | None = None) -> dict:
    d = tmp_path / "seed-0"
    d.mkdir()
    (d / "predictions.jsonl").write_bytes((w.canonical(record)+b"\n") if record else b"")
    c = [sys.executable,"-m","tools.stage10.stage10a_process_escrow_synthetic",
         "--escrow-worker","--directory",str(d),"--seed","0","--rows","5001"]
    with subprocess.Popen(c,cwd=str(w.ROOT),stdin=subprocess.PIPE,stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE) as process:
        output,_ = process.communicate(w.canonical(request)+b"\n",timeout=15)
        assert process.returncode != 0
    return json.loads(output.splitlines()[0])


def test_all_five_real_os_processes_without_real_treatment(all_seed_root):
    report = a.audit_all(all_seed_root)
    assert report["cross_process_synthetic_only_pass"] is True
    assert report["five_seeds"] == list(w.SEEDS)
    assert report["production_label_confidentiality_verified"] is False
    assert report["production_runtime_trust_verified"] is False
    assert report["stage10a_treatment_execution_authorized"] is False


@pytest.mark.parametrize("message",[
    {"op":"request_label","seed":0,"clock":0},
    {"op":"observe","seed":0,"clock":5000},
    {"op":"observe","seed":1,"clock":0},
    {"op":"close"},
    {"op":"observe","seed":0,"clock":0,"future_label":1},
])
def test_separate_worker_rejects_uncommitted_future_or_cross_seed_request(tmp_path,message):
    response=_direct_worker(tmp_path,request=message)
    assert response["ok"] is False


def test_worker_accepts_only_one_confirmed_clock(tmp_path):
    d=tmp_path/"seed-0";d.mkdir()
    rec=w._record(0,0,w.ZERO)
    (d/"predictions.jsonl").write_bytes(w.canonical(rec)+b"\n")
    c=[sys.executable,"-m","tools.stage10.stage10a_process_escrow_synthetic",
       "--escrow-worker","--directory",str(d),"--seed","0","--rows","5001"]
    with subprocess.Popen(c,cwd=str(w.ROOT),stdin=subprocess.PIPE,stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE) as process:
        assert process.stdin and process.stdout
        request=w.canonical({"op":"observe","seed":0,"clock":0})+b"\n"
        process.stdin.write(request); process.stdin.flush()
        first=json.loads(process.stdout.readline())
        assert first["ok"] is True and first["mature_label"] is None
        process.stdin.write(request);process.stdin.flush()
        second=json.loads(process.stdout.readline())
        assert second["ok"] is False
        process.stdin.close()
        assert process.wait(timeout=15)==2


@pytest.mark.parametrize("mutation",[
    "future_label_in_prediction", "boundary_in_prediction", "alter_prediction_token",
    "reforge_prediction_chain", "early_label_grant", "alter_receipt_clock",
    "spoof_same_process", "replace_seal_release", "truncate_receipts",
])
def test_independent_raw_auditor_rejects_forgery(original,tmp_path,mutation):
    d=_copy(original,tmp_path)
    if mutation in {"future_label_in_prediction","boundary_in_prediction",
                    "alter_prediction_token","reforge_prediction_chain"}:
        path=d/"predictions.jsonl"
        lines=path.read_bytes().splitlines()
        doc=json.loads(lines[0])
        if mutation=="future_label_in_prediction": doc["true_label"]=1
        if mutation=="boundary_in_prediction": doc["boundary_index"]=69260
        if mutation=="alter_prediction_token": doc["fake_prediction_sha256"]="0"*64
        if mutation=="reforge_prediction_chain":
            doc["fake_prediction_sha256"]="1"*64
            doc["record_sha256"]=w.sha(w.canonical({k:v for k,v in doc.items() if k!="record_sha256"}))
        lines[0]=w.canonical(doc)
        path.write_bytes(b"\n".join(lines)+b"\n")
        _rewrite_doc(d/"seal.json",lambda z:z.update(prediction_sha256=w.sha(path.read_bytes())))
    elif mutation in {"early_label_grant","alter_receipt_clock","spoof_same_process",
                      "truncate_receipts"}:
        path=d/"escrow_receipts.jsonl"
        lines=path.read_bytes().splitlines()
        doc=json.loads(lines[0])
        if mutation=="early_label_grant": doc["mature_label"]=1; doc["mature_label_origin"]=0
        if mutation=="alter_receipt_clock": doc["clock"]=1
        if mutation=="spoof_same_process": doc["escrow_pid"]=json.loads((d/"attempt.json").read_bytes())["writer_pid"]
        if mutation=="truncate_receipts":lines.pop()
        else:lines[0]=w.canonical(doc)
        path.write_bytes(b"\n".join(lines)+b"\n")
        _rewrite_doc(d/"seal.json",lambda z:z.update(escrow_receipts_sha256=w.sha(path.read_bytes())))
    else:
        _rewrite_doc(d/"seal.json",lambda z:z.update(release_signed=True,stage10a_treatment_execution_authorized=True))
    with pytest.raises(ValueError):
        a.audit_seed(tmp_path,0)


def test_frozen_fixture_lifecycle_and_execution_hard_stops(original,tmp_path):
    _copy(original,tmp_path)
    with pytest.raises(ValueError,match="five-seed"):
        a.audit_all(tmp_path)
    with pytest.raises(ValueError,match="bounded"):
        w.generate_fixture(tmp_path,1,138530)
    with pytest.raises(FileExistsError):
        w.generate_fixture(tmp_path,0)
    with pytest.raises(ValueError,match="Non-synthetic"):
        a.audit_all(tmp_path,rows=138530)


def test_contract_does_not_import_scientific_executors_or_download_external_bytes():
    source=inspect.getsource(w)+inspect.getsource(a)
    for forbidden in ("import torch","torch.load(","pickle.load(","pandas.read_csv(",
                      "requests.get(","urllib.request", "load_accepted_system_a_model"):
        assert forbidden not in source
