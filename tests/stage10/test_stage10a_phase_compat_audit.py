"""Synthetic-only Stage-8 directory/manifest compatibility verifier tests."""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.stage10 import stage10a_phase_compat_audit as a


def j(value):
    return a.canonical(value) + b"\n"


def write_json(path, value):
    path.write_bytes(j(value))


def make_fixture(root, monkeypatch, rows=a.LATENCY+1):
    stage={"raw_source":{"sha256":"a"*64},
           "scenario":{"stream_row_ids_sha256":"b"*64},
           "inherited_identities":{"preprocessing_core_state_sha256":"c"*64}}
    ckpt={"checkpoint_files":[{"sha256":f"{i}"*64} for i in a.SEEDS]}
    monkeypatch.setattr(a,"_authority",lambda repo:(stage,{},ckpt))
    root.mkdir(exist_ok=True)
    phasea=root/"phase_a_shared_control_plane";phaseb=root/"phase_b_symbolic_arms"
    phasea.mkdir();phaseb.mkdir()
    allshared={}
    states={}
    for seed in a.SEEDS:
        aa=phasea/f"seed-{seed}";aa.mkdir()
        bb=phaseb/f"seed-{seed}";bb.mkdir()
        attempt={"run_id":f"{a.FIXTURE}-a-{seed}","seed":seed,"git_commit":"unverified-synthetic",
                 "synthetic_only":True,"primary_boundary_scored":False,"symbolic_arms_executed":False}
        write_json(aa/"attempt.json",attempt)
        identity={"source_sha256":stage["raw_source"]["sha256"],
                  "row_ids_sha256":stage["scenario"]["stream_row_ids_sha256"],
                  "preprocessing_sha256":stage["inherited_identities"]["preprocessing_core_state_sha256"],
                  "seed":seed,"fixture":a.FIXTURE,"real_input_loaded":False}
        write_json(aa/"input_identity.json",identity)
        preds=[a._expected_prediction(seed,i) for i in range(rows)]
        label=[{"row_id":f"fixture-s{seed}-row-{i}","origin_index":i,"maturity_index":i+a.LATENCY} for i in range(rows)]
        events=[]
        for i in range(rows):
            events.append({"event_type":"prediction","origin_index":i,"logical_clock":i,"prediction_committed":True})
            if i >= a.LATENCY:
                events.append({"event_type":"label_release","origin_index":i-a.LATENCY,"logical_clock":i,"maturity_index":i})
        checkpoint=[{"sequence":0,"parent_state_sha256":None,
                     "child_state_sha256":a._sha(f"{a.FIXTURE}|{seed}|fake-initial-state".encode()),
                     "checkpoint_file_sha256":ckpt["checkpoint_files"][seed]["sha256"],
                     "publication_effective_index":0,"synthetic_only":True}]
        data=dict(predictions=preds,label_schedule=label,detector_observations=[],events=events,replay_transactions=[],checkpoint_chain=checkpoint)
        for k,v in data.items():
            (aa/f"{k}.jsonl").write_bytes(b"".join(j(x) for x in v))
        sharedbase={"label_schedule_sha256":a._sha(a.canonical(label)),
                    "detector_events_sha256":a._sha(a.canonical([])),
                    "replay_evidence_sha256":a._sha(a.canonical([])),
                    "checkpoint_chain_sha256":a._sha(a.canonical(checkpoint))}
        shared={**sharedbase,"identity_sha256":a._sha(a.canonical(sharedbase))}
        allshared[str(seed)]=shared["identity_sha256"]
        write_json(aa/"shared_identity.json",{"seed":seed,"shared_identity":shared,"fixture":a.FIXTURE,
                    "real_neural_state_verified":False})
        desc={name:{"path":f"{name}.jsonl","sha256":a._sha((aa/f"{name}.jsonl").read_bytes())} for name in a.STREAMS}
        desc.update({k:{"path":f"{k}.json","sha256":a._sha((aa/f"{k}.json").read_bytes())}
                     for k in ("input_identity","shared_identity")})
        run={"schema_version":1,"run_id":f"{a.FIXTURE}-a-{seed}","seed":seed,
             "arm":"shared_control_plane","git_commit":"unverified-synthetic",
             "protocol_hashes":{},"runtime":{"fixture_only":True},
             "scenario_identity":{"synthetic_only":True,"adaptive_runner_received_boundary_metadata":False},
             "initial_checkpoint_sha256":ckpt["checkpoint_files"][seed]["sha256"],
             "preprocessing_sha256":stage["inherited_identities"]["preprocessing_core_state_sha256"],
             "files":desc,"status":"synthetic_unscored_schema_projection"}
        write_json(aa/"run_manifest.json",{**run,"manifest_sha256":a._sha(a.canonical(run))})
        anames={p.name for p in aa.iterdir()}
        seal={"schema":a.SCHEMA,"seed":seed,"shared_identity_sha256":shared["identity_sha256"],
              "stage10a_source_receipt_sha256":a.SOURCE_RECEIPT_SHA256,
              "stage10a_checkpoint_receipt_sha256":a.CHECKPOINT_RECEIPT_SHA256,
              "phase_a_files":{k:a._sha((aa/k).read_bytes()) for k in sorted(anames)},
              "real_execution_authenticated":False,"stage10a_treatment_execution_authorized":False}
        write_json(aa/"stage10a_provenance_seal.json",seal)
        seal_sha=a._sha((aa/"stage10a_provenance_seal.json").read_bytes())
        bindings={}
        for arm in a.ARMS:
            arm_dir=bb/arm;arm_dir.mkdir()
            symbol={"fixture":a.FIXTURE,"seed":seed,"arm":arm,
                    "real_symbolic_lifecycle_executed":False,
                    "synthetic_symbolic_token_sha256":a._sha(f"{a.FIXTURE}|{seed}|{arm}".encode())}
            write_json(arm_dir/"symbolic_fixture.json",symbol)
            body={"schema_version":1,"seed":seed,"arm":arm,
                  "operator_config_sha256":a.OPERATOR_TOKEN,
                  "shared_identity_sha256":shared["identity_sha256"],
                  "phase_a_seal_sha256":seal_sha,"readonly_shared_writer":True,
                  "neural_writer_invocations":0,"synthetic_only":True,
                  "files":{"symbolic_fixture":{"path":"symbolic_fixture.json",
                  "sha256":a._sha((arm_dir/"symbolic_fixture.json").read_bytes())}}}
            arm_manifest={**body,"manifest_sha256":a._sha(a.canonical(body))}
            write_json(arm_dir/"arm_manifest.json",arm_manifest)
            bindings[arm]={"path":f"{arm}/arm_manifest.json",
                            "sha256":a._sha((arm_dir/"arm_manifest.json").read_bytes()),
                            "manifest_sha256":arm_manifest["manifest_sha256"]}
        states[seed]=(bb,shared["identity_sha256"],seal_sha,bindings)
    for seed,(bb,identity,sealsha,bindings) in states.items():
        body={"schema_version":1,"run_id":f"{a.FIXTURE}-b-{seed}","seed":seed,
              "git_commit":"unverified-synthetic","status":"synthetic_unscored_schema_projection",
              "shared_identity_sha256":identity,
              "all_phase_a_shared_identity_sha256":allshared,
              "operator_config_sha256":a.OPERATOR_TOKEN,
              "phase_a_seal_sha256":sealsha,"arms":bindings,"synthetic_only":True,
              "primary_boundary_scored":False}
        write_json(bb/"phase_b_manifest.json",{**body,"manifest_sha256":a._sha(a.canonical(body))})
    return root


