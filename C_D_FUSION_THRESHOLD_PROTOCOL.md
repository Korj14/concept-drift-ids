# C/D Fusion and Operational-Threshold Protocol

**Status:** PROSPECTIVE DESIGN FREEZE — C/D FUSION AUTHORITY AND OPERATING POINT  
**Branch:** `stage5-cd-design-audit`  
**Accepted parent:** `main` at `4c13d71a111ce7b72b3ef26a01b2918592425aa1`  
**Date:** 8 October 2026  
**Depends on:** accepted R0.v2, `C_D_NEURAL_ADAPTATION_PROTOCOL.md`  
**Adaptive held-out execution:** PROHIBITED

## 1. Purpose

This protocol freezes how C and D convert their shared neural score plus symbolic state into a fused
score and a thresholded intrusion decision.

The main causal threat is threshold adaptation becoming a second treatment. If C and D independently
recalibrate thresholds from their own fused score trajectories, D symbolic evolution would alter not
only the symbolic state but also its future operating point.

The primary design therefore keeps fusion authority and fused thresholds fixed throughout the
adaptive stream.

## 2. Primary fusion rule

The accepted System-B/R0.v2 fusion function remains unchanged:

`fused = lambda * neural_probability + (1-lambda) * symbolic_probability`

on resolved symbolic coverage.

When the symbolic layer is:

- uncovered; or
- in unresolved cross-class conflict/abstention,

the fused score is exactly the neural probability.

Primary neural weight:

`lambda = 0.50`.

The symbolic weight is therefore 0.50 on resolved covered cases.

No post-drift or per-event lambda optimization occurs.

## 3. Primary fixed fused thresholds

The primary seed-specific operating thresholds are exactly the accepted R0.v2 development-selected
thresholds from `data/manifests/system_b_v2.json`:

- seed 0: `0.692427396774292`
- seed 1: `0.9354645609855652`
- seed 2: `0.8299936652183533`
- seed 3: `0.9747405052185059`
- seed 4: `0.9527904391288757`

Each threshold remains fixed for that seed for the entire C/D adaptive trajectory, across all shared
neural checkpoints and all D symbolic versions.

C and D use the **same threshold value** for a matched seed.

## 4. Why thresholds are not adapted in the primary contrast

A treatment-dependent fused-threshold trajectory would compromise the claim that the primary
C-vs-D treatment difference is symbolic evolution.

A shared online threshold learned from D fused scores would contaminate C with D treatment
information.

A separate threshold learned independently in each arm would add a second treatment.

A threshold learned from the known boundary or future evaluation windows would be leakage.

The primary therefore accepts the possibility that a fixed operating point becomes suboptimal after
neural/symbolic adaptation. That is a scientifically visible consequence of adaptation rather than a
reason to optimize the threshold after seeing the result.

Threshold-free ranking metrics are reported alongside thresholded metrics so score-ordering behavior
is not hidden by an old operating point.

## 5. Separation from the detector monitor threshold

The detector's fixed System-A monitor threshold and the operational fused threshold are different
objects.

- detector monitor threshold: creates the shared neural-only delayed hard-error stream;
- operational fused threshold: converts each C/D fused score into the reported intrusion decision.

Changing one must never implicitly change the other.

The detector event stream therefore remains independent of symbolic fusion authority.

## 6. D symbolic evolution and score-scale changes

System D may change rule coverage, rule confidence, consequents, conflict state and therefore the
distribution of fused scores.

The fixed threshold is not re-centered after such changes.

That is intentional: the symbolic lifecycle treatment includes the consequences of publishing a new
symbolic state under the already accepted operating-point contract.

If D changes score scale in a way that harms thresholded performance while preserving or improving
ranking/explanation quality, that trade-off is reported rather than tuned away.

## 7. Prespecified fusion-authority sensitivities

The accepted R0.v2 development grid already contains alternative lambda/threshold pairs selected
before C/D adaptive outcomes.

The following are frozen as secondary sensitivities.

### 7.1 lambda = 0.70

Per-seed fixed thresholds:

- seed 0: `0.698998749256134`
- seed 1: `0.9423287034034729`
- seed 2: `0.8308807015419006`
- seed 3: `0.9747405052185059`
- seed 4: `0.9527904391288757`

### 7.2 lambda = 0.90

Per-seed fixed thresholds:

