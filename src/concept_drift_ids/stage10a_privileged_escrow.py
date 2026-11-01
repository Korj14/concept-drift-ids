"""Stage-10A privileged Unix-domain prediction escrow, NOT a treatment launcher.

The daemon runs as the separately provisioned escrow UID, reads only the private
labels vault, and persists each neural prediction via fsync *before* releasing
one label aged 5,000 stream rows. The writer UID can connect but cannot modify
or read the escrow vault/journal. The accepted Stage-8 source remains untouched.

The provisioning controller must be independent of the experiment writer.
Neither this transport nor any JSON receipt is independent host attestation,
scientific authorization, or a production RELEASE.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import socket
import stat
import struct
import sys
from typing import Any

import numpy as np

ROWS = 138_530
LATENCY = 5_000
MAX_LINE = 1024
HEX64 = re.compile(r"^[0-9a-f]{64}$")
TOKEN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]{0,79}$")
SOCKET_NAME = "prediction-gateway.sock"
LOG_NAME = "durable-predictions.jsonl"
SCHEMA = "stage10a-privileged-escrow-v1"


def _canonical(payload: dict[str, Any]) -> bytes:
    return (json.dumps(payload, sort_keys=True, separators=(",", ":"),
                       allow_nan=False, ensure_ascii=False) + "\n").encode("utf-8")


def _hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _regular(path: Path, *, uid: int, mode: int) -> None:
    if not path.is_absolute() or path.is_symlink():
        raise ValueError("Vault path must be absolute without symlinks")
    st = path.lstat()
    if (not stat.S_ISREG(st.st_mode) or st.st_uid != uid or
        stat.S_IMODE(st.st_mode) != mode or st.st_nlink != 1):
        raise ValueError("Vault file ownership/mode/link count invalid")


def _folder(path: Path, *, uid: int, gid: int | None, mode: int) -> None:
    if not path.is_absolute() or path.is_symlink() or path.resolve() != path:
        raise ValueError("Vault directory must be absolute and symlink-free")
    st = path.lstat()
    if (not stat.S_ISDIR(st.st_mode) or st.st_uid != uid or
        (gid is not None and st.st_gid != gid) or
        stat.S_IMODE(st.st_mode) != mode):
        raise ValueError("Vault directory ownership or mode invalid")


def _roles(writer_uid: int, writer_gid: int,
           escrow_uid: int, escrow_gid: int) -> None:
    if (sys.platform != "linux" or
        any(type(x) is not int or not 1000 <= x < 60000 for x in
            (writer_uid, writer_gid, escrow_uid, escrow_gid)) or
        writer_uid == escrow_uid or writer_gid == escrow_gid):
        raise ValueError("Distinct nonroot Linux principal UIDs/GIDs required")


def _layout(attempt: Path, *, escrow_uid: int, escrow_gid: int,
            writer_gid: int) -> tuple[Path, Path, Path]:
    _folder(attempt, uid=0, gid=None, mode=0o711)
    label_dir = attempt / "escrow"
    label_file = label_dir / "labels.npy"
    _folder(label_dir, uid=escrow_uid, gid=escrow_gid, mode=0o500)
    _regular(label_file, uid=escrow_uid, mode=0o400)
    ipc = attempt / "ipc"
    return label_file, ipc, attempt


def provision_ipc(*, attempt: Path, writer_uid: int, writer_gid: int,
                  escrow_uid: int, escrow_gid: int) -> None:
    """A root controller creates a writer-traversable, escrow-owned IPC root.

    Writer group has traverse only, never directory write. The SGID flag causes
    escrow-created socket nodes to inherit the writer GID, without putting
    the escrow daemon in the writer group.
    """
    _roles(writer_uid, writer_gid, escrow_uid, escrow_gid)
    if os.geteuid() != 0 or os.getegid() != 0:
        raise PermissionError("Independent Linux root controller required")
    _, ipc, attempt = _layout(Path(attempt), escrow_uid=escrow_uid,
                              escrow_gid=escrow_gid, writer_gid=writer_gid)
    ipc.mkdir(mode=0o700, exist_ok=False)
    os.chown(ipc, escrow_uid, writer_gid)
    os.chmod(ipc, 0o2710)
    fd = os.open(attempt, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _load_labels(label_file: Path, pinned_hash: str) -> np.ndarray:
    if type(pinned_hash) is not str or not HEX64.fullmatch(pinned_hash):
        raise ValueError("Escrow label hash must be externally pinned")
    fd = os.open(label_file, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
    with os.fdopen(fd, "rb") as f:
        raw = f.read()
    if _hash(raw) != pinned_hash:
        raise ValueError("Private labels differ from pinned custody receipt")
    import io
    array = np.load(io.BytesIO(raw), allow_pickle=False)
    if (array.shape != (ROWS,) or array.dtype != np.dtype("uint8") or
        not np.isin(array, [0, 1]).all()):
        raise ValueError("Private labels violate frozen Stage-10A contract")
    array.setflags(write=False)
    return array


def _peer_uid(conn: socket.socket) -> int:
    raw = conn.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize("3i"))
    _pid, uid, _gid = struct.unpack("3i", raw)
    return uid


def _readline(reader: Any) -> bytes:
    data = reader.readline(MAX_LINE + 1)
    if not data:
        raise ConnectionError("Writer disconnected or aborted before final seal")
    if len(data) > MAX_LINE or not data.endswith(b"\n"):
        raise ValueError("Overlength or unterminated prediction frame")
    return data


def _record_write(fd: int, event: dict[str, Any], prev: str) -> str:
    payload = dict(event, previous_event_sha256=prev)
    sha = _hash(_canonical(payload))
    line = _canonical(dict(payload, event_sha256=sha))
    offset = 0
    while offset < len(line):
        written = os.write(fd, line[offset:])
        if written <= 0:
            raise OSError("Failed to append escrow evidence")
        offset += written
    os.fsync(fd)  # Label grant can only follow this successful return.
    return sha


def _check_prediction(request: Any, *, attempt_id: str, run_id: str,
                      seed: int, clock: int) -> dict[str, Any]:
    fields = {"schema", "attempt_id", "seed", "run_id", "row_id",
              "origin_index", "maturity_index", "checkpoint_sha256",
              "neural_probability"}
    if type(request) is not dict or set(request) != fields:
        raise ValueError("Unexpected or missing prediction fields")
    if (request["schema"] != SCHEMA or request["attempt_id"] != attempt_id or
        request["run_id"] != run_id or type(request["seed"]) is not int or
        request["seed"] != seed or type(request["origin_index"]) is not int or
        request["origin_index"] != clock or type(request["maturity_index"]) is not int or
        request["maturity_index"] != clock + LATENCY or
        type(request["row_id"]) is not str or
        request["row_id"] != f"stage10a-logical-{clock:06d}" or
        type(request["checkpoint_sha256"]) is not str or
        not HEX64.fullmatch(request["checkpoint_sha256"]) or
        type(request["neural_probability"]) is not float or
        not math.isfinite(request["neural_probability"]) or
        not 0.0 <= request["neural_probability"] <= 1.0):
        raise ValueError("Prediction identity, clock or probability mismatch")
    return request


def serve(*, attempt: Path, attempt_id: str, run_id: str, seed: int,
          writer_uid: int, writer_gid: int, escrow_uid: int, escrow_gid: int,
          labels_sha256: str) -> None:
    """Run once as escrow UID; no recovery/restart, no treatment launch.

    All 138530 commits are required for completed seal; an early disconnect
    yields an incomplete, write-once journal that cannot be resumed.
    """
    _roles(writer_uid, writer_gid, escrow_uid, escrow_gid)
    if (os.geteuid() != escrow_uid or os.getegid() != escrow_gid or
        type(seed) is not int or seed not in range(5) or
        type(attempt_id) is not str or not TOKEN.fullmatch(attempt_id) or
        type(run_id) is not str or not TOKEN.fullmatch(run_id)):
        raise PermissionError("Wrong escrow process authority/identity")
    attempt = Path(attempt)
    labels_path, ipc, _ = _layout(attempt, escrow_uid=escrow_uid,
                                  escrow_gid=escrow_gid, writer_gid=writer_gid)
    _folder(ipc, uid=escrow_uid, gid=writer_gid, mode=0o2710)
    labels = _load_labels(labels_path, labels_sha256)
    journal = ipc / LOG_NAME
    fd = os.open(journal, os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                 os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
    sock_path = ipc / SOCKET_NAME
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        server.bind(str(sock_path))
        os.chmod(sock_path, 0o660)
        st = sock_path.lstat()
        if (st.st_uid != escrow_uid or st.st_gid != writer_gid or
            stat.S_IMODE(st.st_mode) != 0o660):
            raise PermissionError("Escrow socket custody policy invalid")
        server.listen(1)
        server.settimeout(120)
        dirfd = os.open(ipc, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            os.fsync(dirfd)
        finally:
            os.close(dirfd)
        conn, _ = server.accept()
        with conn:
            conn.settimeout(20)
            if _peer_uid(conn) != writer_uid:
                raise PermissionError("Only independently specified writer UID may commit")
            prev = _hash(_canonical({"attempt_id": attempt_id, "seed": seed,
                                     "labels_sha256": labels_sha256, "schema": SCHEMA}))
            reader = conn.makefile("rb")
            for clock in range(ROWS):
                raw = _readline(reader)
                request = json.loads(raw)
                if raw != _canonical(request):
                    raise ValueError("Prediction frame must be canonical JSON")
                record = _check_prediction(request, attempt_id=attempt_id,
                                           run_id=run_id, seed=seed, clock=clock)
                prev = _record_write(fd, dict(record, event="prediction"), prev)
                mature = clock - LATENCY
                granted = None
                if mature >= 0:
                    granted = {"origin_index": mature,
                               "binary_target": int(labels[mature])}
                    prev = _record_write(fd, {
                        "event": "label_grant", "logical_clock": clock,
                        "origin_index": mature,
                        "private_labels_sha256": labels_sha256,
                    }, prev)
                answer = {"schema": SCHEMA, "status": "committed",
                          "origin_index": clock, "commit_sha256": prev,
                          "grant": granted}
                conn.sendall(_canonical(answer))
            prev = _record_write(fd, {"event": "complete", "rows": ROWS,
                                      "matured": ROWS - LATENCY,
                                      "right_censored": LATENCY}, prev)
            os.fchmod(fd, 0o400)
            os.fsync(fd)
            dfd = os.open(ipc, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            try:
                os.fsync(dfd)
            finally:
                os.close(dfd)
    finally:
        server.close()
        os.close(fd)
        # Do not unlink socket or journal: preserve failed attempt evidence.


class Stage10AUnixGateway:
    """Writer-side client that implements Stage10APredictionGateway."""

    def __init__(self, *, socket_path: Path, expected_escrow_uid: int,
                 attempt_id: str, run_id: str, seed: int):
        if (type(expected_escrow_uid) is not int or expected_escrow_uid < 1000 or
            type(seed) is not int or seed not in range(5) or
            type(attempt_id) is not str or not TOKEN.fullmatch(attempt_id) or
            type(run_id) is not str or not TOKEN.fullmatch(run_id)):
            raise ValueError("Externally pinned writer launch identity required")
        self._socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._socket.settimeout(30)
        try:
            self._socket.connect(str(socket_path))
            if _peer_uid(self._socket) != expected_escrow_uid:
                raise PermissionError("Untrusted escrow socket peer UID")
        except BaseException:
            self._socket.close()
            raise
        self._reader = self._socket.makefile("rb")
        self._attempt = attempt_id
        self._run = run_id
        self._seed = seed
        self._clock = 0

    def close(self) -> None:
        self._reader.close()
        self._socket.close()

    def __enter__(self) -> "Stage10AUnixGateway":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def commit_prediction(self, *, seed: int, run_id: str, row_id: str,
                          origin_index: int, maturity_index: int,
                          checkpoint_sha256: str,
                          neural_probability: float) -> Any:
        if (seed != self._seed or run_id != self._run or
            origin_index != self._clock or origin_index >= ROWS):
            raise ValueError("Out-of-order or cross-seed writer prediction")
        request = {"schema": SCHEMA, "attempt_id": self._attempt,
                   "seed": seed, "run_id": run_id, "row_id": row_id,
                   "origin_index": origin_index, "maturity_index": maturity_index,
                   "checkpoint_sha256": checkpoint_sha256,
                   "neural_probability": neural_probability}
        self._socket.sendall(_canonical(request))
        answer_raw = _readline(self._reader)
        answer = json.loads(answer_raw)
        if (answer_raw != _canonical(answer) or type(answer) is not dict or
            set(answer) != {"schema", "status", "origin_index", "commit_sha256", "grant"} or
            answer["schema"] != SCHEMA or answer["status"] != "committed" or
            type(answer["origin_index"]) is not int or answer["origin_index"] != origin_index or
            type(answer["commit_sha256"]) is not str or not HEX64.fullmatch(answer["commit_sha256"])):
            raise RuntimeError("Untrusted durable prediction acknowledgment")
        expected_mature = origin_index - LATENCY
        grant = answer["grant"]
        if expected_mature < 0:
            if grant is not None:
                raise RuntimeError("Premature escrow label")
            result = None
        else:
            if (type(grant) is not dict or set(grant) != {"origin_index", "binary_target"} or
                type(grant["origin_index"]) is not int or grant["origin_index"] != expected_mature or
                type(grant["binary_target"]) is not int or grant["binary_target"] not in (0, 1)):
                raise RuntimeError("Missing, delayed, or substituted escrow label")
            from concept_drift_ids.stage10a_control_runner import Stage10ALabelGrant
            result = Stage10ALabelGrant(grant["origin_index"], grant["binary_target"])
        self._clock += 1
        return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Stage-10A privileged label escrow; NO treatments")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("provision-ipc", "serve"):
        p = commands.add_parser(name)
        p.add_argument("--attempt", type=Path, required=True)
        p.add_argument("--writer-uid", type=int, required=True)
        p.add_argument("--writer-gid", type=int, required=True)
        p.add_argument("--escrow-uid", type=int, required=True)
        p.add_argument("--escrow-gid", type=int, required=True)
        if name == "serve":
            p.add_argument("--attempt-id", required=True)
            p.add_argument("--run-id", required=True)
            p.add_argument("--seed", type=int, required=True)
            p.add_argument("--labels-sha256", required=True)
    a = vars(parser.parse_args())
    cmd = a.pop("command")
    if cmd == "provision-ipc":
        provision_ipc(**a)
    else:
        serve(**a)


if __name__ == "__main__":
    main()
