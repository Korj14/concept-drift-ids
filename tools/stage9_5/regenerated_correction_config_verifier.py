from __future__ import annotations

import argparse
import copy
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]

AUDIT_ID = "stage9.5-6-regenerated-correction-config-verifier-v1"
ACCEPTED_STAGE8_EVIDENCE_COMMIT = "c2ded83b8195b9321e715626c1f305f9627936e8"
HISTORICAL_PHASE_A_B_HEAD = "bfa14b942e4a5b2fbfa8aa3c43728a7f1cd81645"
CORRECTION_SOURCE_HEAD = "79ddc4c6d6dea52c7cabc55a6d082448fc24fcf9"
ACCEPTED_CORRECTION_MANIFEST_SHA256 = (
    "d380fce5f9db8f0b639dc999298a263b10a10a3d02e35def226a121d098e2222"
)
ACCEPTED_CORRECTION_CONFIG_PATH = "data/manifests/cd_primary_run_config_v1_1.json"
PHASE_A_SUBDIR = "phase_a_shared_control_plane"
PHASE_B_SUBDIR = "phase_b_symbolic_arms"
SEEDS = (0, 1, 2, 3, 4)

FROZEN_SCIENTIFIC_BLOCKS = (
    "governing_source_hashes",
    "scenario",
    "system_a",
    "r0_v2",
    "primary_control_plane",
    "primary_symbolic_operator",
    "fusion",
    "analysis",
)

CORRECTION_FALSE_FLAGS = (
    "scientific_parameter_change",
    "treatment_change",
    "endpoint_change",
    "threshold_change",
    "upstream_adaptive_artifact_reexecution",
)


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for key, value in pairs:
        if key in payload:
            raise ValueError(f"Duplicate JSON object key: {key}")
        payload[key] = value
    return payload


def _parse_json(text: str) -> dict[str, Any]:
    payload = json.loads(text, object_pairs_hook=_reject_duplicate_pairs)
    if not isinstance(payload, dict):
        raise TypeError("Expected JSON object")
    return payload


def _load_json(path: Path) -> dict[str, Any]:
    return _parse_json(path.read_text(encoding="utf-8"))


def _canonical_sha256(payload: object) -> str:
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _git(
    repo_root: Path,
    *args: str,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo_root,
        check=check,
        capture_output=True,
        text=True,
    )


def _git_head(repo_root: Path) -> str:
    return _git(repo_root, "rev-parse", "HEAD").stdout.strip()


def _git_commit_exists(repo_root: Path, commit: str) -> bool:
    result = _git(
        repo_root,
        "cat-file",
        "-e",
        f"{commit}^{{commit}}",
        check=False,
    )
    return result.returncode == 0


def _git_is_ancestor(repo_root: Path, ancestor: str, descendant: str) -> bool:
    result = _git(
        repo_root,
        "merge-base",
        "--is-ancestor",
        ancestor,
        descendant,
        check=False,
    )
    return result.returncode == 0


def _git_show_json(repo_root: Path, commit: str, path: str) -> dict[str, Any]:
    result = _git(repo_root, "show", f"{commit}:{path}")
    return _parse_json(result.stdout)


def _verify_hashed_json(payload: dict[str, Any], *, label: str) -> list[str]:
    failures: list[str] = []
    stored_payload = payload.get("payload_sha256")
    stored_manifest = payload.get("manifest_sha256")

    payload_core = dict(payload)
    payload_core.pop("payload_sha256", None)
    if not isinstance(stored_payload, str):
        failures.append(f"{label}:payload_sha256_missing")
    elif _canonical_sha256(payload_core) != stored_payload:
        failures.append(f"{label}:payload_sha256_mismatch")

    manifest_core = dict(payload_core)
    manifest_core.pop("manifest_sha256", None)
    if not isinstance(stored_manifest, str):
        failures.append(f"{label}:manifest_sha256_missing")
    elif _canonical_sha256(manifest_core) != stored_manifest:
        failures.append(f"{label}:manifest_sha256_mismatch")
    return failures


