# Pre-Stage 3 Readiness and Decision Record

**Status:** COMPLETE  
**Frozen on:** 6 October 2026  
**Applies to:** `cicids2017_sudden_benign_v1` and the first Stage-3 implementation pass

This record closes Pre-Stage 3. It freezes the remaining implementation decisions that were intentionally left unresolved until the actual repository, Stage-1/Stage-2 code, manifests, dependency lock, and governing doctrine could be inspected.

## 1. Authority hierarchy

When sources conflict, use this order:

1. `MAIN - Concept_Drift_NIDS_Research_Gap_Doctrine.docx`
2. The two earlier guiding research/design Word documents where they do not conflict with the doctrine
3. Frozen Stage-1 and Stage-2 manifests/artifacts and their regression invariants
4. The reconciled Pre-Stage-3 / Stage-3 implementation plan
5. Implementation convenience

The repository copy `RESEARCH_DOCTRINE.md` is a convenience pointer and preserves the exact governing research-gap wording. It does not replace the source Word doctrine.

## 2. Stage-1 / Stage-2 reopening rule

Stage 1 and Stage 2 are treated as complete and frozen.

Do not rerun exploratory raw-data profiling, KS studies, duplicate discovery, conflict discovery, or redesign `sudden_benign_v1` unless a concrete inconsistency is discovered during implementation.

The pushed Stage-2 generator currently matches the normalized SHA-256 frozen in `sudden_benign_v1.json`. The manifest, scenario boundaries, counts, feature schema, replacement hashes, duplicate policy, contradiction policy, chronology wording, and future-information policy were inspected and remain consistent with the frozen contract.

The existing 13 Stage-2 regression tests remain authoritative. They intentionally require Python 3.11.9 and must not be weakened merely to run in a different interpreter.

## 3. Environment contract

- Python: **3.11.9 exactly**
- Dependency versions: **exactly those in `requirements-lock.txt`**
- Do not change package versions to solve implementation problems.
- The BOM/encoding portability logic already used for the lock-file semantic hash remains authoritative.
- Repository-relative paths stored in manifests use POSIX separators.

## 4. Frozen 77-feature / metadata / target contract

Stage 3 consumes the structurally preprocessed Stage-1 representation.

- Model features are the exact ordered 77 names frozen in `sudden_benign_v1.json`.
- No broad new numeric coercion is permitted in Stage 3.
- Reuse the Stage-1 structural behavior: validated numeric features, known label normalization, duplicate `Fwd Header Length` verification/removal, and infinity-to-NaN conversion.
- `source_file`, `source_order`, `row_in_source`, synthetic-stream provenance fields, and `Label` are metadata/target information and never enter `X`.
- Binary target: `BENIGN -> 0`; every other retained label -> `1`.
- Original multiclass `Label` remains available as metadata.

## 5. Synthetic post-drift provenance contract

For every reconstructed row, distinguish **where the observation came from** from **where it occurs in the synthetic stream**.

The Stage-3 provenance representation is frozen as:

- `scenario_partition`
- `scenario_row`
- `source_file`
- `source_order`
- `row_in_source`
- `template_source_file`
- `template_source_order`
- `template_row_in_source`
- `synthetic_replacement`

For Thursday BENIGN replacements in the post-drift partition:

- the `source_*` fields describe the real Thursday source observation;
- the `template_*` fields describe the Wednesday post-template slot occupied by that observation;
- the two identities must never be overwritten into one another.

For non-synthetic rows, source and template identities coincide.

## 6. Initial imputation policy

The initial missing-value transformer is frozen as:

`sklearn.impute.SimpleImputer(strategy="median")`

Rules:

- Fit **once on the frozen training partition only**.
- Before fitting, fail loudly if any of the 77 training features is entirely missing.
- Do not drop rows because of missing values.
- Do not fit or partially fit on development, pre-drift, or post-drift data.
- Reuse the training-fitted medians unchanged for all four partitions.
- Do not add missingness-indicator features in the primary experiment; the feature dimension remains exactly 77.

## 7. Initial scaler policy

The initial scaler is frozen prospectively as:

`sklearn.preprocessing.StandardScaler(with_mean=True, with_std=True)`

Rationale: the primary neural detector is a compact MLP operating on heterogeneous continuous flow features; StandardScaler is simple, deterministic, invertible for threshold interpretation, available in the locked scikit-learn environment, and introduces no additional model novelty.

Rules:

- Fit only **after median imputation of the frozen training partition**.
- Fit **once on imputed training values only**.
- Apply the fitted mean/scale unchanged to training, development, pre-drift, and post-drift data.
- No `fit`, `fit_transform`, or `partial_fit` is allowed on future partitions.
- Adaptive preprocessing is not part of the core experiment. If later studied, it is a separate sensitivity treatment and must be matched between Systems C and D.

## 8. Shared preprocessing dtype policy

The shared Stage-3 preprocessing representation remains NumPy/pandas **float64**.

- Fitted imputer/scaler statistics are retained in float64.
- Do not make PyTorch dtype part of shared preprocessing.
- Conversion to `torch.float32` occurs only at the PyTorch dataset/tensor boundary for neural-model execution.
- Rule extraction, symbolic processing, and other non-PyTorch consumers receive the same shared transformed representation unless a later explicitly documented component requires a conversion.
- Any conversion must not change feature order or fitted preprocessing state.

## 9. Preprocessing-state persistence convention

Do **not** persist giant transformed train/development/pre/post CSV copies as the primary reproducibility mechanism.

Persist a small, human-readable JSON state artifact at:

`data/manifests/sudden_benign_v1_preprocessing_v1.json`

The artifact must contain at least:

- scenario ID/version and scenario-manifest identity/hash;
- exact ordered 77-feature list;
- frozen training row count and deterministic training-identity description/hash;
- imputer class/configuration and 77 fitted medians;
- scaler class/configuration and fitted `mean_`, `scale_`, `var_`, and relevant sample-count state;
- output dtype policy;
- Python version and dependency-lock provenance;
- preprocessing implementation file/hash;
- explicit statement that development/pre/post did not participate in fitting.

JSON is the authoritative audit artifact. A pickle/joblib object is not required as the source of truth.

## 10. Determinism and leakage acceptance tests

Stage 3A must behaviorally prove the following before any MLP work begins:

- exact four-partition reconstruction from the frozen manifest;
- exact ordered 77-feature matrices;
- exact binary and multiclass counts;
- exact post-drift replacement ordering and frozen mapping hashes;
- no silent row removal beyond the explicitly frozen 11-row Heartbleed exclusion;
- duplicate and representation-level contradiction policies unchanged;
- all transformed feature values finite;
- imputer statistics derive only from training;
- scaler state derives only from imputed training;
- changing development/pre/post values while training is fixed cannot change training medians, scaler state, or transformed training values;
- repeated reconstruction/transformation is deterministic;
- persisted preprocessing-state data agrees with the in-memory fitted state.

Use numerical equivalence/tolerances for floating arrays rather than relying on cross-platform byte hashes of huge transformed matrices.

## 11. Large-artifact policy

Prefer deterministic reconstruction to large intermediate copies.

- Raw files remain source data.
- Stage-1 structurally preprocessed files remain reconstructible.
- Scenario partitions are reconstructed from the frozen manifest.
- Transformed matrices need not be committed.
- Small manifests/state artifacts and tests carry the reproducibility contract.

## 12. System-A boundary

Pre-Stage 3 does **not** freeze System-A architecture/training hyperparameters beyond the already authoritative research constraints:

- compact MLP;
- architecture is not the novelty;
- development data may be used for legitimate model-development choices;
- pre/post evaluation windows must not be used for tuning;
- later stochastic comparisons use prespecified fixed seeds.

Architecture, optimizer, class-imbalance treatment, early stopping, probability calibration, threshold selection, and any bounded hyperparameter search are Stage 3B decisions and must be frozen before untouched pre/post evaluation.

## 13. Stage-3 authorization gate

Pre-Stage 3 is complete.

Stage 3 is authorized to proceed in this order:

1. Stage 3A.1–3A.2: manifest-driven scenario reconstruction and feature/metadata/target contract.
2. Stage 3A.3–3A.6: training-only imputer/scaler state, frozen transformations, provenance artifact, and leakage/determinism tests.
3. **Only after the Stage-3A tests pass:** begin System A.

Do not jump directly to the MLP.

## 14. Research-doctrine guardrails that implementation must preserve

- Primary System C: identical adaptive neural procedure + frozen symbolic rule base `R_0`.
- System D: same neural adaptation + evolved `R_t`.
- The rule-evolution operator must later support both drift-triggered and periodic trigger policies.
- `sudden_benign_v1` is a controlled benign source-regime covariate shift, not natural production concept drift.
- The final paper requires evidence beyond this one scenario.
- Symbolic staleness must be measured before symbolic recovery is claimed.
- Symbolic evolution must be versioned, validated, auditable, and richer than wholesale regeneration.
- Broad “first adaptive/rule-evolving IDS” novelty claims are prohibited.
- The live novelty search must be refreshed at later major milestones and before submission.
