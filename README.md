# Concept-Drift IDS

Research code for an adaptive neuro-symbolic network intrusion-detection system with concept-drift-driven symbolic rule evolution.

## Environment

The project is frozen to:

- Python **3.11.9 exactly**
- dependency versions in `requirements-lock.txt`

Do not substitute another Python or change dependency versions to make a run succeed.

## Local setup

From the repository root:

```bash
python --version
# must print: Python 3.11.9

python -m venv .venv
# activate .venv with the command appropriate for your shell
python -m pip install --upgrade pip
python -m pip install -r requirements-lock.txt
```

The test configuration adds `src/` to the Python path automatically.

## Frozen Stage-1 / Stage-2 artifacts

Generated data and result files are intentionally ignored by Git. A local run therefore needs the original CICIDS2017 CSV files under:

```text
data/raw/cicids2017/
```

The frozen project code reconstructs generated artifacts from those source files. Existing Stage-1/Stage-2 artifacts should be retained locally when already generated.

## Pre-Stage 3 status

`PRE_STAGE_3_READINESS.md` records the frozen implementation decisions.

`GOVERNING_SOURCES.md` pins the exact SHA-256 identities of the two governing project-source documents. `RESEARCH_DOCTRINE.md` is the repository-visible summary of those governing sources. `MAIN - Concept_Drift_NIDS_Research_Gap_Doctrine.docx` remains the highest scientific authority; `Reconciled_Pre-Stage_3_and_Stage_3_Implementation_Plan.docx` is the authoritative operational protocol where it does not conflict with MAIN.

Forward experimental control is tracked in `EXPERIMENT_CONTROL_REGISTER.md` and `STATISTICAL_ANALYSIS_PLAN.md`. Repository milestone/merge discipline is recorded in `REPOSITORY_GOVERNANCE.md`.

## Stage-3 execution

First run the regression suite:

```bash
python -m pytest -q
```

Then run the Stage-3A preprocessing acceptance pass:

```bash
python run.py stage3a-preprocess
```

The acceptance pass:

1. reconstructs the frozen `sudden_benign_v1` scenario;
2. fits median imputation on training only;
3. fits `StandardScaler` on imputed training only;
4. transforms all four partitions serially using the frozen state;
5. verifies finite outputs; and
6. writes the small provenance artifact
   `data/manifests/sudden_benign_v1_preprocessing_v1.json`.

Large transformed matrices are not persisted.

## Notebook / cloud execution

The code avoids machine-specific paths and can run in a notebook or remote VM from the repository root. The root `run.py` bootstraps the `src/` layout using only the Python standard library, so no editable package install or custom `PYTHONPATH` is required. The runtime must still be **Python 3.11.9 exactly**. A hosted notebook whose fixed runtime is a different Python version is not an equivalent project environment; use a custom runtime/container or another service that can provide 3.11.9.

## Stage 3B — System A

Stage 3A has been execution-validated under Python 3.11.9. The accepted preprocessing state is committed at:

`data/manifests/sudden_benign_v1_preprocessing_v1.json`

The frozen System-A protocol is documented in `SYSTEM_A_PROTOCOL.md`.

Run the repo-only System-A tests first:

```bash
python -m pytest -q tests/test_system_a_unit.py
```

Then perform a one-seed smoke training run:

```bash
python run.py system-a train --seeds 0 --device auto
```

If that succeeds, complete the remaining frozen seeds:

```bash
python run.py system-a train --seeds 1,2,3,4 --device auto
```

Local checkpoints and seed records are written under `artifacts/system_a/` and are intentionally ignored by Git.

After all five seeds complete, the runner creates:

`data/manifests/system_a_v1.json`

Commit that small manifest **before** looking at pre/post results. It freezes the neural starting states, development-selected thresholds, checkpoint hashes, and model-development protocol.

Only after that manifest is committed should the static System-A pre/post evaluation run:

```bash
python run.py system-a evaluate --device auto
```

Evaluation output is written under `results/frozen/system_a_v1/` and does not alter the frozen model-development state. These compact JSON/CSV summaries are intentionally trackable in Git; model checkpoints remain ignored.

The evaluation produces an integrity manifest plus:

- `evaluation_manifest.json` — hashes and identities for every frozen evaluation output;
- `static_evaluation.json` — complete nested record;
- `metrics_by_seed.csv` — long-form per-seed metrics;
- `aggregate_metrics.csv` — mean, SD, and 95% CI by metric/partition;
- `paired_deltas_by_seed.csv` — per-seed post-minus-pre changes;
- `aggregate_paired_deltas.csv` — aggregate paired changes with uncertainty;
- `training_history.csv` — epoch-level training loss and development AP.

The CSV schemas include system/scenario identifiers so equivalent outputs from later systems can be concatenated directly for plots and comparisons.

## Current implementation boundary

System A is complete and frozen as the static-neural reference.

