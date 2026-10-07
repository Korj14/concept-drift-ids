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

- deduplicated development-validation sensitivity by exact frozen feature pattern;
- group-aware bootstrap where identical feature patterns are resampled as groups.

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
