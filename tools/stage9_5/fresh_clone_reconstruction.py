from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from importlib import metadata
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
IDENTITY_PATH = PROJECT_ROOT / "data" / "manifests" / "stage9_5_fresh_clone_reconstruction_v1_2.json"


def _canonical_json_hash(payload: object) -> str:
    data = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _normalized_text_sha256(path: Path) -> str:
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        text = raw.decode("utf-8-sig")
    elif raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        text = raw.decode("utf-16")
    else:
        text = raw.decode("utf-8")
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _check(report: dict[str, Any], name: str, passed: bool, detail: Any) -> None:
    report["checks"].append({"name": name, "passed": bool(passed), "detail": detail})
    if not passed:
        report["failures"].append(name)


def _verify_manifest_hash(
    report: dict[str, Any],
    *,
    name: str,
    path: Path,
    hash_field: str,
    expected: str,
) -> dict[str, Any]:
    payload = _load_json(path)
    stored_payload = payload.pop("payload_sha256", None)
    payload_hash_ok = (
        stored_payload is None or stored_payload == _canonical_json_hash(payload)
    )
    stored = payload.get(hash_field)
    core = dict(payload)
    core.pop(hash_field, None)
    actual = _canonical_json_hash(core)
    _check(
        report,
        name,
        payload_hash_ok and stored == expected and actual == expected,
        {
            "path": str(path.relative_to(PROJECT_ROOT)),
            "writer_payload_sha256": stored_payload,
            "writer_payload_hash_ok": payload_hash_ok,
            "stored": stored,
            "actual": actual,
            "expected": expected,
        },
    )
    return payload


def _locked_distributions(lock_path: Path) -> dict[str, str]:
    raw = lock_path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        text = raw.decode("utf-8-sig")
    elif raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        text = raw.decode("utf-16")
    else:
        text = raw.decode("utf-8")
    expected: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "==" not in line:
            raise ValueError(f"non-exact lock entry: {line}")
        name, version = [item.strip() for item in line.split("==", 1)]
        expected[name] = version
    actual: dict[str, str] = {}
    for name, expected_version in expected.items():
        actual_version = metadata.version(name)
        if actual_version != expected_version:
            raise RuntimeError(f"{name}={actual_version} expected={expected_version}")
        actual[name] = actual_version
    return dict(sorted(actual.items()))


def _collect_path_hash_entries(node: Any) -> list[dict[str, str]]:
    found: list[dict[str, str]] = []
    if isinstance(node, dict):
        if isinstance(node.get("path"), str) and isinstance(node.get("sha256"), str):
            found.append({"path": node["path"], "sha256": node["sha256"]})
        for value in node.values():
            found.extend(_collect_path_hash_entries(value))
    elif isinstance(node, list):
        for value in node:
            found.extend(_collect_path_hash_entries(value))
    return found



