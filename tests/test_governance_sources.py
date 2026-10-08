from concept_drift_ids.governance import (
    CURRENT_GOVERNING_SOURCE_HASHES,
    HISTORICAL_SYSTEM_B_GOVERNING_SOURCE_HASHES,
)


def test_current_governing_source_hashes_are_pinned() -> None:
    assert CURRENT_GOVERNING_SOURCE_HASHES == {
        "MAIN - Concept_Drift_NIDS_Research_Gap_Doctrine.docx": (
            "c3f1fed692ff0478c221925fca5c311380617a993e7ebf0021af2e05a362ab66"
        ),
        "Reconciled_Pre-Stage_3_and_Stage_3_Implementation_Plan.docx": (
            "05378ef14437f037bab0aa77853a16980b4fc60ac303398acc1cc293bdd32bdb"
        ),
    }


def test_historical_system_b_authority_is_preserved() -> None:
    assert HISTORICAL_SYSTEM_B_GOVERNING_SOURCE_HASHES == {
        "MAIN - Concept_Drift_NIDS_Research_Gap_Doctrine.docx": (
            "f0700fc28e5c49ee50a6fab73db870725006ba52541a0d9cf4b285ccbe143a8f"
        ),
        "Reconciled_Pre-Stage_3_and_Stage_3_Implementation_Plan.docx": (
            "83d1e101a525e840a1235743ac5fc050ca560f228df047bee17a84e80cbf3082"
        ),
    }
