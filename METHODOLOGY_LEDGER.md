# Methodology and Execution Ledger

This file is a running research record. It preserves implementation decisions, execution facts, rationale, and evidence that may later support the methodology, system-design, reproducibility, limitations, and threats-to-validity sections.

It is intentionally more detailed than the eventual manuscript methodology. Later writing should select from this record rather than reconstructing decisions from memory.

## Governing principle

Record:

- what was decided before evaluation;
- what data were available at each decision point;
- what code/artifact version implemented the decision;
- what was actually executed;
- whether an execution result caused any protocol change;
- what evidence is suitable for the final methodology versus internal reproducibility context.

Do not rewrite earlier entries after seeing later results. Add a new dated entry if a decision changes.

---

## 6 October 2026 — Pre-Stage 3 closure

### Scientific authority

The governing project doctrine is:

`MAIN - Concept_Drift_NIDS_Research_Gap_Doctrine.docx`

The repository copy `RESEARCH_DOCTRINE.md` is a convenience pointer only.

### Frozen causal design consequences

- System A: static neural model, no symbolic layer.
- System B: static neural model + active initial symbolic rule base `R_0`.
- System C: adaptive neural model + active initial symbolic rule base `R_0` held frozen.
- System D: identical neural adaptation + symbolic rule base allowed to evolve `R_t`.
- C versus D is the primary causal comparison isolating symbolic adaptation.
- The same symbolic evolution operator must later support drift-triggered and periodic trigger policies.

### Frozen scenario interpretation

`cicids2017_sudden_benign_v1` is a controlled synthetic benign source-regime covariate shift under pseudo-chronological source/order reconstruction.

It is not claimed to be natural production concept drift and is not sufficient alone for the full publication claim.

---

## 6 October 2026 — Stage 3A preprocessing acceptance

### Scenario reconstruction

Frozen partitions:

- training: 1,322,179 rows
- development: 207,810 rows
- pre-drift: 69,260 rows
- post-drift: 69,270 rows

Model representation:

- exact ordered 77-feature schema
- `BENIGN -> 0`; every retained non-BENIGN label -> `1`
- original multiclass label retained as metadata
- provenance metadata excluded from model features
- post-drift Thursday BENIGN source identity kept distinct from Wednesday template-slot identity

### Frozen initial preprocessing

Imputation:

`SimpleImputer(strategy="median")`

Scaling:

`StandardScaler(with_mean=True, with_std=True)`

Fit scope:

- fitted once on the frozen training partition only
- development, pre-drift, and post-drift do not contribute fitted statistics
- no preprocessing `fit`/`partial_fit` after the initial training fit in the primary experiment

Dtype policy:

- shared fitted preprocessing state: float64
- PyTorch model boundary: float32

### Leakage controls

Counterfactual tests demonstrated that changing development/pre/post feature values while holding training fixed does not change:

- fitted medians
- scaler mean/variance/scale
- transformed training data

### Accepted preprocessing artifact

`data/manifests/sudden_benign_v1_preprocessing_v1.json`

Accepted core state SHA-256:

`4527f77220f2cf6063108a7d71d80aaa0e82099ad282ff25408a2d9ce3488b1e`

### Local execution evidence

Runtime:

- Python 3.11.9
- exact dependency lock

Regression results:

- Stage-2 + preprocessing contract block: 20 passed
- real-data scenario loader: 6 passed
- Stage-3A full transform: all four partitions finite, 77 features, frozen row counts preserved

No Stage-3A acceptance result caused a change to the frozen scientific preprocessing protocol.

---

## 6 October 2026 — Stage 3B System A protocol freeze

### Purpose

System A is the static neural-only baseline. It establishes the behavior of a compact fixed neural detector before any symbolic reasoning, drift detection, or adaptation is introduced.

Neural architectural novelty is explicitly not a contribution target.

### Model

Architecture:

`77 -> 128 -> 64 -> 1`

Hidden activation:

- ReLU

Dropout:

- 0.10 after each hidden layer

Initialization:

- explicit Kaiming-uniform initialization for linear weights
- zero biases

Output:

- one binary logit

Calibration:

- no separate probability calibration in primary System A

### Training

Loss:

- `BCEWithLogitsLoss`

Class imbalance treatment:

- positive-class weight derived only from training labels:
  `training_benign / training_attack`

Optimizer:

- Adam

Learning rate:

- 0.001

Weight decay:

- 0.00001

Batch size:

- 4096

Maximum epochs:

- 20

DataLoader workers:

- 0

Fixed stochastic seeds:

- 0, 1, 2, 3, 4

### Early stopping

Selection partition:

- development only

Selection metric:

- development average precision

Patience:

- 3 epochs

Minimum required improvement:

- 0.0001

For each seed, the best development checkpoint is retained.

### Decision threshold

Threshold is selected independently for each seed using development predictions only.

Primary objective:

- maximize MCC

Deterministic tie-break order:

1. higher F1
2. lower FPR
3. threshold closest to 0.5

### Evaluation firewall

Pre-drift and post-drift partitions are not loaded by the System-A model-development path.

The evaluation path is gated on a complete five-seed `system_a_v1.json` manifest with hash-verified checkpoints.

No architecture, optimizer, imbalance treatment, early-stopping rule, or threshold-selection rule may be altered after viewing pre/post performance without declaring a new protocol version.

---

## 6 October 2026 — System A repository/unit acceptance

Repository-only System-A contract tests:

- 6 passed under Python 3.11.9

The tests verify:

- accepted preprocessing state can be consumed without refitting
- preprocessing formula reproduces the frozen median/standardization transformation
- float32 model-boundary output is finite
- MLP shape/output contract
- MCC-based threshold-selection behavior
- required detection metrics
- frozen protocol constants

No model-development parameter was changed in response to these test results.

---

## 6 October 2026 — System A seed-0 smoke run

Command:

`python run.py system-a train --seeds 0 --device auto`

Resolved device:

- CPU

Accepted preprocessing state:

`4527f77220f2cf6063108a7d71d80aaa0e82099ad282ff25408a2d9ce3488b1e`

Seed:

- 0

Observed development-only training result:

- best epoch: 12
- development average precision: 0.812427
- selected development threshold: 0.939024
- development MCC at selected threshold: 0.744096

Remaining frozen seeds:

- 1
- 2
- 3
- 4

Execution consistency clarification made before seeds 1–4:

- seed 0 resolved to CPU;
- seeds 1–4 will also be executed on CPU;
- this keeps the compute backend constant across the five matched System-A runs and is not a response to the observed development score.

### Interpretation rule

This was a smoke/execution-validity run on the already-frozen protocol.

The observed development metrics are recorded for reproducibility but are not used to redesign the architecture or training protocol.

No pre-drift or post-drift evaluation was performed.

---

## Methodology-report candidates accumulated so far

Likely final-methodology material:

- authority and causal system definitions
- pseudo-chronological controlled scenario construction
- exact partition roles
- training-only preprocessing and leakage controls
- fixed preprocessing artifact/provenance
- compact MLP rationale
- class weighting
- fixed seed protocol
- development-only early stopping
- development-only threshold selection
- evaluation firewall
- matched-checkpoint strategy for later systems
- reproducibility environment

Likely internal/contextual material rather than main-methodology prose:

- exact local command sequence
- individual smoke-run development values
- repository branch names
- debugging/portability fixes
- low-level path/bootstrap mechanics

These distinctions may change when the manuscript/design report is assembled; preserve the raw record regardless.


---

## 6 October 2026 — System A five-seed training completion

All five frozen seeds were trained on CPU under the previously frozen System-A protocol.

Accepted preprocessing state:

`4527f77220f2cf6063108a7d71d80aaa0e82099ad282ff25408a2d9ce3488b1e`

Per-seed development results:

| Seed | Best epoch | Dev AP | Dev-selected threshold | Dev MCC |
| ---: | ---: | ---: | ---: | ---: |
| 0 | 12 | 0.812427 | 0.939024 | 0.744096 |
| 1 | 13 | 0.739113 | 0.933374 | 0.759472 |
| 2 | 4 | 0.611827 | 0.912125 | 0.708114 |
| 3 | 17 | 0.728322 | 0.978962 | 0.771594 |
| 4 | 15 | 0.694060 | 0.954619 | 0.737331 |

Descriptive five-seed development summaries:

- mean AP: 0.717150; sample SD: 0.072991; 95% t-interval: [0.626519, 0.807780]
- mean MCC: 0.744121; sample SD: 0.024151; 95% t-interval: [0.714134, 0.774108]
- mean selected threshold: 0.943621; sample SD: 0.024940
- mean best epoch: 12.2; sample SD: 4.97

The variation across seeds, including the lower seed-2 development ranking metrics, is retained as part of stochastic model behavior. No seed was discarded and no protocol parameter was changed in response.

The five-seed frozen manifest was generated and committed:

`data/manifests/system_a_v1.json`

Frozen manifest SHA-256 recorded by the implementation:

`42004b5ed100b690023b9998bdc959fac41ab947b996fb7c58e44cee5e8dc6de`

All five manifest records use:

- device: CPU
- PyTorch: 2.14.1+cpu
- identical preprocessing state
- identical model/training protocol
- independently selected development-only thresholds

No pre-drift or post-drift performance had been inspected when this manifest was frozen.

---

## 6 October 2026 — Visualization-ready output policy frozen before first pre/post evaluation

Future experiment outputs should be machine-readable and directly combinable across systems/scenarios.

System-A evaluation therefore emits both a complete JSON record and tidy CSV tables.

Long-form per-seed metric schema:

- system ID
- scenario ID/version
- partition
- seed
- frozen decision threshold
- metric
- value

Aggregate metric schema:

- system ID
- scenario ID/version
- partition
- metric
- number of seeds
- mean
- sample standard deviation
- 95% confidence-interval bounds

Paired drift-delta schema:

- system ID
- scenario ID/version
- source/target partition
- seed
- metric
- post-minus-pre delta

An aggregate paired-delta table is also produced.

Epoch-level training history is exported separately with:

- system/scenario identity
- seed
- epoch
- training loss
- development average precision
- best-epoch flag

These schemas are designed so later Systems B/C/D can emit equivalent rows and be concatenated directly for line plots, grouped bars, seed-distribution plots, confidence-interval plots, pre/post comparisons, and cross-system drift-delta figures.

Primary detection metrics remain:

- precision
- recall
- F1
- FPR
- MCC
- ROC-AUC
- average precision

Before first pre/post evaluation, two secondary descriptive metrics were added prospectively:

- accuracy
- balanced accuracy

They are explicitly secondary because ordinary accuracy can be misleading under severe class imbalance. Their addition does not change model fitting, early stopping, checkpoint selection, or decision-threshold selection.


### Frozen evaluation-output retention policy

Before first pre/post evaluation, compact evaluation summaries were designated as versioned research artifacts under:

`results/frozen/system_a_v1/`

They are intentionally trackable in Git because they are small, directly support later plots/tables, and preserve the exact reported evidence.

Large model checkpoints remain local/ignored.

The evaluation creates `evaluation_manifest.json`, which records:

- system/scenario identity;
- frozen System-A manifest hash;
- frozen preprocessing state hash;
- the relative path and SHA-256 of every JSON/CSV evaluation product;
- its own manifest hash.

This separates durable research evidence from large executable checkpoint artifacts.


---

## 7 October 2026 — System A untouched pre/post evaluation closure

The frozen five-seed System-A manifest was committed before the pre/post evaluation was executed. The evaluation therefore used already-fixed model checkpoints, development-selected thresholds, preprocessing state, seeds, and CPU execution backend.

Pre-evaluation unit contract:

- `tests/test_system_a_unit.py`: 8 passed under Python 3.11.9.

Frozen evaluation identity:

- directory: `results/frozen/system_a_v1/`
- evaluation manifest: `evaluation_manifest.json`
- evaluation manifest SHA-256: `e721b641b5898976c76c0449dedf7152cb302be4447604525afb7ddf1c94c5b3`
- System-A manifest SHA-256: `42004b5ed100b690023b9998bdc959fac41ab947b996fb7c58e44cee5e8dc6de`
- preprocessing core state SHA-256: `4527f77220f2cf6063108a7d71d80aaa0e82099ad282ff25408a2d9ce3488b1e`
- first frozen evaluation commit: `7ace6ecbdc69b03fdfe40415ebd794c9c8a1d741`

Five-seed aggregate results:

| Metric | Pre-drift mean | Post-drift mean | Mean paired post-minus-pre |
| --- | ---: | ---: | ---: |
| Accuracy | 0.975339 | 0.978732 | +0.003393 |
| Balanced accuracy | 0.768372 | 0.797892 | +0.029520 |
| Precision | 0.975942 | 0.985887 | +0.009946 |
| Recall | 0.537476 | 0.596250 | +0.058774 |
| F1 | 0.693017 | 0.743022 | +0.050005 |
| FPR | 0.000731 | 0.000466 | -0.000265 |
| MCC | 0.714462 | 0.757969 | +0.043506 |
| ROC-AUC | 0.977831 | 0.973914 | -0.003917 |
| Average precision | 0.895855 | 0.845229 | -0.050626 |

