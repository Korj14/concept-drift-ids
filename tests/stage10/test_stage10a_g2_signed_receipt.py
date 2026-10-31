"""Actual Ed25519 cryptographic checks. No model, CSV, synthetic predictions."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import shutil
import subprocess

import pytest

from tools.stage10 import stage10a_g2_signed_receipt as a


@pytest.fixture
def receipt_bundle(tmp_path):
    if not shutil.which("openssl"):
        pytest.skip("No OpenSSL binary in this host")
    priv = tmp_path / "controller-private.pem"
    pub = tmp_path / "controller-public.pem"
    receipt = tmp_path / "launch.json"
    signature = tmp_path / "launch.sig"
    def cmd(*args):
        subprocess.run(["openssl", *map(str, args)], check=True, capture_output=True)
    cmd("genpkey", "-algorithm", "ED25519", "-out", priv)
    cmd("pkey", "-in", priv, "-pubout", "-out", pub)
    doc = {
        "schema": a.SCHEMA,
        "issued_by": "independent_launch_controller",
        "scope": "pre_execution_source_only",
        "subject_git_head": "a"*40,
        "attempt_id": "preflight-g2-001",
        "release_authorized": False,
        "frozen_authority": {
            "stage_manifest_git_blob_sha1": a.STAGE_MANIFEST_GIT_BLOB,
            "master_manifest_git_blob_sha1": a.MASTER_MANIFEST_GIT_BLOB,
            "original_source_receipt_sha256": a.ORIGINAL_SOURCE_RECEIPT_SHA256,
            "original_checkpoint_receipt_sha256": a.ORIGINAL_CHECKPOINT_RECEIPT_SHA256,
        },
        "runtime": {
            "python_version": "3.11.9",
            "requirements_lock_sha256": "c"*64,
            "clean_exact_head_checkout": True,
            "executor_image_sha256": "d"*64,
            "host_job_identity": "externally-controlled-job-1",
            "thread_environment": a.THREADS,
        },
        "access_observation": {
            "writer_principal_id": "uid-2020",
            "label_custodian_principal_id": "uid-2021",
            "checkpoint_custodian_principal_id": "uid-2022",
            "access_deny_receipt_sha256": "1"*64,
            "append_policy_receipt_sha256": "2"*64,
            "checkpoint_policy_receipt_sha256": "3"*64,
            "phase_b_readonly_policy_receipt_sha256": "4"*64,
        },
    }
    def sign(d):
        receipt.write_bytes((json.dumps(d, sort_keys=True, separators=(",", ":"),
                                      ensure_ascii=False, allow_nan=False)+"\n").encode())
        cmd("pkeyutl", "-sign", "-inkey", priv, "-rawin", "-in", receipt, "-out", signature)
    sign(doc)
    kw = dict(receipt=receipt, signature=signature, trusted_public_key=pub,
              independently_pinned_key_sha256=a.trusted_public_key_sha256(pub),
              expected_git_head="a"*40)
    return doc, sign, kw, tmp_path


def test_valid_signature_authenticates_claim_but_never_grants_release(receipt_bundle):
    _, _, kw, _ = receipt_bundle
    result = a.verify_external_launch_receipt(**kw)
    assert result["external_receipt_signature_valid"] is True
    assert result["stage10a_g2_accepted"] is False
    assert result["stage10a_release_ready"] is False
    assert result["host_principal_isolation_independently_verified"] is False


def test_tampered_unsigned_receipt_rejected(receipt_bundle):
    _, _, kw, _ = receipt_bundle
    kw["receipt"].write_bytes(kw["receipt"].read_bytes().replace(b"uid-2022", b"uid-2222"))
    with pytest.raises(ValueError, match="signature"):
        a.verify_external_launch_receipt(**kw)


@pytest.mark.parametrize("change", [
    "self_release", "bad_master", "bad_stage", "wrong_git", "future_labels_same_uid",
    "bad_python", "dirty_checkout", "bad_thread", "missing_access", "extra_fields", "changed_receipt",
])
def test_signed_but_policy_invalid_document_rejected(receipt_bundle, change):
    doc, sign, kw, _ = receipt_bundle
    doc = copy.deepcopy(doc)
    if change == "self_release": doc["release_authorized"] = True
    elif change == "bad_master": doc["frozen_authority"]["master_manifest_git_blob_sha1"] = "e"*40
    elif change == "bad_stage": doc["frozen_authority"]["stage_manifest_git_blob_sha1"] = "f"*40
    elif change == "wrong_git": doc["subject_git_head"] = "b"*40
    elif change == "future_labels_same_uid": doc["access_observation"]["label_custodian_principal_id"] = "uid-2020"
    elif change == "bad_python": doc["runtime"]["python_version"] = "3.13.5"
    elif change == "dirty_checkout": doc["runtime"]["clean_exact_head_checkout"] = False
    elif change == "bad_thread": doc["runtime"]["thread_environment"]["OMP_NUM_THREADS"] = "2"
    elif change == "missing_access": doc["access_observation"].pop("access_deny_receipt_sha256")
    elif change == "extra_fields": doc["real_treatment_release_signed"] = True
    else: doc["frozen_authority"]["original_source_receipt_sha256"] = "a"*64
    sign(doc)
    with pytest.raises(ValueError):
        a.verify_external_launch_receipt(**kw)


def test_unpinned_or_swapped_public_key_rejected(receipt_bundle):
    _, _, kw, temp = receipt_bundle
    with pytest.raises(ValueError, match="pin"):
        a.verify_external_launch_receipt(**{**kw, "independently_pinned_key_sha256": "0"*64})
    other = temp / "other-private.pem"
    other_pub = temp / "other-public.pem"
    subprocess.run(["openssl", "genpkey", "-algorithm", "ED25519", "-out", str(other)],
                   check=True, capture_output=True)
    subprocess.run(["openssl", "pkey", "-in", str(other), "-pubout", "-out", str(other_pub)],
                   check=True, capture_output=True)
    with pytest.raises(ValueError, match="signature"):
        a.verify_external_launch_receipt(**{**kw, "trusted_public_key": other_pub,
          "independently_pinned_key_sha256": a.trusted_public_key_sha256(other_pub)})


def test_refuse_symlink_and_noncanonical_encoding(receipt_bundle):
    _, sign, kw, temp = receipt_bundle
    alt = temp / "symlink.json"
    alt.symlink_to(kw["receipt"])
    with pytest.raises(ValueError, match="redirected"):
        a.verify_external_launch_receipt(**{**kw, "receipt": alt})
    data = json.loads(kw["receipt"].read_bytes())
    kw["receipt"].write_bytes(json.dumps(data, indent=2).encode()+b"\n")
    with pytest.raises(ValueError, match="canonical"):
        a.verify_external_launch_receipt(**kw)


def test_no_treatment_imports_or_signing_key_handling():
    source = Path(a.__file__).read_text()
    for forbidden in ("import torch", "torch.load(", "pandas.read_csv(",
                      "checkpoint.pt", "genpkey", '"-sign"', "stage10_execution_permitted=True"):
        assert forbidden not in source
