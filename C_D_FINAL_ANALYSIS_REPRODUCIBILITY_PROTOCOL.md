# C/D Final Statistical, Runtime, and Reproducibility Freeze

**Status:** PROSPECTIVE DESIGN FREEZE — FINAL PRE-IMPLEMENTATION CONTRACT  
**Branch:** `stage5-cd-design-audit`  
**Accepted parent:** `main` at `4c13d71a111ce7b72b3ef26a01b2918592425aa1`  
**Date:** 8 October 2026  
**Adaptive held-out execution:** PROHIBITED UNTIL IMPLEMENTATION-READY GATE

## 1. Purpose

This document removes the remaining material analytical and reproducibility degrees of freedom before
adaptive implementation begins.

It freezes:

- primary confirmatory endpoints;
- paired estimands, intervals/tests, and multiplicity;
- recovery/censoring/failure rules;
- runtime/backend/thread controls;
- write-once evidence families;
- fail-closed causal verifiers;
- the implementation test matrix;
- stage/branch order;
- the exact gate before first adaptive held-out access.

No result from primary adaptive C/D execution may be used to revise this contract without creating a
new disclosed protocol version and preserving the original evidence.

## 2. Primary inferential unit

The primary inferential unit remains:

> one matched seed-level treatment effect within the frozen primary scenario.

There are five matched seeds: 0,1,2,3,4.

Reporting windows, rules, drift events, symbolic opportunities, lifecycle transitions, and checkpoint
versions are longitudinal/nested observations. They are not independent replicates.

There is **no confirmatory window-level mixed model/GEE analysis in the primary scenario**.

Window trajectories are used for mechanism, delay, recovery, staleness and visualization only.
Confirmatory treatment effects are computed once per seed from prespecified whole-post-regime
endpoints.

## 3. Primary post-reference evaluation domain

The primary confirmatory domain is the entire frozen `post_drift` partition:

- 69,270 ordered rows;
- every prediction remains the prediction actually made under causal stream chronology;
- no post-hoc threshold refit;
- no removal of pre-publication rows;
- no conditioning on whether D successfully published a symbolic update.

This is intentionally an intention-to-treat-style adaptive trajectory estimand: delayed detection,
waiting, no-ops, censored maintenance, and late publication all contribute to the realized treatment
effect.

The evaluator-known boundary identifies the post domain only after the prediction trajectory is
frozen.

## 4. Confirmatory endpoint family

Exactly three endpoints form the primary confirmatory family.

### E1 — D-drift versus C post-regime MCC

For each seed:

`Delta_MCC_s = MCC_post(D-drift,s) - MCC_post(C,s)`.

MCC is computed from all 69,270 post-regime thresholded predictions under the frozen primary
lambda/threshold contract.

Interpretation:

- positive favors D-drift predictive performance;
- zero indicates no incremental thresholded predictive effect;
- negative indicates predictive cost.

D is **not required** to beat C on MCC for the symbolic contribution to remain scientifically
interesting. This endpoint prevents explanation gains from being discussed without disclosing
predictive consequences.

### E2 — D-drift versus C post-regime macro correct symbolic coverage

Define, for class `c in {0,1}`:

`correct_symbolic_coverage_c = N(y=c AND resolved_symbolic_prediction=c) / N(y=c)`.

A row contributes zero useful symbolic coverage when it is:

- uncovered;
- unresolved cross-class conflict/abstention;
- resolved to the wrong symbolic class.

Define:

`MCSC = 0.5 * (correct_symbolic_coverage_0 + correct_symbolic_coverage_1)`.

Then:

`Delta_MCSC_s = MCSC_post(D-drift,s) - MCSC_post(C,s)`.

This endpoint integrates explanation availability and correctness without allowing high correctness on
tiny coverage to appear automatically favorable.

The component quantities remain mandatory:

- benign coverage;
- attack coverage;
- benign symbolic correctness among covered;
- attack symbolic correctness among covered;
- conflict/abstention.

MCSC does not replace those components in reporting.

### E3 — D-drift versus D-periodic post-regime MCSC

