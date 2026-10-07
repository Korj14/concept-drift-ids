# System B / Pre-C-D Robustness Plan

**Status:** PROSPECTIVE FOR C/D; POST-HOC ROBUSTNESS ONLY FOR ALREADY-OBSERVED SYSTEM B  
**Freeze date:** 7 October 2026  
**Primary System-B evidence remains immutable.**

This document fixes the high-leverage robustness questions before any adaptive C/D held-out outcome is observed. The first System-B held-out outcomes are already known, so nothing here may replace or retune R0.v1, lambda=0.50, the five fused thresholds, or the first B evaluation. New B sensitivity results are secondary/post-hoc robustness only.

## 1. SHAP reference distribution

Primary remains DeepExplainer on raw attack logit with the balanced 128/128 training background and balanced 1,024/1,024 attribution sample, seed 20261007.

Robustness variants:

- natural-prevalence training background, n=256;
- balanced 128/128 backgrounds with deterministic seeds 20261007, 20261008, 20261009.

Keep the frozen attribution sample when isolating background sensitivity. Report top-k Jaccard, rank correlation, feature turnover, candidate/accepted-rule counts and surrogate/accepted-rule fidelity. Do not describe absolute SHAP magnitude as prevalence-neutral.

## 2. Feature-count sensitivity

Primary k=12. One-factor variants: k in {8,12,16}. Report surrogate fidelity, accepted-rule coverage, rule count/complexity and selected-feature stability. Do not tune k on B held-out outcomes.

## 3. Destination Port sensitivity

Destination Port remains in the primary frozen representation. A mandatory robustness variant excludes Destination Port from SHAP selection and surrogate/rule antecedents while leaving the frozen neural detector and all other representation inputs unchanged.

This is a benchmark-shortcut sensitivity, not a replacement primary model. Report feature selection, surrogate fidelity, rule count, rule coverage/precision/fidelity and class-conditional symbolic behavior. Apply the same exclusion symmetrically in later matched C/D robustness where feasible.

## 4. Duplicate/conflict sensitivity

Primary policy retains duplicates and original conflicting labels.

Because row duplicates can inflate effective sample size and row-bootstrap persistence, include:

- exact-pattern equal-weight development-validation sensitivity (a deduplicated-pattern analysis that preserves within-pattern label contradictions rather than arbitrarily keeping one row);\n- group-aware bootstrap where identical feature patterns are resampled as whole groups.

Do not majority-relabel conflicts. Report support, covered count, precision, fidelity, stability and gate transitions under the sensitivity.

## 5. Surrogate constraints

Primary depth=4 and min_samples_leaf=1000. One-factor variants:

- max_depth in {3,4,5};
- min_samples_leaf in {500,1000,2000}.

Do not jointly grid-search against B held-out outcomes. Report teacher agreement, accepted-rule coverage, count and complexity.

## 6. Rule gates

Primary gates remain immutable. One-at-a-time robustness:

- min support {0.0005,0.001,0.002};
- min class precision {0.75,0.80,0.85};
- min neural fidelity {0.85,0.90,0.95};
- min bootstrap gate-persistence {0.80,0.90,0.95};
- max complexity {3,4,5}.

The primary minimum covered count stays 100. Duplicate-aware effective-sample analysis is preferred to casually changing it.

## 7. Fusion authority

Primary remains lambda=0.50. The audit shows all five frozen fused thresholds exceed 0.50, so a covered benign rule has effective veto authority over any neural score.

Mandatory sensitivities use neural weights 0.70, 0.90 and 1.00. Each uses the same development-only MCC threshold procedure and tie breaks. These test dependence on symbolic authority; they are not a retrospective search for a better B score.

## 8. Confidence and conflict semantics

R0 rules are disjoint leaves of one tree. Normally one rule fires, so normalized confidence mass collapses to a hard symbolic class and q is lifecycle/validation metadata rather than a soft weighting mechanism in B.

Zero B conflict is structurally constrained and is not evidence that conflict handling is solved. D must log overlap opportunity, resolution/demotion and abstention once independently generated/refined/merged rules can overlap.

## 9. Class-conditional explanation evidence

Overall coverage/fidelity is insufficient under class imbalance. Later systems must report, where defined:

- benign and attack symbolic coverage;
- symbolic ground-truth correctness among covered benign and attack rows;
- neural fidelity by true class when per-observation evidence permits;
- uncovered/conflict rates by true class.

A frozen-evidence-only semantic analysis derives the first two for B because R0 leaves are disjoint.

## 10. Stability terminology

