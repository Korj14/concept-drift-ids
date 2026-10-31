# Stage-10A — matched-state pre-release engineering review

**Date:** 31 October 2026 (Asia/Riyadh)  
**Role:** WARM implementation review only; neither scientific protocol nor second canonical project state. Governing authority remains the frozen Stage-10+ master v1.1 and GoldenEye Stage-10A protocol; changing status resides only in `STAGE10A_CURRENT_STATE_AND_RESUME.md`. **Stage-10A treatment execution: HOLD.**

## Accepted inputs, not evidence of real matched execution

- Original Wednesday source-only receipt: PASS, run [41143214495](https://github.com/Korj14/concept-drift-ids/actions/runs/41143214495), 138,530 retained rows and 77 inherited features with 5,000-row label latency; logical boundary 69,260 is evaluator-only.
- Original five-seed System-A checkpoint and R0.v2 byte-identity receipt: PASS, run [41156553037](https://github.com/Korj14/concept-drift-ids/actions/runs/41156553037), no deserialization or prediction.
- Existing `stage10a_isolation_contract.py` and `stage10a_synthetic_preflight.py` supply synthetic-only isolation and fsynced test-before-label checks. Their supplied digests are not independently witnessed raw neural/control trajectories.
- New `stage10a_pre_release_evidence_gate.py` rechecks both immutable receipts against frozen identities, 19-stage-field/16-obligation structure and HOLD flags; exact-head Python 3.11.9 CI [41157687405](https://github.com/Korj14/concept-drift-ids/actions/runs/41157687405) passed 184 repository-only tests. This is an acceptance recheck, not a scientific release.

## Unverified engineering requirements — prospective checks, not new decisions

1. **Trusted provenance:** Bind every seed, exact clean Git HEAD, Python/runtime lock, frozen checkpoint/preprocessing/R0 and stream identity to a durable raw journal and independently recomputed hashes. Self-declared digest equality is insufficient. Never retain checkpoint binaries or signed URLs in public artifacts.
2. **Matched C/D/D-periodic control:** Verify per-seed identical initial neural state, observation/prediction stream, mature-label admissions, ADWIN and drift events, replay selection, RNG/optimizer/neural updates, fusion and reporting windows. Only symbolic lifecycle may differ. Any shared neural/control divergence is Class-A.
3. **Prediction and information firewall:** Persist/fsync each prediction before admitting its label, enforce original index `i + 5000` maturity and never expose unavailable labels or offline boundary 69,260 to adaptation/detector/symbolic code. Prove real operational order separately from existing synthetic fixture.
4. **Complete five-seed evidence:** Require the full 138,530 retained predictions for each frozen arm and all seeds, with attempted-seed retention, write-once failures, trusted event-source linkage and independent raw trace comparison. No pseudo-replication by window/rule/event.
5. **Comparator and lifecycle:** Verify D-periodic inherited schedule (27,706; 55,412; 83,118; 110,824), shared neural semantics and symbolic operator; preserve 10,000-row separated generation/validation windows and accepted lifecycle gate.
6. **Offline evaluator and inference:** Evaluate only after sealed chronology. Preserve frozen E1/E2/E3 paired-seed (n=5) estimands, t/sign/Holm family, Class-A invalid-run rules and raw null/unfavorable results. No outcome metrics or analysis are authorized by this review.
7. **S10-04 external environment:** Criteria freeze is complete, but a second eligible dataset, dataset-specific 19-field freeze and independent-environment experiment are still unfulfilled.

## Unsettled implementation choices — require explicit review

A prospective, separately reviewed artifact schema must specify how the trusted shared neural/control trace is witnessed and bound to each arm's journal, whether a common neural writer or independently demonstrated identical arm executions are used, and how raw journals/digests are retained without treatment leakage. This review does **not** settle those design choices, retune parameters, authorize model loading, or replace existing frozen science. The next authorized work is synthetic-only design/test preparation and bounded engineering review. A later versioned Stage-10A RELEASE is mandatory before any real C/D/D-periodic treatment execution.
