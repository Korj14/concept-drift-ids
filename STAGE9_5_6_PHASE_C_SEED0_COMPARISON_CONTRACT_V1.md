# Stage 9.5-6 Corrected Phase-C Seed-0 Comparison Contract v1

**Status:** PROSPECTIVELY FROZEN / NO COMPARATOR IMPLEMENTATION IN THIS TRANCHE  
**Machine contract:** `data/manifests/stage9_5_6_phase_c_seed0_comparison_v1.json`  
**Scope:** corrected Phase-C v1.1, seed 0 only

## Purpose and authority

This contract freezes how accepted and fresh corrected Phase-C seed-0 outputs
must be compared during Stage 9.5-6 historical replay.

The rules are derived only from pre-outcome authorities:

- historical corrected Phase-C source at
  `79ddc4c6d6dea52c7cabc55a6d082448fc24fcf9`;
- the v1.1 correction config with manifest SHA-256
  `d380fce5f9db8f0b639dc999298a263b10a10a3d02e35def226a121d098e2222`;
- `STAGE8_PHASE_C_V1_1_CORRECTION.md`;
- the already-frozen Stage-9.5-6 replay-equivalence protocol v1.1;
- the already-frozen Phase-B projection contracts.

No accepted corrected Phase-C result value is used to define an exclusion or
tolerance. No new diagnostic exclusion is introduced.

## Dependency gate

Corrected Phase-C seed-0 output comparison is meaningful only after:

1. correction-config preconditions pass;
2. the original failed-v1 seed-0 `attempt.json` / `failure.json` lineage is
   preserved;
3. Phase-A replay comparison passes;
4. Phase-B replay comparison passes;
5. seed-0 Phase-A shared identity is exact;
6. seed-0 Phase-B has exactly the three frozen arms.

Phase A and Phase B are not re-executed under the v1.1 correction.

## Successful corrected output surface

A successful corrected seed-0 output directory is frozen to exactly:

- `attempt.json`;
- `c_frozen_symbolic_evaluation.json`;
- `c_frozen_symbolic_prediction_trace.jsonl.gz`;
- `d_drift_evaluation.json`;
- `d_drift_prediction_trace.jsonl.gz`;
- `d_periodic_evaluation.json`;
- `d_periodic_prediction_trace.jsonl.gz`;
- `phase_c_seed_manifest.json`.

A successful run must not contain `failure.json` or additional scored
artifacts.

## Prediction-trace identity

For every arm, the prediction trace path is exactly
`<arm>_prediction_trace.jsonl.gz`.

The historical source writes deterministic gzip with an empty filename,
compression level 9, and `mtime=0`, and writes canonical JSON lines with
sorted keys, compact separators, and `allow_nan=False`.

Therefore both levels of identity are required:

1. the raw compressed file SHA-256 must equal the descriptor
   `prediction_trace.sha256`, and accepted and fresh raw SHA-256 values must
   be identical;
2. SHA-256 of the exact decompressed JSONL bytes must equal
   `prediction_trace.canonical_jsonl_sha256`, and accepted and fresh content
   SHA-256 values must be identical.

The non-empty decompressed line count must equal `row_count`, and
`row_count` must equal the frozen stream length, 138530.

There is no trace projection, float tolerance, row omission, or byte-identity
exception.

This makes every row-level field fail-closed, including row and checkpoint
identities, rule-base version, neural probability, symbolic probability/class,
coverage/abstention state, every frozen fusion probability, and every frozen
decision.

## Evaluation JSON

Each arm evaluation is raw-integrity checked before projection:

1. verify `payload_sha256`;
2. verify `summary_sha256`;
3. require `seed=0` and the exact arm identity;
4. bind `primary_config_manifest_sha256` to that tree's validated correction
   config;
5. bind `phase_b_arm_manifest_sha256` to that tree's validated Phase-B arm;
6. bind `shared_identity_sha256` to the exact Phase-A seed-0 shared identity;
7. require the raw `maintenance_summary` to equal the same tree's Phase-B arm
   maintenance summary;
8. verify the prediction-trace descriptor and bytes/content.

After those checks, only these transformations are legitimate:

- normalize the already-validated correction-config manifest identity;
- normalize the already-validated Phase-B arm-manifest identity;
- remove `payload_sha256` and `summary_sha256` after their raw verification;
- remove exactly the six Phase-B timing-only maintenance-summary fields already
  frozen before Phase-C replay:
  - `compute_seconds`;
  - `shap_seconds`;
  - `surrogate_seconds`;
  - `lifecycle_seconds`;
  - `compute_seconds_per_opportunity`;
  - `compute_seconds_per_publication`.

No other field is projected. The resulting accepted/fresh evaluation objects
must be recursively identical and have identical canonical JSON SHA-256.

## Metrics

`metrics_by_neural_weight` must have exactly the frozen weights:

- `0.5`;
- `0.7`;
- `0.9`;
- `1.0`.