Paired 95% t-intervals across the five frozen seeds include:

- balanced-accuracy delta: [0.026131, 0.032909]
- recall delta: [0.051963, 0.065585]
- F1 delta: [0.043504, 0.056506]
- MCC delta: [0.037532, 0.049481]
- FPR delta: [-0.000546, 0.000016]
- ROC-AUC delta: [-0.043502, 0.035669]
- average-precision delta: [-0.125459, 0.024208]

Seed-level sign behavior:

- accuracy, balanced accuracy, recall, F1, and MCC improved post-drift for all five seeds;
- FPR decreased for four of five seeds and increased slightly for seed 3;
- precision improved for four of five seeds and decreased for seed 3;
- ROC-AUC decreased for four of five seeds but increased for seed 2;
- average precision decreased for four of five seeds but increased for seed 2.

### Scientific interpretation

The controlled source-regime shift did not create a universal degradation of the frozen neural baseline. Thresholded classification behavior improved consistently for several metrics, while ranking behavior was mixed and average precision decreased for four of five seeds.

This is retained as evidence rather than treated as a reason to retune System A. It reinforces the governing rule that drift is not defined by the direction of a single predictive metric and that later adaptation success cannot be reduced to recovery of F1 alone.

No preprocessing, architecture, class weighting, early stopping, threshold selection, seed, checkpoint, or scenario choice was changed after these untouched results were observed.

### System-A closure

System A is accepted as the frozen static-neural reference for subsequent work.

Its role is not to prove the proposed neuro-symbolic contribution. Its accepted outputs provide:

- fixed neural starting states/checkpoint identities;
- a non-symbolic detection reference;
- seed-level variability;
- frozen thresholds;
- longitudinal-rescoring inputs once the common window policy is frozen;
- plot-ready evidence for later matched A/B/C/D comparisons.

---

## 7 October 2026 — publication-grade governance synchronization

The current project-source authorities are:

1. `MAIN - Concept_Drift_NIDS_Research_Gap_Doctrine.docx` — highest scientific authority.
2. `Reconciled_Pre-Stage_3_and_Stage_3_Implementation_Plan.docx` — authoritative operational protocol where non-conflicting.

Repository governance was synchronized to those sources before merging the completed System-A milestone.

Two prospective control artifacts were introduced:

- `EXPERIMENT_CONTROL_REGISTER.md`
- `STATISTICAL_ANALYSIS_PLAN.md`

The control register separates already-frozen decisions from future variables that must be resolved before outcome-sensitive adaptive evaluation. The statistical-analysis plan explicitly treats windows as dependent longitudinal observations rather than automatic independent replicates and gates untouched C/D evaluation on a completed prespecified confirmatory analysis.

These additions strengthen future evidence control and do not alter any frozen Stage-3A or System-A experimental artifact.


### System-A integrity verifier and count supplement

A read-only `python run.py system-a verify` path was added after System-A closure. It validates frozen manifests/checkpoint hashes and compact evaluation-file hashes without loading pre/post partitions. This adds an integrity check only; it does not alter model state or results.

The already-frozen System-A evaluation did not contain TP/TN/FP/FN fields. Rather than rewrite it, a separately versioned supplement was added:

`results/frozen/system_a_v1_supplement_v1/`

Supplement manifest SHA-256:

`1b41edecf3f69f2a2ae9804c3979b155d6436b4b7cd6e470723a3d75cd849fdc`

The supplement reconstructs exact integer confusion counts from:

- the frozen per-seed recall and FPR values;
- the frozen pre/post benign and attack counts.

The reconstruction is exact: `TP = recall × attack_count` and `FP = FPR × benign_count` yield integers for every frozen seed/partition, after which `FN` and `TN` follow from the frozen class totals.

No checkpoint was rerun; no probability, threshold, metric, or original evaluation artifact was changed.


### Governing source-version pin

The exact project-source documents governing this repository milestone were materialized and SHA-256 hashed before merge:

- MAIN doctrine: `f0700fc28e5c49ee50a6fab73db870725006ba52541a0d9cf4b285ccbe143a8f`
- Reconciled implementation plan: `83d1e101a525e840a1235743ac5fc050ca560f228df047bee17a84e80cbf3082`

These identities are recorded in `GOVERNING_SOURCES.md`. Future source updates require a new source-register entry and an explicit repository alignment review before the next untouched scientific stage.


### Supplement line-ending integrity correction

Before milestone merge, the System-A count supplement was independently hash-checked against the actual bytes committed to GitHub. The initial supplement manifest had recorded the SHA-256 of a CRLF local representation while the repository stored LF bytes. The numerical CSV content was unchanged.

The manifest was corrected prospectively before merge to reference the actual committed LF-byte SHA-256:

`e1cac14c7209b71737643ee1ae603460c12be3f86df6f52cbc9d781e344d944f`

Corrected supplement-manifest SHA-256:

`1b41edecf3f69f2a2ae9804c3979b155d6436b4b7cd6e470723a3d75cd849fdc`

The verifier and unit suite now check the committed supplement manifest/file relationship so future line-ending or byte-level drift is detected automatically. No frozen System-A prediction, metric, threshold, checkpoint, or original evaluation artifact changed.


### Cross-platform frozen-evidence reconstruction policy

A Linux CI check of the original System-A evaluation manifest exposed a platform representation issue: the frozen CSV artifacts had been generated on Windows using the CSV module's CRLF line endings, while Git's canonical text storage normalized them to LF. The first detected mismatch was `training_history.csv`; `static_evaluation.json`, written explicitly with LF, verified before that point.

The original System-A evaluation manifest remains unchanged because it is the execution-time record of the files generated on Windows. Repository reconstruction is made deterministic through `.gitattributes`:

- original `results/frozen/system_a_v1/*.csv`: checked out as CRLF, matching generation-time bytes;
- original JSON: checked out as LF;
- separately versioned count supplement: checked out as LF.

Future CSV evidence writers now use explicit LF line termination so later systems have platform-stable text artifacts.

This is a byte-representation/reproducibility correction only. No numerical result, threshold, model, scenario, or original frozen manifest was modified.

System-A evaluation execution is also write-protected after closure: if the frozen evaluation manifest already exists, the evaluation command refuses to overwrite it and directs the operator to the read-only verifier.


---

## 7 October 2026 — System-B launch verification and prospective protocol freeze

Stage 4 began from the accepted System-A milestone on the dedicated `stage4-system-b` branch.

### Continuity verification

Remote GitHub verification showed:

- `main`: `5d5cb67dda1abcda720eac785c29fa259f6bf5b8`;
- `stage4-system-b`: `5d5cb67dda1abcda720eac785c29fa259f6bf5b8`;
- branch comparison: identical, ahead 0 / behind 0.

The uploaded governing source bytes were re-hashed before Stage-4 design work:

- MAIN: `f0700fc28e5c49ee50a6fab73db870725006ba52541a0d9cf4b285ccbe143a8f`, 55,780 bytes;
- Reconciled plan: `83d1e101a525e840a1235743ac5fc050ca560f228df047bee17a84e80cbf3082`, 50,623 bytes.

These exactly match `GOVERNING_SOURCES.md`; no source migration or prior-evidence impact assessment was required.

Remote verification cannot establish local working-tree cleanliness or the presence of ignored System-A checkpoint bytes. Those remain local-only execution prerequisites and are not inferred from GitHub state.

### Permitted evidence and outcome firewall

The System-B protocol was frozen using:

- MAIN and the Reconciled operational plan;
- the accepted repository contracts and System-A development identities;
- current 2025–2026 literature;
- design/engineering constraints.

No System-B pre/post outcome existed or was inspected.

The research team historically knows the frozen System-A pre/post results. Those held-out results were explicitly excluded from all System-B choices. No SHAP setting, tree constraint, validation threshold, fusion policy, rule threshold, or longitudinal reporting window was selected from System-A pre/post behavior.

### Literature refresh

A targeted live search immediately before protocol freeze did not identify a new peer-reviewed flow-level NIDS paper implementing the complete governing conjunction. Recent 2026 explanation-reliability work did materially strengthen the requirement to define and audit stability rather than use the term generically. The details and references are appended to `LITERATURE_WATCH.md`.

### Prospective System-B decisions

`SYSTEM_B_PROTOCOL.md` was created before implementation and before untouched B evaluation. Major decisions include:

- seed-specific `R_0^(s)` mapped to the corresponding frozen System-A checkpoint and carried forward within the same stochastic block;
- training-only SHAP and surrogate candidate generation;
- deterministic non-overlapping 60/40 development split for rule validation versus fusion/threshold tuning;
- DeepExplainer on the raw attack logit with fixed class-balanced training background/sample identities;
- 12-feature class-aware SHAP restriction;
- depth-4, minimum-leaf-1000 weighted surrogate mimicking the frozen neural decision;
- conjunctive support, class-precision, neural-fidelity, bootstrap-stability, and complexity gates;
- candidate confidence defined conservatively as min(class precision, neural fidelity);
- explicit empirical redundancy/conflict semantics and neural fallback for runtime cross-class symbolic conflicts;
- one global development-selected fusion weight across seeds, with seed-specific fused thresholds;
- no probability calibration;
- a 5,000-row non-overlapping common longitudinal reporting grid, boundary-aligned for evaluator scoring only.

Exact accepted rule-base bytes, the development-selected global fusion weight, and the five fused thresholds remain intentionally unfrozen until the local build uses the ignored System-A checkpoints and permitted training/development data. They must be frozen and committed before any System-B pre/post evaluation.

This entry is prospective. Untouched System-B outcomes must not cause the protocol above to be rewritten.


### System-B pre-execution implementation clarifications

Before any System-B training/development build was executed, the protocol was clarified in four implementation-sensitive areas:

- System-B v1 construction and evaluation use CPU only, consistent with the accepted System-A primary backend and avoiding backend-dependent attribution behavior as an uncontrolled source of variation.
- Rule conditions preserve the authoritative standardized/model-space threshold used by inference and also store its deterministic inverse-scaled raw-unit value for human readability. Raw thresholds are explanation metadata only.
- Bootstrap pass-persistence stability is the candidate-validation gate on the development validation slice and is recomputed separately on the complete frozen pre/post partitions after the rule base is frozen. Longitudinal 5,000-row windows remain repeated descriptive observations and are not converted into pseudo-replicates by running independent inferential bootstrap gates per window.
- Untouched System-B evaluation must begin from a committed freeze. The evaluator is required to reject a dirty worktree so generated R0/manifests cannot be evaluated before their identities are committed.

A formatting defect introduced in the previous control-register edit (a literal backslash-n between two System-B rows) was corrected. It had no scientific effect.

These are prospective implementation clarifications. No System-B rule build, fusion selection, pre-drift evaluation, or post-drift evaluation had been executed when they were recorded.


### System-B orchestration implementation

The reusable symbolic primitives were followed by a System-B orchestration layer that mechanically enforces the prospective firewall.

Repository-only implementation now provides:

- `system-b build`: CPU-only, clean-worktree build using only training and development partitions; it validates the frozen System-A checkpoint identities, performs the frozen SHAP/surrogate/validation procedure, selects the global fusion weight and per-seed thresholds on the designated development slice, and writes seed-specific `R0.v1` artifacts plus a hash-linked System-B manifest.
- `system-b verify`: read-only verification of the compact System-B freeze and local checkpoint identities without loading pre/post.
- `system-b evaluate`: refuses to start unless the freeze is committed (clean worktree), then and only then loads pre/post and writes immutable seed-, rule-, and reporting-window evidence.

The build is fail-closed: if any seed produces no validated active rules, it aborts rather than weakening validation gates using held-out evidence. No System-B training/development build or held-out evaluation was executed while this code was authored; repository-only tests exercise the partition firewall, deterministic development split, CPU requirement, global-lambda tie policy, and overwrite protection.


### System-B CLI routing defect corrected before data execution

Repository review after the orchestration commit found that the intended root-runner edit had not taken effect: `run.py` listed `system-b` as a valid command but still dispatched every non-preprocessing command to System A. The defect was identified before any System-B build or evaluation was executed. The runner was corrected to dispatch System A and System B explicitly, and a repository-only regression assertion was added so this integration path cannot silently regress.


### Single-class longitudinal-window metric guard

A static code audit identified that the shared `binary_metrics` helper computes ROC-AUC unconditionally and would therefore raise on a longitudinal reporting window containing only one class. Before any System-B evaluation, the window-specific wrapper was corrected to retain thresholded confusion-derived metrics while recording ROC-AUC and average precision as undefined for single-class windows. A repository-only regression test was added. Full pre/post partitions still use the standard shared metric implementation because both classes are present by construction.


### Surrogate-leaf consequent semantics fixed before rule generation

