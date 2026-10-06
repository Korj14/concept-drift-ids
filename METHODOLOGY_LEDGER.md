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
