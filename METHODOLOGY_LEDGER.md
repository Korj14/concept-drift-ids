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