def _stage8_archive_requirements(
    cfg: dict[str, Any],
) -> list[dict[str, str]]:
    root = PROJECT_ROOT / str(cfg["root"])
    requirements: dict[str, dict[str, str]] = {}

    def add(
        relative: Path,
        descriptor: dict[str, Any],
        source: str,
    ) -> None:
        path = relative.as_posix()
        sha256 = str(descriptor["sha256"])
        existing = requirements.get(path)
        if existing is not None and existing["sha256"] != sha256:
            raise ValueError(
                f"Conflicting accepted Stage-8 archive hash for {path}."
            )
        requirements[path] = {
            "path": path,
            "sha256": sha256,
            "source": source,
        }

    for seed in range(5):
        phase_a_relative = (
            Path("phase_a_shared_control_plane") / f"seed-{seed}"
        )
        phase_a = _load_json(root / phase_a_relative / "run_manifest.json")
        for name, descriptor in phase_a.get("files", {}).items():
            add(
                phase_a_relative / str(descriptor["path"]),
                descriptor,
                f"phase_a:{seed}:{name}",
            )

        phase_b_relative = (
            Path("phase_b_symbolic_arms") / f"seed-{seed}"
        )
        phase_b = _load_json(root / phase_b_relative / "phase_b_manifest.json")
        for arm, arm_descriptor in phase_b.get("arms", {}).items():
            arm_manifest_relative = Path(str(arm_descriptor["path"]))
            arm_manifest = _load_json(
                root / phase_b_relative / arm_manifest_relative
            )
            arm_directory = arm_manifest_relative.parent
            for name, descriptor in arm_manifest.get("files", {}).items():
                add(
                    phase_b_relative
                    / arm_directory
                    / str(descriptor["path"]),
                    descriptor,
                    f"phase_b:{seed}:{arm}:{name}",
                )

        phase_c_relative = (
            Path("phase_c_offline_evaluation_v1_1") / f"seed-{seed}"
        )
        phase_c_dir = root / phase_c_relative
        for evaluation_path in sorted(
            phase_c_dir.glob("*_evaluation.json")
        ):
            evaluation = _load_json(evaluation_path)
            descriptor = evaluation.get("prediction_trace")
            if not isinstance(descriptor, dict):
                raise TypeError(
                    f"Missing prediction-trace descriptor: {evaluation_path}"
                )
            if not isinstance(descriptor.get("path"), str):
                raise TypeError(
                    f"Invalid prediction-trace path: {evaluation_path}"
                )
            if not isinstance(descriptor.get("sha256"), str):
                raise TypeError(
                    f"Invalid prediction-trace hash: {evaluation_path}"
                )
            add(
                phase_c_relative / descriptor["path"],
                descriptor,
                f"phase_c:{seed}:{evaluation_path.name}",
            )

    return sorted(requirements.values(), key=lambda item: item["path"])


def _verify_stage8_large_archive(
    report: dict[str, Any],
    stage8_cfg: dict[str, Any],
    archive_cfg: dict[str, Any],
    archive_root: Path | None,
) -> None:
    requirements = _stage8_archive_requirements(stage8_cfg)
    root = (
        Path(archive_root)
        if archive_root is not None
        else PROJECT_ROOT / str(archive_cfg["default_external_root"])
    )
    detail: dict[str, Any] = {
        "required": True,
        "root": str(root),
        "requirement_count": len(requirements),
        "verified_count": 0,
        "missing": [],
        "mismatches": [],
        "retrieval": archive_cfg["retrieval"],
    }
    report["external_artifacts"]["stage8_large_artifact_archive"] = detail

    if not root.is_dir():
        report["blockers"].append("stage8_large_artifact_archive_missing")
        return

    missing: list[dict[str, str]] = []
    mismatches: list[dict[str, str]] = []
    verified = 0
    for item in requirements:
        path = root / item["path"]
        if not path.is_file():
            missing.append(
                {
                    "path": item["path"],
                    "source": item["source"],
                }
            )
            continue
        actual = _sha256_file(path)
        if actual != item["sha256"]:
            mismatches.append(
                {
                    "path": item["path"],
                    "expected": item["sha256"],
                    "actual": actual,
                    "source": item["source"],
                }
            )
            continue
        verified += 1

    detail["verified_count"] = verified
    detail["missing"] = missing
    detail["mismatches"] = mismatches
    if missing or mismatches:
        report["failures"].append(
            "stage8_large_artifact_archive_incomplete_or_mismatched"
        )