The implementation review clarified that each extracted candidate must preserve the fitted surrogate's semantics. The consequent is therefore taken from the fitted decision-tree leaf prediction, including the effect of the prospectively frozen neural-class sample weights. It is not recomputed afterward from an unweighted majority of covered training decisions. Independent development neural-fidelity validation remains the acceptance safeguard.

Candidate logs were also expanded to retain the full canonical antecedent for accepted and rejected candidates, so later lifecycle/rejection analysis does not depend only on opaque candidate IDs. These changes occurred before any System-B rule generation or held-out evaluation.


### Common longitudinal grid activated for frozen System A

Because the 5,000-row, non-overlapping, boundary-aligned reporting grid was frozen prospectively before System-B held-out outcomes, the previously accepted System-A checkpoints can now be rescored on that identical grid as required by the Reconciled operational plan. A separate `system_a_v1_longitudinal_v1` supplement was implemented.

The supplement does not retrain, recalibrate, rethreshold, or rewrite the original System-A evaluation. It reuses every frozen checkpoint and threshold, records per-seed/per-window confusion counts and detection metrics, links back to the accepted System-A evaluation manifest, and writes new immutable LF-normalized evidence. Single-class windows retain thresholded metrics while ranking metrics are recorded as undefined.

No longitudinal System-A rescore was executed during this repository-only implementation step because the ignored local checkpoint bytes remain local-only.


### Longitudinal-rescore sequencing/provenance guard

Before local execution, the common-grid System-A rescore path was tightened to require a clean Git worktree and record its exact commit/branch in both the supplement summary and manifest. The README execution order now requires committing the additive System-A longitudinal supplement before invoking `system-b build`; otherwise the intentionally strict System-B clean-worktree gate would reject the build. This correction was made before any longitudinal rescore or System-B rule build was executed.


---

## 7 October 2026 — System-B R0 execution freeze and pre-evaluation sanitation

The local operator reported successful completion of the prescribed repository tests, System-A verification, common-grid System-A longitudinal rescore, System-B development-only build, and System-B read-only verification. Repository-side inspection was then performed independently before permitting untouched System-B evaluation.

### System-A common-grid longitudinal supplement

Committed supplement:

`results/frozen/system_a_v1_longitudinal_v1/`

Accepted longitudinal manifest SHA-256:

`9f26b54834d041da115adffd7921b10c97ed826e832c2325f77dd0e2a617754a`

The supplement references the accepted System-A manifest `42004b5ed100b690023b9998bdc959fac41ab947b996fb7c58e44cee5e8dc6de` and original evaluation manifest `e721b641b5898976c76c0449dedf7152cb302be4447604525afb7ddf1c94c5b3`.

Its execution provenance records clean commit `e29830bdf0ded41240058f19b4928259b01b5280`, CPU backend, and the prospectively frozen 5,000-row non-overlapping boundary-aligned grid.

Repository sanitation confirmed:

- 14 pre-drift windows per seed totaling exactly 69,260 rows;
- 14 post-drift windows per seed totaling exactly 69,270 rows;
- five seeds retained;
- 140 seed/partition/window rows in total;
- no retraining, recalibration, or threshold reselection implied by the artifact identity.

### System-B development-only build

Accepted System-B manifest:

`data/manifests/system_b_v1.json`

Canonical manifest SHA-256:

`6e3589056d4c252c1a6c7cfd87b891fb8a24f1e30e86b17833b6035ea9ee86a8`

The build provenance recorded by the manifest is:

- clean git commit `cd2078eacb7da28cbd8460da43d96381bd70b013`;
- branch `stage4-system-b`;
- Python 3.11.9;
- Windows runtime;
- CPU backend / PyTorch 2.14.1+cpu;
- NumPy 2.4.6;
- scikit-learn 1.9.1;
- SHAP 0.51.0.

The manifest explicitly records:

- training used: true;
- development used: true;
- pre_drift used: false;
- post_drift used: false.

It also preserves hashes for the training rows, the non-overlapping development validation/fusion slices, and the fixed SHAP background/attribution samples.

### R0 rule-base outcome

Candidate -> active-rule counts were:

- seed 0: 13 -> 7;
- seed 1: 12 -> 8;
- seed 2: 13 -> 7;
- seed 3: 12 -> 8;
- seed 4: 12 -> 6.

The corresponding quality-gate rejection counts were 6, 4, 6, 4, and 6.

Independent repository inspection confirmed for every seed:

- exactly 12 SHAP-selected features;
- every active rule traces to a candidate that passed the prospectively frozen conjunctive quality gate;
- every active rule satisfies support >= 0.001, covered rows >= 100, class precision >= 0.80, neural fidelity >= 0.90, bootstrap stability >= 0.90, and complexity <= 4;
- every rule artifact references the corresponding accepted System-A checkpoint hash and frozen System-A threshold;
- no favorable seed or rule base was substituted after generation.

Active-rule class composition is sparse on the attack consequent but nonzero for every seed:

- seed 0: 6 benign / 1 attack rule;
- seed 1: 6 benign / 2 attack rules;
- seed 2: 6 benign / 1 attack rule;
- seed 3: 7 benign / 1 attack rule;
- seed 4: 5 benign / 1 attack rule.

This composition is retained as generated; it is not rebalanced post hoc.

### Fusion freeze

The prespecified global grid was evaluated on the development fusion slice only.

Mean MCC by neural weight was monotonically highest at the lowest prespecified grid point:

- lambda 0.50: 0.7721332020;
- 0.60: 0.7706859479;
- 0.70: 0.7692022392;
- 0.80: 0.7672804491;
- 0.90: 0.7629981606;
- 1.00: 0.7454673697.

Therefore the frozen selection rule chose `lambda=0.50`.

Frozen per-seed fused thresholds are:

- seed 0: 0.692427396774292;
- seed 1: 0.9235901534557343;
- seed 2: 0.8299936652183533;
- seed 3: 0.9747405052185059;
- seed 4: 0.9527904391288757.

These values were not selected from pre/post evidence.

### Repository/CI sanitation

The R0 artifacts and manifest were committed in:

`245ca52371d7cdbcf8475b1d86b4b95d2b9850f5`

The exact commit completed the GitHub Research Contract successfully.

Repository inspection at that head found no committed `results/frozen/system_b_v1` evaluation directory. Untouched System-B pre/post evidence therefore remained ungenerated/uncommitted at the time of this sanitation review.

A documentation lag was identified before evaluation: the protocol header and control register still described exact R0/fusion identities as not yet frozen even though the freeze commit and CI had succeeded. Those status fields are synchronized in the present governance commit. This is an audit-trail correction only; no rule, threshold, fusion weight, checkpoint, preprocessing state, or evaluation code is changed.

A new repository-only frozen-contract test is also added so CI verifies the committed System-B manifest and R0 artifacts directly, including hashes, checkpoint/threshold linkage, data-access firewall flags, active-rule counts, and validation-gate invariants.

No System-B pre/post metric was viewed or used during this sanitation/freeze synchronization.


---

## 7 October 2026 — pre-evaluation evidence-path sanitation

After accepting the development-only R0 freeze and before any System-B pre/post execution, the untouched evaluator was reviewed against MAIN, the Reconciled operational plan, `SYSTEM_B_PROTOCOL.md`, and the common System-A evidence schema.

The audit found no leakage path: the evaluator loads pre/post only after clean-worktree validation, accepted R0-manifest verification, frozen System-A checkpoint verification, and frozen preprocessing verification.

One publication-grade evidence-completeness gap was found prospectively. The evaluator preserved wide seed-level detection evidence, per-rule pre/post evidence, and window trajectories, but it did not yet emit explicit paired/aggregate metric tables or a direct rule-level staleness-delta table. Although those values would be derivable later, relying on retrospective reconstruction would be weaker than freezing plot-ready machine-readable evidence at evaluation time.

The evaluator was therefore strengthened before any held-out execution to add:

- System-A-compatible long-form seed metric evidence;
- aggregate pre/post metric summaries across the five fixed seeds;
- paired seed-level post-minus-pre deltas and aggregate paired-effect intervals;
- direct rule-ID-matched pre/post staleness deltas;
- frozen-gate pass/fail transition labels without a composite staleness score;
- evaluation runtime/software provenance;
- a read-only post-evaluation hash verifier.

A second semantic hygiene fix records symbolic-neural fidelity as undefined when no resolved symbolic coverage exists instead of encoding absence of an explanation as fidelity zero.

Finally, the evaluation loader now pins the exact accepted `R0.v1` manifest canonical identity and verifies canonical rule-artifact hashes in addition to raw file hashes. This prevents an internally self-consistent but non-accepted replacement rule base from silently entering the untouched evaluation path.

No System-B pre/post values were available or inspected during these changes. The frozen R0, lambda, thresholds, preprocessing, checkpoints, validation gates, and longitudinal window policy are unchanged.


---

## 7 October 2026 — System-B execution-order correction after evidence push

After the first System-B evaluation was committed and pushed, repository provenance established that the local untouched evaluation had in fact been executed earlier than the repository-side evidence-path sanitation commits.

Exact original evaluation provenance:

- source clean commit: `245ca52371d7cdbcf8475b1d86b4b95d2b9850f5`;
- source System-B manifest: `6e3589056d4c252c1a6c7cfd87b891fb8a24f1e30e86b17833b6035ea9ee86a8`;
- evaluation manifest: `f44cad2ed9674bcb7118f05f174f845b5dfb135f95e2cb2b4a230f0f998c3e42`;
- evidence commit: `4542108f61e01348e69a19ee642e5c01abb97491`;
- Research Contract for the evidence commit: successful.

This means earlier ledger/protocol statements asserting that no System-B pre/post outcome had yet been generated during the later sanitation commits were chronologically inaccurate. They are not erased. This entry explicitly corrects them.

Importantly, the later sanitation was not outcome-informed: repository-side review had not inspected System-B metric values when the R0 governance synchronization and evaluator-hardening changes were authored. The changes did not alter R0, lambda, fused thresholds, neural checkpoints, preprocessing, fusion arithmetic, rule activation semantics, or the frozen reporting grid.

Independent integrity checks of the first-run evidence confirmed:

- all 10 seed/partition confusion matrices conserve sample/class totals exactly;
- all five seeds are present;
- pre/post rule IDs match exactly within every seed, with 7/8/7/8/6 rules;
- 14 pre windows per seed sum to 69,260 rows;
- 14 post windows per seed sum to 69,270 rows;
- no reporting window has zero resolved symbolic coverage;
- no aggregate/reporting-window conflict-abstention event occurred;
- the evaluation references the accepted R0.v1 and preprocessing identities.

The correct scientific response is therefore **preservation, not history deletion**. The first untouched evaluation remains the authoritative primary System-B v1 evaluation.

The missing paired/aggregate/staleness tables will be generated as `system_b_v1_supplement_v1` strictly from the already-frozen first-run CSV evidence. The supplement generator is mechanically prohibited from loading raw partitions or model checkpoints. This follows the same additive-evidence principle previously used for the System-A count supplement.

No model rerun, threshold change, rule change, or result-driven retuning is authorized.


---

## 7 October 2026 — Q1 adversarial audit opened; surrogate-leaf protocol discrepancy identified

After the System-B first-run evaluation and additive supplement were frozen, a full adversarial audit was opened against MAIN, the Reconciled operational plan, the frozen System-B protocol, implementation, evidence, and current 2025–2026 literature.

The audit is not an attempt to retune System B. Its purpose is to distinguish protocol conformance, valid but assumption-sensitive design choices, and publication-level robustness gaps before the symbolic substrate is reused in C/D.

A material protocol/code discrepancy was identified:

- `SYSTEM_B_PROTOCOL.md` prospectively requires the candidate consequent to equal the fitted weighted CART leaf prediction;
- the implementation that generated R0.v1 computes the consequent from the unweighted majority of frozen neural decisions among training observations satisfying the leaf path;
- the surrogate itself was fitted with sample weights that equalize the two neural-predicted classes;
- therefore the two consequent definitions are not mathematically guaranteed to agree.

The historical ledger entry stating that the weighted-leaf semantics had been implemented is incorrect. It is preserved rather than rewritten.

No System-B held-out outcome is needed to diagnose realized impact. A new command, `python run.py system-b audit-r0-protocol`, reconstructs the surrogate from **training only** using the frozen selected features and corresponding System-A checkpoint, then compares every stored candidate consequent with the weighted CART leaf class. It records development_used=false, pre_drift_used=false, and post_drift_used=false.

The result will determine the next governance action:

- zero realized mismatches -> preserve R0.v1 and document a no-effect implementation discrepancy;
- one or more mismatches -> preserve all existing evidence, classify a real frozen-protocol implementation defect, and assess a versioned correction without selecting the remedy from held-out performance.

