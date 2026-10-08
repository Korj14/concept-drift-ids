# Statistical Analysis Plan

**Version:** 1.0 — frozen prospective C/D analysis plan  
**Authority:** `MAIN - Concept_Drift_NIDS_Research_Gap_Doctrine.docx` and `Reconciled_Pre-Stage_3_and_Stage_3_Implementation_Plan.docx`.

This plan prevents analysis choices from being selected after seeing the outcomes they are intended to judge. It was created prospectively and is now frozen for the primary C/D experiment before any adaptive C/D held-out execution.

Adaptive C/D held-out evaluation remains prohibited until the separately frozen implementation-ready gate is satisfied. Any later change to an outcome-sensitive analysis choice requires a new version, preserved prior plan, and explicit disclosure of whether adaptive held-out outcomes had already been inspected.

## 1. Research questions and confirmatory contrasts

The statistical analysis follows the governing research questions rather than searching for whichever metric happens to improve.

### RQ1 — static symbolic staleness under drift

Primary evidence source:

- System B and its frozen initial symbolic state `R_0`.

Required longitudinal outcomes include:

- rule support;
- class precision;
- neural fidelity;
- coverage;
- activation rate/pattern;
- stability;
- conflict/abstention behavior;
- rules remaining valid as well as rules degrading.

Interpretation is descriptive/longitudinal unless a prespecified paired contrast is applicable. Drift is not defined by deterioration of a single predictive metric.

### RQ2 — incremental value of symbolic evolution

Primary causal contrast:

`System D - System C`

C and D must be matched by seed, initial neural checkpoint, initial `R_0`, preprocessing, stream/window order, confirmed drift event, adaptation evidence, label availability, neural update algorithm/budget, replay/buffer policy, fusion mechanism, and compute backend wherever feasible.

The treatment difference is symbolic state:

- C: `R_0 -> R_0`
- D: `R_0 -> R_t`

### RQ3 — validity and cost of evolved explanations

Required outcome families:

- fidelity;
- coverage;
- stability;
- complexity;
- churn;
- conflict;
- abstention;
- activation/staleness;
- lifecycle event counts;
- symbolic-maintenance latency/memory/cost.

### Trigger-policy hypothesis

Primary trigger contrast:

`D-drift - D-periodic`

Both conditions must use the same symbolic-evolution operator with a defensibly matched evidence/update opportunity. The analysis will compare recovery, explanation validity, update count, unnecessary updates, churn/stability, cost, and recovery achieved per update.

## 2. Inferential unit and dependence

### Primary inferential unit

For matched causal comparisons, the primary inferential unit is the **matched seed-level treatment effect within a scenario**.

A longitudinal stream window is a repeated observation from the same seed/scenario trajectory. Windows are **not independent experimental replicates** and must not be treated as such merely to increase sample size.

### Longitudinal use of windows

Window-level observations are used to estimate prespecified trajectory quantities such as:

- immediate degradation;
- detection delay;
- recovery time;
- area/mean performance over a defined post-drift interval;
- explanation-quality trajectory;
- rule-activation/staleness trajectory;
- update/churn trajectory.

There is no confirmatory window-level mixed-effects/GEE/clustered model in the primary scenario. Reporting windows remain longitudinal mechanism/descriptive units only. Confirmatory treatment effects are computed once per seed from the prespecified whole-post-regime endpoints. Any later longitudinal inferential model is exploratory unless separately versioned prospectively for a new scenario.

### Multiple scenarios/datasets

Scenario and dataset replications are not automatically pooled as independent observations. Analyses will report scenario-specific matched effects first. Any cross-scenario synthesis must use a prespecified blocked/hierarchical or meta-analytic approach that respects repeated seeds and scenario/dataset structure.

## 3. Endpoint hierarchy

The project reports a broad metric family, but confirmatory inference must use a limited prospectively declared endpoint set to avoid cherry-picking.

### Detection metrics available

Primary-quality candidates:

- MCC;
- F1 / macro-F1 where appropriate;
- recall;
- precision;
- FPR;
- ROC-AUC;
- average precision.

Secondary descriptive metrics:

- accuracy;
- balanced accuracy.

Accuracy alone is never a success criterion.

### Adaptation metrics available

- drift-detection delay;
- false drift alarms;
- immediate degradation;
- recovery time;
- adaptation gain;
- stability across matched windows.

### Explanation/rule metrics available

