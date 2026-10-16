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

The deterministic replay comparator/producer is not yet implemented.

Therefore the current additional assurance blocker is:

`replay_report_deterministic_producer_not_implemented`

This blocker is separate from the two external artifact blockers:

- `system_a_checkpoint_bytes_missing`;
- `stage8_large_artifact_archive_missing`.

Recovery of those external artifacts does not by itself authorize Stage-9.5-6
execution or closure.

## Required producer identity

The future deterministic producer is frozen to the identity:

`stage9.5-6-replay-equivalence-assurance-v1`

Before execution, its implementation and dedicated tests must be committed and
frozen. The producer must derive the final report from comparison evidence; it
must not expose a manual override that can set `pass=true`.

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

For Phase A, all five seeds are required. Only the predeclared diagnostic
runtime fields may be normalized:

- `runtime.platform`;
- `runtime.processor`;
- `runtime.threadpool_info[*].filepath`.

For Phase B, all five seeds and all three arms are required. The original
accepted `maintenance.jsonl` records are required. Only the predeclared
timing fields in the v1.1 protocol may be projected away.

For Phase C, the frozen rerun seed is seed 0. The original failed-v1 seed-0
lineage, regenerated correction-config scientific-block equality, corrected
Phase-C execution, predictions, metrics, explanations, diagnostics, retention
probes, and other non-diagnostic scientific fields remain fail-closed.

## Derived-hash implementation boundary

The accepted manifests contain self-hashes and transitive hashes that can
change when only predeclared diagnostic fields change. The replay protocol
defines the allowed diagnostic projections, but a deterministic implementation
must explicitly define how self-hashes and their dependent manifest hashes are
handled under those projections.

That implementation detail must be frozen in code and tests **before** replay
outcomes are inspected. It must not be inferred, relaxed, or expanded after a
mismatch is observed.

## Fail-closed rules

Until the deterministic producer is implemented and frozen:

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
