# System B Q1 Adversarial Audit

**Status:** ACTIVE — System B is not scientifically closed until the material protocol-conformance diagnostic below is resolved.  
**Audit date:** 7 October 2026  
**Scope:** frozen System-B protocol, R0.v1 construction, first untouched evaluation, additive supplement, and readiness of the symbolic substrate for later C/D causal work.

This audit is intentionally adversarial. A green CI run proves repository contracts; it does not by itself prove that every scientific assumption is strong enough for a top-quartile paper.

## 1. Current evidence chain verified

The following identities are preserved:

- accepted System-A milestone remains on `main`;
- accepted System-B manifest: `6e3589056d4c252c1a6c7cfd87b891fb8a24f1e30e86b17833b6035ea9ee86a8`;
- first untouched System-B evaluation manifest: `f44cad2ed9674bcb7118f05f174f845b5dfb135f95e2cb2b4a230f0f998c3e42`;
- additive System-B supplement manifest: `70d41b210ed54f2fa2269ec738ccd94100148d701bb5a2ae79d8d30839e9d190`;
- no original System-B evidence has been overwritten.

The first evaluation preserves all five seeds, exact partition totals, identical per-seed R0 rule identities across pre/post, and the prospectively frozen 14-window reporting grid.

## 2. Material open issue — surrogate leaf consequent semantics

**Severity: RED until diagnosed.**

The prospectively frozen protocol states that a candidate rule consequent is the class predicted by the fitted weighted CART leaf.

The build implementation instead computes:

`argmax(unweighted count of frozen neural decisions among training rows satisfying the path)`.

The tree itself was fitted with sample weights that equalize the total weight of the two neural-predicted classes. Therefore weighted leaf prediction and unweighted path majority are not guaranteed to agree.

This discrepancy was introduced into the written protocol before R0 generation, while the intended code correction was not actually implemented. The methodology ledger incorrectly stated that the implementation had been fixed. The historical statement must remain and be corrected by a later append-only entry.

No held-out evidence is needed to determine realized impact. The repository therefore provides:

`python run.py system-b audit-r0-protocol`

The command reconstructs each surrogate from **training only**, using the frozen selected features and corresponding System-A checkpoint, and compares every stored candidate consequent with the weighted CART leaf class required by the protocol. It does not load development, pre_drift, or post_drift.

Decision rule:

- zero mismatches: preserve R0.v1 and record that the implementation discrepancy had zero realized consequence for this freeze;
- any mismatch: preserve R0.v1 and all evaluation evidence, classify the issue as a real frozen-protocol implementation defect, and evaluate a transparent versioned correction before C/D. Do not choose a remedy based on whether corrected held-out metrics look better.

## 3. Symbolic validation is strong locally but not universally stable

From the frozen development candidate logs:

- full extracted path-partition neural fidelity ranges from approximately 0.946 to 0.991 across seeds;
- quality-accepted path coverage ranges from approximately 0.945 to 0.990;
- neural fidelity over accepted covered validation observations is approximately 0.9994–0.9999.

This supports the claim that selective validation materially improves fidelity of the retained symbolic subset.

However, validation-regime acceptance is not equivalent to universal rule validity. Fifteen of 36 accepted R0 rules do not pass the same conjunctive gate in the held-out pre-drift partition. Several failures are simply low activation/support, but at least one rule illustrates a more substantive distinction: a benign rule can remain highly faithful to the neural detector while having poor true-label class precision, meaning it faithfully explains a neural failure region.

Publication implication:

- never equate neural fidelity with correctness;
- report development validation, pre-drift generalization, and post-drift change as separate stages;
- do not describe R0 as guaranteed-valid throughout the initial stream merely because it passed development validation.

## 4. RQ1 outcome is selective persistence, not broad symbolic decay

The frozen gate-transition table contains:

- 20 pass -> pass rules;
- 8 fail -> pass rules;
- 7 fail -> fail rules;
- 1 pass -> fail rule.

Five rules are inactive pre-drift and become active post-drift; no rule is active pre-drift and completely inactive post-drift.