@pytest.fixture
def fixture(tmp_path,monkeypatch):
    return make_fixture(tmp_path,monkeypatch)


def modify(path,field,value):
    body=json.loads(path.read_bytes())
    body[field]=value
    write_json(path,body)


def test_five_seed_three_arm_synthetic_schema_pass(fixture):
    v=a.verify_all(fixture)
    assert len(v["five_seed_phase_a_seal_sha256"])==5
    assert v["fixture_only_pass"] is True
    for k in ("git_runtime_authenticated","real_model_loaded_or_predicted",
              "real_phase_a_neural_trajectory_verified","real_phase_b_symbolic_treatments_verified",
              "stage10a_treatment_execution_authorized","stage10a_release_ready"):
        assert v[k] is False


@pytest.mark.parametrize("part",["predictions.jsonl","label_schedule.jsonl","events.jsonl",
                                 "detector_observations.jsonl","replay_transactions.jsonl",
                                 "checkpoint_chain.jsonl","shared_identity.json","run_manifest.json",
                                 "stage10a_provenance_seal.json"])
def test_tampered_phase_a_raw_evidence_fails_closed(fixture,part):
    p=fixture/"phase_a_shared_control_plane/seed-0"/part
    p.write_bytes(p.read_bytes()+b"tamper")
    with pytest.raises(ValueError):a.verify_all(fixture)


@pytest.mark.parametrize("part",["phase_b_manifest.json","c_frozen_symbolic/arm_manifest.json",
                                "d_drift/symbolic_fixture.json","d_periodic/arm_manifest.json"])
def test_arm_bindings_cannot_change(fixture,part):
    p=fixture/"phase_b_symbolic_arms/seed-1"/part
    p.write_bytes(p.read_bytes()+b"tamper")
    with pytest.raises(ValueError):a.verify_all(fixture)


def test_injecting_unexpected_file_rejected(fixture):
    (fixture/"phase_a_shared_control_plane/seed-2/real_checkpoint.pt").write_bytes(b"not a checkpoint")
    with pytest.raises(ValueError,match="inventory"):a.verify_all(fixture)


def test_missing_seed_fails_closed(fixture):
    import shutil
    shutil.rmtree(fixture/"phase_b_symbolic_arms/seed-4")
    with pytest.raises(ValueError,match="five frozen"):a.verify_all(fixture)


def test_unverified_git_or_release_promotion_rejected(fixture):
    f=fixture/"phase_a_shared_control_plane/seed-0/stage10a_provenance_seal.json"
    modify(f,"real_execution_authenticated",True)
    with pytest.raises(ValueError):a.verify_all(fixture)


def test_real_row_count_is_unreachable(fixture):
    with pytest.raises(ValueError,match="Production stream"):a.verify_all(fixture,rows=138530)


def test_no_model_or_network_dependencies():
    import inspect
    src=inspect.getsource(a)
    for prohibited in ("import torch","torch.load(","pickle.load(","urlopen(",
                       "requests.get(",".write_bytes(","pandas.read_csv("):
        assert prohibited not in src


def test_repository_frozen_receipts_and_execution_hold_still_match():
    """Not mocked: exact accepted upstream bytes are checked in GitHub CI."""
    stage, source, checkpoint = a._authority(a.ROOT)
    assert source["logical_rows"] == 138530
    assert source["label_latency_rows"] == a.LATENCY
    assert stage["scenario"]["boundary_role"] == "offline_evaluator_scoring_and_diagnostics_only"
    assert [x["seed"] for x in checkpoint["checkpoint_files"]] == list(a.SEEDS)
    assert checkpoint["no_model_loaded_or_predicted"] is True