For each seed:

`Delta_trigger_MCSC_s = MCSC_post(D-drift,s) - MCSC_post(D-periodic,s)`.

This tests whether the endogenous statistical trigger yields a more useful post-regime symbolic
trajectory than the frozen periodic maintenance schedule under the same operator and maximum
opportunity budget.

Trigger efficiency/cost quantities remain important secondary evidence rather than being hidden
inside a composite confirmatory score.

## 5. Secondary endpoint families

### 5.1 Detection / ranking

Mandatory secondary reporting includes:

- precision;
- recall;
- F1;
- FPR;
- ROC-AUC;
- average precision;
- TP/TN/FP/FN.

### 5.2 Explanation/lifecycle

Mandatory secondary reporting includes:

- class-conditional coverage;
- class-conditional symbolic correctness;
- neural fidelity;
- rule support;
- stability;
- complexity;
- active rule count;
- confidence trajectory;
- conflict/abstention;
- rule age;
- additions;
- refinements;
- merges;
- demotions;
- retirements;
- reactivations;
- rejected candidates by reason;
- staleness status;
- version count and lineage length.

### 5.3 Trigger/adaptation

Mandatory secondary reporting includes:

- detector event count;
- first post-boundary confirmation delay;
- pre-reference alarms;
- repeated alarms;
- neural response waiting rows;
- neural publication count;
- symbolic opportunity count;
- completed validation count;
- symbolic publication count;
- no-op count;
- censored/aborted count by reason;
- maintenance attempts avoided;
- publication/opportunity ratio;
- cost per opportunity;
- cost per publication.

Ratios with zero denominators are recorded as undefined, never replaced by zero.

### 5.4 Forgetting / retention

Report the already frozen development-retention and offline pre-regime checkpoint probes.
These are secondary longitudinal diagnostics and never feed adaptation.

## 6. Primary paired effect summary

For each confirmatory endpoint retain the five raw paired effects.

Primary effect estimate:

`mean_delta = arithmetic mean of the five paired seed effects`.

Mandatory descriptive companions:

- median paired effect;
- sample SD of paired effects;
- minimum/maximum;
- number positive / zero / negative;
- all five individual paired values;
- leave-one-seed-out mean-effect range.

No seed is hidden because it is inconvenient.

## 7. Primary confidence interval

The primary interval is the conventional 95% Student-t interval over the five paired seed
differences:

`mean_delta +/- t_(0.975, df=4) * sd_delta/sqrt(5)`.

This interval is explicitly interpreted as uncertainty over the project's stochastic seed variation
**conditional on the fixed scenario**.

It is not an environmental/deployment-population interval.

With five seeds, normality cannot be meaningfully diagnosed. Therefore:

- no low-power normality pretest is used to choose the interval;
- the raw five effects and leave-one-seed-out range are mandatory alongside the interval;
- an interval crossing zero is not converted into a claim of "no effect";
- stored intervals are not clipped to metric bounds.

No bootstrap interval is primary because five seed pairs are too few for a bootstrap procedure to
create credible environmental information absent from the experiment.

## 8. Exact sign-consistency test

A p-value is secondary calibration, not the success criterion.

For each confirmatory endpoint use an exact one-sided sign test of:

`H0: P(paired effect > 0) <= 0.5`

versus

`H1: P(paired effect > 0) > 0.5`.

Rules:

- zero paired differences are removed from the sign-test denominator;
- report `n_effective`;
- the exact binomial probability under p=.5 is used;
- direction is frozen as positive-benefit before outcomes;
- also report the raw positive/zero/negative sign pattern.

The sign test deliberately ignores effect magnitude; magnitude is carried by the paired estimate and
interval.

Because the five seeds share the same stream, this p-value is not evidence of five independent
environments.

## 9. Multiplicity

The three confirmatory sign-test p-values form one family.

Use Holm-Bonferroni step-down adjustment at familywise alpha=.05.

Report both raw and Holm-adjusted p-values.

No manuscript conclusion is reduced to whether adjusted p<.05. With five seed pairs the attainable
p-value grid is coarse; this is a design limitation, not permission to inflate n using windows or
rules.

