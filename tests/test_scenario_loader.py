from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from concept_drift_ids.scenario_loader import (
    PROVENANCE_COLUMNS,
    load_manifest,
    load_partition,
    load_scenario,
)
from concept_drift_ids.scenario_manifest import (
    sha256_int64_array,
    sha256_int64_pairs,
)


@pytest.fixture(scope="session")
def scenario():
    return load_scenario()


def test_manifest_contract_exposes_exact_ordered_feature_schema() -> None:
    manifest = load_manifest()
    feature_columns = manifest["feature_schema"]["feature_columns"]

    assert len(feature_columns) == 77
    assert len(set(feature_columns)) == 77
    assert manifest["feature_schema"]["model_feature_count"] == 77
    assert {"Label", "source_file", "source_order", "row_in_source"}.isdisjoint(
        feature_columns
    )


def test_reconstructed_partition_sizes_and_binary_counts(scenario) -> None:
    expected = {
        "training": (1_322_179, 1_064_858, 257_321),
        "development": (207_810, 205_797, 2_013),
        "pre_drift": (69_260, 65_671, 3_589),
        "post_drift": (69_270, 65_697, 3_573),
    }

    for name, (rows, benign, attack) in expected.items():
        partition = scenario.partition(name)
        assert len(partition.X) == rows
        assert len(partition.y) == rows
        assert int((partition.y == 0).sum()) == benign
        assert int((partition.y == 1).sum()) == attack


def test_original_multiclass_labels_are_preserved(scenario) -> None:
    assert scenario.training.labels.value_counts().to_dict() == {
        "BENIGN": 1_064_858,
        "DoS Hulk": 231_073,
        "FTP-Patator": 7_938,
        "SSH-Patator": 5_897,
        "DoS slowloris": 5_796,
        "DoS Slowhttptest": 5_499,
        "DoS GoldenEye": 1_118,
    }
    assert scenario.development.labels.value_counts().to_dict() == {
        "BENIGN": 205_797,
        "DoS GoldenEye": 2_013,
    }
    assert scenario.pre_drift.labels.value_counts().to_dict() == {
        "BENIGN": 65_671,
        "DoS GoldenEye": 3_589,
    }
    assert scenario.post_drift.labels.value_counts().to_dict() == {
        "BENIGN": 65_697,
        "DoS GoldenEye": 3_573,
    }


def test_model_matrices_use_only_the_frozen_77_features(scenario) -> None:
    expected_features = list(scenario.feature_columns)
    forbidden = {"Label", *PROVENANCE_COLUMNS}

    for name in ("training", "development", "pre_drift", "post_drift"):
        partition = scenario.partition(name)
        assert list(partition.X.columns) == expected_features
        assert partition.X.shape[1] == 77
        assert forbidden.isdisjoint(partition.X.columns)


def test_training_provenance_preserves_frozen_component_order(scenario) -> None:
    provenance = scenario.training.provenance

    blocks = [
        (0, 529_918, "Monday-WorkingHours.pcap_ISCX.csv", 0, 529_918),
        (529_918, 975_827, "Tuesday-WorkingHours.pcap_ISCX.csv", 1, 445_909),
        (975_827, 1_322_179, "Wednesday-workingHours.pcap_ISCX.csv", 2, 346_352),
    ]

    for start, end, source_file, source_order, source_rows in blocks:
        block = provenance.iloc[start:end]
        assert len(block) == source_rows
        assert (block["source_file"] == source_file).all()
        assert (block["source_order"] == source_order).all()
        np.testing.assert_array_equal(
            block["row_in_source"].to_numpy(dtype=np.int64),
            np.arange(source_rows, dtype=np.int64),
        )
        assert not block["synthetic_replacement"].any()
        np.testing.assert_array_equal(
            block["row_in_source"].to_numpy(dtype=np.int64),
            block["template_row_in_source"].to_numpy(dtype=np.int64),
        )


