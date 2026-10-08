# Stage 7 Symbolic Lifecycle — Portable Handoff

**Date:** 8 October 2026  
**Project:** Concept-drift IDS  
**Branch:** `stage7-cd-symbolic-lifecycle`  
**Accepted parent:** Stage-6 `main` at `f11f2709bc1f6a32a7c416012860342d9a772ff7`  
**Draft PR:** #5 — Stage 7 C/D symbolic lifecycle and evaluation

## Scientific status

Stage 7 implementation is complete pending exact-terminal-head Research Contract CI and milestone
acceptance.

Primary adaptive pre/post execution remains **LOCKED**.

## Implemented symbolic treatment

- accepted R0.v2 hash-pinned migration;
- explicit semantic rule / revision / lineage / rule-base-version identities;
- one-sided Wilson online validation;
- bootstrap gate persistence;
- independent checkpoint-pure future validation;
- retain/demote/retire/reactivate;
- stale-rule refinement with lineage preservation;
- same-class merge/consolidation;
- cross-class Pareto demotion;
- unresolved conflict relations and neural fallback semantics;
- separate inference-version hash and lifecycle-history hash;
- write-once maintenance and version artifacts.

## Candidate generation

Frozen online proposal implementation:

- DeepExplainer raw attack logit;
- 128/class background;
- up to 1024/class attribution;
- top 12 features;
- deterministic symbolic RNG namespace;
- weighted CART depth 4 / min leaf 100;
- fitted weighted CART leaf argmax consequent.

No scenario loader exists in the Stage-7 runtime modules.

## Trigger arms

D-drift:

- first four shared confirmed detector opportunities;
- uses associated shared child checkpoint and neural-current generation evidence.

D-periodic:

- exact target clocks 27,706 / 55,412 / 83,118 / 110,824;
- current shared checkpoint at target;
- most recent 10,000 mature rows for candidate generation;
- validation begins at target+1, not at an older checkpoint's original birth.

Both arms:

- same operator config hash;
- same four-slot budget;
- same shared-control-plane identity;
- same seed and accepted R0 starting state;
- same independent validation rules;
- cannot alter detector/replay/neural checkpoint trajectory.

## Evaluation / analysis

Implemented:

- fixed lambda=.50 operating point;
- .70/.90 sensitivities;
- lambda=1 predictive negative control;
- MCSC and class-specific components;
- dynamic rule-base-version scoring by effective logical index;
- E1/E2/E3 five-seed paired summaries;
- paired t95 interval, df=4;
- exact one-sided sign calibration;
- Holm adjustment;
- two-window recovery;
- opportunity/validation/publication/no-op/censoring and maintenance-cost summaries.

## Implementation defects caught prospectively

1. **Toy Wilson fixture:** test-only LCB threshold was incompatible with n=4. Corrected test fixture only;
   primary .80/.90 LCB gate unchanged.
2. **Periodic validation chronology:** initial orchestration could admit validation rows before the
   periodic target when a checkpoint was long-lived. Corrected with explicit
   `validation_start_index=target+1`. Dedicated regression test added.
3. **Stale refinement/conflict hardening:** stale demoted incumbents remain eligible as refinement
   parents and unresolved conflict relations are rebuilt deterministically from the final active set.

All were corrected before primary adaptive pre/post access.

## Readiness preflight

`python run.py cd-preflight`

This command performs file/hash/config checks only. It does not load a scenario partition.

It requires local accepted System-A checkpoint bytes and will fail closed if any are absent or
hash-wrong.

It verifies:

- Python 3.11.9;
- SAP v1.0 and required protocols;
- scenario raw/canonical identities;
- preprocessing identity;
- System-A manifest and five checkpoint files;
- accepted R0.v2 manifest/rule artifacts;
- primary control-plane config;
- primary symbolic config.

## Tests

Stage-7 CI test set:

- `test_cd_symbolic_lifecycle_unit.py`
- `test_cd_symbolic_candidates_unit.py`
- `test_cd_symbolic_arms_analysis_unit.py`
- `test_cd_symbolic_runner_evidence_unit.py`
- `test_cd_implementation_preflight_unit.py`

Historical Stage-2/3 and Stage-6 tests remain in the same Research Contract workflow.

## Acceptance gate

Before merge:

1. exact terminal head passes Research Contract;
2. changed-file audit remains within Stage-7 source/tests/docs/CI/ledger plus explicit safe
   `run.py` preflight dispatch;
3. no primary adaptive evaluation artifact exists;
4. PR #5 is merged normally, not squashed.

After merge:

1. create annotated tag `cd-implementation-ready-v1` on the accepted Stage-7 merge commit;
2. locally run `python run.py cd-preflight`;
3. confirm preflight success and clean worktree.

## Exact next stage

Create `stage8-cd-primary-evaluation` from the accepted/tagged implementation-ready commit.

**Do not immediately run the primary stream.**

First Stage-8 actions:

1. verify implementation-ready tag points to Stage-7 accepted merge;
2. run local `cd-preflight`;
3. freeze exact runtime environment/thread controls;
4. generate the primary run/config manifest package with protocol/source/checkpoint/config hashes;
5. commit that package;
6. require clean worktree and green CI on that exact config commit;
7. only then execute Phase A shared control-plane trajectories for seeds 0–4;
8. freeze/hash-verify Phase A before any C/D symbolic-arm evaluation.

Phase B then consumes the frozen shared trajectories for C, D-drift, and D-periodic.

No post-access parameter change is permitted except preserved/versioned implementation-defect
correction under the frozen doctrine.
