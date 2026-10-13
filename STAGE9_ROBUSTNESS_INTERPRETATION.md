# Stage 9 v1.1 Prespecified Robustness Interpretation

**Status:** POST-EXECUTION INTERPRETATION — FROZEN ROBUSTNESS EVIDENCE  
**Evidence commit:** `9a05602b68cfaee7c45d2002a760b65115a581fd`  
**Stage-9 config manifest:** `b72fc0dce0df46974737cd0c33714cc17b23f31ce188e92d318b1787c0ae027e`  
**Execution plan:** `4ae426dd32ffed2384b4565710364459f4ee0ac2752543d6ec075facf66e53c8`  
**Compact export manifest:** `d2d6f1a75aa427f2ba1769b8fef2d51253a5f10b5d3bfdb6c31de10d811aae22`  
**Robustness aggregate:** `6432dd5791f0baa9bdb2597c072b866814fb614f5a1f670dffec7f760bd1491a`  
**Robustness aggregate raw SHA-256:** `d6e70aaa591de7169ed9acc7f1da7c0aa6edfc7e7d3e8b5e72657d7d1e57be70`  
**Parent Stage-8 evidence commit:** `c2ded83b8195b9321e715626c1f305f9627936e8`

## 1. Classification and interpretation boundary

This document interprets the already frozen Stage-9 v1.1 robustness evidence. It changes no
treatment, comparator, threshold, endpoint, seed, detector setting, replay setting, label latency,
symbolic gate, neural trajectory, statistical family, or compact evidence.

Stage 9 is **prespecified robustness evidence, not a new confirmatory family**. No new p-values are
computed. The inferential unit remains the stochastic seed conditional on the same fixed controlled
scenario. The five seeds are not five independent environments.

The scenario remains the controlled BENIGN-source-regime-dominant
`cicids2017_sudden_benign_v1` stream. Stage 9 therefore strengthens or weakens same-scenario causal
and implementation robustness only. It does not provide environmental replication, natural
production-drift evidence, direct attack-pattern/conditional-label drift evidence, or cross-dataset
generalization.

The immutable Stage-8 primary result is not replaced by any more favorable Stage-9 sensitivity.

## 2. Execution and evidence integrity

The corrected v1.1 matrix completed all 110 frozen steps with no outcome-dependent early stopping.

The final evidence commit has one parent, the accepted Stage-9 v1.1 config-freeze commit
`b882df355de7b865c5623b90604ee50438e4243d`.

The evidence commit adds exactly 358 files, all under:

`results/frozen/cd_robustness_v1_1/`

No file outside that compact-evidence root changes.

The compact manifest describes exactly 357 child files; the manifest itself is the 358th file.
All child paths are unique.

Exact-head Research Contract and Stage-9 robustness-contract CI pass on the evidence commit,
including Stage-8 regression tests.

The accepted compact export contains all eleven prespecified conditions:

- fusion authority: lambda=.70, .90, 1.00;
- reporting windows: 2,500 and 10,000 rows;
- label latency: 0 and 10,000 rows;
- Page-Hinkley on delayed hard error;
- ADWIN on delayed Brier loss;
- no replay;
- static symbolic gate.

## 3. Main robustness question: D-drift versus frozen-symbolic C

The primary same-scenario robustness question is whether the positive Stage-8 D-drift-minus-C
predictive effect survives the already-prespecified perturbations.

Post-regime MCC paired effects are:

| Condition | Mean D-drift − C MCC | Seed signs (+ / 0 / -) | Descriptive 95% t interval |
|---|---:|---:|---:|
| Stage-8 primary lambda=.50 | +0.059752 | 5 / 0 / 0 | [+0.049832, +0.069671] |
| lambda=.70 | +0.049873 | 4 / 0 / 1 | [+0.014058, +0.085689] |
| lambda=.90 | +0.049323 | 5 / 0 / 0 | [+0.025551, +0.073095] |
| lambda=1.00 | +0.000000 | 0 / 5 / 0 | [0.000000, 0.000000] |
| label latency L=0 | +0.035265 | 2 / 3 / 0 | [-0.026748, +0.097278] |
| label latency L=10,000 | +0.045821 | 4 / 1 / 0 | [-0.016340, +0.107983] |
| Page-Hinkley hard error | +0.057254 | 5 / 0 / 0 | [+0.039977, +0.074531] |
| ADWIN Brier | +0.052663 | 5 / 0 / 0 | [+0.024563, +0.080763] |
| no replay | +0.042119 | 4 / 0 / 1 | [+0.011090, +0.073147] |
| static symbolic gate | +0.060361 | 5 / 0 / 0 | [+0.049963, +0.070759] |