def test_non_synthetic_partitions_preserve_source_identity_and_order(scenario) -> None:
    development = scenario.development.provenance
    assert (development["source_file"] == "Wednesday-workingHours.pcap_ISCX.csv").all()
    np.testing.assert_array_equal(
        development["row_in_source"].to_numpy(dtype=np.int64),
        np.arange(346_352, 554_162, dtype=np.int64),
    )
    assert not development["synthetic_replacement"].any()
    pd.testing.assert_series_equal(
        development["row_in_source"],
        development["template_row_in_source"],
        check_names=False,
    )

    pre = scenario.pre_drift.provenance
    assert not pre["synthetic_replacement"].any()
    assert len(pre) == 69_260
    assert pre["template_row_in_source"].is_monotonic_increasing
    assert pre["template_row_in_source"].min() == 554_162
    assert pre["template_row_in_source"].max() == 623_432


def test_post_drift_preserves_template_order_and_distinguishes_source_identity(scenario) -> None:
    post = scenario.post_drift
    provenance = post.provenance
    manifest = scenario.manifest
    replacement = manifest["partitions"]["post_drift"]["benign_replacement"]

    np.testing.assert_array_equal(
        provenance["template_row_in_source"].to_numpy(dtype=np.int64),
        np.arange(623_433, 692_703, dtype=np.int64),
    )

    replacement_mask = provenance["synthetic_replacement"].to_numpy(dtype=bool)
    assert int(replacement_mask.sum()) == 65_697
    assert int((~replacement_mask).sum()) == 3_573

    replaced = provenance.loc[replacement_mask]
    retained = provenance.loc[~replacement_mask]

    assert (replaced["source_file"] == replacement["source_file"]).all()
    assert (replaced["source_order"] == replacement["source_order"]).all()
    assert (
        replaced["template_source_file"]
        == "Wednesday-workingHours.pcap_ISCX.csv"
    ).all()

    assert (retained["source_file"] == "Wednesday-workingHours.pcap_ISCX.csv").all()
    assert (
        retained["row_in_source"].to_numpy(dtype=np.int64)
        == retained["template_row_in_source"].to_numpy(dtype=np.int64)
    ).all()
    assert (post.labels.loc[~replacement_mask] == "DoS GoldenEye").all()

    selected_ids = replaced["row_in_source"].to_numpy(dtype=np.int64)
    template_ids = replaced["template_row_in_source"].to_numpy(dtype=np.int64)

    assert sha256_int64_array(selected_ids) == replacement[
        "selected_source_row_id_sha256"
    ]
    assert sha256_int64_array(template_ids) == replacement[
        "template_benign_slot_row_id_sha256"
    ]
    assert sha256_int64_pairs(template_ids, selected_ids) == replacement[
        "slot_to_source_row_id_mapping_sha256"
    ]


def test_scenario_row_is_contiguous_and_no_rows_are_silently_removed(scenario) -> None:
    for name in ("training", "development", "pre_drift", "post_drift"):
        partition = scenario.partition(name)
        np.testing.assert_array_equal(
            partition.provenance["scenario_row"].to_numpy(dtype=np.int64),
            np.arange(len(partition.X), dtype=np.int64),
        )

    assert "Heartbleed" not in set(scenario.pre_drift.labels.astype(str))
    assert scenario.manifest["partitions"]["pre_drift"]["excluded_labels"] == {
        "Heartbleed": 11
    }


def test_post_drift_reconstruction_is_deterministic() -> None:
    first = load_partition("post_drift")
    second = load_partition("post_drift")

    pd.testing.assert_frame_equal(first.X, second.X, check_exact=True)
    pd.testing.assert_series_equal(first.y, second.y, check_exact=True)
    pd.testing.assert_series_equal(first.labels, second.labels, check_exact=True)
    pd.testing.assert_frame_equal(first.provenance, second.provenance, check_exact=True)
