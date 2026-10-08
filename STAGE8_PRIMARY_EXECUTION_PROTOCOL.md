# Stage 8 Primary C/D Execution Protocol

**Status:** PROSPECTIVE PRIMARY EXECUTION FREEZE — HELD-OUT ACCESS STILL LOCKED  
**Date:** 9 October 2026  
**Branch:** `stage8-cd-primary-evaluation`  
**Corrected implementation-ready parent:** `cd-implementation-ready-v1.1` / `5627e36c7f1fef9620346e31e2aee01a2dd155ee`

## 1. Purpose

Stage 8 is the first stage permitted to execute the frozen primary adaptive stream.

This document freezes the execution order and the final operational safeguards before that access.

No primary pre/post adaptive row may be processed until the generated primary run-config manifest is:

1. created by the no-data preparation command;
2. committed on this branch;
3. the only intended configuration addition relative to the tested execution source;
4. present in a clean worktree;
5. green under the exact-head Research Contract CI.

## 2. Primary launcher

All primary commands must be invoked through:

`powershell -ExecutionPolicy Bypass -File scripts/run_primary.ps1 <command> [args]`

The launcher sets, before Python starts:

- `PYTHONHASHSEED=0`
- `OMP_NUM_THREADS=1`
- `MKL_NUM_THREADS=1`
- `OPENBLAS_NUM_THREADS=1`
- `NUMEXPR_NUM_THREADS=1`

The Python runtime then enforces single-thread numerical pools and deterministic PyTorch controls.

## 3. Configuration freeze

The command:

`scripts/run_primary.ps1 cd-primary-prepare`

must not load `training`, `development`, `pre_drift`, or `post_drift` partitions.

It verifies the corrected implementation-ready tag and local preflight, requires a clean worktree, and writes exactly:

`data/manifests/cd_primary_run_config_v1.json`

The config freezes:

- current governing-source hashes;
- protocol normalized-text hashes;
- scientific source normalized-text hashes;
- dependency lock identity;
- accepted scenario/preprocessing identities;
- five accepted System-A checkpoint identities and monitor thresholds;
- accepted R0.v2 identity;
- primary control-plane configuration and RNG namespace;
- primary symbolic-operator configuration;
- periodic trigger clocks;
- fixed fusion weights and thresholds;
- confirmatory endpoint family;
- seeds, arms, phase order and runtime contract;
- the fact that no held-out access occurred during preparation.

The config hashes the scientific source **tree**, not its own Git commit. Therefore the generated config can be committed without creating a self-referential identity problem.

Any source/protocol/dependency change after this config freeze makes execution fail closed.

## 4. Evidence locations

Heavy/write-once primary execution evidence is stored under:

`artifacts/cd_primary_v1/`

This path is Git-ignored so execution of one seed does not make the worktree dirty and thereby invalidate subsequent seed runs.

Compact publication/audit evidence is exported only after the complete primary evaluation to:

`results/frozen/cd_primary_v1/`

Large traces and adaptive checkpoint bytes remain externally archived by cryptographic hash and are not silently committed to Git.

## 5. Phase A — shared adaptive control plane

Command form:

`scripts/run_primary.ps1 cd-primary-phase-a --seed <0..4>`

Phase A:

- requires the tracked frozen primary config;
- requires a clean worktree;
- reconstructs the accepted training-only 10,000-row anchor;
- reconstructs the ordered primary stream;
- neutralizes adaptive row IDs to `stream:<index>`;
- passes no boundary metadata or partition name into the shared runner;
- loads the accepted seed-specific System-A checkpoint;
- executes the shared delayed-label ADWIN/replay/neural trajectory;
- verifies information timing, checkpoint purity and shared identity;
- writes a seed-specific write-once run manifest and checkpoint lineage;
- performs no boundary scoring and no symbolic-arm execution.

The CLI intentionally does not print drift counts, update counts, pending-state details or performance metrics.

Technical failures are preserved in a write-once failure artifact and are not silently rerun.

### Phase-A barrier

**All five** Phase-A seeds must verify before any Phase-B symbolic treatment is allowed.

## 6. Phase B — frozen C / D-drift / D-periodic symbolic trajectories

Command form:

`scripts/run_primary.ps1 cd-primary-phase-b --seed <0..4>`

