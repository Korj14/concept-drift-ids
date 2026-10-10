# Q1 Adversarial Methodology and Implementation Audit Register

**Status:** ACTIVE PUBLICATION-GATE REGISTER  
**Audit basis:** immutable Stage-8 evidence commit `c2ded83b8195b9321e715626c1f305f9627936e8`  
**Purpose:** identify reviewer-grade attacks against code, causal design, statistics, dataset validity, explanation claims, novelty, and deployment interpretation before broader execution or submission.

## 1. Epistemic rule

This project does **not** claim that all possible reviewer criticism can be eliminated.

A Q1-ready standard is instead:

1. no known defect that changes the scientific object remains unresolved;
2. every high-probability reviewer attack is either:
   - controlled directly;
   - tested by a frozen robustness/replication analysis; or
   - explicitly bounded as a limitation that narrows the claim;
3. inconvenient negative evidence remains visible;
4. no post-outcome retuning is permitted to rescue a preferred narrative;
5. broad claims are prohibited until external-validity obligations are satisfied.

## 2. Restart / invalidation criteria

A restart or versioned replacement run is mandatory if any of the following is established:

- future-information or boundary leakage into adaptive decisions;
- treatment-dependent neural trajectories in a contrast claimed to isolate symbolic evolution;
- wrong scenario, preprocessing, System-A checkpoint, R0, threshold, or seed identity;
- labels used before maturity;
- predictions overwritten or retrospectively recomputed for detector evidence;
- candidate generation/validation using future or overlapping forbidden evidence;
- analysis endpoint computed differently from the frozen definition;
- primary seed exclusion because of unfavorable performance;
- implementation mismatch that materially changes a treatment, estimand, endpoint, or information set;
- unrecoverable hash/provenance failure.

### Current disposition

No such defect is currently known in the accepted Stage-8 primary evidence.

The Phase-C `read_jsonl` NameError was a technical execution defect discovered before any successful
Phase-C scoring output existed. The failed attempt and correction lineage are preserved separately.
It does not currently trigger a scientific restart.

## 3. Independently rechecked primary statistics

The five frozen paired effects were independently recomputed outside the repository analysis
implementation.

The independent calculation reproduced exactly:

- E1/E2/E3 mean effects;
- sample SDs;
- Student-t 95% intervals;
- positive/zero/negative sign counts;
- exact one-sided sign-test probabilities;
- leave-one-seed-out mean ranges;
- Holm-Bonferroni adjusted p-values.

This reduces single-implementation risk for the primary statistical summary.

## 4. High-priority reviewer attacks and required disposition

### A. Primary shift is not a clean real-concept-drift experiment

**Attack:** the primary scenario is BENIGN-source-regime-dominant and pseudo-chronological. It is not
a clean demonstration of a change in `P(Y|X)` and must not be presented as natural production
concept drift.

**Severity:** PUBLICATION-CRITICAL, not restart.

**Current control:** disclosed prospectively; boundary scoring-only; no natural timestamp claim.

**Required before broad claim:**

- direct attack-pattern / conditional-label-change scenario;
- gradual drift where defensible;
- unseen-attack scenario where defensible;
- second flow-oriented dataset.

### B. The controlled boundary is not metaphysical drift ground truth

**Attack:** perceived drift depends on window/reference definition; a designated experimental boundary
does not prove that an underlying data-generating process changed exactly at that row.

**Severity:** PUBLICATION-CRITICAL language issue.

**Current control:** boundary is never supplied to adaptation; pre-reference detections are retained.

**Required wording:**

- use “designated controlled boundary/reference”;
- use “pre-reference detector event” rather than universal “false alarm”;
- do not claim the detector found the true natural drift point.

### C. Pre-reference detector events consumed the D-drift symbolic budget

**Observed:** every seed has 2–3 detector events before the designated boundary. Seven of eight
successful D-drift symbolic publications occur before the boundary.

**Attack:** the primary result is not a clean “shift occurs -> detector fires -> symbolic layer
repairs itself” chain.

**Severity:** PUBLICATION-CRITICAL, not restart because this behavior follows the prospectively frozen
policy without boundary leakage.

**Required:**

