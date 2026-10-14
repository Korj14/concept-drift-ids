from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import subprocess
from pathlib import Path
from typing import Any, Mapping

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = PROJECT_ROOT / "data" / "manifests" / "stage9_5_claim_reporting_v1.json"
DEFINITIONS_PATH = PROJECT_ROOT / "data" / "manifests" / "stage9_5_claim_definitions_v1.json"


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
        result: dict[str, Any] = {}
        for row in rows:
            if any(row.get(key) != expected for key, expected in spec["filters"].items()):
                continue
            group = str(row[spec["group_by"]])
            result[group] = result.get(group, 0) + row[spec["field"]]
        return dict(sorted(result.items()))
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


def _claim_source_sha(contract: Mapping[str, Any], path: str) -> str:
    frozen = {item["path"]: item["blob_sha"] for item in contract["claim_source_freeze"]}
    expected = frozen[path]
    observed = subprocess.run(
        ["git", "hash-object", path],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=True,
    ).stdout.strip()
    if observed != expected:
        raise ValueError(f"Claim-source blob mismatch for {path}: {observed} != {expected}")
    return observed


def run(output_dir: Path) -> dict[str, Any]:
    contract = _load_json(CONTRACT_PATH)
    definitions = _load_json(DEFINITIONS_PATH)
    cache: dict[str, Any] = {}

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
        source_sha = _claim_source_sha(contract, claim["source_interpretation_path"])
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
        "audit_id": "stage9.5-7-claim-to-evidence-traceability-v1",
        "contract": str(CONTRACT_PATH.relative_to(PROJECT_ROOT)),
        "definitions": str(DEFINITIONS_PATH.relative_to(PROJECT_ROOT)),
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
