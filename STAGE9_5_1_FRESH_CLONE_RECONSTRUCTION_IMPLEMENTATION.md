# Stage 9.5-1 Fresh-Clone Reconstruction Implementation

**Status:** IMPLEMENTATION FROZEN BEFORE FIRST 9.5-1 EXECUTION  
**Governing protocol:** `STAGE9_5_Q1_INDEPENDENT_ASSURANCE_PROTOCOL.md`  
**Stage 9.5-0 closure commit:** `9b2796b2d0085660e981ad82f7b22070f88eefb9`

## Purpose

Stage 9.5-1 independently tests whether the accepted identity/evidence chain is reconstructible from a clean clone plus explicitly documented external/heavy artifacts.

The verifier must not silently depend on workstation-local state.

## Clean-clone checks

The first implementation verifies:

- exact Git HEAD and clean worktree identity, with the 9.5-0 closure commit in ancestry;
- Python 3.11.9 and the frozen installed-distribution fingerprint;
- requirements-lock raw and normalized-text identities;
- scenario raw and canonical identities;
- frozen preprocessing state identity and train-only fit declaration;
- canonical System-A manifest identity and all five checkpoint byte SHA-256 values;
- canonical R0.v2 manifest identity, all five rule-file normalized-text hashes, and internal artifact hashes;
- every committed Stage-8 compact export file against its compact manifest;
- every committed Stage-9 compact evidence file against its compact manifest, plus aggregate and execution-plan identities;
- explicit external/heavy artifact inventory.

## External artifact disposition

The eight CICIDS2017 MachineLearningCSV files are external to Git. In the current assurance session, all eight supplied files were byte-hashed and exactly matched `cicids2017_raw_manifest.json`. They are documented external inputs for later full historical rerun work.

The five frozen System-A checkpoint files are also outside Git. Their paths and hashes are frozen in `system_a_v1.json`. Repository history and the historical Stage-3 GitHub Actions runs were checked; no committed checkpoint blobs or retained Actions artifacts were found.

Because 9.5-1 explicitly requires System-A identity verification, missing checkpoint bytes are a blocking reconstruction finding. The first clean-clone execution is therefore expected to fail closed unless an external checkpoint root containing the exact five frozen files is supplied.

This is an assurance/retrievability finding, not a scientific retuning opportunity. Checkpoints may not be regenerated and substituted merely because regenerated weights appear similar; the frozen byte identities remain authoritative unless a prospectively documented assurance disposition establishes a different verification object.
