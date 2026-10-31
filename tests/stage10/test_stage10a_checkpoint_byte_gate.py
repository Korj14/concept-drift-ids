"""Source-only synthetic tests. No network, checkpoint loading or predictions."""
import hashlib
import json
from pathlib import Path
from unittest.mock import patch

import pytest
from tools.stage10.stage10a_checkpoint_byte_gate import (
    EXPECTED, EXPECTED_SIZE, KIND, load_links, validate_request,
    retrieve_one, verify_holds, verify_accepted_source,
)


def request():
    return {
        "kind": KIND, "checkpoint_size_bytes": EXPECTED_SIZE,
        "checkpoint_sha256_by_seed": EXPECTED,
        "transfer_approved_for_identity_only": True,
        "checkpoint_deserialization_allowed": False,
        "stage10a_treatment_execution_authorized": False,
        "fixture_only_pilot_already_passed": True,
    }


def test_frozen_request_passes():
    validate_request(request())


@pytest.mark.parametrize("key,value", [
    ("kind", "other"), ("checkpoint_size_bytes", True),
    ("checkpoint_size_bytes", EXPECTED_SIZE - 1),
    ("checkpoint_deserialization_allowed", True),
    ("stage10a_treatment_execution_authorized", True),
    ("fixture_only_pilot_already_passed", False),
    ("transfer_approved_for_identity_only", False),
    ("checkpoint_sha256_by_seed", {"0": "a" * 64}),
])
def test_invalid_request_rejected(key, value):
    o = request()
    o[key] = value
    with pytest.raises(ValueError):
        validate_request(o)


def test_request_unknown_field_rejected():
    d = request()
    d["some_label"] = "non-source"
    with pytest.raises(ValueError):
        validate_request(d)


def test_missing_or_duplicate_secret_urls_rejected():
    a = {str(i): "https://uc1.dl.dropboxusercontent.com/one" for i in range(5)}
    with pytest.raises(ValueError, match="distinct"):
        load_links(json.dumps(a))
    del a["4"]
    with pytest.raises(ValueError, match="Exactly five"):
        load_links(json.dumps(a))


def test_untrusted_secret_url_rejected():
    a = {str(i): f"https://evil.example/{i}" for i in range(5)}
    with pytest.raises(ValueError):
        load_links(json.dumps(a))


def test_trusted_unique_secret_urls_pass():
    a = {str(i): f"https://uc1.dl.dropboxusercontent.com/{i}" for i in range(5)}
    assert load_links(json.dumps(a)) == a


def test_streaming_wrong_size_is_rejected_without_file_write(tmp_path):
    class MockResponse:
        def __enter__(self):
            return self
        def __exit__(self, *_):
            pass
        def read(self, n):
            assert n == EXPECTED_SIZE + 1
            return b"x" * (EXPECTED_SIZE + 1)

    class MockOpener:
        def open(self, *_, **__):
            return MockResponse()

    with patch("tools.stage10.stage10a_checkpoint_byte_gate.build_opener", return_value=MockOpener()):
        with pytest.raises(ValueError, match="identity mismatch"):
            retrieve_one("0", "https://uc1.dl.dropboxusercontent.com/x", tmp_path)
    assert not list(tmp_path.iterdir())


def test_exact_synthetic_bytes_written_exclusive(tmp_path):
    fake = b"synthetic" * 11
    hash_value = hashlib.sha256(fake).hexdigest()
    class MockResponse:
        def __enter__(self):
            return self
        def __exit__(self, *_):
            pass
        def read(self, n):
            return fake
    class MockOpener:
        def open(self, *_, **__):
            return MockResponse()
    with patch("tools.stage10.stage10a_checkpoint_byte_gate.EXPECTED_SIZE", len(fake)), \
        patch.dict(EXPECTED, {"0": hash_value}), \
        patch("tools.stage10.stage10a_checkpoint_byte_gate.build_opener", return_value=MockOpener()):
        retrieve_one("0", "https://uc1.dl.dropboxusercontent.com/x", tmp_path)
        assert (tmp_path / "seed_0.pt").read_bytes() == fake
        with pytest.raises(FileExistsError):
            retrieve_one("0", "https://uc1.dl.dropboxusercontent.com/x", tmp_path)


def test_frozen_holds_reject_execution_permission(tmp_path):
    def put(path, data):
        p = tmp_path / path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(data))
    put("data/manifests/stage10_plus_master_replication_sensitivity_v1_1.json", {"hard_gate": {"stage10_execution_permitted": True}})
    put("data/manifests/stage10a_goldeneye_attack_pattern_v1.json", {"stage10_treatment_execution_authorized": False, "stage10_treatment_outcomes_accessed_during_freeze": False})
    put("data/manifests/stage10a_execution_candidate_v1.json", {"governance": {"stage10_execution_permitted": False, "stage10a_treatment_execution_authorized": False, "release_signed": False}})
    put("data/manifests/stage9_5_fresh_clone_reconstruction_v1_2.json", {"system_a": {"checkpoints": [{"seed": int(s), "sha256": h} for s, h in EXPECTED.items()]}})
    with pytest.raises(ValueError, match="HOLD"):
        verify_holds(tmp_path)


def test_frozen_holds_reject_changed_checkpoint(tmp_path):
    def put(path, data):
        p = tmp_path / path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(data))
    put("data/manifests/stage10_plus_master_replication_sensitivity_v1_1.json", {"hard_gate": {"stage10_execution_permitted": False}})
    put("data/manifests/stage10a_goldeneye_attack_pattern_v1.json", {"stage10_treatment_execution_authorized": False, "stage10_treatment_outcomes_accessed_during_freeze": False})
    put("data/manifests/stage10a_execution_candidate_v1.json", {"governance": {"stage10_execution_permitted": False, "stage10a_treatment_execution_authorized": False, "release_signed": False}, "inherited_neural":{"checkpoint_sha256_by_seed":EXPECTED}})
    put("data/manifests/stage9_5_fresh_clone_reconstruction_v1_2.json", {"system_a": {"checkpoints": [{"seed": int(s), "sha256": "0" * 64} for s in EXPECTED]}})
    with pytest.raises(ValueError, match="provenance"):
        verify_holds(tmp_path)


def test_immutable_source_receipt_rejects_changed_bytes(tmp_path):
    p = tmp_path / "results/audits/stage10a_original_source_receipt_601516ff_2026_10_31.json"
    p.parent.mkdir(parents=True)
    p.write_bytes(b"tampered")
    with pytest.raises(ValueError, match="receipt bytes changed"):
        verify_accepted_source(tmp_path)


def test_no_checkpoint_deserializer_imported():
    import inspect
    import tools.stage10.stage10a_checkpoint_byte_gate as m
    src = inspect.getsource(m)
    assert "torch.load(" not in src
    assert "pickle.load(" not in src
    assert "model.predict(" not in src
