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

`RESEARCH_DOCTRINE.md` is a repository-visible pointer to the governing project doctrine. The source Word document `MAIN - Concept_Drift_NIDS_Research_Gap_Doctrine.docx` remains the highest scientific authority.

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

## Current implementation boundary

System A must not be trained until the Stage-3A reconstruction and preprocessing tests pass.
