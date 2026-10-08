# Stage 7 — Symbolic Lifecycle and C/D Evaluation Implementation

**Status:** IMPLEMENTATION COMPLETE — PENDING EXACT-HEAD CI AND MILESTONE ACCEPTANCE  
**Branch:** `stage7-cd-symbolic-lifecycle`  
**Accepted parent:** Stage-6 `main` at `f11f2709bc1f6a32a7c416012860342d9a772ff7`  
**Date:** 8 October 2026  
**Primary adaptive pre/post execution:** PROHIBITED

## 1. Scope

Stage 7 implements the symbolic treatment and analysis machinery frozen in Stage 5 on top of the
accepted shared control plane from Stage 6.

In scope:

- accepted R0.v2 migration into an explicit revision/lineage lifecycle schema;
- online candidate generation;
- independent future validation;
- Wilson/bootstrap gate;
- retain/demote/retire/reactivate/refine/merge/conflict lifecycle;
- immutable symbolic maintenance/version evidence;
- D-drift and D-periodic arm scheduling;
- frozen C arm;
- arm consumption of one immutable shared neural/control-plane trajectory;
- dynamic fusion/evaluation;
- lambda=1 causal negative control;
- MCSC;
- frozen confirmatory analysis builders;
- trigger-efficiency/cost summaries;
- implementation-readiness preflight without primary partition access.

Out of scope:

- primary adaptive pre/post execution;
- outcome inspection/tuning;
- changes to Stage-5 detector/neural/replay/fusion/symbolic/statistical design.

## 2. Implemented modules

### `cd_symbolic_lifecycle.py`

Implements:

- primary online rule gate;
- one-sided 95% Wilson lower bounds;
- bootstrap full-gate persistence;
- R0.v2 semantic migration;
- rule semantic/revision/lineage identities;
- staleness evidence;
- active -> retained/demoted;
- demoted -> reactivated/retired;
- retired -> reactivated;
- exact semantic reactivation;
- new additions;
- same-class consolidation;
- stale-rule refinement with lineage preservation;
- cross-class Pareto demotion;
- deterministic unresolved conflict relations;
- separate inference rule-base hash and lifecycle-history hash;
- fail-closed lifecycle-state verifier.

The split between inference hash and lifecycle-history hash is intentional. Audit-only transitions such
as `demoted -> retired` can advance lifecycle history without falsely publishing a new predictive
rule-base version.

### `cd_symbolic_candidates.py`

Implements the frozen online proposal mechanism:

- DeepExplainer on raw attack logit;
- balanced background up to 128/class;
- balanced attribution sample up to 1,024/class;
- top-12 normalized SHAP feature ranking;
- deterministic Stage-5 symbolic seed namespace;
- weighted CART, gini/best, depth 4, min leaf 100;
- equal-total neural predicted-class weights;
- fitted weighted CART leaf argmax consequent;
- deterministic canonical rule paths;
- optional raw-threshold reconstruction;
- nanosecond monotonic timing.

### `cd_r0_lifecycle.py`

Loads only the accepted R0.v2 identity:

- manifest SHA fixed to `131027d2f136494eb388183f18dcb7eb0e9d7e9fe786f22dba25f4e1624c1483`;
- raw rule artifact hashes verified;
- canonical rule artifact hashes verified;
- exact active counts 7/6/7/6/6;
- migration changes metadata/lifecycle representation only, not antecedent/consequent/confidence semantics.

### `cd_symbolic_arms.py`

Implements:

- four-slot drift opportunity budget;
- exact D-periodic clocks 27,706 / 55,412 / 83,118 / 110,824;
- one operator configuration hash;
- exactly 10,000 generation row IDs per primary opportunity;
- independent checkpoint-pure validation;
- explicit `validation_start_index`;
- class-diversity requirement;
- right censoring;
- checkpoint supersession;
- primary symbolic-operator verifier.

### `cd_symbolic_runner.py`

Implements dataset-agnostic symbolic arm orchestration.

All arms require:

- same seed;
- same accepted migrated R0 starting inference hash;
- same frozen shared-control-plane identity.

D trigger arms additionally require the same symbolic operator hash.

The runner consumes:

- shared prediction/evidence/checkpoint artifacts;
- caller-supplied feature/label row view;
- caller-supplied checkpoint model resolver.

It does not create neural updates or drift events.

Periodic validation begins **after the scheduled maintenance clock**, even if the active neural
checkpoint was published much earlier.

D-drift validation begins after the associated child checkpoint becomes effective.

A symbolic publication is refused when its causal effective index would collide with or follow a
shared neural supersession of the checkpoint against which it was validated.

Per-opportunity cost fields include SHAP, surrogate, lifecycle and validation-wait quantities.

### `cd_symbolic_evidence.py`

Implements write-once:

- maintenance-event artifacts;
- published rule-base-version artifacts;
- parent version/hash provenance;
- inference canonical hash;
- lifecycle-history hash;
- validation-start provenance;
- serialization timing;
- symbolic version-chain verification.

Every opportunity can therefore leave audit evidence even when no predictive version is published.

### `cd_symbolic_evaluation.py`

Implements:

- accepted lambda=.50 thresholds;
- frozen lambda=.70/.90 sensitivity thresholds;
- lambda=1.0 neural-only control;
- MCSC and class-specific components;
- static and dynamic symbolic trajectory evaluation;
- prediction provenance rows;
- exact lambda=1 matched-prediction verifier.

### `cd_analysis.py`

Implements:

- E1/E2/E3 frozen confirmatory family;
- five paired seed effects;
- arithmetic mean;
- Student-t 95% interval, df=4;
- raw sign pattern;
- leave-one-seed-out mean range;
- exact one-sided sign test;
- Holm-Bonferroni;
- two-window persistent recovery;
- symbolic opportunity/validation/publication/no-op/censoring summaries;
- maintenance cost and lifecycle-decision summaries.

### `cd_implementation_preflight.py`

Implements a no-primary-partition readiness check for:

- Python 3.11.9;
- required frozen governance/protocol documents;
- SAP v1.0;
- scenario raw/canonical manifest identities;
- preprocessing state identity;
- accepted System-A manifest;
- all five System-A checkpoint bytes/hashes when run locally;
- accepted R0.v2 manifest/rule artifacts;
- frozen primary control-plane configuration;
- frozen primary symbolic-operator configuration.

The preflight contains no partition loader and does not execute the adaptive stream.

CI deliberately tests that a workspace lacking external checkpoint bytes fails closed rather than
being reported ready.

## 3. Prospective defects/corrections caught during Stage 7

### 3.1 Toy Wilson fixture error

The first Stage-7 CI run failed because a test-only helper used a Wilson-LCB threshold of .60 with
only four perfectly correct covered rows. The one-sided 95% Wilson lower bound is below .60 at that
toy n, so the implementation correctly rejected the rule.

Correction:

- changed only the toy gate fixture to .50;
- primary frozen precision/fidelity LCB thresholds remain .80/.90;
- no scientific protocol or primary parameter changed.

### 3.2 Periodic validation chronology defect

A real orchestration defect was found prospectively.

Initial code anchored D-periodic validation only to the current neural checkpoint's publication
index. If a checkpoint had been active long before a periodic target, that could admit validation
rows that occurred before the periodic maintenance opportunity.

Correction:

- added explicit `validation_start_index`;
- D-periodic sets it to `target_clock + 1`;
- D-drift keeps child-checkpoint effective index;
- validation evidence records this field;
- a regression test proves pre-target rows cannot enter periodic validation.

This correction occurred before any primary adaptive pre/post execution.

### 3.3 Stale refinement / conflict-history hardening

Adversarial code audit identified two state-machine risks:

- a newly demoted stale incumbent could be omitted from candidate refinement parent selection;
- unresolved cross-class relations could accumulate stale/duplicate relation entries across updates.

Correction:

- stale same-class incumbents remain eligible as refinement parents;
- successful refinement preserves their lineage;
- unresolved conflict relations are deterministically rebuilt from the final surviving active rule set
  after each completed maintenance decision;
- adversarial tests cover stale-lineage preservation and one-to-many unresolved conflicts.

No frozen lifecycle threshold or operator rule changed.

## 4. Tests

Research Contract CI executes:

- `tests/test_cd_symbolic_lifecycle_unit.py`;
- `tests/test_cd_symbolic_candidates_unit.py`;
- `tests/test_cd_symbolic_arms_analysis_unit.py`;
- `tests/test_cd_symbolic_runner_evidence_unit.py`;
- `tests/test_cd_implementation_preflight_unit.py`.

Coverage includes:

- Wilson n=24/n=25 boundary;
- accepted R0.v2 identity/migration;
- weighted leaf consequent;
- deterministic symbolic RNG namespace;
- demotion/retirement/reactivation;
- stale refinement lineage;
- multi-conflict relation completeness;
- periodic clock exactness;
- four-slot drift budget;
- independent validation;
- periodic validation-after-target chronology;
- supersession;
- MCSC;
- lambda=1 equality;
- five-seed statistics/Holm;
- recovery persistence;
- trigger-efficiency accounting;
- shared prediction identity;
- shared seed/R0/control-plane invariants;
- symbolic write-once evidence/version chain;
- Stage-7 scenario-loader firewall;
- no-data implementation preflight.

## 5. Held-out status

**LOCKED.**

No primary adaptive pre/post execution has occurred or been inspected in Stage 7.

No Stage-7 runtime module imports `scenario_loader` or `load_partition`.

## 6. Implementation-ready acceptance gate

Stage 7 may be accepted only when:

1. exact terminal head passes Research Contract CI;
2. Stage-7 changed-file audit contains only implementation/tests/governance artifacts;
3. no primary evaluation outputs exist;
4. PR #5 is merged normally with scientific history preserved;
5. accepted merge commit is annotated locally as `cd-implementation-ready-v1`;
6. project owner runs the local no-data implementation-ready preflight with external System-A
   checkpoint bytes present and confirms success.

Only then may Stage 8 prepare the primary run/config manifest.

The primary adaptive stream still cannot be executed until the Stage-8 run manifest/config is
committed, the worktree is clean, and all frozen runtime/environment controls are satisfied.
