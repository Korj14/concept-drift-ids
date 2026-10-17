# Stage 9.5-6 Replay Report Construction Contract v1

**Status:** PROSPECTIVELY FROZEN / EXECUTION BLOCKED  
**Contract:** `data/manifests/stage9_5_6_replay_report_construction_v1.json`  
**Governing replay protocol:** `stage9.5-6-replay-equivalence-correction-v1_1`

## Purpose

The Stage-9.5-6 order gate now requires a preserved canonical
`results/audits/stage9_5_full_seed_rerun_v1/replay_equivalence_report.json`.
This document freezes how a future successful report may be constructed.

A successful replay report may **not** be manually authored from favorable
observations or from copied pass/fail booleans. Its pass state must be derived
by a deterministic comparator/producer whose implementation and tests are
frozen before recovered-artifact replay outcomes are inspected.

## Current blocker

The deterministic replay-report finalizer is implemented and prospectively frozen as `stage9.5-6-replay-report-finalizer-v1`. It validates the frozen machine-comparison evidence schema, derives the replay report fields, and computes the canonical report hash. It does **not** compare Phase-A/B/C replay artifacts.

The Stage-1 reconstruction prerequisite is now **closed** by the preserved
authoritative report
`results/audits/stage9_5_full_seed_rerun_v1/stage1_reconstruction_report.json`.
Its canonical SHA-256 is
`4bafa772f9737d934f40c90bf7be8d80a62108cf89a9c74895fbe5c12c4a88af`,
with 8/8 raw files, 8/8 reconstructed interim tables, zero semantic
mismatches, empty failures/blockers, and the frozen Python 3.11.9 environment.
The additive closure record is
`STAGE9_5_6_STAGE1_RECONSTRUCTION_EVIDENCE_CLOSURE.md`.

No non-external replay-construction blocker is currently identified. The two
remaining blockers are the original external artifact blockers:

- `system_a_checkpoint_bytes_missing`;
- `stage8_large_artifact_archive_missing`.

Recovery and exact verification of both external artifact families is still
required before the historical all-five-seed replay can execute to closure.

## Required producer identity

The future deterministic producer is frozen to the identity:

`stage9.5-6-replay-equivalence-assurance-v1`

The report-construction pipeline is split into the frozen comparator identity
`stage9.5-6-replay-equivalence-comparator-v1` and finalizer identity
`stage9.5-6-replay-report-finalizer-v1`. The finalizer implementation and
dedicated tests are committed. The comparator now has prospectively frozen
Phase-A, Phase-B, Phase-C failure-lineage/correction-config, and corrected
Phase-C seed-0 output comparison layers. Neither layer may expose a manual
override that can set `pass=true`.

The successful report must carry, at minimum:

- `construction.contract_id = stage9.5-6-replay-report-construction-v1`;
- `construction.producer_id = stage9.5-6-replay-equivalence-assurance-v1`;
- `construction.manual_success_report_permitted = false`;
- `construction.deterministic_comparison_complete = true`;
- `construction.source_evidence_complete = true`;
- `construction.mismatch_count = 0`.

## Comparison scope already frozen

The producer must implement the existing v1.1 replay-equivalence rules rather
than define new comparison semantics after replay outcomes exist.

For Phase A, all five seeds are required. The comparator is now implemented
and prospectively frozen in
`tools/stage9_5/replay_equivalence_comparator.py`, with dedicated tests in
`tests/stage9_5/test_replay_equivalence_comparator.py`.

For each accepted/fresh seed pair, the comparator first verifies the raw
historical hash chain: `payload_sha256` is checked against the raw JSON object
without that field but still containing `manifest_sha256`; then
`manifest_sha256` is checked against the object without either derived hash.
Every descriptor-linked file is independently byte-hash checked, and descriptor
paths must remain inside the seed root.

Only these predeclared diagnostic runtime fields are normalized, using the
fixed sentinel `<stage9.5-6-diagnostic-normalized>`:

- `runtime.platform`;
- `runtime.processor`;
- `runtime.threadpool_info[*].filepath`.

After raw hash integrity is established, the two diagnostic-dependent derived
hash fields `payload_sha256` and `manifest_sha256` are removed from the
comparison projection. The accepted and fresh projected manifests must then
have identical canonical JSON SHA-256 values and exact recursive content
equality. All descriptor hashes, checkpoint identities, runtime fields other
than the three above, protocol/configuration fields, and scientific content
remain exact.

For Phase B, all five seeds and all three arms are required. The comparator
is now implemented and prospectively frozen in the same comparator module and
test file. The original accepted `maintenance.jsonl` records remain mandatory.

For each arm, raw `payload_sha256` and `manifest_sha256` values are verified
first, every file descriptor is constrained to the arm root, and every
descriptor SHA-256 is checked against the referenced bytes. Initial state,
final state, and all version-file descriptors remain exact.

The ordered maintenance records are then compared after removing only the
predeclared timing fields:

- `shap_seconds`;
- `surrogate_seconds`;
- `lifecycle_seconds`;
- `generation_payload.timing_seconds`.

