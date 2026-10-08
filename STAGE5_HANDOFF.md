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

### Packet 6 — D symbolic lifecycle / online validation

`D_SYMBOLIC_LIFECYCLE_PROTOCOL.md` is frozen.

Primary symbolic-treatment decisions:

- candidate generation and candidate acceptance are separate stages;
- D-drift candidate generation uses the 10,000-row neural current-evidence window associated with the shared child checkpoint;
- candidate acceptance uses a different chronological 10,000-row future validation block predicted by that child checkpoint and matured while that checkpoint remains active;
- checkpoint supersession before validation completion aborts the symbolic transaction with no partial publication;
- online SHAP preserves the R0 extraction family: DeepExplainer raw attack logit, balanced background up to 128/class, attribution up to 1024/class, top-12 features;
- online surrogate remains weighted CART with max_depth=4, min_samples_leaf=100 and **weighted fitted-leaf consequent semantics**;
- online rule acceptance uses support>=.001, covered>=25, point precision>=.80 plus one-sided 95% Wilson LCB>=.80, point fidelity>=.90 plus Wilson LCB>=.90, 100-replicate full-gate persistence>=.90, complexity<=4;
- existing D rules are assessed for staleness before candidate integration;
- first completed failure demotes an active rule, second consecutive completed failure retires it; later full-gate pass may reactivate the lineage;
- confidence is refreshed only at completed independent maintenance validation as min(point precision, point neural fidelity);
- same-class overlap>=.95 uses merge/consolidation; overlap [.50,.95) permits refinement only when candidate dominates or resolves documented staleness; lower overlap permits new addition;
- cross-class overlap>=.50 preserves Pareto resolution and unresolved conflict abstention/neural fallback;
- maintenance events, rejected candidates, no-ops, censored transactions, rule revisions and parent-hash rule-base versions are immutable evidence;
- symbolic recovery requires a documented valid -> stale/demoted -> refinement/reactivation/replacement -> post-publication improvement chain.

### Packet 7 — D-drift versus D-periodic trigger ablation

`D_TRIGGER_ABLATION_PROTOCOL.md` is frozen.

Trigger-ablation decisions:

- D-drift and D-periodic use the exact same symbolic operator/configuration and shared neural trajectory;
- maximum symbolic maintenance budget = four opportunities per seed per trigger arm;
- every opportunity consumes a slot regardless of publication/no-op/censoring; no retries beyond four;
- D-drift uses the first four confirmed primary detector events for its symbolic slots;
- D-periodic uses fixed clocks 27,706; 55,412; 83,118; 110,824;
- those clocks equal floor(i*N/5) for N=138,530 and were derived from the frozen 25,000-row symbolic evidence footprint, not from the known boundary or detector results;
- periodic scheduling never consults detector alarms;
- periodic candidate generation uses the most recent 10,000 mature rows at the fixed target clock and the current shared checkpoint;
- periodic validation uses the same future 10,000-row checkpoint-pure validation contract;
- checkpoint supersession aborts the transaction; the periodic schedule does not move;
- at most one symbolic transaction is outstanding per seed/arm; a periodic target arriving while a transaction remains pending is logged pending_transaction_skip and consumes its slot;
- opportunity, completed validation, publication, no-op and censored/aborted transaction are distinct outcomes.

### Packet 8 — final statistical / runtime / reproducibility freeze

`C_D_FINAL_ANALYSIS_REPRODUCIBILITY_PROTOCOL.md` is frozen and
`STATISTICAL_ANALYSIS_PLAN.md` is now version 1.0.

Primary confirmatory family:

- E1: whole-post MCC, D-drift minus C;
- E2: whole-post macro correct symbolic coverage (MCSC), D-drift minus C;
- E3: whole-post MCSC, D-drift minus D-periodic.

Primary seed-level effect summary:

- arithmetic mean of five paired seed differences;
- 95% Student-t interval over paired differences, df=4;
- all five raw pairs, median, SD, min/max, sign pattern and leave-one-seed-out mean range mandatory;
- exact one-sided sign test is secondary calibration;
- Holm-Bonferroni adjusts the three confirmatory sign-test p-values;
- windows/events/rules are not promoted to independent replicates.

Primary runtime/reproducibility:

- CPU-only;
- Python 3.11.9 + frozen requirements;
- PYTHONHASHSEED=0;
- OMP/MKL/OpenBLAS/NumExpr threads=1;
- torch intra/inter-op threads=1;
- deterministic algorithms;
- DataLoader workers=0;
- threadpoolctl inventory recorded and fail-closed.

Write-once evidence and ten causal verifier families are frozen, including exact C/D shared-control-plane identity, information timing, checkpoint purity, lambda=1 predictive equality, symbolic evidence separation, trigger-arm operator identity, no-boundary contamination and hash integrity.

Implementation sequence is frozen:

1. accept/tag this design milestone as `cd-design-freeze-v1`;
2. `stage6-cd-control-plane`;
3. `stage7-cd-symbolic-lifecycle`;
4. accept/tag `cd-implementation-ready-v1`;
5. `stage8-cd-primary-evaluation`.

Held-out execution is two-phase: first freeze one shared detector/neural control-plane trajectory per seed, then C/D-drift/D-periodic consume that immutable trajectory.

## Current scientific gate

**Status: PROSPECTIVE C/D DESIGN FREEZE COMPLETE — IMPLEMENTATION MAY BEGIN ONLY AFTER MILESTONE ACCEPTANCE.**

Adaptive held-out execution remains prohibited until `cd-implementation-ready-v1`.

No adaptive C/D held-out execution is authorized.

No adaptive detector/updater/lifecycle implementation should begin until the remaining prospective controls below are frozen.

## Remaining blocking controls

There are **no remaining material prospective design TBDs** blocking adaptive implementation.

The remaining gates are implementation/governance gates:

1. exact Stage-5 design head must pass Research Contract CI;
2. draft PR #3 must be reviewed/accepted and merged to `main` preserving history;
3. accepted merge commit must receive immutable annotated tag `cd-design-freeze-v1`;
4. Stage-6/7 implementation and repository-only verifier tests must complete before any primary adaptive pre/post execution;
5. `cd-implementation-ready-v1` must be accepted/tagged before Stage-8 primary evaluation.

## Exact next packet

**Milestone acceptance, then Stage 6 shared control-plane implementation.**

Before implementation code:

1. verify Research Contract CI on the exact final Stage-5 head;
2. merge draft PR #3 to `main` without squashing scientific history;
3. create immutable annotated tag `cd-design-freeze-v1` on the accepted merge commit;
4. create `stage6-cd-control-plane` from that accepted parent.

Stage 6 then implements only:

- stream logical clock and delayed-label queue;
- shared ADWIN detector/event epochs;
- treatment-independent replay memory;
- shared neural adaptation transaction/checkpoint lineage;
- write-once run/control-plane schemas;
- causal verifiers for timing/control-plane identity/checkpoint purity;
- repository-only toy/generated tests.

**Stage 6 must not execute the primary pre/post adaptive stream.**

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
6. if Stage-5 has been accepted/tagged, continue with Stage-6 shared control-plane implementation only; otherwise complete milestone acceptance first.

Scientific decisions that matter must continue to be committed to the repository rather than existing only in conversational context.
