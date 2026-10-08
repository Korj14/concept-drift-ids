# Stage 5 C/D Design Audit — Portable Handoff

**Date:** 8 October 2026  
**Project:** Concept-drift IDS  
**Branch:** `stage5-cd-design-audit`  
**Accepted parent:** `main` at `4c13d71a111ce7b72b3ef26a01b2918592425aa1`  
**Draft PR:** #3 — C/D adversarial design audit

## Completed in this packet

1. System B was accepted into `main` through PR #2 without squashing its scientific history.
2. PR-specific Research Contract run #156 passed on exact System-B source head
   `317b8d957c3ac983598523215a1205b6869f8c17`.
3. `stage5-cd-design-audit` was created from the accepted System-B `main` milestone.
4. `C_D_ADVERSARIAL_DESIGN_AUDIT.md` was added.
5. `METHODOLOGY_LEDGER.md` records the milestone transition and adversarial gate.
6. `EXPERIMENT_CONTROL_REGISTER.md` now freezes causal-isolation principles:
   - treatment-independent drift-event provenance;
   - treatment-independent label/evidence acquisition;
   - hash-verifiable C/D non-symbolic state equality;
   - abort on unexplained non-symbolic divergence;
   - no alert-conditioned adaptation in the primary causal contrast;
   - no independent C/D fused-score threshold adaptation in the primary contrast.
7. Draft PR #3 was opened as the CI/review surface. It must remain draft through the design-freeze packets.

## Scientific gate

**Status: NOT READY FOR ADAPTIVE IMPLEMENTATION.**

No C/D held-out execution and no adaptive implementation code is authorized yet.

The adversarial audit did **not** identify a defect requiring System B to be reopened.

## Blocking controls still to freeze

1. stream-time and label-latency model;
2. monitored drift signal;
3. drift detector family/configuration;
4. confirmation/persistence/reset/refractory semantics;
5. adaptation evidence horizon;
6. serious neural continual-learning/replay procedure;
7. replay capacity/sampling/eviction;
8. neural update budget/stopping;
9. matched C/D threshold policy;
10. D symbolic lifecycle/operator state machine;
11. online symbolic validation/sample-size semantics;
12. rule-confidence update semantics;
13. D-periodic cadence/opportunity matching;
14. confirmatory endpoints, intervals/tests, multiplicity;
15. runtime/thread/determinism and cost scopes.

## Next packet

**Stream-time / information-availability contract first.**

Reason: detector choice cannot be scientifically frozen until it is known which signals and labels can legally exist at each time. The next packet should:

1. define the event clock and prequential order;
2. define a primary label-delay/maturity model and prespecified sensitivity if justified;
3. define pending/mature evidence semantics;
4. define detector/update/publication eligibility at each clock step;
5. prohibit future-row use in adaptation windows;
6. only then compare admissible drift-monitor signals/detectors.

## Prohibited actions until later gate

- no adaptive held-out C/D scoring;
- no use of the known synthetic boundary as detector/updater input;
- no tuning from C/D outcomes;
- no C/D-specific label/replay/evidence acquisition;
- no treatment-dependent neural adaptation;
- no symbolic lifecycle implementation before the lifecycle protocol is complete;
- no merging draft PR #3 while material C/D design controls remain TBD.

## Local artifact requirement

The exact accepted System-A checkpoint bytes remain intentionally outside Git and must remain available locally against their recorded SHA-256 values before eventual adaptive execution.

## Milestone tag hygiene

Repository governance calls for an annotated tag on accepted major milestones. The GitHub connector available in this chat cannot create annotated Git tags. Create the System-B milestone tag locally only after verifying the accepted main SHA exactly, and never move it after creation.

Suggested tag name: `system-b-v2`.
