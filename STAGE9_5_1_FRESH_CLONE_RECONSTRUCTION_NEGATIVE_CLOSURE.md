# Stage 9.5-1 Fresh-Clone Reconstruction — Negative Closure

**Status:** CLOSED — FAILED / EXTERNAL PROVENANCE UNRESOLVED  
**Closure kind:** Negative closure; not a successful reconstruction  
**Classification:** Class A remains unresolved for Stage-9.5 assurance  
**Observed head:** `3ff7319e83e84a7e3c289cd023ba02e7bc35af31`  
**Observed date:** 17 October 2026  
**Machine record:** `data/manifests/stage9_5_1_negative_closure_v1.json`

## Decision

Stage 9.5-1 is closed as a **failed assurance package** because the frozen
success criterion cannot be satisfied from any authoritative artifact surface
currently accessible to this project session.

This closure does **not** declare the accepted Stage-8/9 numerical results
wrong. It also does **not** reinterpret missing evidence as successful
reconstruction.

The frozen Stage-9.5-1 success criterion remains unchanged:

1. the five exact original System-A checkpoint byte streams must be supplied
   and match their frozen SHA-256 identities; and
2. the original Stage-8 heavy archive rooted at `artifacts/cd_primary_v1`
   must be supplied and verify all **145/145** descriptor-linked requirements.

Neither condition is currently satisfied.

## Frozen checkpoint identities

- seed 0 — `514c6d552b3cd680ae966bbb568105bd2871bc68d3a47aded070a70ba0615bd1`
- seed 1 — `07696c3f580645d9c96ac3e736cfb5eeaa8033f148bf64822e8ee105861cf552`
- seed 2 — `7630514cf409256bd2bbe27eca59f881acb238be698b5fdb1ee12bca8e402491`
- seed 3 — `cce1ce47db047b9d441bbe6dad9bd53f1ee6ff3ad7d404521cae72a38bccd4b4`
- seed 4 — `9b9e56371f3246482998c4efea4829e1e6d5aaf549bb43e1af05e471dfcb9e93`

## Exact-head assurance evidence

At head `3ff7319e83e84a7e3c289cd023ba02e7bc35af31`:

- Stage-9 robustness run `39050628185`: **success**;
- Stage-9.5 assurance run `39050628180`;
- assurance-contract job: **87 tests passed**;
- fresh-clone job `117448298396`: **13 tests passed** and the verifier
  reported **0 identity failures / 2 external-artifact blockers**;
- order-gate job `117448298419`: **success**, with
  `later_packages_unlocked=false`;
- Stage-9.5-7/8/9: **skipped**;
- the known Stage-9.5-5 discovery baseline remained
  **ruff=154 / mypy=55** and is not reopened by this closure.

The two external blockers remain:

- `system_a_checkpoint_bytes_missing`;
- `stage8_large_artifact_archive_missing`.

## Recovery sweep performed before closure

The following currently accessible surfaces were checked without finding the
authoritative bytes:

- Project and conversation files;
- the current container/local mounted paths;
- repository branches/history/path history already audited during Stage 9.5;
- GitHub Releases;
- the System-A freeze commit's Actions run
  (`37531241834`), which retained no artifacts;
- all four Actions runs attached to the accepted Stage-8 evidence commit
  `c2ded83b8195b9321e715626c1f305f9627936e8`, all of which retained no
  workflow artifacts;
- public web searches for each exact checkpoint SHA-256 and the
  `artifacts/cd_primary_v1` identifiers;
- the later Stage-1 transport/mirror surface, which contains CICIDS2017 source
  material rather than project-generated System-A checkpoints or the Stage-8
  replay archive.

No GitHub release exists for the repository.

Google Drive, Dropbox, Box, and SharePoint connectors are available in the
product but are **not installed/connected in this session**. Therefore this
closure does not claim that no user-held copy can exist anywhere. It states
only the defensible fact: no authoritative copy is recoverable from the
surfaces presently accessible to the assurance process.

## Why regeneration is not accepted

This negative closure deliberately preserves the previously frozen
reproducibility boundary.

It is not acceptable to:

- retrain System A and substitute newly serialized checkpoints;
- regenerate a Stage-8 archive and call it the original archive merely because
  metrics appear equivalent;
- weaken the 145-file requirement after the recovery failure is known;
- relabel this Class-A assurance defect as a lower class in order to unlock
  later work; or
- manually author a successful recovery report.

Those actions would convert a transparent provenance limitation into a
post-outcome assurance rewrite.

## Scientific interpretation

This closure distinguishes **scientific-result validity** from
**publication-grade reconstruction**.

The committed Stage-8/9 evidence identities checked by the assurance machinery
remain internally consistent; this closure does not establish that their
reported numerical results are false.

However, the project can no longer claim that an independent clean clone has
verified the exact original neural checkpoint bytes and complete Stage-8 heavy
evidence chain. The full reconstruction/replay assurance claim therefore
remains unsupported.

## Downstream consequence

This is a closed-failed package, not a successful gate pass.

Accordingly:

- Stage 9.5-6 cannot obtain a valid replay closure from the frozen procedure;
- Stage 9.5-7/8/9 remain locked as authoritative closure packages;
- zero-unresolved-Class-A closure has not been achieved;
- Stage 10 remains **PROHIBITED** under the governing plan.

No accepted Stage-8/9 scientific object is modified or replaced by this
negative closure.

## Reopening rule

This negative closure may be reopened only if an authoritative source later
supplies:

1. all five exact original System-A checkpoint files; and
2. the original Stage-8 heavy archive.

The existing frozen v1.2 verifier must then independently produce:

- `pass=true`;
- verified checkpoint seeds `[0,1,2,3,4]`;
- Stage-8 archive requirement count `145`;
- Stage-8 archive verified count `145`;
- zero failures; and
- zero blockers.

Until that happens, this negative closure is the authoritative disposition of
Stage 9.5-1.
