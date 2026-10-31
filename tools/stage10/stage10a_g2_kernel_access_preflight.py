"""Stage-10A Linux kernel access-denial preflight: protected nonsecret probes only.

Runs actual filesystem open(2) attempts under role-specific OS UIDs using
setpriv; never reads original CSV, actual labels, checkpoint bytes, or models.
A passing probe is local host-boundary evidence, NOT trusted key custody,
durable per-prediction commitment, an execution schema freeze, or RELEASE.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
from typing import Any

SCHEMA = "stage10a-g2-kernel-access-preflight-v1"
PROBE_FILE = ".stage10a_access_probe"
ROLES = ("writer", "label_custodian", "checkpoint_custodian", "phase_b", "evaluator")
RESOURCES = ("labels", "initial_checkpoints", "live_phase_a", "sealed_phase_a", "evaluator_boundary")
HEX40 = re.compile(r"^[0-9a-f]{40}$")
# read/write means kernel OPEN capability only; the probe never changes contents.
EXPECTED = {
    "writer": {"live_phase_a": (True, True)},
    "label_custodian": {"labels": (True, True)},
    "checkpoint_custodian": {"initial_checkpoints": (True, True)},
    "phase_b": {"sealed_phase_a": (True, False)},
    "evaluator": {"evaluator_boundary": (True, True)},
}
# sealed_phase_a is controlled by root, group-readable only by the Phase-B role.
CHILD = r'''
import errno, json, os, sys
files=json.loads(sys.stdin.buffer.read())
result={}
for resource, path in files.items():
    state={}
    for kind, flag in (("read", os.O_RDONLY), ("write", os.O_WRONLY)):
        try:
            fd=os.open(path, flag | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK)
            os.close(fd)
            state[kind]="allowed"
        except OSError as exc:
            if exc.errno in (errno.EACCES, errno.EPERM):
                state[kind]="denied"
            else:
                state[kind]="unexpected_errno:"+str(exc.errno)
    result[resource]=state
sys.stdout.write(json.dumps({"uid":os.getuid(),"gid":os.getgid(),"observations":result},sort_keys=True))
'''


def _keys(value: Any, expected: set[str]) -> bool:
    return type(value) is dict and set(value) == expected


def _check_path(path: str) -> Path:
    if type(path) is not str or not path.startswith("/") or "\x00" in path:
        raise ValueError("Probe roots must be absolute Linux paths")
    p = Path(path)
    if p.is_symlink() or not p.is_dir() or p.resolve() != p:
        raise ValueError("Probe root must be an existing non-symlink directory")
    return p


def _read_policy(file: Path) -> dict[str, Any]:
    if file.is_symlink() or not file.is_file() or file.stat().st_size > 8192:
        raise ValueError("Missing, redirected or oversized controller policy")
    policy_stat = file.stat()
    parent_stat = file.parent.stat()
    if (policy_stat.st_uid != 0 or parent_stat.st_uid != 0
        or stat.S_IMODE(policy_stat.st_mode) & 0o022
        or stat.S_IMODE(parent_stat.st_mode) & 0o022):
        raise ValueError("Policy and its direct parent must be root-controlled, non-writable by roles")
    raw = file.read_bytes()
    doc = json.loads(raw)
    if type(doc) is not dict or raw != (json.dumps(doc, sort_keys=True, separators=(",", ":"),
                                                  allow_nan=False, ensure_ascii=False)+"\n").encode():
        raise ValueError("Controller policy must be strictly canonical JSON")
    if not _keys(doc, {"schema", "attempt_id", "expected_git_head", "role_ids", "probe_roots",
                       "stage10a_treatment_execution_authorized"}):
        raise ValueError("Controller policy fields differ")
    return doc


def inspect_policy(doc: dict[str, Any]) -> tuple[dict[str, tuple[int, int]], dict[str, Path]]:
    if (not _keys(doc, {"schema", "attempt_id", "expected_git_head", "role_ids", "probe_roots",
                        "stage10a_treatment_execution_authorized"})
        or doc["schema"] != SCHEMA or doc["stage10a_treatment_execution_authorized"] is not False
        or type(doc["attempt_id"]) is not str or not 1 <= len(doc["attempt_id"]) <= 128
        or type(doc["expected_git_head"]) is not str or not HEX40.fullmatch(doc["expected_git_head"])
        or not _keys(doc["role_ids"], set(ROLES))
        or not _keys(doc["probe_roots"], set(RESOURCES))):
        raise ValueError("Invalid or release-promoted kernel preflight policy")
    identities: dict[str, tuple[int, int]] = {}
    for role, item in doc["role_ids"].items():
        if (not _keys(item, {"uid", "gid"}) or type(item["uid"]) is not int
            or type(item["gid"]) is not int or not 1000 <= item["uid"] < 60000
            or not 1000 <= item["gid"] < 60000):
            raise ValueError("Role UID/GID must be dedicated nonroot Linux identities")
        identities[role] = (item["uid"], item["gid"])
    if (len({uid for uid, _ in identities.values()}) != len(ROLES)
        or len({gid for _, gid in identities.values()}) != len(ROLES)):
        raise ValueError("Role UIDs and GIDs must be distinct")
    roots = {name: _check_path(path) for name, path in doc["probe_roots"].items()}
    if len(set(roots.values())) != len(RESOURCES):
        raise ValueError("Policy must identify distinct protected roots")
    for resource, root in roots.items():
        f = root / PROBE_FILE
        if f.is_symlink() or not f.is_file() or f.stat().st_size > 128:
            raise ValueError("Missing, oversized or redirected nonsecret probe: "+resource)
        st_dir, st_file = root.stat(), f.stat()
        owner = ("label_custodian" if resource == "labels" else
                 "checkpoint_custodian" if resource == "initial_checkpoints" else
                 "writer" if resource == "live_phase_a" else
                 "evaluator" if resource == "evaluator_boundary" else None)
        if resource == "sealed_phase_a":
            if (st_dir.st_uid != 0 or st_file.st_uid != 0
                or st_dir.st_gid != identities["phase_b"][1]
                or st_file.st_gid != identities["phase_b"][1]
                or stat.S_IMODE(st_dir.st_mode) != 0o750
                or stat.S_IMODE(st_file.st_mode) != 0o640):
                raise ValueError("Sealed Phase-A fixture must be root-owned, Phase-B group-read-only")
        else:
            uid, gid = identities[owner]  # type: ignore[index]
            if (st_dir.st_uid != uid or st_file.st_uid != uid or st_dir.st_gid != gid
                or st_file.st_gid != gid or stat.S_IMODE(st_dir.st_mode) != 0o700
                or stat.S_IMODE(st_file.st_mode) != 0o600):
                raise ValueError("Host probe ownership/mode differs for "+resource)
    return identities, roots


def probe_host_policy(policy_file: Path, *, setpriv: str | None = None) -> dict[str, Any]:
    if sys.platform != "linux" or os.geteuid() != 0:
        raise ValueError("Trusted Linux host controller with effective UID 0 required")
    binary = setpriv or shutil.which("setpriv")
    if not binary or not Path(binary).is_absolute():
        raise ValueError("Explicit trusted setpriv binary required")
    policy = _read_policy(Path(policy_file))
    identities, roots = inspect_policy(policy)
    path_map = {k: str(p / PROBE_FILE) for k, p in roots.items()}
    observations: dict[str, Any] = {}
    for role in ROLES:
        uid, gid = identities[role]
        args = [binary, f"--reuid={uid}", f"--regid={gid}", "--clear-groups",
                "--inh-caps=-all", "--ambient-caps=-all", "--bounding-set=-all",
                sys.executable, "-I", "-c", CHILD]
        result = subprocess.run(args, input=json.dumps(path_map).encode(), capture_output=True,
                                cwd="/", env={"PATH":"/usr/bin:/bin", "PYTHONHASHSEED":"0"},
                                timeout=12, check=False)
        if result.returncode != 0 or len(result.stdout) > 4096:
            raise ValueError("Kernel probe child failed to execute for "+role)
        obs = json.loads(result.stdout)
        if not _keys(obs, {"uid", "gid", "observations"}) or (obs["uid"], obs["gid"]) != (uid,gid):
            raise ValueError("Kernel probe did not execute as the selected principal")
        if not _keys(obs["observations"], set(RESOURCES)):
            raise ValueError("Incomplete observed kernel access matrix")
        observations[role] = obs["observations"]
        for resource in RESOURCES:
            required = EXPECTED[role].get(resource, (False, False))
            got = obs["observations"][resource]
            if not _keys(got, {"read", "write"}):
                raise ValueError("Kernel result has unknown fields")
            for kind, expected in zip(("read", "write"), required):
                if got[kind] != ("allowed" if expected else "denied"):
                    raise ValueError(f"Kernel access policy violation: {role}/{resource}/{kind}={got[kind]}")
    raw = Path(policy_file).read_bytes()
    return {
        "schema": SCHEMA,
        "attempt_id": policy["attempt_id"],
        "subject_git_head": policy["expected_git_head"],
        "policy_sha256": hashlib.sha256(raw).hexdigest(),
        "kernel_access_matrix_verified_on_this_host": True,
        "resources_tested": list(RESOURCES),
        "role_ids_tested": {role: {"uid": identities[role][0], "gid": identities[role][1]}
                            for role in ROLES},
        "observations": observations,
        "nonsecret_probe_files_only": True,
        "production_label_custody_verified": False,
        "production_prediction_durability_verified": False,
        "trusted_runtime_attestation_accepted": False,
        "g1_method_approval_signed": False,
        "g2_production_accepted": False,
        "stage10a_treatment_execution_authorized": False,
        "stage10a_release_ready": False,
    }


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="G2 Linux nonsecret kernel access probes; never RELEASE")
    parser.add_argument("--policy", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(probe_host_policy(args.policy),sort_keys=True))


if __name__ == "__main__":
    main()