- seed 0: `0.9025245904922485`
- seed 1: `0.9258511900901795`
- seed 2: `0.8964613080024719`
- seed 3: `0.9747405052185059`
- seed 4: `0.9527904391288757`

### 7.3 lambda = 1.00 neural-only negative control

Per-seed fixed development-grid thresholds:

- seed 0: `0.9448108673095703`
- seed 1: `0.9337316751480103`
- seed 2: `0.9123510122299194`
- seed 3: `0.9789738655090332`
- seed 4: `0.9561389088630676`

At `lambda=1.00`, symbolic scores have zero predictive authority.

Because C and D share the exact same neural checkpoint trajectory, the C and D fused score arrays and
thresholded prediction arrays must be bitwise/numerically identical at lambda=1.00 for a matched
seed/row sequence.

Any C-vs-D predictive difference under this negative-control condition is an implementation defect.

Symbolic explanation traces may still differ if D rules evolve, but those traces cannot alter the
lambda=1 predictive output.

## 8. No post-hoc per-window threshold optimization

The project will not select an MCC/F1-optimal threshold independently for each evaluation window,
post-drift segment or D rule version and present those numbers as primary adaptive performance.

Such an analysis would use the outcomes being evaluated to repair the operating point.

If a post-hoc oracle-threshold envelope is ever displayed for diagnostic purposes, it must be:

- explicitly labeled exploratory/oracle;
- excluded from confirmatory claims;
- unable to change the frozen primary decision stream.

It is not required by the primary protocol.

## 9. Required score reporting

For every primary C/D prediction record preserve:

- neural probability;
- symbolic resolved/uncovered/conflict state;
- symbolic attack score where defined;
- active lambda;
- fused score;
- fixed operational threshold;
- thresholded decision;
- neural checkpoint identity;
- rule-base version identity.

This permits independent reconstruction of thresholded and threshold-free metrics.

## 10. Primary evaluation consequences

Thresholded metrics include:

- precision;
- recall;
- F1;
- FPR;
- MCC;
- confusion counts.

Threshold-free score metrics include:

- ROC-AUC;
- average precision.

The manuscript must not infer absence of adaptation value merely because thresholded and ranking
metrics move in different directions.

This is especially important because the accepted A/B evidence already demonstrated that fixed-point
metrics and ranking metrics can diverge directionally.

## 11. Causal invariant

For each matched seed and logical row in the primary C-vs-D contrast:

- same neural probability source checkpoint;
- same lambda;
- same operational threshold;
- same fusion implementation;
- same preprocessing.

Only symbolic state may differ.

This makes any fused-score difference attributable to symbolic state under the matched neural
trajectory.

## 12. Interaction with future symbolic-confidence updates

The symbolic lifecycle protocol may later define how D rule confidence changes.

Such changes are allowed to alter D's symbolic score because they are part of the symbolic treatment.

They do **not** authorize:

- lambda changes;
- threshold recalibration;
- detector monitor-threshold changes.

## 13. Sensitivity interpretation

The lambda=.70 and .90 conditions test whether the C-vs-D conclusion depends strongly on the amount
of symbolic predictive authority.

The lambda=1.00 condition is primarily a causal/implementation negative control.

Sensitivity outcomes cannot be used to replace lambda=.50 as the primary because they are more
favorable.

## 14. Remaining limitations

A fixed threshold can become poorly calibrated as the neural model or D symbolic confidence evolves.

That limitation is accepted in exchange for stronger causal isolation.

The project does not claim the primary fixed threshold is deployment-optimal under indefinite drift.

A separately designed threshold-adaptive deployment system would be a different treatment and may be
studied later, but not folded silently into the primary C-vs-D experiment.

## 15. Still unresolved after this packet

The remaining material design controls are now concentrated on the symbolic and final-analysis side:

- D symbolic lifecycle/operator state machine;
- symbolic candidate-generation evidence;
- independent online validation evidence;
- support/count/uncertainty gate semantics;
- rule-confidence update semantics;
- D-periodic trigger cadence/opportunity matching;
- final confirmatory endpoint hierarchy, interval/test and multiplicity;
- runtime/thread/cost benchmark scope;
- exact event/lifecycle serialization schemas and fail-closed implementation verifiers.

## 16. Gate

**Fusion/operational-threshold packet: FROZEN.**

All neural-side causal controls required before symbolic lifecycle design are now prospectively
specified.

Adaptive implementation remains prohibited.

The next packet is the D symbolic lifecycle/operator and online validation protocol.
