from __future__ import annotations

import hashlib
import json
import platform
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

MANIFEST_PATH = PROJECT_ROOT / "data" / "manifests" / "sudden_benign_v1.json"
SCENARIO_SOURCE_PATH = (
    PROJECT_ROOT / "src" / "concept_drift_ids" / "scenario_manifest.py"
)
REQUIREMENTS_LOCK_PATH = PROJECT_ROOT / "requirements-lock.txt"

EXPECTED_RAW_MANIFEST_CANONICAL_SHA256 = (
    "ef1f58af1192091fdf1037edd3a2af6770dad6f0f731ac61cceb007c0cafd8ea"
)
EXPECTED_POST_BENIGN_SOURCE_ROW_ID_SHA256 = (
    "2ab5636a81923eae27faa0eac8de4dd8b55af9fb991bf0ddfdf5419e69c017c9"
)
EXPECTED_POST_BENIGN_TEMPLATE_SLOT_SHA256 = (
    "e393262d5ba7f02dd167aee8575e4980fa108b9471cef8034bb069a1340f5527"
)
EXPECTED_POST_BENIGN_MAPPING_SHA256 = (
    "027112a593a9e6c28720e8393590110f00e8337680f88965fee1d3dc479462ad"
)


def load_manifest() -> dict:
    if not MANIFEST_PATH.exists():
        raise AssertionError(
            "Scenario manifest does not exist. Run scenario_manifest.py first."
        )

    with MANIFEST_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as file:
        while True:
            chunk = file.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)

    return digest.hexdigest()


def sha256_normalized_text(path: Path) -> str:
    """
    Hash text content in a portable canonical form.

    Accept UTF-8 (with or without BOM) and BOM-marked UTF-16, then
    normalize line endings to LF and hash the canonical UTF-8 bytes.
    This keeps the semantic lock-file hash stable across common Windows
    text encodings without changing any dependency versions.
    """
    raw = path.read_bytes()

    if raw.startswith(b"\xef\xbb\xbf"):
        text = raw.decode("utf-8-sig")
    elif raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        text = raw.decode("utf-16")
    else:
        text = raw.decode("utf-8")

    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def sha256_conflict_projection(path: Path) -> str:
    import pandas as pd

    frame = pd.read_csv(
        path,
        usecols=["partition", "Label", "exact_conflict_group_id"],
        low_memory=False,
    )
    digest = hashlib.sha256()
    for row in frame.itertuples(index=False, name=None):
        partition, label, group_id = row
        digest.update(
            f"{partition}\t{label}\t{int(group_id)}\n".encode("utf-8")
        )
    return digest.hexdigest()


def sha256_canonical_json(path: Path) -> str:
    with path.open("r", encoding="utf-8") as file:
        payload = json.load(file)

    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")

    return hashlib.sha256(canonical).hexdigest()


def project_path(relative_path: str) -> Path:
    return PROJECT_ROOT / Path(relative_path)


def test_scenario_identity_and_target_mapping() -> None:
    manifest = load_manifest()

    assert manifest["manifest_format_version"] == 1
    assert manifest["scenario_id"] == "cicids2017_sudden_benign_v1"
    assert manifest["scenario_version"] == 1
    assert manifest["dataset"] == "CICIDS2017"
    assert manifest["task"] == "binary_intrusion_detection"
    assert manifest["binary_target_mapping"] == {
        "BENIGN": 0,
        "all_other_labels": 1,
    }


def test_environment_is_frozen_and_current() -> None:
    manifest = load_manifest()
    environment = manifest["environment"]

    assert environment["python_version"] == "3.11.9"
    assert platform.python_version() == "3.11.9"

    assert environment["requirements_lock_file"] == "requirements-lock.txt"
    assert REQUIREMENTS_LOCK_PATH.exists()

    assert (
        sha256_file(REQUIREMENTS_LOCK_PATH)
        == environment["requirements_lock_sha256"]
    )
    assert (
        sha256_normalized_text(REQUIREMENTS_LOCK_PATH)
        == environment["requirements_lock_normalized_text_sha256"]
    )


def test_generator_is_frozen() -> None:
    manifest = load_manifest()
    generator = manifest["generator"]

    assert generator["file"] == "src/concept_drift_ids/scenario_manifest.py"
    assert SCENARIO_SOURCE_PATH.exists()
    assert (
        sha256_normalized_text(SCENARIO_SOURCE_PATH)
        == generator["normalized_text_sha256"]
    )