def _verify_stage8_compact(report: dict[str, Any], cfg: dict[str, Any]) -> None:
    root = PROJECT_ROOT / cfg["root"]
    manifest_path = PROJECT_ROOT / cfg["manifest_path"]
    manifest = _verify_manifest_hash(
        report,
        name="stage8_compact_manifest_identity",
        path=manifest_path,
        hash_field="manifest_sha256",
        expected=cfg["manifest_sha256"],
    )
    files = manifest.get("files")
    if not isinstance(files, list):
        _check(report, "stage8_compact_file_inventory_type", False, type(files).__name__)
        return
    mismatches: list[dict[str, str]] = []
    for entry in files:
        path = PROJECT_ROOT / str(entry["export_path"])
        expected = str(entry["sha256"])
        if not path.is_file():
            mismatches.append({"path": str(path.relative_to(PROJECT_ROOT)), "issue": "missing"})
            continue
        actual = _sha256_file(path)
        if actual != expected:
            mismatches.append({"path": str(path.relative_to(PROJECT_ROOT)), "expected": expected, "actual": actual})
    _check(
        report,
        "stage8_compact_export_bytes",
        not mismatches,
        {"file_count": len(files), "mismatches": mismatches[:20]},
    )
    confirmatory = root / "phase_c_offline_evaluation_v1_1" / "confirmatory_analysis.json"
    payload = _verify_manifest_hash(
        report,
        name="stage8_confirmatory_analysis_identity",
        path=confirmatory,
        hash_field="manifest_sha256",
        expected=cfg["confirmatory_aggregate_sha256"],
    )
    _check(
        report,
        "stage8_confirmatory_config_link",
        payload.get("primary_config_manifest_sha256") == manifest.get("primary_config_manifest_sha256"),
        {
            "confirmatory": payload.get("primary_config_manifest_sha256"),
            "compact": manifest.get("primary_config_manifest_sha256"),
        },
    )


def _verify_stage9_compact(report: dict[str, Any], cfg: dict[str, Any]) -> None:
    root = PROJECT_ROOT / cfg["root"]
    manifest = _verify_manifest_hash(
        report,
        name="stage9_compact_manifest_identity",
        path=PROJECT_ROOT / cfg["manifest_path"],
        hash_field="manifest_sha256",
        expected=cfg["manifest_sha256"],
    )
    entries = _collect_path_hash_entries(manifest.get("files", {}))
    mismatches: list[dict[str, str]] = []
    unique: dict[tuple[str, str], None] = {}
    for entry in entries:
        unique[(entry["path"], entry["sha256"])] = None
    for relative, expected in unique:
        path = root / relative
        if not path.is_file():
            mismatches.append({"path": relative, "issue": "missing"})
            continue
        actual = _sha256_file(path)
        if actual != expected:
            mismatches.append({"path": relative, "expected": expected, "actual": actual})
    _check(
        report,
        "stage9_compact_evidence_bytes",
        not mismatches,
        {"file_count": len(unique), "mismatches": mismatches[:20]},
    )

    aggregate_path = PROJECT_ROOT / cfg["aggregate_path"]
    raw = _sha256_file(aggregate_path)
    aggregate = _load_json(aggregate_path)
    stored_payload = aggregate.pop("payload_sha256", None)
    payload_hash_ok = (
        stored_payload is None or stored_payload == _canonical_json_hash(aggregate)
    )
    stored = aggregate.get("aggregate_sha256")
    core = dict(aggregate)
    core.pop("aggregate_sha256", None)
    canonical = _canonical_json_hash(core)
    _check(
        report,
        "stage9_aggregate_identity",
        raw == cfg["aggregate_raw_sha256"]
        and payload_hash_ok
        and stored == cfg["aggregate_canonical_sha256"]
        and canonical == cfg["aggregate_canonical_sha256"],
        {
            "raw": raw,
            "expected_raw": cfg["aggregate_raw_sha256"],
            "writer_payload_sha256": stored_payload,
            "writer_payload_hash_ok": payload_hash_ok,
            "stored_canonical": stored,
            "actual_canonical": canonical,
            "expected_canonical": cfg["aggregate_canonical_sha256"],
        },
    )

    plan_path = root / "execution_plan.json"
    plan = _load_json(plan_path)
    stored_payload = plan.pop("payload_sha256", None)
    payload_hash_ok = (
        stored_payload is None or stored_payload == _canonical_json_hash(plan)
    )
    stored_plan = plan.get("plan_sha256")
    plan_core = dict(plan)
    plan_core.pop("plan_sha256", None)
    actual_plan = _canonical_json_hash(plan_core)
    _check(
        report,
        "stage9_execution_plan_identity",
        payload_hash_ok
        and stored_plan == cfg["execution_plan_sha256"]
        and actual_plan == cfg["execution_plan_sha256"],
        {
            "writer_payload_sha256": stored_payload,
            "writer_payload_hash_ok": payload_hash_ok,
            "stored": stored_plan,
            "actual": actual_plan,
            "expected": cfg["execution_plan_sha256"],
        },
    )


