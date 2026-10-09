from __future__ import annotations

import ast
import gzip
import inspect
import json
import os
from pathlib import Path

import numpy as np
import pytest
import torch

import concept_drift_ids.cd_primary_config as primary_config
import concept_drift_ids.cd_primary_correction as correction
import concept_drift_ids.cd_primary_export as primary_export
import concept_drift_ids.cd_primary_phase_a as phase_a
import concept_drift_ids.cd_primary_phase_b as phase_b
import concept_drift_ids.cd_primary_phase_c as phase_c
from concept_drift_ids.cd_control_plane import (
    canonical_sha256,
    write_json_new,
)
from concept_drift_ids.cd_symbolic_arms import SymbolicOperatorConfig
from concept_drift_ids.cd_symbolic_lifecycle import (
    migrate_r0_v2_rules,
    rule_base_state_from_dict,
)
from concept_drift_ids.cd_symbolic_runner import (
    SharedSymbolicRow,
    _generation_result,
    run_periodic_symbolic_arm,
)
from concept_drift_ids.symbolic import Condition, Rule


def _preflight() -> dict:
    return {
        "status": "implementation_ready_preflight_passed",
        "primary_pre_post_partitions_loaded": False,
        "system_b_v2_active_rule_counts": {
            0: 7,
            1: 6,
            2: 7,
            3: 6,
            4: 6,
        },
        "primary_control_plane_config_sha256": "control",
        "primary_symbolic_operator_config_sha256": "symbolic",
    }


def test_primary_config_build_is_no_data_and_freezes_complete_surface(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        primary_config,
        "verify_implementation_tag",
        lambda **_: None,
    )
    monkeypatch.setattr(
        primary_config,
        "require_clean_worktree",
        lambda **_: None,
    )
    monkeypatch.setattr(
        primary_config,
        "_text_hashes",
        lambda paths, project_root: {
            str(path): f"hash-{index}"
            for index, path in enumerate(paths)
        },
    )
    monkeypatch.setattr(
        primary_config,
        "_requirements_identity",
        lambda **_: {
            "path": "requirements-lock.txt",
            "binding_normalized_text_sha256": "text",
            "installed_distributions": {"numpy": "2.4.6"},
            "installed_distributions_sha256": "installed",
        },
    )
    monkeypatch.setattr(
        primary_config,
        "_git_output",
        lambda *args, **kwargs: "prepared-head",
    )

    payload = primary_config.build_primary_run_config(
        project_root=tmp_path,
        preflight=_preflight(),
    )

    assert payload["status"] == "frozen_before_primary_adaptive_access"
    assert payload["preparation"]["primary_partitions_loaded"] is False
    assert payload["preparation"]["heldout_access_occurred"] is False
    assert payload["execution"]["phase_order"] == [
        "phase_a_shared_control_plane",
        "phase_b_symbolic_arms",
        "phase_c_offline_evaluation",
    ]
    assert payload["execution"]["execution_output_root"] == (
        "artifacts/cd_primary_v1"
    )
    for required in (
        "src/concept_drift_ids/cd_primary_phase_a.py",
        "src/concept_drift_ids/cd_primary_phase_b.py",
        "src/concept_drift_ids/cd_primary_phase_c.py",
        "src/concept_drift_ids/cd_primary_export.py",
        "scripts/run_primary.ps1",
        ".gitattributes",
        ".gitignore",
        ".github/workflows/stage3-unit.yml",
    ):
        assert required in payload["scientific_source_hashes"]


def test_primary_config_json_hash_round_trip_and_tamper_rejection(
    tmp_path: Path,
) -> None:
    core = {
        "schema_version": 1,
        "run_id": "toy-primary",
        "status": "frozen_before_primary_adaptive_access",
    }
    payload = dict(core)
    payload["manifest_sha256"] = canonical_sha256(core)
    path = tmp_path / "config.json"
    write_json_new(path, payload)

    loaded = primary_config.load_primary_run_config(path=path)
    assert loaded["manifest_sha256"] == payload["manifest_sha256"]

    text = path.read_text(encoding="utf-8")
    path.write_text(
        text.replace("toy-primary", "toy-primary-mutated"),
        encoding="utf-8",
        newline="\n",
    )
    with pytest.raises(ValueError, match="hash mismatch"):
        primary_config.load_primary_run_config(path=path)


