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