- fidelity;
- coverage;
- stability;
- complexity;
- support;
- class precision;
- activation/staleness;
- churn;
- conflict;
- abstention;
- lifecycle operation counts.

### Trigger/computational metrics available

- update frequency/count;
- unnecessary/false-triggered updates;
- recovery per update;
- wall-clock update latency;
- memory where feasible;
- neural-update cost;
- symbolic-evolution cost.

### Confirmatory endpoint set

Exactly three endpoints form the primary confirmatory family.

1. **E1 — post-regime MCC, D-drift minus C.** MCC is computed over all 69,270 frozen post-drift rows under the fixed primary fusion/threshold contract.
2. **E2 — post-regime macro correct symbolic coverage (MCSC), D-drift minus C.** For class c, correct symbolic coverage is the proportion of true class-c rows receiving a resolved correct symbolic prediction; uncovered, conflict-abstained, and symbolically wrong rows contribute zero. MCSC is the unweighted mean across benign and attack classes.
3. **E3 — post-regime MCSC, D-drift minus D-periodic.** This is the primary trigger-policy explanation-utility contrast.

The whole post-regime domain is used without removing rows before adaptation/publication. This is an intention-to-treat-style adaptive trajectory estimand: detector delay, waiting, no-ops, censored maintenance, and late publication remain part of the treatment effect.

All component explanation metrics remain mandatory so MCSC cannot hide whether a change came from benign versus attack coverage/correctness or conflict/abstention.

Trigger cost/efficiency quantities are mandatory secondary evidence rather than being hidden inside a confirmatory composite.

## 4. Effect definitions

For any metric where larger is better:

`paired effect = D - C`

For any metric where smaller is better (for example FPR, recovery time, conflict rate, cost):

the report will either preserve the raw `D - C` direction and label it clearly, or define a benefit-oriented sign convention prospectively before analysis. The convention must be uniform within each reported table/figure.

For pre/post quantities:

`drift delta = post - pre`

For secondary recovery trajectories, the pre-reference baseline is the row-count-weighted mean of the final three frozen pre-drift reporting windows for that system/seed. For a higher-is-better metric, recovery is the first post window at or above that baseline whose immediately following post window also remains at or above baseline; lower-is-better metrics reverse the inequality. The recovery clock is the first qualifying window start. Failure to achieve two-window persistence is right-censored at stream end. Symbolic-recovery language additionally requires the lifecycle evidence chain frozen in `D_SYMBOLIC_LIFECYCLE_PROTOCOL.md`.

## 5. Descriptive summaries

For every system/scenario/endpoint where applicable, preserve seed-level observations and report:

- n;
- mean;
- sample SD;
- 95% interval where defined;
- median;
- IQR;
- minimum/maximum when useful;
- sign consistency for paired effects (number of seeds with positive/negative/zero effect);
- TP, TN, FP, FN, prevalence, and sample count for thresholded detection metrics.

Raw seed/window-level evidence remains available behind all aggregates.

## 6. Confidence intervals

The current System-A summaries use t-based intervals across five frozen seeds. Those intervals remain immutable historical evidence.

For future matched C/D effects:

- paired-effect intervals are computed from the five paired seed differences, not from independently combined marginal intervals;
- the primary effect estimate is the arithmetic mean paired difference;
- the primary interval is the conventional 95% Student-t interval over the five paired differences with df=4;
- the interval is interpreted only as stochastic-seed uncertainty conditional on the fixed scenario, not environmental/deployment-population uncertainty;
- all five paired effects, their median, sample SD, min/max, positive/zero/negative sign count, and leave-one-seed-out mean-effect range are mandatory alongside the interval;
- no normality pretest is used to choose a different interval with n=5;
- no bootstrap interval is primary;
- intervals for bounded metrics are not silently clipped in stored data;
- presentation-layer clipping, if used, follows `VISUALIZATION_POLICY.md`.

## 7. Hypothesis tests and practical significance

P-values are secondary to effect magnitude and uncertainty.

The default principle is:

- paired test for matched C/D and trigger-policy contrasts;
- parametric paired procedure only when its assumptions are credible;
- otherwise a prespecified paired non-parametric or randomization procedure.

For each of the three confirmatory endpoints, use an exact one-sided sign test with benefit direction frozen as positive before outcomes:

- H0: P(paired effect > 0) <= 0.5;
- H1: P(paired effect > 0) > 0.5;
- zero paired differences are removed from the sign-test denominator;
- report the effective nonzero-pair count and the raw positive/zero/negative sign pattern;
- compute the exact binomial probability under p=.5.

The sign-test p-value is secondary calibration rather than the project success criterion. It deliberately ignores magnitude; magnitude is carried by the paired estimate/interval.

Because five paired seeds provide limited formal power and share one underlying stream, conclusions will not rely on crossing an arbitrary p-value threshold. Practical magnitude, interval uncertainty, consistency across seeds/scenarios, longitudinal behavior, robustness, and explanation/cost outcomes are part of the evidentiary judgment.

## 8. Multiplicity

Multiplicity must be controlled transparently across confirmatory endpoint families and repeated scenario/dataset claims.

The three primary confirmatory sign-test p-values form one family.

Use Holm-Bonferroni step-down adjustment at familywise alpha=.05 and report both raw and adjusted p-values.

Secondary/descriptive p-values, if any, are labeled exploratory and are not mixed into the confirmatory family.

Later scenarios/datasets are reported as separate replication families first rather than pooled as extra independent observations. Broad claims require directional/mechanistic consistency across those replications, not a pooled pseudo-replicate p-value.

## 9. Missing runs, failures, and exclusions

All prespecified seeds/runs remain in the record.

A run may be excluded/repeated only for a documented technical failure unrelated to observed performance, such as:

- corrupt/missing required artifact;
- failed hash/integrity check;
- process termination before protocol completion;
- verified hardware/runtime fault;
- implementation defect that invalidates the run against the frozen protocol.

The failed original run, error evidence, reason, corrective action, and replacement run identity must remain in the methodology ledger.

Poor performance, inconvenient direction, or wide uncertainty is never an exclusion criterion.

## 10. Sensitivity and robustness analysis

Sensitivity analyses test whether the main conclusion depends on reasonable design alternatives; they are not parameter searches for a more favorable result.

The prespecified robustness package is now frozen:

- label latency L=0 and L=10,000;
- Page-Hinkley on the same delayed hard-error signal;
- ADWIN on delayed Brier loss;
- no-replay neural fine-tuning;
- lambda=.70 and lambda=.90 fusion-authority sensitivities;
- lambda=1.00 neural-only causal negative control;
- non-overlapping 2,500-row and 10,000-row reporting-window sensitivities for descriptive/recovery trajectories;
- static-style symbolic gate sensitivity: support>=.001, covered>=100, point precision>=.80, point fidelity>=.90, bootstrap persistence>=.90, complexity<=4, with no Wilson lower-bound requirement.

Existing System-B duplicate/multiplicity robustness remains contextual evidence rather than a C/D tuning device.

Before broad publication claims, add at least one scenario with a more direct attack-pattern/conditional-label change opportunity and a defensible second flow-oriented dataset where semantics permit the higher-level causal protocol without artificial harmonization.

Adaptive preprocessing, if studied, is a separately labeled matched treatment and not a sensitivity tweak to the primary experiment.

For every sensitivity analysis, record:

- parameter/value range;
- reason the range is scientifically plausible;
- data permitted to select the range;
- whether it is confirmatory, robustness, or exploratory;
- whether all matched systems are rerun.

## 11. Visualization and reporting

All numerical figures/tables are generated programmatically from immutable versioned JSON/CSV evidence.

Preferred displays include:

- paired seed slope/point plots;
- paired-effect forest plots;
- longitudinal trajectories with detected drift events and scoring boundaries distinguished;
- explanation-quality/staleness trajectories;
- rule-version/churn timelines;
- grouped system comparisons with individual seed points;
- recovery-per-update and cost-versus-recovery plots.

No figure transformation may alter the stored statistical result.

## 12. Analysis freeze gate

Before the first adaptive C/D held-out outcome is inspected, this version-1.0 plan must remain unchanged unless a new disclosed protocol version is created before access.

At that gate:

1. assign a version number;
2. record its Git commit/hash in `METHODOLOGY_LEDGER.md`;
3. record the frozen longitudinal-window policy;
4. record the frozen drift/adaptation policy;
5. record the confirmatory endpoints/effect definitions;
6. record the primary interval/test and multiplicity procedure;
7. record failed-run/exclusion rules and sensitivity analyses;
8. run the repository tests/verification checks;
9. only then unlock untouched adaptive evaluation.

Any subsequent change requires a new analysis-plan version, explicit rationale, and disclosure of whether outcomes had already been inspected.