Primary stability is **row-bootstrap gate-persistence stability**. It is not adversarial robustness, local perturbation stability, SHAP stability or cross-seed stability.

Robustness package includes group-aware duplicate-pattern bootstrap, SHAP feature-set stability, cross-seed feature Jaccard and longitudinal rule activation/coverage trajectories.

Valid-domain perturbation stability from the older design may be added only after specifying a defensible joint feature-domain constraint model.

## 11. Reproducibility / thread controls

Before C/D execution freeze:

- record torch intra/inter-op thread counts;
- record threadpoolctl.threadpool_info();
- freeze/document OMP/MKL/OpenBLAS settings;
- preserve deterministic-algorithm settings;
- match backend/thread policy within paired C/D blocks.

For B, perform a local reconstruction diagnostic where feasible. Before submission, archive the five exact System-A checkpoint bytes against their recorded SHA-256 values.

## 12. CICIDS2017 limits

Mandatory limitation/robustness treatment includes Destination Port shortcut risk, duplicates, CICFlowMeter/label defects, pseudo-chronological source-row ordering, one-week/single-testbed scope and retained conflicting patterns.

The primary scenario is a controlled proving ground, not deployment-valid evidence.

## 13. Scenario/dataset expansion

For broad Q1 claims, later evidence should include where defensible: gradual drift, attack-pattern/real-concept drift, unseen/evolving attack, and a second flow-oriented dataset with a different operating context. Do not artificially harmonize incompatible feature semantics.

## 14. Statistical robustness

Never treat 36 rules or 140 windows as independent replicates. Matched seed remains the primary unit within scenario. Window inference must model dependence; rule analyses are descriptive/hierarchical. Freeze confirmatory endpoints, paired interval/test and multiplicity before C/D held-out outcomes.

## 15. Status

- Primary B artifacts: immutable.
- New B sensitivities: secondary/post-hoc robustness.
- C/D robustness plan: prospective.
- No sensitivity result may erase an inconvenient primary result.


## 16. Reporting-window sensitivity

Primary reporting grid remains 5,000 rows with stride 5,000 and boundary-aligned partitions.

Prospective sensitivity for later longitudinal C/D reporting:

- 2,500-row non-overlapping windows;
- 5,000-row non-overlapping windows;
- 10,000-row non-overlapping windows.

The internal drift-detector/adaptation window is a separate control and must not be conflated with this reporting sensitivity. Apply identical reporting grids to matched systems and do not use window choice to manufacture independent replicates or select favorable effects.

## 17. D lifecycle-provenance requirement

R0's static schema is only the starting substrate. D must record immutable lifecycle events with trigger/event ID, operation type, parents/sources, evidence-window identity, candidate metrics, accept/reject reason, resulting version/rule IDs, conflict/abstention decision and computational cost.

The lifecycle event schema must be frozen before the first adaptive symbolic run.


## 18. SHAP aggregation-policy sensitivity

In addition to background and top-k sensitivity, compare the frozen class-aware max-normalized policy against:

- conventional global mean absolute SHAP ranking;
- equal-weight mean of separately normalized BENIGN and attack mean-absolute-SHAP vectors.

Use the same frozen training-only attribution sample and background when isolating aggregation-policy effects. Report top-k overlap, surrogate fidelity, accepted-rule identities and class-conditional rule behavior.

For already-observed B, this is post-hoc robustness only. For later scenarios/datasets, freeze the chosen primary extraction policy before their held-out outcomes.

## 19. Development-split sensitivity

Primary R0 uses the frozen split seed 20261007.

Post-hoc B robustness should repeat the **selection analysis only** with alternate deterministic split seeds {20261008, 20261009, 20261010, 20261011}; do not replace R0.v1.

Report:

- accepted-rule count;
- accepted-rule identity/antecedent overlap where comparable;
- support/precision/fidelity/stability distributions;
- selected lambda/threshold variation if fusion is recomputed on the complementary slice.

The purpose is to estimate dependence on one legitimate development split, not to choose the best split.

## 20. Rule-gate sample-size sensitivity for future D

The fixed minimum covered count of 100 is retained for R0.v1.

Before D, report the implied effective minimum support for the actual adaptation-validation window size. If the window makes the count gate materially stronger than the 0.001 support gate, one of the following must be frozen prospectively:

- a sufficiently large adaptation-validation window;
- a separately versioned count gate scaled to evidence size;
- an uncertainty-based minimum-evidence criterion.

The same rule must apply to D-drift and D-periodic and must not be chosen from their held-out outcomes.

## 21. Attack-family validity scope

