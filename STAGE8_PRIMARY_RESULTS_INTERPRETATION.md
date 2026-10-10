# Stage 8 Primary C/D Results Interpretation

**Status:** POST-EXECUTION INTERPRETATION — IMMUTABLE PRIMARY EVIDENCE  
**Evidence commit:** `c2ded83b8195b9321e715626c1f305f9627936e8`  
**Compact export manifest:** `409b516d75cbc5e71d3633019008432ea6088d1d923b4e4a95570263528ed523`  
**Confirmatory aggregate manifest:** `1be77ce4be9f3faad021a3f3bfd636488e5de6aa1b2a6e7c596e48feb41bb54d`  
**Corrected Phase-C config:** `d380fce5f9db8f0b639dc999298a263b10a10a3d02e35def226a121d098e2222`  
**Archival Research Contract:** run #512 — success

## 1. Interpretation boundary

This document interprets the already frozen Stage-8 primary evidence. It changes no experiment,
threshold, endpoint, trigger, seed, model, rule operator, or inferential procedure.

The primary scenario remains the controlled BENIGN-source-regime-dominant
`cicids2017_sudden_benign_v1` stream. Results therefore quantify matched stochastic-seed variation
conditional on this one fixed scenario. They do not establish deployment-population or cross-dataset
generalization.

The five seed-level confirmatory effects are the inferential units. Windows, detector events, rules,
publications, and maintenance opportunities are longitudinal/nested observations and are not promoted
to independent replicates.

## 2. Primary confirmatory family

### E1 — post-drift MCC: D-drift minus C

Paired effects by seed:

| Seed | D-drift − C post MCC |
|---:|---:|
| 0 | +0.048421 |
| 1 | +0.063315 |
| 2 | +0.070044 |
| 3 | +0.060085 |
| 4 | +0.056893 |

Frozen summary:

- mean paired effect: **+0.059752**
- median: **+0.060085**
- sample SD: **0.007989**
- 95% paired Student-t interval: **[+0.049832, +0.069671]**
- sign pattern: **5 positive / 0 zero / 0 negative**
- leave-one-seed-out mean range: **[+0.057179, +0.062584]**
- exact one-sided sign-test p: **0.03125**
- Holm-adjusted p across the three-endpoint family: **0.09375**

Interpretation:

The predictive effect is highly consistent across the five stochastic seeds and materially large on
the MCC scale within this controlled scenario. The paired interval is wholly positive and the
leave-one-seed-out means are tightly clustered.

However, the prespecified familywise sign-test criterion does **not** cross alpha=.05 after Holm
adjustment. This is not converted into a claim of “no effect”: the frozen analysis plan explicitly
treats p-values as secondary calibration with n=5. The correct statement is that the primary scenario
provides strong magnitude-and-consistency evidence for improved post-regime MCC, but not a
Holm-adjusted sign-test rejection at familywise .05.

### E2 — post-drift MCSC: D-drift minus C

Paired effects by seed:

| Seed | D-drift − C post MCSC |
|---:|---:|
| 0 | +0.063516 |
| 1 | -0.089166 |
| 2 | -0.110064 |
| 3 | -0.089410 |
| 4 | -0.090392 |

Frozen summary:

- mean paired effect: **-0.063103**
- median: **-0.089410**
- sample SD: **0.071333**
- 95% paired Student-t interval: **[-0.151675, +0.025469]**
- sign pattern: **1 positive / 0 zero / 4 negative**
- exact one-sided benefit-direction sign-test p: **0.96875**
- Holm-adjusted p: **1.0**

Interpretation:

The primary evidence does **not** support the hypothesis that drift-gated symbolic evolution improves
post-regime MCSC relative to the frozen symbolic baseline. Four of five seeds move in the opposite
direction. Any manuscript claim that symbolic evolution “preserved” or “restored” longitudinal
explanation quality in this primary scenario would be contradicted by the frozen evidence.

### E3 — post-drift MCSC: D-drift minus D-periodic

Paired effects by seed:

| Seed | D-drift − D-periodic post MCSC |
|---:|---:|
| 0 | +0.117635 |
| 1 | -0.078612 |
| 2 | -0.033089 |
| 3 | +0.005237 |
| 4 | -0.076167 |

Frozen summary:

- mean paired effect: **-0.012999**
- median: **-0.033089**
- sample SD: **0.080772**
- 95% paired Student-t interval: **[-0.113291, +0.087293]**
- sign pattern: **2 positive / 0 zero / 3 negative**
- exact one-sided sign-test p: **0.8125**
- Holm-adjusted p: **1.0**

