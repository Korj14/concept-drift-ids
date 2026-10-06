# System A Protocol — Static Neural Baseline

**Status:** FROZEN, EVALUATED, AND CLOSED  
**Python:** 3.11.9 exactly

System A is the static neural baseline. It contains no symbolic rules, drift detector, or adaptation.

## Inputs

- Scenario: `cicids2017_sudden_benign_v1`
- Features: exact frozen 77-feature order
- Preprocessing: accepted Stage-3A artifact `data/manifests/sudden_benign_v1_preprocessing_v1.json`
- Training partition: model fitting only
- Development partition: early stopping and decision-threshold selection only
- Pre/post partitions: prohibited during model development; evaluation only after the System-A manifest is frozen

## Fixed model

- MLP: `77 -> 128 -> 64 -> 1`
- Hidden activation: ReLU
- Dropout: 0.10 after each hidden layer
- Explicit Kaiming-uniform initialization for hidden/output weights; zero biases
- Output: one binary logit
- Probability calibration: none in the primary System-A baseline

The architecture is intentionally compact because neural architecture novelty is not part of the research contribution.

## Fixed training protocol

- Loss: `BCEWithLogitsLoss`
- Positive-class weight: training BENIGN count / training attack count
- Optimizer: Adam
- Learning rate: 0.001
- Weight decay: 0.00001
- Batch size: 4096
- Maximum epochs: 20
- Early-stopping metric: development average precision
- Patience: 3 epochs
- Minimum improvement: 0.0001
- DataLoader workers: 0
- Fixed seeds: 0, 1, 2, 3, 4
- Device consistency: all five seeds in the primary System-A run use the same compute backend. Seed 0 resolved to CPU, therefore seeds 1–4 are also executed on CPU for this run.

Each seed saves its best development checkpoint. Later Systems B/C/D must reuse the corresponding neural starting checkpoint when a matched initial neural state is required.

## Decision threshold

For each seed, choose the binary decision threshold on development predictions only.

Primary threshold objective: maximize MCC.

Deterministic tie-break order:

1. higher MCC;
2. higher F1;
3. lower FPR;
4. threshold closest to 0.5.

The selected threshold is frozen before pre/post evaluation.

## Development metrics

Record:

- precision
- recall
- F1
- FPR
- MCC
- ROC-AUC
- average precision

## Artifacts

Local checkpoints and per-seed records live under `artifacts/system_a/` and are not committed.

After all five seeds are complete, generate:

`data/manifests/system_a_v1.json`

That small manifest is the auditable frozen System-A starting-state record and may be committed.

## Evaluation gate

The pre/post evaluation command must refuse to run unless the complete five-seed System-A manifest exists and every referenced checkpoint hash still matches.

No architecture, optimizer, early-stopping, class-weighting, or threshold decision may be changed after looking at pre/post metrics without declaring a new protocol version.


## Accepted evaluation closure

The first untouched pre/post evaluation was executed only after the five-seed `system_a_v1.json` manifest was committed and checkpoint hashes were verified.

Accepted evaluation manifest:

`results/frozen/system_a_v1/evaluation_manifest.json`

Manifest SHA-256:

`e721b641b5898976c76c0449dedf7152cb302be4447604525afb7ddf1c94c5b3`

System A is now a fixed reference condition. It must not be retrained, recalibrated, rethresholded, or selectively reseeded in response to its observed pre/post results. Any scientifically justified alternative requires a new protocol/version and preservation of this accepted baseline.

After the common longitudinal windowing policy is frozen, these already-frozen checkpoints may be **rescored** on the common windows without retraining or retuning.