Therefore `sudden_benign_v1` does **not** provide evidence of widespread post-boundary symbolic collapse. This is scientifically admissible and consistent with the governing doctrine, which explicitly requires reporting rules that remain valid.

Publication implication:

- do not claim that the controlled benign source-regime shift broadly makes R0 stale;
- describe the evidence as selective changes in activation/support and isolated validity degradation;
- later real-concept/attack-pattern drift scenarios are essential if the paper is to make a stronger claim about symbolic recovery.

## 5. Inactive-rule metric semantics need a corrected derived view

The first evaluator encoded class precision and neural fidelity as 0 when a rule had zero activation. Those quantities are mathematically undefined when the denominator is zero.

The immutable first-run evidence and supplement are not rewritten.

Before manuscript figures/tables, create an additive semantic-analysis artifact that:

- records active/inactive status per rule/partition;
- represents precision/fidelity as null when covered_count = 0;
- computes precision/fidelity deltas only when both endpoints are defined;
- reports inactive -> active / active -> inactive transitions explicitly;
- preserves support/activation rate as zero where appropriate.

This prevents artificial +1.0 precision/fidelity “improvements” caused only by a rule beginning to fire.

## 6. Stability has a narrow, defensible meaning

The current rule stability measure is bootstrap persistence of the complete validation gate under stratified resampling.

Strengths:

- deterministic and auditable;
- avoids semantically impossible synthetic network-flow perturbations;
- directly measures sampling robustness of rule validity.

Limits:

- it is not adversarial robustness;
- it is not local perturbation consistency;
- it is not SHAP-background stability;
- it is not cross-seed explanation consistency.

The manuscript must call it **bootstrap gate-persistence stability** or equivalent rather than presenting it as universal explanation stability.

Recent 2026 IDS/XAI reliability work reinforces the need to separate fidelity, robustness, consistency and stability rather than treating them as interchangeable.

## 7. SHAP feature selection is reproducible but not uniquely stable

Top-12 feature sets are seed-specific by design.

Observed frozen cross-seed behavior:

- four features occur in all five seeds: Destination Port, Packet Length Variance, Bwd Packet Length Std, and Min Packet Length;
- mean pairwise Jaccard overlap of the five top-12 sets is approximately 0.427;
- pairwise intersections range from 5 to 9 of 12 features;
- the rank-12 versus rank-13 selection-score gap is small for every seed and extremely small for seed 3.

Implication:

The selected set is a reproducible extraction policy, not proof of one canonical globally stable set of important features.

Required robustness direction before submission:

- SHAP background-distribution sensitivity;
- top-k feature-count sensitivity;
- cross-seed feature-set stability reporting.

These analyses must be labeled robustness/exploratory and must not replace R0.v1 after seeing held-out outcomes.

## 8. SHAP background choice is scientifically consequential

DeepExplainer uses a balanced training background (128 benign / 128 attack) and a balanced attribution sample.

This is defensible because the purpose is minority-aware symbolic extraction, not estimation of natural-prevalence expected risk.

But the SHAP baseline depends on the background distribution. Therefore the paper must not imply that the resulting absolute SHAP magnitudes are prevalence-neutral.

A training-only robustness analysis should compare at least:

- the frozen balanced background;
- a natural-prevalence training background of the same size;
- optionally multiple deterministic background draws.

The primary R0 remains unchanged.

## 9. Fusion is a score fusion, not calibrated probabilistic fusion

System A uses weighted BCE and no probability calibration. Its sigmoid output is therefore an operational neural attack score, not a guaranteed calibrated probability.

The symbolic rule score is also not a calibrated posterior.

Accordingly, manuscript terminology should use **neural score**, **symbolic score**, and **fused score** unless calibration is explicitly measured.

The development-selected fused threshold makes the operating point legitimate without creating a calibration claim.

Recent 2026 IDS work increasingly reports calibration explicitly, so imprecise probability language would invite avoidable reviewer criticism.

## 10. Initial R0 confidence weights are operationally degenerate

