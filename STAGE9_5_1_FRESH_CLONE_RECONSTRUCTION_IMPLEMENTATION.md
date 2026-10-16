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

Recovery classification is fail-closed: when no checkpoint recovery is supplied and no checkpoint bytes are present, absence remains the external blocker `system_a_checkpoint_bytes_missing`; once a checkpoint root is supplied (or partial local checkpoint bytes are present), any missing seed is a recovery/identity failure, and any hash mismatch is likewise a failure. The Stage-8 large archive follows the same distinction: absent root is an external blocker, while a supplied incomplete or mismatched root is an identity failure.

This is an assurance/retrievability finding, not a scientific retuning opportunity. Checkpoints may not be regenerated and substituted merely because regenerated weights appear similar; the frozen byte identities remain authoritative unless a prospectively documented assurance disposition establishes a different verification object.

## Authoritative recovery verification

When the original external bytes are recovered, verify them from a clean historical-runtime environment with the existing fail-closed CLI rather than copying them into Git:

```bash
python tools/stage9_5/fresh_clone_reconstruction.py \
  --output-dir results/audits/stage9_5_full_seed_rerun_v1 \
  --checkpoint-root <directory-containing-seed_0.pt-through-seed_4.pt> \
  --stage8-archive-root <recovered-artifacts-cd_primary_v1-root>
```

The command verifies the five checkpoint SHA-256 identities and every descriptor-linked required Stage-8 heavy file, then writes `fresh_clone_reconstruction_report.json` and the companion Markdown report directly under `results/audits/stage9_5_full_seed_rerun_v1/`. Preserve those small verifier outputs unchanged as assurance evidence and commit them with the eventual closure record; the order gate recomputes the JSON report's canonical hash and verifies its audit/status, five verified checkpoint seeds, zero failures/blockers, and **145 required / 145 verified** Stage-8 archive counts. Do not commit recovered heavy checkpoint/archive bytes merely to satisfy the verifier.

A successful Stage 9.5-1 recovery verification removes the external-artifact blockers only. It does not itself close Stage 9.5-6, does not replace the accepted Stage-8/9 evidence, and does not authorize Stage-10 treatment execution; the frozen replay-equivalence v1.1 procedure and work-package ordering still apply.

