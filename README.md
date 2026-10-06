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

`RESEARCH_DOCTRINE.md` is the repository-visible summary of the governing project sources. `MAIN - Concept_Drift_NIDS_Research_Gap_Doctrine.docx` remains the highest scientific authority; `Reconciled_Pre-Stage_3_and_Stage_3_Implementation_Plan.docx` is the authoritative operational protocol where it does not conflict with MAIN.

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

Before later adaptive evaluation, the project must freeze the common longitudinal window policy, drift/adaptation controls, label-availability assumptions, rule/fusion controls, and the confirmatory statistical-analysis choices recorded as unresolved in the control register and statistical-analysis plan.

After the longitudinal window policy is frozen, the existing System-A checkpoints should be rescored over those common windows without retraining or retuning so A/B/C/D share the same temporal evaluation grid.

## Research milestone workflow

`main` is intended to represent the latest fully accepted scientific milestone. New major stages should branch from accepted `main`, pass their scientific gate and CI, then return through a pull request. See `REPOSITORY_GOVERNANCE.md` for the merge/tag/deviation policy.

