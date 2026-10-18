# Stage 9.5-6 Historical Replay Execution Handoff

**Status:** EXECUTION HANDOFF / BLOCKED BY EXTERNAL ARTIFACT RECOVERY  
**Date frozen:** 17 October 2026  
**Scientific semantics changed:** no  
**Stage-10 access authorized:** no

## Purpose

This handoff joins the already-frozen Stage-9.5-1 recovery verifier, replay-equivalence v1.1 procedure, deterministic Phase-A/B/C comparator, replay-report finalizer, and work-package order gate into one operator sequence.

It is **not** a new scientific protocol. If this handoff conflicts with the frozen replay-equivalence contract or machine manifests, the frozen machine/protocol artifacts control.

The remaining prerequisites are external only:

- `system_a_checkpoint_bytes_missing`;
- `stage8_large_artifact_archive_missing`.

The Stage-1 historical reconstruction prerequisite is already closed by:

`results/audits/stage9_5_full_seed_rerun_v1/stage1_reconstruction_report.json`

with canonical SHA-256:

`4bafa772f9737d934f40c90bf7be8d80a62108cf89a9c74895fbe5c12c4a88af`.

## 0. Non-negotiable identities

Historical Phase-A/B execution head:

`bfa14b942e4a5b2fbfa8aa3c43728a7f1cd81645`

Historical Phase-C correction source:

`79ddc4c6d6dea52c7cabc55a6d082448fc24fcf9`

Accepted Stage-8 evidence commit:

`c2ded83b8195b9321e715626c1f305f9627936e8`

Accepted correction manifest SHA-256:

`d380fce5f9db8f0b639dc999298a263b10a10a3d02e35def226a121d098e2222`

System-A checkpoint paths inside the historical replay worktree:

- `artifacts/system_a/checkpoints/seed_0.pt`
- `artifacts/system_a/checkpoints/seed_1.pt`
- `artifacts/system_a/checkpoints/seed_2.pt`
- `artifacts/system_a/checkpoints/seed_3.pt`
- `artifacts/system_a/checkpoints/seed_4.pt`

Their exact accepted SHA-256 values remain those frozen in `data/manifests/system_a_v1.json`. No retraining, reserialization, or substitute checkpoint is allowed.

The recovered accepted Stage-8 archive must represent the original root:

`artifacts/cd_primary_v1`

and must satisfy all 145 descriptor-linked requirements of Stage-9.5-1 v1.2.

## 1. Choose the assurance audit head

After both external artifact families are available, select the current assurance-branch head as the replay **audited head** `H`.

Before replay closure:

- Stage-9 robustness must complete successfully on exactly `H`;
- no Stage-10 outcome may be accessed;
- no replay-comparator, projection, or finalizer semantics may be changed after fresh replay outcomes are observed.

The eventual closure/evidence commits may be descendants of `H`; the order gate requires `H` to remain an ancestor and requires the same-head Stage-9 success to name `H`.

## 2. Verify the recovered external artifacts first

From a clean Python-3.11.9 historical-runtime checkout of the assurance branch:

```bash
python tools/stage9_5/fresh_clone_reconstruction.py \
  --output-dir results/audits/stage9_5_full_seed_rerun_v1 \
  --checkpoint-root <directory-containing-seed_0.pt-through-seed_4.pt> \
  --stage8-archive-root <recovered-original-artifacts-cd_primary_v1-root>
```

Do not continue unless the verifier-produced
`fresh_clone_reconstruction_report.json` has:

- `pass = true`;
- `failures = []`;
- `blockers = []`;
- verified checkpoint seeds `[0,1,2,3,4]`;
- Stage-8 archive `requirement_count = 145`;
- Stage-8 archive `verified_count = 145`.

Preserve that report unchanged. Do not commit the recovered heavy bytes.

## 3. Create the historical Phase-A/B worktree

Create a clean worktree at exactly:

`bfa14b942e4a5b2fbfa8aa3c43728a7f1cd81645`.

Example:

```bash
git worktree add <ab-worktree> bfa14b942e4a5b2fbfa8aa3c43728a7f1cd81645
```

Use Python **3.11.9**, the frozen dependency lock, and the frozen single-thread environment:

```text
PYTHONHASHSEED=0
OMP_NUM_THREADS=1
MKL_NUM_THREADS=1
OPENBLAS_NUM_THREADS=1
NUMEXPR_NUM_THREADS=1
```

Place the five exact recovered System-A checkpoint files at the frozen checkpoint paths under `<ab-worktree>`.

## 4. Materialize Stage-1 interim tables for historical execution