def _upstream_maps(
    config: dict[str, Any],
    *,
    label: str,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None, list[str]]:
    failures: list[str] = []
    correction = config.get("correction")
    if not isinstance(correction, dict):
        return None, None, [f"{label}:correction_block_invalid"]
    reused = correction.get("reused_upstream_artifacts")
    if not isinstance(reused, dict):
        return None, None, [f"{label}:reused_upstream_artifacts_invalid"]
    phase_a = reused.get("phase_a")
    phase_b = reused.get("phase_b")
    if not isinstance(phase_a, dict):
        failures.append(f"{label}:phase_a_upstream_map_invalid")
        phase_a = None
    if not isinstance(phase_b, dict):
        failures.append(f"{label}:phase_b_upstream_map_invalid")
        phase_b = None
    return phase_a, phase_b, failures


def _verify_accepted_evidence(
    *,
    repo_root: Path,
    accepted_evidence_commit: str,
    accepted_correction_manifest_sha256: str,
    historical_phase_a_b_head: str,
    correction_source_head: str,
) -> tuple[dict[str, Any] | None, list[str]]:
    failures: list[str] = []
    current_head = _git_head(repo_root)

    for name, commit in (
        ("accepted_stage8_evidence", accepted_evidence_commit),
        ("historical_phase_a_b", historical_phase_a_b_head),
        ("correction_source", correction_source_head),
    ):
        if not _git_commit_exists(repo_root, commit):
            failures.append(f"{name}_commit_missing:{commit}")

    if failures:
        return None, failures

    if not _git_is_ancestor(repo_root, accepted_evidence_commit, current_head):
        failures.append("accepted_stage8_evidence_not_ancestor_of_current_head")
    if not _git_is_ancestor(
        repo_root,
        historical_phase_a_b_head,
        accepted_evidence_commit,
    ):
        failures.append("historical_phase_a_b_head_not_ancestor_of_stage8_evidence")
    if not _git_is_ancestor(
        repo_root,
        correction_source_head,
        accepted_evidence_commit,
    ):
        failures.append("correction_source_head_not_ancestor_of_stage8_evidence")

    try:
        accepted = _git_show_json(
            repo_root,
            accepted_evidence_commit,
            ACCEPTED_CORRECTION_CONFIG_PATH,
        )
    except (subprocess.CalledProcessError, json.JSONDecodeError, TypeError, ValueError) as exc:
        failures.append(
            f"accepted_correction_config_unreadable:{type(exc).__name__}"
        )
        return None, failures

    failures.extend(
        _verify_hashed_json(accepted, label="accepted_correction_config")
    )
    if accepted.get("manifest_sha256") != accepted_correction_manifest_sha256:
        failures.append("accepted_correction_manifest_identity_mismatch")

    implementation_ready = accepted.get("implementation_ready")
    if (
        not isinstance(implementation_ready, dict)
        or implementation_ready.get("prepared_from_git_commit")
        != correction_source_head
    ):
        failures.append("accepted_correction_source_head_mismatch")

    phase_a, phase_b, map_failures = _upstream_maps(
        accepted,
        label="accepted_correction_config",
    )
    failures.extend(map_failures)

    if phase_a is not None and phase_b is not None:
        for seed in SEEDS:
            key = str(seed)
            accepted_a = phase_a.get(key)
            accepted_b = phase_b.get(key)
            if not isinstance(accepted_a, dict):
                failures.append(f"accepted_correction_config:missing_phase_a_seed:{seed}")
            if not isinstance(accepted_b, dict):
                failures.append(f"accepted_correction_config:missing_phase_b_seed:{seed}")

            try:
                a_manifest = _git_show_json(
                    repo_root,
                    accepted_evidence_commit,
                    (
                        "results/frozen/cd_primary_v1/"
                        f"{PHASE_A_SUBDIR}/seed-{seed}/run_manifest.json"
                    ),
                )
                b_manifest = _git_show_json(
                    repo_root,
                    accepted_evidence_commit,
                    (
                        "results/frozen/cd_primary_v1/"
                        f"{PHASE_B_SUBDIR}/seed-{seed}/phase_b_manifest.json"
                    ),
                )
            except (
                subprocess.CalledProcessError,
                json.JSONDecodeError,
                TypeError,
                ValueError,
            ) as exc:
                failures.append(
                    f"accepted_upstream_manifest_unreadable:{seed}:{type(exc).__name__}"
                )
                continue

            failures.extend(
                _verify_hashed_json(a_manifest, label=f"accepted_phase_a_seed_{seed}")
            )
            failures.extend(
                _verify_hashed_json(b_manifest, label=f"accepted_phase_b_seed_{seed}")
            )
            if a_manifest.get("git_commit") != historical_phase_a_b_head:
                failures.append(f"accepted_phase_a_head_mismatch:{seed}")
            if b_manifest.get("git_commit") != historical_phase_a_b_head:
                failures.append(f"accepted_phase_b_head_mismatch:{seed}")

            if isinstance(accepted_a, dict) and (
                accepted_a.get("run_manifest_sha256")
                != a_manifest.get("manifest_sha256")
            ):
                failures.append(
                    f"accepted_phase_a_manifest_binding_mismatch:{seed}"
                )
            if isinstance(accepted_b, dict) and (
                accepted_b.get("phase_b_manifest_sha256")
                != b_manifest.get("manifest_sha256")
            ):
                failures.append(
                    f"accepted_phase_b_manifest_binding_mismatch:{seed}"
                )

    return accepted, failures


