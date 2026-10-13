from __future__ import annotations

import hashlib
import json
from pathlib import Path

from tools.stage9_5.fresh_clone_reconstruction import (
    _canonical_json_hash,
    _collect_path_hash_entries,
    _normalized_text_sha256,
    _sha256_file,
)


def test_canonical_json_hash_matches_frozen_encoding() -> None:
    left = {"b": 2, "a": [1, "x"]}
    right = {"a": [1, "x"], "b": 2}
    assert _canonical_json_hash(left) == _canonical_json_hash(right)
    expected = hashlib.sha256(b'{"a":[1,"x"],"b":2}').hexdigest()
    assert _canonical_json_hash(left) == expected


def test_normalized_text_hash_is_eol_independent(tmp_path: Path) -> None:
    lf = tmp_path / "lf.txt"
    crlf = tmp_path / "crlf.txt"
    lf.write_bytes(b"a\nb\n")
    crlf.write_bytes(b"a\r\nb\r\n")
    assert _normalized_text_sha256(lf) == _normalized_text_sha256(crlf)


def test_collect_path_hash_entries_walks_nested_manifest() -> None:
    payload = {
        "a": {"path": "x.json", "sha256": "a" * 64},
        "b": [{"nested": {"path": "y.json", "sha256": "b" * 64}}],
    }
    assert _collect_path_hash_entries(payload) == [
        {"path": "x.json", "sha256": "a" * 64},
        {"path": "y.json", "sha256": "b" * 64},
    ]


def test_sha256_file_uses_raw_bytes(tmp_path: Path) -> None:
    path = tmp_path / "x.bin"
    path.write_bytes(b"abc\r\n")
    assert _sha256_file(path) == hashlib.sha256(b"abc\r\n").hexdigest()


def test_identity_manifest_declares_checkpoint_blocker() -> None:
    root = Path(__file__).resolve().parents[2]
    payload = json.loads(
        (root / "data/manifests/stage9_5_fresh_clone_reconstruction_v1.json").read_text(
            encoding="utf-8"
        )
    )
    assert payload["system_a"]["checkpoint_bytes_required_for_stage9_5_1"] is True
    assert payload["closure_rule"]["fail_on_missing_or_mismatched_system_a_checkpoint_bytes"] is True
    assert len(payload["system_a"]["checkpoints"]) == 5
    assert payload["system_a"]["checkpoint_retrieval"]["repository_committed"] is False


def test_external_raw_inventory_is_complete() -> None:
    root = Path(__file__).resolve().parents[2]
    payload = json.loads(
        (root / "data/manifests/stage9_5_fresh_clone_reconstruction_v1.json").read_text(
            encoding="utf-8"
        )
    )
    files = payload["external_raw_dataset"]["files"]
    assert len(files) == 8
    assert sum(int(item["size_bytes"]) for item in files) == 884645759
    assert all(len(item["sha256"]) == 64 for item in files)