def _top_level_import_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    modules: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


def test_primary_prepare_has_no_scenario_partition_loader_import() -> None:
    path = Path(primary_config.__file__)
    modules = _top_level_import_modules(path)
    assert "concept_drift_ids.scenario_loader" not in modules
    assert all("load_partition" not in module for module in modules)


def test_phase_a_defers_primary_adapter_until_after_frozen_config_gate() -> None:
    path = Path(phase_a.__file__)
    modules = _top_level_import_modules(path)
    assert "concept_drift_ids.cd_primary_adapter" not in modules

    source = inspect.getsource(phase_a.execute_phase_a_seed)
    gate = source.index("verify_primary_run_config_for_execution()")
    adapter = source.index(
        "from concept_drift_ids.cd_primary_adapter import"
    )
    assert gate < adapter


def _toy_rule() -> Rule:
    return Rule(
        rule_id="toy",
        lineage_id="toy-lineage",
        rule_base_version="R0.v2",
        seed=0,
        conditions=(Condition("x", ">", 0.5),),
        consequent=1,
        confidence=0.95,
        support=0.5,
        covered_count=50,
        class_precision=0.95,
        neural_fidelity=0.95,
        stability=1.0,
        complexity=1,
        lifecycle_state="active",
        source_candidate_id="source",
        validation_evidence_id="validation",
    )


def test_rule_base_state_round_trip_preserves_hashes() -> None:
    state = migrate_r0_v2_rules(
        seed=0,
        rules=[_toy_rule()],
        neural_checkpoint_sha256="checkpoint",
    )
    restored = rule_base_state_from_dict(state.to_dict())
    assert restored == state
    assert restored.canonical_sha256 == state.canonical_sha256
    assert restored.history_sha256 == state.history_sha256


def test_periodic_arm_rejects_seed_mismatch_before_any_shared_access() -> None:
    state = migrate_r0_v2_rules(
        seed=0,
        rules=[],
        neural_checkpoint_sha256="checkpoint",
    )
    with pytest.raises(ValueError, match="seed mismatch"):
        run_periodic_symbolic_arm(
            seed=1,
            initial_state=state,
            shared_identity_sha256="shared",
            shared_predictions=(),
            checkpoint_chain=(),
            rows=(),
            feature_names=("x",),
            model_resolver=lambda _: torch.nn.Identity(),
        )


def test_insufficient_generation_preserves_auditable_payload() -> None:
    rows = tuple(
        SharedSymbolicRow(
            row_id=f"r-{index}",
            origin_index=index,
            maturity_index=index,
            features=np.asarray([float(index)], dtype=np.float32),
            true_label=0,
            neural_probability=0.1,
            neural_checkpoint_sha256="checkpoint",
        )
        for index in range(10)
    )
    lookup = {row.row_id: row for row in rows}
    (
        candidates,
        evidence_id,
        status,
        timing,
        payload,
    ) = _generation_result(
        model=torch.nn.Identity(),
        row_ids=tuple(lookup),
        lookup=lookup,
        feature_names=("x",),
        seed=0,
        opportunity_id=1,
        raw_affine=None,
        operator_config=SymbolicOperatorConfig(),
    )
    assert candidates == ()
    assert len(evidence_id) == 64
    assert status == "candidate_generation_insufficient_class_evidence"
    assert timing == {"shap": 0.0, "surrogate": 0.0}
    assert payload["status"] == status
    assert payload["generation_evidence_id"] == evidence_id
    assert payload["row_count"] == 10


def test_primary_trace_writer_preserves_uncompressed_content_identity(
    tmp_path: Path,
) -> None:
    rows = (
        {"row_id": "r0", "value": 1},
        {"row_id": "r1", "value": 2},
    )
    path = tmp_path / "trace.jsonl.gz"
    identity = phase_c._write_trace_gzip_new(path, rows)

    digest = __import__("hashlib").sha256()
    with gzip.open(path, "rb") as file:
        content = file.read()
    digest.update(content)
    assert digest.hexdigest() == identity["canonical_jsonl_sha256"]
    assert identity["sha256"]
    assert content.decode("utf-8").splitlines() == [
        '{"row_id":"r0","value":1}',
        '{"row_id":"r1","value":2}',
    ]