The accepted R0 rules originate from disjoint leaves of one decision tree. After rejection of some leaves, the retained antecedents remain mutually exclusive.

Therefore at most one R0 rule should activate for a sample. Under the current normalized confidence-mass formula, the symbolic attack score becomes exactly 0 or 1 on resolved coverage, irrespective of the accepted rule's q value.

Thus q is meaningful metadata for validation/lifecycle provenance, but it does not modulate the initial R0 decision score.

Future evolved rule bases may contain overlapping retained/new rules, at which point confidence mass can become operational. Do not claim that q currently performs soft confidence weighting in System B.

## 11. The frozen fused operating point gives benign rules veto authority

With frozen global neural weight lambda = 0.50:

`fused = 0.5 * neural_score + 0.5 * symbolic_score`.

All five fused decision thresholds are greater than 0.50.

For any covered benign rule, symbolic_score = 0, so fused <= 0.50 for every possible neural score. Therefore a covered benign R0 rule necessarily produces a benign final classification at the frozen operating point.

This is an **effective hard veto within covered benign-rule regions**, despite implementation through convex score fusion.

Attack rules do not have symmetric unconditional authority; the neural-score requirement under an active attack rule varies by seed from approximately 0.385 to 0.949.

This does not invalidate the frozen baseline, but it is a major interpretive fact. The paper must not describe the mechanism as if a stale benign rule can never override the neural detector.

Before C/D, prespecify a fusion-authority sensitivity or intervention analysis. The primary B/C/D configuration remains frozen unless a separately versioned design is scientifically justified.

## 12. Lambda selection is valid but sits at a grid boundary

The global lambda = 0.50 was selected by the prospectively frozen development rule and has the highest mean development MCC among {0.50, 0.60, 0.70, 0.80, 0.90, 1.00}.

However, 0.50 is the lower boundary of the searched grid.

Therefore:

- the primary choice is legitimate;
- it must not be described as an unconstrained optimum;
- later robustness should test whether conclusions depend strongly on symbolic authority;
- the grid must not be expanded retrospectively merely to seek better System-B held-out results.

## 13. A versus B is descriptive, not a clean causal treatment effect

System B reuses the same frozen neural checkpoints but selects a fused threshold on the B fusion-development slice. System A thresholds were selected earlier on the full development partition.

Therefore A versus B changes symbolic reasoning **and** the decision-score/threshold construction.

The comparison remains useful descriptively, but it should not be the paper's primary causal claim about symbolic value.

The governing causal contrast remains C versus D, where all non-symbolic controls must be matched.

## 14. Development separation is improved but not fully nested

System-B candidate paths use training rows only, and rule validation and fusion tuning use disjoint 60/40 development slices.

However, the frozen System-A checkpoint and original neural threshold were themselves selected using the full development partition before System B existed.

This is legitimate upstream model selection, but it means the B validation slice is not statistically untouched with respect to the already-frozen teacher.

The paper should say that B prevents **direct reuse of B rule-validation observations for candidate fitting/fusion tuning**, not that the development slice was never involved anywhere upstream.

## 15. Rule-gate thresholds are policy controls, not universal constants

The frozen thresholds are:

- support >= 0.001;
- covered_count >= 100;
- class precision >= 0.80;
- neural fidelity >= 0.90;
- bootstrap stability >= 0.90;
- complexity <= 4.

They were frozen prospectively and are legitimate primary controls.

But they are not established universal NIDS constants. Q1 reporting should give the rationale and a prespecified threshold-sensitivity analysis rather than claiming optimality.

The absolute covered-count gate also means effective support requirements depend on partition size. Pre/post partitions have similar sizes, so their comparison is internally fair, but development versus pre/post gate-pass status should not be interpreted as a size-invariant hypothesis test.

## 16. Destination Port is a known external-validity risk

Destination Port appears in the selected top-12 set for every seed.

Prior CICIDS2017 studies have warned that destination port can encode benchmark-specific attack setup and produce overly optimistic discrimination. More generally, CICIDS2017 has documented flow-construction, duplication and labeling limitations.

