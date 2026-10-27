# Stage 9 Prespecified Robustness Execution Protocol

**Status:** POST-PRIMARY PROSPECTIVE ROBUSTNESS FREEZE — NO ROBUSTNESS OUTCOMES ACCESSED  
**Parent immutable primary evidence:** `c2ded83b8195b9321e715626c1f305f9627936e8`  
**Primary compact-export manifest:** `409b516d75cbc5e71d3633019008432ea6088d1d923b4e4a95570263528ed523`  
**Primary confirmatory aggregate:** `1be77ce4be9f3faad021a3f3bfd636488e5de6aa1b2a6e7c596e48feb41bb54d`

## 1. Purpose

Stage 9 executes only robustness conditions that were frozen before the primary C/D outcomes were
inspected.

No Stage-9 result may replace, retune, or redefine the immutable Stage-8 primary result.

Stage 9 is additive evidence answering whether the Stage-8 conclusions depend materially on
prespecified high-leverage choices.

## 2. Primary result remains authoritative

The following Stage-8 findings are immutable:

- E1 post-MCC D-drift minus C;
- E2 post-MCSC D-drift minus C;
- E3 post-MCSC D-drift minus D-periodic;
- five frozen seed identities;
- primary lambda=.50;
- primary L=5,000;
- primary delayed hard-error ADWIN detector;
- primary replay-enabled neural adaptation;
- primary online uncertainty-aware symbolic gate;
- primary 5,000-row reporting windows.

Robustness may strengthen, weaken, or reverse confidence in interpretation, but may not overwrite the
primary artifacts.

## 3. Stage-9 condition families

### 3.1 Offline-only robustness

These conditions use immutable Stage-8 trajectories and do not rerun adaptive state:

1. fusion authority lambda=.70;
2. fusion authority lambda=.90;
3. lambda=1.00 neural-only causal negative control;
4. 2,500-row reporting-window sensitivity;
5. 10,000-row reporting-window sensitivity.

The Stage-8 Phase-C artifacts already contain lambda=.70/.90/1.00 row decisions/metrics. Stage 9
must read those frozen artifacts rather than recompute or refit thresholds.

Reporting-window sensitivities may be recomputed only from the immutable Stage-8 prediction traces
and frozen rule-state trajectories. They do not alter whole-post confirmatory endpoints.

### 3.2 Adaptive control-plane robustness

These conditions require new matched adaptive runs:

1. label latency L=0;
2. label latency L=10,000;
3. River PageHinkley on the same delayed checkpoint-pure hard-error signal;
4. ADWIN on delayed checkpoint-pure Brier loss;
5. neural no-replay ablation using the same current window, optimizer and update budget.

Each condition is a separate robustness family. All five seeds are retained.

The designated scenario boundary remains scoring-only.

### 3.3 Symbolic-operator robustness

The static-style symbolic gate sensitivity is:

- support >= .001;
- covered >= 100;
- point precision >= .80;
- point neural fidelity >= .90;
- 100-replicate full-gate bootstrap persistence >= .90;
- complexity <= 4;
- no Wilson lower-bound requirement.

This condition may reuse the immutable primary shared control-plane trajectories because it changes
only symbolic validation/lifecycle acceptance. It must rerun all symbolic arms affected by the gate
under a new write-once Stage-9 identity.

## 4. Runtime strategy

The primary Stage-8 run remains bound to its original frozen Windows CPU environment.

Stage 9 has not yet begun. Because the adaptive robustness package requires substantially more than
five expensive runs, Stage 9 may prospectively use a cloud CPU environment.

A generic notebook session is not accepted as the scientific runtime merely for convenience.

Preferred execution target:

- dedicated x86_64 Linux cloud VM;
- Python 3.11.9 exactly;
- exact frozen `requirements-lock.txt`;
- CPU-only execution;
- `PYTHONHASHSEED=0`;
- OMP/MKL/OpenBLAS/NumExpr threads=1;
- PyTorch deterministic algorithms;
- torch intra/inter-op threads=1;
- DataLoader workers=0;
- exact installed-distribution inventory frozen before first Stage-9 adaptive access;
- machine/platform/CPU metadata recorded in the Stage-9 run config.

Colab may be used only if the same runtime contract can be verified and frozen for the entire
condition family. A dedicated VM is preferred because notebook runtimes can change underneath a run.

## 5. Cross-runtime baseline requirement

If Stage 9 executes on a runtime different from Stage 8, a matched Stage-9 baseline replication of
the primary condition is mandatory before interpreting adaptive robustness deltas.

The Stage-9 baseline uses:

- L=5,000;
- primary delayed hard-error ADWIN;
- replay enabled;
- primary online symbolic gate;
- lambda=.50;
- same five seeds;
- same scenario and accepted System-A/R0.v2 start states.

The Stage-9 baseline does not replace Stage 8.

Its purpose is to separate a runtime/platform effect from a robustness-condition effect.

Variant effects are compared primarily against the matched Stage-9 baseline when runtime differs.

The Stage-8 primary result remains reported independently.

## 6. Execution grouping

