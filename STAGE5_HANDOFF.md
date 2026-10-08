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

### Packet 4 — shared neural adaptation / replay

`C_D_NEURAL_ADAPTATION_PROTOCOL.md` is frozen.

Primary neural-control decisions:

- one shared neural update is executed once per seed/event and the resulting child checkpoint bytes/hash are consumed by both C and D;
- current evidence budget = 10,000 most recent mature labeled observations whose original prediction was produced by the parent checkpoint;
- if that budget is unavailable at event time, the parent remains active and the detector remains disarmed until the full budget matures;
- terminal shortfall is a right-censored response; the window is not shrunk and no terminal update is forced;
- replay memory = immutable 10,000-row uniform training anchor + 10,000-row uniform mature-stream reservoir;
- each update replays 5,000 anchor + 5,000 eligible online rows, excluding current-window row IDs;
- update dataset = 10,000 current + 10,000 replay;
- fixed original pos_weight=4.138247558496975;
- all MLP parameters trainable;
- fresh Adam per event, lr=1e-4, weight_decay=1e-5, batch=1024, exactly 5 epochs;
- no scheduler, no early stopping, no performance-based publication gate;
- technically valid but harmful updates are retained as evidence;
- deterministic replay/adaptation seeds are frozen;
- catastrophic forgetting is measured on the full historical development probe and by offline pre-drift checkpoint rescoring, never used to control the update;
- no-replay fine-tuning is a prespecified secondary ablation.

### Packet 5 — fusion and operational threshold

`C_D_FUSION_THRESHOLD_PROTOCOL.md` is frozen.

Primary decision-policy controls:

- accepted R0.v2 fusion rule remains primary;
- lambda=.50 on resolved symbolic coverage;
- neural fallback on uncovered/conflict;
- accepted R0.v2 fused threshold for each seed remains fixed for the entire adaptive trajectory;
- C and D use exactly the same lambda and threshold within a matched seed;
- no per-event, per-window or per-arm threshold recalibration;
- threshold-free ROC-AUC/AP remain mandatory alongside thresholded metrics;
- accepted R0.v2 development-grid lambda=.70 and lambda=.90 pairs are frozen as secondary fusion-authority sensitivities;
- lambda=1.00 is a causal negative control: C/D predictive scores and thresholded decisions must be identical because symbolic predictive authority is zero and the neural checkpoint chain is shared.

All neural-side causal controls are now prospectively specified.

## Current scientific gate

**Status: NOT READY FOR ADAPTIVE IMPLEMENTATION.**

No adaptive C/D held-out execution is authorized.

No adaptive detector/updater/lifecycle implementation should begin until the remaining prospective controls below are frozen.

## Remaining blocking controls

1. D symbolic lifecycle/operator state machine;
2. symbolic candidate-generation evidence;
3. independent online symbolic validation evidence;
4. online support/count/uncertainty gate semantics;
5. rule-confidence update semantics;
6. D-periodic cadence/opportunity matching;
7. confirmatory endpoints, intervals/tests and multiplicity;
8. runtime/thread/determinism and cost scopes;
9. final event/lifecycle/evidence serialization schemas;
10. fail-closed contamination/integrity verifiers and implementation tests.

## Exact next packet

**D symbolic lifecycle / online validation protocol.**

This is the next high-risk design packet and should begin from the already frozen shared control plane rather than from the static R0 implementation details alone.

Required order:

1. define the immutable symbolic version/event state machine;
2. separate candidate generation from candidate acceptance;
3. define which shared neural checkpoint and which current-evidence rows candidate generation may use;
4. create an independent, time-respecting symbolic validation evidence slice/pool;
5. resolve the static R0 min-covered=100/sample-size problem for online validation without weakening gates after seeing C/D outcomes;
6. freeze add/refine/merge/retain/demote/retire/reactivate semantics;
7. freeze conflict resolution and abstention semantics across versions;
8. freeze confidence update source/timing and whether confidence can change without structural rule change;
9. define lineage IDs, parent/source IDs, version hashes and rejected-change records;
10. define staleness tests for existing R0/Rt rules before permitting retirement/replacement;
11. only after the operator is frozen, freeze D-drift versus D-periodic opportunity matching;
12. then finish the confirmatory statistical and runtime/reproducibility freeze.

No symbolic update may use the evaluator-known boundary, pending labels, future rows, or C/D outcome direction.

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
6. continue with the symbolic lifecycle / online-validation design packet only.

Scientific decisions that matter must continue to be committed to the repository rather than existing only in conversational context.