The result is therefore not dependent on one exact detector family, one exact detector signal, neural
replay, the online Wilson-LCB gate, or the primary 5,000-row label latency.

The two label-latency variants are weaker in seed consistency than Page-Hinkley, ADWIN-Brier, and
the static gate, but their pattern is mechanistically interpretable rather than contradictory:
seeds in which D-drift publishes no symbolic update can remain exactly tied to C.

The most defensible Stage-9 statement is:

> Within the fixed controlled scenario, the positive predictive effect of drift-gated symbolic
> lifecycle state relative to a frozen-symbolic matched adaptive control is robust to the major
> prespecified implementation choices.

This is a robustness statement, not an environmental-generalization claim.

## 4. Lambda=1 is the decisive causal negative control

At lambda=1.00, symbolic authority is removed from prediction and every arm reduces exactly to the
shared adaptive-neural prediction stream.

For D-drift minus C:

- MCC difference: exactly 0 in all five seeds;
- F1 difference: exactly 0 in all five seeds;
- FPR difference: exactly 0 in all five seeds.

D-drift minus D-periodic is also exactly zero on those predictive outputs.

This is strong causal-isolation evidence. It rules out treatment-specific neural trajectories as the
source of the C/D predictive difference and shows that the difference passes through symbolic
state/fusion.

However, this control also narrows the contribution.

Comparing the primary lambda=.50 arm to the lambda=1 neural-only stream:

- frozen-symbolic C is worse than neural-only in all five seeds, with mean MCC difference
  lambda=.50 minus neural-only of about **-0.07125**;
- D-drift lambda=.50 is better than neural-only in four of five seeds but substantially worse in one,
  giving a mean difference of about **-0.01150**;
- D-periodic lambda=.50 is mixed and has a mean difference of about **-0.00583**.

Therefore Stage 9 does **not** support a blanket claim that evolved symbolic fusion outperforms the
adaptive neural subsystem itself.

The stronger supported mechanism remains:

> symbolic lifecycle adaptation mitigates the predictive damage of stale frozen symbolic authority,
> bringing the neuro-symbolic system much closer to the shared adaptive-neural fallback.

That is consistent with the frozen Stage-8 mechanism audit, in which most D-drift predictive gain
was allocated to validated withdrawal of stale symbolic authority rather than broad superiority of
newly evolved rules.

## 5. Zero-latency behavior is informative, not a failed sensitivity

Under L=0, the D-drift-minus-C MCC seed effects are:

- seed 0: +0.106195;
- seed 1: 0;
- seed 2: +0.070129;
- seed 3: 0;
- seed 4: 0.

The post-export publication-clock diagnostic shows that the three zero-effect seeds have zero
D-drift symbolic publications, while seeds 0 and 2 each have two publications.

This is a descriptive post-export cross-check, not a new inferential test.

It is nevertheless important because it behaves exactly as the causal design predicts: when no
symbolic lifecycle treatment is realized, D-drift and C remain predictively identical; when symbolic
state changes are published, the arms can diverge.

No extra seed is created from publications, opportunities, rows, or clocks.

## 6. Detector-family and detector-signal robustness

The Page-Hinkley hard-error sensitivity produces mean D-drift-minus-C MCC **+0.057254**, positive in
all five seeds.

The ADWIN-Brier sensitivity produces mean D-drift-minus-C MCC **+0.052663**, also positive in all
five seeds.

The primary effect therefore does not appear to be an artifact of one specific combination of ADWIN
and delayed hard-error input.

This does not establish a universally optimal drift detector. It shows that the symbolic-lifecycle
effect survives two prespecified alternative detector constructions in the same scenario.

## 7. Replay and symbolic-gate robustness

Removing neural replay leaves a mean D-drift-minus-C MCC effect of **+0.042119**, with four positive
seeds and one very small negative seed.

Replacing the primary uncertainty-aware symbolic gate with the frozen static-style gate yields mean
D-drift-minus-C MCC **+0.060361**, positive in all five seeds.

