# Stage 9 v1.1 Prespecified Robustness Results Interpretation

**Status:** POST-EXECUTION INTERPRETATION — IMMUTABLE ROBUSTNESS EVIDENCE  
**Stage-9 evidence commit:** `9a05602b68cfaee7c45d2002a760b65115a581fd`  
**Stage-9 compact manifest:** `d2d6f1a75aa427f2ba1769b8fef2d51253a5f10b5d3bfdb6c31de10d811aae22`  
**Stage-9 aggregate canonical SHA:** `6432dd5791f0baa9bdb2597c072b866814fb614f5a1f670dffec7f760bd1491a`  
**Stage-9 aggregate raw SHA:** `d6e70aaa591de7169ed9acc7f1da7c0aa6edfc7e7d3e8b5e72657d7d1e57be70`  
**Stage-9 config manifest:** `b72fc0dce0df46974737cd0c33714cc17b23f31ce188e92d318b1787c0ae027e`  
**Stage-9 execution plan SHA:** `4ae426dd32ffed2384b4565710364459f4ee0ac2752543d6ec075facf66e53c8`  
**Parent Stage-8 evidence commit:** `c2ded83b8195b9321e715626c1f305f9627936e8`  
**Parent Stage-8 confirmatory aggregate:** `1be77ce4be9f3faad021a3f3bfd636488e5de6aa1b2a6e7c596e48feb41bb54d`

## 1. Interpretation boundary

This document interprets the already-frozen Stage-9 v1.1 robustness evidence. It changes no treatment,
seed, threshold, detector configuration, label latency, replay policy, symbolic gate, endpoint,
reporting window, statistical family, or execution result.

Stage 9 is a **prespecified robustness package**, not a second confirmatory family. No new p-values are
computed. The five matched seeds remain the stochastic inferential units conditional on the one fixed
controlled scenario. Detector events, maintenance opportunities, rules, publications, windows, and
rows are nested longitudinal observations and are not promoted to independent replicates.

The scenario remains the controlled BENIGN-source-regime-dominant
`cicids2017_sudden_benign_v1` stream. Stage 9 therefore strengthens or weakens the robustness of
the Stage-8 fixed-scenario interpretation; it does not establish deployment-population, natural-drift,
or cross-dataset generalization.

## 2. Execution and evidence integrity

The corrected v1.1 matrix completed all 110 frozen steps with no outcome-dependent early stopping.
The subsequent verify-only pass confirmed all 110 steps from existing artifacts.

The immutable compact evidence commit adds exactly **358 files**, all under
`results/frozen/cd_robustness_v1_1/`, with no changed or deleted files elsewhere.

The frozen export contains all eleven prespecified robustness conditions:

- fusion authority: lambda=.70, .90, and 1.00;
- reporting windows: 2,500 and 10,000 rows;
- label latency: L=0 and L=10,000;
- Page-Hinkley on delayed hard error;
- ADWIN on delayed Brier loss;
- no-replay neural adaptation;
- static-style symbolic validation gate.

The aggregate records:

- all frozen conditions reported;
- no condition selection by outcome;
- no new Stage-9 p-values;
- seed as inferential unit within the fixed scenario;
- environmental-replication claims forbidden.

The evidence commit passed exact-head Research Contract and Stage-9 robustness contract workflows for
both push and pull-request events.

## 3. Stage-8 primary anchor

The immutable Stage-8 primary D-drift minus C post-reference MCC effect was:

- mean **+0.059752**;
- seed effects **+0.048421, +0.063315, +0.070044, +0.060085, +0.056893**;
- sign pattern **5 positive / 0 zero / 0 negative**;
- paired 95% Student-t interval **[+0.049832, +0.069671]**;
- exact one-sided sign p **0.03125**;
- Holm-adjusted p **0.09375**.

The primary MCSC contrast was unfavorable:

- mean D-drift minus C **-0.063103**;
- sign pattern **1 positive / 0 zero / 4 negative**.

The primary evidence therefore supported a strong fixed-scenario predictive effect without
familywise .05 rejection and with a predictive-versus-explanation trade-off.

Stage 9 asks whether that picture is fragile to the already-frozen design perturbations.

## 4. Main robustness result: D-drift versus frozen-symbolic C

The table reports paired whole-post MCC effects. The interval is descriptive stochastic-seed
dispersion conditional on the fixed scenario, not environmental inference.