The authoritative Stage-1 closure report is already preserved and must not be replaced.

For the fresh historical rerun, materialize the interim tables into:

`<ab-worktree>/data/interim/cicids2017`

using the frozen Stage-1 verifier/contract under Python 3.11.9 and the same eight raw CSV identities. A temporary operational report path may be used; it is **not** a replacement for the already-preserved authoritative Stage-1 report.

The resulting interim tables are execution inputs. Gzip container bytes are not promoted to scientific identity; the frozen Stage-1 semantic/reconstruction contract remains authoritative.

## 5. Run all five Phase-A seeds

At exact historical head `bfa14...`, with a clean tracked worktree and required external inputs present:

```bash
python run.py cd-primary-phase-a --seed 0
python run.py cd-primary-phase-a --seed 1
python run.py cd-primary-phase-a --seed 2
python run.py cd-primary-phase-a --seed 3
python run.py cd-primary-phase-a --seed 4
```

Do not run Phase B until all five Phase-A seeds complete and verify.

The fresh outputs must remain under:

`<ab-worktree>/artifacts/cd_primary_v1/phase_a_shared_control_plane/`

## 6. Run all five Phase-B seeds

Still at exact head `bfa14...`:

```bash
python run.py cd-primary-phase-b --seed 0
python run.py cd-primary-phase-b --seed 1
python run.py cd-primary-phase-b --seed 2
python run.py cd-primary-phase-b --seed 3
python run.py cd-primary-phase-b --seed 4
```

Do not substitute summary-only evidence. Preserve the complete fresh Phase-B trees, including every `maintenance.jsonl`, state file, version file, arm manifest, and seed manifest.

## 7. Reproduce/preserve the original Phase-C v1 seed-0 failure lineage

With all five A/B seeds present at `bfa14...`, execute the original Phase-C seed-0 path:

```bash
python run.py cd-primary-phase-c --seed 0
```

This historical v1 attempt is expected to fail with the frozen seed-0 `NameError` lineage. Preserve the resulting `attempt.json` and `failure.json`.

Do **not** treat an unexpected success, different exception, additional output artifact, or different lineage as acceptable.

## 8. Create the correction-source worktree

Create a second clean worktree at:

`79ddc4c6d6dea52c7cabc55a6d082448fc24fcf9`.

Example:

```bash
git worktree add <correction-worktree> 79ddc4c6d6dea52c7cabc55a6d082448fc24fcf9
```

Transfer into that worktree, without changing tracked scientific source:

- the complete fresh `artifacts/cd_primary_v1` tree from the A/B worktree, including the preserved failed-v1 seed-0 lineage;
- the materialized Stage-1 interim tables;
- the same exact original System-A checkpoint bytes at their frozen paths.

Heavy artifacts remain untracked/external.

## 9. Regenerate and freeze the correction config

At exact correction source `79dd...`:

```bash
python run.py cd-primary-correction-prepare
```

This must generate:

`data/manifests/cd_primary_run_config_v1_1.json`

from the fresh A/B identities while preserving every frozen scientific block.

Before committing, verify that the correction manifest is the **only tracked change**.

Create a fresh correction-config-only child commit whose parent is exactly `79dd...`:

```bash
git add data/manifests/cd_primary_run_config_v1_1.json
git commit -m "Freeze Stage 9.5-6 regenerated correction config"
```

Do not amend historical accepted commits and do not add any other tracked file to this commit.

The resulting fresh correction-freeze commit is an execution artifact, not replacement Stage-8 evidence.

## 10. Run corrected Phase C for seed 0 only

At the fresh correction-config-only child commit:

```bash
python run.py cd-primary-phase-c --seed 0
```

Do not build a new confirmatory aggregate and do not rerun seeds 1-4 for Stage-9.5-6 unless a separately frozen protocol requires it.

Preserve the corrected seed-0 output tree under:

`<correction-worktree>/artifacts/cd_primary_v1/phase_c_offline_evaluation_v1_1/seed-0/`

## 11. Run the deterministic replay comparator

Return to the assurance checkout at audited head `H` or an unchanged checkout of that exact comparator implementation.

Run:

```bash
python tools/stage9_5/replay_equivalence_comparator.py \
  --accepted-root <recovered-original-artifacts-cd_primary_v1-root> \
  --fresh-root <correction-worktree>/artifacts/cd_primary_v1 \
  --accepted-correction-config data/manifests/cd_primary_run_config_v1_1.json \
  --fresh-correction-config <correction-worktree>/data/manifests/cd_primary_run_config_v1_1.json \
  --stage1-report results/audits/stage9_5_full_seed_rerun_v1/stage1_reconstruction_report.json \
  --stage9-5-1-recovery-report results/audits/stage9_5_full_seed_rerun_v1/fresh_clone_reconstruction_report.json \
  --output results/audits/stage9_5_full_seed_rerun_v1/replay_comparison_evidence.json \
  --finalizer-output-dir results/audits/stage9_5_full_seed_rerun_v1
```