The primary representation remains frozen and must not be silently altered.

For publication robustness, prespecify:

- a Destination-Port-excluded sensitivity;
- the already-permitted duplicate/unseen-pattern sensitivities;
- second-dataset replication;
- clear limitation language around CICIDS2017 artifacts.

## 17. Statistical interpretation must respect hierarchy

System-B RQ1 is primarily descriptive/longitudinal.

Do not treat 36 rules or 140 windows as independent replicates.

For rule-level staleness, preserve nesting by seed and use per-rule records descriptively unless a hierarchical method is prospectively justified.

The current t-intervals across five seeds are descriptive and can extend outside [0,1]; this is acceptable in stored evidence under the existing statistical plan, but bounded metrics need careful presentation.

Before C/D, the statistical plan still must freeze:

- confirmatory endpoints;
- primary paired interval/test;
- multiplicity handling;
- dependence-aware longitudinal method if inferential window modelling is used.

## 18. Reporting completeness still needs a publication-analysis layer

The frozen supplement provides mean, SD and t-intervals, but the statistical plan also calls for median, IQR, min/max and paired sign consistency where useful.

Add these as a derived analysis artifact from immutable evidence. Do not rewrite the frozen evaluation or supplement.

## 19. Reproducibility gap — ignored neural checkpoints

The repository contains hashes and metadata for the five accepted System-A checkpoints, but the checkpoint bytes are intentionally ignored and are only guaranteed on the local machine.

This is adequate for internal governance but insufficient for strong external reproducibility if a reviewer cannot obtain the exact frozen neural states.

Before submission, publish the frozen checkpoint bundle through an appropriate archival/release mechanism and bind it to the recorded SHA-256 values, or provide an equally defensible reproducibility route.

## 20. Scenario/external-validity conclusion

`sudden_benign_v1` remains a useful controlled proving ground, but it changes the benign source regime while keeping GoldenEye behavior essentially fixed.

The current B evidence accordingly shows substantial rule persistence and improvement rather than widespread decay.

A Q1-strength paper still requires, where defensible:

- attack-pattern / real-concept drift;
- gradual drift;
- unseen/evolving attack evidence;
- second-dataset replication.

These are not optional decorations if the manuscript makes broad claims about evolving threats.

## 21. Current Q1 gate

System B is **not rejected**, but it is **not yet scientifically closed**.

Immediate blocking item:

1. execute and freeze the training-only surrogate-leaf protocol diagnostic.

Then:

2. determine whether R0.v1 has zero or nonzero realized consequent mismatch;
3. add a corrected inactive-rule semantic analysis artifact;
4. freeze the robustness/sensitivity plan before C/D;
5. resolve the remaining C/D controls and statistical-plan TBDs before any adaptive held-out outcome.


## 22. Zero System-B conflict is structurally constrained

R0 rules are retained root-to-leaf paths from one decision tree. Distinct leaves are mutually exclusive. Therefore frozen B's zero conflict-abstention rate is largely structural, not empirical proof that future lifecycle conflict resolution is effective. D must supply conflict evidence once independently evolved rules can overlap.

## 23. Class imbalance hides symbolic correctness asymmetry

Because accepted R0 leaves are disjoint, frozen rule evidence supports exact class-conditional derivation. Across five seeds, mean benign symbolic coverage is about 0.983 pre and 0.980 post, while mean attack coverage is about 0.676 pre and 0.755 post. Covered-benign ground-truth correctness is approximately 1.000, whereas covered-attack correctness averages about 0.746 pre and 0.715 post.

Thus overall coverage (~0.97) and neural fidelity (~0.998) hide materially weaker attack-side symbolic correctness. Neural fidelity is not correctness, and overall coverage is not class-conditional coverage.

## 24. Duplicate rows can inflate bootstrap persistence

The primary duplicate-retention policy is unchanged. However, row-bootstrap gate persistence does not model dependence among identical feature patterns and can overstate effective-sample robustness. Publication robustness therefore requires deduplicated-validation and group-aware duplicate-pattern bootstrap sensitivities.