The arm-level maintenance summary removes only:

- `compute_seconds`;
- `shap_seconds`;
- `surrogate_seconds`;
- `lifecycle_seconds`;
- `compute_seconds_per_opportunity`;
- `compute_seconds_per_publication`.

After raw integrity verification, the arm projection removes the raw
`files.maintenance.sha256`, `manifest_sha256`, and `payload_sha256`
identities because those hashes are transitively timing-dependent. No other
arm-level fields are relaxed.

At the seed-level Phase-B manifest, each arm descriptor's raw
`sha256` and `manifest_sha256` values are likewise removed only after the
referenced arm manifest has passed raw integrity verification and projected
arm equality. The seed manifest's own `payload_sha256` and
`manifest_sha256` are then removed for projected equality. All other fields
remain exact, including `git_commit`, configuration identities, all shared
Phase-A identities, operator identity, descriptor paths,
`primary_boundary_scored`, and `arm_isolation_sha256`.

For Phase C, the frozen rerun seed is seed 0. The precondition layer is now
implemented and prospectively frozen.

The original failed-v1 seed-0 directory must contain exactly
`attempt.json` and `failure.json`. Both accepted and replayed copies must
match the file and payload SHA-256 identities frozen inside the accepted
correction config; equality merely between the two copies is not sufficient.

The accepted and regenerated correction configs are each raw-hash verified.
The accepted config must retain manifest identity
`d380fce5f9db8f0b639dc999298a263b10a10a3d02e35def226a121d098e2222`,
and both configs must bind `prepared_from_git_commit` to historical correction
source `79ddc4c6d6dea52c7cabc55a6d082448fc24fcf9`. All eight frozen scientific
blocks remain exact.

Before projection, each correction config's five Phase-A
`run_manifest_sha256` values and five Phase-B
`phase_b_manifest_sha256` values must match the actual corresponding replay
artifact manifests. Only those ten already-proven diagnostic-transitive raw
identities are then normalized. After raw self-hash verification,
`payload_sha256` and `manifest_sha256` are removed, and the accepted and
regenerated configs must otherwise match exactly under canonical recursive
comparison.

Corrected Phase-C seed-0 output comparison is now implemented and
prospectively frozen. Each arm evaluation first passes raw
`payload_sha256` / `summary_sha256` verification and is rebound to its
actual correction config, Phase-B arm manifest, copied Phase-B maintenance
summary, and Phase-A `shared_identity.identity_sha256`. Prediction traces
must remain path-contained and exact for compressed-file SHA-256,
decompressed canonical JSONL SHA-256, row count, and the frozen scenario
stream-row count.

Only identities already proven to be downstream of the approved Phase-A /
Phase-B diagnostic projections may be normalized:

- arm-evaluation `primary_config_manifest_sha256`;
- arm-evaluation `phase_b_arm_manifest_sha256`;
- the six already-approved Phase-B maintenance-summary timing fields;
- seed-manifest correction-config, Phase-A, Phase-B, and arm-summary raw hash
  identities.

After raw integrity and upstream binding checks, derived
`payload_sha256`, `summary_sha256`, and seed `manifest_sha256` fields
are removed from the comparison projection. Predictions, metrics,
explanations, windows, recovery diagnostics, trigger diagnostics, retention
probes, shared identity, boundary/contamination controls, lambda-one
negative-control evidence, all non-timing maintenance content, and both
prediction-trace identities remain exact. The prediction-trace writer uses an
empty gzip filename, `mtime=0`, and compression level 9, so there is no
compression-diagnostic exclusion.

## Derived-hash implementation boundary

The accepted manifests contain self-hashes and transitive hashes that can
change when only predeclared diagnostic fields change. Phase-A and Phase-B
handling are now explicitly frozen as described above and are no longer
implementation blockers.

Phase-C correction-config, failure-lineage, and corrected seed-0 output
handling are now explicitly frozen and implemented. The replay comparator and
report finalizer therefore no longer have an unimplemented Phase-A/B/C
projection layer.

Replay step 1 from the v1.1 protocol is now independently evidenced and
closed. The replay comparator validates the preserved Stage-1 report directly,
requires its repository head to be in the replay lineage, and carries its
canonical SHA-256 into comparison evidence. Stage-1 success remains an explicit
verified prerequisite rather than something inferred from downstream Phase-A/B/C
success.

## Fail-closed rules

Until the two external artifact prerequisites are recovered and verified:

- do not create a successful `replay_equivalence_report.json` manually;
- do not treat aggregate agreement as a substitute for record-level comparison;
- do not lower the accepted-maintenance requirement;
- do not add new diagnostic exclusions;
- do not replace accepted Stage-8/9 evidence;
- do not access Stage-10 outcomes.

Any missing source evidence, unimplemented projection, or mismatch outside the
predeclared diagnostic fields keeps Stage 9.5-6 blocked.

## Scientific meaning

This construction contract changes assurance mechanics only. It does not alter
the accepted Stage-8/9 estimands, treatments, metrics, results, or claim
boundaries.
