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

### Packet 3 — treatment-independent drift monitor

`C_D_DRIFT_MONITOR_PROTOCOL.md` is frozen.

Primary detector decisions:

- signal = delayed neural-only 0/1 prequential error;
- each error uses the neural prediction stored at original arrival and the label only after maturity;
- monitor-only decision threshold = fixed accepted System-A development threshold for that seed;
- primary detector = `river.drift.ADWIN` under `river==0.26.1`;
- exact primary ADWIN parameters are River defaults: delta=.002, clock=32, max_buckets=5, min_window_length=5, grace_period=10;
- one ADWIN detection is one confirmed statistical drift event; no extra hit/majority rule;
- detector starts fresh per seed with no training/development preload;
- detector event terminology is statistical neural-error/performance drift, not proof of P(Y|X) change;
- detector epochs are checkpoint-pure;
- after an event, the detector is disarmed during the neural-response transaction;
- after a new neural checkpoint is published, old-checkpoint delayed errors are quarantined from the new detector epoch;
- the next epoch receives input only when labels mature for predictions actually produced by the new checkpoint;
- no arbitrary primary cooldown is added beyond this causal feedback-quarantine rule;
- robustness: default Page-Hinkley on the same hard-error signal, ADWIN on delayed Brier loss, plus L=0/L=10,000 latency conditions;
- synthetic boundary remains post-hoc scoring only.

A provisional idea to set ADWIN grace_period=5,000 was explicitly rejected before freeze. River's default grace_period=10 remains primary; delayed-feedback contamination is handled by checkpoint-pure epoch eligibility instead of by detector tuning.

These controls have been propagated into the control register, statistical plan, literature watch and methodology ledger.

## Current scientific gate

**Status: NOT READY FOR ADAPTIVE IMPLEMENTATION.**

No adaptive C/D held-out execution is authorized.

No adaptive detector/updater/lifecycle implementation should begin until the remaining prospective controls below are frozen.

## Remaining blocking controls

1. adaptation evidence horizon/window after a confirmed event;
2. serious shared neural continual-learning/replay procedure;
3. replay capacity/sampling/eviction;
4. neural update budget/stopping/publication transaction;
5. matched C/D operational/fusion threshold policy;
6. D symbolic lifecycle/operator state machine;
7. online symbolic validation/sample-size semantics;
8. rule-confidence update semantics;
9. D-periodic cadence/opportunity matching;
10. confirmatory endpoints, intervals/tests, multiplicity;
11. runtime/thread/determinism and cost scopes;
12. final event/evidence serialization schemas and fail-closed verifiers.

## Exact next packet

**Shared neural adaptation / replay protocol.**

Required order:

1. define the neural-adaptation objective and what counts as a scientifically serious System-C comparator;
2. distinguish current-event evidence from replay/retention evidence;
3. freeze the adaptation evidence horizon and label-maturity eligibility;
4. compare simple replay-based fine-tuning against reasonable continual-learning alternatives using training/development/design evidence only;
5. freeze replay capacity, class handling, admission/eviction, sampling and RNG;
6. freeze optimizer state policy, learning rate, epochs/update budget, batch size and stopping;
7. freeze catastrophic-forgetting/retention diagnostics;
8. define the neural adaptation transaction and publication/checkpoint hash semantics that the detector re-arm rule depends on;
9. require the exact same neural transaction trajectory for matched C and D;
10. only after that move to the matched operational/fusion threshold policy.

The neural-adaptation design must be credible enough that D cannot appear useful merely because C is an intentionally weak adaptive baseline.

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
