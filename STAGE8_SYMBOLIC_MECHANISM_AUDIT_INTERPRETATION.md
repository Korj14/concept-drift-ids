# Stage 8 Symbolic Mechanism Audit v1.2 Interpretation

**Status:** FROZEN POST-PRIMARY EXPLORATORY INTERPRETATION  
**Mechanism evidence archive commit:** `90e574fd3cee278fd4514609c24dfe58d5c6d944`  
**Mechanism config commit:** `325604265c9ef5478e897d76adc9b45ad20eb929`  
**Mechanism config manifest:** `e7d1ffe85a9d8442435c279bee79103f23a468b3fdf52f6f92f427e4f6131e7d`  
**Mechanism audit manifest:** `c8edd1228942371d55b13e196c3050a9fa64d51c9e36069dc218c0dc03c89b66`  
**Mechanism aggregate:** `6c35c026c52fa7bee93cd31bffa459b2bf605efe950f9645e6bea48f86a99acd`  
**Parent Stage-8 evidence:** `c2ded83b8195b9321e715626c1f305f9627936e8`

## 1. Classification

This document interprets the already-frozen Stage-8 symbolic-value mechanism audit.

The mechanism audit is exploratory/descriptive and post-primary. It creates no new p-value family,
does not replace E1/E2/E3, and does not modify any primary prediction, treatment, endpoint, threshold,
detector event, symbolic trajectory, or confirmatory statistic.

The audit regenerated all five seed results from the frozen heavy Phase-C traces during
`--verify-only` and reproduced the same aggregate and audit-manifest identities as the original
v1.2 execution.

## 2. Main D-drift versus C post-reference result

The frozen primary D-drift minus C post-reference MCC effect is reproduced exactly in the mechanism
audit:

- seed effects: +0.048421, +0.063315, +0.070044, +0.060085, +0.056893;
- mean effect: +0.059752;
- all five seeds positive.

The exact three-stratum Shapley allocation shows:

- **withdrawal**
  - mean MCC contribution: +0.057321;
  - positive in 5/5 seeds;
  - mean post-domain row fraction: 0.157895;
  - mean net corrected decisions: +346.8 per seed;
- **addition**
  - mean MCC contribution: +0.002431;
  - positive in 5/5 seeds;
  - mean post-domain row fraction: 0.013720;
  - mean net corrected decisions: +15.8 per seed;
- **retained authority**
  - mean MCC contribution: exactly 0.000000;
  - zero in 5/5 seeds;
  - mean post-domain row fraction: 0.799423;
  - mean net corrected decisions: exactly 0.0.

Using the aggregate means, withdrawal accounts for approximately **96%** of the realized mean
D-drift-versus-C post-reference MCC difference. Addition accounts for approximately **4%**.
Retained-authority rows account for none of the realized final-decision MCC difference.

This is the central mechanism finding.

## 3. What withdrawal is doing

Across the five frozen D-drift post-reference traces, the withdrawal strata contain:

- 1,997 rescues;
- 263 harms;
- net +1,734 corrected decisions.

These row counts are descriptive longitudinal observations, not independent replicates.

The confusion accounting is highly structured. On withdrawal rows, C has no false positives in any
seed. Its errors are missed attacks. D-drift withdrawal therefore rescues attack false negatives by
removing symbolic authority and using the shared fallback path, while the corresponding harms appear
as benign false positives.

The defensible mechanism statement is therefore:

> Within the fixed primary scenario, most of the D-drift predictive gain over frozen-symbolic C is
> associated with withdrawal of stale symbolic authority, which restores attack decisions from the
> shared adaptive-neural fallback on rows where the frozen symbolic state had been suppressing them.

This is evidence for **stale-symbolic-interference mitigation through validated authority
withdrawal/abstention**.

It is not evidence that newly evolved rules generally outperform the shared adaptive neural
predictor.

## 4. What addition is doing

Addition is consistently positive but much smaller.

Across the five D-drift post-reference traces:

- addition produces 79 rescues and 0 harms;
- the mean net gain is +15.8 corrected decisions per seed;
- the mean Shapley MCC contribution is +0.002431.

The class-level confusion accounting shows that these rescues are corrections of benign false
positives. The newly authoritative D-drift symbolic state does not produce a corresponding set of
rescued attack false negatives in this post-reference decomposition.

The appropriate bounded interpretation is:

> Newly established symbolic authority contributes a small additional predictive benefit, primarily
> by suppressing a limited number of benign false positives.

Seed 2 is the only seed in which the addition MCC contribution is material relative to the total:
+0.010294 of a +0.070044 total effect. In the other four seeds the addition contribution is below
+0.0007.

## 5. Retained authority is not the source of the gain

Retained-authority rows comprise approximately 80% of the post-reference domain on average, yet their
Shapley MCC contribution and net corrected-decision contribution are exactly zero in all five
D-drift seeds.

This means the stored lambda=.50 primary decisions do not change between C and D-drift on rows where
both systems retain symbolic authority.

It does **not** prove that internal symbolic scores, rule identities, or explanations are identical.
It establishes only that retained symbolic authority does not change the final primary decisions in
this decomposition.

Accordingly, the Stage-8 predictive gain must not be described as broad improvement from revised
rules acting on already-covered rows.

## 6. Timing further rejects a simple post-boundary repair narrative

D-drift produced eight successful symbolic publications across the five seeds:

- seven were effective before the designated controlled boundary at row 69,260;
- one was effective after the boundary.

The pre-reference D-drift-versus-C domain already has a positive mean MCC difference of +0.014659,
of which +0.014520 is allocated to withdrawal.

