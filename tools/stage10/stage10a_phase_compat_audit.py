"""Read-only, synthetic-only Stage-8-layout Stage-10A provenance schema audit.

No model imports, real-run entrypoint, acceptance of production evidence, or writes.
Stage-8 Phase-A/Phase-B directory and manifest shapes are reused only as a
prospective *synthetic projection*. Real schema/runtime witness remain HOLD.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "stage10a-phase-compat-synthetic-provenance-v1"
SEEDS = (0, 1, 2, 3, 4)
ARMS = ("c_frozen_symbolic", "d_drift", "d_periodic")
LATENCY = 5000
FIXTURE = "stage10a-phase-compat-fixture-only-v1"
STREAMS = ("predictions", "label_schedule", "detector_observations", "events", "replay_transactions", "checkpoint_chain")
MASTER_SHA1 = "8ac82c8d907243556a5673d09600cd1bdc19aa52"
STAGE_SHA1 = "001501350fbf9fa4a4075176b9af43c2cf275bc5"
SOURCE_RECEIPT_SHA256 = "d6e0874181b4aebe4d259b7f4f66b7d608aaf7803c6dc3c10f0151aaf2f9a42a"
CHECKPOINT_RECEIPT_SHA256 = "94cf6ee608e63be4834372aa0be8956eaaf289234f395dd788a9e0d23ba2b1c1"
OPERATOR_TOKEN = hashlib.sha256(b"stage10a-synthetic-nonoperator").hexdigest()


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False,
                      separators=(",", ":")).encode("utf-8")


def _json(root: Path, rel: str, *, lines: bool = False) -> Any:
    path = root / rel
    if path.is_symlink() or not path.is_file():
        raise ValueError("Missing, redirected or nonregular evidence")
    raw = path.read_bytes()
    if lines:
        if raw and not raw.endswith(b"\n"):
            raise ValueError("Unterminated source journal")
        try:
            records = [json.loads(line) for line in raw.splitlines()]
        except (ValueError, UnicodeError) as exc:
            raise ValueError("Malformed source journal") from exc
        if b"".join(canonical(r) + b"\n" for r in records) != raw:
            raise ValueError("Noncanonical source journal")
        return records
    try:
        val = json.loads(raw)
    except (ValueError, UnicodeError) as exc:
        raise ValueError("Malformed source manifest") from exc
    if type(val) is not dict or canonical(val) + b"\n" != raw:
        raise ValueError("Noncanonical source manifest")
    return val


def _authority(repo: Path) -> tuple[dict, dict, dict]:
    required = (
        ("data/manifests/stage10_plus_master_replication_sensitivity_v1_1.json", MASTER_SHA1, "blob"),
        ("data/manifests/stage10a_goldeneye_attack_pattern_v1.json", STAGE_SHA1, "blob"),
        ("results/audits/stage10a_original_source_receipt_601516ff_2026_10_31.json", SOURCE_RECEIPT_SHA256, "sha256"),
        ("results/audits/stage10a_original_checkpoint_source_only_receipt_41156553037.json", CHECKPOINT_RECEIPT_SHA256, "sha256"),
    )
    decoded: list[dict] = []
    for rel, expected, kind in required:
        raw = (repo / rel).read_bytes()
        got = (_sha(raw) if kind == "sha256" else hashlib.sha1(
            b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest())
        if got != expected:
            raise ValueError("Frozen authority/accepted receipt altered")
        decoded.append(json.loads(raw))
    master, stage, source, ckpt = decoded
    if (master["hard_gate"]["stage10_execution_permitted"] is not False or
        master["stage10_treatment_outcomes_accessed"] is not False or
        stage["stage10_treatment_execution_authorized"] is not False or
        stage["stage10_treatment_outcomes_accessed_during_freeze"] is not False or
        source["pass"] is not True or ckpt["pass"] is not True or
        source["raw_source_sha256"] != stage["raw_source"]["sha256"] or
        ckpt["source_receipt_canonical_sha256"] != source["canonical_sha256"] or
        ckpt["no_model_loaded_or_predicted"] is not True or
        [c["seed"] for c in ckpt["checkpoint_files"]] != list(SEEDS)):
        raise ValueError("Unaccepted source/checkpoint identity or treatment HOLD")
    return stage, source, ckpt


def _expected_prediction(seed: int, index: int) -> dict:
    return {"origin_index": index, "row_id": f"fixture-s{seed}-row-{index}",
            "logical_clock": index, "maturity_index": index + LATENCY,
            "synthetic_neural_token_sha256": _sha(f"{FIXTURE}|{seed}|{index}".encode())}


def _expect_exact(actual: Any, expected: Any, where: str) -> None:
    if actual != expected:
        raise ValueError(f"Invalid synthetic Phase-A/Phase-B provenance: {where}")


def verify_seed(root: Path, seed: int, *, rows: int, stage: dict, ckpt: dict,
                all_shared: dict[str, str]) -> str:
    if type(seed) is not int or seed not in SEEDS or type(rows) is not int or rows not in (LATENCY+1, LATENCY+2):
        raise ValueError("Only bounded synthetic fixtures, never real prediction data")
    aa = root / "phase_a_shared_control_plane" / f"seed-{seed}"
    bb = root / "phase_b_symbolic_arms" / f"seed-{seed}"
    if any(p.is_symlink() or not p.is_dir() for p in (aa, bb)):
        raise ValueError("Phase-A/Phase-B directories absent or redirected")
    a_names = {"attempt.json", "input_identity.json", "shared_identity.json", "run_manifest.json", "stage10a_provenance_seal.json"} | {f"{s}.jsonl" for s in STREAMS}
    if {p.name for p in aa.iterdir()} != a_names:
        raise ValueError("Incomplete or unexpected Phase-A artifact inventory")
    if {p.name for p in bb.iterdir()} != {"phase_b_manifest.json"} | set(ARMS):
        raise ValueError("Incomplete or unexpected Phase-B artifact inventory")
    attempt = _json(aa, "attempt.json")
    _expect_exact(attempt, {"run_id": f"{FIXTURE}-a-{seed}", "seed": seed,
                            "git_commit": "unverified-synthetic", "synthetic_only": True,
                            "primary_boundary_scored": False, "symbolic_arms_executed": False}, "attempt")
    input_identity = _json(aa, "input_identity.json")
    _expect_exact(input_identity, {"source_sha256": stage["raw_source"]["sha256"],
        "row_ids_sha256": stage["scenario"]["stream_row_ids_sha256"],
        "preprocessing_sha256": stage["inherited_identities"]["preprocessing_core_state_sha256"],
        "seed": seed, "fixture": FIXTURE, "real_input_loaded": False}, "input_identity")
    data = {name: _json(aa, f"{name}.jsonl", lines=True) for name in STREAMS}
    preds, schedule, detectors, events, replays, checkpoints = (data[name] for name in STREAMS)
    _expect_exact(preds, [_expected_prediction(seed,i) for i in range(rows)], "predictions")
    _expect_exact(schedule, [{"row_id": f"fixture-s{seed}-row-{i}",
                               "origin_index":i,"maturity_index":i+LATENCY}
                              for i in range(rows)], "label_schedule")
    _expect_exact(detectors, [], "detector_observations")
    _expect_exact(replays, [], "replay_transactions")
    target_events = []
    for i in range(rows):
        target_events.append({"event_type":"prediction","origin_index":i,
                              "logical_clock":i,"prediction_committed":True})
        if i >= LATENCY:
            target_events.append({"event_type":"label_release","origin_index":i-LATENCY,
                                  "logical_clock":i,"maturity_index":i})
    _expect_exact(events, target_events, "prediction-before-mature-label events")
    _expect_exact(checkpoints, [{"sequence":0,"parent_state_sha256":None,
        "child_state_sha256":_sha(f"{FIXTURE}|{seed}|fake-initial-state".encode()),
        "checkpoint_file_sha256":ckpt["checkpoint_files"][seed]["sha256"],
        "publication_effective_index":0,"synthetic_only":True}], "synthetic checkpoint chain")
    identity_base = {"label_schedule_sha256":_sha(canonical(schedule)),
                     "detector_events_sha256":_sha(canonical(detectors)),
                     "replay_evidence_sha256":_sha(canonical(replays)),
                     "checkpoint_chain_sha256":_sha(canonical(checkpoints))}
    identity = {**identity_base, "identity_sha256":_sha(canonical(identity_base))}
    _expect_exact(_json(aa, "shared_identity.json"),
                 {"seed":seed,"shared_identity":identity,"fixture":FIXTURE,
                  "real_neural_state_verified":False},"shared_identity")
    if all_shared[str(seed)] != identity["identity_sha256"]:
        raise ValueError("Cross-seed Phase-A identity map mismatch")
    desc = {name: {"path":f"{name}.jsonl", "sha256":_sha((aa/f"{name}.jsonl").read_bytes())}
            for name in STREAMS}
    desc.update({name: {"path":f"{name}.json", "sha256":_sha((aa/f"{name}.json").read_bytes())}
                 for name in ("input_identity","shared_identity")})
    run = {"schema_version":1,"run_id":f"{FIXTURE}-a-{seed}","seed":seed,
           "arm":"shared_control_plane","git_commit":"unverified-synthetic",
           "protocol_hashes":{},"runtime":{"fixture_only":True},
           "scenario_identity":{"synthetic_only":True,"adaptive_runner_received_boundary_metadata":False},
           "initial_checkpoint_sha256":ckpt["checkpoint_files"][seed]["sha256"],
           "preprocessing_sha256":stage["inherited_identities"]["preprocessing_core_state_sha256"],
           "files":desc,"status":"synthetic_unscored_schema_projection"}
    _expect_exact(_json(aa, "run_manifest.json"),
                 {**run,"manifest_sha256":_sha(canonical(run))}, "Phase-A run manifest")
    seal = {"schema":SCHEMA,"seed":seed,"shared_identity_sha256":identity["identity_sha256"],
            "stage10a_source_receipt_sha256":SOURCE_RECEIPT_SHA256,
            "stage10a_checkpoint_receipt_sha256":CHECKPOINT_RECEIPT_SHA256,
            "phase_a_files":{name:_sha((aa/name).read_bytes()) for name in sorted(a_names-{"stage10a_provenance_seal.json"})},
            "real_execution_authenticated":False,"stage10a_treatment_execution_authorized":False}
    _expect_exact(_json(aa,"stage10a_provenance_seal.json"),seal,"Phase-A seal")
    seal_sha=_sha((aa/"stage10a_provenance_seal.json").read_bytes())
    bindings={}
    for arm in ARMS:
        arm_dir=bb/arm
        if arm_dir.is_symlink() or not arm_dir.is_dir() or {p.name for p in arm_dir.iterdir()} != {"arm_manifest.json","symbolic_fixture.json"}:
            raise ValueError("Symbolic arm artifact inventory invalid")
        symbol={"fixture":FIXTURE,"seed":seed,"arm":arm,"real_symbolic_lifecycle_executed":False,
                "synthetic_symbolic_token_sha256":_sha(f"{FIXTURE}|{seed}|{arm}".encode())}
        _expect_exact(_json(arm_dir,"symbolic_fixture.json"),symbol,"symbolic fixture")
        arm_body={"schema_version":1,"seed":seed,"arm":arm,"operator_config_sha256":OPERATOR_TOKEN,
             "shared_identity_sha256":identity["identity_sha256"],
             "phase_a_seal_sha256":seal_sha,"readonly_shared_writer":True,
             "neural_writer_invocations":0,"synthetic_only":True,
             "files":{"symbolic_fixture":{"path":"symbolic_fixture.json","sha256":_sha((arm_dir/"symbolic_fixture.json").read_bytes())}}}
        arm_doc={**arm_body,"manifest_sha256":_sha(canonical(arm_body))}
        _expect_exact(_json(arm_dir,"arm_manifest.json"),arm_doc,"arm manifest")
        bindings[arm]={"path":f"{arm}/arm_manifest.json",
                       "sha256":_sha((arm_dir/"arm_manifest.json").read_bytes()),
                       "manifest_sha256":arm_doc["manifest_sha256"]}
    phase_b={"schema_version":1,"run_id":f"{FIXTURE}-b-{seed}","seed":seed,
             "git_commit":"unverified-synthetic","status":"synthetic_unscored_schema_projection",
             "shared_identity_sha256":identity["identity_sha256"],
             "all_phase_a_shared_identity_sha256":all_shared,
             "operator_config_sha256":OPERATOR_TOKEN,
             "phase_a_seal_sha256":seal_sha,"arms":bindings,"synthetic_only":True,
             "primary_boundary_scored":False}
    _expect_exact(_json(bb,"phase_b_manifest.json"),
                  {**phase_b,"manifest_sha256":_sha(canonical(phase_b))},"Phase-B manifest")
    return seal_sha


def verify_all(root: Path, *, rows: int = LATENCY + 1, repo: Path = ROOT) -> dict[str, Any]:
    """Five seed synthetic projection only; production mode intentionally absent."""
    if type(rows) is not int or rows not in (LATENCY+1, LATENCY+2):
        raise ValueError("Production stream cannot be accepted by synthetic verifier")
    stage, _, ckpt = _authority(Path(repo))
    root=Path(root)
    if root.is_symlink() or not root.is_dir() or {p.name for p in root.iterdir()} != {"phase_a_shared_control_plane","phase_b_symbolic_arms"}:
        raise ValueError("Unexpected Phase-A/Phase-B root")
    a,b=(root/name for name in ("phase_a_shared_control_plane","phase_b_symbolic_arms"))
    if any(p.is_symlink() or not p.is_dir() or {x.name for x in p.iterdir()} != {f"seed-{i}" for i in SEEDS} for p in (a,b)):
        raise ValueError("Exactly five frozen seed directories required in each phase")
    map_sha = {}
    for seed in SEEDS:
        shared=_json(a/f"seed-{seed}","shared_identity.json")
        map_sha[str(seed)] = shared.get("shared_identity",{}).get("identity_sha256")
    results={str(seed): verify_seed(root,seed,rows=rows,stage=stage,ckpt=ckpt,all_shared=map_sha) for seed in SEEDS}
    if len(set(results.values())) != len(SEEDS):
        raise ValueError("Shared writer seed seals are not distinct")
    return {"schema":SCHEMA,"fixture_only_pass":True,"source_only_receipts_pinned":True,
            "five_seed_phase_a_seal_sha256":results,"three_readonly_arms_per_seed":True,
            "git_runtime_authenticated":False,"real_model_loaded_or_predicted":False,
            "real_phase_a_neural_trajectory_verified":False,
            "real_phase_b_symbolic_treatments_verified":False,
            "stage10a_treatment_execution_authorized":False,"stage10a_release_ready":False,
            "status":"HOLD_SYNTHETIC_STAGE8_LAYOUT_ONLY"}