- primary estimand described as whole-stream endogenous detector-gated policy effect;
- Stage-9 detector/latency robustness executed unchanged;
- trigger timing, opportunity-budget use and publication clocks reported centrally;
- later replication should include a scenario whose intended change produces a more interpretable
  post-change opportunity structure.

### D. E1 does not prove evolved symbolic knowledge beats neural-only adaptation

Frozen post-MCC comparison to lambda=1:

| Seed | C - neural-only | D-drift - neural-only | D-drift - C |
|---:|---:|---:|---:|
| 0 | -0.126928 | -0.078507 | +0.048421 |
| 1 | -0.061266 | +0.002049 | +0.063315 |
| 2 | -0.061843 | +0.008201 | +0.070044 |
| 3 | -0.052779 | +0.007305 | +0.060085 |
| 4 | -0.053442 | +0.003452 | +0.056893 |

Mean:

- C minus neural-only: approximately **-0.07125 MCC**;
- D-drift minus neural-only: approximately **-0.01150 MCC**;
- D-drift minus C: **+0.05975 MCC**.

**Attack:** most of E1 may be stale-rule authority withdrawal rather than new symbolic knowledge
adding predictive information.

**Severity:** MUST-FIX MECHANISM INTERPRETATION.

**Current valid claim:** symbolic lifecycle evolution improves the evolving-symbolic policy relative to
the frozen-symbolic policy on post-regime MCC.

**Claims currently not supported:** that D-drift broadly outperforms the adaptive neural model, or
that new rules themselves are the dominant source of predictive gain.

**Required analysis before submission:**

prospectively freeze a post-primary mechanism decomposition, explicitly exploratory/secondary:

- neural-only;
- frozen C;
- full D lifecycle;
- retirement/demotion-only authority withdrawal;
- candidate-addition/refinement-only where reconstructable;
- coverage/shared-row decomposition;
- C-covered vs D-covered vs both-covered vs neither-covered prediction effects;
- per-rule-version contribution and transition timing.

This analysis must never be retroactively promoted to a primary endpoint.

### E. Explanation endpoint deteriorates

**Observed:** E2 post-MCSC D-drift-C is negative in 4/5 seeds; mean approximately -0.0631.

**Attack:** the proposed symbolic lifecycle does not preserve longitudinal explanation quality in the
primary scenario.

**Severity:** substantive negative result, not a defect.

**Required:**

- report it without euphemism;
- characterize prediction/explanation trade-off;
- report MCSC components, coverage, correctness, conflict and fidelity;
- do not use “explanation recovery” as a primary success claim for Stage 8.

### F. MCSC is project-specific and not a universally validated human-usefulness metric

**Attack:** MCSC combines class-balanced correct symbolic coverage, but reviewers may dispute whether
it captures explanation usefulness, stability, comprehensibility, or analyst trust.

**Severity:** MUST-FIX construct-validity issue if manuscript uses broad “explanation quality”
language.

**Required:**

- keep MCSC definition unchanged;
- triangulate with rule coverage, class correctness, neural fidelity, conflict, stability, complexity,
  churn/version persistence and temporal continuity;
- define MCSC narrowly as class-balanced correct symbolic coverage, not universal explainability;
- if operational analyst usefulness is claimed, add a separate blinded expert/analyst evaluation or
  remove the human-usefulness claim.

### G. Candidate selection and common-validation winner's curse

**Attack:** multiple generated rule candidates are assessed against a shared validation block.
Wilson bounds and gate-persistence bootstrap control local uncertainty but do not constitute a formal
multiple-candidate selective-inference correction.

**Severity:** MUST-DISCLOSE / SHOULD-ROBUSTNESS.

**Current control:** generation/validation separation; future independent validation block; full-gate
bootstrap persistence; deterministic lifecycle rules.

**Required:**

- report number generated, tested, accepted, rejected and published;
- avoid interpreting each accepted rule as an independently hypothesis-tested discovery;
- static-style gate sensitivity;
- consider a nested/holdout candidate-selection diagnostic in later replication if computationally
  feasible.

### H. CICIDS2017 quality and artifact dependence

**Attack:** known traffic-generation, flow-construction, feature-extraction and labeling problems can
materially alter results.