def _verify_regenerated_upstream_bindings(
    config: dict[str, Any],
    *,
    fresh_artifact_root: Path,
    historical_phase_a_b_head: str,
) -> list[str]:
    failures: list[str] = []
    phase_a, phase_b, map_failures = _upstream_maps(
        config,
        label="regenerated_correction_config",
    )
    failures.extend(map_failures)
    if phase_a is None or phase_b is None:
        return failures

    for seed in SEEDS:
        key = str(seed)
        config_a = phase_a.get(key)
        config_b = phase_b.get(key)
        if not isinstance(config_a, dict):
            failures.append(f"regenerated_correction_config:missing_phase_a_seed:{seed}")
        if not isinstance(config_b, dict):
            failures.append(f"regenerated_correction_config:missing_phase_b_seed:{seed}")

        a_path = (
            fresh_artifact_root
            / PHASE_A_SUBDIR
            / f"seed-{seed}"
            / "run_manifest.json"
        )
        b_path = (
            fresh_artifact_root
            / PHASE_B_SUBDIR
            / f"seed-{seed}"
            / "phase_b_manifest.json"
        )
        try:
            a_manifest = _load_json(a_path)
        except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
            failures.append(
                f"regenerated_phase_a_manifest_unreadable:{seed}:{type(exc).__name__}"
            )
            a_manifest = None
        try:
            b_manifest = _load_json(b_path)
        except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
            failures.append(
                f"regenerated_phase_b_manifest_unreadable:{seed}:{type(exc).__name__}"
            )
            b_manifest = None

        if isinstance(a_manifest, dict):
            failures.extend(
                _verify_hashed_json(a_manifest, label=f"regenerated_phase_a_seed_{seed}")
            )
            if a_manifest.get("git_commit") != historical_phase_a_b_head:
                failures.append(f"regenerated_phase_a_head_mismatch:{seed}")
            if isinstance(config_a, dict) and (
                config_a.get("run_manifest_sha256")
                != a_manifest.get("manifest_sha256")
            ):
                failures.append(
                    f"regenerated_phase_a_manifest_binding_mismatch:{seed}"
                )

        if isinstance(b_manifest, dict):
            failures.extend(
                _verify_hashed_json(b_manifest, label=f"regenerated_phase_b_seed_{seed}")
            )
            if b_manifest.get("git_commit") != historical_phase_a_b_head:
                failures.append(f"regenerated_phase_b_head_mismatch:{seed}")
            if isinstance(config_b, dict) and (
                config_b.get("phase_b_manifest_sha256")
                != b_manifest.get("manifest_sha256")
            ):
                failures.append(
                    f"regenerated_phase_b_manifest_binding_mismatch:{seed}"
                )

    return failures