## 25. Determinism provenance is incomplete

B records exact environment versions, OS, CPU count, hashes and backend, but not full BLAS/OpenMP/PyTorch thread state. Before C/D, freeze threadpool/runtime controls. For B, exact reconstruction should be checked locally where feasible, and the frozen System-A checkpoint bytes must be archived before submission.

## 26. Pseudo-chronology remains bounded evidence

Source/scenario row order is a controlled pseudo-chronological proxy, not a natural production stream with fully trustworthy temporal provenance. Combined with known CICIDS2017 flow/label issues, sudden_benign_v1 supports a controlled source-regime shift claim, not broad temporal deployment validity.

## 27. Frozen robustness agenda

The sensitivity questions/ranges are now fixed in `SYSTEM_B_ROBUSTNESS_PLAN.md`. B sensitivities are post-hoc robustness because B outcomes are known; the same plan is prospective for C/D while adaptive held-out outcomes remain unseen.

## 28. Current audit verdict

**GREEN:** artifact integrity, seed retention, rule identity, window totals, immutable first evaluation and additive supplement.

**AMBER:** class-conditional validity, Destination Port, duplicate-aware stability, SHAP background/top-k, fusion authority, surrogate/gate sensitivity, thread-level reproducibility, checkpoint archival and external validation.

**RED closure blocker:** the training-only weighted-leaf consequent diagnostic must be executed and frozen before R0.v1 is inherited into C/D.


## 29. Duplicate dependence quantified on the actual B evidence slices

An audit-only reconstruction from the frozen raw CSVs (no model/rule changes) measured exact 77-feature-pattern duplication:

- full development: 10,018 rows belong to duplicated patterns (4.82%); maximum pattern multiplicity 344;
- rule-validation 60% slice: 4,835 rows (3.88%); maximum multiplicity 206;
- fusion 40% slice: 2,675 rows (3.22%); maximum multiplicity 138;
- exact pre-drift partition after Heartbleed exclusion: 4,061 rows (5.86%); maximum multiplicity 548;
- exact synthetic post-drift partition: 2,203 rows (3.18%); maximum multiplicity 136.

Thus duplicate dependence is not dominant in row count, but a few high-multiplicity patterns can materially influence rare-rule support and row-bootstrap persistence. This supports, rather than replaces, the planned group-aware sensitivity.

## 30. R0 schema is a lifecycle substrate, not a completed lifecycle

The static rule schema preserves persistent rule ID, lineage ID, rule-base version, conditions, consequent, validation metrics, lifecycle state and generic relations.

That is sufficient to carry R0 identities forward, but a Q1 claim about a **validated/versioned lifecycle** in D requires a richer immutable event record including at minimum:

- trigger/drift-event identity;
- operation type (addition/refinement/merge/demotion/retirement/reactivation);
- parent/source rule IDs;
- evidence window and information-timing identity;
- candidate quality evidence;
- acceptance/rejection decision and reason;
- resulting rule/version IDs;
- conflict/abstention decision where applicable;
- operation time/cost.

D must add this prospectively without rewriting R0.v1.


## 28. Fixed covered-count gate is sample-size dependent

The primary initial-rule gate requires both support >= 0.001 and covered_count >= 100.

On the 60% System-B development validation slice (~124.7k observations), support >= 0.001 already implies roughly 125 covered rows. The absolute count gate is therefore redundant during the original R0 validation.

On the ~69k pre/post partitions, covered_count >= 100 corresponds to an effective minimum support of about 0.00144 and is stricter than the nominal 0.001 support gate.

More importantly, on a future 5,000-row adaptation-validation window, covered_count >= 100 would imply 2% coverage. Blindly reusing the B gate in D would therefore create a substantially stricter symbolic acceptance operator solely because the evidence window is smaller.

Q1 implication:

- the B gate remains frozen and valid for R0.v1;
- development-to-pre/post gate-pass comparisons are descriptive, not size-invariant tests;
- before D, freeze either an adaptation-validation window large enough for the original gate semantics to remain comparable, or a separately versioned sample-size-aware count/support rule;
- C/D and D-drift/D-periodic must use the exact same rule-validation semantics within each matched comparison.

## 29. Initial attack-rule validation is GoldenEye-specific

The frozen System-B development partition contains BENIGN plus DoS GoldenEye only. Training contains multiple attack families, but true-label rule acceptance is performed on the development validation slice.

Therefore an accepted binary attack rule has demonstrated class precision against the GoldenEye-containing development regime, not against a representative mixture of all CICIDS2017 attacks.

This is not leakage and does not invalidate the primary controlled scenario. It does limit interpretation:

- R0.v1 is a scenario-specific validated symbolic substrate;
- its attack-rule validation must not be described as generic attack-family validity;
- attack-pattern and unseen-attack scenarios are required before making broader symbolic generalization claims;
- second-dataset replication becomes materially important rather than decorative.

## 30. SHAP feature-selection score is a bespoke policy

The frozen top-12 score is the elementwise maximum of three separately max-normalized mean-absolute-SHAP vectors: global, BENIGN, and attack.

This has a clear design rationale: prevent the majority class from dominating symbolic feature restriction. It is also deterministic and prospectively frozen.

However, it is not a canonical SHAP global-importance estimator. Separate normalization removes absolute scale differences among the three vectors, and the max operator gives a feature full influence if it is dominant in only one view.

Publication implication:

- describe this as a **class-aware feature-selection policy using SHAP**, not as the unique SHAP feature ranking;
- report the raw three attribution summaries already preserved in the artifact;
- include a post-hoc B / prospective C-D sensitivity using conventional global mean-absolute SHAP and a balanced class-average aggregation, while leaving R0.v1 unchanged.

The fixed background and attribution samples use the same RNG seed but are generated independently at different sample sizes. This creates deterministic dependence but only minimal expected row overlap; it is a reproducibility detail, not currently a material validity threat.

## 31. One development split does not establish split robustness

Candidate paths are training-only, and rule validation versus fusion tuning is cleanly separated by one deterministic 60/40 stratified development split.

Bootstrap gate persistence measures sampling variation **within that selected validation slice**. It does not measure whether rule acceptance is stable to a different legitimate validation partition.

For Q1 robustness, add repeated deterministic development-split sensitivity using prespecified alternate split seeds. The primary R0 remains unchanged. Report:

- accepted-rule identity overlap;
- rule-count variation;
- support/precision/fidelity variation;
- fusion-weight/threshold variation descriptively;
- whether qualitative conclusions depend on a single split realization.

Do not select an alternate split because it makes B look better.

## 32. Five-seed intervals quantify optimization variability, not environmental generalization

All five System-A/System-B seeds use the same scenario rows. Their variation reflects stochastic neural training / seed-specific symbolic extraction, not independent network environments.

Therefore t-intervals across five seeds are conditional on this scenario and dataset. They must not be described as confidence intervals for deployment-population performance.

Q1-strength generalization evidence must come from additional scenarios/datasets, not from treating more seeds on the same stream as environmental replication.

This scope also applies to later C-vs-D paired seed effects: paired seed is the correct within-scenario causal unit, but cross-environment claims require scenario/dataset replication.

## 33. Validation-selection optimism remains distinct from held-out generalization

Rules are accepted because they pass precision/fidelity/support/stability gates on the development validation slice. The reported validation metrics for accepted rules are therefore selection-conditional and expected to be optimistic relative to fresh data.

The held-out pre-drift partition is the first genuine post-selection generalization check for R0 validity. The observed pre-drift gate failures are therefore scientifically informative rather than evidence that the validation procedure was implemented incorrectly.

Manuscript reporting must distinguish:

1. candidate-generation/training evidence;
2. selection/validation evidence;
3. held-out pre-drift generalization;
4. post-drift change.

## 34. Computational timing field is not yet a strong cost benchmark