| Condition | Mean MCC effect | Sign +/0/- | 95% descriptive interval | Mean MCSC effect | Mean resolved-coverage effect |
|---|---:|---:|---:|---:|---:|
| Stage-8 primary lambda=.50 | +0.059752 | 5/0/0 | [+0.049832, +0.069671] | -0.063103 | -0.144175 |
| lambda=.70 | +0.049873 | 4/0/1 | [+0.014058, +0.085689] | -0.063103 | -0.144175 |
| lambda=.90 | +0.049323 | 5/0/0 | [+0.025551, +0.073095] | -0.063103 | -0.144175 |
| lambda=1.00 | +0.000000 | 0/5/0 | [+0.000000, +0.000000] | -0.063103 | -0.144175 |
| latency L=0 | +0.035265 | 2/3/0 | [-0.026748, +0.097278] | -0.005651 | -0.038467 |
| latency L=10,000 | +0.045821 | 4/1/0 | [-0.016340, +0.107983] | -0.009317 | -0.047848 |
| Page-Hinkley hard error | +0.057254 | 5/0/0 | [+0.039977, +0.074531] | -0.065035 | -0.152072 |
| ADWIN Brier | +0.052663 | 5/0/0 | [+0.024563, +0.080763] | -0.105238 | -0.229158 |
| no replay | +0.042119 | 4/0/1 | [+0.011090, +0.073147] | -0.049818 | -0.120323 |
| static symbolic gate | +0.060361 | 5/0/0 | [+0.049963, +0.070759] | -0.056484 | -0.143138 |

### Interpretation

The Stage-8 predictive result is **not a single-setting artifact**.

The D-drift versus C MCC contrast remains positive in mean under every prespecified non-neural-only
robustness condition. It is 5/5 positive under lambda=.90, Page-Hinkley, ADWIN-Brier, and the static
gate; 4/5 positive under lambda=.70 and no replay; and nonnegative with exact zeros under the latency
conditions where some seeds publish no D-drift symbolic revision.

The effect is therefore robust to:

- increased neural fusion authority short of removing symbolic predictive authority entirely;
- detector-family change;
- detector-signal change;
- replay removal;
- a looser static-style symbolic gate;
- substantial changes in label latency.

This is strong fixed-scenario robustness evidence for a symbolic-lifecycle contribution to predictive
behavior beyond an otherwise matched adaptive neural control.

It is **not** evidence of universal benefit across environments.

## 5. Lambda=1 negative control materially strengthens causal attribution

At lambda=1.00, symbolic predictive authority is removed and every matched arm collapses exactly to
the shared neural prediction stream.

The D-drift minus C MCC effect becomes:

- **0.000000 mean**;
- **five exact zeros**;
- interval **[0, 0]**.

The same exact predictive equality holds between D-drift and D-periodic.

This is a particularly important robustness result because it demonstrates that the nonzero
lambda<1 arm differences are not produced by hidden arm-specific neural training trajectories. The
predictive contrast disappears exactly when symbolic predictive authority is removed.

The MCSC contrast does not become zero at lambda=1 because MCSC is a symbolic explanation/coverage
endpoint, not a neural-only prediction endpoint. Lambda=1 is therefore a causal negative control for
the **predictive path**, not a deletion of the symbolic explanation state.

The defensible causal statement is:

> Within the fixed Stage-8 scenario and matched neural trajectory, the observed predictive
> D-drift-versus-C difference is mediated through symbolic state/fusion authority rather than
> different neural adaptation histories.

## 6. Explanation-quality trade-off is robust, not rescued

Stage 9 does not rescue the unfavorable Stage-8 explanation endpoint.

D-drift minus C mean MCSC remains negative under every listed robustness condition. The magnitude is
smaller under the two latency variants because fewer symbolic publications occur in several seeds,
but the general evidence still does not support a claim that symbolic evolution preserves or improves
the prespecified explanation-quality endpoint.

Resolved symbolic coverage also decreases on average in every non-neural-only condition.

The strongest publication-safe conclusion remains:

> The symbolic lifecycle can improve predictive behavior while reducing the amount of class-balanced
> correct symbolic authority/coverage.

This is a trade-off, not a simultaneous prediction-and-explanation win.

## 7. Drift-gated trigger versus periodic trigger

Stage 9 gives no stable evidence that the drift trigger is categorically superior to matched periodic
symbolic maintenance.

D-drift minus D-periodic mean MCC effects are:

| Condition | Mean MCC effect | Sign +/0/- | 95% descriptive interval |
|---|---:|---:|---:|
| lambda=.70 | +0.002434 | 3/0/2 | [-0.054618, +0.059485] |
| lambda=.90 | -0.005932 | 2/0/3 | [-0.078254, +0.066391] |
| lambda=1.00 | +0.000000 | 0/5/0 | [0, 0] |
| latency L=0 | -0.035064 | 1/0/4 | [-0.074198, +0.004069] |
| latency L=10,000 | +0.024061 | 4/1/0 | [+0.005800, +0.042322] |
| Page-Hinkley hard error | +0.003743 | 2/0/3 | [-0.067529, +0.075015] |
| ADWIN Brier | -0.010525 | 4/0/1 | [-0.080179, +0.059129] |
| no replay | +0.001217 | 2/0/3 | [-0.046209, +0.048642] |
| static symbolic gate | -0.005064 | 3/0/2 | [-0.082267, +0.072140] |

