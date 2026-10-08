# Statistical Analysis Plan

**Version:** 0.1 — prospective framework  
**Authority:** `MAIN - Concept_Drift_NIDS_Research_Gap_Doctrine.docx` and `Reconciled_Pre-Stage_3_and_Stage_3_Implementation_Plan.docx`.

This plan prevents analysis choices from being selected after seeing the outcomes they are intended to judge. It is deliberately created before Systems B/C/D are evaluated. Items explicitly marked **TBD BEFORE C/D** are unresolved design decisions, not permission to decide them after untouched results are known.

Untouched C/D confirmatory evaluation is prohibited until all confirmatory items in this document have been frozen and the version/hash has been recorded in the methodology ledger.

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

If window-level inferential modelling is used, its dependence structure must be explicitly represented through a prespecified blocked, clustered, mixed-effects, GEE, or equivalent longitudinal method. The exact method is **TBD BEFORE C/D** and must be frozen before untouched adaptive outcomes.

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

**TBD BEFORE C/D.**

Before untouched C/D evaluation, select a small confirmatory set that directly represents:

1. predictive/adaptation performance;
2. longitudinal explanation validity;
3. trigger/update efficiency.

All remaining metrics will be secondary or descriptive. The selection must be justified from the research questions and development/design evidence, not from C/D test outcomes.

## 4. Effect definitions

For any metric where larger is better:

`paired effect = D - C`

For any metric where smaller is better (for example FPR, recovery time, conflict rate, cost):

the report will either preserve the raw `D - C` direction and label it clearly, or define a benefit-oriented sign convention prospectively before analysis. The convention must be uniform within each reported table/figure.

For pre/post quantities:

`drift delta = post - pre`

For recovery trajectories, exact baseline and recovery definitions are **TBD BEFORE longitudinal adaptive evaluation** and must be tied to the frozen windowing policy.

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

- paired-effect intervals must be computed from paired differences, not from independently combined marginal intervals;
- the exact primary interval method is **TBD BEFORE C/D**, chosen before outcomes are inspected;
- small-n limitations must be stated explicitly;
- intervals for bounded metrics are not silently clipped in stored data;
- presentation-layer clipping, if used, follows `VISUALIZATION_POLICY.md`.

If bootstrap or permutation intervals/tests are selected, the resampling unit must respect the declared experimental unit and dependence structure.

## 7. Hypothesis tests and practical significance

P-values are secondary to effect magnitude and uncertainty.

The default principle is:

- paired test for matched C/D and trigger-policy contrasts;
- parametric paired procedure only when its assumptions are credible;
- otherwise a prespecified paired non-parametric or randomization procedure.

The exact confirmatory test(s), including treatment of ties and small sample sizes, are **TBD BEFORE C/D**.

Because five paired seeds provide limited formal power, conclusions will not rely on crossing an arbitrary p-value threshold. Practical magnitude, interval uncertainty, consistency across seeds/scenarios, longitudinal behavior, robustness, and explanation/cost outcomes are part of the evidentiary judgment.

## 8. Multiplicity

Multiplicity must be controlled transparently across confirmatory endpoint families and repeated scenario/dataset claims.

**TBD BEFORE C/D:**

- final confirmatory endpoint count;
- correction procedure and family definition;
- whether scenario-level replication is treated as confirmatory replication or exploratory robustness.

Secondary/descriptive metrics will be labeled accordingly rather than presented as independent confirmatory discoveries.

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

At minimum, prespecify before untouched C/D:

- reasonable window-size/stride sensitivity;
- drift-detector/persistence sensitivity;
- rule-validation threshold sensitivity;
- duplicate/conflict sensitivity where relevant;
- alternative drift scenario(s);
- second-dataset replication where scientifically defensible.

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

Before the first untouched C/D outcome is inspected, this document must have no unresolved **TBD BEFORE C/D** item affecting confirmatory analysis.

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