The comparator now verifies the Stage-9.5-1 recovery report before accepting the replay comparison and passes its exact generated comparison-evidence file directly into the frozen replay-report finalizer. Do not continue unless the integrated command exits successfully and the generated comparison evidence has:

- all five Phase-A seeds complete;
- all five Phase-B seeds complete;
- Phase-C preconditions pass;
- original failed-v1 lineage preserved;
- corrected seed-0 output comparison pass;
- accepted maintenance archive verified;
- Stage-1 report verified;
- zero mismatches;
- zero failures;
- zero blockers;
- `comparison_complete = true`;
- `source_evidence_complete = true`;
- `unresolved_class_a = []`;
- `stage10_outcomes_accessed = false`.

## 12. Verify the integrated replay-report finalizer output

The Stage-9.5-6 comparator command in Step 11 invokes the already-frozen replay-report finalizer directly on the exact comparison-evidence file it just wrote. There is no separate operator-authored success step.

Required output:

`results/audits/stage9_5_full_seed_rerun_v1/replay_equivalence_report.json`

The replay report must bind:

- the comparison-evidence canonical SHA-256;
- the Stage-9.5-1 recovery-report canonical SHA-256;
- the frozen comparator/finalizer identities;
- zero mismatches, failures, blockers, and unresolved Class-A issues.

Do not hand-edit or regenerate that report through a different path.

## 13. Construct closure metadata only from verified reports

Only after Stage-9.5-1 recovery, comparator, and finalizer all pass:

- create `results/audits/stage9_5_full_seed_rerun_v1/success.json`;
- create/update `STAGE9_5_6_CLEAN_DETERMINISTIC_FULL_SEED_RERUN_CLOSURE.md`.

Closure metadata must be copied/derived from the actual verifier/comparator/finalizer reports and the same-head Stage-9 success. Do not invent or manually override success booleans.

The closure record must preserve the historical failed-attempt lineage and explicitly link:

- the Stage-9.5-1 recovery report path and canonical SHA-256;
- the replay-equivalence report path and canonical SHA-256;
- the replay construction contract and manifest;
- the v1.1 replay protocol;
- audited head `H`;
- same-head Stage-9 success on `H`;
- zero unresolved Class-A defects;
- no Stage-10 outcome access.

## 14. Run the fail-closed order gate

Before treating 9.5-6 as closed:

```bash
python tools/stage9_5/work_package_order_gate.py \
  --contract data/manifests/stage9_5_6_closure_order_gate_v1.json \
  --closure-doc STAGE9_5_6_CLEAN_DETERMINISTIC_FULL_SEED_RERUN_CLOSURE.md \
  --success-json results/audits/stage9_5_full_seed_rerun_v1/success.json \
  --report-path artifacts/stage9_5_order_gate_v1/order_gate_report.json
```

Required result:

`later_packages_unlocked=true`

Anything else leaves 9.5-7/8/9 locked.

## 15. Commit only small assurance evidence

The closure commit may include the small reports, success record, closure document, and related assurance metadata.

Do **not** commit:

- recovered System-A checkpoint bytes;
- recovered Stage-8 heavy archive;
- fresh replay heavy trees;
- reconstructed interim-table heavy bytes merely to satisfy closure.

The order gate permits closure/evidence commits after audited head `H` as long as `H` remains a valid ancestor and every report/hash/linkage requirement passes.

## 16. After 9.5-6 closure

Follow the frozen order only:

1. revalidate Stage-9.5-7 traceability;
2. rerun/revalidate Stage-9.5-8 independent reporting;
3. run Stage-9.5-9 hostile review last;
4. require zero unresolved Class-A defects;
5. finalize the multi-chat assurance-diversion retrospective;
6. close Stage 9.5;
7. only then authorize Stage-10 access.

## Retrospective requirement

Every failed attempt, harness defect, backout, blocker transition, and authoritative resolution used during this handoff must be appended to:

`STAGE9_5_ASSURANCE_DIVERSION_RETROSPECTIVE_WORKING_NOTES.md`

The final reviewer-facing retrospective must distinguish the historical path from the accepted final procedure and must demonstrate that no accepted Stage-8/9 scientific result or claim boundary was changed by the assurance diversion.