The same audit also identified non-blocking but publication-important issues now recorded in `SYSTEM_B_Q1_AUDIT.md`: inactive-rule precision/fidelity semantics, seed-specific SHAP stability, background/top-k sensitivity, score-vs-probability terminology, effective benign-rule veto authority under the frozen fusion operating point, boundary lambda selection, threshold sensitivity, Destination Port/CICIDS2017 artifact risk, statistical hierarchy, and external checkpoint availability.

No frozen System-B artifact is changed by this audit commit.


### Q1 audit artifact persistence guard

Before local execution of the R0 protocol diagnostic, repository review found that the existing ignore policy admitted only `results/frozen/**`; the proposed `results/audits/**` path would therefore have remained untracked. The ignore policy was prospectively extended to admit audit evidence before the diagnostic was run.

The diagnostic was also tightened before execution to enforce the System-B CPU/Python environment contract and verify the complete frozen training scenario-row identity in addition to the SHAP background and attribution sample hashes. No data were loaded and no diagnostic result existed when these corrections were made.


---

## 7 October 2026 — expanded Q1 audit of hidden assumptions

The System-B audit was expanded without modifying any primary artifact.

Material findings added to the audit record:

- zero B conflict is structurally constrained by disjoint single-tree leaves;
- q is lifecycle metadata in B and does not soften a one-active-leaf symbolic score;
- lambda=0.50 plus thresholds >0.50 gives covered benign rules effective veto authority;
- aggregate coverage/fidelity hides materially weaker attack-side symbolic correctness;
- row-bootstrap persistence does not account for retained duplicate-pattern dependence;
- exact threadpool state was not captured in B build provenance;
- CICIDS2017 Destination Port and known flow/labelling defects require explicit sensitivity/limitations.

`SYSTEM_B_ROBUSTNESS_PLAN.md` freezes the sensitivity agenda before any C/D held-out outcome. Because B outcomes are already known, B robustness analyses are explicitly post-hoc and cannot replace R0.v1 or the first evaluation.


---

## 7 October 2026 — semantic-analysis hash-chain sanitation

Before executing the new frozen-evidence semantic analysis, its source chain was tightened: the accepted System-B supplement manifest is now pinned to canonical SHA-256 `70d41b210ed54f2fa2269ec738ccd94100148d701bb5a2ae79d8d30839e9d190`, and the semantic-analysis command verifies both the original evaluation and the accepted supplement before reading derived tables.

This is an integrity-only change. No numerical result, R0 rule, threshold, fusion setting, or held-out computation is changed.


---

## 7 October 2026 — duplicate-dependence and lifecycle-schema sanitation

Audit-only reconstruction quantified identical 77-feature patterns in the actual B evidence slices: 3.88% of the rule-validation slice belongs to duplicated patterns (max group 206), 5.86% of exact pre-drift rows (max 548), and 3.18% of exact synthetic post-drift rows (max 136). The primary duplicate-retention policy remains unchanged. These figures justify the already-frozen group-aware/deduplicated stability sensitivity and caution against interpreting row-bootstrap persistence as independence-aware robustness.

The static R0 schema was also reviewed against the final D lifecycle claim. It is adequate for persistent initial rule identity but not, by itself, a complete lifecycle event log. D must prospectively add immutable operation/parent/evidence/trigger/decision/cost records while preserving the frozen R0 IDs.


---

## 7 October 2026 — semantic-analysis artifact tracking guard

Before executing the new System-B semantic-analysis command, repository ignore rules were checked. `results/analysis/` was still covered by the generic `results/*` ignore pattern. The directory is now explicitly unignored so the derived semantic-analysis artifact can be reviewed, hashed and committed through the normal scientific freeze workflow.

No analysis output had yet been generated when this guard was added.


---

## 7 October 2026 — expanded Q1 audit: hidden controls identified before C/D

A second adversarial pass reviewed System-B mechanics not with the intent to improve already-observed B outcomes, but to determine whether assumptions would survive top-quartile peer review and whether they create hidden treatment variables for C/D.

No frozen System-B artifact, rule, lambda, threshold or held-out outcome was changed.

New material findings were appended to `SYSTEM_B_Q1_AUDIT.md` and prospective sensitivities to `SYSTEM_B_ROBUSTNESS_PLAN.md`.

Key findings:

- the absolute covered-count rule has sample-size-dependent meaning and cannot be transplanted blindly into a smaller D adaptation-validation window;
- B development true-label validation contains only GoldenEye attacks, so R0 attack-rule precision is scenario-specific rather than generic attack-family validation;
- the SHAP top-12 score is a bespoke class-aware max-normalized selection policy and requires robustness against conventional aggregation choices;
- one deterministic 60/40 development split does not establish acceptance stability across legitimate validation partitions;
- five-seed intervals quantify stochastic-model variability conditional on one stream, not environmental generalization;
- accepted-rule validation metrics are selection-conditional; held-out pre-drift is the actual post-selection generalization check;
- the historical B timing field includes symbolic inference plus fusion and lacks a strong repeated/thread-frozen benchmarking protocol;
- C/D fused-threshold handling is itself a causal control after neural adaptation;
- true-label class precision makes label latency part of D's treatment definition;
- adaptation candidate-generation and validation evidence must be time-respecting;
- imputed antecedent values are currently invisible in rule traces;
- future overlapping D rules make confidence-update timing operationally important.

The statistical analysis plan was expanded to state explicitly that seed-level uncertainty is conditional on scenario, rule-level outcomes remain nested/descriptive, and adaptive recovery/update timing must respect actual information availability.

These changes are prospective for C/D. They do not authorize any retuning of R0.v1 after observed System-B outcomes.

The previously identified weighted-surrogate-leaf consequent diagnostic remains the immediate blocking System-B closure gate.


---

## 7 October 2026 — R0.v1 protocol defect realized; R0.v2 correction frozen prospectively

The committed training-only diagnostic `results/audits/system_b_r0_protocol_audit_v1.json` has raw SHA-256 `abfcb3af93531369427489fc27773f41e500a57279b0fa752b946c3985ebbf32`.

It reconstructed all 62 original surrogate leaves using the exact frozen training rows, selected features, System-A checkpoints and weighted CART fitting procedure. It loaded no development, pre-drift or post-drift partition.

Result:

- 7 candidate consequents differ between the historical unweighted implementation and the fitted weighted CART leaf class;
- 4 mismatches are active in R0.v1;
- 0 path reconstruction mismatches;
- 0 mismatches between the stored artifact and the historical unweighted-majority code.

All four active discrepancies are stored BENIGN rules whose weighted CART leaf class is ATTACK. Using their already-frozen development-validation counts, the protocol-correct ATTACK consequent fails both class-precision and neural-fidelity gates for all four. They therefore should not have entered an implementation conforming to the frozen protocol.

The original R0.v1 and all v1 evaluation evidence remain immutable.

Before any corrected held-out computation, `SYSTEM_B_R0_V2_CORRECTION_PLAN.md` freezes a narrow deterministic correction:

- inherit the exact frozen v1 feature selections;
- do not rerun SHAP;
- reconstruct the same weighted trees and paths;
- derive candidate consequent from weighted CART leaf class;
- reapply the original development validation gates;
- abort if any unaffected active v1 rule changes;
- reselect lambda and fused thresholds only on the original development fusion slice;
- forbid pre/post access during v2 build.

The correction decision is outcome-independent: if the build satisfies the frozen correction contract, R0.v2 supersedes R0.v1 for all future C/D initialization regardless of eventual corrected B held-out performance.

A later corrected B v2 evaluation is required for static-reference comparability. It will be labeled a protocol-defect correction rather than an untouched first-look evaluation because v1 held-out outcomes are historically known.

No C/D adaptive outcome has been generated, so the primary future C-vs-D causal contrast remains uncontaminated.


### R0.v2 pre-execution sanitation hardening

Before any local R0.v2 build, the correction code was reviewed again.

Two additional integrity guards were added:

- the v2 builder now invokes the complete accepted R0.v1 verifier, including source rule-artifact and checkpoint identities, rather than trusting only the v1 manifest's internal hash;
- every candidate whose consequent is unaffected by the audited defect must reproduce its original development support, covered count, class precision, neural fidelity, bootstrap stability, complexity and gate decision exactly. Any discrepancy aborts v2 before fusion selection.

The inherited v1 SHAP ranking is copied into each v2 rule artifact for provenance; SHAP itself remains unrecomputed.

The correction plan, Q1 audit and robustness plan are now required governance files in CI.

No data were loaded and no R0.v2 artifact existed when these guards were added.


---

## 7 October 2026 — protocol-conformant R0.v2 frozen and independently sanitized

R0.v2 was generated locally from clean commit `cf28304e2f08be731c3ebaf096f4f31fd66eaef7` under Python 3.11.9 / CPU and committed at `16cd22a448e43e598b03446b978fb762fbd42523`.

Accepted manifest:

`data/manifests/system_b_v2.json`

Canonical SHA-256:

`131027d2f136494eb388183f18dcb7eb0e9d7e9fe786f22dba25f4e1624c1483`

The exact artifact-freeze commit passed Research Contract #91.

Independent repository comparison against R0.v1 confirmed:

- training, development-validation, development-fusion, SHAP-background and SHAP-attribution row identities are unchanged;
- preprocessing, System-A manifest and dependency-lock identities are unchanged;
- all five selected-feature lists and SHAP rankings are unchanged;
- candidate counts are unchanged at 13/12/13/12/12;
- the only changed candidate consequents are exactly the seven frozen-audit mismatches;
- every changed candidate is rejected under the original quality gates;
- every unaffected candidate reproduces antecedent, support, covered count, class precision, neural fidelity, stability, complexity and gate decision exactly;
- the only active R0.v1 rules removed are the four audited defective rules (two in seed 1 and two in seed 3);
- no new active rule is introduced;
- final active counts are 7/6/7/6/6.

The same frozen fusion grid was recomputed on the same development fusion slice. Lambda 0.50 remains the rank-1 selection by mean MCC (0.7716683), followed monotonically by 0.60, 0.70, 0.80, 0.90 and 1.00. This is a fresh development-only consequence of R0.v2, not an inherited v1 constant.

Frozen R0.v2 fused thresholds:

- seed 0: 0.692427396774292;
- seed 1: 0.9354645609855652;
- seed 2: 0.8299936652183533;
- seed 3: 0.9747405052185059;
- seed 4: 0.9527904391288757.

Only seed 1's threshold changes materially from v1. No pre/post partition was loaded during the v2 build.

R0.v2 is now the required symbolic initialization for future C/D regardless of corrected B held-out performance. R0.v1 remains immutable historical nonconformant evidence.


---

## 7 October 2026 — corrected System-B v2 evaluation protocol frozen before execution

After R0.v2 was accepted and before any R0.v2 pre/post computation, `SYSTEM_B_V2_EVALUATION_PROTOCOL.md` was frozen.

The corrected evaluation is explicitly classified as an implementation-defect correction rather than untouched first-look evidence because R0.v1 held-out outcomes are historically known.

No R0.v2 detection/explanation outcome existed when the protocol was fixed.

The evaluator is isolated from v1 evaluation artifacts and may load only pre_drift/post_drift. It uses the accepted R0.v2 manifest, unchanged System-A checkpoints, frozen preprocessing, lambda and per-seed thresholds.

Q1-audit-driven evidence additions are prospective and do not alter prediction:

- benign/attack symbolic coverage, correctness and neural fidelity separately;
- per-rule imputed-antecedent activation plus imputation-free rule-quality diagnostics;
- repeated symbolic+fusion timing (1 warm-up + 5 measured exact-reproduction passes);
- torch/threadpool/environment provenance.

The output is write-once under `results/frozen/system_b_v2_corrected_v1/`.

R0.v2 remains the required C/D initial symbolic state regardless of corrected evaluation results.


### Corrected-v2 evaluator pre-run diagnostic test hardening

Before corrected R0.v2 pre/post execution, a repository-only unit test was added for the new imputation-aware explanation diagnostic. It verifies that only activated rules whose antecedent feature was actually missing are counted, and that the imputation-free quality calculation excludes those activations without altering primary prediction.

No R0.v2 held-out output existed when this test was added.


### Statistical-status sanitation before corrected v2 evaluation

Before R0.v2 pre/post execution, the statistical-analysis plan was amended to make the correction status explicit. R0.v2 is the protocol-conformant B baseline, but its corrected evaluation is not a second untouched first-look experiment. The v1-v2 contrast is therefore sensitivity/provenance rather than a confirmatory hypothesis test.

The newly frozen class-conditional symbolic and imputation-aware diagnostics are descriptive. They do not add post-hoc confirmatory endpoints or alter the later primary matched C-vs-D inferential unit.

No R0.v2 held-out result existed when this statistical classification was recorded.


---

## 7 October 2026 — corrected System-B v2 evaluation frozen and sanitation-complete

The corrected protocol-conformant System-B v2 evaluation was executed from clean commit `51690ea23906ab87b9406311eacf381c7a22b5fb` and committed at `03b7e52da3a24ebc2c28b26f8293bcbea2413ed3`.