All secondary endpoint p-values, if computed, are labeled exploratory/descriptive and are not mixed
with the confirmatory family.

## 10. Practical interpretation

No arbitrary minimum clinically/practically important difference is invented for MCC or MCSC because
the project lacks a defensible external domain standard for such a margin.

Interpretation therefore uses:

- absolute paired effect magnitude;
- raw seed consistency;
- 95% interval;
- longitudinal mechanism;
- predictive/explanation trade-off;
- trigger/cost behavior;
- prespecified robustness;
- later scenario/dataset replication.

A favorable explanation endpoint with predictive degradation must be reported as a trade-off, not a
win.

## 11. Recovery definitions

Recovery outcomes are secondary.

For any higher-is-better windowed metric:

1. define the pre-reference baseline as the **row-count-weighted mean of the final three frozen
   pre-drift reporting windows** for that system/seed;
2. a post window qualifies as recovered when its metric is >= that baseline;
3. recovery is declared at the first qualifying post window whose immediately following post window
   also qualifies;
4. recovery clock = start row of the first qualifying post window;
5. if no two-window persistent recovery occurs, recovery time is right-censored at stream end.

For lower-is-better metrics the inequality is reversed.

The final post window cannot establish persistence without a subsequent window and therefore cannot
alone create a recovery event.

Recovery time is reported in logical rows from the controlled boundary.

No tolerance band is introduced after outcomes are observed.

For a claim specifically labeled **symbolic recovery**, the stricter lifecycle chain in
`D_SYMBOLIC_LIFECYCLE_PROTOCOL.md` also applies.

## 12. Missing, censored, and failed trajectories

### 12.1 Scientific zero/no-update outcomes

The following are valid outcomes, not missing data:

- no detector event;
- no executable neural response;
- no accepted symbolic candidate;
- no symbolic publication;
- validated no-op;
- symbolic budget exhaustion;
- right-censored symbolic validation;
- checkpoint supersession.

The realized prediction stream is still scored.

No favorable update is imputed.

### 12.2 Technical/protocol failure

A run may be repeated only for documented invalidating failure such as:

- artifact corruption;
- hash mismatch;
- violated causal invariant;
- wrong data/preprocessing identity;
- code crash before required prediction completion;
- non-finite model state;
- discovered implementation defect.

The failed artifact/log remains preserved.

A corrected rerun receives a new run/version identity and explicit methodology-ledger entry.

### 12.3 Confirmatory missingness

The primary analysis requires all five seed-level post-regime prediction streams.

If a seed is unavailable because of unresolved technical/protocol failure, the confirmatory analysis
is not silently reduced to n=4.

Report the incomplete family and do not claim the prespecified five-seed confirmatory analysis until
the failure is validly resolved.

## 13. Prespecified robustness package

The primary result is never replaced by a more favorable sensitivity.

Already frozen robustness conditions include:

- label latency L=0 and L=10,000;
- Page-Hinkley detector on the same delayed hard-error signal;
- ADWIN on delayed Brier loss;
- no-replay neural fine-tuning;
- lambda=.70 and lambda=.90 fusion authority;
- lambda=1.00 neural-only causal negative control.

Additional reporting-window sensitivity:

- non-overlapping 2,500-row windows;
- non-overlapping 10,000-row windows.

These affect longitudinal descriptive/recovery summaries, not the whole-post confirmatory endpoints.

Symbolic gate sensitivity:

- static-style gate with support>=.001, covered>=100, point precision>=.80,
  point fidelity>=.90, bootstrap persistence>=.90, complexity<=4;
- no Wilson lower-bound requirement.

This is a robustness condition testing dependence on the online uncertainty-aware gate. It cannot
replace the primary gate.

Existing System-B duplicate/multiplicity robustness remains contextual evidence; it is not used to
retune C/D.

## 14. Scenario/dataset replication

The primary scenario remains a controlled BENIGN-source-regime-dominant proving ground.

Before broad publication claims, the project should add:

- at least one scenario with a more direct attack-pattern / conditional-label change opportunity;
- a defensible second flow-oriented dataset where feature/label semantics permit the higher-level
  causal protocol without artificial harmonization.

Scenario/dataset effects are reported separately first.

The five seeds from different scenarios are not pooled as if they were independent environments.

## 15. Runtime and deterministic execution contract

Primary adaptive execution is CPU-only.

Before Python imports that initialize numerical thread pools, set:

- `PYTHONHASHSEED=0`;
- `OMP_NUM_THREADS=1`;
- `MKL_NUM_THREADS=1`;
- `OPENBLAS_NUM_THREADS=1`;
- `NUMEXPR_NUM_THREADS=1`.

Inside the process:

- Python 3.11.9 exactly;
- frozen `requirements-lock.txt`;
- `torch.set_num_threads(1)`;
- `torch.set_num_interop_threads(1)`;
- deterministic PyTorch algorithms requested;
- DataLoader workers=0;
- all already frozen project RNG seeds/configuration;
- no GPU/CUDA primary execution.

Record `threadpoolctl.threadpool_info()` in the runtime manifest and fail the primary run if an
identified BLAS/OpenMP numerical pool is using more than one thread after controls are applied.

Record:

- OS/platform;
- CPU model where available;
- logical/physical CPU count where available;
- Python package versions;
- Git commit/branch;
- environment variables above;
- torch deterministic settings;
- threadpool inventory.

## 16. Cost measurement scope

Use `time.perf_counter_ns()` for monotonic wall-clock component timing.

Record non-overlapping or clearly nested scopes for:

- stream neural prediction;
- detector update/event handling;
- neural evidence assembly;
- neural training;
- checkpoint serialization;
- SHAP candidate generation;
- surrogate fitting;
- symbolic validation;
- lifecycle/conflict resolution;
- rule-version serialization;
- whole-run wall clock.

Also record:

- processed row counts;
- detector-input counts;
- minibatch counts;
- evidence waiting rows;
- checkpoint bytes;
- rule/version artifact bytes.

Peak memory is optional/descriptive where a cross-platform method is available; absence of a reliable
memory measure does not invalidate the run and must not be filled by an incomparable proxy.

Timing is measured once on the realized primary trajectory. It is not a benchmark tournament and is
not converted to production throughput because arrival timestamps are not defensible.

## 17. Write-once evidence families

The implementation must produce versioned, non-overwriting evidence.

Minimum families:

1. **run manifest JSON**
   - protocol/config hashes;
   - Git identity;
   - runtime identity;
   - scenario/preprocessing/checkpoint identities;
   - arm/seed;
   - parent artifacts;
   - completion/failure status.

2. **shared control-plane event log**
   - prediction/label maturity;
   - detector inputs/events;
   - neural transaction events;
   - replay/current evidence hashes;
   - checkpoint publications.

3. **shared checkpoint inventory**
   - parent/child SHA-256 chain;
   - event identity;
   - evidence/config/RNG identities;
   - publication-effective clock.

4. **arm prediction table**
   - logical row identity;
   - neural score;
   - symbolic status/score;
   - lambda;
   - fused score;
   - thresholded decision;
   - checkpoint/version IDs.

5. **symbolic maintenance event log**
   - opportunity source/clock;
   - candidate-generation evidence;
   - validation evidence;
   - lifecycle decisions;
   - censored/no-op/publication status.

6. **rule revision/version artifacts**
   - semantic/revision/lineage/parent IDs;
   - validation metrics/Wilson bounds;
   - confidence/state/relations;
   - valid-from/to;
   - canonical hash.

7. **metrics/evaluation evidence**
   - seed/arm whole-regime metrics;
   - window metrics;
   - confirmatory paired-effect table;
   - secondary/cost/lifecycle tables.

All compact evidence referenced by a manifest is hash-verified before acceptance.

## 18. Common event-envelope fields

Every event record must contain at minimum where applicable:

- schema_version;
- run_id;
- seed;
- arm;
- event_type;
- event_id;
- logical_clock;
- origin_index when delayed evidence is involved;
- maturity_index when label-dependent;
- parent_event_id where applicable;
- neural_checkpoint_sha256;
- rule_base_version_id where applicable;
- evidence_sha256/config_sha256 where applicable;
- Git commit;
- status/reason.

Event-specific schemas may add fields but may not omit causal provenance required to reconstruct why
the action was legal at that time.

## 19. Fail-closed causal verifiers

Before results are accepted, automated verifiers must fail on any violation of:

### V1 — shared control-plane identity

Matched C and D reference the exact same:

- detector-event artifact hash;
- label-availability schedule hash;
- replay/current-evidence identities;
- neural checkpoint chain hashes.

### V2 — information timing

No adaptive evidence row has:

- origin_index > action clock;
- maturity_index > action clock when a label is required.

No prediction is overwritten after later labels/updates.

### V3 — checkpoint purity

Detector epochs and symbolic validation blocks contain only predictions from the required checkpoint
identity.

### V4 — threshold/fusion identity

Matched C/D use the frozen seed-specific lambda/threshold configuration.

### V5 — lambda=1.00 negative control

For matched rows, C and D neural-only sensitivity fused scores and thresholded predictions must be
exactly identical. Any difference is an implementation defect.

### V6 — symbolic generation/validation separation

No row ID used for candidate-generation evidence may appear in that transaction's independent
symbolic-validation block.

Validation rows must be post-child-publication and label-mature under the frozen timing contract.

### V7 — trigger-ablation operator identity

D-drift and D-periodic reference the same symbolic operator configuration hash and maximum
opportunity budget.

Periodic target clocks must equal exactly:

`27706, 55412, 83118, 110824`.

### V8 — symbolic lifecycle integrity

No active rule revision lacks:

- lineage;
- validation evidence;
- current checkpoint identity;
- valid-from clock;
- lifecycle transition history.

No rejected/retired rule is deleted from historical evidence.

### V9 — no boundary contamination

The adaptive control plane and symbolic operator execution inputs contain no synthetic-boundary flag
or post/pre partition indicator.

### V10 — write-once/hash integrity

Accepted evidence cannot be overwritten in place and all manifest-referenced hashes verify.

Any verifier failure blocks scientific acceptance of that run.

## 20. Repository test matrix before held-out execution

Implementation must add repository-only tests using toy/generated fixtures and, where explicitly
allowed, training/development evidence.

Minimum test families:

- delayed-label prediction-before-release;
- no boundary reset/flush;
- end-of-stream pending-label censoring;
- ADWIN input uses stored original prediction;
- detector checkpoint-pure re-arm;
- replay reservoir deterministic admission/eviction;
- current/replay row exclusion and hash identity;
- deterministic child checkpoint reproduction;
- C/D shared checkpoint reference;
- fixed monitor/fusion threshold identities;
- lambda=1 exact prediction equality;
- candidate generation/validation row disjointness;
- Wilson lower-bound edge cases including n=24/n=25 perfect-fidelity boundary;
- weighted CART leaf consequent regression test;
- lifecycle retain/demote/retire/reactivate;
- refinement/merge deterministic tie breaks;
- unresolved conflict abstention;
- symbolic supersession/right-censoring;
- periodic exact target clocks and four-slot budget;
- trigger-arm operator config identity;
- write-once artifact refusal;
- manifest/hash corruption failure;
- all causal verifiers above.

CI must be extended to execute the new repository-only tests before the implementation stage is
accepted.

## 21. Stage and branch sequence

### Stage 5 — current design freeze

Complete this design-only branch.

After CI passes and review confirms no material C/D design TBD remains:

1. merge draft PR #3 to `main` with history preserved;
2. create immutable annotated tag `cd-design-freeze-v1`.

### Stage 6 — shared adaptive control-plane implementation

Create:

`stage6-cd-control-plane`

from tagged/accepted design-freeze `main`.

Implement:

- stream clock/label queue;
- shared detector;
- replay memory;
- neural adaptation transactions;
- checkpoint manifests;
- shared event schemas;
- control-plane verifiers.

