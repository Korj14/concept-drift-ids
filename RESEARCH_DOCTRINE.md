# Research doctrine precedence

This repository is governed by two project-source documents, in the following order:

1. `MAIN - Concept_Drift_NIDS_Research_Gap_Doctrine.docx` — highest scientific authority.
2. `Reconciled_Pre-Stage_3_and_Stage_3_Implementation_Plan.docx` — authoritative operational protocol where it does not conflict with MAIN.

If an implementation convenience conflicts with MAIN, the implementation must change unless new scientific evidence justifies a documented doctrine revision. If MAIN is silent on an engineering detail, the Reconciled implementation plan governs. Frozen experimental artifacts are never silently rewritten after outcomes are known; a legitimate revision creates a new version, states the rationale, and preserves the earlier audit trail.

Improvements remain permitted and encouraged when they strengthen publication quality, validity, reproducibility, robustness, or interpretability without contaminating frozen evidence. Any improvement that changes an experimental treatment, data access, analysis choice, or previously frozen contract must be prospectively versioned and justified before it is used on untouched evidence.

## Governing research gap — exact wording

Prior work has separately demonstrated concept-drift-aware adaptation of predictive IDS models; online or continuous adaptation of fuzzy, belief-rule, and other interpretable intrusion detectors; neuro-symbolic intrusion detection; CTI/context-driven symbolic updates; and, very recently, drift-triggered re-mining of symbolic knowledge for SOC alert triage. However, insufficient controlled evidence exists at the flow-level NIDS layer on whether an explicit statistical concept-drift event can serve as the endogenous gate for a validated and versioned symbolic rule-evolution lifecycle, and whether that symbolic evolution contributes measurable value beyond an otherwise matched adaptive system while preserving longitudinal explanation quality.

## Binding scientific consequences

- Broad novelty claims such as “first adaptive neuro-symbolic IDS”, “first rule-evolving IDS”, or “first drift-aware IDS” are prohibited.
- Primary System C is adaptive neural + active but frozen initial symbolic rule base `R_0`.
- System D uses identical neural adaptation but permits symbolic evolution from `R_0` to `R_t`.
- The primary C-versus-D treatment difference is symbolic rule evolution. Drift event, adaptation evidence, neural starting state, neural update procedure/budget, preprocessing, fusion mechanism, label availability, evaluation windows, and compute backend must be matched wherever feasible.
- The same symbolic-evolution operator must support drift-triggered and periodic trigger policies so the usefulness of the drift trigger itself can be tested under a defensibly matched evidence/update budget.
- Initial imputation and scaling remain fitted on frozen training data only and fixed in the core experiment. Adaptive preprocessing is a separate treatment/sensitivity analysis.
- `sudden_benign_v1` is a controlled synthetic source-regime covariate-shift proving ground, not natural production concept drift and not the complete publication evidence.
- Symbolic staleness must be measured before symbolic recovery is claimed. Rules that remain valid must be reported as well as rules that degrade.
- The symbolic lifecycle must be validated, versioned, auditable, and richer than wholesale rule regeneration: candidate generation and acceptance remain separate; addition, refinement, merge, conflict handling, retention, demotion, retirement, reactivation, and symbolic abstention must be represented where applicable.
- Detection, adaptation, trigger-quality, explanation/rule-quality, lifecycle, and computational outcomes must all be evaluated longitudinally.
- A controlled shift need not worsen every metric. Fixed-threshold metrics may move differently from ranking/calibration/explanation metrics. High absolute accuracy does not establish symbolic value.
- Mixed or null results are scientifically valid. Untouched outcomes must not be used to retune earlier components or redefine treatments.

## Publication-grade experimental control

The intended quality bar is a strong Q2 and, where the evidence supports it, Q1 journal. That requires exclusion or explicit control of plausible alternative explanations.

Before untouched adaptive evaluation:

- maintain an experimental-control register for every high-leverage variable/parameter;
- freeze longitudinal window size/stride, transition handling, known-boundary scoring convention, persistence rule, adaptation-window construction, label availability/latency, drift-detector configuration, replay/buffer policy, neural update budget/stopping, fusion settings, rule-generation/validation thresholds, trigger policy, and computational budget;
- declare the inferential unit and avoid treating dependent windows as independent replicates;
- freeze the statistical-analysis plan: primary contrasts/endpoints, effect sizes, confidence intervals, paired/resampling tests, assumptions/fallbacks, multiplicity, failed-run/exclusion policy, stopping rules, and prespecified sensitivity analyses;
- retain every valid prespecified seed/run, including inconvenient or negative outcomes;
- keep matched systems on the same runtime/backend configuration where feasible and record unavoidable differences explicitly;
- enforce information timing: detector/updaters may use only information available at that point in the stream; synthetic boundaries are scoring-only;
- hash/version scenario, preprocessing, model/rule, and evaluation artifacts; retain seed/window-level evidence sufficient to regenerate every table and figure;
- generate figures/tables programmatically from immutable evidence artifacts rather than manually edited summaries;
- perform robustness/sensitivity checks for high-leverage choices without using them to search for favorable conclusions;
- support broad empirical claims with multiple defensible drift types and second-dataset replication where scientifically possible; otherwise narrow the claim.

## Publication-success interpretation

Publication success is an evidence chain, not a headline metric. The final package should establish:

1. trustworthy scenario/provenance and frozen initial representation;
2. credible System A/B reference conditions;
3. measurable symbolic staleness where it actually occurs;
4. a serious matched adaptive-neural control;
5. C-versus-D isolation of incremental symbolic-evolution value;
6. drift-driven versus periodic trigger comparison;
7. longitudinal detection and explanation/rule outcomes;
8. computational/update cost and trigger efficiency;
9. robustness/sensitivity analysis;
10. external validation commensurate with the breadth of the claim.

System D need not dominate C on every predictive metric. A defensible contribution can also arise from materially better explanation validity, conflict/abstention behavior, stability, or recovery-per-update/cost while predictive performance remains matched. Conversely, high predictive performance alone is insufficient.

## Live literature obligation

The novelty boundary must be rechecked adversarially before major later milestones, submission, and revision. If new work directly collapses the governing conjunction, the contribution must be reassessed rather than hidden.


## October 2026 retrospective-assumption doctrine synchronization

The current governing Word sources now include an explicit restart-versus-sensitivity rule.

For future repository work:

- restart/versioned rerun is reserved for realized defects that change the scientific object, such as future-information leakage, wrong frozen identity, treatment contamination, or a material implementation/protocol mismatch;
- ordinary dependence on a reasonable modeling choice is handled as additive sensitivity unless it invalidates causal interpretation;
- limited external validity is handled through prespecified scenario/dataset replication and claim narrowing, not by pretending one scenario is a population sample;
- `sudden_benign_v1` must be described as BENIGN-source-regime-dominant rather than attack-invariant because its pre/post GoldenEye observations come from different Wednesday segments;
- exact-pattern reuse, duplicate dependence, development-split dependence, fusion authority and explanation-extraction dependence are now explicit publication-strength robustness obligations;
- raw bounded-metric seed-level t-intervals remain authoritative even when their numerical endpoints leave the physical metric range; publication graphics may respect physical axes without rewriting evidence.

Current governing source hashes are recorded in `GOVERNING_SOURCES.md`. Historical A/B manifests retain the source hashes that governed them at their own freeze points.
