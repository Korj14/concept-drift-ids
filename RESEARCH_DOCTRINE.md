# Research doctrine precedence

This repository is governed by the project source document:

`MAIN - Concept_Drift_NIDS_Research_Gap_Doctrine.docx`

If that doctrine conflicts with either earlier guiding Word document or with an implementation convenience, the doctrine takes precedence unless a later documented scientific revision explicitly supersedes it. Where there is no conflict, the original research/design documents and frozen Stage-1/Stage-2 artifacts remain authoritative.

## Governing research gap — exact wording

Prior work has separately demonstrated concept-drift-aware adaptation of predictive IDS models; online or continuous adaptation of fuzzy, belief-rule, and other interpretable intrusion detectors; neuro-symbolic intrusion detection; CTI/context-driven symbolic updates; and, very recently, drift-triggered re-mining of symbolic knowledge for SOC alert triage. However, insufficient controlled evidence exists at the flow-level NIDS layer on whether an explicit statistical concept-drift event can serve as the endogenous gate for a validated and versioned symbolic rule-evolution lifecycle, and whether that symbolic evolution contributes measurable value beyond an otherwise matched adaptive system while preserving longitudinal explanation quality.

## Binding implementation consequences

- Primary System C is adaptive neural + frozen initial symbolic rule base `R_0`.
- System D uses identical neural adaptation but permits symbolic evolution from `R_0` to `R_t`.
- The core treatment changes symbolic evolution, not neural adaptation, preprocessing, data budget, or evaluation windows.
- The same rule-evolution operator must later support both drift-triggered and periodic trigger policies so the usefulness of the drift trigger itself can be tested.
- Initial imputation and scaling remain fitted on frozen training data only and fixed in the core experiment.
- `sudden_benign_v1` is a controlled source-regime covariate-shift proving ground, not a claim of natural production concept drift and not the complete publication evidence.
- Symbolic staleness must be demonstrated before symbolic recovery is claimed.
- The symbolic lifecycle must be validated, versioned, auditable, and richer than wholesale rule regeneration.
- Detection, adaptation, trigger-quality, explanation/rule-quality, and computational outcomes must all be evaluated.
- Broad novelty claims such as “first adaptive neuro-symbolic IDS” or “first rule-evolving IDS” are prohibited.
- The novelty boundary must be rechecked against live literature before major later milestones and submission.