Accepted identities:

- preprocessing core state: `4527f77220f2cf6063108a7d71d80aaa0e82099ad282ff25408a2d9ce3488b1e`
- System-A manifest: `42004b5ed100b690023b9998bdc959fac41ab947b996fb7c58e44cee5e8dc6de`
- System-A evaluation manifest: `e721b641b5898976c76c0449dedf7152cb302be4447604525afb7ddf1c94c5b3`

The frozen evaluation lives under `results/frozen/system_a_v1/`.

A separately versioned evidence supplement under
`results/frozen/system_a_v1_supplement_v1/` records exact per-seed TP/TN/FP/FN,
sample counts, and attack prevalence. It is derived losslessly from the frozen
recall/FPR values and frozen partition class counts; the original evaluation
files are unchanged.

Before later adaptive evaluation, the project must freeze the common longitudinal window policy, drift/adaptation controls, label-availability assumptions, rule/fusion controls, and the confirmatory statistical-analysis choices recorded as unresolved in the control register and statistical-analysis plan.

Verify the accepted System-A evidence locally without loading pre/post partitions:

```bash
python run.py system-a verify
```

The verifier checks the frozen System-A manifest, seed/checkpoint identities, current preprocessing/scenario identity, evaluation manifest self-hash, and every referenced compact result-file hash.

After the longitudinal window policy is frozen, the existing System-A checkpoints should be rescored over those common windows without retraining or retuning so A/B/C/D share the same temporal evaluation grid.

## Research milestone workflow

`main` is intended to represent the latest fully accepted scientific milestone. New major stages should branch from accepted `main`, pass their scientific gate and CI, then return through a pull request. See `REPOSITORY_GOVERNANCE.md` for the merge/tag/deviation policy.



## Stage 4 — System B static neuro-symbolic baseline

The prospective System-B protocol is frozen in `SYSTEM_B_PROTOCOL.md`. System B reuses each accepted System-A checkpoint unchanged and derives a seed-matched validated `R_0^(s)` using training/development evidence only.

The required local sequence is deliberately gated:

```bash
git switch stage4-system-b
git pull --ff-only
python --version
python -m pytest -q
python run.py system-a verify

# The common reporting grid is now frozen. Re-score accepted System A
# without retraining or rethresholding and preserve it as a separate supplement.
python run.py system-a rescore-windows --device cpu

# Freeze the additive System-A longitudinal supplement before System-B build.
git add results/frozen/system_a_v1_longitudinal_v1
git commit -m "Freeze System A longitudinal v1 rescore"
python run.py system-a verify

# Training + development only. This must not load pre/post.
python run.py system-b build --device cpu

# Inspect the generated freeze:
#   data/rules/system_b_r0_v1/seed_0.json ... seed_4.json
#   data/manifests/system_b_v1.json
#
# Commit those exact rule/manifests before any held-out evaluation.

git add data/rules/system_b_r0_v1 data/manifests/system_b_v1.json
git commit -m "Freeze validated System B R0"
python run.py system-b verify

# Only after the freeze commit:
python run.py system-b evaluate --device cpu
```

The evaluator refuses to run from a dirty worktree and refuses to overwrite an existing accepted evaluation. It records detection counts/metrics, resolved symbolic coverage, raw activation coverage, conflict-abstention, neural fidelity, per-rule pre/post support/precision/fidelity/stability/activation, and the frozen 5,000-row longitudinal reporting grid.

Do not relax rule gates, change fusion settings, or regenerate `R_0` because held-out results are inconvenient. A genuine defect requires a new documented version.


### System-B frozen evaluation chronology correction

The authoritative first System-B held-out evaluation is the immutable first run recorded by
`results/frozen/system_b_v1/evaluation_manifest.json` (manifest SHA-256
`f44cad2ed9674bcb7118f05f174f845b5dfb135f95e2cb2b4a230f0f998c3e42`).
Do not rerun or overwrite it.

After pulling the chronology-correction commit and confirming a clean worktree, generate only the additive publication-table supplement:

```bash
python run.py system-b supplement
python run.py system-b verify-supplement
```

This supplement reads only the committed frozen System-B CSV evidence. It does not load raw pre/post data or model checkpoints. Commit the resulting
`results/frozen/system_b_v1_supplement_v1/` directory unchanged.


### System-B Q1 protocol-conformance audit

System B is under an adversarial pre-C/D scientific audit. Before treating R0.v1 as closed, run the training-only consequent-semantics diagnostic on the local machine that holds the frozen System-A checkpoints:

```bash
python run.py system-b audit-r0-protocol
```

Expected output always includes:

```text
development_loaded=false
pre_post_partitions_loaded=false
```

The command writes `results/audits/system_b_r0_protocol_audit_v1.json`. It does not evaluate or reload the held-out pre/post partitions. Commit that audit artifact unchanged and do not rebuild or replace R0 based on performance.
