# Stage 8 Phase C v1.1 Implementation-Defect Correction

**Date:** 9 October 2026  
**Classification:** post-access implementation-defect correction; no scientific-design change  
**Parent primary config:** `cd_primary_run_config_v1.json`  
**Parent config SHA-256:** `3e3f768b5aa32f469440bb334508f747bbf2f7f5b08d9570a7aef2dbb9cb0257`  
**Correction config:** `cd_primary_run_config_v1_1.json`  
**Correction branch:** `stage8-phase-c-v1-1-correction`

## 1. Frozen upstream state before the defect

The original primary configuration was frozen and accepted at commit:

`bfa14b942e4a5b2fbfa8aa3c43728a7f1cd81645`

All five Phase-A shared-control-plane trajectories completed and verified under that config.

All five Phase-B symbolic trajectories completed and verified under that config.

No Phase-B execution performed boundary-aware scoring.

These Phase-A and Phase-B artifacts are valid upstream evidence and are not rerun as part of this
correction.

## 2. Observed Phase-C failure

The first Phase-C execution attempt was seed 0:

`powershell -ExecutionPolicy Bypass -File scripts/run_primary.ps1 cd-primary-phase-c --seed 0`

The command failed with:

`NameError: name 'read_jsonl' is not defined`

at the first attempted call that would read the frozen Phase-A prediction JSONL.

The defect was caused by `cd_primary_phase_c.py` referencing `read_jsonl` without importing it.

## 3. Scoring status at failure

The Phase-C function had already created the version-v1 seed directory and its write-once
`attempt.json`, but the exception occurred at the first Phase-A JSONL read.

Therefore no:

- prediction array;
- true-label stream array;
- symbolic trajectory scoring;
- fused score;
- pre/post metric;
- MCSC;
- recovery diagnostic;
- trigger diagnostic;
- retention probe;
- prediction trace;
- arm evaluation summary; or
- Phase-C seed manifest

was successfully produced before the exception.

The exception handler preserved `failure.json`.

The correction preparation gate requires the failed v1 seed-0 directory to contain **exactly**:

- `attempt.json`
- `failure.json`

and rejects correction preparation if any scored Phase-C output exists in that directory.

## 4. Correction

The minimal functional correction is to bind:

`from concept_drift_ids.cd_evidence import read_jsonl`

in `cd_primary_phase_c.py`.

Because primary held-out access had already occurred in Phases A/B, this is not applied silently to
the original config.

Instead, a versioned correction mechanism is introduced.

The correction also:

1. preserves the original v1 config unchanged;
2. preserves the failed v1 Phase-C attempt/failure artifacts unchanged;
3. re-verifies all five original Phase-A artifacts against the parent v1 config;
4. re-verifies all five original Phase-B artifacts against the parent v1 config;
5. freezes their exact run/trajectory identities into the v1.1 correction config;
6. proves that the frozen scientific config blocks are identical to v1;
7. hashes the corrected source/protocol/dependency environment;
8. forbids Phase-A or Phase-B re-execution under v1.1;
9. writes successful corrected Phase-C evidence under a new write-once directory:
   `artifacts/cd_primary_v1/phase_c_offline_evaluation_v1_1/`;
10. carries the failed v1 attempt/failure into the final compact evidence export.

## 5. Frozen scientific blocks

The correction verifier requires exact equality between v1 and v1.1 for:

- governing-source identities;
- scenario;
- System A;
- accepted R0.v2;
- primary control-plane configuration;
- primary symbolic-operator configuration;
- fusion thresholds/weights;
- confirmatory analysis definition.

No detector parameter, label latency, replay rule, neural update rule, symbolic gate, trigger schedule,
fusion threshold, endpoint, inferential unit or robustness definition is changed.

## 6. Correction preparation

After correction source CI passes, the local command:

`powershell -ExecutionPolicy Bypass -File scripts/run_primary.ps1 cd-primary-correction-prepare`

must:

- run on a clean worktree;
- verify the corrected implementation-ready ancestry;
- verify the parent v1 config;
- verify all five Phase-A and Phase-B artifacts;
- verify the exact failed v1 seed-0 attempt/failure evidence;
- confirm no successful v1 Phase-C scoring artifact exists;
- freeze the corrected scientific source and protocol hashes;
- write only:
  `data/manifests/cd_primary_run_config_v1_1.json`.

That correction config must then be committed as the **only changed path** in its commit and pass
exact-head CI before corrected Phase C can execute.

## 7. Rerun policy

Phase A and Phase B are **not rerun**.

The failed Phase-C v1 seed-0 attempt is **not deleted or overwritten**.

Corrected Phase C begins in the new v1.1 output tree and may reuse only the exact Phase-A and Phase-B
identities frozen into the correction config.

## 8. Scientific interpretation

This correction is a technical execution repair discovered before any successful Phase-C scoring.

It does not permit outcome-dependent tuning because no Phase-C result existed at the time of the
correction.

The original failed attempt, original v1 config, correction source history, correction config and
corrected outputs remain separately identifiable in the audit trail.