**Severity:** PUBLICATION-CRITICAL external/data validity.

**Current controls:**

- exact-pattern/duplicate robustness;
- pattern-deduplicated teacher and full-chain checks;
- split discipline;
- no random crossing of the controlled boundary;
- no silent relabeling/deduplication in the primary.

**Required:**

- explicitly cite CICIDS2017 quality literature;
- keep claims dataset-bounded;
- add a corrected-CICIDS sensitivity where scientifically useful (e.g. LYCOS/improved reconstruction);
- still add an actually independent second dataset; corrected CICIDS alone does not provide external
  dataset independence.

### I. Destination-port / shortcut learning and source-regime cues

**Attack:** flow-based IDS can exploit dataset-specific shortcuts rather than attack semantics.

**Severity:** SHOULD-ROBUSTNESS / manuscript disclosure.

**Current project:** System-B robustness already includes feature/selection/duplicate diagnostics.

**Required:**

- retain destination-port and exact-pattern robustness in publication supplement;
- report feature dependence where materially high;
- later cross-dataset/scenario replication is the decisive test.

### J. Five seeds are not five environments

**Attack:** n=5 is low-power and all seeds share one stream.

**Severity:** known inferential limitation.

**Current control:** inferential unit and scope are explicit; windows/rules are not pseudo-replicates;
all raw effects and leave-one-out means retained.

**Required:**

- no environmental-population interpretation of the t interval;
- no p-value headline;
- scenario/dataset replication instead of pseudo-replication;
- future independent replication may prospectively use more seeds if affordable, but primary n is not
  extended after outcome inspection to chase significance.

### K. Sign-test/Holm power is intrinsically coarse

With five nonzero paired effects the smallest one-sided sign-test p is 1/32=.03125. In a three-test
Holm family, a perfect 5/5 sign pattern still yields adjusted p=.09375.

**Severity:** design limitation, not coding error.

**Required:**

- emphasize magnitude, raw pairs, uncertainty and replication;
- never imply Holm non-rejection means no E1 effect;
- never switch tests post hoc for significance.

### L. Replay assumptions and poisoning

**Attack:** replay is a strong continual-learning control but creates a security-sensitive memory
surface; primary labels/evidence are trusted.

**Severity:** external operational-security limitation.

**Required:**

- Stage-9 no-replay ablation;
- explicitly disclose trusted-label/replay-integrity assumption;
- if claiming operational robustness, add separately frozen label-noise/replay-poisoning stress tests.

### M. Complete delayed labels are optimistic

**Attack:** L=5,000 models delay but not permanently missing labels, variable delay, or label noise.

**Severity:** external validity.

**Required:**

- execute L=0 and L=10,000;
- disclose fixed-row delay as simulation assumption;
- later partial/noisy-label robustness if operational claims require it.

### N. Supervised hard-error detector is only one drift-monitor class

**Attack:** label-free input/representation/score drift monitors may detect distributional change
earlier and avoid complete-label assumptions.

**Severity:** model-choice limitation.

**Current control:** primary signal was prospectively selected for predictive-degradation relevance.

**Required:**

- PageHinkley hard-error and ADWIN-Brier already prespecified;
- label-free monitoring may be added as a separately frozen diagnostic/replication, not retroactively
  substituted as primary.

### O. Periodic comparator cadence

**Attack:** one evenly spaced periodic cadence is not universally optimal and may advantage/disadvantage
the comparator.

**Severity:** robustness issue, not restart.

**Current control:** same maximum opportunity budget, operator and RNG namespace; cadence frozen
prospectively.

**Required:**

- state explicitly that periodic cadence is one matched comparator;
- if trigger superiority becomes a manuscript claim, add a prospectively defined cadence/random-clock
  sensitivity and report it separately.

### P. Neural architecture specificity

**Attack:** a simple MLP does not establish architecture-invariant symbolic-lifecycle behavior.

**Severity:** external/model validity.

**Required:**

- describe MLP as controlled backbone rather than novelty;
- include serious adaptive-neural baseline/replay;
- for a broad Q1 claim, replicate the higher-level treatment with at least one materially different
  backbone if feasible.

