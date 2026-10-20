# Stage 9.5-1 v1.2 Heavy-Artifact Inventory Correction

**Status:** PROSPECTIVE ASSURANCE-HARNESS CORRECTION  
**Parent evidence:** Stage 9.5-1 v1.1 remains preserved  
**Scientific source/evidence changed:** no

## Defect

The frozen Stage-9.5 protocol requires fresh-clone reconstruction to document every required external/heavy artifact and whether it is retrievable.

The v1.1 verifier correctly inventoried the eight external raw CICIDS2017 files and the five external System-A initial checkpoints, but it did not register the accepted Stage-8 large artifact archive.

The accepted Stage-8 compact manifest itself declares:

- `large_artifact_archive_required_for_publication: true`;
- `large_artifact_root: artifacts/cd_primary_v1`;
- adaptive checkpoint bytes are not in Git;
- large prediction traces are not in Git.

The original large archive is also required by the prospectively frozen Stage-9.5-6 replay-equivalence verification because the committed compact evidence does not contain the original timing-bearing Phase-B maintenance streams.

Therefore the v1.1 report is preserved as valid for the identities it checked, but it is incomplete as the full external/heavy-artifact inventory.

## v1.2 correction

The v1.2 identity manifest adds `stage8_large_artifact_archive` as a required Stage-9.5-1 external artifact.

The verifier now derives descriptor-linked archive requirements from immutable committed Stage-8 evidence:

- Phase-A run-manifest file descriptors, including stream evidence and adaptive child checkpoints;
- Phase-B arm-manifest file descriptors, including maintenance streams and rule-state/version artifacts;
- Phase-C prediction-trace descriptors.

If no archive root exists, the verifier reports:

`stage8_large_artifact_archive_missing`.

If an archive root is supplied, every descriptor-linked file must exist and match its accepted SHA-256. Missing or mismatched supplied bytes are identity failures, not soft blockers.

## Expected blocked state

With neither external artifact set supplied in CI, the expected semantic result becomes:

- identity failures: **0**;
- external-artifact blockers: **2**:
  1. `system_a_checkpoint_bytes_missing`;
  2. `stage8_large_artifact_archive_missing`.

This correction does not reinterpret accepted Stage-8/9 results, regenerate missing bytes, or authorize Stage 9.5-6/Stage 10.