The Stage-8 finding therefore does not depend on replay or on the Wilson lower-bound component of the
primary symbolic gate.

Neither sensitivity may replace the primary configuration.

## 8. Trigger-specific superiority is not established

The D-drift-minus-D-periodic MCC contrast is not stable in sign across Stage 9:

| Condition | Mean D-drift − D-periodic MCC | Seed signs (+ / 0 / -) |
|---|---:|---:|
| lambda=.70 | +0.002434 | 3 / 0 / 2 |
| lambda=.90 | -0.005932 | 2 / 0 / 3 |
| lambda=1.00 | 0.000000 | 0 / 5 / 0 |
| L=0 | -0.035064 | 1 / 0 / 4 |
| L=10,000 | +0.024061 | 4 / 1 / 0 |
| Page-Hinkley hard error | +0.003743 | 2 / 0 / 3 |
| ADWIN Brier | -0.010525 | 4 / 0 / 1 |
| no replay | +0.001217 | 2 / 0 / 3 |
| static symbolic gate | -0.005064 | 3 / 0 / 2 |

The L=10,000 condition descriptively favors D-drift and has a positive descriptive t interval, while
L=0 favors periodic maintenance. Other conditions are small or mixed.

The correct conclusion is:

> Stage 9 supports drift-gating as a viable endogenous lifecycle scheduler, but does not establish
> that drift-triggered maintenance is categorically superior to matched periodic maintenance.

This is a central limitation, not a secondary footnote.

## 9. Explanation-quality and coverage trade-off remains

Stage 9 does not rescue the primary MCSC result.

For D-drift minus C, mean post-regime MCSC differences are generally negative:

- lambda sensitivities: about -0.0631;
- L=0: -0.0057;
- L=10,000: -0.0093;
- Page-Hinkley: -0.0650, negative in all five seeds;
- ADWIN-Brier: -0.1052;
- no replay: -0.0498;
- static gate: -0.0565.

Resolved symbolic coverage also generally falls for D-drift relative to C.

The lifecycle can therefore improve predictive behavior while reducing the amount of correctly
resolved symbolic authority.

No manuscript should claim that Stage 9 establishes a prediction-and-explanation win-win.

The more defensible interpretation is a trade-off:

> lifecycle adaptation can improve prediction by withdrawing or changing stale symbolic authority,
> but that same process can reduce class-balanced correct symbolic coverage.

## 10. Trigger timing still rejects a simple boundary-detect-then-repair story

The controlled boundary remains row 69,260 and is never supplied to the adaptive components.

Across the prespecified scored variants, detector events occur both before and after that boundary.

A deterministic post-export publication-clock audit derived from the frozen arm manifests further
shows that many successful D-drift publications occur before the controlled boundary:

- L=0: 4 pre-reference, 0 post-reference D-drift publications;
- L=10,000: 3 pre-reference, 6 post-reference;
- Page-Hinkley: 6 pre-reference, 4 post-reference;
- ADWIN-Brier: 9 pre-reference, 4 post-reference;
- no replay: 6 pre-reference, 1 post-reference;
- static gate: 6 pre-reference, 1 post-reference.

The publication-clock audit is preserved at `results/audits/stage9_v1_1_publication_clock_audit.json`, with its deterministic derivation documented in `results/audits/STAGE9_V1_1_PUBLICATION_CLOCK_AUDIT.md`. It is descriptive/post-export and creates no new hypothesis test.

Its timing result is nevertheless consistent with Stage 8 and further constrains causal language.

The experiment does not identify a clean sequence of:

controlled boundary -> detector recognizes that boundary -> symbolic repair -> recovery.

The estimand remains the downstream effect of an endogenous detector-gated symbolic lifecycle
operating over the full stream, whose state may already differ before the designated scoring
boundary.

## 11. Reporting-window recovery is not stable enough for a strong timing claim

The 2,500-row and 10,000-row conditions are reporting sensitivities only. They do not rerun the
adaptive system and do not alter whole-post Stage-8 endpoints.

Recovery status and observed recovery time change materially with reporting-window size.

For example, D-drift MCC recovery is observed in:

- 2/5 seeds under 2,500-row windows;
- 3/5 seeds under the primary 5,000-row windows;
- 5/5 seeds under 10,000-row windows.

MCSC and FPR recovery classifications also change with window size and censoring.

Therefore no precise recovery-time claim should be elevated to a central contribution.