The first System-B evidence field named `symbolic_inference_seconds` times both symbolic inference **and score fusion** for an entire seed/partition pass.

It was measured on one Windows CPU execution without a prospectively frozen warm-up/repetition/thread-affinity protocol. It is therefore descriptive execution evidence, not a publication-grade microbenchmark of symbolic inference alone.

Before C/D cost claims:

- rename future instrumentation semantically (e.g. symbolic+fusion latency versus lifecycle-update latency);
- freeze warm-up/repetition policy;
- record threadpool state and CPU/runtime;
- report distributional timing summaries where feasible;
- keep matched timing conditions across C/D and D-trigger ablations.

The original B timing column remains immutable and must be described according to what it actually measured.

## 35. C/D fused decision-threshold policy is a causal control

System B has seed-specific fused thresholds selected on its frozen development fusion slice. Neural adaptation in C/D can change the neural-score distribution.

Before any adaptive held-out run, freeze whether C/D:

- retain the System-B fused thresholds throughout the stream; or
- use an explicitly defined matched threshold-adaptation mechanism.

Allowing only D to retune a threshold, or retuning C/D with different evidence, would introduce a second treatment. If adaptive thresholding is used, label timing and update budget must be identical across C/D and its cost/evidence access must be logged.

The simplest causal design is a fixed threshold unless strong development-only evidence justifies matched threshold adaptation.

## 36. Label timing is part of the symbolic treatment definition

The rule acceptance operator uses true-label class precision. Consequently, future D symbolic evolution cannot be described as immediately online unless labels are legitimately available at the adaptation time.

Before C/D, freeze:

- what label is available;
- its delay/latency distribution or deterministic delay;
- which observations in an adaptation window have matured labels;
- whether neural adaptation and symbolic validation consume the same matured labels;
- what happens when insufficient labels are available;
- whether a candidate can remain pending rather than being accepted prematurely.

A label-free drift trigger does not make the full adaptation pipeline label-free if rule validation still requires ground truth.

## 37. Adaptation generation and validation must preserve information time

The source design requires candidates to be validated on held-out adaptation evidence. In a streaming setting, a random split of one recent window can leak later-in-window information into a rule that is treated as available earlier.

Before D, freeze a temporally coherent adaptation protocol. Preferred structure:

- evidence-collection interval;
- candidate-generation subwindow;
- later validation subwindow (or another explicitly time-respecting cross-fit);
- publication time of the new rule-base version only after required labels/evidence are available.

This is especially important when duplicate/near-duplicate flows cluster locally.

## 38. Imputation is invisible in current rule explanations

Rules operate on the accepted median-imputed, standardized representation. A rule condition can therefore be satisfied using an imputed feature value, but the rule trace currently does not indicate that an antecedent feature was originally missing.

The overall missing/non-finite fraction is small, so this is not currently a reason to replace R0. For explanation-quality claims, however, add an imputation-activation diagnostic where feasible:

- fraction of rule activations involving at least one antecedent feature that was imputed;
- per-rule count/rate;
- sensitivity excluding those rows from explanation-quality summaries.

This should be derived without changing the primary preprocessing.

## 39. Rule-confidence semantics depend on future label availability

For R0, q = min(class precision, neural fidelity) is useful lifecycle metadata but operationally degenerate because accepted tree leaves are mutually exclusive.

In D, independently evolved/retained rules may overlap, making q operational in symbolic aggregation. Updating q then requires a clear evidence policy, especially because class precision needs labels while neural fidelity does not.

Before D, freeze whether q is:

- recomputed only from matured labeled validation evidence;
- carried forward when labels are unavailable;
- decayed with evidence age;
- or represented with separate correctness/fidelity components rather than collapsed immediately.

Do not let D gain an implicit advantage by updating confidence with future labels unavailable to C at the same stream time.

## 40. Current System-B scientific status after expanded audit

System B remains a valuable and largely well-controlled static baseline, but **C/D inheritance is blocked** until the training-only weighted-leaf diagnostic is executed and its result is frozen.