def test_heavy_primary_evidence_is_gitignored_and_compact_export_is_not() -> None:
    root = primary_config.PROJECT_ROOT
    ignore = (root / ".gitignore").read_text(encoding="utf-8")
    attrs = (root / ".gitattributes").read_text(encoding="utf-8")
    assert "artifacts/*" in ignore
    assert str(primary_config.PRIMARY_OUTPUT_ROOT).startswith(
        str(root / "artifacts")
    )
    assert str(primary_export.COMPACT_EXPORT_ROOT).startswith(
        str(root / "results" / "frozen")
    )
    assert "data/manifests/cd_primary_run_config_v1.json text eol=lf" in attrs
    assert "results/frozen/cd_primary_v1/** text eol=lf" in attrs


def test_compact_export_file_selection_excludes_heavy_prediction_traces() -> None:
    files = primary_export._phase_c_compact_files(0)
    assert files
    assert all(not str(path).endswith(".jsonl.gz") for path in files)


def test_root_runner_exposes_all_gated_primary_commands() -> None:
    text = (primary_config.PROJECT_ROOT / "run.py").read_text(
        encoding="utf-8"
    )
    for command in (
        "cd-primary-prepare",
        "cd-primary-phase-a",
        "cd-primary-phase-b",
        "cd-primary-phase-c",
        "cd-primary-export",
    ):
        assert f'"{command}"' in text


def test_primary_launcher_sets_frozen_environment_before_python() -> None:
    text = (
        primary_config.PROJECT_ROOT / "scripts" / "run_primary.ps1"
    ).read_text(encoding="utf-8")
    python_position = text.index("python run.py")
    for key in (
        "PYTHONHASHSEED",
        "OMP_NUM_THREADS",
        "MKL_NUM_THREADS",
        "OPENBLAS_NUM_THREADS",
        "NUMEXPR_NUM_THREADS",
    ):
        assert text.index(f"$env:{key}") < python_position



def test_exact_config_commit_gate_rejects_later_head(
    monkeypatch,
    tmp_path: Path,
) -> None:
    def same_head(*args, **kwargs):
        if args[:2] == ("rev-parse", "HEAD"):
            return "config-commit"
        if args[:3] == ("log", "-1", "--format=%H"):
            return "config-commit"
        raise AssertionError(args)

    monkeypatch.setattr(primary_config, "_git_output", same_head)
    assert (
        primary_config._require_exact_config_commit(
            project_root=tmp_path
        )
        == "config-commit"
    )

    def later_head(*args, **kwargs):
        if args[:2] == ("rev-parse", "HEAD"):
            return "later-commit"
        if args[:3] == ("log", "-1", "--format=%H"):
            return "config-commit"
        raise AssertionError(args)

    monkeypatch.setattr(primary_config, "_git_output", later_head)
    with pytest.raises(RuntimeError, match="exactly the commit"):
        primary_config._require_exact_config_commit(
            project_root=tmp_path
        )



def test_committed_primary_config_verifies_exact_head_when_present() -> None:
    if not primary_config.PRIMARY_CONFIG_PATH.is_file():
        pytest.skip("Primary run config has not been generated yet.")

    head = primary_config._git_output("rev-parse", "HEAD")
    config_commit = primary_config._git_output(
        "log",
        "-1",
        "--format=%H",
        "--",
        "data/manifests/cd_primary_run_config_v1.json",
    )
    if (
        os.environ.get("GITHUB_EVENT_NAME") == "pull_request"
        and head != config_commit
    ):
        pytest.skip(
            "PR workflow is testing a synthetic merge commit; the exact "
            "config-head push run is the primary execution gate."
        )

    config = primary_config.verify_primary_run_config_for_execution()
    assert config["status"] == "frozen_before_primary_adaptive_access"
    assert config["preparation"]["heldout_access_occurred"] is False



def test_dependency_lock_binding_is_normalized_text_not_raw_checkout_bytes() -> None:
    identity = primary_config._requirements_identity(
        project_root=primary_config.PROJECT_ROOT
    )
    assert (
        identity["binding_normalized_text_sha256"]
        == primary_config.EXPECTED_REQUIREMENTS_NORMALIZED_SHA256
    )
    assert "freeze_checkout_raw_sha256" not in identity
    assert identity["installed_distributions"]["numpy"] == "2.4.6"
    assert len(identity["installed_distributions_sha256"]) == 64
    attrs = (primary_config.PROJECT_ROOT / ".gitattributes").read_text(
        encoding="utf-8"
    )
    assert "requirements-lock.txt text eol=lf" in attrs