Evaluation manifest:

`results/frozen/system_b_v2_corrected_v1/evaluation_manifest.json`

Canonical SHA-256:

`583fa356c291bd7b2b275d726bb9eee31ae9aa5470cca50f0146c91642873710`

The evidence commit passed Research Contract #96.

Repository-side sanitation confirmed:

- accepted R0.v2 manifest identity `131027d2f136494eb388183f18dcb7eb0e9d7e9fe786f22dba25f4e1624c1483`;
- evaluation executed from a clean worktree under Python 3.11.9 / CPU;
- training/development were not loaded by the evaluator;
- all five seeds and both pre/post partitions are present;
- every confusion matrix conserves sample and class totals exactly;
- 14 windows per seed/partition cover exactly 69,260 pre rows and 69,270 post rows;
- rule identities match pre/post within each seed at counts 7/6/7/6/6;
- 32 direct rule staleness records are present;
- staleness transitions are 18 pass→pass, 7 fail→pass, 6 fail→fail, 1 pass→fail;
- all conflict-abstention rates are zero, as expected for mutually exclusive static tree-leaf rules;
- all 64 rule×partition imputation diagnostics report zero activated rule antecedents depending on an imputed raw value;
- repeated symbolic+fusion timing used the frozen 1 warm-up + 5 measured-repeat protocol and recorded thread/runtime state.

Detection remained strong but did not turn the controlled shift into a generic degradation event. Across five seeds, mean MCC increased from 0.73324 pre to 0.77291 post and mean F1 from 0.71394 to 0.75933. Mean AP decreased from 0.90240 to 0.85119 and mean ROC-AUC slightly decreased from 0.97933 to 0.97518.

Symbolic behavior is class-asymmetric:

- mean overall resolved coverage: 0.96229 pre, 0.95732 post;
- mean BENIGN resolved coverage: 0.98140 pre, 0.97062 post;
- mean attack resolved coverage: 0.61259 pre, 0.71279 post;
- mean BENIGN symbolic correctness: ~0.99999 pre and 1.0 post;
- mean attack symbolic correctness: 0.80333 pre and 0.74953 post;
- mean attack symbolic-to-neural fidelity: 0.94418 pre and 0.96406 post.

Thus the shift increases attack-side rule activation/coverage on average while true-label correctness among covered attack rows declines on average. Neural fidelity improves at the same time. This directly demonstrates why class precision/correctness and neural fidelity must remain separate explanation-quality dimensions.

The only pass→fail rule is seed 3 rule `r0-s3-e71a7cc956b5d661`, a BENIGN rule. Its class precision remains 1.0; support declines from 0.001790 to 0.001545, neural fidelity from 1.0 to 0.98131, and bootstrap gate-persistence stability from 1.0 to 0.8. The failure is therefore stability-driven rather than a correctness collapse.

The v1→v2 correction has small predictive effect but meaningful coverage impact only on the affected seeds. Seeds 0/2/4 are unchanged. Seed 1 loses ~0.021 pre and ~0.035 post resolved coverage with MCC changes about -0.00284/-0.00202; seed 3 loses ~0.00445 pre and ~0.02165 post coverage while MCC is approximately unchanged/slightly improved post. This is implementation-correction provenance, not a model-selection comparison.

R0.v2 remains the required initial symbolic state for future C/D regardless of these corrected held-out outcomes.


---

## 7 October 2026 — governing-source revision after retrospective assumption audit

The two project-source Word authorities were revised additively after corrected System-B v2 evidence was already frozen.

Current source identities:

- MAIN: `c3f1fed692ff0478c221925fca5c311380617a993e7ebf0021af2e05a362ab66`;
- Reconciled implementation plan: `05378ef14437f037bab0aa77853a16980b4fc60ac303398acc1cc293bdd32bdb`.

The previously frozen A/B artifacts legitimately contain the earlier governing-source hashes and are not rewritten. The revised authorities govern new robustness diagnostics and all future C/D work.

The revision formalizes:

- a restart/versioned-rerun versus additive-sensitivity versus later-generalization classification;
- BENIGN-source-regime-dominant wording for `sudden_benign_v1`, with explicit acknowledgment of nonzero GoldenEye temporal movement;
- mandatory exact-pattern/duplicate-aware, development-split, fusion-authority, SHAP-reference and rule-gate robustness around immutable R0.v2;
- a Stage-3A float64-versus-System-B-float32 conformance diagnostic;
- unchanged/raw bounded seed-level t-intervals with publication-layer physical-axis handling;
- multi-scenario/second-dataset and checkpoint-archive obligations before broad submission claims.

No historical frozen artifact was altered by this governance sync.


### Stage-3A/System-B dtype conformance audit frozen before execution

The retrospective audit identified a documentation/implementation divergence: the Stage-3A readiness contract designates float64 as the shared preprocessing output for non-PyTorch consumers, while System B fit the surrogate from float32 transformed matrices.

Before any robustness tranche or C/D implementation, a training/development-only audit command was added. The neural teacher remains float32 in both comparison arms; accepted R0.v2 feature selections are reused exactly; SHAP is not recomputed. The audit compares float32 versus float64 surrogate topology, train/validation leaf assignment, weighted leaf consequents, validation-gate outcomes and active candidate sets.

The decision rule was frozen before execution: harmless threshold roundoff alone does not replace R0.v2. A new version is required only if the dtype change produces a discrete scientific difference in topology/assignment, consequent, gate outcome or accepted candidate set. No pre/post partition is loaded by this audit.


### Repository retrospective scenario/exact-pattern audit added

A write-once post-hoc diagnostic was added to reproduce the earlier raw-data recheck inside the governed repository.

It records:

- exact training duplicate-excess rows after the frozen 77-feature representation;
- exact training-seen feature-pattern counts for development, pre-drift and post-drift, including class decomposition;
- feature-wise KS diagnostics for pre/post BENIGN and GoldenEye subsets using the historical deterministic 50,000-row BENIGN sampling convention;
- conservative scenario wording that does not assume attack-distribution invariance.

This diagnostic may read all frozen partitions because it is explicitly retrospective descriptive evidence after A/B outcomes are known. It may not change scenario construction, R0.v2, thresholds or primary evaluation.


### Fixed A/B seen-versus-unseen exact-pattern rescore added

The Stage-2 data-quality policy had prospectively called for reporting observations whose exact feature pattern was not present in training. That reporting obligation was not carried through the original A/B evaluation.

A new write-once robustness command now:

- defines membership from exact equality of the raw frozen 77-feature representation before imputation/scaling;
- uses training rows only to construct the membership mask;
- reruns the already-frozen System-A checkpoints and accepted R0.v2 on pre/post without retraining, rule changes, lambda changes or rethresholding;
- reports seen and unseen strata separately for A and B-v2;
- treats one-class seen strata descriptively, with ROC-AUC/AP undefined where appropriate.

This is additive post-hoc robustness, not model selection and not a replacement primary evaluation.


### Bounded-metric interval reporting policy frozen

The repository now explicitly distinguishes statistical arithmetic from presentation. Existing seed-level t-interval endpoints remain untouched even when a bounded metric interval extends outside [0,1]. Numerical tables retain the raw interval. Figures may use physical metric axes only with disclosure if the underlying interval exceeds the visible domain. No frozen evidence is clipped or rewritten.


### Two-stage System-B selection robustness implemented

The high-leverage B robustness choices are now implemented as a training/development-only selection freeze followed by a separate future held-out rescore.

The selection stage covers:

- Destination Port exclusion;
- two alternate SHAP aggregation policies derived from the frozen attribution evidence;
- four deterministic alternate development splits;
- one-factor rule-gate variants for support, class precision, neural fidelity, bootstrap gate-persistence and complexity.

For every variant, candidate rules use the protocol-correct weighted CART leaf consequent, the same redundancy/conflict policy, and the same development-only fusion-weight grid/threshold selection procedure. The resulting variant rule artifacts, lambda and thresholds are write-once and must be committed before any pre/post robustness evaluation.

These variants can never replace accepted R0.v2 because held-out performance is better; they are secondary/post-hoc robustness only.


### Held-out evaluation stage for B selection robustness implemented

A separate robustness evaluator now consumes only a previously frozen/committed training-development selection manifest. It loads pre/post but not training/development, preserves every variant's frozen rules, lambda and per-seed threshold, and reports detection plus class-conditional symbolic outcomes. The resulting held-out robustness evidence cannot select a replacement for R0.v2.


### Robustness isolation hardening

Before any selection-robustness execution, the alternate-development-split implementation was reviewed for one-factor isolation. An initial draft also changed the bootstrap RNG as the split seed changed. That would have confounded split sensitivity with resampling realization. The code was corrected so bootstrap random state remains the original base+model-seed policy for every split variant; only development row membership changes.


### Duplicate-aware System-B validation sensitivity implemented

The duplicate sensitivity now avoids arbitrary first-row deduplication or majority relabeling. Exact raw 77-feature patterns are grouped; each pattern receives equal total weight, while any conflicting labels within a pattern remain represented as fractional class correctness. Bootstrap stability resamples entire exact-pattern groups.

This provides a dependence-aware sensitivity for support/precision/fidelity/stability and candidate gate decisions without changing the primary row-retention policy.


### SHAP background-reference sensitivity added to the selection freeze

The selection-robustness stage now includes two alternate balanced SHAP backgrounds (seeds 20261008 and 20261009) and one natural-prevalence 256-row background (seed 20261007). The original balanced 20261007 background remains the primary reference.

For these variants, the attribution sample remains exactly the frozen balanced 1,024/1,024 training sample from seed 20261007. Thus only the background reference distribution/seed changes. Each resulting ranking proceeds through the same surrogate, validation and development-only fusion selection pipeline before any held-out robustness evaluation.


### Pattern-deduplicated System-A robustness teacher implemented

A separate post-hoc alternate teacher now tests whether the primary neural baseline materially depends on repeated training observations. Training rows are collapsed by exact raw 77-feature pattern plus binary label, preserving contradictory BENIGN/attack representations as separate observations and forbidding majority relabeling. The accepted training-fitted preprocessor is reused without refit.

The neural architecture, initialization/seeds, optimizer, early-stopping rule, development evidence, class-weight formula and MCC threshold-selection procedure remain the accepted System-A protocol. The alternate checkpoints and manifest are isolated under robustness paths and cannot replace accepted System A based on later held-out performance. No pre/post partition is loaded during alternate-teacher training.


### CI repair for alternate-teacher data-firewall test — 7 October 2026

Research Contract runs #115–#117 failed because the new repository-only test searched the entire `build_pattern_dedup_teacher` source for the bare strings `pre_drift` and `post_drift`. The builder legitimately records `pre_drift_used=False` and `post_drift_used=False` in its provenance manifest, causing a false-positive test failure even though its only partition loads are training and development.

The test was narrowed to forbid exact held-out calls `load_partition("pre_drift")` and `load_partition("post_drift")` while still requiring explicit training/development loads. No experimental code, frozen artifact, treatment, data-access rule, or scientific result changed.


### Fusion-authority robustness implementation — 7 October 2026

The remaining high-priority System-B assumption, symbolic/neural fusion authority, was implemented as an isolated sensitivity rather than mixed into rule-selection variants.

The sensitivity reuses the exact accepted R0.v2 rule artifacts. It does not rerun SHAP, fit a surrogate, change gates, or rebuild rules. Lambda values 0.70, 0.90 and 1.00 are fixed before held-out sensitivity execution. Each weight receives seed-specific thresholds selected only on the original development fusion slice with the original MCC/tie-break rule. The selection artifact must be committed before any pre/post sensitivity rescore.

This design specifically tests whether the primary lambda=0.50 boundary choice and veto-like BENIGN rule authority materially drive the observed B conclusions without creating a post-hoc replacement baseline.


### Fusion-authority CLI routing correction — 7 October 2026

After the selection-robustness evaluation was frozen, the first attempted calls to
`build-fusion-authority-robustness` and `verify-fusion-authority-robustness`
were found to be misrouted by the System-B CLI dispatcher to
`verify_duplicate_aware_validation()` through a catch-all `else` branch.

Observed consequence:

- both commands only re-verified the already frozen duplicate-aware validation artifact;
- no fusion-authority selection directory or manifest was created;
- no fusion-authority threshold selection occurred;
- no pre_drift/post_drift partition was loaded by those attempted calls;
- accepted A, R0.v2, B, and all frozen robustness evidence were unchanged.

The dispatcher was corrected to use explicit command branches for duplicate-aware
verification and all four fusion-authority operations, with an explicit error for
any unhandled System-B command. A repository-only regression test now guards the
mapping in CI. The fusion-authority sensitivity remains unexecuted until the
corrected dispatcher commit passes CI.


### Pattern-deduplicated teacher R0 robustness gate wired — 7 October 2026