def _verify_r0(report: dict[str, Any], cfg: dict[str, Any]) -> None:
    manifest = _verify_manifest_hash(
        report,
        name="r0_v2_manifest_identity",
        path=PROJECT_ROOT / cfg["manifest_path"],
        hash_field="manifest_sha256",
        expected=cfg["manifest_sha256"],
    )
    manifest_rules = manifest.get("rule_artifacts", {})
    mismatches: list[dict[str, Any]] = []
    for item in cfg["rules"]:
        seed = str(item["seed"])
        entry = manifest_rules.get(seed)
        if not isinstance(entry, dict):
            mismatches.append({"seed": seed, "issue": "missing manifest rule entry"})
            continue
        if entry.get("path") != item["path"] or entry.get("sha256") != item["text_sha256"] or entry.get("artifact_sha256") != item["artifact_sha256"]:
            mismatches.append({"seed": seed, "issue": "manifest identity mismatch"})
            continue
        path = PROJECT_ROOT / item["path"]
        if not path.is_file():
            mismatches.append({"seed": seed, "issue": "missing rule file"})
            continue
        text_hash = _normalized_text_sha256(path)
        payload = _load_json(path)
        stored_artifact = payload.get("artifact_sha256")
        core = dict(payload)
        core.pop("artifact_sha256", None)
        artifact_hash = _canonical_json_hash(core)
        if text_hash != item["text_sha256"] or stored_artifact != item["artifact_sha256"] or artifact_hash != item["artifact_sha256"]:
            mismatches.append(
                {
                    "seed": seed,
                    "expected_text": item["text_sha256"],
                    "actual_text": text_hash,
                    "expected_artifact": item["artifact_sha256"],
                    "stored_artifact": stored_artifact,
                    "actual_artifact": artifact_hash,
                }
            )
    _check(report, "r0_v2_rule_bytes", not mismatches, {"rule_count": len(cfg["rules"]), "mismatches": mismatches})


def _verify_system_a(
    report: dict[str, Any],
    cfg: dict[str, Any],
    preprocessing_hash: str,
    checkpoint_root: Path | None,
) -> None:
    manifest = _verify_manifest_hash(
        report,
        name="system_a_manifest_identity",
        path=PROJECT_ROOT / cfg["manifest_path"],
        hash_field="manifest_sha256",
        expected=cfg["manifest_sha256"],
    )
    _check(
        report,
        "system_a_preprocessing_link",
        manifest.get("preprocessing_state_hash") == preprocessing_hash,
        {"manifest": manifest.get("preprocessing_state_hash"), "expected": preprocessing_hash},
    )
    records = {int(row["seed"]): row for row in manifest.get("seed_records", [])}
    missing: list[dict[str, Any]] = []
    mismatches: list[dict[str, Any]] = []
    verified: list[int] = []
    for item in cfg["checkpoints"]:
        seed = int(item["seed"])
        record = records.get(seed)
        if record is None or record.get("checkpoint_file") != item["path"] or record.get("checkpoint_sha256") != item["sha256"]:
            mismatches.append({"seed": seed, "issue": "manifest checkpoint declaration mismatch"})
            continue
        repo_path = PROJECT_ROOT / item["path"]
        candidates = [repo_path]
        if checkpoint_root is not None:
            candidates.append(checkpoint_root / Path(item["path"]).name)
        path = next((candidate for candidate in candidates if candidate.is_file()), None)
        if path is None:
            missing.append({"seed": seed, "path": item["path"], "sha256": item["sha256"]})
            continue
        actual = _sha256_file(path)
        if actual != item["sha256"]:
            mismatches.append({"seed": seed, "path": str(path), "expected": item["sha256"], "actual": actual})
            continue
        verified.append(seed)
    _check(report, "system_a_checkpoint_declarations", not mismatches, {"mismatches": mismatches})
    report["external_artifacts"]["system_a_checkpoints"] = {
        "required": True,
        "verified_seeds": verified,
        "missing": missing,
        "mismatches": mismatches,
        "retrieval": cfg["checkpoint_retrieval"],
    }
    if missing:
        report["blockers"].append("system_a_checkpoint_bytes_missing")
    if mismatches:
        report["failures"].append("system_a_checkpoint_bytes_mismatch")