Every Phase-B invocation re-verifies all five Phase-A shared trajectories before symbolic work begins.

For a given seed:

- C uses the accepted migrated R0.v2 frozen for the whole stream;
- D-drift uses the first four shared confirmed detector opportunities;
- D-periodic uses the exact clocks 27,706 / 55,412 / 83,118 / 110,824;
- all arms share the same seed, R0 start state, shared control-plane identity and symbolic operator hash;
- D candidate generation and independent validation follow the Stage-7 contracts;
- complete generation provenance is frozen, including selected features, SHAP ranking, background/attribution row IDs, candidate structures and timing;
- symbolic maintenance evidence and published rule-base versions are frozen;
- no boundary scoring is performed.

### Phase-B barrier

**All five** Phase-B seeds must verify before Phase C is allowed.

## 7. Phase C — offline boundary-aware evaluation

Command form:

`scripts/run_primary.ps1 cd-primary-phase-c --seed <0..4>`

Phase C is the first component allowed to use the designated boundary.

It may begin only after all five Phase-A and all five Phase-B trajectories verify.

For each seed, Phase C:

- deserializes frozen symbolic versions rather than rerunning maintenance;
- scores the immutable C, D-drift and D-periodic trajectories;
- evaluates lambda=.50 primary fusion and lambda=.70/.90/1.00 sensitivities;
- enforces exact lambda=1 predictive equality across matched arms;
- computes full/pre/post detection and explanation summaries;
- computes the frozen reporting-window and recovery summaries;
- records trigger diagnostics relative to the boundary;
- performs offline development and pre-reference neural retention probes per checkpoint;
- writes deterministic-content-hashed compressed row-level prediction traces;
- records that adaptive components never received boundary metadata.

No threshold or rule is refitted in Phase C.

## 8. Confirmatory aggregate

After all five Phase-C seed artifacts verify:

`scripts/run_primary.ps1 cd-primary-phase-c --aggregate`

writes the prespecified five-seed confirmatory family only:

- E1 post MCC: D-drift minus C;
- E2 post MCSC: D-drift minus C;
- E3 post MCSC: D-drift minus D-periodic.

It uses the frozen paired mean/t95 interval, sign test and Holm family.

Windows, rules, events and maintenance opportunities are never promoted to independent replicates.

## 9. Compact export

After the aggregate exists:

`scripts/run_primary.ps1 cd-primary-export`

exports only compact manifests/summaries/state-version evidence to the trackable frozen-results tree.

The export manifest records exact hashes back to the heavy `artifacts/cd_primary_v1` evidence.

The compact export is committed only after its changed-file set is reviewed.

## 10. Pre-access Stage-8 hardening

The following changes were made prospectively, before any primary adaptive access:

1. D-periodic now has the same local seed-mismatch guard as C and D-drift.
2. Symbolic maintenance records now preserve complete candidate-generation provenance rather than only candidate counts/evidence IDs.
3. Rule-base JSON deserialization was added and is hash-verified so Phase C consumes immutable Phase-B versions rather than rerunning symbolic maintenance.
4. Primary execution evidence was moved to the Git-ignored artifact tree so the clean-worktree gate remains meaningful between seeds.
5. Phase-A CLI output was narrowed to integrity identities instead of exposing drift/update outcomes during execution.
6. Phase-A and Phase-B technical exceptions are preserved as write-once failure artifacts.
7. Phase C prospectively verifies both compressed trace file hashes and canonical uncompressed JSONL content identities.

These are implementation/audit hardenings. They do not change the frozen detector, neural update, symbolic operator, trigger schedule, fusion rule, endpoints or inferential unit.

## 11. Post-access change rule

After the first successful Phase-A command reads the primary adaptive stream:

- no scientific parameter may be changed because of observed direction;
- no failed update may be removed because it performs poorly;
- no threshold/rule/trigger schedule may be retuned;
- any invalidating implementation defect must preserve the failed artifact/log, receive a new versioned correction and be disclosed;
- the original frozen config remains preserved.

Primary robustness conditions remain prespecified and may not replace the primary trajectory based on favorable results.


## 12. Final pre-access integrity hardening

The following controls were added before primary run-config generation and before any adaptive
held-out access:

- The dependency lock is bound by its normalized UTF-8 text SHA-256 rather than platform-specific
  checkout bytes. `requirements-lock.txt` is pinned to LF for future checkouts.
