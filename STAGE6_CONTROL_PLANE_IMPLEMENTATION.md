# Stage 6 — Shared C/D Control-Plane Implementation

**Status:** IMPLEMENTATION IN PROGRESS — PRIMARY ADAPTIVE PRE/POST EXECUTION PROHIBITED  
**Branch:** `stage6-cd-control-plane`  
**Accepted parent:** `cd-design-freeze-v1` / `6f677a2115a1f8d9cbe8e2a3f46d877a01d29f27`  
**Date:** 8 October 2026

## 1. Scope

Stage 6 implements only the treatment-independent adaptive control plane frozen by the accepted
Stage-5 design milestone.

In scope:

- logical prediction clock and delayed-label release;
- shared neural-only drift monitoring;
- checkpoint-pure detector epochs;
- treatment-independent replay memory;
- fixed neural adaptation transactions;
- child checkpoint lineage;
- write-once compact evidence;
- shared-trajectory identity;
- fail-closed timing/checkpoint/integrity verifiers;
- deterministic runtime helpers;
- repository-only toy/generated tests.

Out of scope:

- System D symbolic lifecycle implementation;
- D-periodic symbolic scheduler;
- C/D fused arm evaluation;
- confirmatory C/D analysis execution;
- primary adaptive pre/post stream execution.

## 2. Implemented modules

### `src/concept_drift_ids/cd_control_plane.py`

Implements:

- frozen primary constants;
- prediction-first delayed-label queue;
- uniform mature-history reservoir;
- deterministic training-anchor sampling helper;
- parent-checkpoint-pure current-evidence selection;
- deterministic replay selection with current/replay disjointness;
- checkpoint-pure River ADWIN wrapper;
- fixed neural update configuration;
- deterministic replay fine-tuning;
- stable tensor-state SHA-256;
- non-overwriting checkpoint/JSON writers;
- causal timing/checkpoint/shared-identity/boundary-contamination verifiers.

No scenario loader is imported.

### `src/concept_drift_ids/cd_evidence.py`

Implements:

- versioned shared event envelope;
- canonical event and records hashing;
- non-overwriting JSONL evidence writer;
- checkpoint parent-hash chain records/verifier;
- shared-control-plane identity;
- run-manifest builder;
- manifest file-hash verifier.

### `src/concept_drift_ids/cd_runtime.py`

Implements the frozen primary environment checks:

- Python process must begin with the frozen hash/thread environment;
- PyTorch single-thread/deterministic configuration helper;
- `threadpoolctl` inventory and fail-closed numerical-pool check;
- runtime-manifest payload.

### `src/concept_drift_ids/cd_shared_runner.py`

Implements a dataset-agnostic shared trajectory generator.

The runner:

1. receives caller-supplied ordered feature/label rows;
2. predicts before label release;
3. stores the only pre-maturity stream-label copy inside the delayed-label queue;
4. admits labels only at maturity;
5. feeds only checkpoint-pure mature errors into the shared detector;
6. opens one outstanding neural transaction after a detector event;
7. waits for the complete fixed current-evidence budget rather than shrinking it;
8. selects treatment-independent replay;
9. executes one deterministic child-model update;
10. writes the child checkpoint once;
11. publishes the child for the next logical prediction;
12. starts a fresh checkpoint-pure detector epoch;
13. freezes prediction, label schedule, detector, replay, checkpoint, event and identity evidence;
14. preserves pending labels/transactions at stream end rather than flushing them.

The module contains no CICIDS2017/pre/post scenario-loading function.

## 3. Evidence-access discipline

The runner receives a `StreamRow` containing the evaluator-owned true label because a controlled
simulation must eventually release that label.

At prediction time:

- the neural predictor receives features only;
- the label is inserted into the delayed-label queue;
- the ordinary stream feature store keeps features only, not the caller's `StreamRow` label object.

Downstream replay/update code obtains stream labels only from mature-label records.

This narrows the implementation surface through which a pending label could leak.

## 4. Tests wired into Research Contract CI

Current Stage-6 repository-only tests:

- `tests/test_cd_control_plane_unit.py`;
- `tests/test_cd_evidence_unit.py`;
- `tests/test_cd_shared_runner_unit.py`;
- `tests/test_cd_runtime_unit.py`.

They cover, among other cases:

- prediction-before-label-release, including L=0;
- no terminal pending-label flush;
- deterministic uniform reservoir;
- no current/replay overlap;
- incomplete current window returns no update rather than shrinking;
- detector disarm and old-checkpoint delayed-error quarantine;
- exact ADWIN primary configuration;
- information-time failure cases;
- shared-control-plane divergence failure;
- recursive synthetic-boundary-field rejection;
- deterministic neural child state from identical parent/evidence/config;
- write-once checkpoint/evidence behavior;
- event-envelope validation;
- checkpoint parent-chain verification;
- manifest corruption detection;
- an end-to-end toy shared trajectory with drift, delayed response, child publication and stale-error quarantine;
- shared trajectory self-verification;
- deliberate maturity tampering failure;
- frozen runtime environment requirements.

## 5. Scientific non-events

No primary adaptive pre/post scenario execution has been performed in Stage 6.

No detector parameter, neural hyperparameter, replay budget, timing rule, threshold, endpoint or
symbolic gate has been changed from the accepted design milestone.

Toy test configuration values smaller than the primary budgets exist only to make repository tests
fast. They are explicit `ControlPlaneConfig` overrides and do not change the frozen primary
defaults.

## 6. Stage-6 acceptance requirements still outstanding

Before Stage 6 can be accepted into `main`:

1. exact-head Research Contract CI must pass the new Stage-6 tests;
2. a final implementation audit must confirm no scenario/pre/post execution path was introduced;
3. a compact methodology-ledger entry must record implementation and any defect corrections;
4. draft PR #4 changed files must match Stage-6 scope;
5. all fail-closed verifiers in Stage-6 scope must have tests;
6. local repository parity should be confirmed by the project owner.

Only after Stage 6 acceptance does Stage 7 implement symbolic lifecycle/evaluation code.

## 7. Held-out status

**LOCKED.**

Primary adaptive pre/post execution remains prohibited until the later
`cd-implementation-ready-v1` milestone after Stage 7.