def run(
    output_dir: Path,
    checkpoint_root: Path | None = None,
    stage8_archive_root: Path | None = None,
) -> dict[str, Any]:
    cfg = _load_json(IDENTITY_PATH)
    report: dict[str, Any] = {
        "audit_id": "stage9.5-1-fresh-clone-reconstruction-v1_2",
        "identity_manifest": str(IDENTITY_PATH.relative_to(PROJECT_ROOT)),
        "checks": [],
        "failures": [],
        "blockers": [],
        "external_artifacts": {
            "raw_dataset": cfg["external_raw_dataset"],
        },
    }

    head = _git("rev-parse", "HEAD")
    status = _git("status", "--porcelain")
    ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", cfg["prerequisite"]["stage9_5_0_closure_commit"], head],
        cwd=PROJECT_ROOT,
        check=False,
    ).returncode == 0
    _check(report, "git_worktree_clean", status == "", {"head": head, "status": status})
    _check(
        report,
        "stage9_5_0_closure_in_ancestry",
        ancestor,
        {"head": head, "closure": cfg["prerequisite"]["stage9_5_0_closure_commit"]},
    )
    report["repository_head"] = head

    runtime = cfg["runtime"]
    _check(report, "python_version", ".".join(map(str, sys.version_info[:3])) == runtime["python_version"], sys.version)
    for key, expected in runtime["thread_environment"].items():
        _check(report, f"thread_env:{key}", os.environ.get(key) == expected, {"actual": os.environ.get(key), "expected": expected})

    lock_path = PROJECT_ROOT / runtime["requirements_lock_path"]
    _check(report, "requirements_lock_raw_sha256", _sha256_file(lock_path) == runtime["requirements_lock_sha256"], _sha256_file(lock_path))
    _check(
        report,
        "requirements_lock_normalized_sha256",
        _normalized_text_sha256(lock_path) == runtime["requirements_lock_normalized_text_sha256"],
        _normalized_text_sha256(lock_path),
    )
    versions = _locked_distributions(lock_path)
    dist_hash = _canonical_json_hash(versions)
    _check(report, "installed_distributions_sha256", dist_hash == runtime["installed_distributions_sha256"], dist_hash)

    import torch

    torch.set_num_threads(int(runtime["torch_num_threads"]))
    try:
        torch.set_num_interop_threads(int(runtime["torch_num_interop_threads"]))
    except RuntimeError:
        pass
    torch.use_deterministic_algorithms(bool(runtime["torch_deterministic_algorithms"]))
    _check(report, "torch_version", str(torch.__version__) == runtime["torch_version"], str(torch.__version__))
    _check(report, "torch_num_threads", torch.get_num_threads() == int(runtime["torch_num_threads"]), torch.get_num_threads())
    _check(report, "torch_num_interop_threads", torch.get_num_interop_threads() == int(runtime["torch_num_interop_threads"]), torch.get_num_interop_threads())
    _check(report, "torch_deterministic_algorithms", torch.are_deterministic_algorithms_enabled(), torch.are_deterministic_algorithms_enabled())

    scenario_cfg = cfg["scenario"]
    scenario_path = PROJECT_ROOT / scenario_cfg["manifest_path"]
    scenario_checkout_raw = _sha256_file(scenario_path)
    scenario_repository_text = _normalized_text_sha256(scenario_path)
    scenario = _load_json(scenario_path)
    scenario_canonical = _canonical_json_hash(scenario)
    scenario_version = scenario.get("scenario_version")
    _check(
        report,
        "scenario_identity",
        scenario_repository_text == scenario_cfg["raw_sha256"]
        and scenario_canonical == scenario_cfg["canonical_sha256"]
        and scenario.get("scenario_id") == scenario_cfg["scenario_id"]
        and scenario_version is not None
        and int(scenario_version) == int(scenario_cfg["scenario_version"]),
        {
            "checkout_raw": scenario_checkout_raw,
            "repository_lf_text_sha256": scenario_repository_text,
            "expected_repository_lf_text_sha256": scenario_cfg["raw_sha256"],
            "canonical": scenario_canonical,
            "scenario_id": scenario.get("scenario_id"),
            "scenario_version": scenario.get("scenario_version"),
        },
    )

    prep_cfg = cfg["preprocessing"]
    preprocessing = _load_json(PROJECT_ROOT / prep_cfg["artifact_path"])
    _check(
        report,
        "preprocessing_identity",
        preprocessing.get("core_state_sha256") == prep_cfg["core_state_sha256"]
        and preprocessing.get("training_fit_scope", {}).get("identity_sha256") == prep_cfg["training_rows_identity_sha256"]
        and int(preprocessing.get("feature_schema", {}).get("count")) == int(prep_cfg["feature_count"])
        and preprocessing.get("training_fit_scope", {}).get("development_used_for_fit") is False
        and preprocessing.get("training_fit_scope", {}).get("pre_drift_used_for_fit") is False
        and preprocessing.get("training_fit_scope", {}).get("post_drift_used_for_fit") is False,
        {
            "core_state_sha256": preprocessing.get("core_state_sha256"),
            "training_identity": preprocessing.get("training_fit_scope", {}).get("identity_sha256"),
        },
    )

    _verify_system_a(report, cfg["system_a"], prep_cfg["core_state_sha256"], checkpoint_root)
    _verify_r0(report, cfg["r0_v2"])
    _verify_stage8_compact(report, cfg["stage8_compact"])
    _verify_stage8_large_archive(
        report,
        cfg["stage8_compact"],
        cfg["stage8_large_artifact_archive"],
        stage8_archive_root,
    )
    _verify_stage9_compact(report, cfg["stage9_compact"])

    report["status"] = "pass" if not report["failures"] and not report["blockers"] else "blocked"
    report["pass"] = report["status"] == "pass"
    report["canonical_sha256"] = _canonical_json_hash(report)

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "fresh_clone_reconstruction_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    md = [
        "# Stage 9.5-1 Fresh-Clone Reconstruction",
        "",
        f"- status: **{report['status'].upper()}**",
        f"- repository head: `{head}`",
        f"- failures: **{len(report['failures'])}**",
        f"- blockers: **{len(report['blockers'])}**",
        f"- report canonical SHA-256: `{report['canonical_sha256']}`",
        "",
        "## Blockers",
        "",
    ]
    md += [f"- {item}" for item in report["blockers"]] or ["- none"]
    md += ["", "## Failures", ""]
    md += [f"- {item}" for item in report["failures"]] or ["- none"]
    (output_dir / "FRESH_CLONE_RECONSTRUCTION_REPORT.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    if not report["pass"]:
        raise SystemExit(
            f"Stage 9.5-1 blocked: {len(report['failures'])} identity failures and "
            f"{len(report['blockers'])} external-artifact blockers."
        )
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Stage 9.5-1 clean-clone reconstruction verifier")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("artifacts/stage9_5_v1_2/fresh_clone_reconstruction"),
    )
    parser.add_argument(
        "--checkpoint-root",
        type=Path,
        default=None,
        help="Optional external directory containing seed_0.pt ... seed_4.pt.",
    )
    parser.add_argument(
        "--stage8-archive-root",
        type=Path,
        default=None,
        help=(
            "Optional recovered root corresponding to artifacts/cd_primary_v1."
        ),
    )
    args = parser.parse_args()
    run(
        args.output_dir,
        checkpoint_root=args.checkpoint_root,
        stage8_archive_root=args.stage8_archive_root,
    )


if __name__ == "__main__":
    main()