def test_phase_c_recovery_reports_rows_from_boundary() -> None:
    windows = {
        "pre": [
            {
                "row_count": 5_000,
                "mcc": 0.6,
                "mcsc": 0.6,
                "fpr": 0.3,
                "start_index": primary_config.PRIMARY_STREAM_LENGTH - 80_000,
            },
            {
                "row_count": 5_000,
                "mcc": 0.7,
                "mcsc": 0.7,
                "fpr": 0.2,
                "start_index": primary_config.PRIMARY_STREAM_LENGTH - 75_000,
            },
            {
                "row_count": 5_000,
                "mcc": 0.8,
                "mcsc": 0.8,
                "fpr": 0.1,
                "start_index": primary_config.PRIMARY_STREAM_LENGTH - 70_000,
            },
        ],
        "post": [
            {
                "row_count": 5_000,
                "mcc": 0.75,
                "mcsc": 0.75,
                "fpr": 0.15,
                "start_index": phase_c.EXPECTED_PRE_ROWS,
            },
            {
                "row_count": 5_000,
                "mcc": 0.75,
                "mcsc": 0.75,
                "fpr": 0.15,
                "start_index": phase_c.EXPECTED_PRE_ROWS + 5_000,
            },
        ],
    }
    summary = phase_c._recovery_summary(windows)
    assert summary["mcc"]["recovery_clock"] == phase_c.EXPECTED_PRE_ROWS
    assert summary["mcc"]["recovery_rows_from_boundary"] == 0



def _write_hashed_json(path: Path, payload: dict, hash_field: str) -> str:
    body = dict(payload)
    body[hash_field] = canonical_sha256(body)
    write_json_new(path, body)
    return body[hash_field]


def test_phase_b_verifier_rebinds_shared_identity_to_verified_phase_a(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        phase_b,
        "verify_primary_run_config_for_execution",
        lambda: {"manifest_sha256": "config"},
    )
    monkeypatch.setattr(
        phase_b,
        "verify_phase_a_seed",
        lambda seed: {
            "shared_identity_sha256": f"shared-{seed}",
            "run_manifest_sha256": f"phase-a-{seed}",
        },
    )
    monkeypatch.setattr(
        phase_b,
        "_phase_b_dir",
        lambda seed: tmp_path,
    )

    operator_sha = SymbolicOperatorConfig().sha256()
    core = {
        "schema_version": 1,
        "seed": 0,
        "primary_config_manifest_sha256": "config",
        "shared_identity_sha256": "forged-shared",
        "all_phase_a_shared_identity_sha256": {
            str(seed): f"shared-{seed}" for seed in primary_config.PRIMARY_SEEDS
        },
        "operator_config_sha256": operator_sha,
        "arm_isolation_sha256": "isolation",
        "arms": {},
    }
    _write_hashed_json(
        tmp_path / "phase_b_manifest.json",
        core,
        "manifest_sha256",
    )

    with pytest.raises(ValueError, match="verified Phase A"):
        phase_b.verify_phase_b_seed(0)