The directions are mixed. Latency=10,000 is the one prespecified robustness condition with a wholly
positive descriptive seed interval for D-drift minus periodic MCC, while latency=0 moves in the
opposite direction.

That pattern is scientifically interesting but cannot be used post hoc to select a favorable trigger
regime. Across the full frozen package, there is no stable trigger-specific superiority.

Therefore Stage 9 strengthens the claim that a **validated symbolic maintenance lifecycle** has value,
while continuing to weaken any claim that the **drift trigger itself** is uniquely responsible for
that value.

## 8. Trigger behavior remains imperfectly aligned to the designated boundary

The designated boundary is row 69,260 and remains scoring-only.

Across scored robustness conditions, mean pre-reference detector alarms range from **2.4 to 4.4 per
seed**. Every detector/latency variant has pre-reference activity.

Mean first post-reference confirmation delay is also substantially larger than label latency alone:

| Condition | Mean pre-reference alarms | Mean first post-reference delay | Mean latency-adjusted excess delay |
|---|---:|---:|---:|
| ADWIN Brier | 2.4 | 10,955.0 | 5,955.0 |
| latency L=0 | 4.4 | 14,009.4 | 14,009.4 |
| latency L=10,000 | 2.8 | 19,190.2 | 9,190.2 |
| no replay | 2.8 | 10,004.6 | 5,004.6 |
| Page-Hinkley hard error | 2.8 | 18,938.4 | 13,938.4 |
| static gate / primary Phase-A source | 2.8 | 18,052.6 | 13,052.6 |

No scored condition supports the simplified narrative “controlled boundary occurs, detector promptly
identifies it, then symbolic repair begins.”

The estimand remains the downstream effect of an endogenous detector-gated lifecycle operating over
the whole stream.

## 9. Publication-clock audit

A separate post-outcome publication-clock audit was computed from the frozen Stage-9 provenance. It
does not alter any outcome and is descriptive only.

D-drift publication totals by robustness condition were:

| Condition | Total publications | Pre-reference | Post-reference | Seeds with any publication |
|---|---:|---:|---:|---:|
| ADWIN Brier | 13 | 9 | 4 | 5 |
| latency L=0 | 4 | 4 | 0 | 2 |
| latency L=10,000 | 9 | 3 | 6 | 4 |
| no replay | 7 | 6 | 1 | 5 |
| Page-Hinkley hard error | 10 | 6 | 4 | 5 |
| static symbolic gate | 7 | 6 | 1 | 5 |

The timing pattern reinforces the Stage-8 interpretation. Most conditions still have many successful
D-drift symbolic publications before the scoring boundary.

Latency=0 is especially informative: D-drift publishes only in seeds 0 and 2, all four publications
are pre-reference, and those are exactly the two seeds with positive D-drift-minus-C MCC effects;
the other three seeds have no D-drift publications and exact zero MCC effects. This is descriptive
mechanistic consistency, not a new inferential test.

The publication audit must not be used to claim that pre-reference publication is inherently optimal.
It demonstrates only that the predictive effect is not a clean post-boundary repair phenomenon.

## 10. Symbolic maintenance workload

All scored D arms retain the same maximum four symbolic opportunities per seed.

Realized publication rates vary materially with detector, latency, and gate conditions. D-drift mean
publications per seed range from **0.8** under latency=0 to **2.6** under ADWIN-Brier. Periodic
maintenance also produces substantial publication activity and often comparable predictive value.

The robustness package therefore demonstrates that the lifecycle is genuinely active under multiple
trigger/control variants rather than relying on one exact event schedule. At the same time, the
periodic comparator shows that lifecycle value should not be attributed solely to drift detection.

Symbolic `compute_seconds` recorded in the maintenance summaries is a component-level cost measure
and must not be confused with end-to-end wall-clock runtime of the full Stage-9 execution.

## 11. Recovery-window sensitivity is not robust enough for a headline claim

The 2,500-row and 10,000-row window conditions do not change whole-post endpoints by construction.
They test only longitudinal recovery summaries.

Recovery conclusions are materially sensitive to window size.

For D-drift:

- MCC recovery: 2/5 seeds at 2,500-row windows versus 5/5 at 10,000-row windows;
- FPR recovery: 4/5 versus 0/5;
- MCSC recovery: 5/5 versus 1/5.

The window size changes censoring and apparent recovery timing enough that recovery should remain a
secondary descriptive endpoint. No manuscript headline should depend on a single recovery-window
choice.

