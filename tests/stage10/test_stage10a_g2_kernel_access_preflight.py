"""Source-only Linux OS access matrix. Never touches CICIDS, models or treatment."""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile

import pytest
from tools.stage10 import stage10a_g2_kernel_access_preflight as g

UIDS = {"writer":32101,"label_custodian":32102,"checkpoint_custodian":32103,
        "phase_b":32104,"evaluator":32105}
OWNERS = {"labels":"label_custodian", "initial_checkpoints":"checkpoint_custodian",
          "live_phase_a":"writer", "evaluator_boundary":"evaluator"}


def make_policy(root: Path) -> dict:
    return {
        "schema": g.SCHEMA, "attempt_id": "nonsecret-access-probe-1",
        "expected_git_head": "a"*40,
        "role_ids": {k:{"uid":v,"gid":v} for k,v in UIDS.items()},
        "probe_roots": {r:str(root/r) for r in g.RESOURCES},
        "stage10a_treatment_execution_authorized":False,
    }


def write_policy(root: Path, doc: dict) -> Path:
    p=root/"controller-policy.json"
    p.write_text(json.dumps(doc,sort_keys=True,separators=(",", ":"))+"\n")
    return p


def configure_probe_roots(root: Path, doc: dict) -> None:
    os.chmod(root,0o755)  # role subprocesses must traverse this disposable parent
    for resource,path in doc["probe_roots"].items():
        d=Path(path); d.mkdir()
        f=d/g.PROBE_FILE; f.write_text("nonsecret readiness marker\n")
        if resource == "sealed_phase_a":
            os.chown(d,0,UIDS["phase_b"]); os.chown(f,0,UIDS["phase_b"])
            os.chmod(d,0o750);os.chmod(f,0o640)
        else:
            v=UIDS[OWNERS[resource]]
            os.chown(d,v,v); os.chown(f,v,v)
            os.chmod(d,0o700);os.chmod(f,0o600)


def test_expected_matrix_does_not_consider_uid_separation_proof():
    assert set(g.EXPECTED)==set(g.ROLES)
    assert g.EXPECTED["phase_b"]["sealed_phase_a"]==(True,False)
    assert "labels" not in g.EXPECTED["writer"]
    assert "initial_checkpoints" not in g.EXPECTED["writer"]
    assert "evaluator_boundary" not in g.EXPECTED["writer"]


@pytest.mark.parametrize("alter", ["release_true","same_uid","same_gid","uid_root","bad_git","missing_role","missing_resource","extra_field","relative_root"])
def test_reject_malformed_policy_without_privileged_host(tmp_path, alter):
    p=make_policy(tmp_path)
    if alter=="release_true":p["stage10a_treatment_execution_authorized"]=True
    elif alter=="same_uid":p["role_ids"]["writer"]["uid"]=p["role_ids"]["label_custodian"]["uid"]
    elif alter=="same_gid":p["role_ids"]["writer"]["gid"]=p["role_ids"]["label_custodian"]["gid"]
    elif alter=="uid_root":p["role_ids"]["writer"]["uid"]=0
    elif alter=="bad_git":p["expected_git_head"]="a"*39
    elif alter=="missing_role":del p["role_ids"]["phase_b"]
    elif alter=="missing_resource":del p["probe_roots"]["labels"]
    elif alter=="extra_field":p["approved_for_real_treatment"]=True
    elif alter=="relative_root":p["probe_roots"]["labels"]="labels"
    with pytest.raises(ValueError):
        g.inspect_policy(p)


def test_missing_protected_resources_fail_closed(tmp_path):
    with pytest.raises(ValueError,match="non-symlink"):
        g.inspect_policy(make_policy(tmp_path))


def test_inherited_release_flags_always_false_in_return_source():
    src=Path(g.__file__).read_text()
    for forbidden in ("import torch","import pandas","torch.load(","read_csv(","subprocess.Popen("):
        assert forbidden not in src
    for key in ("g2_production_accepted", "stage10a_treatment_execution_authorized",
                "stage10a_release_ready", "production_label_custody_verified"):
        assert f'"{key}": False' in src


@pytest.mark.skipif(sys.platform!="linux" or os.geteuid()!=0 or not shutil.which("setpriv"),
                    reason="Requires separate privileged Linux host; do not simulate UID probes")
def test_actual_kernel_access_denial_and_fail_closed_on_permission_change():
    with tempfile.TemporaryDirectory(dir="/tmp",prefix="s10a-kernel-probe-") as raw:
        root=Path(raw);d=make_policy(root)
        configure_probe_roots(root,d)
        policy=write_policy(root,d)
        result=g.probe_host_policy(policy)
        assert result["kernel_access_matrix_verified_on_this_host"] is True
        assert result["nonsecret_probe_files_only"] is True
        assert result["g2_production_accepted"] is False
        assert result["stage10a_release_ready"] is False
        assert result["observations"]["writer"]["labels"]["read"]=="denied"
        assert result["observations"]["label_custodian"]["labels"]["read"]=="allowed"
        assert result["observations"]["phase_b"]["sealed_phase_a"]["read"]=="allowed"
        assert result["observations"]["phase_b"]["sealed_phase_a"]["write"]=="denied"
        # Wrong mode is a Class-A fail-closed preflight, even if tests might otherwise pass.
        os.chmod(policy,0o666)
        with pytest.raises(ValueError,match="root-controlled"):
            g.probe_host_policy(policy)
        os.chmod(policy,0o644)
        os.chmod(root/"labels",0o755)
        with pytest.raises(ValueError,match="ownership/mode"):
            g.probe_host_policy(policy)
        os.chmod(root/"labels",0o700)
        # Actual kernel denial failure with a permissive ACL to a writer would also fail.
        target=root/"labels"/g.PROBE_FILE
        os.chmod(target,0o644)
        with pytest.raises(ValueError,match="ownership/mode"):
            g.probe_host_policy(policy)
        os.chmod(target,0o600)
        symlink=root/"labels"/g.PROBE_FILE
        symlink.unlink();symlink.symlink_to("/etc/hosts")
        with pytest.raises(ValueError,match="redirected"):
            g.probe_host_policy(policy)