Recovery remains secondary, descriptive, and sensitive to reporting granularity.

## 12. What Stage 9 strengthens

Within this one controlled scenario, Stage 9 materially strengthens the following claims:

1. The D-drift-versus-C predictive effect is not an artifact of the exact primary detector,
   detector signal, replay setting, symbolic gate, or label latency.
2. Matched C/D arm differences are genuinely symbolic: the lambda=1 neural-only control removes
   predictive arm differences exactly.
3. The Stage-8 withdrawal-dominant mechanism is compatible with the robustness evidence.
4. Symbolic lifecycle treatment can mitigate stale-symbolic interference under several
   prespecified perturbations.
5. The system's causal isolation and provenance machinery survive a much broader execution matrix
   than the primary experiment alone.

## 13. What Stage 9 weakens or leaves unsupported

Stage 9 does not support:

- drift-gated trigger superiority over periodic maintenance;
- universal improvement of explanation quality;
- preservation of resolved symbolic coverage;
- broad superiority of evolved neuro-symbolic prediction over neural-only prediction;
- a clean post-boundary detection-and-repair story;
- precise recovery-time claims;
- generalization beyond the controlled CICIDS2017 scenario;
- environmental or deployment-population inference.

These are not failed attempts to rescue the narrative. They are the accepted outcomes of the frozen
robustness program.

## 14. Research-gap implication

The governing research gap asks whether an explicit statistical concept-drift event can serve as the
endogenous gate for a validated and versioned symbolic-rule lifecycle, and whether that symbolic
evolution contributes measurable value beyond an otherwise matched adaptive system while preserving
longitudinal explanation quality.

Stage 8 plus Stage 9 now provide a **partial and scientifically useful answer**:

### Supported provisionally

An explicit statistical detector event can serve as an endogenous gate for a versioned,
validation-controlled symbolic lifecycle without contaminating the shared adaptive-neural trajectory.

That lifecycle can materially change predictive outcomes relative to a matched adaptive system whose
symbolic state is frozen, and this effect survives the major prespecified same-scenario
perturbations.

### Not supported as a stronger claim

The evidence does not show that drift-gating is better than periodic scheduling.

It does not show a consistent predictive advantage over neural-only.

It does not show preservation of the prespecified explanation-quality endpoint or resolved symbolic
coverage.

Accordingly, the strongest current contribution is not:

> adaptive symbolic rules broadly outperform neural-only prediction and preserve explanations.

It is:

> under a matched adaptive-neural control, validated symbolic lifecycle evolution can reduce the
> predictive harm of stale symbolic authority through an auditable endogenous maintenance process;
> that causal effect is robust to several prespecified implementation choices, while trigger
> superiority, explanation preservation, and broader generalization remain unresolved or
> unsupported.

That is a meaningful answer to an under-controlled part of the research gap, but it is not yet the
full external-validity result required for a broad NIDS claim.

## 15. Required next evidence

Per the already-frozen protocol and doctrine, the next work is replication, not retuning.

Priority:

1. freeze and execute at least one scenario with a direct attack-pattern or conditional-label-change
   opportunity;
2. freeze and execute a defensible second flow-oriented dataset whose feature and label semantics
   permit the same causal protocol without artificial harmonization;
3. report scenario/dataset results separately before any cross-scenario synthesis;
4. do not pool five-seed families as though they were independent environments;
5. preserve Stage-8 and Stage-9 primary/robustness evidence unchanged regardless of replication
   direction;
6. rerun the literature/novelty audit immediately before manuscript submission.

## 16. Current Stage-9 verdict

Stage 9 **strengthens the causal and implementation-robustness case while narrowing the scientific
claim**.

The strongest positive result is that D-drift's predictive advantage over frozen-symbolic C survives
the main prespecified implementation perturbations and disappears exactly under the neural-only
negative control.

The strongest negative result is that this is not a general proof that drift-gated symbolic
maintenance beats periodic maintenance or neural-only prediction, and explanation-quality/coverage
trade-offs remain.

The project therefore has a defensible same-scenario causal result:

> validated symbolic lifecycle evolution matters, and its value is robustly associated with
> mitigating stale symbolic authority under a shared adaptive-neural trajectory.

The next stage must determine whether that result survives a more direct attack-pattern/conditional
drift opportunity and a second dataset before any broader publication claim is made.