After the alternate System-A teacher manifest was frozen, the downstream alternate-R0 builder was promoted from a direct-import-only module to explicit System-B CLI commands:

- `build-pattern-dedup-teacher-r0`
- `verify-pattern-dedup-teacher-r0`

The builder must start from a clean worktree and verifies the frozen alternate-teacher manifest/checkpoint hashes before use. It reconstructs the exact retained training rows, checks both retained-training and development row identities, reuses the accepted frozen preprocessing without refit, preserves the System-B SHAP/surrogate/validation protocol including weighted CART leaf consequents, and uses training/development only. The resulting alternate R0 manifest/rules are write-once and must be committed before any pre/post alternate-chain evaluation.

The frozen alternate teacher removed 113,817 repeated training rows under exact raw 77-feature-pattern-plus-binary-label deduplication. Because label-conflicting feature patterns are preserved as separate observations, this differs by 41 rows from the earlier feature-pattern-only duplicate-excess count of 113,858; the difference is expected and is provenance evidence, not a correction.

The deduplication is class-asymmetric: attack rows decrease more strongly than BENIGN rows, so the alternate teacher's positive-class weight changes accordingly. This is part of the intended training-multiplicity sensitivity and must not be interpreted as an isolated row-count perturbation.


### Held-out pattern-deduplicated A-to-R0-to-B chain evaluation implemented — 7 October 2026

After the alternate neural teacher and its downstream alternate R0 were both frozen before held-out access, a write-once evaluator was added for the complete duplicate-dependence chain.

The evaluator:

- verifies both frozen source manifests and their file identities before scoring;
- loads pre_drift and post_drift only, with no training or development access;
- scores the pattern-deduplicated alternate System-A teacher at its frozen per-seed development MCC thresholds;
- scores the matched alternate System-B rule state using the same alternate teacher, its frozen selected lambda and per-seed development fusion thresholds;
- reports seed-level, aggregate and paired post-minus-pre detection results, plus the corrected-v2 class-conditional symbolic evidence for alternate B;
- cannot be used to select a replacement for accepted System A, R0.v2 or corrected System B.

This sensitivity intentionally keeps the accepted training-fitted preprocessing fixed. It therefore measures dependence on training-example multiplicity and the resulting teacher/rule state, not a fully deduplicated end-to-end preprocessing pipeline.


### Deduplicated-training chain evaluator CSV-schema correction — 8 October 2026

The first held-out invocation of `evaluate-pattern-dedup-chain` occurred only after
the alternate System-A teacher and alternate R0 manifests had been frozen. The
evaluator successfully verified those frozen sources, loaded and scored the
pre_drift/post_drift partitions, and then failed while serializing
`metrics_by_seed_system.csv`.

Cause: the shared CSV writer inferred field names from the first neural-only
System-A row, while later System-B rows additionally contained the frozen
symbolic evidence fields (coverage, correctness, fidelity, and abstention
metrics). Python's `csv.DictWriter` therefore rejected the later rows as
containing fields outside the first-row schema.

Scientific consequence classification:

- frozen alternate teacher: unchanged;
- frozen alternate R0: unchanged;
- thresholds, neural weight, rules, and held-out scoring equations: unchanged;
- no evaluation manifest was produced by the failed write;
- no persisted result is accepted from the failed attempt;
- pre/post had nevertheless been accessed and scored in memory, so the corrected
  rerun is explicitly classified as an implementation-defect correction rather
  than a pristine first-look evaluation.

Correction: the evaluator now rectangularizes the mixed System-A/System-B row
schema deterministically before aggregation and CSV serialization. A
repository-only regression test reproduces the heterogeneous-row condition.
The correction changes serialization only and must not be used to alter model,
rule, threshold, fusion, or metric choices.


### System-B implementation closure after full duplicate-dependence chain — 8 October 2026

The full pattern-deduplicated A-to-R0-to-B robustness chain is now frozen after a serialization-only evaluator correction. Research Contract run #151 passed on the frozen evaluation commit.

Frozen duplicate-chain identities:

- alternate System-A teacher manifest: `9aaf25d65052f3b6521c248d88aab6d55dd5dd2e02ed73d18452bc0460db3c5f`;
- alternate R0 manifest: `3e1d7a984776ccc5d336716f25063f0e9f655590f8b4a92c1b6928f4517fe681`;
- full-chain evaluation summary artifact hash: `b38765fc0c1a936d1918da77ddf332ca46924d829e9d58aa5c7001ca27ed1f3d`.

The alternate teacher removes training multiplicity under exact raw 77-feature-pattern-plus-binary-label deduplication while preserving label conflicts and reusing the accepted preprocessing state. The resulting alternate R0 selects neural weight 0.50 but has 8/8/8/9/8 active rules across seeds, demonstrating substantial symbolic-state dependence on upstream training multiplicity.

Held-out alternate-B mean detection remains viable: MCC is approximately 0.762 pre-drift and 0.790 post-drift; F1 approximately 0.745 and 0.779. Its post-minus-pre MCC is approximately +0.0287 and F1 +0.0332. Symbolic behavior differs materially from accepted R0.v2: attack resolved coverage is approximately 0.897 pre and 0.907 post, while attack symbolic correctness is approximately 0.563 pre and 0.614 post. These differences are treated as assumption dependence, not as a basis to replace accepted System A or R0.v2.

With this evidence frozen, the mandatory retrospective System-B robustness tranche is closed. No unresolved System-B implementation defect remains that requires reopening A, R0.v2, or corrected B before C/D design work. Remaining open controls belong to the prospective adaptive phase and must be frozen before any C/D held-out execution.


### System-B milestone acceptance and C/D adversarial design gate — 8 October 2026

System B was formally accepted into `main` through pull request #2 after the exact
`stage4-system-b` closure head
`317b8d957c3ac983598523215a1205b6869f8c17` passed PR-specific Research
Contract run #156. The pull request was merged with a normal merge commit rather
than a squash so the 94-commit System-B scientific history remains part of the
audit trail. The resulting accepted `main` milestone is
`4c13d71a111ce7b72b3ef26a01b2918592425aa1`.

The next stage branch, `stage5-cd-design-audit`, was created from that exact
accepted parent. No adaptive implementation code was introduced at branch
creation.

A prospective adversarial review was then frozen in
`C_D_ADVERSARIAL_DESIGN_AUDIT.md`. Its purpose is to attempt to falsify the
C-versus-D causal design before implementation rather than to confirm readiness.

The audit identified treatment-contamination risks that must be eliminated
prospectively. Most importantly:

- D symbolic state must not affect the signal or state used to produce the
  shared drift-event stream;
- C/D fused outputs must not determine label acquisition, replay membership,
  neural-update evidence, or symbolic evidence availability in the primary
  causal comparison;
- label maturity and prequential information timing must be explicit before a
  detector or updater is selected;
- adaptation windows must not use post-trigger future rows before their claimed
  publication time;
- matched C/D neural trajectories must be mechanically verifiable through
  detector-event, replay-row, update-row, and checkpoint hashes rather than
  asserted from common hyperparameters;
- independent threshold adaptation from C/D fused scores is not admissible for
  the primary contrast because it creates a treatment-dependent operating-point
  trajectory;
- D-drift and D-periodic must be opportunity/budget matched with only the
  symbolic trigger schedule differing;
- online symbolic gate/count semantics, confidence timing, and the complete
  lifecycle state machine remain unresolved blockers.

The audit therefore classifies the project as ready for **prospective C/D design
freeze but not adaptive implementation**. This is not a defect in accepted A/B
evidence and does not reopen System B.

The preferred causal architecture emerging from the audit is a shared per-seed
non-symbolic control plane: one treatment-independent detector/event stream,
one replay/buffer trajectory, and one neural-checkpoint trajectory are consumed
by both C and D. System C holds accepted R0.v2 frozen; System D alone receives
the symbolic-evolution treatment. Any divergence in required non-symbolic state
is an experimental abort condition.

Current 2025-2026 literature was consulted prospectively only. Recent
stream-learning work on delayed labels and processing-framework choice supports
making label timing a first-class design variable, while recent continual-NIDS
comparisons support replay as a serious candidate neural adaptation baseline.
These observations motivate later design choices but do not freeze a detector,
delay value, replay variant, or update hyperparameter.


### C/D stream-time and information-availability contract frozen — 8 October 2026

Before choosing the drift detector or implementing any adaptive component, the project froze
`C_D_STREAM_TIME_CONTRACT.md`.

This ordering is deliberate. A detector or updater that is selected before deciding when labels and
observations legally exist can force hidden assumptions into the experiment. The timing contract was
therefore treated as upstream of detector choice.

The frozen scenario manifest was rechecked and confirms that the MachineLearningCSV scenario used
here does not support true timestamp chronology. The adaptive experiment therefore uses row index as
a logical observation clock and makes no wall-clock label-delay or production-throughput claim.

Primary information-time decisions:

- the adaptive stream is the uninterrupted ordered concatenation of pre_drift followed by post_drift;
- no detector, label queue, replay/buffer, model, rule, threshold or RNG state is reset at the evaluator-known synthetic boundary;
- the primary verification latency is a fixed 5,000 stream rows;
- label `y_j` becomes adaptively visible only after the prediction at row `j+5000` is committed;
- labels whose maturity falls beyond the end of the stream are not flushed into adaptive components;
- the offline evaluator may use all labels after predictions are frozen, but this scoring channel is logically separated from adaptive label availability;
- prediction always precedes label release, including the zero-delay sensitivity;
- a supervised prequential drift statistic must use the prediction stored at the origin row, rather than rescoring that historical row under a later model;
- updates may use only observations already arrived and labels already mature at their causal update clock;
- any new adaptive state can affect the next logical prediction at earliest;
- the primary logical stream is synchronous between predictions because no trustworthy event timestamps exist to model backlog during computation; update wall-clock cost is measured separately.

The 5,000-row delay is an explicit controlled simulation assumption, not an estimate of SOC
investigation latency. It reuses an already frozen stream granularity to avoid adding an
outcome-sensitive scale while remaining logically independent of the reporting-window mechanism.
Prespecified latency robustness conditions are `L=0` and `L=10,000`.

The primary condition assumes complete eventual supervision subject to the fixed delay and terminal
right-censoring. Partial/selective label acquisition is excluded from the primary causal contrast
because it would add a second evidence-acquisition treatment; it may be studied later only as a
separately frozen robustness condition.

A targeted literature refresh was performed before freeze. Recent Pattern Recognition and Digital
Signal Processing work confirms that processing framework, verification latency and partial label
availability materially affect drift evaluation. NOCTOWL (IEEE Access 2025) further confirms that
delayed/selective supervision is already an explicit NIDS operating constraint. These works motivate
the methodological control but do not supply an empirically correct CICIDS2017 delay value.

The information-time decisions were propagated into `EXPERIMENT_CONTROL_REGISTER.md` and
`STATISTICAL_ANALYSIS_PLAN.md`. No detector family, detector hyperparameter, adaptation window,
replay policy, neural update, threshold adaptation, or symbolic lifecycle decision was selected from
this packet.

The remote annotated tag `system-b-v2` was also verified through the GitHub compare interface to
resolve to accepted `main` milestone
`4c13d71a111ce7b72b3ef26a01b2918592425aa1` exactly.

**Gate after this packet:** timing/label availability is frozen; adaptive implementation remains
prohibited. The next packet must select the treatment-independent drift-monitor signal and detector
under this timing contract.


### Primary C/D drift-monitor protocol frozen after delayed-feedback audit — 8 October 2026

The next prospective design packet selected the upstream detector only after the information-time
contract had been frozen.

The primary signal is seed-specific delayed neural-only prequential hard error:

`e_j = 1[1[p_j >= tau_monitor] != y_j]`.

The neural probability `p_j` is the immutable score stored when row `j` originally arrived.
The label is used only after maturity under the already frozen 5,000-row verification latency.
The monitor threshold is the accepted System-A development threshold for the corresponding seed and
remains fixed for detector purposes even if later operational/fusion threshold policy differs.

The exact primary thresholds are:

- seed 0: 0.939024031162262
- seed 1: 0.9333740472793579
- seed 2: 0.9121250510215759
- seed 3: 0.9789621233940125
- seed 4: 0.954619288444519

This creates a treatment-independent neural sentinel. C/D fused scores, symbolic coverage, rule
confidence, conflict and abstention are explicitly forbidden upstream detector inputs.

The primary detector is `river.drift.ADWIN` under the locked `river==0.26.1` dependency with
the exact River defaults: delta=0.002, clock=32, max_buckets=5, min_window_length=5 and
grace_period=10. No detector parameter is tuned against the adaptive pre/post stream. One
`drift_detected=True` output constitutes one confirmed statistical drift event; no additional
outcome-tuned multi-hit rule is used.

A key delayed-feedback problem was identified during this design audit. If a neural update is
published while labels are delayed by 5,000 rows, the next 5,000 mature errors initially refer to
predictions made by the **old** checkpoint. Feeding those stale-model errors into a reset detector
would mix checkpoint regimes and could generate repeated events caused by verification latency rather
than by the current model/environment relationship.