Each weight must contain exactly the domains `full`, `pre`, and `post`.
Within every domain, all of these fields compare exactly:

- accuracy;
- balanced accuracy;
- precision;
- recall;
- F1;
- FPR;
- MCC;
- ROC AUC;
- average precision;
- TP, TN, FP, FN.

No numerical tolerance, re-rounding, recalibration, recomputation
substitution, or endpoint relaxation is permitted.

## Explanations

For each of `full`, `pre`, and `post`, the following fields are exact:

- benign rows;
- benign coverage;
- benign symbolic correctness on covered rows;
- benign correct symbolic coverage;
- attack rows;
- attack coverage;
- attack symbolic correctness on covered rows;
- attack correct symbolic coverage;
- MCSC;
- resolved coverage;
- uncovered rate;
- conflict-abstain rate.

A null/value difference is a mismatch. No explanation field is an allowed
diagnostic exclusion.

## Diagnostics

`primary_windows` is compared as exact ordered `pre` and `post` arrays.
Every window must match on:

- start index;
- end-exclusive index;
- row count;
- MCC;
- FPR;
- F1;
- MCSC;
- resolved coverage;
- conflict-abstain rate.

`primary_recovery` must have exactly the metric keys `mcc`, `mcsc`, and
`fpr`. A metric is either the exact unavailable form
`{available:false, reason:"undefined_window_metric"}`, or the exact available
form containing baseline, recovered status, recovery clock, right-censoring,
and recovery rows from the boundary.

The seed-manifest `trigger_diagnostics` fields are all exact, including alarm
counts/clocks, first post-reference confirmation and delays, repeated
post-reference events, and neural publication count.

These are scientific/operational diagnostics, not machine-runtime diagnostics.
They receive no exclusion.

## Neural retention probes

`neural_retention_probes` is an exact ordered list. Every row must match on:

- sequence;
- checkpoint file SHA-256;
- publication effective index;
- the full nested metrics object.

The metric set is the Cartesian product of prefixes
`development_` / `pre_reference_` and:

- accuracy;
- balanced accuracy;
- precision;
- recall;
- F1;
- FPR;
- MCC;
- ROC AUC;
- average precision.

Every metric contains exact `value`, `delta_from_initial`, and
`descriptive_forgetting` fields. No tolerance or diagnostic exclusion is
permitted.

## Seed manifest and arm-summary identities

The seed manifest is raw-integrity checked first:

- verify `payload_sha256`;
- verify `manifest_sha256`;
- require seed 0;
- require `status=complete_offline_evaluation`;
- require `lambda_one_predictive_equality=true`;
- require `boundary_index=69260`;
- require `adaptive_components_received_boundary=false`;
- bind correction-config, Phase-A seed-0, and Phase-B seed-0 identities;
- require exactly the three arm-summary keys;
- require each raw arm-summary value to equal that tree's corresponding raw
  evaluation `summary_sha256`.

Raw accepted/fresh arm-summary SHA-256 values are **not required to be equal**
because they transitively include already-validated correction-config /
Phase-B identities and the already-frozen Phase-B timing-only fields.

They may be normalized only after:

1. each evaluation's raw self-hashes verify;
2. all upstream bindings verify;
3. the inherited Phase-B timing projection is applied;
4. the accepted/fresh projected evaluation comparison passes.

The seed-manifest correction-config, Phase-A manifest, Phase-B seed-manifest,
and three arm-summary identity fields are treated the same way: bind them to
their own verified upstream objects first, then normalize them for the
cross-tree projection.

After that, `payload_sha256` and `manifest_sha256` are removed only because
their raw integrity has already been established. All remaining seed-manifest
content, especially trigger diagnostics and retention probes, must match
exactly.

## Derived hashes versus exclusions

Removing a verified self-hash or normalizing a verified transitive identity is
not a scientific diagnostic exclusion. It prevents a permitted upstream
diagnostic difference from causing a second-order hash mismatch after the
underlying objects have already been checked.

The following are explicitly **not** derived/normalizable:

- raw prediction-trace SHA-256;
- decompressed canonical JSONL SHA-256;
- trace row count;
- shared identity;
- metrics;
- explanations;
- primary windows/recovery;
- trigger diagnostics;
- retention probes;
- lambda=1 negative-control result;
- boundary index;
- adaptive-boundary-contamination flag.

## No new exclusions

The Phase-C exclusion set is exactly the six inherited Phase-B timing-summary
fields listed above.

There are no new Phase-C diagnostic exclusions, and none may be added after
fresh replay outcomes are inspected.

## Implementation boundary

This tranche freezes comparison semantics only.

It does **not** implement or modify the comparator, does not inspect replay
outcomes, does not replace accepted Stage-8/9 evidence, and does not authorize
Stage 10.

The next implementation task is to audit the existing comparator against this
standalone contract. Any correction may only tighten conformance to the frozen
rules; it may not add an exclusion.