def verify_regenerated_correction_config(
    regenerated_config_path: Path,
    fresh_artifact_root: Path,
    *,
    repo_root: Path = PROJECT_ROOT,
    accepted_evidence_commit: str = ACCEPTED_STAGE8_EVIDENCE_COMMIT,
    historical_phase_a_b_head: str = HISTORICAL_PHASE_A_B_HEAD,
    correction_source_head: str = CORRECTION_SOURCE_HEAD,
    accepted_correction_manifest_sha256: str = ACCEPTED_CORRECTION_MANIFEST_SHA256,
) -> dict[str, Any]:
    failures: list[str] = []

    accepted, accepted_failures = _verify_accepted_evidence(
        repo_root=repo_root,
        accepted_evidence_commit=accepted_evidence_commit,
        accepted_correction_manifest_sha256=accepted_correction_manifest_sha256,
        historical_phase_a_b_head=historical_phase_a_b_head,
        correction_source_head=correction_source_head,
    )
    failures.extend(accepted_failures)

    try:
        regenerated = _load_json(regenerated_config_path)
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        regenerated = None
        failures.append(
            f"regenerated_correction_config_unreadable:{type(exc).__name__}"
        )

    scientific_block_mismatches: list[str] = []
    if isinstance(regenerated, dict):
        failures.extend(
            _verify_hashed_json(
                regenerated,
                label="regenerated_correction_config",
            )
        )

        ready = regenerated.get("implementation_ready")
        if (
            not isinstance(ready, dict)
            or ready.get("prepared_from_git_commit") != correction_source_head
        ):
            failures.append("regenerated_correction_source_head_mismatch")

        if isinstance(accepted, dict):
            if (
                regenerated.get("run_id") != accepted.get("run_id")
                or regenerated.get("status") != accepted.get("status")
                or regenerated.get("upstream_artifact_config_manifest_sha256")
                != accepted.get("upstream_artifact_config_manifest_sha256")
            ):
                failures.append("regenerated_correction_protocol_identity_mismatch")

            for block in FROZEN_SCIENTIFIC_BLOCKS:
                if regenerated.get(block) != accepted.get(block):
                    scientific_block_mismatches.append(block)
                    failures.append(f"scientific_block_mismatch:{block}")

            accepted_correction = accepted.get("correction")
            regenerated_correction = regenerated.get("correction")
            if not isinstance(regenerated_correction, dict):
                failures.append("regenerated_correction_metadata_invalid")
            elif isinstance(accepted_correction, dict):
                for field in (
                    "classification",
                    "correction_id",
                    "parent_config_manifest_sha256",
                    "corrected_phase_c_output_subdir",
                ):
                    if regenerated_correction.get(field) != accepted_correction.get(field):
                        failures.append(
                            f"regenerated_correction_metadata_mismatch:{field}"
                        )
                for flag in CORRECTION_FALSE_FLAGS:
                    if regenerated_correction.get(flag) is not False:
                        failures.append(
                            f"regenerated_correction_forbidden_change_flag:{flag}"
                        )

        failures.extend(
            _verify_regenerated_upstream_bindings(
                regenerated,
                fresh_artifact_root=fresh_artifact_root,
                historical_phase_a_b_head=historical_phase_a_b_head,
            )
        )

    report: dict[str, Any] = {
        "audit_id": AUDIT_ID,
        "status": "pass" if not failures else "blocked",
        "pass": not failures,
        "failures": failures,
        "bindings": {
            "historical_phase_a_b_head": historical_phase_a_b_head,
            "correction_source_head": correction_source_head,
            "accepted_correction_manifest_sha256": (
                accepted_correction_manifest_sha256
            ),
            "accepted_stage8_evidence_commit": accepted_evidence_commit,
        },
        "frozen_scientific_blocks": list(FROZEN_SCIENTIFIC_BLOCKS),
        "scientific_blocks_equal": not scientific_block_mismatches,
        "scientific_block_mismatches": scientific_block_mismatches,
        "post_outcome_scientific_field_changes_permitted": False,
        "phase_c_outcomes_accessed": False,
        "stage10_outcomes_accessed": False,
        "manual_success_override_permitted": False,
    }
    core = copy.deepcopy(report)
    report["canonical_sha256"] = _canonical_sha256(core)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Verify a regenerated Stage-9.5-6 correction config against the "
            "accepted Stage-8 correction identity and historical Phase-A/B lineage."
        )
    )
    parser.add_argument("--regenerated-config", type=Path, required=True)
    parser.add_argument("--fresh-artifact-root", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    report = verify_regenerated_correction_config(
        args.regenerated_config,
        args.fresh_artifact_root,
    )
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    print(json.dumps(report, indent=2, sort_keys=True))
    if not report["pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