def test_phase_c_verifier_rebinds_arm_summary_to_verified_phase_a(
    monkeypatch,
    tmp_path: Path,
) -> None:
    phase_c_dir = tmp_path / "phase-c"
    phase_b_dir = tmp_path / "phase-b"
    phase_c_dir.mkdir()
    phase_b_dir.mkdir()

    monkeypatch.setattr(
        phase_c,
        "verify_primary_run_config_for_execution",
        lambda: {
            "manifest_sha256": "config",
            "scenario": {"stream_rows": 2},
        },
    )
    monkeypatch.setattr(
        phase_c,
        "verify_phase_a_seed",
        lambda seed: {
            "run_manifest_sha256": "phase-a-manifest",
            "shared_identity_sha256": "verified-shared",
        },
    )
    monkeypatch.setattr(
        phase_c,
        "verify_phase_b_seed",
        lambda seed: {"phase_b_manifest_sha256": "phase-b-manifest"},
    )
    monkeypatch.setattr(
        phase_c,
        "_phase_c_dir",
        lambda seed: phase_c_dir,
    )
    monkeypatch.setattr(
        phase_c,
        "_phase_b_dir",
        lambda seed: phase_b_dir,
    )

    seed_core = {
        "schema_version": 1,
        "seed": 0,
        "primary_config_manifest_sha256": "config",
        "phase_a_run_manifest_sha256": "phase-a-manifest",
        "phase_b_seed_manifest_sha256": "phase-b-manifest",
        "arm_summary_sha256": {},
        "lambda_one_predictive_equality": True,
        "adaptive_components_received_boundary": False,
    }

    first_arm = phase_c.ARM_NAMES[0]
    arm_manifest_core = {
        "schema_version": 1,
        "seed": 0,
        "arm": first_arm,
        "maintenance_summary": {"opportunity_count": 0},
    }
    arm_dir = phase_b_dir / first_arm
    arm_dir.mkdir()
    arm_manifest_sha = _write_hashed_json(
        arm_dir / "arm_manifest.json",
        arm_manifest_core,
        "manifest_sha256",
    )
    phase_b_seed_core = {
        "arms": {
            first_arm: {
                "path": f"{first_arm}/arm_manifest.json",
                "manifest_sha256": arm_manifest_sha,
            }
        }
    }
    write_json_new(
        phase_b_dir / "phase_b_manifest.json",
        phase_b_seed_core,
    )

    summary_core = {
        "seed": 0,
        "arm": first_arm,
        "primary_config_manifest_sha256": "config",
        "phase_b_arm_manifest_sha256": arm_manifest_sha,
        "shared_identity_sha256": "forged-shared",
        "maintenance_summary": {"opportunity_count": 0},
        "prediction_trace": {
            "path": "unused.jsonl.gz",
            "row_count": 2,
            "sha256": "unused",
            "canonical_jsonl_sha256": "unused",
        },
    }
    summary_sha = _write_hashed_json(
        phase_c_dir / f"{first_arm}_evaluation.json",
        summary_core,
        "summary_sha256",
    )
    seed_core["arm_summary_sha256"][first_arm] = summary_sha
    _write_hashed_json(
        phase_c_dir / "phase_c_seed_manifest.json",
        seed_core,
        "manifest_sha256",
    )

    with pytest.raises(ValueError, match="verified Phase A"):
        phase_c.verify_phase_c_seed(0)



def test_primary_config_freeze_commit_is_parent_bound_and_config_only(
    monkeypatch,
    tmp_path: Path,
) -> None:
    config = {
        "implementation_ready": {
            "prepared_from_git_commit": "source-head",
        }
    }

    def valid_git(*args, **kwargs):
        if args[:2] == ("rev-parse", "HEAD^"):
            return "source-head"
        if args[:4] == (
            "diff-tree",
            "--no-commit-id",
            "--name-only",
            "-r",
        ):
            return "data/manifests/cd_primary_run_config_v1.json"
        raise AssertionError(args)

    monkeypatch.setattr(primary_config, "_git_output", valid_git)
    primary_config._require_config_only_freeze_commit(
        config,
        project_root=tmp_path,
    )

    def wrong_parent(*args, **kwargs):
        if args[:2] == ("rev-parse", "HEAD^"):
            return "different-parent"
        raise AssertionError(args)

    monkeypatch.setattr(primary_config, "_git_output", wrong_parent)
    with pytest.raises(RuntimeError, match="parent differs"):
        primary_config._require_config_only_freeze_commit(
            config,
            project_root=tmp_path,
        )

    def extra_file(*args, **kwargs):
        if args[:2] == ("rev-parse", "HEAD^"):
            return "source-head"
        if args[:4] == (
            "diff-tree",
            "--no-commit-id",
            "--name-only",
            "-r",
        ):
            return (
                "data/manifests/cd_primary_run_config_v1.json\n"
                "METHODOLOGY_LEDGER.md"
            )
        raise AssertionError(args)

    monkeypatch.setattr(primary_config, "_git_output", extra_file)
    with pytest.raises(RuntimeError, match="exactly one file"):
        primary_config._require_config_only_freeze_commit(
            config,
            project_root=tmp_path,
        )



def test_phase_c_read_jsonl_dependency_is_bound_at_module_import() -> None:
    assert callable(phase_c.read_jsonl)


