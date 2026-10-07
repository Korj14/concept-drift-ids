# System B v2 Corrected Evaluation Protocol

**Status:** PROSPECTIVELY FROZEN BEFORE CORRECTED V2 PRE/POST EXECUTION  
**Date:** 7 October 2026  
**Accepted symbolic state:** R0.v2  
**R0.v2 manifest SHA-256:** `131027d2f136494eb388183f18dcb7eb0e9d7e9fe786f22dba25f4e1624c1483`

## 1. Scientific status

This evaluation is a deterministic implementation-defect correction.

It is **not** an untouched first-look evaluation because the historical R0.v1 pre/post outcomes are already known. The treatment/configuration of R0.v2 was nevertheless frozen without using those held-out outcomes:

- the defect was diagnosed from training-only reconstruction;
- the correction reused the original training/development identities and gates;
- the seven corrected consequents were determined mechanically by the weighted CART leaf class;
- all seven corrected candidates failed the pre-existing validation gates;
- lambda and fused thresholds were reselected on the original development fusion slice only;
- R0.v2 was frozen and CI-accepted before this corrected evaluation.

R0.v2 is the required future C/D initial symbolic state regardless of the results below.

## 2. Evaluation data firewall

The corrected evaluator may load only:

- `pre_drift`;
- `post_drift`.

It must not load training or development.

The evaluator must not read the historical System-B v1 evaluation or supplement. V1 is compared with v2 only later through a separate derived-analysis step after v2 evidence is frozen.

## 3. Frozen model and inference controls

For each seed 0–4:

- use the same accepted System-A checkpoint;
- use the accepted frozen preprocessing state without refit;
- use the accepted seed-specific R0.v2 artifact;
- use global neural weight `lambda=0.50`;
- use the frozen R0.v2 fused threshold for that seed;
- no neural retraining, calibration, threshold retuning, rule modification or adaptation.

The evaluator runs on CPU and requires Python 3.11.9.

## 4. Detection evidence

Per seed and partition record:

- sample count, benign/attack count and prevalence;
- TN, FP, FN, TP;
- precision, recall, F1, FPR, MCC, ROC-AUC, average precision;
- accuracy and balanced accuracy as secondary descriptive metrics.

Write System-A-compatible long-form seed, aggregate, paired-delta and aggregate paired-delta tables.

Five-seed intervals are conditional on this scenario and quantify seed variability, not independent deployment environments.

## 5. Explanation evidence

Record the original aggregate symbolic quantities:

- resolved coverage;
- raw activation coverage;
- uncovered rate;
- conflict-abstention rate;
- symbolic-to-neural fidelity among resolved covered observations.

Additionally, because the Q1 audit showed that aggregate fidelity can conceal attack-side weakness, prospectively record:

- BENIGN resolved coverage;
- attack resolved coverage;
- BENIGN symbolic correctness among resolved BENIGN rows;
- attack symbolic correctness among resolved attack rows;
- class-conditional symbolic-to-neural fidelity.

These are descriptive explanation outcomes, not new tuning objectives.

## 6. Rule-level staleness

For every active R0.v2 rule and each partition record:

- support;
- covered count;
- class precision;
- neural fidelity;
- bootstrap gate-persistence stability;
- complexity;
- activation rate.

Write a direct pre-to-post rule-staleness table preserving raw pre, post and delta values and frozen-gate pass/fail transitions.

No composite staleness score is introduced.

## 7. Imputation-aware explanation diagnostic

The primary preprocessing remains unchanged.

For every rule/partition, use the raw pre-imputation feature frame only to record whether an activated rule relied on at least one antecedent feature that was missing and therefore median-imputed.

Record:

- imputed-antecedent activation count;
- fraction of that rule's activations involving an imputed antecedent;
- rule support/covered count/class precision/neural fidelity after excluding such activations.

This is a diagnostic only. It does not alter any primary prediction or explanation.

## 8. Longitudinal evidence

Use the already-frozen common reporting grid:

- 5,000 rows;
- stride 5,000;
- pre/post partition boundary aligned;
- final remainder policy unchanged.

Record the detection and aggregate/class-conditional symbolic metrics on every window.

Windows remain repeated dependent observations and are not inferential replicates.

## 9. Computational evidence

The historical v1 timing was a single symbolic+fusion timing and is not a strong benchmark.

For v2:

- record the actual single neural-inference duration descriptively;
- record symbolic+fusion latency using 1 untimed warm-up plus 5 timed repeats on the same fixed partition/seed input;
- require every repeat to reproduce the primary symbolic statuses and fused scores;
- report median, minimum, maximum, 25th and 75th percentile;
- record torch intra/inter-op thread counts;
- record threadpoolctl inventory;
- record OMP/MKL/OpenBLAS/NUMEXPR thread environment variables.

These timings remain descriptive and should not be generalized across hardware. The same instrumentation convention should later be reused for matched C/D cost comparisons.

## 10. Immutable outputs

Write once to:

`results/frozen/system_b_v2_corrected_v1/`

Required files:

- `detection_by_seed.csv`;
- `metrics_by_seed.csv`;
- `aggregate_metrics.csv`;
- `paired_deltas_by_seed.csv`;
- `aggregate_paired_deltas.csv`;
- `rule_quality_by_seed_partition.csv`;
- `rule_staleness_deltas.csv`;
- `window_metrics.csv`;
- `runtime_by_seed_partition.csv`;
- `system_b_v2_evaluation.json`;
- `evaluation_manifest.json`.

The directory is write-once. A verifier must validate all hashes without loading pre/post data.

## 11. Interpretation firewall

After the corrected evaluation:

- do not modify R0.v2, lambda, thresholds or preprocessing;
- do not choose between R0.v1 and R0.v2 based on held-out performance;
- R0.v2 remains the C/D initial symbolic state;
- any v1-v2 comparison is labeled implementation-correction sensitivity/provenance, not model selection;
- mixed or worse corrected results remain valid evidence.