Even if the diagnostic reports zero realized mismatches, the following C/D controls remain mandatory before adaptive held-out execution:

- label timing;
- drift-monitor signal and persistence;
- adaptation-window and time-respecting validation construction;
- rule-gate sample-size semantics;
- fused-threshold policy;
- thread/runtime controls;
- confirmatory endpoints/interval/test/multiplicity;
- lifecycle-event schema.

No B robustness result may be used to retroactively replace R0.v1.


## 41. Corrected R0.v2 held-out audit conclusion

The protocol-conformant R0.v2 evaluation is now frozen. It does not overturn the earlier Q1 audit; it sharpens it.

Key corrected findings:

- detection improves post-shift on MCC/F1/recall across all five seeds while AP decreases on average;
- overall resolved symbolic coverage changes little;
- attack-side resolved coverage increases on average (~0.613 to ~0.713);
- attack-side true-label correctness among covered rows decreases on average (~0.803 to ~0.750);
- attack-side neural fidelity increases on average (~0.944 to ~0.964);
- BENIGN symbolic correctness remains effectively 1.0;
- only 1/32 accepted rules changes pass→fail under the frozen gates;
- the failure is a low-support BENIGN rule and is stability-driven;
- no activated rule antecedent depends on an imputed value in either held-out partition;
- static tree-leaf rules produce zero conflict-abstention by construction.

Q1 interpretation:

System B provides evidence of **selective symbolic redistribution/staleness**, not global symbolic degradation. The controlled benign covariate shift changes support/activation and class-conditional explanation quality while thresholded detection can improve. The separation between neural fidelity and true-label symbolic correctness is empirically necessary.

This is a stronger and more defensible baseline for the later C-vs-D question than a manufactured claim that all rules become stale after drift.


## 42. System-B implementation closure status — 8 October 2026

This section supersedes the operational blocking language in earlier audit sections without rewriting the historical record.

The protocol-conformance defect identified in R0.v1 was corrected by accepted R0.v2, and the subsequent mandatory retrospective robustness tranche has now been executed and frozen. C/D inheritance is therefore **no longer blocked by any unresolved System-B implementation defect**.

Completed closure evidence includes:

- Stage-3A float64/float32 symbolic-consumer conformance: numerically inert, no R0 version change required;
- repository-frozen scenario attribution / exact-pattern audit;
- A/B exact-training-pattern seen-versus-unseen held-out rescore;
- duplicate-aware validation and whole-pattern bootstrap sensitivity;
- Destination Port exclusion;
- alternate development splits;
- SHAP background and aggregation sensitivities;
- one-factor rule-gate sensitivities;
- fusion-authority sensitivities at neural weights 0.70, 0.90 and 1.00;
- pattern-deduplicated alternate System-A teacher;
- matched alternate R0 rebuilt from that teacher after the teacher freeze;
- full alternate A-to-R0-to-B held-out duplicate-dependence evaluation after both upstream artifacts were frozen.

The full pattern-deduplicated chain confirms that training multiplicity materially affects the learned teacher and symbolic state, especially class-conditional symbolic coverage/correctness, but it does not reveal a scientific-contract defect requiring replacement of accepted System A or R0.v2. The alternate B state uses 8/8/8/9/8 active rules across seeds versus 7/6/7/6/6 in accepted R0.v2, while its held-out detection remains viable. This is therefore reported as substantive assumption dependence, not retroactive model selection.

The mandatory System-B robustness package is considered **implementation-complete for transition into C/D design freeze**. Secondary top-k and surrogate-constraint sweeps remain optional publication robustness unless later interpretation specifically requires them; they are not prerequisites for starting C/D.

Before the first adaptive C/D held-out execution, the remaining open work is prospective C/D control design rather than System-B repair: drift signal/configuration/persistence, label timing, time-respecting adaptation evidence, neural adaptation procedure/budget/replay/stopping, D rule-gate sample-size semantics, threshold policy, rule-confidence update, D-periodic cadence/budget, backend/thread controls, confirmatory endpoint/multiplicity freeze, and lifecycle-event schema.
