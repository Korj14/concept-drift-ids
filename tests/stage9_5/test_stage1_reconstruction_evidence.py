from __future__ import annotations

import copy
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pandas as pd
import pytest

import tools.stage9_5.stage1_reconstruction_evidence as stage1


def _write_toy_raw(path: Path) -> None:
    path.write_text(
        " Fwd Header Length, Fwd Header Length, Flow Bytes/s, Label\n"
        "1,1,2.5,BENIGN\n"
        "2,2,Infinity,Web Attack \ufffd XSS\n",
        encoding="utf-8",
    )


def _contract() -> dict[str, Any]:
    return json.loads(stage1.CONTRACT_PATH.read_text(encoding="utf-8"))


def test_historical_source_blob_matches_frozen_contract_and_toy_semantics(
    tmp_path: Path,
) -> None:
    contract = _contract()
    historical = stage1._historical_namespace(contract)
    raw = tmp_path / "toy.csv"
    _write_toy_raw(raw)

    historical_df, historical_report = historical.preprocess_file(raw, 0)
    independent_df, independent_report = stage1._independent_preprocess_file(
        raw,
        0,
    )

    stage1._assert_semantic_equal(historical_df, independent_df)
    assert historical_report == independent_report
    assert list(historical.get_feature_columns(historical_df)) == [
        "Fwd Header Length",
        "Flow Bytes/s",
    ]
    assert independent_df.loc[1, "Label"] == "Web Attack - XSS"
    assert pd.isna(independent_df.loc[1, "Flow Bytes/s"])


def test_historical_source_blob_identity_is_fail_closed() -> None:
    contract = _contract()
    mutated = copy.deepcopy(contract)
    environment = mutated["historical_environment"]
    assert isinstance(environment, dict)
    environment["preprocessing_git_blob_sha1"] = "0" * 40

    with pytest.raises(ValueError, match="Git blob identity mismatch"):
        stage1._historical_namespace(mutated)


def test_semantic_compare_detects_model_feature_tamper(tmp_path: Path) -> None:
    raw = tmp_path / "toy.csv"
    _write_toy_raw(raw)
    independent, _ = stage1._independent_preprocess_file(raw, 0)
    tampered = independent.copy()
    tampered.loc[0, "Flow Bytes/s"] = 999.0

    with pytest.raises(AssertionError):
        stage1._assert_semantic_equal(tampered, independent)