## 13. Scope of seed-level uncertainty

The five stochastic seeds within one scenario share the same underlying stream observations. Seed-level intervals therefore quantify variability attributable to stochastic training / seed-specific symbolic extraction conditional on that scenario.

They are **not** estimates of independent environmental or deployment-population variation.

Accordingly:

- within-scenario C-vs-D inference remains paired by seed;
- scenario/dataset conclusions are reported separately first;
- broad generalization requires additional scenario/dataset replication;
- the manuscript must not inflate effective sample size by combining seeds, windows, or rules as if they were independent environments.

## 14. Rule-level descriptive uncertainty

Rule support, class precision and neural fidelity are descriptive nested outcomes, not 36 independent confirmatory experiments.

Where publication tables emphasize a rule-level proportion, report its denominator and an appropriate descriptive uncertainty interval where useful. Selection-slice intervals do not remove selection bias and must not be presented as independent validation.

Gate-persistence bootstrap remains a robustness metric, not a p-value.

## 15. Information-time constraint on adaptive analysis

Any C/D endpoint depending on an update time must use the time at which all protocol-required evidence was actually available.

If symbolic validation requires delayed ground-truth labels, recovery time and update latency begin/end definitions must respect that latency. A rule-base version cannot be credited with recovery before it could legitimately have been published.

This timing rule must be frozen together with the adaptive protocol before untouched C/D outcomes.


### 15.1 Frozen primary information-time contract — 8 October 2026

`C_D_STREAM_TIME_CONTRACT.md` prospectively freezes the following timing rules before detector/updater selection:

- the adaptive stream is the uninterrupted ordered `pre_drift -> post_drift` sequence with no state reset at the known synthetic boundary;
- logical time is row index because the frozen scenario does not support true timestamp chronology;
- primary verification latency is fixed at `L=5,000` rows;
- a label for origin row `j` becomes adaptively visible only after the prediction at `j+L` has been committed;
- prediction precedes label release even in the `L=0` oracle-latency sensitivity;
- supervised prequential detector evidence must use the prediction stored when the origin row was first processed, not a later rescore under an adapted model;
- updates may use only arrived rows and labels mature by the update clock;
- a new state can affect prediction no earlier than the next logical row;
- pending labels are not flushed at the synthetic boundary or at end of stream;
- the offline evaluator may use all true labels only after prediction records are frozen and may not feed them back into adaptation.

Prespecified latency robustness conditions are `L=0` and `L=10,000`. They do not create additional independent replicates.

For timing-dependent outcomes:

- drift-detection delay is measured to the confirmed event's causal availability clock, not retrospectively to the origin time of delayed evidence;
- adaptation/recovery cannot be credited before the updated state is published;
- predictions are assigned to longitudinal reporting windows by their origin-row index;
- right-censored terminal labels remain unavailable to adaptive components even though the offline scorer can evaluate their frozen predictions.

The 5,000-row latency is a controlled simulation assumption, not an estimate of real SOC label turnaround. The primary scenario remains unsuitable for real-time throughput/backlog claims because trustworthy event timestamps are absent.


### 15.2 Frozen primary drift-monitor analysis contract — 8 October 2026

`C_D_DRIFT_MONITOR_PROTOCOL.md` freezes the primary upstream event generator as River 0.26.1
ADWIN operating on the delayed neural-only hard-error stream at the fixed accepted System-A
development threshold for each seed.

The event is interpreted as a statistically significant change in the mean of the eligible neural
error stream. It is not treated as proof of a change specifically in `P(Y|X)`.

Primary trigger-quality reporting relative to the designated controlled boundary will include:

- pre-reference-boundary alarm count and clocks;
- whether a post-boundary event occurs;
- first post-boundary confirmation clock;
- end-to-end delay = confirmation clock minus boundary index;
- latency-adjusted descriptive excess delay = confirmation clock minus (boundary index + L);
- repeated post-boundary events;
- total event count and inter-event spacing;
- eligible detector-input count by checkpoint-pure epoch;
- disarmed/blind duration and suppressed stale-checkpoint-error count.

The synthetic boundary is used for these diagnostics only after the detector event log is frozen.
It is never supplied to the running detector.

The latency-adjusted excess delay is descriptive. It does not subtract verification latency from the
causal publication clock and cannot be used to credit earlier adaptation.

