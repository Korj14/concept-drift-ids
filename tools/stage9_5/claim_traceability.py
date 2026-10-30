from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import subprocess
from collections.abc import Mapping
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = PROJECT_ROOT / "data" / "manifests" / "stage9_5_claim_reporting_v1.json"
DEFINITIONS_PATH = PROJECT_ROOT / "data" / "manifests" / "stage9_5_claim_definitions_v1.json"

SOURCE_COMPATIBILITY_PATH = (
    PROJECT_ROOT / "data" / "manifests" / "stage9_5_claim_source_compatibility_v1_1.json"
)
# These pins make the additive v1.1 policy fail closed if edited after review.
_PINNED_SOURCE_COMPATIBILITY = {'schema_version': '1.1',
 'status': 'assurance_only_corrective_not_stage9_5_closure',
 'scope': 'stage9.5-7-claim-source-ledger-additive-compatibility',
 'frozen_claim_contract': {'path': 'data/manifests/stage9_5_claim_reporting_v1.json',
                           'blob_sha': 'b38302c509bda9af65e2dbf319e7e903a00ab111'},
 'frozen_claim_definitions': {'path': 'data/manifests/stage9_5_claim_definitions_v1.json',
                              'blob_sha': '18157779d5860b366b568926d6a89a2205e75480'},
 'ledger': {'path': 'METHODOLOGY_LEDGER.md',
            'claim_source_blob_sha': '9b977705b9748138bb12745e9f0fb3d77d73c2b2',
            'claim_source_historical_commit': 'b141a65033fee1ffbe7709a54838ea1af1324225',
            'pre_correction_snapshot_blob_sha': '8a14bd17528851e26748b993b7ae85cd90c40db3',
            'pre_correction_commit': '207c05e5e99568fb4cb7f89996af3314be0d5ef3',
            'compatibility_mode': 'immutable_frozen_prefix_and_preserved_snapshot_prefix',
            'report_blob_identity': 'frozen_original'},
 'other_claim_sources': 'require_exact_head_blob_identity',
 'scientific_objects_modified': False,
 'stage10_outcomes_accessed': False}


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _canonical_sha256(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _pointer(value: Any, pointer: str) -> Any:
    if pointer in {"", "/"}:
        return value
    current = value
    for token in pointer.lstrip("/").split("/"):
        token = token.replace("~1", "/").replace("~0", "~")
        if isinstance(current, list):
            current = current[int(token)]
        elif isinstance(current, Mapping):
            current = current[token]
        else:
            raise KeyError(f"Cannot descend through {type(current).__name__} at {token!r}.")
    return current


def _repo_path(relative: str) -> Path:
    return PROJECT_ROOT / relative


def _data(cache: dict[str, Any], relative: str) -> Any:
    if relative not in cache:
        cache[relative] = _load_json(_repo_path(relative))
    return cache[relative]


def _source_seeds(spec: Mapping[str, Any], cache: dict[str, Any]) -> list[Any]:
    source = spec["seed_source"]
    seeds = _pointer(_data(cache, source["path"]), source["pointer"])
    if not isinstance(seeds, list):
        raise TypeError("seed_source must resolve to a list.")
    return seeds


def _aggregate(values: list[Any], kind: str) -> Any:
    if kind == "list":
        return values
    if kind == "mean":
        numeric = [float(item) for item in values if item is not None]
        if not numeric:
            raise ValueError("Cannot compute mean of an empty/non-numeric series.")
        return statistics.fmean(numeric)
    if kind == "sum":
        return sum(values)
    if kind == "count_true":
        return sum(item is True for item in values)
    if kind == "count_false":
        return sum(item is False for item in values)
    raise ValueError(f"Unsupported aggregation: {kind}")


def _resolve(spec: Mapping[str, Any], cache: dict[str, Any]) -> Any:
    kind = spec["type"]
    if kind == "direct":
        return _pointer(_data(cache, spec["path"]), spec["pointer"])
    if kind == "list_length":
        value = _pointer(_data(cache, spec["path"]), spec["pointer"])
        return len(value)
    if kind == "seed_aggregate":
        values: list[Any] = []
        for seed in _source_seeds(spec, cache):
            path = spec["path_pattern"].format(seed=seed)
            values.append(_pointer(_data(cache, path), spec["pointer"]))
        return _aggregate(values, spec["aggregation"])
    if kind == "seed_nested_relation_count":
        threshold = _resolve(spec["threshold_source"], cache)
        total = 0
        for seed in _source_seeds(spec, cache):
            path = spec["path_pattern"].format(seed=seed)
            rows = _pointer(_data(cache, path), spec["pointer"])
            for row in rows:
                value = _pointer(row, spec["item_pointer"])
                relation = spec["relation"]
                if relation == "lt":
                    match = value < threshold
                elif relation == "ge":
                    match = value >= threshold
                else:
                    raise ValueError(f"Unsupported relation: {relation}")
                total += int(match)
        return total
    if kind == "object_child_map":
        root = _pointer(_data(cache, spec["path"]), spec["pointer"])
        if not isinstance(root, Mapping):
            raise TypeError("object_child_map root must be a mapping.")
        result: dict[str, Any] = {}
        for key in sorted(root):
            try:
                result[str(key)] = _pointer(root[key], spec["relative_pointer"])
            except (KeyError, IndexError):
                if not spec.get("skip_missing", False):
                    raise
        return result
    if kind == "filtered_group_sum":
        rows = _pointer(_data(cache, spec["path"]), spec["pointer"])
        grouped: dict[str, Any] = {}
        for row in rows:
            if any(row.get(key) != expected for key, expected in spec["filters"].items()):
                continue
            group = str(row[spec["group_by"]])
            grouped[group] = grouped.get(group, 0) + row[spec["field"]]
        return dict(sorted(grouped.items()))
    raise ValueError(f"Unsupported selector type: {kind}")


def _contains_numeric_literal(value: Any) -> bool:
    if isinstance(value, bool):
        return False
    if isinstance(value, (int, float)):
        return True
    if isinstance(value, Mapping):
        return any(_contains_numeric_literal(item) for item in value.values())
    if isinstance(value, list):
        return any(_contains_numeric_literal(item) for item in value)
    return False


def _evidence_paths(value: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(value, Mapping):
        for key, item in value.items():
            if key in {"path", "path_pattern"} and isinstance(item, str):
                found.add(item)
            else:
                found.update(_evidence_paths(item))
    elif isinstance(value, list):
        for item in value:
            found.update(_evidence_paths(item))
    return found


def _git_bytes(*args: str) -> bytes:
    return subprocess.run(
        ["git", *args],
        cwd=PROJECT_ROOT,
        capture_output=True,
        check=True,
    ).stdout


def _git_tree_blob(commit: str, path: str) -> str:
    return _git_bytes("rev-parse", f"{commit}:{path}").decode("ascii").strip()


def _assert_append_only_ledger(
    frozen: bytes, published_snapshot: bytes, observed_head: bytes
) -> None:
    """Preserve both claim-era bytes and the entire pre-correction ledger history."""
    if not frozen or not published_snapshot or not observed_head:
        raise ValueError("Ledger source or preservation witness is empty.")
    if not published_snapshot.startswith(frozen):
        raise ValueError("Pre-correction ledger does not preserve the frozen claim source.")
    if not observed_head.startswith(published_snapshot):
        raise ValueError("HEAD ledger rewrites or truncates preserved historical entries.")


def _validate_claim_source_identities(contract: Mapping[str, Any]) -> dict[str, str]:
    policy = _load_json(SOURCE_COMPATIBILITY_PATH)
    if policy != _PINNED_SOURCE_COMPATIBILITY:
        raise ValueError("Unrecognized Stage-9.5-7 v1.1 compatibility policy.")

    # The original frozen v1 contract and claim definitions must remain byte-identical.
    for key in ("frozen_claim_contract", "frozen_claim_definitions"):
        item = policy[key]
        observed = _git_tree_blob("HEAD", item["path"])
        if observed != item["blob_sha"]:
            raise ValueError(
                f"Original claim freeze changed at {item['path']}: "
                f"{observed} != {item['blob_sha']}"
            )

    frozen = {item["path"]: item["blob_sha"] for item in contract["claim_source_freeze"]}
    ledger = policy["ledger"]
    ledger_path = ledger["path"]
    if len(frozen) != 4 or ledger_path not in frozen:
        raise ValueError("Expected exactly four original frozen claim sources.")
    if frozen[ledger_path] != ledger["claim_source_blob_sha"]:
        raise ValueError("Original frozen methodology-ledger blob was substituted.")

    # Git blob checks alone do not detect uncommitted edits to worktree inputs.
    # Reject changed frozen contracts, definitions, or claim-source documents.
    tracked_sources = [
        policy["frozen_claim_contract"]["path"],
        policy["frozen_claim_definitions"]["path"],
        *frozen,
    ]
    try:
        _git_bytes("diff", "--quiet", "HEAD", "--", *tracked_sources)
    except subprocess.CalledProcessError as exc:
        raise ValueError("Frozen claim-source inputs differ from the checked HEAD.") from exc

    # The witness is bound to the actual published assurance commit, not a
    # substitute blob supplied after observing the failed workflow.
    _git_bytes(
        "merge-base", "--is-ancestor", ledger["pre_correction_commit"], "HEAD"
    )
    historical_sha = _git_tree_blob(
        ledger["claim_source_historical_commit"], ledger_path
    )
    snapshot_sha = _git_tree_blob(ledger["pre_correction_commit"], ledger_path)
    if historical_sha != ledger["claim_source_blob_sha"]:
        raise ValueError("Frozen ledger does not match its historical Git commit.")
    if snapshot_sha != ledger["pre_correction_snapshot_blob_sha"]:
        raise ValueError("Published pre-correction ledger witness is inconsistent.")

    # Do not allow the compatibility exception to spread to any other source.
    for path, expected in frozen.items():
        observed = _git_tree_blob("HEAD", path)
        if path != ledger_path:
            if observed != expected:
                raise ValueError(
                    f"Claim-source blob mismatch for {path}: {observed} != {expected}"
                )
            continue

        frozen_bytes = _git_bytes("cat-file", "blob", expected)
        snapshot_bytes = _git_bytes("cat-file", "blob", snapshot_sha)
        head_bytes = _git_bytes("cat-file", "blob", observed)
        _assert_append_only_ledger(frozen_bytes, snapshot_bytes, head_bytes)

    # The authoritative claim-source identity remains the original frozen blob.
    return frozen


def run(output_dir: Path) -> dict[str, Any]:
    contract = _load_json(CONTRACT_PATH)
    definitions = _load_json(DEFINITIONS_PATH)
    cache: dict[str, Any] = {}
    source_identities = _validate_claim_source_identities(contract)

    frozen_families = set(contract["claim_families"])
    claims = definitions["claims"]
    claim_ids = [item["claim_id"] for item in claims]
    if len(claim_ids) != len(set(claim_ids)):
        raise ValueError("Duplicate claim_id in claim definitions.")

    defined_families = {item["family"] for item in claims}
    missing_families = sorted(frozen_families - defined_families)
    extra_families = sorted(defined_families - frozen_families)
    if missing_families or extra_families:
        raise ValueError(f"Claim-family mismatch: missing={missing_families}, extra={extra_families}")

    rows: list[dict[str, Any]] = []
    identity_bank = contract["frozen_scientific_identities"]
    for claim in claims:
        if _contains_numeric_literal(claim["values"]):
            raise ValueError(f"Hand-entered numeric literal under values for {claim['claim_id']}.")
        resolved = {name: _resolve(spec, cache) for name, spec in claim["values"].items()}
        if not resolved:
            raise ValueError(f"Claim {claim['claim_id']} has no resolved evidence values.")
        identity_refs = claim["evidence_identity_refs"]
        identities = {name: identity_bank[name] for name in identity_refs}
        source_sha = source_identities[claim["source_interpretation_path"]]
        row = {
            "claim_id": claim["claim_id"],
            "family": claim["family"],
            "claim_text_template": claim["claim_text_template"],
            "claim_status": claim["claim_status"],
            "interpretation_status": claim["interpretation_status"],
            "source_interpretation_path": claim["source_interpretation_path"],
            "source_section": claim["source_section"],
            "source_blob_sha": source_sha,
            "immutable_evidence_path": sorted(_evidence_paths(claim["values"])),
            "evidence_selector": claim["values"],
            "resolved_values": resolved,
            "generating_code_path": claim["generating_code_path"],
            "verification_code_path": claim["verification_code_path"],
            "config_protocol_identity": claim["config_protocol_identity"],
            "evidence_commit_or_hash": identities,
            "display_transformation": claim["display_transformation"],
            "claim_boundary": claim["claim_boundary"],
        }
        rows.append(row)

    required = set(contract["stage9_5_7"]["required_fields"])
    missing_fields = {
        row["claim_id"]: sorted(required - set(row))
        for row in rows
        if required - set(row)
    }
    if missing_fields:
        raise ValueError(f"Required claim-ledger fields missing: {missing_fields}")

    report: dict[str, Any] = {
        "audit_id": "stage9.5-7-claim-to-evidence-traceability-v1_1",
        "contract": str(CONTRACT_PATH.relative_to(PROJECT_ROOT)),
        "definitions": str(DEFINITIONS_PATH.relative_to(PROJECT_ROOT)),
        "claim_source_compatibility_policy": str(SOURCE_COMPATIBILITY_PATH.relative_to(PROJECT_ROOT)),
        "ledger_frozen_source_blob_sha": source_identities["METHODOLOGY_LEDGER.md"],
        "ledger_preservation_witness_blob_sha": _PINNED_SOURCE_COMPATIBILITY["ledger"]["pre_correction_snapshot_blob_sha"],
        "claim_count": len(rows),
        "family_count": len(defined_families),
        "frozen_family_count": len(frozen_families),
        "missing_families": missing_families,
        "extra_families": extra_families,
        "orphan_current_claims": [],
        "hand_entered_numeric_evidence_literals": 0,
        "final_manuscript_gate": {
            "required": True,
            "policy": contract["stage9_5_7"]["orphan_policy"],
            "status": "pending_final_manuscript",
        },
        "claims": rows,
        "scientific_objects_modified": False,
        "stage10_outcomes_accessed": False,
    }
    report["pass"] = (
        not missing_families
        and not extra_families
        and not report["orphan_current_claims"]
        and report["hand_entered_numeric_evidence_literals"] == 0
    )
    report["status"] = "pass" if report["pass"] else "blocked"
    report["canonical_sha256"] = _canonical_sha256(
        {key: value for key, value in report.items() if key != "canonical_sha256"}
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "claim_ledger.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    lines = [
        "# Stage 9.5-7 Claim-to-Evidence Traceability",
        "",
        f"- status: **{report['status'].upper()}**",
        f"- claims: **{report['claim_count']}**",
        f"- frozen families covered: **{report['family_count']}/{report['frozen_family_count']}**",
        f"- orphan current claims: **{len(report['orphan_current_claims'])}**",
        f"- hand-entered numeric evidence literals: **{report['hand_entered_numeric_evidence_literals']}**",
        f"- report canonical SHA-256: `{report['canonical_sha256']}`",
        "",
        "The final-manuscript zero-orphan-number audit remains mandatory.",
    ]
    (output_dir / "CLAIM_TRACEABILITY_REPORT.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )
    if not report["pass"]:
        raise SystemExit("Stage 9.5-7 claim traceability blocked.")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Stage 9.5-7 claim-to-evidence ledger")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("artifacts/stage9_5_claims_v1"),
    )
    args = parser.parse_args()
    run(args.output_dir)


if __name__ == "__main__":
    main()