The protocol therefore freezes **checkpoint-pure detector epochs**. Each armed detector epoch accepts
only errors whose stored predictions were generated by that epoch's neural checkpoint. A confirmed
event closes the epoch and disarms the detector while the shared neural-response transaction is
outstanding. After a new checkpoint is published, the detector remains without eligible supervised
inputs until labels mature for predictions actually made by that new checkpoint. Old-checkpoint errors
that mature in the meantime remain in provenance/evaluation records but are not fed into the new
detector epoch.

This produces an information-mandated refractory/blind interval rather than an arbitrary cooldown.

An earlier provisional design thought was to set ADWIN's `grace_period` itself to 5,000. That
choice was **rejected before freeze**. Once the delayed-feedback issue was identified, changing
ADWIN's grace period would not directly solve model-version contamination and would add an arbitrary
detector hyperparameter tied to a reused project scale. The primary therefore keeps River's exact
grace_period=10 and handles delayed-feedback purity explicitly at the experiment-control layer.

The detector starts fresh for each seed and is not preloaded with training/development errors. This
avoids creating a development-to-pre detector transition. The synthetic boundary never initializes,
resets, confirms or tunes the detector.

The primary event is interpreted narrowly as a statistically significant change in the mean delayed
neural-error stream. It is not proof that P(Y|X) changed. This terminology is especially important in
the BENIGN-source-regime-dominant primary scenario.

Prospective robustness conditions were frozen without selecting among them on held-out performance:

1. River 0.26.1 Page-Hinkley defaults on the identical delayed hard-error signal and checkpoint-pure
   timing;
2. primary ADWIN defaults on delayed Brier loss, which removes dependence on the fixed hard-decision
   threshold but is explicitly secondary because accepted neural probabilities are uncalibrated;
3. the already frozen label-latency L=0 and L=10,000 timing conditions.

Trigger-quality scoring is also frozen prospectively: pre-reference alarms, first post-boundary
confirmation, end-to-end delay, latency-adjusted descriptive excess delay, repeated events, total
event count, inter-event spacing, epoch input counts, blind duration and suppressed stale-error count.
The evaluator-known boundary is used only after the event log is frozen.

The detector decisions were propagated into `EXPERIMENT_CONTROL_REGISTER.md`,
`STATISTICAL_ANALYSIS_PLAN.md` and `LITERATURE_WATCH.md`.

**Gate after this packet:** primary drift monitor is frozen; adaptive implementation remains
prohibited. The next packet is the shared neural adaptation/replay protocol.


### Shared neural adaptation and replay protocol frozen — 8 October 2026

The project froze `C_D_NEURAL_ADAPTATION_PROTOCOL.md` before any adaptive C/D held-out
execution or adaptive implementation.

The primary neural comparator is deliberately a serious but simple replay-based continual learner.
The goal is to prevent System C from becoming a straw man without turning the paper into a neural
continual-learning method search.

A confirmed drift event opens one shared neural response transaction. The current-evidence budget is
the most recent 10,000 mature labeled stream observations whose original prediction was produced by
the parent checkpoint. If fewer than 10,000 are available at confirmation, the parent remains active
and the detector remains disarmed until that fixed budget becomes available. The budget is not shrunk
to obtain an earlier update. If the stream ends first, the response is right-censored and no terminal
update is forced.

Replay uses two treatment-independent memories:

- immutable 10,000-row uniform training anchor, selection seed 20261008;
- 10,000-row uniform reservoir over adaptively mature stream rows, seed 20261009.

Each update uses 5,000 anchor rows plus 5,000 eligible online-reservoir rows. Current-window row IDs
are excluded from the online replay sample for that transaction. Replay sampling uses seed
`20261010 + event_id`.

The primary update dataset is therefore exactly 20,000 rows: 10,000 current + 10,000 replay.

The accepted binary loss objective is retained with fixed
`BCEWithLogitsLoss(pos_weight=4.138247558496975)`. The positive weight is not recomputed after
drift because doing so would add a second prevalence-dependent adaptation mechanism.

The neural update is:

- all accepted MLP parameters trainable;
- fresh Adam optimizer for every event;
- learning rate 1e-4;
- weight decay 1e-5;
- batch size 1024;
- exactly five epochs;
- no scheduler;
- no early stopping;
- no performance-based checkpoint publication gate;
- CPU and deterministic repository controls;
- shuffle seed `20261011 + 1000*seed + event_id`.

The 1e-4 learning rate is prospectively fixed at one tenth of the original System-A rate as a
conservative fine-tuning step. The smaller batch size is used because the fixed 20,000-row adaptation
dataset would otherwise receive very few optimizer steps under the original 4096-row batch.

A technically valid but performance-degrading update remains part of the evidence. It is not
discarded because it fails to improve a probe or held-out trajectory.

Critically, C and D do not separately train "identical" neural models. The shared control plane
executes the neural update once and creates one versioned child checkpoint. Both C and D literally
reference that same checkpoint hash. Each child records parent checkpoint hash, event/evidence
identities, update configuration, RNG identity and child SHA-256.

This converts neural-side causal matching from a configuration claim into artifact identity.

Catastrophic forgetting is measured explicitly:

- the entire frozen development partition is a historical retention probe after each child
  checkpoint, but it can never influence training, stopping or publication;
- the frozen pre-drift partition may be rescored per checkpoint only offline after the adaptive
  trajectory is fixed, as a retrospective retention diagnostic;
- retention delta and best-to-current forgetting are reported within seed.

A secondary no-replay ablation uses the identical current window and update hyperparameters but omits
replay. It is not a model-selection competitor for the primary trajectory.

The replay decision was informed prospectively by 2025-2026 NIDS continual-learning literature,
including Khraisat & Li (Computer Networks 2025), Costagliola et al. (MILCOM 2025), Delgado et al.
(Applied Soft Computing 2026), and Zhang et al. (INFOCOM 2025). This literature supports replay as a
credible retention mechanism but also shows that replay composition can materially affect behavior.
For that reason the primary uses transparent uniform dual memory rather than task-aware/error-based
selection.

The neural controls were propagated into `EXPERIMENT_CONTROL_REGISTER.md`,
`STATISTICAL_ANALYSIS_PLAN.md`, and `LITERATURE_WATCH.md`.

**Gate after this packet:** the shared detector and shared neural response are prospectively frozen.
Adaptive implementation remains prohibited. The next packet must freeze the matched C/D
operational/fusion threshold policy before symbolic lifecycle design.


### C/D fusion and fixed operating-point policy frozen — 8 October 2026

The project next froze `C_D_FUSION_THRESHOLD_PROTOCOL.md`.

The accepted R0.v2 fusion rule remains the primary C/D operating contract:

- lambda = 0.50 on resolved symbolic coverage;
- neural fallback on uncovered or unresolved conflict;
- seed-specific accepted R0.v2 fused thresholds remain fixed through all later neural checkpoints
  and all D symbolic versions.

The primary thresholds are:

- seed 0: 0.692427396774292
- seed 1: 0.9354645609855652
- seed 2: 0.8299936652183533
- seed 3: 0.9747405052185059
- seed 4: 0.9527904391288757

No per-arm, per-event or per-window threshold recalibration is allowed in the primary C-vs-D
contrast.

This is a causal-isolation choice rather than a claim that the original threshold will remain
deployment-optimal forever. If C and D independently recalibrated from their own fused scores,
symbolic evolution would alter both rule state and future operating point. If a common threshold were
learned from D fused scores, D treatment information would contaminate C. The primary therefore
accepts a potentially stale operating point and reports threshold-free ROC-AUC/AP alongside
thresholded metrics.

The accepted R0.v2 development grid is reused prospectively for fusion-authority sensitivities:

- lambda=.70 with its already frozen per-seed dev-grid thresholds;
- lambda=.90 with its already frozen per-seed dev-grid thresholds.

These are robustness conditions and cannot replace lambda=.50 after adaptive outcomes are observed.

A lambda=1.00 condition is frozen as a causal negative control. Symbolic predictive authority is zero
there. Because C and D share the exact same neural checkpoint chain, their matched fused scores and
thresholded predictions must be identical at lambda=1.00. Any predictive difference is an
implementation defect. Symbolic explanation traces may still differ, but cannot affect the decision.

The detector monitor threshold remains a separate object from the fused operational threshold and is
not changed by this policy.

The threshold controls were propagated into `EXPERIMENT_CONTROL_REGISTER.md` and
`STATISTICAL_ANALYSIS_PLAN.md`.

**Gate after this packet:** stream timing, detector, neural replay adaptation, and fusion/operating
point are all prospectively frozen. Adaptive implementation remains prohibited. The next packet is
the D symbolic lifecycle/operator and online validation protocol.


### D symbolic lifecycle and independent online validation frozen — 8 October 2026

The project froze `D_SYMBOLIC_LIFECYCLE_PROTOCOL.md` before any adaptive symbolic implementation or
C/D held-out execution.

The main methodological decision is that candidate generation and candidate acceptance are separate
causal stages.

For primary D-drift, candidate structures are generated from the same fixed 10,000-row mature
current-evidence window used by the associated shared neural update, but candidate acceptance is
forbidden on those rows. The updated child checkpoint must remain deployed long enough for a
different chronological 10,000-row validation block to be predicted by that child and for those
labels to mature.

If the child checkpoint is superseded before that validation completes, the symbolic transaction
closes as `superseded_before_validation`; generated candidates are preserved for audit but no
partial rule update is published. This prevents a rule base from being validated against a neural
checkpoint that is no longer the active shared predictor.

Candidate generation preserves the R0 extraction family but is versioned for the online evidence
scale:

- DeepExplainer on raw attack logit;
- class-balanced background up to 128 rows/class;
- class-balanced attribution sample up to 1,024 rows/class;
- at least 128 rows/class required for new candidate generation;
- top-12 feature selection under the same normalized SHAP scoring family;
- weighted CART surrogate of the updated child neural decision at the frozen System-A neural
  threshold;
- max_depth=4;
- min_samples_leaf=100 on the fixed 10,000-row generation window;
- equal-total neural predicted-class weights;
- candidate consequent = fitted weighted CART leaf argmax.

The weighted leaf consequent is explicitly frozen because System-B history demonstrated that
unweighted path-row majority is a real implementation defect, not an interchangeable interpretation.

The static R0 `covered>=100` gate was not transferred mechanically. The online validation gate is
sample-size aware:

- support >= .001;
- covered >= 25;
- point class precision >= .80;
- one-sided 95% Wilson lower bound for class precision >= .80;
- point neural fidelity >= .90;
- one-sided 95% Wilson lower bound for fidelity >= .90;
- 100-replicate stratified bootstrap full-gate persistence >= .90;
- complexity <= 4.

The one-sided Wilson z value is 1.6448536269514722. The covered minimum of 25 is directly tied to the
fidelity requirement: below 25 observations, even a perfect observed fidelity cannot establish a .90
one-sided 95% Wilson lower bound.

Existing D rules are evaluated on the same independent validation block **before** candidate
integration. Their immutable pre-resolution state is logged as valid, quality_failed or
evidence_insufficient. The lifecycle then operates as follows:

- active + pass -> retained active;
- active + first completed failure -> demoted/inactive;
- demoted + pass -> reactivated;
- demoted + second consecutive completed failure -> retired;
- retired + later full-gate pass -> may reactivate under the same lineage after current
  redundancy/conflict checks.

This makes retirement reversible under recurring regimes while preventing unsupported rules from
retaining predictive authority indefinitely.

Confidence is refreshed only on completed independent maintenance validation and equals
`min(class_precision, neural_fidelity)`, preserving R0 confidence semantics. There is no per-row
confidence update, decay or pending-label use. System C's accepted R0.v2 confidence is permanently
frozen.

Same-class lifecycle relations reuse previously accepted overlap scales:

- overlap >= .95 -> deterministic merge/consolidation;
- overlap in [.50,.95) -> possible refinement only if the candidate Pareto-dominates the incumbent
  or resolves a documented current stale-rule failure;
- overlap < .50 -> genuinely new addition.

No synthetic antecedent union/intersection is created during merge; the stronger independently
validated rule is retained and losing redundant revisions are logged as merged.

Cross-class overlap >= .50 preserves accepted Pareto/conflict semantics. A dominated candidate is
rejected, a dominated incumbent is demoted, and unresolved opposite-consequent overlap remains
auditable with runtime symbolic abstention/neural fallback.

Every maintenance attempt produces a write-once event artifact. A new rule-base version is published
only when inference-relevant symbolic state changes. Rejected candidates, no-ops, right-censored
transactions and superseded transactions remain first-class evidence.