Interpretation:

There is no primary evidence that the ADWIN drift gate yields better post-regime symbolic explanation
quality than the matched periodic trigger. The direction is mixed and the mean favors periodic
maintenance slightly.

## 3. Descriptive post-regime operating picture

Across the five seeds, mean primary-lambda=.50 post-regime outcomes were:

| Arm | MCC | F1 | Recall | FPR | MCSC | Resolved coverage | Uncovered rate |
|---|---:|---:|---:|---:|---:|---:|---:|
| C frozen symbolic | 0.841875 | 0.837437 | 0.727064 | 0.000368 | 0.750184 | 0.957318 | 0.042682 |
| D-drift | 0.901627 | 0.902405 | 0.838847 | 0.000929 | 0.687081 | 0.813143 | 0.186369 |
| D-periodic | 0.907300 | 0.907360 | 0.845452 | 0.000734 | 0.700080 | 0.854442 | 0.145492 |

These marginal means are descriptive only; the confirmatory inference remains paired by seed.

The mechanism-level trade-off is clear:

- D-drift increases mean post-regime recall by about **0.112** relative to C;
- its mean FPR also rises by about **0.00056 absolute**;
- its mean resolved symbolic coverage drops by about **0.144**;
- its mean uncovered rate rises from about **4.3% to 18.6%**;
- MCSC therefore decreases on average even while predictive MCC improves.

The evidence therefore supports a **predictive-versus-explanation trade-off**, not a universal
improvement.

## 4. Trigger timing is a major interpretation constraint

The designated controlled boundary is row **69,260** and was never supplied to the adaptive system.

Observed ADWIN hard-error trigger diagnostics:

| Seed | Pre-reference alarms | First post-reference confirmation delay | Latency-adjusted excess delay |
|---:|---:|---:|---:|
| 0 | 2 | 21,851 rows | 16,851 rows |
| 1 | 3 | 14,275 rows | 9,275 rows |
| 2 | 3 | 26,739 rows | 21,739 rows |
| 3 | 3 | 11,011 rows | 6,011 rows |
| 4 | 3 | 16,387 rows | 11,387 rows |

Every seed produced multiple detector events before the designated shift. This is not information
leakage: the boundary was scoring-only. It is nevertheless scientifically important because
D-drift uses the first four confirmed detector opportunities.

D-drift symbolic publication clocks were:

- seed 0: **30,000; 58,360; 121,112**
- seed 1: **60,000**
- seed 2: **30,000; 65,168**
- seed 3: **60,000**
- seed 4: **60,000**

Thus **7 of 8 D-drift symbolic publications occurred before the designated boundary**. Only the final
seed-0 publication occurred after it.

This sharply constrains causal language. The primary D-drift contrast measures the downstream effect
of an **endogenous detector-gated symbolic lifecycle over the whole stream**, whose state was already
altered before the controlled shift in most seeds. It is not a clean experiment in which the
designated boundary occurs, the detector then identifies that shift, and the symbolic layer is
subsequently repaired.

That distinction must be explicit in any paper.

## 5. D-drift versus periodic maintenance

Both trigger arms had the same frozen maximum budget of four symbolic opportunities per seed.

Mean realized maintenance quantities:

| Quantity | D-drift | D-periodic |
|---|---:|---:|
| opportunities / seed | 4.0 | 4.0 |
| candidates / seed | 26.6 | 31.6 |
| completed validations / seed | 1.6 | 1.6 |
| censored/blocked / seed | 2.4 | 2.4 |
| publications / seed | 1.6 | 1.6 |
| compute seconds / seed | 42.04 | 41.40 |
| mean validation-wait rows | 14,999 | 25,893.5 |

The drift trigger therefore did not reduce publication count or total symbolic compute in the primary
run. It did yield much shorter validation waiting in logical rows, because drift opportunities were
opened relative to detector events rather than fixed periodic clocks.

Descriptively, D-periodic actually has slightly higher mean post MCC than D-drift
(**0.9073 vs 0.9016**) and slightly higher mean post MCSC (**0.7001 vs 0.6871**). Those marginal
differences are not replacements for the frozen confirmatory family, but they reinforce the absence of
evidence that the primary ADWIN trigger is categorically superior to periodic maintenance.

## 6. Recovery behavior

Recovery metrics are secondary and use the frozen two-window persistence rule.

For post-regime MCC:

- C recovered in 2/5 seeds and was right-censored in 3/5;
- D-drift recovered in 3/5 seeds and was right-censored in 2/5;
- D-periodic recovered in 4/5 seeds and was right-censored in 1/5.

