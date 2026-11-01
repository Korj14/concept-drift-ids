"""Real Linux UID/AF_UNIX/fsync access-path tests. No model or treatment.

The 138530-row fixture is a disposable private label vault solely to exercise
privilege and protocol mechanics. It does not stand in for the original data
or constitute Stage-10A outcome evidence.
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
import time

import numpy as np
import pytest

from concept_drift_ids.stage10a_privileged_escrow import (
    _check_prediction, _record_write, provision_ipc, _canonical, _hash, ROWS, SOCKET_NAME,
    LOG_NAME, SCHEMA,
)

WRITER = (54011, 54011)
ESCROW = (54012, 54012)


def test_rejects_wrong_prediction_identity_and_future_clocks():
    r = dict(schema="stage10a-privileged-escrow-v1", attempt_id="custody-test",
             seed=0, run_id="gate-test", row_id="stage10a-logical-000000",
             origin_index=0, maturity_index=5000,
             checkpoint_sha256="a" * 64, neural_probability=0.25)
    assert _check_prediction(r, attempt_id="custody-test", run_id="gate-test",
                             seed=0, clock=0) == r
    for key, bad in (("origin_index", 1), ("maturity_index", 0),
                     ("row_id", "bad"), ("seed", True),
                     ("checkpoint_sha256", "bad"),
                     ("neural_probability", float("nan")),
                     ("neural_probability", 2.0),
                     ("attempt_id", "other")):
        with pytest.raises(ValueError):
            _check_prediction(dict(r, **{key: bad}), attempt_id="custody-test",
                              run_id="gate-test", seed=0, clock=0)
    with pytest.raises(ValueError, match="fields"):
        _check_prediction(dict(r, binary_target=0), attempt_id="custody-test",
                          run_id="gate-test", seed=0, clock=0)


def test_fsync_failure_cannot_return_success(tmp_path, monkeypatch):
    f = tmp_path / "log.jsonl"
    fd = os.open(f, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        def fail(_fd):
            raise OSError("storage fault")
        monkeypatch.setattr(os, "fsync", fail)
        with pytest.raises(OSError, match="storage fault"):
            _record_write(fd, {"event": "prediction", "origin_index": 0}, "0" * 64)
    finally:
        os.close(fd)


@pytest.mark.skipif(sys.platform != "linux" or os.geteuid() != 0 or
                    not shutil.which("setpriv"),
                    reason="requires a controlled root Linux host with setpriv")
def test_actual_distinct_uids_socket_commit_and_delayed_label_boundary():
    import importlib.util
    root = Path(importlib.util.find_spec("concept_drift_ids.stage10a_privileged_escrow").origin).parents[2]
    py = sys.executable
    with tempfile.TemporaryDirectory(prefix="stage10a-escrow-", dir="/tmp") as temporary:
        base = Path(temporary)
        os.chmod(base, 0o711)
        attempt = base / "custody-test"
        attempt.mkdir(mode=0o711)
        label_dir = attempt / "escrow"
        label_dir.mkdir(mode=0o700)
        label_path = label_dir / "labels.npy"
        labels = (np.arange(ROWS) % 2).astype(np.uint8)
        np.save(label_path, labels, allow_pickle=False)
        sha = hashlib.sha256(label_path.read_bytes()).hexdigest()
        os.chown(label_path, *ESCROW)
        os.chmod(label_path, 0o400)
        os.chown(label_dir, *ESCROW)
        os.chmod(label_dir, 0o500)
        provision_ipc(attempt=attempt, writer_uid=WRITER[0], writer_gid=WRITER[1],
                      escrow_uid=ESCROW[0], escrow_gid=ESCROW[1])
        ipc = attempt / "ipc"
        code_server = (
            f"import sys;sys.path.insert(0,{str(root / 'src')!r});"
            "from concept_drift_ids.stage10a_privileged_escrow import serve;"
            f"serve(attempt=__import__('pathlib').Path({str(attempt)!r}),"
            "attempt_id='custody-test',run_id='gate-test',seed=0,"
            f"writer_uid={WRITER[0]},writer_gid={WRITER[1]},"
            f"escrow_uid={ESCROW[0]},escrow_gid={ESCROW[1]},labels_sha256={sha!r})"
        )
        server = subprocess.Popen(
            ["setpriv", "--reuid", str(ESCROW[0]), "--regid", str(ESCROW[1]),
             "--clear-groups", py, "-c", code_server],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        try:
            sock = ipc / SOCKET_NAME
            for _ in range(150):
                if sock.exists():
                    break
                if server.poll() is not None:
                    raise AssertionError(server.communicate()[1].decode())
                time.sleep(.04)
            else:
                raise AssertionError("Escrow server did not bind")
            code_writer = (
                f"import sys;sys.path.insert(0,{str(root / 'src')!r});"
                "from concept_drift_ids.stage10a_privileged_escrow import Stage10AUnixGateway;"
                "from pathlib import Path;"
                f"g=Stage10AUnixGateway(socket_path=Path({str(sock)!r}),"
                f"expected_escrow_uid={ESCROW[0]},attempt_id='custody-test',"
                "run_id='gate-test',seed=0);"
                "exec('for i in range(5001):\\n"
                " r=g.commit_prediction(seed=0,run_id=\\\"gate-test\\\","
                "row_id=f\\\"stage10a-logical-{i:06d}\\\",origin_index=i,"
                "maturity_index=i+5000,checkpoint_sha256=\\\"a\\\"*64,"
                "neural_probability=0.25)\\n"
                " if i<5000: assert r is None\\n"
                " else: assert (r.origin_index,r.binary_target)==(0,0)\\n');"
                "g.close()"
            )
            run = subprocess.run(
                ["setpriv", "--reuid", str(WRITER[0]), "--regid", str(WRITER[1]),
                 "--clear-groups", py, "-c", code_writer],
                capture_output=True, text=True, timeout=55,
            )
            assert run.returncode == 0, run.stderr
            out, err = server.communicate(timeout=20)
            # Incomplete 5001-row attempt must not be mistaken for a complete run.
            assert server.returncode != 0
            events = (ipc / LOG_NAME).read_text().splitlines()
            assert len(events) == 5002
            first = json.loads(events[0])
            last = json.loads(events[-1])
            assert first["origin_index"] == 0 and first["event"] == "prediction"
            assert last["event"] == "label_grant" and last["origin_index"] == 0
            assert last["logical_clock"] == 5000
            prev = _hash(_canonical({"attempt_id": "custody-test", "seed": 0,
                                     "labels_sha256": sha, "schema": SCHEMA}))
            for line in events:
                e = json.loads(line)
                assert e["previous_event_sha256"] == prev
                own = e.pop("event_sha256")
                assert _hash(_canonical(e)) == own
                prev = own
            assert not any(json.loads(x)["event"] == "complete" for x in events)
            # An incomplete attempt remains one-shot; no second launch may
            # reuse or overwrite its committed log even with the same UID.
            previous = hashlib.sha256((ipc / LOG_NAME).read_bytes()).hexdigest()
            retry = subprocess.run(
                ["setpriv", "--reuid", str(ESCROW[0]), "--regid", str(ESCROW[1]),
                 "--clear-groups", py, "-c", code_server],
                capture_output=True, text=True, timeout=10,
            )
            assert retry.returncode != 0
            assert "File exists" in retry.stderr
            assert hashlib.sha256((ipc / LOG_NAME).read_bytes()).hexdigest() == previous
            # Writer cannot read private labels OR the escrow-owned journal.
            code_deny = (
                "import os,sys;"
                f"paths=[{str(label_path)!r},{str(ipc / LOG_NAME)!r}];"
                "exec('for p in paths:\\n"
                " try:open(p,\\\"rb\\\");raise AssertionError(\\\"leak\\\")\\n"
                " except PermissionError:pass\\n')"
            )
            denied = subprocess.run(
                ["setpriv", "--reuid", str(WRITER[0]), "--regid", str(WRITER[1]),
                 "--clear-groups", py, "-c", code_deny],
                capture_output=True, text=True, timeout=10,
            )
            assert denied.returncode == 0, denied.stderr
        finally:
            if server.poll() is None:
                server.kill()
                server.communicate(timeout=10)
