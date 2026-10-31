"""Stage-10A source-only five-checkpoint byte gate. NEVER deserializes checkpoints.

Consumes exactly five short-lived Dropbox URLs only after checking frozen HOLD
manifests, the immutable accepted CSV source receipt, exact Git identity and a
single-request commit. Bytes live exclusively in a temporary runner directory.
Only an identity-only, write-once receipt is retained. No model or prediction.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from urllib.request import ProxyHandler, Request, build_opener

from tools.stage10.stage10a_dropbox_harmless_pilot import (
    DropboxRedirectGuard, check_git, validate_url, write_once,
)
from tools.stage10.stage10a_execution_candidate import ROOT, tracked_blob_identity
from tools.stage10.stage10a_original_state_preflight import verify_original_state

EXPECTED_SIZE = 76105
EXPECTED = {
    "0": "514c6d552b3cd680ae966bbb568105bd2871bc68d3a47aded070a70ba0615bd1",
    "1": "07696c3f580645d9c96ac3e736cfb5eeaa8033f148bf64822e8ee105861cf552",
    "2": "7630514cf409256bd2bbe27eca59f881acb238be698b5fdb1ee12bca8e402491",
    "3": "cce1ce47db047b9d441bbe6dad9bd53f1ee6ff3ad7d404521cae72a38bccd4b4",
    "4": "9b9e56371f3246482998c4efea4829e1e6d5aaf549bb43e1af05e471dfcb9e93",
}
FROZEN_SOURCE_RECEIPT_BLOB = "a3f2e1e9cec47add542505cab2e48eec2c4351ad"
FROZEN_SOURCE_RECEIPT_RAW_SHA256 = "d6e0874181b4aebe4d259b7f4f66b7d608aaf7803c6dc3c10f0151aaf2f9a42a"
FROZEN_SOURCE_RECEIPT_CORE_SHA256 = "eb145dda1654df375016eb254e90e469b3318ebbc7a6fd17b4402a9ef855c93a"
RECEIPT_PATH = "results/audits/stage10a_original_source_receipt_601516ff_2026_10_31.json"
REQUEST_RE = re.compile(r"original-[0-9a-f]{16}\.json\Z")
KIND = "stage10a-original-checkpoint-byte-preflight-request-v1"


def validate_request(request: object) -> None:
    if not isinstance(request, dict) or set(request) != {
        "kind", "checkpoint_size_bytes", "checkpoint_sha256_by_seed",
        "transfer_approved_for_identity_only", "checkpoint_deserialization_allowed",
        "stage10a_treatment_execution_authorized", "fixture_only_pilot_already_passed",
    }:
        raise ValueError("Invalid request shape")
    if (request["kind"] != KIND
        or type(request["checkpoint_size_bytes"]) is not int
        or request["checkpoint_size_bytes"] != EXPECTED_SIZE
        or request["checkpoint_sha256_by_seed"] != EXPECTED
        or request["transfer_approved_for_identity_only"] is not True
        or request["checkpoint_deserialization_allowed"] is not False
        or request["stage10a_treatment_execution_authorized"] is not False
        or request["fixture_only_pilot_already_passed"] is not True):
        raise ValueError("Request not frozen at source-only identity scope")


def verify_accepted_source(root: Path) -> dict:
    """Do not trust the frozen candidate's stale source_receipt_accepted=False flag."""
    file = root / RECEIPT_PATH
    raw = file.read_bytes()
    if (hashlib.sha256(raw).hexdigest() != FROZEN_SOURCE_RECEIPT_RAW_SHA256
        or tracked_blob_identity(file) != FROZEN_SOURCE_RECEIPT_BLOB):
        raise ValueError("Accepted Wednesday source receipt bytes changed")
    receipt = json.loads(raw)
    core = dict(receipt)
    digest = core.pop("canonical_sha256", None)
    actual = hashlib.sha256(json.dumps(
        core, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")).hexdigest()
    if digest != FROZEN_SOURCE_RECEIPT_CORE_SHA256 or actual != digest:
        raise ValueError("Accepted Wednesday source receipt core digest mismatch")
    required = {
        "audit_id": "stage10a-original-source-receipt-v1",
        "pass": True,
        "python_version": "3.11.9",
        "raw_source_sha256": "893c27dc968bf7a8adef1689f90be55ca4a4dc3088fb63d6ff247ac56856df2a",
        "logical_rows": 138530,
        "frozen_features": 77,
        "label_latency_rows": 5000,
        "model_checkpoints_loaded": False,
        "neural_or_symbolic_treatments_executed": False,
        "stage10_treatment_execution_authorized": False,
        "stage10_treatment_outcomes_accessed": False,
    }
    for key, value in required.items():
        if type(receipt.get(key)) is not type(value) or receipt[key] != value:
            raise ValueError("Accepted source receipt fails prospective identity gate")
    if receipt.get("git") != {
        "branch": "stage10a-governance", "clean": "true",
        "head": "601516ff7e71d14fdcab2c7caa76fdc512aa9e71",
    }:
        raise ValueError("Accepted source receipt lacks exact original run identity")
    return {"source_receipt_canonical_complete": True,
            "source_receipt_git_blob_sha1": FROZEN_SOURCE_RECEIPT_BLOB,
            "source_receipt_canonical_sha256": digest}


def verify_holds(root: Path) -> None:
    master = json.loads((root / "data/manifests/stage10_plus_master_replication_sensitivity_v1_1.json").read_text())
    stage = json.loads((root / "data/manifests/stage10a_goldeneye_attack_pattern_v1.json").read_text())
    candidate = json.loads((root / "data/manifests/stage10a_execution_candidate_v1.json").read_text())
    historical = json.loads((root / "data/manifests/stage9_5_fresh_clone_reconstruction_v1_2.json").read_text())
    if (master["hard_gate"]["stage10_execution_permitted"] is not False
        or stage["stage10_treatment_execution_authorized"] is not False
        or stage["stage10_treatment_outcomes_accessed_during_freeze"] is not False
        or candidate["governance"]["stage10_execution_permitted"] is not False
        or candidate["governance"]["stage10a_treatment_execution_authorized"] is not False
        or candidate["governance"]["release_signed"] is not False):
        raise ValueError("Stage10/10A HOLD gate violated")
    original = historical["system_a"]["checkpoints"]
    if (len(original) != 5 or
        {str(item["seed"]): item["sha256"] for item in original} != EXPECTED or
        candidate["inherited_neural"]["checkpoint_sha256_by_seed"] != EXPECTED):
        raise ValueError("Frozen checkpoint provenance diverged")


def load_links(secret: str) -> dict[str, str]:
    # Secret is NEVER logged, written, printed, or preserved in the receipt.
    urls = json.loads(secret)
    if not isinstance(urls, dict) or set(urls) != set(EXPECTED):
        raise ValueError("Exactly five Dropbox one-use URLs required")
    for url in urls.values():
        validate_url(url)
    if len(set(urls.values())) != 5:
        raise ValueError("All five one-use links must be distinct")
    return urls


def retrieve_one(seed: str, url: str, directory: Path) -> None:
    """Exactly one GET per seed; prevent proxy leaks and untrusted redirects."""
    opener = build_opener(ProxyHandler({}), DropboxRedirectGuard())
    # No HEAD, Range, preflight, retries, caching, or URL-bearing exception logs.
    with opener.open(Request(url, method="GET"), timeout=45) as response:
        data = response.read(EXPECTED_SIZE + 1)
    if len(data) != EXPECTED_SIZE or hashlib.sha256(data).hexdigest() != EXPECTED[seed]:
        raise ValueError("Original System-A byte identity mismatch")
    target = directory / f"seed_{seed}.pt"
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(target, flags, 0o600)
    with os.fdopen(fd, "wb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())


def perform(*, request_path: Path, output: Path, runner_temp: Path, link_secret: str) -> None:
    # Source/script checkout is immutable at the exact triggering commit.
    head = check_git()
    request = request_path.resolve()
    if (request.parent != (ROOT / ".github/stage10a-requests").resolve()
        or not REQUEST_RE.fullmatch(request.name)
        or request.stat().st_size > 4096):
        raise ValueError("Invalid Stage-10A request location")
    validate_request(json.loads(request.read_text(encoding="utf-8")))
    verify_holds(ROOT)
    source = verify_accepted_source(ROOT)
    urls = load_links(link_secret)
    if not runner_temp.is_dir() or runner_temp.resolve().is_relative_to(ROOT.resolve()):
        raise ValueError("Temporary external runner directory required")
    if output.resolve().is_relative_to(ROOT.resolve()):
        raise ValueError("Receipt must be outside tracked checkout")
    with tempfile.TemporaryDirectory(prefix="stage10a-original-bytes-", dir=runner_temp) as tmp:
        work = Path(tmp)
        for seed in EXPECTED:
            retrieve_one(seed, urls[seed], work)
        # Existing frozen-source-only preflight verifies five exact file SHA-256s
        # AND five accepted R0.v2 LF-normalized text/artifact identities.
        report = verify_original_state(checkpoint_directory=work, root=ROOT)
        if (report["source_receipt_canonical_complete"] is not False
            or report["stage10a_treatment_execution_authorized"] is not False
            or report["stage10_treatment_outcomes_accessed"] is not False
            or report["no_model_loaded_or_predicted"] is not True
            or len(report["checkpoint_files"]) != 5
            or len(report["r0_rule_files"]) != 5
            or any(x["bytes"] != EXPECTED_SIZE or x["sha256"] != EXPECTED[str(x["seed"])]
                   for x in report["checkpoint_files"])):
            raise ValueError("Original-state preflight did not return frozen HOLD")
        report.update(source)
        report.update({
            "audit_id": "stage10a-original-checkpoint-source-only-github-transfer-v1",
            "pass": True,
            "git_head": head,
            "git_branch": "stage10a-governance",
            "python_version": "3.11.9",
            "original_checkpoint_bytes_transferred_ephemerally": True,
            "checkpoint_bytes_preserved_in_artifact": False,
            "dropbox_links_preserved_in_artifact": False,
            "stage10a_treatment_execution_authorized": False,
            "stage10_treatment_outcomes_accessed": False,
            "no_model_loaded_or_predicted": True,
        })
        write_once(output, report)
    print("Stage-10A five checkpoint SHA-256 and R0.v2 source-only identities PASS. No model loaded.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Source-only original checkpoint SHA-256 and R0.v2 identity gate")
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        perform(
            request_path=args.request, output=args.output,
            runner_temp=Path(os.environ["RUNNER_TEMP"]),
            link_secret=os.environ["STAGE10A_ORIGINAL_CHECKPOINT_LINKS_JSON"],
        )
    except BaseException:
        # Keep Dropbox signed links and transported checkpoint data out of logs.
        sys.exit("Stage-10A source-only original checkpoint identity gate FAILED. STOP; investigate privately.")


if __name__ == "__main__":
    main()