Because B development attacks are GoldenEye-only, later robustness/generalization must separate:

- within-GoldenEye rule validity;
- attack-pattern changes to a known family;
- previously unseen attack-family behavior;
- second-dataset attack behavior.

Do not aggregate these into one generic “attack-rule precision” claim without per-scenario/per-class evidence.

## 22. Imputation-aware explanation diagnostic

Using the frozen preprocessing and source rows, quantify whether activated rule antecedents rely on originally non-finite values replaced by the training median.

Primary model/rule outputs remain unchanged. Report activation counts/rates with and without any imputed antecedent feature.

## 23. Computational benchmarking protocol

Before C/D cost comparison, freeze:

- warm-up passes;
- repeated timing count;
- timer scope for neural inference, symbolic inference, fusion, drift detection, neural update, symbolic maintenance;
- CPU/thread configuration;
- summary statistics.

The first B `symbolic_inference_seconds` value is historical descriptive timing of symbolic inference plus fusion and must not be overinterpreted.

## 24. C/D threshold-authority sensitivity

Primary C/D threshold policy must be frozen before adaptive held-out execution.

If the primary uses fixed System-B fused thresholds, a matched threshold-adaptation condition may be studied only as a separately labeled sensitivity.

If adaptive thresholding becomes primary, C and D must use the identical update rule, label timing, evidence window, and update schedule.


## 25. Retrospective-assumption closure order

The revised governing sources require the publication-strength System-B robustness package to proceed without modifying accepted R0.v2 or its corrected evaluation.

Execution order:

1. Stage-3A float64/float32 symbolic-consumer conformance audit using training/development only.
2. Repository-frozen scenario attribution and exact-pattern-dependence diagnostic.
3. Fixed A/B seen-versus-unseen held-out rescore.
4. Destination Port exclusion sensitivity.
5. Duplicate-aware package: deduplicated validation, group-aware duplicate-pattern bootstrap, and deduplicated-training sensitivity.
6. Alternate development-split sensitivity.
7. Fusion-authority sensitivity.
8. SHAP background/aggregation sensitivity.
9. One-factor rule-gate sensitivity.

Top-k and surrogate-constraint sweeps remain secondary unless an earlier mandatory result exposes instability requiring them for interpretation.

None of these analyses may replace R0.v2 because it performs better. A versioned correction is considered only if an independent conformance audit establishes a realized scientific-contract defect.


## Fusion-authority sensitivity implementation freeze — 7 October 2026

The high-priority lambda/fusion-authority sensitivity is implemented as a separate two-stage robustness analysis so it cannot accidentally regenerate or replace R0.v2.

Selection stage:

- exact accepted R0.v2 rules are reused;
- no SHAP or surrogate rebuild occurs;
- no training partition is loaded;
- the original development fusion slice is reconstructed and hash-checked;
- neural weights 0.70, 0.90 and 1.00 are fixed prospectively;
- for each weight/seed, only the fused operating threshold is selected using the original MCC/F1/FPR/0.5 tie policy;
- the resulting selection manifest must be committed before held-out rescoring.

Evaluation stage:

- loads only pre_drift/post_drift;
- uses the frozen sensitivity weight/threshold identities;
- reports the same corrected-v2 detection and class-conditional symbolic metrics;
- cannot replace lambda=0.50 or accepted R0.v2 regardless of outcome.


## 26. System-B mandatory robustness closure — 8 October 2026

The mandatory retrospective System-B robustness tranche is now complete and frozen.

Completed mandatory items:

- dtype conformance audit;
- scenario attribution / exact-pattern diagnostic;
- exact-pattern seen-versus-unseen A/B rescore;
- duplicate-aware validation and whole-pattern bootstrap;
- Destination Port exclusion;
- alternate development splits;
- fusion-authority sensitivity;
- SHAP background and aggregation sensitivity;
- one-factor rule-gate sensitivity;
- pattern-deduplicated alternate System-A teacher;
- matched alternate R0 construction;
- full held-out alternate A-to-R0-to-B duplicate-dependence evaluation.

The mandatory evidence does not establish a need to replace accepted R0.v2. It does establish that exact symbolic composition and class-conditional explanation behavior are assumption-dependent under several reasonable construction choices, while the main static longitudinal detection pattern is substantially more stable.

Secondary items from Sections 2 and 5 (top-k and surrogate-constraint sweeps) remain available for publication robustness but are not required before transition to C/D unless a later interpretive claim depends specifically on those dimensions.

System-B implementation is therefore considered closed for purposes of beginning prospective C/D design freeze. No further B-side tuning or held-out selection is permitted.
