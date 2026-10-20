# Stage 9.5-6 Phase-C Pre-Rerun Execution Handoff

**Status:** PROSPECTIVELY FROZEN / READY ONCE HARD PREREQUISITES PASS  
**Contract:** `data/manifests/stage9_5_6_phase_c_pre_rerun_verification_v1.json`  
**Scientific semantics changed:** no  
**Corrected Phase-C seed-0 rerun authorized in this handoff:** no  
**Stage-10 access authorized:** no

## Purpose

This handoff is the exact execution boundary for the small Stage-9.5-6 tranche
that must occur **after**:

1. the unchanged Stage-9.5-1 v1.2 verifier passes; and
2. the complete historical Phase-A and Phase-B replay passes the frozen
   deterministic comparator for all five seeds and all three symbolic arms.

It reproduces and verifies the original Phase-C v1 seed-0 failure lineage,
regenerates the correction config from the fresh A/B identities at the frozen
correction source, verifies frozen scientific-block equality fail-closed, and
preserves one canonical pre-rerun report.

It **stops before corrected Phase-C execution**.

## 0. Live-head reconciliation

Before any repository mutation or authoritative evidence commit, re-read PR #21
and record its live head. Reconcile any external advance first.

The assurance-branch head used to preserve the final pre-rerun report must remain
outside Stage-10 outcome access and must not change replay comparator,
projection, correction-config, or verifier semantics after outcome-bearing
historical replay evidence is inspected.

## 1. Hard prerequisite gate

Do not start this tranche unless the unchanged Stage-9.5-1 v1.2 verifier report
has all of the following:

- `audit_id = stage9.5-1-fresh-clone-reconstruction-v1_2`;
- `pass = true`;
- `failures = []`;
- `blockers = []`;
- verified System-A seeds `[0,1,2,3,4]`;
- Stage-8 descriptor-linked archive `145 required / 145 verified`.

Also require the complete fresh historical replay at:

`bfa14b942e4a5b2fbfa8aa3c43728a7f1cd81645`

to have passed the deterministic Phase-A/B comparator for:

- Phase A seeds 0-4;
- Phase B seeds 0-4;
- arms `c_frozen_symbolic`, `d_drift`, and `d_periodic`;
- accepted maintenance-record archive verification.

If either prerequisite is false, stop. Do not inspect or regenerate Phase-C
pre-rerun evidence.

## 2. Reproduce the exact original Phase-C v1 seed-0 failure

In the historical A/B worktree at exact head:

`bfa14b942e4a5b2fbfa8aa3c43728a7f1cd81645`

with all five fresh A/B seeds present, run:

```bash
python run.py cd-primary-phase-c --seed 0
```

The command is expected to fail. Preserve only the frozen failed-v1 seed-0
surface:

- `attempt.json`;
- `failure.json`.

Required lineage:

- seed 0;
- phase `offline_boundary_aware_evaluation`;
- `adaptive_components_received_boundary = false`;
- exception type `NameError`;
- exact message `name 'read_jsonl' is not defined`;
- no successful scoring artifact;
- no additional unexpected Phase-C output.

Any different exception, success, missing file, extra file, or changed payload
identity is fail-closed.

## 3. Regenerate the correction config at the frozen source

Create/use a clean correction worktree at exactly:

`79ddc4c6d6dea52c7cabc55a6d082448fc24fcf9`.

Transfer into it without changing tracked scientific source:

- the complete fresh `artifacts/cd_primary_v1` tree from the historical A/B
  worktree, including the preserved failed-v1 seed-0 lineage;
- the materialized Stage-1 interim tables;
- the same exact original System-A checkpoint bytes.

Then run:

```bash
python run.py cd-primary-correction-prepare
```

This must create:

`data/manifests/cd_primary_run_config_v1_1.json`.

Before committing it, verify that it is the **only tracked change**. If a frozen
execution artifact commit is needed, create a config-only child commit whose
parent is exactly `79dd...`.

Do not amend accepted historical commits.

## 4. Run the canonical pre-rerun verifier from the assurance checkout

From the current assurance checkout, point the verifier at:

- the recovered accepted Stage-8 archive root;
- the fresh historical A/B + failed-v1 artifact root;
- the accepted correction config;
- the freshly regenerated correction config;
- the successful unchanged Stage-9.5-1 v1.2 report.

Run:

```bash
python tools/stage9_5/phase_c_pre_rerun_verifier.py \
  --accepted-root <accepted-artifacts-cd_primary_v1-root> \
  --fresh-root <fresh-artifacts-cd_primary_v1-root> \
  --accepted-correction-config <accepted-cd_primary_run_config_v1_1.json> \
  --regenerated-correction-config <fresh-cd_primary_run_config_v1_1.json> \
  --stage9-5-1-recovery-report <successful-fresh_clone_reconstruction_report.json> \
  --output results/audits/stage9_5_full_seed_rerun_v1/phase_c_pre_rerun_verification_report.json
```

The verifier re-runs the frozen Phase-A/B deterministic comparison, verifies
the accepted Stage-8 archive root, verifies the unchanged Stage-9.5-1 recovery
report, verifies the exact failed-v1 seed-0 lineage, invokes the independent
regenerated-correction-config verifier, and checks that corrected Phase-C seed-0
output is still absent.

## 5. Required successful report state

The report is acceptable only if all of these hold:

- `pass = true`;
- `hard_prerequisites_pass = true`;
- `original_phase_c_v1_seed0_failure_lineage_verified = true`;
- `regenerated_correction_config_scientific_blocks_equal = true`;
- `corrected_phase_c_seed0_output_absent = true`;
- `corrected_phase_c_seed0_rerun_executed_by_this_tool = false`;
- `stage10_outcomes_accessed = false`;
- `next_authorized_step = corrected_phase_c_seed0_rerun`;
- canonical report SHA-256 recomputes exactly.

Preserve this report unchanged as Stage-9.5-6 assurance evidence.

## 6. Mandatory stop

**Stop after the successful pre-rerun report is preserved.**

Do not run:

```bash
python run.py cd-primary-phase-c --seed 0
```

from the correction-config child commit in this tranche.

Do not create or inspect corrected
`phase_c_offline_evaluation_v1_1/seed-0` output.

Do not build a new confirmatory aggregate.

Do not access Stage-10 outcomes.

The corrected Phase-C seed-0 rerun is a separate next tranche and is authorized
only by a successful canonical pre-rerun report.

## Retrospective preservation

This handoff is part of the multi-chat Stage-9.5 assurance diversion. Its
chronology and rationale must remain represented in
`STAGE9_5_ASSURANCE_DIVERSION_RETROSPECTIVE_WORKING_NOTES.md` and in the
eventual Stage-9.5 closure retrospective. This handoff is execution guidance,
not scientific-result replacement.
