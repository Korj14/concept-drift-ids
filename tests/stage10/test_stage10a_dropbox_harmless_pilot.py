"""Harmless, local-only synthetic pilot tests. No network or treatment execution."""
import hashlib
import pytest
from tools.stage10.stage10a_dropbox_harmless_pilot import (
    KIND, EXPECTED_BYTES, EXPECTED_SHA256, DropboxRedirectGuard,
    validate_url, validate_request, verify_binary, write_once,
)


def request():
    return {"kind": KIND, "non_sensitive_fixture_confirmed": True,
            "fixture_size_bytes": EXPECTED_BYTES, "fixture_sha256": EXPECTED_SHA256,
            "checkpoint_file": False, "treatment_execution_authorized": False}


def test_good_request():
    validate_request(request())


@pytest.mark.parametrize("field,value", [
    ("kind", "checkpoint"), ("non_sensitive_fixture_confirmed", False),
    ("checkpoint_file", True), ("treatment_execution_authorized", True),
    ("fixture_size_bytes", True), ("fixture_size_bytes", 4096),
    ("fixture_sha256", "a" * 64),
])
def test_bad_request(field, value):
    d = request()
    d[field] = value
    with pytest.raises(ValueError):
        validate_request(d)


def test_unknown_field():
    d = request()
    d["outcome_mcc"] = .9
    with pytest.raises(ValueError):
        validate_request(d)


@pytest.mark.parametrize("url", [
    "", "http://uc1.dl.dropboxusercontent.com/file",
    "https://dl.dropboxusercontent.com.evil.example/file",
    "https://www.dropbox.com/home/a",
    "https://user:pass@uc1.dl.dropboxusercontent.com/file",
    "https://uc1.dl.dropboxusercontent.com:8080/file",
    "https://uc1.dl.dropboxusercontent.com/file#fragment",
])
def test_disallowed_urls(url):
    with pytest.raises(ValueError):
        validate_url(url)


def test_allowed_host_and_redirect_guard():
    validate_url("https://uc1.dl.dropboxusercontent.com/cd/0/get/fixture?c_luid=abc")
    with pytest.raises(ValueError):
        DropboxRedirectGuard().redirect_request(None, None, 302, "redirect", {},
                                                "https://evil.example/file")


def test_exact_fixture_bytes():
    # Tests a local harmless 120-byte mock. The real fixture digest is frozen.
    with pytest.raises(ValueError):
        verify_binary(b"x" * EXPECTED_BYTES)
    with pytest.raises(ValueError):
        verify_binary(b"x" * (EXPECTED_BYTES + 1))


def test_exclusive_receipt(tmp_path):
    p = tmp_path / "receipt.json"
    write_once(p, {"pass": True})
    existing = p.read_bytes()
    with pytest.raises(FileExistsError):
        write_once(p, {"pass": False})
    assert p.read_bytes() == existing