For MCSC:

- C recovered in 5/5 seeds;
- D-drift recovered in only 1/5 seeds;
- D-periodic recovered in 3/5 seeds.

This is consistent with the whole-post endpoints: adaptive symbolic maintenance improves predictive
behavior in important cases but often fails to restore the frozen symbolic explanation baseline.

No recovery statistic is promoted to an independent confirmatory replicate.

## 7. Neural control-plane retention

The lambda=1 negative control passed exactly for all five seeds, proving that matched arms reduce to
the identical shared neural prediction stream when symbolic authority is removed.

The shared adaptive neural control also retained or improved strong offline development and
pre-reference performance at the final checkpoint in each seed. Final checkpoint development MCC
values were approximately **0.961–0.980**, and final pre-reference MCC values approximately
**0.949–0.966**.

This supports the intended causal isolation: the C/D differences at lambda=.50 are attributable to
symbolic-state/fusion differences on a shared neural trajectory rather than to different neural
training histories across arms.

These retention probes remain secondary diagnostics and were never fed back into adaptation.

## 8. What the primary experiment supports

Within the fixed primary scenario, the evidence supports the following bounded conclusions:

1. **Incremental symbolic evolution materially changed predictive behavior beyond the matched shared
   adaptive neural trajectory and frozen symbolic baseline.**
2. **For D-drift versus C, post-regime MCC improved consistently in all five seeds, with mean paired
   gain about +0.060.**
3. **That predictive gain did not preserve explanation quality under the prespecified MCSC endpoint;
   four of five D-drift seeds had lower post-regime MCSC than C.**
4. **The primary ADWIN hard-error trigger did not demonstrate superior MCSC to matched periodic
   maintenance.**
5. **The realized trigger timing is imperfectly aligned to the designated shift: repeated pre-boundary
   detector events caused most D-drift symbolic publications to occur before the boundary.**
6. **The experiment therefore demonstrates value and cost of endogenous detector-gated symbolic
   evolution, but not a clean post-boundary symbolic-repair mechanism.**

## 9. What the primary experiment does not support

The following claims would overstate the evidence:

- that D-drift is universally better than C;
- that symbolic evolution preserved or restored explanation quality;
- that ADWIN drift-gating is superior to periodic symbolic maintenance;
- that the detector uniquely identified the designated controlled boundary;
- that the post-regime MCC gain generalizes to natural production drift;
- that five seeds represent five independent deployment environments;
- that this one BENIGN-source-regime-dominant scenario establishes real-concept-drift robustness;
- that the system is production-real-time or adversarially robust.

## 10. Publication-critical next evidence

Per the frozen statistical plan and doctrine, the primary result is now immutable. The next work is
additive robustness/replication, not retuning.

Priority order:

1. execute the already-prespecified primary robustness package:
   - label latency L=0 and L=10,000;
   - Page-Hinkley on the same delayed hard-error signal;
   - ADWIN on delayed Brier loss;
   - no-replay neural ablation;
   - lambda=.70 and lambda=.90;
   - 2,500-row and 10,000-row recovery-window sensitivities;
   - static-style symbolic gate sensitivity;
2. treat trigger behavior as a central robustness question, especially pre-reference alarm burden and
   opportunity-budget consumption;
3. add at least one direct attack-pattern / conditional-label-change scenario;
4. add a defensible second flow-oriented dataset;
5. keep all scenario/dataset families separate before any broader synthesis;
6. rerun the live novelty audit immediately before manuscript submission.

A future trigger variant is scientifically justified only if prospectively frozen as a new
robustness/replication treatment. The primary ADWIN result must not be replaced because its trigger
timing is inconvenient.

## 11. Current primary verdict

The primary Stage-8 result is **scientifically informative but mixed**.

The strongest positive evidence is a stable, practically meaningful post-regime MCC gain from the
D-drift symbolic trajectory relative to C.

The strongest negative evidence is that symbolic explanation quality generally deteriorates, and the
realized drift trigger is poorly aligned with the designated shift in the sense that most successful
symbolic publications occur before the known boundary.

This does not invalidate the research program. It narrows the contribution from “drift-triggered
symbolic evolution restores both detection and explanations” to a more defensible question:

> under a matched adaptive-neural control, endogenous detector-gated symbolic evolution can provide
> measurable predictive value, but its explanation-quality and trigger-timing behavior are not
> automatically favorable and require explicit robustness and replication evidence.

That is the interpretation to carry forward unless the prespecified robustness and replication stages
materially change the evidentiary picture.
