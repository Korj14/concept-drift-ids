"""Stage-10A harmless single-use Dropbox URL test. No checkpoints or treatments.

A sandboxed data-transfer feasibility check only. It accepts a small synthetic
fixture, initiates one GET (allowing only same-provider trusted redirects), compares bytes to an exact public hash, then writes
an exclusive non-outcome receipt. It never prints its URL or network errors.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

ROOT = Path(__file__).resolve().parents[2]
KIND = "stage10a-harmless-dropbox-pilot-v1"
EXPECTED_BYTES = 120
EXPECTED_SHA256 = "ccbc2e85dff26dc9abc25827133cd4468377e37ecc924d69a9f6bd6134520c8d"
REQUEST_PATTERN = re.compile(r"pilot-[0-9a-f]{16}\.json\Z")


def validate_url(url: str) -> None:
    if not isinstance(url, str) or not url or any(c.isspace() for c in url):
        raise ValueError("Missing or malformed URL")
    parsed = urlsplit(url)
    host = parsed.hostname or ""
    if (parsed.scheme != "https" or not host.endswith(".dl.dropboxusercontent.com")
        or host == ".dl.dropboxusercontent.com"
        or parsed.username is not None or parsed.password is not None
        or parsed.port not in (None, 443) or parsed.fragment):
        raise ValueError("Dropbox HTTPS content host required")


class DropboxRedirectGuard(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        validate_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def validate_request(data: dict) -> None:
    expected_keys = {"kind", "non_sensitive_fixture_confirmed", "fixture_size_bytes",
                     "fixture_sha256", "checkpoint_file", "treatment_execution_authorized"}
    if set(data) != expected_keys:
        raise ValueError("Pilot request schema mismatch")
    if (data["kind"] != KIND or data["non_sensitive_fixture_confirmed"] is not True
        or data["checkpoint_file"] is not False
        or data["treatment_execution_authorized"] is not False):
        raise ValueError("Only a harmless synthetic fixture is allowed")
    if type(data["fixture_size_bytes"]) is not int or data["fixture_size_bytes"] != EXPECTED_BYTES:
        raise ValueError("Fixture size differs from frozen harmless file")
    if data["fixture_sha256"] != EXPECTED_SHA256:
        raise ValueError("Fixture hash differs from frozen harmless file")


def check_git() -> str:
    if platform.python_version() != "3.11.9":
        raise ValueError("Exact Python 3.11.9 required")
    if os.getenv("GITHUB_REF") != "refs/heads/stage10a-governance":
        raise ValueError("Not the Stage-10A branch")
    head = os.getenv("GITHUB_SHA", "")
    if not re.fullmatch(r"[0-9a-f]{40}", head):
        raise ValueError("Invalid GitHub SHA")

    def git(*args: str) -> str:
        return subprocess.run(["git", *args], cwd=ROOT, capture_output=True,
                              check=True, text=True).stdout.strip()

    if (git("rev-parse", "HEAD") != head
        or git("branch", "--show-current") != "stage10a-governance"
        or git("status", "--porcelain")
        or Path(git("rev-parse", "--show-toplevel")).resolve() != ROOT.resolve()):
        raise ValueError("Dirty or non-matching Git checkout")
    return head


def verify_binary(data: bytes) -> None:
    if len(data) != EXPECTED_BYTES or hashlib.sha256(data).hexdigest() != EXPECTED_SHA256:
        raise ValueError("Harmless source identity mismatch")


def write_once(path: Path, receipt: dict) -> None:
    if path.resolve().is_relative_to(ROOT.resolve()):
        raise ValueError("Receipt cannot be written into checkout")
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as file:
        json.dump(receipt, file, sort_keys=True, indent=2, allow_nan=False)
        file.write("\n")
        file.flush()
        os.fsync(file.fileno())


def main() -> None:
    ap = argparse.ArgumentParser(description="Harmless Dropbox fixture only; no checkpoints")
    ap.add_argument("--request", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    request = args.request.resolve()
    allowed_dir = ROOT / ".github/stage10a-requests"
    if request.parent != allowed_dir or not REQUEST_PATTERN.fullmatch(request.name):
        ap.error("Exactly one valid Stage-10A pilot request file required")
    content = json.loads(request.read_text(encoding="utf-8"))
    validate_request(content)
    head = check_git()
    try:
        link = os.getenv("STAGE10A_PILOT_DOWNLOAD_URL", "")
        validate_url(link)
        # One initial GET, no HEAD/Range/retries; redirects restricted to Dropbox.
        with build_opener(DropboxRedirectGuard()).open(Request(link, method="GET"), timeout=60) as response:
            content_bytes = response.read(EXPECTED_BYTES + 1)
        verify_binary(content_bytes)
    except Exception:
        # urllib can include secret URLs in exception messages; suppress all.
        sys.exit("Harmless Dropbox pilot failed (transport or byte identity)")
    write_once(args.output, {
        "audit_id": KIND, "pass": True,
        "scope": "harmless_fixture_only",
        "fixture_sha256": EXPECTED_SHA256,
        "fixture_size_bytes": EXPECTED_BYTES,
        "git_head": head,
        "python_version": "3.11.9",
        "checkpoint_bytes_transferred": False,
        "model_or_treatment_executed": False,
        "stage10a_treatment_execution_authorized": False,
    })
    print("Harmless fixture SHA-256 verified. No checkpoint or treatment accessed.")


if __name__ == "__main__":
    main()