For seed 0, the version-level post-reference accounting is especially informative:

- pre-reference-published `d-s0-v0002` is active from row 69,260 through 121,111 and produces
  +280 net corrected decisions over that segment;
- the only post-reference D-drift publication, `d-s0-v0003` at row 121,112, produces -1 net
  corrected decision over its later segment.

Version-level net corrections are not a Shapley MCC decomposition, so they must not be substituted
for the MCC allocation. They nevertheless reinforce the timing conclusion:

> The observed post-reference benefit is not evidence of a clean sequence in which the designated
> boundary occurs, ADWIN detects it, and a subsequently published symbolic repair produces the gain.

The more defensible estimand remains the downstream effect of an endogenous detector-gated symbolic
lifecycle operating over the whole stream.

## 7. D-periodic shows the same mechanism family

D-periodic versus C is also withdrawal-dominant post-reference:

- mean total MCC difference: +0.065425;
- withdrawal mean Shapley contribution: +0.065302;
- addition mean contribution: +0.000400;
- retained-authority mean contribution: -0.000277;
- four seeds positive and one seed negative.

This is descriptive matched-comparator context, not a new confirmatory endpoint.

The key implication is that withdrawal of stale symbolic authority is **not specific to the ADWIN
drift-gated schedule**. Periodic maintenance can produce the same mechanism and is descriptively at
least as competitive in this fixed scenario.

Therefore the mechanism audit strengthens the evidence that the symbolic lifecycle can mitigate
stale-rule interference, while weakening any attempt to attribute that value specifically to the
primary drift trigger.

## 8. Relationship to the neural-only negative control

The frozen lambda=1 analysis already showed that:

- C remains substantially below the shared neural-only stream post-reference;
- D-drift moves much closer to the shared neural-only stream;
- D-drift still does not establish broad superiority over neural-only prediction.

The mechanism decomposition explains that pattern.

The positive D-drift-minus-C effect is largely obtained by withdrawing symbolic authority on rows
where the frozen C symbolic state harms the shared neural decision. This is consistent with the
lambda=1 finding and is not an alternative explanation that rescues a stronger evolved-rule claim.

The correct contribution is therefore not:

> evolved symbolic rules broadly beat the adaptive neural model.

It is:

> a validated symbolic lifecycle can detect and remove stale symbolic authority, reducing the damage
> caused by a frozen symbolic layer while preserving an auditable versioned symbolic control process.

## 9. Explanation-quality trade-off remains

Nothing in this audit reverses the primary MCSC result.

D-drift improved post-reference MCC but reduced the prespecified class-balanced correct symbolic
coverage endpoint relative to C in four of five seeds. The mechanism result explains why that trade-off
is plausible: withdrawal improves predictive behavior precisely by reducing symbolic authority on a
non-trivial portion of the stream.

Therefore no claim that the lifecycle simultaneously improves prediction and preserves explanation
coverage is supported by Stage 8.

MCSC must continue to be described as class-balanced correct symbolic coverage, not universal human
explanation usefulness.

## 10. Supported and unsupported mechanism claims

### Supported, within the fixed scenario

- D-drift's post-reference predictive gain over C is predominantly withdrawal-driven.
- The lifecycle mitigates stale symbolic interference primarily through authority
  withdrawal/abstention and fallback to the shared adaptive-neural path.
- Newly added symbolic authority supplies a small positive secondary contribution, mainly through
  benign false-positive correction.
- Retained symbolic authority does not contribute to the realized primary decision difference.
- The same withdrawal mechanism also appears under periodic maintenance.

### Not supported

- evolved rules generally outperform neural-only prediction;
- retained/revised rules are the main source of the MCC gain;
- the designated boundary caused a post-boundary symbolic repair that explains E1;
- ADWIN drift-gating is mechanistically superior to periodic scheduling;
- the mechanism generalizes beyond the fixed controlled CICIDS2017 scenario;
- row-level rescues or rule versions are independent inferential replicates.

## 11. Consequence for Stage 9

The already-frozen Stage-9 protocol remains unchanged.

The mechanism result increases the importance of the prespecified tests that bear directly on this
interpretation:

- lambda=.70/.90/1.00 authority sensitivities;
- label-latency sensitivity;
- PageHinkley and ADWIN-Brier detector variants;
- no-replay neural ablation;
- static-style symbolic gate sensitivity;
- trigger timing and opportunity-budget accounting.

Stage 9 must not be retuned to manufacture more addition or retained-authority contribution.

The primary question for robustness is now whether the withdrawal-dominant lifecycle effect remains
stable under the already-prespecified perturbations, and whether any evidence emerges that the drift
trigger provides value beyond a matched periodic opportunity schedule.

## 12. Current mechanism verdict

The Stage-8 mechanism audit resolves the main neural-only ambiguity in a scientifically useful but
narrowing direction.

The strongest defensible statement is:

> In the fixed primary scenario, adaptive symbolic lifecycle value arises predominantly from
> validated withdrawal of stale symbolic authority rather than from newly evolved rules changing
> decisions on rows where symbolic authority is retained. This withdrawal restores many missed attack
> decisions from the shared adaptive-neural fallback, with a smaller secondary benefit from newly
> established symbolic authority. Because matched periodic maintenance exhibits the same
> withdrawal-dominant mechanism, Stage 8 does not establish that ADWIN drift-gating itself is the
> uniquely valuable component.

This result is exploratory/post-primary, but it is fully compatible with the immutable Stage-8
primary evidence and materially sharpens the causal interpretation that Stage 9 must test.