Pre-boundary alarms are described as alarms relative to the designated reference boundary rather
than automatically asserted to be objectively false environmental detections, because the
pseudo-chronological pre partition may contain natural internal variation.

Detector events within a seed are dependent longitudinal observations, not independent inferential
replicates.

Prespecified robustness conditions are:

1. identical hard-error signal and timing under River 0.26.1 Page-Hinkley defaults;
2. primary ADWIN configuration on delayed Brier loss instead of hard error;
3. the already-frozen label-latency conditions L=0 and L=10,000 applied to the primary detector.

None may replace the primary ADWIN hard-error condition because its held-out result is more favorable.


### 15.3 Frozen shared neural-adaptation analysis contract — 8 October 2026

`C_D_NEURAL_ADAPTATION_PROTOCOL.md` freezes the primary adaptive-neural comparator before C/D
adaptive held-out execution.

The primary neural response to a confirmed event is fixed-budget replay fine-tuning:

- current evidence = the most recent 10,000 mature labeled observations whose original prediction
  was produced by the parent checkpoint;
- if fewer than 10,000 are available at confirmation, the response remains pending until the fixed
  budget matures; the window is not opportunistically shrunk;
- terminal shortfall is reported as a right-censored response rather than forcing a final update;
- replay evidence = 10,000 rows per transaction from a dual memory: 5,000 immutable
  training-anchor rows plus 5,000 eligible mature-history-reservoir rows, with current-window IDs
  excluded;
- update dataset = 20,000 rows total;
- fixed original System-A positive class weight = 4.138247558496975;
- Adam learning rate 1e-4, weight decay 1e-5, batch size 1024, exactly 5 epochs;
- no adaptive early stopping, no learning-rate scheduler and no performance-based publication gate;
- one child checkpoint is generated once in the shared control plane and referenced by both C and D.

A technically valid but performance-degrading neural update remains part of the result. It is not
discarded or rerun because its direction is inconvenient.

Replay-memory admission is treatment-independent and not conditioned on attack class, neural error,
symbolic state, detector proximity or known-boundary proximity.

Catastrophic-forgetting analysis is prospectively separated from adaptation decisions:

1. the full frozen development partition is rescored after each published checkpoint as a historical
   retention probe; those scores cannot affect update stopping/publication;
2. the frozen pre-drift stream partition may be retrospectively rescored per checkpoint only after
   the adaptive trajectory is fixed, for offline forgetting analysis; those scores never feed any
   adaptive component.

For any larger-is-better retention metric M, report:

- retention delta: M_k - M_0;
- descriptive forgetting: max_{h<=k}(M_h) - M_k.

Checkpoint/event observations are longitudinally dependent within seed and are not independent
replicates.

A no-replay fine-tuning ablation is prespecified using the identical current-evidence window and
optimizer/update budget. It is secondary evidence about replay/forgetting and cannot replace the
primary replay trajectory because its held-out result is favorable.

Neural transaction cost reporting will include evidence-waiting rows, update-row counts,
minibatch count, CPU training time, memory where feasible, checkpoint size/serialization and
detector-disarmed logical duration. Compute time is not converted into production backlog because
the scenario lacks trustworthy arrival timestamps.


### 15.4 Frozen C/D fusion and operating-point contract — 8 October 2026

`C_D_FUSION_THRESHOLD_PROTOCOL.md` freezes the primary decision contract before symbolic
lifecycle implementation.

Primary C/D fusion remains the accepted R0.v2 rule:

- neural weight lambda = 0.50 on resolved symbolic coverage;
- uncovered/conflict cases fall back to the neural probability;
- seed-specific accepted R0.v2 fused thresholds remain fixed for the full adaptive trajectory.

The primary thresholds are:

- seed 0: 0.692427396774292
- seed 1: 0.9354645609855652
- seed 2: 0.8299936652183533
- seed 3: 0.9747405052185059
- seed 4: 0.9527904391288757

There is no per-event, per-window or per-arm threshold recalibration in the primary causal contrast.

This means thresholded metrics intentionally reflect the consequences of neural/symbolic score drift
under a fixed operating-point contract. Threshold-free ROC-AUC and average precision are reported
alongside them so ranking behavior remains visible.

Secondary fusion-authority sensitivities use the already accepted R0.v2 development-grid
lambda/threshold pairs at lambda=.70 and lambda=.90. They cannot replace lambda=.50 based on
adaptive held-out direction.