To avoid unnecessary reruns:

### Group O — offline robustness

No adaptive rerun:

- lambda=.70;
- lambda=.90;
- lambda=1.00 verification;
- 2,500-row windows;
- 10,000-row windows.

### Group G — symbolic-gate robustness

Reuse each frozen Stage-8 Phase-A shared trajectory.

Run:

- C frozen symbolic;
- D-drift static-style gate;
- D-periodic static-style gate;

with the exact accepted R0.v2 start state and the frozen primary trigger/control-plane evidence.

### Group A — adaptive robustness

For each of:

- Stage-9 matched baseline when required by runtime;
- L=0;
- L=10,000;
- PageHinkley hard-error;
- ADWIN Brier;
- no-replay;

execute the full matched shared-control-plane -> symbolic-arm -> offline-evaluation chain for seeds
0..4.

No condition is stopped because early seeds are unfavorable.

## 7. Detector semantics

### 7.1 PageHinkley

PageHinkley receives the identical checkpoint-pure delayed hard-error observation sequence that the
primary ADWIN monitor would receive under the same latency/runtime condition.

Its configuration must be frozen before any robustness held-out execution.

The implementation must not select PageHinkley parameters by looking at Stage-8 trigger clocks or
outcome direction.

### 7.2 ADWIN Brier

The Brier monitor receives:

`(stored neural probability - mature true label)^2`

from the prediction that was actually made for that row under the active checkpoint.

Checkpoint-purity, post-update disarming, delayed-label maturity and stale-error quarantine remain
identical to the primary monitor semantics.

The primary ADWIN structural parameters remain unchanged unless the frozen protocol explicitly
requires a different value. No Stage-8 outcome-dependent tuning is permitted.

## 8. No-replay semantics

No-replay changes only the adaptation training set.

At an otherwise executable neural response:

- use the same current mature window;
- use the same optimizer;
- use the same learning rate;
- use the same weight decay;
- use the same batch size;
- use the same number of epochs;
- use the same shuffle-seed namespace;
- omit all replay rows.

Detector observations, label timing, update eligibility and symbolic treatment logic remain matched.

The no-replay implementation must not silently reduce current-window size or substitute replay rows
from another source.

## 9. Output separation

Stage-9 heavy evidence must be written under a new Git-ignored root, for example:

`artifacts/cd_robustness_v1/`

Compact evidence must be exported only after verification to:

`results/frozen/cd_robustness_v1/`

No Stage-8 file is overwritten.

Every Stage-9 artifact records:

- Stage-8 parent evidence commit;
- Stage-9 config hash;
- condition ID;
- seed;
- runtime identity;
- scenario/preprocessing identity;
- accepted System-A/R0.v2 identities;
- relevant control-plane/symbolic config identity;
- parent/shared-trajectory identity where applicable.

## 10. Analysis rules

Robustness results are reported condition-by-condition.

Do not:

- pool Stage-9 conditions as independent replicates;
- select the most favorable detector/latency/gate as a replacement primary;
- redefine endpoints after seeing variant outcomes;
- promote windows/events/rules to inferential units.

For each variant report:

- all five paired seed effects versus its matched reference;
- mean/median/SD/min/max;
- sign pattern;
- leave-one-seed-out mean range;
- the frozen primary-style interval where scientifically applicable;
- trigger timing/censoring;
- maintenance/publication cost;
- explanation coverage/MCSC;
- whether the qualitative Stage-8 conclusion is strengthened, weakened or reversed.

No new confirmatory family is created unless separately prospectively frozen before the corresponding
robustness outcomes are accessed.

## 11. Trigger-quality focus

Stage 8 observed repeated pre-reference detector events and 7/8 D-drift symbolic publications before
the designated boundary.

This observation motivates careful reporting but does **not** authorize detector retuning.

Stage-9 PageHinkley/Brier and latency variants were already prespecified before Stage-8 outcomes and
therefore may be executed as planned.

Their interpretation must explicitly report:

- pre-reference alarm count;
- first post-reference confirmation delay;
- latency-adjusted excess delay;
- opportunity-budget consumption;
- symbolic publication clocks relative to the boundary;
- completed/censored validation counts.

## 12. External-validity boundary

Stage 9 is robustness on the same primary scenario.

It does not discharge the separately required obligations for:

- a direct attack-pattern / conditional-label-change scenario;
- gradual drift where defensible;
- unseen-attack introduction where defensible;
- a second flow-oriented dataset.

Those remain later replication stages.

## 13. Freeze gate before Stage-9 adaptive access

Before the first new adaptive robustness row is processed:

1. Stage-9 implementation and tests must be committed;
2. the Stage-9 run config must be generated without loading held-out primary partitions;
3. the config must freeze runtime, variant definitions and relevant source/protocol hashes;
4. the config must be the only path in its freeze commit;
5. exact-head CI must pass;
6. the Stage-8 immutable evidence commit and manifests must verify;
7. if a cloud runtime is used, its environment inventory must match the frozen Stage-9 config.

After first Stage-9 adaptive access, no robustness parameter may be changed because of observed
direction.
