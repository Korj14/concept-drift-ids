"""Verify external Stage-10A G2 launch-receipt signature; never authorize execution.

This is one building block, not an attester, original-source loader, model
executor, custody verification, RELEASE, or substitute for independent review.
The trusted public-key fingerprint MUST be supplied from outside the writer's
control; a public key supplied by the same untrusted writer proves nothing.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
from typing import Any

SCHEMA = "stage10a-g2-external-launch-receipt-v1"
STAGE_MANIFEST_GIT_BLOB = "001501350fbf9fa4a4075176b9af43c2cf275bc5"
MASTER_MANIFEST_GIT_BLOB = "8ac82c8d907243556a5673d09600cd1bdc19aa52"
ORIGINAL_SOURCE_RECEIPT_SHA256 = "d6e0874181b4aebe4d259b7f4f66b7d608aaf7803c6dc3c10f0151aaf2f9a42a"
ORIGINAL_CHECKPOINT_RECEIPT_SHA256 = "94cf6ee608e63be4834372aa0be8956eaaf289234f395dd788a9e0d23ba2b1c1"
HEX64 = re.compile(r"^[0-9a-f]{64}$")
HEX40 = re.compile(r"^[0-9a-f]{40}$")
THREADS = {"MKL_NUM_THREADS": "1", "NUMEXPR_NUM_THREADS": "1", "OMP_NUM_THREADS": "1",
           "OPENBLAS_NUM_THREADS": "1", "PYTHONHASHSEED": "0"}
TOP_KEYS = {"schema", "issued_by", "scope", "subject_git_head", "frozen_authority",
            "runtime", "access_observation", "attempt_id", "release_authorized"}
FROZEN_KEYS = {"stage_manifest_git_blob_sha1", "master_manifest_git_blob_sha1",
               "original_source_receipt_sha256", "original_checkpoint_receipt_sha256"}
RUNTIME_KEYS = {"python_version", "requirements_lock_sha256", "clean_exact_head_checkout",
                "executor_image_sha256", "host_job_identity", "thread_environment"}
ACCESS_KEYS = {"writer_principal_id", "label_custodian_principal_id",
               "checkpoint_custodian_principal_id", "access_deny_receipt_sha256",
               "append_policy_receipt_sha256", "checkpoint_policy_receipt_sha256",
               "phase_b_readonly_policy_receipt_sha256"}


def _sha(x: bytes) -> str:
    return hashlib.sha256(x).hexdigest()


def _hex(value: Any, width: int = 64) -> bool:
    return type(value) is str and bool((HEX64 if width == 64 else HEX40).fullmatch(value))


def _keys(obj: Any, required: set[str]) -> bool:
    return type(obj) is dict and set(obj) == required


def _read_regular(path: Path, *, max_size: int) -> bytes:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > max_size:
        raise ValueError("Missing, redirected, or oversized independent receipt input")
    return path.read_bytes()


def _openssl(executable: str | None = None) -> str:
    binary = executable or shutil.which("openssl")
    if not binary:
        raise ValueError("OpenSSL executable required for external signature validation")
    return binary


def trusted_public_key_sha256(public_key: Path, *, openssl: str | None = None) -> str:
    """Fingerprint OpenSSL DER SubjectPublicKeyInfo, NOT raw PEM formatting."""
    pem = _read_regular(Path(public_key), max_size=8192)
    if b"PRIVATE KEY" in pem or b"BEGIN PUBLIC KEY" not in pem:
        raise ValueError("Only an externally trusted public key is permitted")
    done = subprocess.run([_openssl(openssl), "pkey", "-pubin", "-in", str(public_key),
                           "-outform", "DER"], capture_output=True, timeout=10, check=False)
    if done.returncode != 0 or not done.stdout:
        raise ValueError("Unparseable trusted public key")
    return _sha(done.stdout)


def verify_external_launch_receipt(*, receipt: Path, signature: Path,
                                   trusted_public_key: Path,
                                   independently_pinned_key_sha256: str,
                                   expected_git_head: str,
                                   openssl: str | None = None) -> dict[str, Any]:
    """Verify authenticated *claim*, NOT the claimed physical isolation.

    All paths are read-only. No raw CICIDS, checkpoints, models or labels used.
    This function MUST NOT emit RELEASE=true regardless of receipt contents.
    """
    if not _hex(independently_pinned_key_sha256) or not _hex(expected_git_head, 40):
        raise ValueError("Malformed independent public-key pin or expected exact Git HEAD")
    if trusted_public_key_sha256(trusted_public_key, openssl=openssl) != independently_pinned_key_sha256:
        raise ValueError("External key does not match independently provisioned pin")
    raw = _read_regular(Path(receipt), max_size=16384)
    try:
        doc = json.loads(raw)
    except (ValueError, UnicodeError) as exc:
        raise ValueError("Malformed independent launch receipt") from exc
    if not _keys(doc, TOP_KEYS) or raw != (json.dumps(doc, sort_keys=True, separators=(",", ":"),
                                              ensure_ascii=False, allow_nan=False) + "\n").encode():
        raise ValueError("Receipt must be canonical JSON with exact allowed fields")
    frozen = doc["frozen_authority"]
    runtime = doc["runtime"]
    access = doc["access_observation"]
    if (doc["schema"] != SCHEMA or doc["issued_by"] != "independent_launch_controller"
        or doc["scope"] != "pre_execution_source_only"
        or doc["subject_git_head"] != expected_git_head
        or doc["release_authorized"] is not False
        or type(doc["attempt_id"]) is not str or not 1 <= len(doc["attempt_id"]) <= 128
        or not _keys(frozen, FROZEN_KEYS) or not _keys(runtime, RUNTIME_KEYS)
        or not _keys(access, ACCESS_KEYS)):
        raise ValueError("Receipt identity, exact-head authority, or release boundary invalid")
    expected_frozen = {
        "stage_manifest_git_blob_sha1": STAGE_MANIFEST_GIT_BLOB,
        "master_manifest_git_blob_sha1": MASTER_MANIFEST_GIT_BLOB,
        "original_source_receipt_sha256": ORIGINAL_SOURCE_RECEIPT_SHA256,
        "original_checkpoint_receipt_sha256": ORIGINAL_CHECKPOINT_RECEIPT_SHA256,
    }
    if frozen != expected_frozen:
        raise ValueError("Original accepted scientific/source authority changed")
    if (runtime["python_version"] != "3.11.9"
        or runtime["clean_exact_head_checkout"] is not True
        or runtime["thread_environment"] != THREADS
        or not _hex(runtime["requirements_lock_sha256"])
        or not _hex(runtime["executor_image_sha256"])
        or type(runtime["host_job_identity"]) is not str
        or not runtime["host_job_identity"].strip()):
        raise ValueError("Runtime observation does not match the frozen preflight contract")
    principals = [access[k] for k in ("writer_principal_id", "label_custodian_principal_id",
                                      "checkpoint_custodian_principal_id")]
    if (any(type(x) is not str or not x.strip() for x in principals)
        or len(set(principals)) != 3
        or any(not _hex(access[k]) for k in ACCESS_KEYS if k.endswith("sha256"))):
        raise ValueError("Independent custody observation is missing or not principal-separated")
    sig_bytes = _read_regular(Path(signature), max_size=512)
    if len(sig_bytes) != 64:  # OpenSSL Ed25519 signature length.
        raise ValueError("Expected a raw Ed25519 signature")
    public_pem = _read_regular(Path(trusted_public_key), max_size=8192)
    if b"-----BEGIN PUBLIC KEY-----" not in public_pem:
        raise ValueError("Trusted public key must have SubjectPublicKeyInfo PEM format")
    completed = subprocess.run([
        _openssl(openssl), "pkeyutl", "-verify", "-pubin", "-inkey",
        str(trusted_public_key), "-rawin", "-in", str(receipt),
        "-sigfile", str(signature)], capture_output=True, timeout=10, check=False)
    if completed.returncode != 0:
        raise ValueError("Independent launch receipt signature is invalid")
    return {
        "external_receipt_signature_valid": True,
        "source_only_identity_claim_authenticated": True,
        "receipt_sha256": _sha(raw),
        "public_key_sha256": independently_pinned_key_sha256,
        "subject_git_head": expected_git_head,
        # A signed claim is not proof of enforcement or trusted signer custody.
        "host_principal_isolation_independently_verified": False,
        "predictions_durably_witnessed": False,
        "real_neural_or_symbolic_execution_verified": False,
        "stage10a_g2_accepted": False,
        "stage10a_treatment_execution_authorized": False,
        "stage10a_release_ready": False,
    }


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Stage-10A external receipt signature check; NO RELEASE")
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--signature", type=Path, required=True)
    parser.add_argument("--trusted-public-key", type=Path, required=True)
    parser.add_argument("--independent-key-pin-sha256", required=True)
    parser.add_argument("--expected-git-head", required=True)
    args = parser.parse_args()
    print(json.dumps(verify_external_launch_receipt(
        receipt=args.receipt, signature=args.signature,
        trusted_public_key=args.trusted_public_key,
        independently_pinned_key_sha256=args.independent_key_pin_sha256,
        expected_git_head=args.expected_git_head), sort_keys=True))


if __name__ == "__main__":
    main()
