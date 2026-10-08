from __future__ import annotations

import ast
import gzip
import inspect
import json
from pathlib import Path

import numpy as np
import pytest
import torch

import concept_drift_ids.cd_primary_config as primary_config
import concept_drift_ids.cd_primary_export as primary_export
import concept_drift_ids.cd_primary_phase_a as phase_a
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
            "sha256": "raw",
            "normalized_text_sha256": "text",
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