def test_stage1_run_derives_canonical_pass_from_semantic_evidence(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    base_contract = _contract()
    historical = stage1._historical_namespace(base_contract)

    raw_root = tmp_path / "raw"
    raw_root.mkdir()
    filename = "toy.csv"
    raw = raw_root / filename
    _write_toy_raw(raw)

    historical_df, historical_report = historical.preprocess_file(raw, 0)
    feature_columns = list(historical.get_feature_columns(historical_df))
    expected_manifest = stage1._build_preprocessing_manifest(
        reports=[historical_report],
        feature_columns=feature_columns,
    )

    contract = copy.deepcopy(base_contract)
    raw_contract = contract["raw_input_contract"]
    accepted = contract["accepted_stage1_identity"]
    required = contract["required_report"]["required_success_values"]
    assert isinstance(raw_contract, dict)
    assert isinstance(accepted, dict)
    assert isinstance(required, dict)

    raw_contract["required_file_count"] = 1
    raw_contract["exact_file_sha256"] = {
        filename: stage1._sha256_file(raw)
    }
    accepted["model_feature_count"] = len(feature_columns)
    required["raw_file_count_verified"] = 1
    required["interim_table_count_verified"] = 1
    required["preprocessing_manifest_canonical_sha256"] = (
        stage1._canonical_sha256(expected_manifest)
    )

    contract_path = tmp_path / "contract.json"
    contract_path.write_text(
        json.dumps(contract, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    toy_historical = SimpleNamespace(
        EXPECTED_FILES=[filename],
        preprocess_file=historical.preprocess_file,
        get_feature_columns=historical.get_feature_columns,
    )
    monkeypatch.setattr(
        stage1,
        "_verify_environment",
        lambda _: {"python_version": "3.11.9"},
    )
    monkeypatch.setattr(
        stage1,
        "_historical_namespace",
        lambda _: toy_historical,
    )
    monkeypatch.setattr(
        stage1,
        "_verify_raw_manifest",
        lambda _: {"file_order": [filename]},
    )

    report_path = tmp_path / "report.json"
    reconstructed_root = tmp_path / "reconstructed"
    report = stage1.run(
        raw_root=raw_root,
        reconstructed_root=reconstructed_root,
        report_path=report_path,
        contract_path=contract_path,
    )

    assert report["pass"] is True
    assert report["status"] == "pass"
    assert report["raw_file_count_verified"] == 1
    assert report["interim_table_count_verified"] == 1
    assert report["semantic_mismatch_count"] == 0
    assert report["failures"] == []
    assert report["blockers"] == []
    assert (
        report["preprocessing_manifest_canonical_sha256"]
        == required["preprocessing_manifest_canonical_sha256"]
    )

    written = json.loads(report_path.read_text(encoding="utf-8"))
    observed = written.pop("canonical_sha256")
    assert observed == stage1._canonical_sha256(written)


def test_stage1_run_blocks_semantic_tamper(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    contract = _contract()
    historical = stage1._historical_namespace(contract)
    raw_root = tmp_path / "raw"
    raw_root.mkdir()
    filename = "toy.csv"
    raw = raw_root / filename
    _write_toy_raw(raw)

    independent_df, independent_report = stage1._independent_preprocess_file(
        raw,
        0,
    )
    feature_columns = [
        column
        for column in independent_df.columns
        if column not in set(stage1.METADATA_COLUMNS + ["Label"])
    ]
    expected_manifest = stage1._build_preprocessing_manifest(
        reports=[independent_report],
        feature_columns=feature_columns,
    )

    mutated_contract = copy.deepcopy(contract)
    raw_contract = mutated_contract["raw_input_contract"]
    accepted = mutated_contract["accepted_stage1_identity"]
    required = mutated_contract["required_report"]["required_success_values"]
    assert isinstance(raw_contract, dict)
    assert isinstance(accepted, dict)
    assert isinstance(required, dict)
    raw_contract["required_file_count"] = 1
    raw_contract["exact_file_sha256"] = {
        filename: stage1._sha256_file(raw)
    }
    accepted["model_feature_count"] = len(feature_columns)
    required["raw_file_count_verified"] = 1
    required["interim_table_count_verified"] = 1
    required["preprocessing_manifest_canonical_sha256"] = (
        stage1._canonical_sha256(expected_manifest)
    )

    contract_path = tmp_path / "contract.json"
    contract_path.write_text(
        json.dumps(mutated_contract),
        encoding="utf-8",
    )

    def tampered_preprocess(
        path: Path,
        source_order: int,
    ) -> tuple[pd.DataFrame, dict[str, Any]]:
        frame, report = historical.preprocess_file(path, source_order)
        frame.loc[0, "Flow Bytes/s"] = 777.0
        return frame, report

    toy_historical = SimpleNamespace(
        EXPECTED_FILES=[filename],
        preprocess_file=tampered_preprocess,
        get_feature_columns=historical.get_feature_columns,
    )
    monkeypatch.setattr(
        stage1,
        "_verify_environment",
        lambda _: {"python_version": "3.11.9"},
    )
    monkeypatch.setattr(
        stage1,
        "_historical_namespace",
        lambda _: toy_historical,
    )
    monkeypatch.setattr(
        stage1,
        "_verify_raw_manifest",
        lambda _: {"file_order": [filename]},
    )

    report = stage1.run(
        raw_root=raw_root,
        reconstructed_root=tmp_path / "reconstructed",
        report_path=tmp_path / "report.json",
        contract_path=contract_path,
    )

    assert report["pass"] is False
    assert report["semantic_mismatch_count"] == 1
    assert any(
        str(item).startswith(f"table_verification:{filename}:AssertionError")
        for item in report["failures"]
    )