This is a robustness limitation, not an invalidation of the whole-post paired endpoints.

## 12. Relationship to the Stage-8 mechanism audit

The Stage-8 post-primary mechanism audit found that approximately 96% of the primary D-drift-versus-C
post-reference MCC gain was associated with validated withdrawal of stale symbolic authority, with a
much smaller contribution from newly added authority and zero retained-authority contribution to the
realized final-decision MCC difference.

Stage 9 does not re-run that Shapley mechanism decomposition under every sensitivity. Therefore it
would be overclaiming to say that the exact 96/4 withdrawal/addition split is itself robust across all
Stage-9 variants.

What Stage 9 does establish is compatible with the mechanism account:

- predictive arm differences remain under lambda<1;
- they disappear exactly at lambda=1;
- static-gate, detector, replay, and latency variants still often retain positive D-drift-versus-C
  predictive effects;
- periodic maintenance remains competitive.

The mechanism-level claim should therefore remain bounded to Stage 8 unless a new prospectively
specified mechanism robustness audit is later added.

## 13. Research-gap consequence

The governing gap asks whether an explicit statistical concept-drift event can serve as the endogenous
gate for a validated and versioned symbolic rule-evolution lifecycle, and whether that symbolic
evolution contributes measurable value beyond an otherwise matched adaptive system while preserving
longitudinal explanation quality.

The current evidence provides a **partial but meaningful answer**.

### Supported provisionally within the fixed scenario

1. An explicit statistical drift-monitor event can operationally gate a validated, versioned symbolic
   lifecycle under causal/time isolation.
2. Symbolic lifecycle evolution can contribute measurable predictive value beyond the same matched
   adaptive neural trajectory and frozen symbolic baseline.
3. That predictive contribution is not dependent on one detector family, one detector signal, replay,
   the primary Wilson-LCB gate, or the exact primary fusion weight.
4. The lambda=1 negative control strongly supports symbolic-path causal attribution.
5. The effect is better characterized as value from the symbolic lifecycle than as proof of unique
   drift-trigger superiority.

### Not supported

1. Drift-gating is categorically superior to matched periodic symbolic maintenance.
2. The detector uniquely or promptly identifies the designated controlled boundary.
3. The lifecycle preserves the prespecified MCSC explanation-quality endpoint.
4. Recovery timing is stable to reporting-window choice.
5. The result generalizes to natural production drift, direct attack-pattern/conditional-label drift,
   unseen attacks, or another dataset.
6. The same withdrawal-dominant mechanism fraction is proven under every robustness variant.

## 14. Current Stage-9 verdict

Stage 9 **strengthens** the Stage-8 predictive claim and **does not rescue** its explanation or
trigger-specific limitations.

The strongest defensible current statement is:

> In the fixed controlled CICIDS2017 scenario, a validated symbolic rule-evolution lifecycle operating
> on a shared adaptive-neural control plane contributes robust predictive value relative to a frozen
> symbolic baseline across multiple prespecified detector, latency, replay, gate, and fusion
> perturbations. The predictive arm differences disappear exactly when symbolic predictive authority
> is removed at lambda=1, supporting symbolic-path causal attribution. However, matched periodic
> maintenance remains competitive, explanation-quality/coverage trade-offs persist, and detector
> timing is not cleanly aligned to the designated scoring boundary.

This is a stronger and more defensible contribution than the Stage-8 result alone, but it is not yet a
broad concept-drift NIDS generalization claim.

## 15. Required next evidence before broad publication claims

The robustness package does not discharge the frozen external-validity requirements.

The next evidence should remain additive and prospectively frozen:

1. at least one direct attack-pattern / conditional-label-change drift scenario;
2. a defensible second flow-oriented dataset with compatible causal semantics;
3. scenario/dataset effects reported separately before any synthesis;
4. no pooling of seeds across scenarios as if they were independent environments;
5. a live novelty/literature audit immediately before manuscript submission.

No Stage-9 result should be used to retune the accepted primary scenario or replace an inconvenient
Stage-8 endpoint.

## 16. Reviewer-facing bottom line

A hostile reviewer can reasonably say that this one scenario does not establish production concept
drift, that periodic maintenance can produce the same broad lifecycle benefit, and that explanation
coverage deteriorates.

The current evidence can answer those criticisms without narrative rescue:

- **yes**, external validity is still limited and requires replication;
- **yes**, periodic maintenance is competitive, so trigger superiority is not claimed;
- **yes**, explanation-quality trade-offs are real and preserved in the interpretation;
- **but** the predictive symbolic contribution itself survives a substantial prespecified robustness
  battery and vanishes under the correct neural-only negative control.

That is the Stage-9 contribution to carry forward.
