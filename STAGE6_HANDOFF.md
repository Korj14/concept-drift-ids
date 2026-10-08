# Stage 6 Shared Control Plane — Portable Handoff

**Date:** 8 October 2026  
**Project:** Concept-drift IDS  
**Branch:** `stage6-cd-control-plane`  
**Accepted parent:** `cd-design-freeze-v1` / `6f677a2115a1f8d9cbe8e2a3f46d877a01d29f27`  
**Draft PR:** #4 — Stage 6 shared C/D control plane

## Stage-6 scientific scope

Stage 6 implements the treatment-independent adaptive control plane only.

It does **not** implement D symbolic evolution and does **not** execute the primary adaptive pre/post
stream.

## Implemented

### Timing / supervision

- prediction-first delayed-label queue;
- fixed maturity schedule support including L=0 test-then-update semantics;
- terminal pending labels remain censored;
- ordinary stream feature store does not retain the caller's label object after insertion into the
  delayed-label queue.

### Shared drift monitor

- River ADWIN frozen configuration;
- delayed neural-only hard-error input;
- checkpoint-pure detector epochs;
- detector disarm after confirmed event;
- stale old-checkpoint delayed errors quarantined after child publication.

### Replay / neural adaptation

- treatment-independent uniform mature-history reservoir;
- deterministic training-anchor selection helper;
- current-evidence selection restricted to mature parent-checkpoint records;
- replay/current row-ID disjointness;
- deterministic replay sampling;
- fixed Adam replay fine-tuning transaction;
- stable tensor-state SHA-256;
- non-overwriting child checkpoint artifacts;
- exact parent/child checkpoint lineage.

### Evidence / provenance

- common event envelope;
- JSON/JSONL write-once evidence;
- canonical record hashes;
- shared trajectory identity;
- checkpoint-chain verifier;
- run-manifest builder/file verifier;
- non-overwriting frozen shared-trajectory artifacts.

### Runtime

- exact primary hash/thread environment requirements;
- deterministic/single-thread PyTorch helper;
- threadpoolctl inventory and fail-closed numerical-pool check.

### Fail-closed verification

- information-time verification;
- checkpoint-purity verification;
- shared-control-plane identity verification;
- recursive synthetic-boundary-field rejection;
- shared trajectory self-verification;
- exact frozen primary-config/monitor-threshold/anchor-size verifier;
- write-once/hash verification.

### Scenario-access firewall

`cd_shared_runner.py` has no scenario loader, no partition loader, and no pre/post scenario execution
surface. Repository tests inspect the module for those forbidden imports/identifiers.

## Tests

Research Contract CI executes:

- `tests/test_cd_control_plane_unit.py`
- `tests/test_cd_evidence_unit.py`
- `tests/test_cd_shared_runner_unit.py`
- `tests/test_cd_runtime_unit.py`

The test suite uses toy/generated data and small explicit test-only budgets. Those overrides do not
alter the frozen primary defaults.

A dedicated verifier rejects test-style configuration if later code attempts to declare it primary.

## Primary held-out status

**LOCKED.**

No primary adaptive pre/post execution has occurred on this branch.

Stage 6 does not expose a command that loads or executes the primary scenario.

## Acceptance gate

Stage 6 may merge to `main` only after:

1. exact terminal branch head passes Research Contract CI;
2. changed-file audit remains within Stage-6 scope;
3. no primary adaptive pre/post artifact exists;
4. PR #4 is accepted without squashing the scientific history.

## Exact next stage

After Stage 6 acceptance, create:

`stage7-cd-symbolic-lifecycle`

from the accepted Stage-6 `main`.

Stage 7 implements:

- migrated R0.v2 lifecycle schema;
- D symbolic candidate generation;
- independent future symbolic validation;
- Wilson/bootstrap online gate;
- retain/demote/retire/reactivate/refine/merge/conflict state machine;
- immutable rule revisions/lineage/version chain;
- D-drift symbolic arm;
- D-periodic scheduler at frozen clocks;
- C/D/D-periodic arm consumption of the immutable shared control-plane trajectory;
- lambda=1 negative-control verifier;
- MCSC and frozen confirmatory/secondary analysis builders;
- repository-only toy/generated symbolic tests.

Stage 7 still may **not** execute the primary adaptive pre/post stream.

Only after Stage 7 acceptance and annotated
`cd-implementation-ready-v1` may Stage 8 access the primary adaptive stream.

## Continuation procedure

A later chat can recover safely by:

1. `git fetch origin --prune`;
2. verify branch/head and clean worktree;
3. read this file, `STAGE6_CONTROL_PLANE_IMPLEMENTATION.md`,
   `C_D_FINAL_ANALYSIS_REPRODUCIBILITY_PROTOCOL.md`, and the methodology-ledger tail;
4. verify PR #4 exact-head CI;
5. if Stage 6 is not yet merged, complete its acceptance gate;
6. if already merged, branch Stage 7 from accepted `main`;
7. do not execute primary adaptive pre/post data before `cd-implementation-ready-v1`.