Allowed execution before acceptance:

- toy/generated fixtures;
- frozen training/development evidence where required;
- **no primary pre/post adaptive execution**.

Merge only after repository tests and CI pass.

### Stage 7 — symbolic lifecycle and evaluation implementation

Create:

`stage7-cd-symbolic-lifecycle`

from accepted Stage-6 `main`.

Implement:

- D lifecycle operator;
- independent validation;
- periodic scheduler;
- C/D arm evaluator;
- lambda sensitivities;
- confirmatory/secondary analysis builders;
- remaining symbolic/verifier tests.

Again, no primary pre/post adaptive execution during implementation/debugging.

After CI passes, accept to `main` and create annotated tag:

`cd-implementation-ready-v1`.

### Stage 8 — primary adaptive evaluation

Create:

`stage8-cd-primary-evaluation`

from `cd-implementation-ready-v1`.

No scientific code/protocol changes are permitted on this branch except a documented implementation
defect correction that preserves the original failed evidence and versions the correction.

## 22. Held-out access gate

Before first primary adaptive pre/post execution, all of the following must be true:

1. `STATISTICAL_ANALYSIS_PLAN.md` is version 1.0 with no material C/D TBD;
2. control register has no unresolved material C/D freeze item;
3. Stage-6/7 repository tests pass locally;
4. CI is green on exact `cd-implementation-ready-v1` commit;
5. all five accepted System-A checkpoint bytes exist locally and match frozen SHA-256 values;
6. scenario/preprocessing manifests verify;
7. all synthetic/toy causal-verifier tests pass;
8. a primary run manifest/config package is generated and committed;
9. run manifest contains exact config/protocol hashes, external artifact hashes and runtime contract;
10. worktree is clean;
11. no primary pre/post adaptive output has been inspected to select/tune a remaining parameter.

If any item fails, held-out execution remains locked.

## 23. Primary execution order after gate

The held-out stream is accessed in two frozen phases.

### Phase A — freeze shared control-plane trajectories

For each seed, execute the primary stream once to generate:

- immutable neural predictions;
- delayed-label/control-plane events;
- detector events;
- replay/evidence identities;
- child neural checkpoint chain.

Freeze and hash-verify those shared artifacts **before** evaluating symbolic treatment arms.

No C/D symbolic outcome is needed to generate the shared trajectory.

### Phase B — consume the frozen shared trajectory

System C, D-drift and D-periodic consume the exact same frozen shared control-plane trajectory.

This means treatment arms cannot alter:

- drift events;
- replay;
- neural updates;
- checkpoint timing.

Their causal difference is confined to symbolic state/trigger policy as designed.

## 24. Post-access change doctrine

After any primary adaptive held-out output has been inspected:

- poor performance cannot justify tuning;
- unexpected zero events cannot justify changing detector parameters;
- sparse symbolic publication cannot justify weakening gates;
- adverse neural forgetting cannot justify changing replay/budget;
- trigger-ablation direction cannot justify moving periodic clocks.

A realized implementation defect is handled by preserving the failed evidence, fixing only the defect,
versioning the rerun, and documenting whether scientific conclusions changed.

A design limitation becomes sensitivity/future work, not a silent restart.

## 25. Publication interpretation

Primary evidence will be strongest when conclusions distinguish:

- causal treatment effect within this controlled scenario;
- stochastic seed variability;
- longitudinal mechanism;
- trigger efficiency;
- explanation validity;
- external-validity limitations.

A null/mixed C-vs-D result is scientifically valid.

The paper's novelty claim is the controlled evidence about drift-gated validated symbolic lifecycle
value, not a guarantee that symbolic evolution always improves predictive metrics.

## 26. Gate

**Final prospective C/D design packet: FROZEN.**

After this packet is propagated into the statistical plan/control register/handoff, passes CI, and is
accepted into `main` with tag `cd-design-freeze-v1`, adaptive **implementation** may begin.

Adaptive **held-out execution remains prohibited** until the later
`cd-implementation-ready-v1` gate in Section 22.