### Q. Neuro-symbolic terminology itself can be challenged

**Attack:** the symbolic layer is partly neural-derived (SHAP + CART surrogate) and fused with neural
scores; some taxonomies may call this post-hoc rule extraction/hybrid XAI rather than deep integrated
neuro-symbolic reasoning.

**Severity:** terminology/novelty risk.

**Required:**

- define the architecture operationally;
- state that rules are teacher-derived and true-label validated;
- avoid claiming independent expert knowledge or logical theorem reasoning;
- position contribution around validated, versioned symbolic lifecycle and causal ablation rather than
  the label “neuro-symbolic” alone.

### R. Real-time/deployment claims are unsupported

**Attack:** logical row time pauses during maintenance and the scenario lacks trustworthy arrival
timestamps.

**Severity:** claim boundary.

**Required:** no production-throughput, backlog or real-time claim from primary evidence. Wall-clock
maintenance cost may be reported only as compute instrumentation.

### S. Adversarial robustness is untested

**Attack:** adaptive IDS and explanations can be attacked via evasion, poisoning, replay manipulation,
or explanation manipulation.

**Severity:** external security robustness.

**Required:** no adversarial-robustness claim. Add separately frozen adversarial evaluation if the
target journal/reviewer scope makes operational security robustness central.

### T. Novelty is crowded and moving

Current literature contains:

- concept-drift-aware predictive adaptation;
- validation-calibrated drift-response frameworks;
- label-free/explainability-driven drift monitoring;
- neuro-symbolic NIDS;
- continual-learning/replay NIDS;
- rule-based drift explanation;
- adaptive interpretable IDS.

**Severity:** Q1 novelty risk.

**Required:** retain the exact narrow gap wording. No “first ever” claim. Refresh literature
adversarially before each major replication milestone and immediately before submission.

## 5. Code-correctness assurance layers still required

CI success is necessary but does not prove absence of code defects.

Before submission, add an independent software audit tranche:

1. fresh-clone reproduction of compact evidence from frozen config/artifacts;
2. independent recomputation of all table/figure statistics;
3. property tests for:
   - prediction-before-label;
   - no boundary input;
   - checkpoint purity;
   - same shared neural trajectory across symbolic arms;
   - lambda=1 exact equality;
   - no generation/validation overlap;
   - write-once outputs;
4. static analysis/lint/type checks;
5. high-value mutation tests for timing, threshold, boundary and identity guards;
6. deterministic same-platform rerun of at least one complete seed in a clean environment;
7. hash audit of every manuscript-referenced artifact;
8. a second implementation of the confirmatory effect calculation retained as a verification script.

## 6. Current restart decision

**Do not restart Stage 8 at this time.**

Reason:

- no known information leakage;
- no known treatment contamination;
- no known wrong frozen identity;
- no known endpoint mismatch;
- no known primary-statistics implementation error;
- the Phase-C crash was correctly versioned before successful scoring;
- current negative/mixed findings arise from the frozen scientific design rather than a discovered
  invalidating defect.

Restarting because results are inconvenient would be scientifically worse than retaining the result.

## 7. Current Q1-readiness decision

**Not Q1-submission-ready yet.**

The primary causal experiment is credible and auditable, but broad publication strength still requires
at minimum:

1. Stage-9 prespecified robustness;
2. explicit symbolic-mechanism decomposition versus neural-only authority withdrawal;
3. explanation-construct triangulation;
4. direct attack-pattern / conditional-label drift replication;
5. second-dataset replication;
6. CICIDS-quality/corrected-data sensitivity where feasible;
7. fresh novelty audit;
8. independent software/reproducibility audit.

A manuscript submitted before these are addressed would leave avoidable reviewer openings.

## 8. Governing decision rule going forward

At every new phase:

- ask first whether a criticism implies **invalidity**, **robustness dependence**, or **scope
  limitation**;
- invalidity -> stop and version/restart;
- robustness dependence -> preserve primary and add frozen matched sensitivity;
- scope limitation -> narrow claim and add replication where the intended claim requires it;
- never use a robustness result to replace an inconvenient primary result;
- never add a new test after outcome access and describe it as prospectively confirmatory.

This register remains active until submission.
