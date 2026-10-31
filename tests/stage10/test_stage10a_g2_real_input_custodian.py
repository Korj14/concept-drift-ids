"""Integration tests of the actual source-vault writer and OS read-denial.

No original source bytes, checkpoints, model, predictions or treatments.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import types

import numpy as np
import pytest

from tools.stage10 import stage10a_g2_real_input_custodian as c


@pytest.fixture(scope="module")
def source_receipt():
    return {
        "source_sha256": "893c27dc968bf7a8adef1689f90be55ca4a4dc3088fb63d6ff247ac56856df2a",
        "ordered_row_ids_sha256": "81924f3c39cb49adfaebea11d9aef045ab73804dd61faee49dcfbd2dd5f33f25",
        "retained_rows": c.ROWS,
        "protocol_id": "stage10a-goldeneye-attack-pattern-v1",
        "treatment_execution_authorized": False,
    }


@pytest.fixture(scope="module")
def arrays():
    x = np.zeros((c.ROWS, c.FEATURES), np.float32)
    x[0, 0] = 1.5
    y = np.arange(c.ROWS, dtype=np.uint8) % 2
    return x, y


def test_no_permission_on_unprivileged_host(monkeypatch, tmp_path, arrays, source_receipt):
    monkeypatch.setattr(c.os, "geteuid", lambda: 1001)
    with pytest.raises(ValueError, match="Linux root"):
        c._materialize(output_parent=tmp_path, attempt_id="x",
                       writer=(45011, 45011), escrow=(45012, 45012),
                       x=arrays[0], labels=arrays[1], source_receipt=source_receipt)


@pytest.mark.parametrize("writer,escrow", [
    ((0,0),(45012,45012)), ((45011,45011),(45011,45012)),
    ((45011,45011),(45012,45011)), ((45011,45011),(True,45012)),
])
def test_dedicated_principals_are_required(writer, escrow):
    with pytest.raises(ValueError):
        c._validate_privileges(writer, escrow)


def test_forged_receipt_or_shape_fails_before_writing(tmp_path, arrays, source_receipt):
    if sys.platform != "linux" or os.geteuid()!=0:
        pytest.skip("Root-only Linux host test")
    os.chmod(tmp_path, 0o711)
    x, y = arrays
    bad = dict(source_receipt, treatment_execution_authorized=True)
    with pytest.raises(ValueError, match="authority"):
        c._materialize(output_parent=tmp_path,attempt_id="forged",writer=(45011,45011),
                       escrow=(45012,45012),x=x,labels=y,source_receipt=bad)
    with pytest.raises(ValueError, match="contract"):
        c._materialize(output_parent=tmp_path,attempt_id="bad-shape",writer=(45011,45011),
                       escrow=(45012,45012),x=x[:12],labels=y,source_receipt=source_receipt)
    assert not (tmp_path/"forged").exists()
    assert not (tmp_path/"bad-shape").exists()


def test_actual_linux_kernel_denies_cross_principal_reads(arrays, source_receipt):
    if sys.platform != "linux" or os.geteuid()!=0 or not shutil.which("setpriv"):
        pytest.skip("Host-bound root and setpriv required")
    tmp_path=Path(tempfile.mkdtemp(prefix="stage10a-kernel-",dir="/tmp"))
    os.chmod(tmp_path,0o711)
    receipt=c._materialize(output_parent=tmp_path,attempt_id="source-only-vault",
                           writer=(45011,45011),escrow=(45012,45012),
                           x=arrays[0],labels=arrays[1],source_receipt=source_receipt)
    attempt=tmp_path/"source-only-vault"
    features=attempt/"observations/features.npy"
    labels=attempt/"escrow/labels.npy"
    assert receipt["stage10a_treatment_execution_authorized"] is False
    assert receipt["stage10a_release_ready"] is False
    assert receipt["kernel_access_independently_observed"] is False
    assert receipt["expected_within_stream_mature_labels"] == 133530
    assert receipt["right_censored_labels"] == 5000
    assert hashlib.sha256(features.read_bytes()).hexdigest()==receipt["observations_sha256"]
    assert hashlib.sha256(labels.read_bytes()).hexdigest()==receipt["private_labels_sha256"]
    assert (np.load(features,allow_pickle=False)[0,0] == 1.5)
    assert np.array_equal(np.load(labels,allow_pickle=False),arrays[1])
    for uid, good, bad in ((45011, features, labels), (45012, labels, features)):
        code="import os,sys,errno;os.open(sys.argv[1],os.O_RDONLY);\ntry:os.open(sys.argv[2],os.O_RDONLY)\nexcept OSError as e:\n sys.exit(0 if e.errno in (errno.EACCES,errno.EPERM) else 91)\nsys.exit(92)"
        p=subprocess.run([shutil.which("setpriv"),"--reuid",str(uid),"--regid",str(uid),
                          "--clear-groups",sys.executable,"-c",code,str(good),str(bad)],
                         capture_output=True,text=True,timeout=20,check=False)
        assert p.returncode==0, (uid,p.stdout,p.stderr)
    with pytest.raises(FileExistsError):
        c._materialize(output_parent=tmp_path,attempt_id="source-only-vault",
                       writer=(45011,45011),escrow=(45012,45012),
                       x=arrays[0],labels=arrays[1],source_receipt=source_receipt)
    raw=(attempt/"source_custody_receipt.json").read_bytes()
    assert raw==c._canonical(json.loads(raw))
    shutil.rmtree(tmp_path)


def test_public_entrypoint_requires_protected_original_source(tmp_path, monkeypatch):
    if sys.platform != "linux" or os.geteuid()!=0:
        pytest.skip("Root-only Linux host test")
    fake=types.ModuleType("tools.stage10.stage10a_source_readiness")
    fake.SOURCE_FILE="Wednesday-workingHours.pcap_ISCX.csv"
    monkeypatch.setitem(sys.modules, "tools.stage10.stage10a_source_readiness", fake)
    src=tmp_path/"original"
    dst=tmp_path/"output"
    src.mkdir(mode=0o700)
    dst.mkdir(mode=0o711)
    with pytest.raises(ValueError,match="Original Wednesday source"):
        c.provision_real_stage10a_source(
            source_root=src,output_parent=dst,attempt_id="test",
            writer_uid=45011,writer_gid=45011,escrow_uid=45012,escrow_gid=45012)


def test_no_neural_dependencies_or_runtime_authorization():
    import inspect
    src=inspect.getsource(c)
    for prohibited in ("import torch", "torch.load", "model.predict", "stage10a_release_ready\": True",
                       "stage10a_treatment_execution_authorized\": True"):
        assert prohibited not in src


def test_failed_kernel_probe_does_not_publish_success_receipt(
    tmp_path, monkeypatch, arrays, source_receipt
):
    if sys.platform != "linux" or os.geteuid() != 0:
        pytest.skip("Root-only Linux host test")
    os.chmod(tmp_path, 0o711)
    def reject(**kwargs):
        raise ValueError("simulated kernel denial")
    monkeypatch.setattr(c, "_probe_actual_vault_access", reject)
    with pytest.raises(ValueError, match="simulated kernel denial"):
        c._materialize(
            output_parent=tmp_path, attempt_id="failed-access",
            writer=(45011, 45011), escrow=(45012, 45012),
            x=arrays[0], labels=arrays[1], source_receipt=source_receipt,
        )
    attempt = tmp_path / "failed-access"
    assert (attempt / "attempt.json").is_file()
    assert not (attempt / "source_custody_receipt.json").exists()
    with pytest.raises(FileExistsError):
        c._materialize(
            output_parent=tmp_path, attempt_id="failed-access",
            writer=(45011, 45011), escrow=(45012, 45012),
            x=arrays[0], labels=arrays[1], source_receipt=source_receipt,
        )
