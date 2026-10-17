# Stage 9.5-6 Historical Rerun Identity-Replay Blocker

**Status:** OPEN / BLOCKED  
**Classification:** Class A — material provenance/reconstructibility blocker  
**Accepted Stage-8/9 evidence changed:** no  
**Stage-10 outcome access:** none

## Finding

The frozen 9.5-6 protocol requires a clean historical Stage-8 rerun. Source-level audit shows that the accepted corrected Phase-C executable cannot consume genuinely fresh Phase-A/Phase-B outputs even when their scientific trajectories are equivalent, because it requires exact historical upstream manifest hashes that contain non-replayable diagnostic metadata.

This blocker is independent of `system_a_checkpoint_bytes_missing`.

## Historical identities

- Phase-A/B exact config head: `bfa14b942e4a5b2fbfa8aa3c43728a7f1cd81645`
- original config manifest SHA: `3e3f768b5aa32f469440bb334508f747bbf2f7f5b08d9570a7aef2dbb9cb0257`
- corrected Phase-C config head: `1cc61cae8fae40d30530daf2d1f4b542898eef6d`
- corrected config manifest SHA: `d380fce5f9db8f0b639dc999298a263b10a10a3d02e35def226a121d098e2222`
- accepted Stage-8 evidence commit: `c2ded83b8195b9321e715626c1f305f9627936e8`

## Replay obstruction

### Phase A

`execute_phase_a_seed` hashes the full runtime dictionary into `run_manifest_sha256`.

That runtime dictionary includes `platform`, `processor`, and `threadpool_info`, including environment-specific loaded-library file paths. A clean environment can reproduce the same scientific trajectory while producing a different run-manifest hash.

### Phase B

Symbolic execution measures SHAP, surrogate, and lifecycle durations with `time.perf_counter_ns()`.

Those durations are included in `maintenance_summary`, including `compute_seconds`, `shap_seconds`, `surrogate_seconds`, `lifecycle_seconds`, and derived timing rates. The complete summary is included before each arm manifest is canonically hashed; those arm identities feed the seed-level Phase-B manifest hash.

Thus ordinary execution-time variation changes `phase_b_manifest_sha256` even when symbolic decisions, publications, rule states, and predictions are scientifically identical.

### Corrected Phase C

The accepted correction config stores exact original Phase-A `run_manifest_sha256` and Phase-B `phase_b_manifest_sha256` values for all five seeds. `verify_primary_correction_for_execution` reconstructs the upstream identity mapping and requires exact equality with that frozen mapping before scoring.

Fresh A/B outputs therefore fail the corrected Phase-C gate solely because diagnostic runtime/timing fields change.

## Global barrier

The historical code also requires:

- all five Phase-A seeds before any Phase-B seed;
- all five Phase-A and all five Phase-B seeds before corrected Phase C can score even one seed;
- the preserved failed Phase-C v1 seed-0 NameError evidence to match exactly before corrected Phase C.

Therefore a faithful 9.5-6 rerun is not an isolated one-seed A/B/C invocation.

## Interpretation

This is a Class-A **assurance/reconstructibility** defect. It does not establish that accepted Stage-8/9 numerical results are wrong, and it does not overturn the closed statistical, causal, or mutation assurance packages.

The problem is that the historical exact execution gate mixes replay-invariant scientific identity with machine/path/timing diagnostics.

## Stage-1 dependency

Stage-8 reads `data/interim/cicids2017/*.csv.gz`, not the raw CSVs directly. The repository contains the structural preprocessing path from `data/raw/cicids2017/` to those interim tables. This must be independently reconstructed before a future rerun. It is not presently classified as a separate external-byte blocker.

## Required prospective resolution

Before any 9.5-6 execution:

1. preserve all accepted historical hashes as immutable references;
2. recover and hash-verify the five original System-A checkpoint files;
3. freeze a versioned 9.5-6 assurance correction that separates replay-invariant scientific identities from explicitly diagnostic runtime/path/timing fields;
4. define those equivalence rules before rerun outcomes are viewed;
5. keep exact fail-closed checks for scenario, preprocessing, checkpoints, R0, seeds, thresholds, treatment, information timing, trajectories, decisions, publications, and endpoints;
6. preserve the historical failed-v1 correction lineage;
7. do not rewrite accepted Stage-8/9 evidence.

Until both Class-A blockers are resolved, Stage 9.5-6 remains blocked and Stage 10 remains prohibited.
