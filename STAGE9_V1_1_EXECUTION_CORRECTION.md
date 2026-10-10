# Stage 9 v1.1 Execution Correction — Offline Compact-Manifest Reader

Status: implementation-only correction after the first Stage-9 execution attempt; no robustness result accepted before this correction.

## 1. Governing frozen parent

This correction descends from the accepted Stage-9 config-freeze commit:

`d27b2e6019822a9082a3cb1ec7cb38ea20cdf7d8`

Frozen Stage-9 v1 config manifest:

`84357c4a29e8c48ea15669412f2cf562c9e6be528100bb3007936f18d918b017`

Frozen Stage-9 v1 writer payload hash:

`7d0601be511020808ddcc3f4c80337acb30cfaa4707f4cbdf0444398ddd4ae07`

The Stage-8 evidence/config/scenario/System-A/R0/treatment contract and the prospectively frozen Stage-9 condition family remain unchanged.

## 2. Failed v1 execution attempt

The first `execute-all` attempt created the frozen full-matrix execution plan and began the first predetermined step:

- group: offline
- condition: `lambda_0_7`
- seed: 0
- phase: offline

The offline runner wrote its write-once `attempt.json` and then failed while resolving the frozen Stage-8 compact-export descriptor.

Observed exception:

`AttributeError: 'list' object has no attribute 'values'`

Failure location:

`cd_stage9_offline._stage8_eval_payload -> manifest["files"].values()`

Root cause:

The immutable Stage-8 compact export manifest stores `files` as a JSON array/list of descriptor objects. The Stage-9 v1 offline provenance reader incorrectly treated that array as a mapping and called `.values()`.

The Stage-9 unit tests reproduced the same incorrect synthetic schema by constructing `files` as a mapping, so the defect was not detected by exact-head CI.

## 3. Scientific-access classification

This is an implementation/provenance-reader defect.

The failed call sequence was:

1. verify the frozen Stage-9 config and runtime;
2. write the Stage-9 execution plan;
3. create the first offline condition/seed write-once directory;
4. write `attempt.json`;
5. read and validate the frozen Stage-8 compact export manifest;
6. fail while iterating its descriptor container.

The failure occurred before:

- reading a Stage-8 arm evaluation payload for the robustness condition;
- extracting a lambda-specific metric;
- recomputing a reporting window;
- running any Stage-9 adaptive Phase A;
- running any Stage-9 symbolic Phase B;
- running any Stage-9 Phase C scoring;
- writing any accepted Stage-9 `result.json`;
- producing a Stage-9 compact export;
- inspecting a Stage-9 robustness outcome.

Therefore this correction does not change the estimand, treatment, comparator, endpoint, threshold, seed set, scenario, latency assumptions, detector signal, replay policy, symbolic gate, or statistical analysis.

## 4. Preservation requirements

The historical v1 output root is immutable:

`artifacts/cd_robustness_v1`

It must not be deleted, renamed, overwritten, resumed, or reused for corrected execution.

Before preparing the corrected v1.1 config, the implementation must verify and hash the historical v1 remnants. At minimum it must require:

- `artifacts/cd_robustness_v1/execution_plan.json`;
- `artifacts/cd_robustness_v1/offline/lambda_0_7/seed-0/attempt.json`;
- `artifacts/cd_robustness_v1/offline/lambda_0_7/seed-0/failure.json`;
- absence of every historical v1 `result.json`.

The v1.1 config must record the hashes of the preserved historical files and the failure classification above.

## 5. Corrective code change

The Stage-8 compact-manifest reader must iterate the frozen `files` array directly.

The correction must add regression coverage using the real Stage-8 manifest shape: a list/array of descriptor objects.

No fallback accepting both list and mapping is required for the governing frozen Stage-8 manifest. A shape mismatch must fail closed.

## 6. Corrected identities

Corrected execution uses new identities:

- config: `data/manifests/cd_stage9_run_config_v1_1.json`;
- run ID: `cd-robustness-v1_1`;
- heavy output root: `artifacts/cd_robustness_v1_1`;
- compact output root: `results/frozen/cd_robustness_v1_1`.

The historical v1 config and historical v1 outputs remain preserved.

The corrected v1.1 config must be prepared before any corrected robustness result is produced, committed as the sole changed path in its freeze commit, and pass exact-head Research Contract and Stage-9 CI before corrected execution.

## 7. Verification command

A wrapper-safe `verify-config` command must be available through `scripts/run_stage9.ps1` so runtime environment variables are frozen before config verification.

Direct ad-hoc Python verification that bypasses the wrapper is not the governing preflight.

## 8. Claim boundary

This correction is software provenance repair only.

It must never be described as:

- a robustness-method change;
- a new condition;
- a threshold change;
- a comparator change;
- a seed change;
- a statistical rescue;
- a post-outcome tuning response.

If the historical-remnant checks reveal any accepted v1 `result.json` or any access inconsistent with this protocol, preparation must abort and the failure must be reclassified before further execution.
