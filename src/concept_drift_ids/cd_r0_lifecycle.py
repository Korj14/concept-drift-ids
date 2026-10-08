from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from concept_drift_ids.cd_symbolic_lifecycle import (
    RuleBaseState,
    migrate_r0_v2_rules,
)
from concept_drift_ids.scenario_manifest import sha256_file
from concept_drift_ids.symbolic import (
    Condition,
    Rule,
    canonical_json_hash,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
R0_V2_MANIFEST_PATH = PROJECT_ROOT / "data" / "manifests" / "system_b_v2.json"
ACCEPTED_R0_V2_MANIFEST_SHA256 = (
    "131027d2f136494eb388183f18dcb7eb0e9d7e9fe786f22dba25f4e1624c1483"
)
EXPECTED_ACTIVE_COUNTS = {0: 7, 1: 6, 2: 7, 3: 6, 4: 6}


def _condition(payload: dict[str, Any]) -> Condition:
    return Condition(
        feature=str(payload["feature"]),
        operator=str(payload["operator"]),
        threshold=float(payload["threshold"]),
        raw_threshold=(
            float(payload["raw_threshold"])
            if payload.get("raw_threshold") is not None
            else None
        ),
    )


def _rule(payload: dict[str, Any]) -> Rule:
    return Rule(
        rule_id=str(payload["rule_id"]),
        lineage_id=str(payload["lineage_id"]),
        rule_base_version=str(payload["rule_base_version"]),
        seed=int(payload["seed"]),
        conditions=tuple(_condition(item) for item in payload["antecedent"]),
        consequent=int(payload["consequent"]),
        confidence=float(payload["confidence"]),
        support=float(payload["support"]),
        covered_count=int(payload["covered_count"]),
        class_precision=float(payload["class_precision"]),
        neural_fidelity=float(payload["neural_fidelity"]),
        stability=float(payload["stability"]),
        complexity=int(payload["complexity"]),
        lifecycle_state=str(payload["lifecycle_state"]),
        source_candidate_id=str(payload["source_candidate_id"]),
        validation_evidence_id=str(payload["validation_evidence_id"]),
        relations=tuple(payload.get("relations", ())),
    )


def load_accepted_r0_v2_manifest(
    *,
    project_root: Path = PROJECT_ROOT,
) -> dict[str, Any]:
    path = project_root / "data" / "manifests" / "system_b_v2.json"
    if not path.is_file():
        raise FileNotFoundError(f"Missing accepted R0.v2 manifest: {path}")
    manifest = json.loads(path.read_text(encoding="utf-8"))
    stored = manifest.get("manifest_sha256")
    core = dict(manifest)
    core.pop("manifest_sha256", None)
    if canonical_json_hash(core) != stored:
        raise ValueError("R0.v2 manifest canonical hash mismatch.")
    if stored != ACCEPTED_R0_V2_MANIFEST_SHA256:
        raise ValueError("R0.v2 manifest is not the accepted frozen identity.")
    return manifest


def load_accepted_r0_v2_rules(
    seed: int,
    *,
    project_root: Path = PROJECT_ROOT,
) -> tuple[Rule, ...]:
    if seed not in EXPECTED_ACTIVE_COUNTS:
        raise ValueError(f"Unsupported accepted R0.v2 seed: {seed}")
    manifest = load_accepted_r0_v2_manifest(project_root=project_root)
    entry = manifest["rule_artifacts"][str(seed)]
    path = project_root / str(entry["path"])
    if not path.is_file():
        raise FileNotFoundError(f"Missing accepted R0.v2 rule artifact: {path}")
    actual_file_hash = sha256_file(path)
    if actual_file_hash != entry["sha256"]:
        raise ValueError("R0.v2 raw rule artifact hash mismatch.")

    payload = json.loads(path.read_text(encoding="utf-8"))
    stored_artifact_hash = payload.get("artifact_sha256")
    core = dict(payload)
    core.pop("artifact_sha256", None)
    if canonical_json_hash(core) != stored_artifact_hash:
        raise ValueError("R0.v2 canonical rule artifact hash mismatch.")
    if stored_artifact_hash != entry["artifact_sha256"]:
        raise ValueError("R0.v2 rule artifact identity mismatch.")

    rules = tuple(_rule(item) for item in payload["rules"])
    if len(rules) != EXPECTED_ACTIVE_COUNTS[seed]:
        raise ValueError("Unexpected accepted R0.v2 active rule count.")
    if any(rule.seed != seed for rule in rules):
        raise ValueError("R0.v2 rule artifact contains the wrong seed.")
    if any(rule.lifecycle_state != "active" for rule in rules):
        raise ValueError("Accepted R0.v2 artifact contains a non-active rule.")
    return rules


def migrate_accepted_r0_v2_state(
    seed: int,
    *,
    neural_checkpoint_sha256: str,
    project_root: Path = PROJECT_ROOT,
) -> RuleBaseState:
    rules = load_accepted_r0_v2_rules(seed, project_root=project_root)
    return migrate_r0_v2_rules(
        seed=seed,
        rules=rules,
        neural_checkpoint_sha256=neural_checkpoint_sha256,
        valid_from=0,
    )
