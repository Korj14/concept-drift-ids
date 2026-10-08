# Stage 5 C/D Design Audit — Portable Handoff

**Date:** 8 October 2026  
**Project:** Concept-drift IDS  
**Branch:** `stage5-cd-design-audit`  
**Accepted parent:** `main` at `4c13d71a111ce7b72b3ef26a01b2918592425aa1`  
**Accepted milestone tag:** annotated remote tag `system-b-v2` -> `4c13d71a111ce7b72b3ef26a01b2918592425aa1`  
**Draft PR:** #3 — C/D adversarial design audit

## Completed packets

### Packet 0 — System-B milestone hygiene

- System B accepted into `main` through PR #2 without squashing its 94-commit scientific history.
- Exact System-B closure source head:
  `317b8d957c3ac983598523215a1205b6869f8c17`.
- PR-specific Research Contract run #156 passed before merge.
- Accepted `main` milestone:
  `4c13d71a111ce7b72b3ef26a01b2918592425aa1`.
- The project owner created and pushed annotated tag `system-b-v2`.
- The remote tag was subsequently verified to resolve exactly to the accepted `main` milestone.

### Packet 1 — adversarial C/D causal audit

- `C_D_ADVERSARIAL_DESIGN_AUDIT.md` frozen.
- Primary causal architecture requires a shared treatment-independent non-symbolic control plane.
- C/D drift events, label availability, replay membership, neural-update evidence, and neural checkpoint trajectory may not diverge because of D symbolic state.
- Alert-conditioned label/evidence acquisition is prohibited in the primary C/D contrast.
- Independent C/D fused-score threshold adaptation is prohibited in the primary contrast.
- Required non-symbolic state equality must be mechanically verified; unexplained divergence aborts the paired experiment.
- System B remains closed; the audit found no defect requiring it to be reopened.

### Packet 2 — stream-time / information-availability contract

`C_D_STREAM_TIME_CONTRACT.md` is frozen before detector selection.

Primary timing decisions:

- adaptive stream = uninterrupted ordered `pre_drift -> post_drift`;
- logical time = zero-based row index; no wall-clock chronology claim;
- no detector/buffer/model/rule/RNG/label-queue reset at the synthetic boundary;
- prediction is committed before any label release or adaptive action at the same clock;
- primary verification latency = `L=5,000` rows;
- label `y_j` matures only after prediction at logical index `j+L`;
- complete eventual supervision is assumed subject to delay and terminal right-censoring;
- alert-conditioned label acquisition is absent from the primary design;
- supervised prequential monitoring must use the neural prediction stored at original arrival, never a later rescore;
- only arrived observations and mature labels may enter an update;
- new adaptive state is effective next logical prediction at earliest;
- no boundary label-queue flush and no end-of-stream adaptive queue flush;
- offline evaluation labels are logically separated from adaptively available labels;
- primary execution is a synchronous logical stream; compute time is reported separately and is not a production-throughput claim;
- prespecified label-latency robustness conditions: `L=0` and `L=10,000`.

These controls have been propagated into:

- `EXPERIMENT_CONTROL_REGISTER.md`;
- `STATISTICAL_ANALYSIS_PLAN.md`;
- `LITERATURE_WATCH.md`;
- `METHODOLOGY_LEDGER.md`.

## Current scientific gate

**Status: NOT READY FOR ADAPTIVE IMPLEMENTATION.**

No adaptive C/D held-out execution is authorized.

No adaptive detector/updater/lifecycle implementation should begin until the remaining prospective controls below are frozen.

## Remaining blocking controls

1. primary treatment-independent drift-monitor signal;
2. detector family/configuration;
3. detector initialization/warm-up/reference state;
4. confirmation/persistence/reset/refractory semantics;
5. adaptation evidence horizon/window;
6. serious neural continual-learning/replay procedure;
7. replay capacity/sampling/eviction;
8. neural update budget/stopping;
9. matched C/D threshold policy;
10. D symbolic lifecycle/operator state machine;
11. online symbolic validation/sample-size semantics;
12. rule-confidence update semantics;
13. D-periodic cadence/opportunity matching;
14. confirmatory endpoints, intervals/tests, multiplicity;
15. runtime/thread/determinism and cost scopes;
16. final event/evidence serialization schemas and fail-closed verifiers.

## Exact next packet

**Treatment-independent drift-monitor signal and detector audit.**

The next packet must begin from the frozen information-time contract, not from a preferred library implementation.

Required order:

1. define what the primary trigger must mean scientifically;
2. compare admissible signal classes:
   - delayed neural-only prequential error/loss;
   - label-free covariate/representation/prediction-distribution shift;
3. distinguish genuine `P(Y|X)` concept evidence from covariate/data-drift evidence in terminology;
4. evaluate detector families for the chosen signal using design/development evidence only;
5. freeze detector initialization/warm-up;
6. freeze persistence/confirmation/reset/refractory policy;
7. freeze false-alarm and detection-delay diagnostics;
8. do not use the synthetic boundary to tune the detector;
9. only then move to neural adaptation/replay design.

The primary detector must produce the **same confirmed-event stream** for matched C and D because it lives upstream of symbolic treatment.

## Prohibited actions until later gate

- no adaptive C/D held-out scoring;
- no detector tuning from pre/post C/D outcomes;
- no use of the synthetic boundary as detector/updater input or tuning target;
- no C/D-specific label/replay/evidence acquisition;
- no C/D fused output or D symbolic state as primary drift-monitor input;
- no treatment-dependent neural adaptation;
- no future-row or pending-label use;
- no end-of-stream label flush into adaptive state;
- no symbolic lifecycle implementation before lifecycle protocol freeze;
- no merging draft PR #3 while material C/D design controls remain unresolved.

## Local artifact requirement

The exact accepted System-A checkpoint bytes remain intentionally outside Git. Before eventual adaptive execution, all five must be locally available and verify against the SHA-256 identities already recorded in the accepted System-A manifest.

## Continuation procedure

A new chat in this Project can resume safely by:

1. `git fetch origin --prune`;
2. verify branch `stage5-cd-design-audit` and clean worktree;
3. verify local HEAD equals `origin/stage5-cd-design-audit`;
4. read this handoff, `C_D_ADVERSARIAL_DESIGN_AUDIT.md`, `C_D_STREAM_TIME_CONTRACT.md`, the control register, statistical plan, and methodology-ledger tail;
5. verify draft PR #3 CI for the current exact branch head;
6. continue with the detector/signal audit only.

Scientific decisions that matter must continue to be committed to the repository rather than existing only in conversational context.
