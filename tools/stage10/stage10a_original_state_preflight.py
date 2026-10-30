"""Stage-10A original checkpoint/R0 byte preflight; NEVER a treatment runner.

The CLI reads existing frozen manifests and external original checkpoint files,
checks their cryptographic identities and writes only a non-outcome receipt.
No torch.load, no model forward pass, no adaptation or scientific result.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from tools.stage10.stage10a_execution_candidate import ROOT, verify_from_repository
from tools.stage10.stage10a_source_receipt import (
    _git_output,
    _validate_git_identity,
    _write_once,
)

SEEDS = tuple(range(5))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def json_core_hash(payload: Mapping[str, Any]) -> str:
    core = dict(payload)
    core.pop("artifact_sha256", None)
    return hashlib.sha256(json.dumps(
        core, ensure_ascii=False, sort_keys=True, allow_nan=False,
        separators=(",", ":"),
    ).encode("utf-8")).hexdigest()


def normalized_rule_text_hash(path: Path) -> str:
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        text = raw.decode("utf-8-sig")
    elif raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        text = raw.decode("utf-16")
    else:
        text = raw.decode("utf-8")
    return hashlib.sha256(text.replace(
        "\r\n", "\n"
    ).replace("\r", "\n").encode("utf-8")).hexdigest()


def verify_checkpoints(
    directory: Path, expected_sha256: Mapping[str, str]
) -> tuple[dict[str, Any], ...]:
    if set(expected_sha256) != {str(i) for i in SEEDS}:
        raise ValueError("Must bind the exact five frozen checkpoint seeds.")
    records = []
    for seed in SEEDS:
        path = directory / f"seed_{seed}.pt"
        if not path.is_file():
            raise ValueError(f"Original System-A seed {seed} file unavailable.")
        actual = sha256_file(path)
        if actual != expected_sha256[str(seed)]:
            raise ValueError(f"Original System-A checkpoint seed {seed} SHA-256 mismatch.")
        records.append({
            "seed": seed, "filename": path.name, "sha256": actual,
            "bytes": path.stat().st_size,
        })
    return tuple(records)


def verify_r0_rules(
    root: Path, expected_rules: Sequence[Mapping[str, Any]]
) -> tuple[dict[str, Any], ...]:
    if len(expected_rules) != 5 or {r.get("seed") for r in expected_rules} != set(SEEDS):
        raise ValueError("Must bind exactly the five original R0.v2 seeds.")
    records = []
    for rule in sorted(expected_rules, key=lambda r: r["seed"]):
        seed = rule["seed"]
        relative = f"data/rules/system_b_r0_v2/seed_{seed}.json"
        if rule["path"] != relative:
            raise ValueError("Frozen R0 rule path differs from accepted identity.")
        path = root / relative
        if not path.is_file():
            raise ValueError(f"R0.v2 seed {seed} rule file unavailable.")
        actual_text = normalized_rule_text_hash(path)
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
        actual_artifact = json_core_hash(payload)
        if (actual_text != rule["text_sha256"]
            or actual_artifact != rule["artifact_sha256"]
            or payload.get("artifact_sha256") != rule["artifact_sha256"]):
            raise ValueError(f"R0.v2 seed {seed} text/artifact identity mismatch.")
        records.append({
            "seed": seed, "relative_path": relative,
            "normalized_text_sha256": actual_text,
            "artifact_sha256": actual_artifact,
        })
    return tuple(records)


def verify_original_state(
    *,
    checkpoint_directory: Path,
    root: Path = ROOT,
) -> dict[str, Any]:
    # A consistency check, not the nonexistent Stage-10 treatment RELEASE.
    consistency = verify_from_repository(root=root)
    if consistency != {
        "candidate_consistent": True,
        "execution_authorized": False,
        "source_receipt_accepted": False,
        "real_three_arm_isolation_verified": False,
    }:
        raise ValueError("Candidate is not frozen at its pre-outcome HOLD state.")
    audit = json.loads(
        (root / "data/manifests/stage9_5_fresh_clone_reconstruction_v1_2.json")
        .read_text(encoding="utf-8")
    )
    candidate = json.loads(
        (root / "data/manifests/stage10a_execution_candidate_v1.json")
        .read_text(encoding="utf-8")
    )
    historical = audit["system_a"]["checkpoints"]
    checkpoint_expected = {
        str(row["seed"]): row["sha256"] for row in historical
    }
    if len(historical) != 5 or checkpoint_expected != (
        candidate["inherited_neural"]["checkpoint_sha256_by_seed"]
    ):
        raise ValueError("Original checkpoint manifest and Stage-10A binding diverge.")
    if audit["r0_v2"]["manifest_sha256"] != (
        candidate["inherited_symbolic"]["r0_v2_manifest_sha256"]
    ):
        raise ValueError("Original R0 manifest and Stage-10A binding diverge.")
    checkpoints = verify_checkpoints(checkpoint_directory, checkpoint_expected)
    rules = verify_r0_rules(root, audit["r0_v2"]["rules"])
    return {
        "audit_id": "stage10a-original-initial-state-source-only-v1",
        "status": "original_artifact_bytes_verified_but_not_treatment_release",
        "checkpoint_files": list(checkpoints),
        "r0_rule_files": list(rules),
        "source_receipt_canonical_complete": False,
        "stage10a_treatment_execution_authorized": False,
        "stage10_treatment_outcomes_accessed": False,
        "no_model_loaded_or_predicted": True,
        "next_stage10a_release_gate": "separate_explicit_release_after_all_readiness_gates",
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Stage-10A ORIGINAL-STATE BYTE CHECK ONLY, NO TREATMENTS"
    )
    parser.add_argument("--checkpoint-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if platform.python_version() != "3.11.9":
        raise RuntimeError("Exact Python 3.11.9 required.")
    git = _validate_git_identity(
        head=_git_output("rev-parse", "HEAD"),
        branch=_git_output("branch", "--show-current"),
        status=_git_output("status", "--porcelain"),
        root=_git_output("rev-parse", "--show-toplevel"),
    )
    if args.output.resolve().is_relative_to(ROOT.resolve()):
        raise ValueError("Write-once receipt must be outside repository checkout.")
    report = verify_original_state(checkpoint_directory=args.checkpoint_dir)
    report["git"] = git
    report["python_version"] = "3.11.9"
    _write_once(args.output, report)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