A lambda=1.00 neural-only negative control is also frozen. Under this condition symbolic predictive
authority is zero. Because C and D share the exact same neural checkpoint trajectory, matched C/D
fused score arrays and thresholded predictions must be identical. Any predictive C-vs-D difference at
lambda=1.00 is classified as an implementation defect.

Symbolic explanation traces may still differ under lambda=1.00 and may be used descriptively, but
they cannot alter the predictive decision.

No post-hoc per-window oracle threshold is permitted in confirmatory evidence. Any future oracle
threshold envelope must be labeled exploratory and cannot alter the frozen primary decision stream.


### 15.5 Frozen D symbolic-lifecycle analysis contract — 8 October 2026

`D_SYMBOLIC_LIFECYCLE_PROTOCOL.md` freezes the rule-evolution treatment before adaptive held-out
execution.

Candidate generation and acceptance are statistically separated:

- candidate structures are mined from the 10,000-row neural current-evidence window associated with
  the shared child checkpoint;
- predictive authority cannot change until a **different**, chronological 10,000-row
  child-checkpoint-pure validation block has arrived and its labels have matured;
- if the child checkpoint is superseded before that validation block completes, the symbolic
  transaction is censored as `superseded_before_validation` and no partial rule publication is
  allowed.

The online acceptance gate is prospectively sample-size-aware rather than reusing the static
`covered>=100` count mechanically. It requires:

- support >= .001;
- covered >= 25;
- class precision point estimate >= .80 and one-sided 95% Wilson lower bound >= .80;
- neural fidelity point estimate >= .90 and one-sided 95% Wilson lower bound >= .90;
- 100-replicate stratified full-gate persistence >= .90;
- complexity <= 4.

The one-sided Wilson z value is 1.6448536269514722. The covered-count minimum of 25 is tied to the
fidelity requirement: below 25 covered observations even perfect observed fidelity cannot establish a
one-sided 95% lower bound of .90.

Existing active rules are evaluated on the same independent validation block before candidate
integration. Their pre-resolution staleness state is preserved. Lifecycle transitions are
longitudinal dependent observations, not independent inferential replicates.

For lifecycle reporting preserve at minimum, per maintenance opportunity and seed:

- active rule count before/after;
- valid / quality-failed / evidence-insufficient incumbent counts;
- candidate count;
- rejected candidate count by reason;
- retained, new-addition, refined, merged, demoted, retired and reactivated counts;
- unresolved cross-class conflicts;
- symbolic abstention rate after publication;
- confidence-change magnitudes;
- rule-base version identity and parent identity;
- validation waiting rows and symbolic compute cost.

Rule confidence is refreshed only from completed independent symbolic-validation evidence and is
constant between symbolic publications. System C's R0.v2 confidence is frozen.

A claim of symbolic "recovery" requires a documented longitudinal chain:
valid -> stale/demoted -> accepted refinement/reactivation/replacement -> post-publication
improvement. A new rule addition without a stale predecessor is not labeled recovery.

Right-censored or superseded symbolic transactions remain part of the adaptation evidence and cannot
be silently removed from update-rate/cost reporting.


### 15.6 Frozen trigger-ablation analysis contract — 8 October 2026

`D_TRIGGER_ABLATION_PROTOCOL.md` freezes the primary trigger comparison before adaptive execution.

Both D-drift and D-periodic:

- start from the same accepted R0.v2;
- consume the same shared neural checkpoint chain;
- use the identical symbolic evolution operator/configuration;
- use the same generation/validation budgets and RNG namespace;
- have the same maximum symbolic opportunity budget: four slots per seed.

D-drift consumes symbolic slots on the first four confirmed primary detector events.

D-periodic uses exact fixed logical clocks:

- 27,706
- 55,412
- 83,118
- 110,824

These clocks equal `floor(i*N/5)` for `i=1..4`, with `N=138,530`.
They are derived from the frozen stream length and symbolic evidence footprint, not the synthetic
boundary or detector outcomes.

Every trigger/scheduled slot consumes one opportunity budget slot whether it ends in publication,
validated no-op, insufficient generation evidence, checkpoint supersession, right-censoring or
pending-transaction skip.

The trigger-analysis unit therefore distinguishes:

- opportunity;
- completed validation;
- publication;
- no-op;
- censored/aborted transaction.

These are not interchangeable counts.

Primary trigger-ablation summaries must report both effectiveness and efficiency, including:

- publication and no-op frequency;
- cost per opportunity and per publication;
- accepted lifecycle actions;
- active-rule/conflict/abstention trajectories;
- predictive and explanation recovery;
- maintenance attempts avoided;
- improvement/recovery per maintenance opportunity.

Trigger opportunities/events within one seed are longitudinally dependent observations. They do not
increase inferential sample size beyond the matched seed/scenario block.

The evaluator-known controlled boundary may be used only after trajectories are frozen to describe
opportunity timing/delay/unnecessary maintenance. It cannot alter either trigger schedule.


## 16. Corrected System-B v2 evidence status

The R0.v2 evaluation is a protocol-defect correction conducted after historical R0.v1 held-out outcomes were known. It is therefore not treated as a new untouched confirmatory experiment.

For publication:

- R0.v2 is the protocol-conformant static System-B baseline and the required symbolic start state for future C/D;
- R0.v1 versus R0.v2 differences are implementation-correction sensitivity/provenance, not a hypothesis test or model-selection comparison;
- no p-value is attached to the v1-v2 correction contrast;
- the corrected v2 pre/post paired seed summaries are descriptive baseline evidence for RQ1 and for later matched visualization;
- class-conditional symbolic coverage/correctness/fidelity are descriptive explanation diagnostics motivated and frozen before v2 execution;
- imputation-aware rule diagnostics are descriptive robustness evidence and do not redefine the primary rule-validity gates;
- the primary later causal inference remains matched C-vs-D under a common accepted R0.v2 start.

Knowledge of v1 held-out outcomes must not be used to change R0.v2, lambda, thresholds, preprocessing, windows or C/D treatment definitions.


## 17. Bounded metric confidence-interval convention

The frozen A/B aggregate files use ordinary seed-level Student-t intervals. With five seeds, an unconstrained interval for a metric whose realizations lie in [0,1] can numerically extend outside [0,1].

The primary stored arithmetic remains unchanged. Do not truncate or winsorize interval endpoints in JSON/CSV or manuscript numeric tables.

For visualization, a physical [0,1] metric axis is permitted. Any off-domain primary interval endpoint must be disclosed rather than silently replaced. A bounded bootstrap/transformed interval may be reported only as a clearly labeled secondary robustness/presentation interval unless a later untouched protocol prospectively makes it primary.

The more important inferential limitation is unchanged: the five seeds share one scenario stream and therefore quantify stochastic optimization/symbolic-extraction variability conditional on that scenario, not population/environmental uncertainty.


## 16. Final frozen execution and reproducibility contract — 8 October 2026

`C_D_FINAL_ANALYSIS_REPRODUCIBILITY_PROTOCOL.md` is authoritative for the final pre-implementation gate.

Key execution controls:

- primary adaptive execution is CPU-only;
- before numerical-library initialization set `PYTHONHASHSEED=0`, `OMP_NUM_THREADS=1`, `MKL_NUM_THREADS=1`, `OPENBLAS_NUM_THREADS=1`, and `NUMEXPR_NUM_THREADS=1`;
- set PyTorch intra-op and inter-op threads to 1, request deterministic algorithms, and use DataLoader workers=0;
- record `threadpoolctl.threadpool_info()` and fail a primary run when a detected BLAS/OpenMP numerical pool violates the one-thread contract;
- use `time.perf_counter_ns()` for component wall-clock costs;
- preserve write-once run manifests, shared control-plane events, checkpoint lineage, arm predictions, symbolic maintenance events, rule revisions/versions, and evaluation tables;
- run fail-closed verifiers for shared C/D control-plane identity, information timing, checkpoint purity, fusion/threshold identity, lambda=1 equality, generation/validation separation, trigger-arm operator identity, lifecycle integrity, boundary non-contamination, and write-once/hash integrity.

Implementation proceeds on dedicated branches without primary pre/post adaptive execution:

1. `stage6-cd-control-plane`;
2. `stage7-cd-symbolic-lifecycle`;
3. after acceptance/tagging as `cd-implementation-ready-v1`, `stage8-cd-primary-evaluation`.

At primary evaluation, first generate and freeze one shared control-plane trajectory per seed. C, D-drift and D-periodic then consume those immutable detector/neural artifacts. Symbolic arms cannot alter drift events, replay, neural updates or checkpoint timing.

The complete held-out access checklist and post-access change doctrine are frozen in the final reproducibility protocol.