def test_corrected_phase_c_output_tree_preserves_failed_v1_tree() -> None:
    failed = correction.FAILED_PHASE_C_V1_DIR
    corrected = (
        primary_config.PRIMARY_OUTPUT_ROOT
        / correction.CORRECTED_PHASE_C_SUBDIR
        / "seed-0"
    )
    assert failed != corrected
    assert failed.parent.name == "phase_c_offline_evaluation"
    assert corrected.parent.name == "phase_c_offline_evaluation_v1_1"


def test_failed_phase_c_identity_accepts_only_preserved_attempt_and_failure(
    tmp_path: Path,
) -> None:
    root = (
        tmp_path
        / "artifacts"
        / "cd_primary_v1"
        / "phase_c_offline_evaluation"
        / "seed-0"
    )
    root.mkdir(parents=True)
    write_json_new(
        root / "attempt.json",
        {
            "seed": 0,
            "primary_config_manifest_sha256": (
                correction.PARENT_PRIMARY_CONFIG_MANIFEST_SHA256
            ),
            "phase": "offline_boundary_aware_evaluation",
            "adaptive_components_received_boundary": False,
        },
    )
    write_json_new(
        root / "failure.json",
        {
            "seed": 0,
            "exception_type": "NameError",
            "message": "name 'read_jsonl' is not defined",
            "phase": "offline_boundary_aware_evaluation",
            "adaptive_components_received_boundary": False,
        },
    )

    identity = correction._failed_attempt_identity(project_root=tmp_path)
    assert identity["successful_scoring_artifacts_present"] is False
    assert identity["entries"] == ["attempt.json", "failure.json"]
    assert identity["exception_type"] == "NameError"

    (root / "c_frozen_symbolic_evaluation.json").write_text(
        "{}",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="exactly the preserved"):
        correction._failed_attempt_identity(project_root=tmp_path)


def test_correction_rejects_any_frozen_scientific_block_change() -> None:
    parent = {
        key: {"identity": key}
        for key in correction.FROZEN_SCIENTIFIC_BLOCKS
    }
    accepted = {key: dict(value) for key, value in parent.items()}
    correction._verify_frozen_scientific_blocks(accepted, parent)

    mutated = {key: dict(value) for key, value in parent.items()}
    mutated["fusion"] = {"identity": "changed"}
    with pytest.raises(ValueError, match="Scientific block changed"):
        correction._verify_frozen_scientific_blocks(mutated, parent)


def test_phase_a_verifier_uses_explicit_upstream_artifact_config(
    monkeypatch,
    tmp_path: Path,
) -> None:
    # The explicit-config path must not consult the current execution-config
    # gate. The remaining artifact reads are intentionally stopped early.
    monkeypatch.setattr(
        phase_a,
        "verify_primary_run_config_for_execution",
        lambda: (_ for _ in ()).throw(
            AssertionError("current execution config must not be consulted")
        ),
    )
    monkeypatch.setattr(phase_a, "_seed_dir", lambda seed: tmp_path)
    config = {
        "manifest_sha256": "correction",
        "upstream_artifact_config_manifest_sha256": "parent",
        "scenario": {"stream_rows": 138530},
    }
    manifest = {
        "seed": 0,
        "status": "complete_unscored_shared_trajectory",
        "manifest_sha256": "not-used-before-file-check",
        "scenario_identity": {
            "primary_config_manifest_sha256": "parent",
            "adaptive_runner_received_boundary_metadata": False,
        },
    }
    (tmp_path / "run_manifest.json").write_text(
        json.dumps(manifest),
        encoding="utf-8",
    )
    monkeypatch.setattr(phase_a, "_verify_run_manifest_hash", lambda _: None)
    monkeypatch.setattr(
        phase_a,
        "verify_manifest_files",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            RuntimeError("explicit-config-path-reached")
        ),
    )
    with pytest.raises(RuntimeError, match="explicit-config-path-reached"):
        phase_a.verify_phase_a_seed(0, config=config)


def test_root_runner_exposes_versioned_phase_c_correction_prepare() -> None:
    text = (primary_config.PROJECT_ROOT / "run.py").read_text(
        encoding="utf-8"
    )
    assert '"cd-primary-correction-prepare"' in text
    assert "run_cd_primary_correction_prepare" in text