The future implementation must extend the current static Rule schema with rule-revision identity,
semantic identity, parent revision/lineage links, failure streak, valid-from/valid-to clocks,
generation and validation evidence IDs, child neural checkpoint identity and rule-base parent/hash
chain. Initial R0.v2 semantics are migrated into the expanded schema without alteration.

A symbolic "recovery" claim is now contractually restricted to a documented chain:
earlier valid -> later stale/demoted -> accepted refinement/reactivation/replacement ->
post-publication explanation improvement. A newly added rule with no stale predecessor is not
described as recovery.

The lifecycle decisions were propagated into `EXPERIMENT_CONTROL_REGISTER.md`,
`STATISTICAL_ANALYSIS_PLAN.md`, and `LITERATURE_WATCH.md`.

**Gate after this packet:** the D symbolic evolution operator and online evidence gates are frozen.
Adaptive implementation remains prohibited. The next packet is the D-drift versus D-periodic
trigger-ablation schedule/opportunity budget.


### D-drift versus D-periodic trigger ablation frozen — 8 October 2026

The project froze `D_TRIGGER_ABLATION_PROTOCOL.md` after the symbolic lifecycle operator had been
frozen.

The purpose is to test whether the **trigger policy** adds value, not merely whether rule maintenance
can help.

D-drift and D-periodic therefore share:

- accepted seed-matched R0.v2 start state;
- exact shared neural checkpoint trajectory;
- symbolic candidate-generation algorithm;
- independent 10,000-row validation contract;
- uncertainty gates;
- lifecycle transitions;
- conflict/abstention rules;
- fusion/threshold policy;
- symbolic RNG namespace by seed/opportunity.

Only the symbolic maintenance opportunity timing differs.

A common maximum symbolic opportunity budget of four slots per seed is frozen for both trigger arms.
Every triggered/scheduled opportunity consumes a slot regardless of whether it produces a rule-base
publication, a validated no-op, insufficient evidence, checkpoint supersession, right-censoring or a
pending-transaction skip. There is no retry beyond the four-slot budget.

D-drift consumes its first four symbolic slots from the first four confirmed primary detector events.
Later drift events may continue to drive the already-frozen shared neural trajectory, but no fifth
D-drift symbolic maintenance opportunity is permitted.

D-periodic does not consult the drift detector for scheduling. With total primary stream length
N=138,530, the fixed target clocks are:

- 27,706
- 55,412
- 83,118
- 110,824

These equal floor(i*N/5), i=1..4.

The schedule was derived from the frozen stream length and the symbolic evidence footprint:
10,000 retrospective generation rows + 10,000 future validation rows + 5,000-row label delay =
a nominal 25,000-row maintenance footprint. Four interior fifth-spaced opportunities produce
approximately 27,706-row spacing. A five-opportunity six-segment schedule would produce only
approximately 23,088-row spacing and systematically overlap that nominal footprint.

This derivation did not use the evaluator-known synthetic boundary at 69,260; none of the periodic
target clocks equals the boundary.

At a periodic target clock, ordinary row prediction, label maturity and any shared detector/neural
control-plane action at that clock complete first. The periodic opportunity opens last and snapshots
the neural checkpoint effective for the next logical prediction. Its generation evidence is the most
recent 10,000 mature stream rows available at the target clock, evaluated using that current shared
checkpoint. Candidate acceptance then uses the same future checkpoint-pure 10,000-row validation
contract as D-drift.

If the checkpoint is superseded during validation, the periodic transaction aborts without partial
publication and the next periodic clock is not moved. At most one symbolic transaction may be
outstanding per trigger arm/seed. A later periodic target that arrives while a prior periodic
transaction remains pending is logged as `pending_transaction_skip` and still consumes its slot.

The analysis now distinguishes symbolic opportunity, completed validation, publication, no-op and
censored/aborted transaction. These counts may not be conflated. Trigger quality will be evaluated
using both recovery/effectiveness and maintenance efficiency/cost.

**Gate after this packet:** the symbolic lifecycle and mandatory drift-vs-periodic trigger ablation
are prospectively frozen. Adaptive implementation remains prohibited. The next packet is the final
statistical/runtime/reproducibility freeze and fail-closed implementation contract.


### Final C/D statistical, runtime, reproducibility, and held-out-access freeze — 8 October 2026

The project froze `C_D_FINAL_ANALYSIS_REPRODUCIBILITY_PROTOCOL.md` and promoted
`STATISTICAL_ANALYSIS_PLAN.md` to version 1.0 before any adaptive C/D held-out execution.

This packet deliberately resolves the remaining inferential and execution degrees of freedom rather
than leaving them to implementation time.

The primary confirmatory family contains exactly three seed-paired whole-post-regime endpoints:

1. D-drift minus C post-regime MCC;
2. D-drift minus C post-regime macro correct symbolic coverage (MCSC);
3. D-drift minus D-periodic post-regime MCSC.

For class c, correct symbolic coverage is the proportion of true class-c rows receiving a resolved
correct symbolic prediction. Uncovered rows, unresolved conflict/abstention, and wrong symbolic
predictions contribute zero. MCSC is the unweighted mean of benign and attack correct symbolic
coverage. Component coverage/correctness/conflict metrics remain mandatory so the composite cannot
hide class-specific trade-offs.

The full frozen 69,270-row post partition is the confirmatory domain. No rows are removed because an
update had not yet occurred. This makes detector delay, evidence waiting, no-op maintenance,
right-censoring and late publication part of the realized treatment effect rather than post-hoc
exclusions.

For each confirmatory endpoint, the primary effect estimate is the arithmetic mean of the five
matched seed differences. The primary interval is the 95% Student-t interval over the five paired
differences with df=4. This interval is explicitly restricted to stochastic-seed variability
conditional on the one fixed scenario and is not presented as deployment-population uncertainty.

Because n=5 cannot support meaningful normality diagnostics, the plan mandates all five raw paired
effects, median, SD, min/max, positive/zero/negative sign counts and the leave-one-seed-out mean-effect
range alongside the interval. Bootstrap intervals are not primary.

A one-sided exact sign test is frozen as secondary calibration for each of the three positive-benefit
contrasts. Zero differences are removed from its denominator and the effective n is reported.
Holm-Bonferroni controls the three-test family at FWER .05. The plan explicitly rejects p-value
crossing as the sole success criterion because five matched seeds share the same underlying stream
and produce a coarse attainable p-value grid.

No confirmatory window-level mixed model/GEE is used in the primary scenario. Reporting windows are
longitudinal mechanism units, not extra replicates.

Secondary recovery uses a frozen rule: the pre-reference baseline is the row-count-weighted mean of
the final three pre-drift reporting windows. A higher-is-better metric recovers only at the first post
window at or above that baseline whose immediately following post window is also at or above it;
lower-is-better metrics reverse the inequality. Otherwise recovery is right-censored. Symbolic
"recovery" additionally requires the lifecycle evidence chain already frozen in the symbolic
protocol.

Scientific no-update outcomes are not missing data. No detector event, no symbolic publication,
validated no-op, budget exhaustion, checkpoint supersession and right-censored symbolic validation
remain part of the realized trajectory. A technical/protocol failure can be rerun only with preserved
failed evidence, a documented invalidating defect/fault and a new run identity. The five-seed
confirmatory family is not silently reduced to n=4.

The robustness set is now explicit: L=0/L=10,000; Page-Hinkley; ADWIN-Brier; no-replay; lambda
.70/.90/1.0; 2,500/10,000-row longitudinal window sensitivities; and a static-style symbolic
support/count gate without Wilson bounds. Primary results cannot be replaced by a favorable
sensitivity.

Primary runtime is frozen to CPU with Python 3.11.9 and the requirements lock. Before numerical
library initialization, PYTHONHASHSEED=0 and OMP/MKL/OpenBLAS/NumExpr thread counts are set to one.
PyTorch intra/inter-op thread counts are one, deterministic algorithms are requested and DataLoader
workers remain zero. `threadpoolctl.threadpool_info()` is recorded and a detected numerical pool
violating the single-thread contract blocks primary execution.

Write-once evidence families are now frozen for run manifests, shared control-plane events,
checkpoint lineage, arm prediction tables, symbolic maintenance events, rule revisions/versions and
metrics/evaluation evidence.

Ten fail-closed verifier families are prospectively required:

- shared C/D control-plane artifact identity;
- information timing;
- checkpoint purity;
- fusion/threshold identity;
- exact lambda=1 predictive equality;
- symbolic generation/validation separation;
- trigger-arm operator identity and exact periodic clocks;
- symbolic lifecycle integrity;
- no synthetic-boundary contamination;
- write-once/hash integrity.

The implementation test matrix must cover these controls using toy/generated fixtures and permitted
training/development evidence before primary pre/post adaptive execution.

The implementation sequence is also frozen:

1. accept this design milestone into main and annotate `cd-design-freeze-v1`;
2. `stage6-cd-control-plane` implements shared timing/detector/replay/neural/checkpoint/evidence
   infrastructure without primary pre/post adaptive execution;
3. `stage7-cd-symbolic-lifecycle` implements symbolic lifecycle, periodic trigger arm, evaluators,
   analysis builders and remaining verifiers, still without primary pre/post adaptive execution;
4. after acceptance/tagging as `cd-implementation-ready-v1`, create
   `stage8-cd-primary-evaluation`.

The held-out access gate requires SAP v1.0, no material C/D control-register TBD, local and CI tests
green on the exact implementation-ready head, all five System-A checkpoint bytes/hash verification,
scenario/preprocessing verification, causal-verifier tests, a committed primary run/config manifest,
clean worktree and no unresolved outcome-sensitive parameter.

Primary held-out execution itself is two-phase. First, generate and freeze one shared detector/neural
control-plane trajectory per seed. Only after those artifacts are hash-frozen do C, D-drift and
D-periodic consume them. This makes matched neural adaptation an immutable artifact identity and
prevents any symbolic arm from feeding back into drift events, replay or checkpoint timing.

After any adaptive held-out output has been inspected, poor performance, sparse events, harmful
forgetting or trigger direction cannot justify retuning. Realized implementation defects are handled
by preserved failed evidence and versioned correction; design limitations become sensitivities or
future work.

The Research Contract workflow was strengthened prospectively to require all Stage-5 C/D protocol
artifacts, SAP v1.0, absence of unresolved C/D analysis TBD markers and absence of unresolved
control-register freeze-state rows.

**Gate after this packet:** the prospective C/D design is complete. Adaptive implementation may
begin only after this design branch is accepted into main and tagged `cd-design-freeze-v1`.
Adaptive held-out execution remains prohibited until the later `cd-implementation-ready-v1` gate.


### Stage 6 shared control-plane implementation tranche opened — 8 October 2026

Stage 6 was created from accepted design-freeze milestone
`cd-design-freeze-v1` / `6f677a2115a1f8d9cbe8e2a3f46d877a01d29f27`.

No primary adaptive pre/post stream execution was authorized or performed in this tranche.

The first implementation tranche added dataset-agnostic modules:

- `cd_control_plane.py`: delayed-label queue, uniform mature-history reservoir,
  fixed current/replay selection, checkpoint-pure ADWIN wrapper, deterministic neural
  adaptation, state hashing, write-once checkpoint/JSON helpers, and causal verifiers;
- `cd_evidence.py`: event envelopes, JSONL evidence, checkpoint lineage,
  shared identity, run-manifest and file-hash verification;
- `cd_runtime.py`: frozen environment/thread/determinism checks;
- `cd_shared_runner.py`: shared trajectory state machine consuming only caller-supplied
  ordered rows and a frozen anchor.

The shared runner deliberately contains no scenario loader and no primary pre/post execution command.

Its label-access surface was tightened during implementation: after prediction-time insertion into
the delayed-label queue, the ordinary stream feature store retains features only. Stream labels used
by replay/update logic are obtained from mature-label records rather than from the caller's
arrival-time row object.

The toy/generated test suite now exercises prediction-before-label-release, terminal censoring,
deterministic reservoir/replay selection, current/replay disjointness, checkpoint-pure detector
epochs, ADWIN configuration, information-time failures, shared-identity failures, synthetic-boundary
field rejection, deterministic child-state reproduction, write-once artifacts, checkpoint
lineage, manifest corruption detection, a full toy detector->neural-publication trajectory,
self-verification/tamper rejection, frozen runtime variables, and a static scenario-loader firewall.

Research Contract CI was extended to execute the Stage-6 tests and require
`STAGE6_CONTROL_PLANE_IMPLEMENTATION.md`.

Draft PR #4 was opened as the Stage-6 review/CI surface. It remains draft.

This implementation does not change any frozen Stage-5 timing, detector, replay, optimizer,
threshold, endpoint, or inferential choice. Small test-only `ControlPlaneConfig` overrides exist
solely to keep toy unit tests fast; the primary defaults remain the frozen values.

**Gate remains locked:** Stage 6 must pass exact-head CI and final implementation audit before
acceptance into main. Primary adaptive pre/post execution remains prohibited through Stage 7 and
until `cd-implementation-ready-v1`.