def test_provenance_files_still_match_frozen_manifest() -> None:
    manifest = load_manifest()
    provenance = manifest["provenance"]

    raw_manifest_path = project_path(provenance["raw_manifest_file"])
    preprocessing_manifest_path = project_path(
        provenance["preprocessing_manifest_file"]
    )
    conflict_file_path = project_path(provenance["exact_conflict_file"])

    assert raw_manifest_path.exists()
    assert preprocessing_manifest_path.exists()
    assert conflict_file_path.exists()

    assert (
        sha256_canonical_json(raw_manifest_path)
        == provenance["raw_manifest_canonical_sha256"]
    )
    assert (
        provenance["raw_manifest_canonical_sha256"]
        == EXPECTED_RAW_MANIFEST_CANONICAL_SHA256
    )

    assert (
        sha256_canonical_json(preprocessing_manifest_path)
        == provenance["preprocessing_manifest_canonical_sha256"]
    )

    assert (
        sha256_conflict_projection(conflict_file_path)
        == provenance["exact_conflict_projection_sha256"]
    )
    assert provenance["raw_dataset_total_rows"] == 2_830_743


def test_feature_schema_is_frozen() -> None:
    manifest = load_manifest()
    schema = manifest["feature_schema"]

    assert schema["model_feature_count"] == 77
    assert len(schema["feature_columns"]) == 77
    assert len(set(schema["feature_columns"])) == 77

    forbidden = {"Label", "source_file", "source_order", "row_in_source"}
    assert forbidden.isdisjoint(schema["feature_columns"])


def test_chronology_and_construction_claims_are_conservative() -> None:
    manifest = load_manifest()

    chronology = manifest["chronology"]
    assert chronology["type"] == "pseudo-chronological"
    assert chronology["timestamps_available"] is False

    construction = manifest["construction"]
    assert construction["type"] == "controlled_synthetic_composite"
    assert construction["drift_type"] == "benign_source_regime_covariate_shift"
    assert construction["natural_production_drift_claim"] is False


def test_partition_boundaries_are_frozen_and_contiguous() -> None:
    manifest = load_manifest()
    partitions = manifest["partitions"]

    training_components = partitions["training"]["components"]
    monday, tuesday, train_wednesday = training_components

    assert monday == {
        "source_file": "Monday-WorkingHours.pcap_ISCX.csv",
        "source_order": 0,
        "row_start_inclusive": 0,
        "row_end_exclusive": 529_918,
    }
    assert tuesday == {
        "source_file": "Tuesday-WorkingHours.pcap_ISCX.csv",
        "source_order": 1,
        "row_start_inclusive": 0,
        "row_end_exclusive": 445_909,
    }

    development = partitions["development"]
    pre_drift = partitions["pre_drift"]
    post_template = partitions["post_drift"]["template"]

    assert train_wednesday["source_file"] == "Wednesday-workingHours.pcap_ISCX.csv"
    assert train_wednesday["source_order"] == 2
    assert train_wednesday["row_start_inclusive"] == 0
    assert train_wednesday["row_end_exclusive"] == 346_352

    assert development["row_start_inclusive"] == 346_352
    assert development["row_end_exclusive"] == 554_162

    assert pre_drift["row_start_inclusive"] == 554_162
    assert pre_drift["row_end_exclusive"] == 623_433

    assert post_template["row_start_inclusive"] == 623_433
    assert post_template["row_end_exclusive"] == 692_703

    assert train_wednesday["row_end_exclusive"] == development["row_start_inclusive"]
    assert development["row_end_exclusive"] == pre_drift["row_start_inclusive"]
    assert pre_drift["row_end_exclusive"] == post_template["row_start_inclusive"]


def test_partition_sizes_and_binary_counts() -> None:
    manifest = load_manifest()
    partitions = manifest["partitions"]

    expected = {
        "training": {"rows": 1_322_179, "benign": 1_064_858, "attack": 257_321},
        "development": {"rows": 207_810, "benign": 205_797, "attack": 2_013},
        "pre_drift": {"rows": 69_260, "benign": 65_671, "attack": 3_589},
        "post_drift": {"rows": 69_270, "benign": 65_697, "attack": 3_573},
    }

    for partition_name, expected_counts in expected.items():
        partition = partitions[partition_name]
        binary = partition["binary_counts"]

        assert partition["rows"] == expected_counts["rows"]
        assert binary["total"] == expected_counts["rows"]
        assert binary["benign"] == expected_counts["benign"]
        assert binary["attack"] == expected_counts["attack"]

    assert partitions["pre_drift"]["excluded_labels"] == {"Heartbleed": 11}