- `cd-primary-prepare` verifies every installed distribution named in the exact lock and freezes the
  resulting `name -> version` map and its canonical hash. Phase execution re-verifies the same
  installed distribution map.
- GitHub Research Contract checkout uses full history/tags so corrected implementation-ready ancestry
  can be verified in config-head CI.
- Once `cd_primary_run_config_v1.json` is committed, primary execution requires `HEAD` to equal
  exactly the commit that last committed that config file. A later commit, even one that does not
  alter scientific source, invalidates the execution gate until a new versioned config is frozen.
- On GitHub pull-request merge refs, the exact-config-head test is explicitly skipped when GitHub is
  testing a synthetic merge SHA; the branch push run at the exact config commit is the binding
  execution CI gate.
- Phase-B verification now checks arm-manifest file identities, symbolic initial/final state
  identities, strictly increasing publication clocks, contiguous inference-version increments, and
  parent version/hash lineage for every published symbolic state.
- Each Phase-C seed manifest explicitly binds to its exact Phase-A run manifest and Phase-B seed
  manifest. Compact export re-verifies Phases A, B and C plus the five-seed aggregate before copying
  any compact evidence.
- The lambda=1 negative control now requires each arm's fused scores to equal its shared neural scores
  exactly, in addition to cross-arm predictive equality.
- Recovery evidence preserves the absolute qualifying post-window clock and separately reports
  `recovery_rows_from_boundary = recovery_clock - boundary_index`, which is the frozen reporting
  scale required by the analysis protocol. The two-window persistence rule and baseline are unchanged.
- The frozen run config includes the Research Contract workflow and Git execution policies in its
  scientific source identity.

These are fail-closed reproducibility and causal-integrity checks. They do not modify any frozen
scientific parameter, treatment, endpoint, threshold, update budget, trigger schedule or inference
rule.


## 13. Final cross-phase evidence rebinding hardening

A final pre-access verifier audit identified a distinction between **internal consistency** and
**causal provenance binding**.

Before this correction, a Phase-B artifact could prove that C, D-drift and D-periodic all referenced
the same shared identity, yet the verifier did not independently prove that this identity was still
the one frozen in the verified Phase-A seed artifact. Likewise, Phase-C summaries were bound to the
Phase-B seed manifest at the seed level, but individual arm summaries were not rechecked against the
verified Phase-A shared identity and exact Phase-B arm manifest during later verification.

This was corrected prospectively before run-config generation and before any primary adaptive access.

Phase-B verification now:

- re-verifies **all five** Phase-A seeds;
- requires the seed-level Phase-B shared identity to equal the verified Phase-A identity;
- requires the stored all-seed Phase-A identity map to reproduce exactly;
- requires the seed and arm identities of every arm manifest;
- requires every arm and trajectory to use the frozen primary symbolic-operator hash;
- requires every arm/trajectory shared identity to equal the verified Phase-A seed identity.

Phase-C verification now:

- re-binds each arm summary to the verified Phase-A shared identity;
- re-binds each arm summary to the exact Phase-B arm-manifest identity;
- requires the copied symbolic-maintenance summary to equal the frozen Phase-B arm summary;
- records and verifies the exact row count of every compressed prediction trace against the frozen
  primary stream length.

Adversarial unit tests deliberately construct a self-consistent but forged Phase-B shared identity
and a Phase-C arm summary detached from verified Phase A. Both are required to fail closed.

This correction changes no adaptive state, detector, neural update, rule operator, schedule, fusion
parameter, endpoint, or inferential rule. It strengthens only provenance verification before first
held-out access.


## 14. Config-only freeze-commit invariant

The no-data preparation command records the exact source HEAD from which the primary run config was
generated.

Primary execution now requires both:

1. `HEAD` is exactly the commit that last committed
   `data/manifests/cd_primary_run_config_v1.json`; and
2. that commit's single parent equals the recorded no-data preparation source HEAD, while its changed
   path set is exactly:
   `data/manifests/cd_primary_run_config_v1.json`.

Therefore a config commit that also changes tests, documentation, workflow, source, or any other file
is invalid for primary execution even if the scientific source hashes would otherwise still verify.

This control was added before run-config generation and before any primary adaptive access.
