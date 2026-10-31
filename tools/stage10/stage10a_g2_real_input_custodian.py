"""Provision actual Stage-10A pre-execution input custody, with NO neural treatment.

Linux root controller only. Reads the frozen original data through the accepted
source-only adapter, then writes the 77-feature input and private labels under
independently controlled OS UIDs. It cannot authorize Stage-10A treatment.

This is a production *input provisioning* component, not an adaptive runner,
execution RELEASE, durable prediction witness or independent host attestation.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import stat
import sys
from typing import Any

import numpy as np

SCHEMA = "stage10a-g2-real-source-custody-v1"
ROWS = 138_530
FEATURES = 77
LATENCY = 5_000
ATTEMPT = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]{0,79}$")


def _canonical(payload: Any) -> bytes:
    return (json.dumps(payload, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def _controller_dir(path: Path, mode: int) -> None:
    if (not path.is_absolute() or path.is_symlink() or not path.is_dir()
        or path.resolve(strict=True) != path):
        raise ValueError("Controller root must be an existing absolute real directory")
    st = path.stat()
    if st.st_uid != 0 or stat.S_IMODE(st.st_mode) != mode:
        raise ValueError(f"Controller root must be root-owned and exactly mode {mode:04o}")


def _validate_privileges(writer: tuple[int, int], escrow: tuple[int, int]) -> None:
    if (sys.platform != "linux" or os.geteuid() != 0 or
        any(type(v) is not int or not 1000 <= v < 60000
            for v in (*writer, *escrow)) or
        writer[0] == escrow[0] or writer[1] == escrow[1]):
        raise ValueError("Requires Linux root and distinct dedicated nonroot UID/GID roles")


def _write_npy_exclusive(path: Path, payload: np.ndarray) -> str:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC
    descriptor = os.open(path, flags, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as output:
            np.save(output, payload, allow_pickle=False)
            output.flush()
            os.fsync(output.fileno())
    except BaseException:
        # Failed attempts remain in a write-once quarantine, never overwritten.
        raise
    return _sha256(path)


def _write_json_exclusive(path: Path, value: dict[str, Any]) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC
    fd = os.open(path, flags, 0o600)
    with os.fdopen(fd, "wb") as output:
        output.write(_canonical(value))
        output.flush()
        os.fsync(output.fileno())
    os.chmod(path, 0o400)



def _probe_actual_vault_access(
    *, observations: Path, labels: Path,
    writer: tuple[int, int], escrow: tuple[int, int],
) -> None:
    """Kernel open(2) proof at custody time; controller still is not external attestor."""
    binary = shutil.which("setpriv")
    if not binary or not Path(binary).is_absolute():
        raise ValueError("Missing absolute trusted setpriv executable")
    st = Path(binary).stat()
    if st.st_uid != 0 or stat.S_IMODE(st.st_mode) & 0o022:
        raise ValueError("setpriv executable must be root-owned, non-writable by roles")
    probe = (
        "import errno,os,sys\n"
        "fd=os.open(sys.argv[1],os.O_RDONLY|os.O_NOFOLLOW);os.close(fd)\n"
        "try:fd=os.open(sys.argv[2],os.O_RDONLY|os.O_NOFOLLOW)\n"
        "except OSError as e:sys.exit(0 if e.errno in (errno.EACCES,errno.EPERM) else 80)\n"
        "else:os.close(fd);sys.exit(81)\n"
    )
    for role, allowed, denied in ((writer, observations, labels),
                                  (escrow, labels, observations)):
        run = subprocess.run(
            [binary, "--reuid", str(role[0]), "--regid", str(role[1]),
             "--clear-groups", sys.executable, "-I", "-c", probe,
             str(allowed), str(denied)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=20, check=False,
        )
        if run.returncode != 0:
            raise ValueError("Kernel source-vault access denied/allowed incorrectly")


def _materialize(
    *,
    output_parent: Path,
    attempt_id: str,
    writer: tuple[int, int],
    escrow: tuple[int, int],
    x: np.ndarray,
    labels: np.ndarray,
    source_receipt: dict[str, Any],
) -> dict[str, Any]:
    """Write real shape-compatible custody bytes; function takes controller-held arrays.

    The only public caller loads frozen original source, not synthetic fixtures.
    No model import, prediction or outcome is performed.
    """
    _validate_privileges(writer, escrow)
    _controller_dir(output_parent, 0o711)
    if type(attempt_id) is not str or not ATTEMPT.fullmatch(attempt_id):
        raise ValueError("Attempt ID must be a bounded path-safe token")
    xa = np.asarray(x)
    ya = np.asarray(labels)
    if (xa.dtype != np.float32 or xa.shape != (ROWS, FEATURES)
        or not np.isfinite(xa).all() or ya.shape != (ROWS,)
        or ya.dtype not in (np.dtype("uint8"), np.dtype("int8"))
        or not np.isin(ya, (0, 1)).all()):
        raise ValueError("Frozen 138530-row, 77-feature/binary target contract changed")
    if (type(source_receipt) is not dict
        or source_receipt.get("source_sha256") !=
           "893c27dc968bf7a8adef1689f90be55ca4a4dc3088fb63d6ff247ac56856df2a"
        or source_receipt.get("ordered_row_ids_sha256") !=
           "81924f3c39cb49adfaebea11d9aef045ab73804dd61faee49dcfbd2dd5f33f25"
        or source_receipt.get("retained_rows") != ROWS
        or source_receipt.get("protocol_id") != "stage10a-goldeneye-attack-pattern-v1"
        or source_receipt.get("treatment_execution_authorized") is not False):
        raise ValueError("Missing frozen original-source authority binding")

    attempt = output_parent / attempt_id
    attempt.mkdir(mode=0o700, exist_ok=False)
    state = {"schema": SCHEMA, "attempt": attempt_id,
             "status": "STARTED_SOURCE_ONLY_NO_TREATMENT",
             "stage10a_treatment_execution_authorized": False}
    _write_json_exclusive(attempt / "attempt.json", state)
    observations = attempt / "observations"
    label_vault = attempt / "escrow"
    observations.mkdir(mode=0o700)
    label_vault.mkdir(mode=0o700)
    obs_file = observations / "features.npy"
    label_file = label_vault / "labels.npy"
    obs_hash = _write_npy_exclusive(obs_file, xa)
    label_hash = _write_npy_exclusive(label_file, ya.astype(np.uint8, copy=False))
    # Owner-only read/execute; no worker has access to the opposing vault.
    for folder, file, role in ((observations, obs_file, writer),
                               (label_vault, label_file, escrow)):
        os.chown(file, role[0], role[1])
        os.chmod(file, 0o400)
        os.chown(folder, role[0], role[1])
        os.chmod(folder, 0o500)
    receipt = {
        "schema": SCHEMA, "attempt": attempt_id,
        "observations_sha256": obs_hash,
        "private_labels_sha256": label_hash,
        "source_receipt": source_receipt,
        "shape": [ROWS, FEATURES], "label_latency_rows": LATENCY,
        "expected_within_stream_mature_labels": ROWS - LATENCY,
        "right_censored_labels": LATENCY,
        "principal_uids": {"writer": writer[0], "escrow": escrow[0]},
        "same_host_kernel_access_probe_passed": True,
        "kernel_access_independently_observed": False,
        "prediction_commit_witnessed": False,
        "original_checkpoint_loaded": False,
        "production_schema_frozen": False,
        "stage10a_treatment_execution_authorized": False,
        "stage10a_release_ready": False,
    }
    # Make both role-specific vaults reachable but keep their contents private.
    # Do not publish a success receipt until the actual kernel access check and
    # directory-entry durability barrier have succeeded. Failed attempts are
    # preserved without a success receipt (and cannot reuse the attempt ID).
    os.chmod(attempt, 0o711)
    _probe_actual_vault_access(observations=obs_file, labels=label_file,
                               writer=writer, escrow=escrow)
    for folder in (observations, label_vault, attempt, output_parent):
        fd = os.open(folder, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    _write_json_exclusive(attempt / "source_custody_receipt.json", receipt)
    fd = os.open(attempt, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)
    return receipt


def provision_real_stage10a_source(
    *, source_root: Path, output_parent: Path, attempt_id: str,
    writer_uid: int, writer_gid: int, escrow_uid: int, escrow_gid: int,
) -> dict[str, Any]:
    """Single production source-only entrypoint; never load a model/checkpoint."""
    _validate_privileges((writer_uid, writer_gid), (escrow_uid, escrow_gid))
    source_root = Path(source_root)
    output_parent = Path(output_parent)
    _controller_dir(source_root, 0o700)
    _controller_dir(output_parent, 0o711)
    if (source_root == output_parent or source_root in output_parent.parents
        or output_parent in source_root.parents):
        raise ValueError("Original source and output custody roots must be disjoint")
    # The original labeled source is available only to the root controller.
    from tools.stage10 import stage10a_source_readiness as frozen
    original = source_root / frozen.SOURCE_FILE
    if (not original.is_file() or original.is_symlink() or
        original.stat().st_uid != 0 or
        stat.S_IMODE(original.stat().st_mode) != 0o400):
        raise ValueError("Original Wednesday source must be root-owned mode 0400")
    from concept_drift_ids.stage10a_source_adapter import load_stage10a_source_only
    package = load_stage10a_source_only(source_root)
    # The privileged *controller only* may hold both arrays simultaneously.
    observations = package.observations._features
    labels = np.asarray(package.delayed_labels._targets, dtype=np.uint8)
    return _materialize(
        output_parent=output_parent, attempt_id=attempt_id,
        writer=(writer_uid, writer_gid), escrow=(escrow_uid, escrow_gid),
        x=observations, labels=labels,
        source_receipt={
            "source_sha256": package.receipt.source_sha256,
            "ordered_row_ids_sha256": package.receipt.ordered_row_ids_sha256,
            "retained_rows": package.receipt.retained_rows,
            "protocol_id": package.receipt.protocol_id,
            "treatment_execution_authorized": package.receipt.treatment_execution_authorized,
        },
    )


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Root-only Stage-10A original input separation; NO treatments")
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--output-parent", type=Path, required=True)
    parser.add_argument("--attempt-id", required=True)
    parser.add_argument("--writer-uid", type=int, required=True)
    parser.add_argument("--writer-gid", type=int, required=True)
    parser.add_argument("--escrow-uid", type=int, required=True)
    parser.add_argument("--escrow-gid", type=int, required=True)
    args = parser.parse_args()
    out = provision_real_stage10a_source(**vars(args))
    print(json.dumps({"source_provisioned": True,
                      "source_only": True,
                      "stage10a_treatment_execution_authorized": False,
                      "receipt_schema": out["schema"]}, sort_keys=True))