def test_exact_label_counts_are_frozen() -> None:
    manifest = load_manifest()
    partitions = manifest["partitions"]

    assert partitions["training"]["label_counts"] == {
        "BENIGN": 1_064_858,
        "DoS GoldenEye": 1_118,
        "DoS Hulk": 231_073,
        "DoS Slowhttptest": 5_499,
        "DoS slowloris": 5_796,
        "FTP-Patator": 7_938,
        "SSH-Patator": 5_897,
    }
    assert partitions["development"]["label_counts"] == {
        "BENIGN": 205_797,
        "DoS GoldenEye": 2_013,
    }
    assert partitions["pre_drift"]["label_counts"] == {
        "BENIGN": 65_671,
        "DoS GoldenEye": 3_589,
    }
    assert partitions["post_drift"]["label_counts"] == {
        "BENIGN": 65_697,
        "DoS GoldenEye": 3_573,
    }


def test_pre_and_post_attack_family_and_prevalence_match_design() -> None:
    manifest = load_manifest()

    pre = manifest["partitions"]["pre_drift"]
    post = manifest["partitions"]["post_drift"]

    assert set(pre["label_counts"]) == {"BENIGN", "DoS GoldenEye"}
    assert set(post["label_counts"]) == {"BENIGN", "DoS GoldenEye"}

    pre_rate = pre["binary_counts"]["attack"] / pre["binary_counts"]["total"]
    post_rate = post["binary_counts"]["attack"] / post["binary_counts"]["total"]

    # Absolute difference below 0.1 percentage point.
    assert abs(pre_rate - post_rate) < 0.001


def test_post_benign_selection_and_mapping_are_frozen() -> None:
    manifest = load_manifest()
    replacement = manifest["partitions"]["post_drift"]["benign_replacement"]

    assert replacement["source_file"] == (
        "Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv"
    )
    assert replacement["source_order"] == 3
    assert replacement["eligible_label"] == "BENIGN"
    assert replacement["eligible_rows"] == 168_186
    assert replacement["selected_rows"] == 65_697

    assert (
        replacement["selected_source_row_id_sha256"]
        == EXPECTED_POST_BENIGN_SOURCE_ROW_ID_SHA256
    )
    assert (
        replacement["template_benign_slot_row_id_sha256"]
        == EXPECTED_POST_BENIGN_TEMPLATE_SLOT_SHA256
    )
    assert (
        replacement["slot_to_source_row_id_mapping_sha256"]
        == EXPECTED_POST_BENIGN_MAPPING_SHA256
    )

    assert replacement["first_selected_source_row"] == 0
    assert replacement["last_selected_source_row"] == 170_363
    assert replacement["first_template_benign_slot"] == 623_433
    assert replacement["last_template_benign_slot"] == 692_702


def test_conflict_policy_avoids_future_leakage() -> None:
    manifest = load_manifest()
    policy = manifest["data_quality_policy"][
        "representation_level_label_conflicts"
    ]
    diagnostics = policy["diagnostics"]

    assert policy["primary_policy"] == "retain_original_rows_and_labels"
    assert diagnostics["total_conflict_patterns"] == 78
    assert diagnostics["total_conflict_rows"] == 4_877
    assert diagnostics["training_internal_conflict_patterns"] == 41
    assert diagnostics["training_internal_conflict_rows"] == 4_322
    assert diagnostics["training_internal_conflict_label_counts"] == {
        "BENIGN": 46,
        "DoS Hulk": 4_276,
    }
    assert diagnostics["future_only_conflict_patterns"] == 37
    assert diagnostics["future_only_training_rows"] == 513
    assert diagnostics["future_only_future_rows"] == 37
    assert diagnostics["future_only_future_partition_label_counts"] == {
        "development|BENIGN": 34,
        "post_benign|BENIGN": 3,
    }


def test_duplicate_and_future_information_policies_are_frozen() -> None:
    manifest = load_manifest()
    policy = manifest["data_quality_policy"]

    duplicates = policy["duplicate_rows"]
    assert duplicates["primary_policy"] == "retain"
    assert duplicates["drift_detector_stream_policy"] == "full_stream_including_repeats"
    assert duplicates["planned_sensitivity_analysis"] == "deduplicated_training"

    conflicts = policy["representation_level_label_conflicts"]
    assert conflicts["planned_sensitivity_analysis"] == (
        "training_internal_conflict_removal"
    )

    assert "Future development or post-drift labels must never alter historical" in (
        policy["future_information_policy"]
    )
