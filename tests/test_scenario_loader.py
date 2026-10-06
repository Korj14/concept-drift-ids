from __future__ import annotations

import numpy as np
import pandas as pd

from concept_drift_ids.scenario_loader import (
    PROVENANCE_COLUMNS,
    load_manifest,
    load_partition,
)
from concept_drift_ids.scenario_manifest import (
    sha256_int64_array,
    sha256_int64_pairs,
)


def test_manifest_contract_exposes_exact_ordered_feature_schema() -> None:
    manifest = load_manifest()
    features = manifest["feature_schema"]["feature_columns"]

    assert len(features) == 77
    assert len(set(features)) == 77
    assert manifest["feature_schema"]["model_feature_count"] == 77
    assert {"Label", "source_file", "source_order", "row_in_source"}.isdisjoint(
        features
    )


def test_training_reconstruction_preserves_counts_features_and_order() -> None:
    manifest = load_manifest()
    training = load_partition("training")

    assert len(training.X) == 1_322_179
    assert list(training.X.columns) == manifest["feature_schema"]["feature_columns"]
    assert training.X.shape[1] == 77
    assert {"Label", *PROVENANCE_COLUMNS}.isdisjoint(training.X.columns)

    assert training.labels.value_counts().to_dict() == {
        "BENIGN": 1_064_858,
        "DoS Hulk": 231_073,
        "FTP-Patator": 7_938,
        "SSH-Patator": 5_897,
        "DoS slowloris": 5_796,
        "DoS Slowhttptest": 5_499,
        "DoS GoldenEye": 1_118,
    }
    assert int((training.y == 0).sum()) == 1_064_858
    assert int((training.y == 1).sum()) == 257_321

    provenance = training.provenance
    blocks = [
        (0, 529_918, "Monday-WorkingHours.pcap_ISCX.csv", 0, 529_918),
        (529_918, 975_827, "Tuesday-WorkingHours.pcap_ISCX.csv", 1, 445_909),
        (975_827, 1_322_179, "Wednesday-workingHours.pcap_ISCX.csv", 2, 346_352),
    ]

    for start, end, source_file, source_order, rows in blocks:
        block = provenance.iloc[start:end]
        assert len(block) == rows
        assert (block["source_file"] == source_file).all()
        assert (block["source_order"] == source_order).all()
        np.testing.assert_array_equal(
            block["row_in_source"].to_numpy(dtype=np.int64),
            np.arange(rows, dtype=np.int64),
        )
        assert not block["synthetic_replacement"].any()


def test_development_reconstruction_preserves_source_identity() -> None:
    development = load_partition("development")

    assert len(development.X) == 207_810
    assert development.labels.value_counts().to_dict() == {
        "BENIGN": 205_797,
        "DoS GoldenEye": 2_013,
    }
    assert int((development.y == 0).sum()) == 205_797
    assert int((development.y == 1).sum()) == 2_013

    provenance = development.provenance
    assert (provenance["source_file"] == "Wednesday-workingHours.pcap_ISCX.csv").all()
    np.testing.assert_array_equal(
        provenance["row_in_source"].to_numpy(dtype=np.int64),
        np.arange(346_352, 554_162, dtype=np.int64),
    )
    assert not provenance["synthetic_replacement"].any()
    pd.testing.assert_series_equal(
        provenance["row_in_source"],
        provenance["template_row_in_source"],
        check_names=False,
    )


def test_pre_drift_reconstruction_applies_only_frozen_heartbleed_exclusion() -> None:
    manifest = load_manifest()
    pre = load_partition("pre_drift")

    assert len(pre.X) == 69_260
    assert pre.labels.value_counts().to_dict() == {
        "BENIGN": 65_671,
        "DoS GoldenEye": 3_589,
    }
    assert int((pre.y == 0).sum()) == 65_671
    assert int((pre.y == 1).sum()) == 3_589
    assert "Heartbleed" not in set(pre.labels.astype(str))
    assert manifest["partitions"]["pre_drift"]["excluded_labels"] == {
        "Heartbleed": 11
    }

    provenance = pre.provenance
    assert not provenance["synthetic_replacement"].any()
    assert provenance["template_row_in_source"].is_monotonic_increasing
    assert provenance["template_row_in_source"].min() == 554_162
    assert provenance["template_row_in_source"].max() == 623_432


def test_post_drift_preserves_template_order_and_frozen_mapping() -> None:
    manifest = load_manifest()
    post = load_partition("post_drift")
    replacement = manifest["partitions"]["post_drift"]["benign_replacement"]

    assert len(post.X) == 69_270
    assert post.labels.value_counts().to_dict() == {
        "BENIGN": 65_697,
        "DoS GoldenEye": 3_573,
    }

    provenance = post.provenance
    np.testing.assert_array_equal(
        provenance["template_row_in_source"].to_numpy(dtype=np.int64),
        np.arange(623_433, 692_703, dtype=np.int64),
    )

    replaced_mask = provenance["synthetic_replacement"].to_numpy(dtype=bool)
    assert int(replaced_mask.sum()) == 65_697
    assert int((~replaced_mask).sum()) == 3_573

    replaced = provenance.loc[replaced_mask]
    retained = provenance.loc[~replaced_mask]

    assert (replaced["source_file"] == replacement["source_file"]).all()
    assert (replaced["source_order"] == replacement["source_order"]).all()
    assert (
        replaced["template_source_file"]
        == "Wednesday-workingHours.pcap_ISCX.csv"
    ).all()

    assert (retained["source_file"] == "Wednesday-workingHours.pcap_ISCX.csv").all()
    np.testing.assert_array_equal(
        retained["row_in_source"].to_numpy(dtype=np.int64),
        retained["template_row_in_source"].to_numpy(dtype=np.int64),
    )
    assert (post.labels.loc[~replaced_mask] == "DoS GoldenEye").all()

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


def test_post_drift_reconstruction_is_deterministic() -> None:
    first = load_partition("post_drift")
    second = load_partition("post_drift")

    pd.testing.assert_frame_equal(first.X, second.X, check_exact=True)
    pd.testing.assert_series_equal(first.y, second.y, check_exact=True)
    pd.testing.assert_series_equal(first.labels, second.labels, check_exact=True)
    pd.testing.assert_frame_equal(first.provenance, second.provenance, check_exact=True)
