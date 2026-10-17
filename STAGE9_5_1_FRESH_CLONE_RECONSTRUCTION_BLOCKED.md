> **Current disposition — 17 October 2026:** Stage 9.5-1 is now **CLOSED — FAILED / EXTERNAL PROVENANCE UNRESOLVED**. See `STAGE9_5_1_FRESH_CLONE_RECONSTRUCTION_NEGATIVE_CLOSURE.md` and `data/manifests/stage9_5_1_negative_closure_v1.json`. The historical body below is preserved unchanged as provenance and must not be read as the current package status.
>
# Stage 9.5-1 Fresh-Clone Reconstruction — BLOCKED Disposition

> **Historical disposition — superseded for current blocker inventory.** This file preserves the v1.1 fresh-clone result at the audited head shown below. It must not be read as the current Stage-9.5-1 blocker count. The governing current correction is `STAGE9_5_1_V1_2_HEAVY_ARTIFACT_INVENTORY_CORRECTION.md`: fresh-clone v1.2 reports **0 identity failures / 2 external-artifact blockers**, adding `stage8_large_artifact_archive_missing` alongside `system_a_checkpoint_bytes_missing`. This historical file remains part of the provenance trail and is not rewritten to replace its original v1.1 result.

**Status:** OPEN / BLOCKED — NOT CLOSED  
**Classification:** Class A — material provenance/reconstructibility blocker  
**Audited head:** `3f421e92cf81704570c0155eff94047b7bf989e0`  
**Stage-9.5 run:** `38453776937`  
**Fresh-clone job:** `115491107852`

## Result

The corrected v1.1 fresh-clone verifier produced the intended clean separation:

- verifier tests: **8 passed, 0 failed**;
- independent identity failures: **0**;
- external-artifact blockers: **1**;
- blocker: `system_a_checkpoint_bytes_missing`.

The same-head Stage-9 robustness contract passed and the already-closed Stage 9.5-0 assurance job also passed.

## What reconstructed successfully

The clean runner independently verified:

- frozen Python/runtime/thread identities;
- scenario identity, including cross-platform repository-text and canonical JSON identity;
- frozen preprocessing identity;
- System-A manifest identity and all five checkpoint declarations;
- R0.v2 manifest and all five rule artifacts;
- Stage-8 compact manifest and **109/109** committed compact evidence files;
- Stage-8 confirmatory aggregate identity;
- Stage-9 compact manifest and **357/357** committed compact evidence files;
- Stage-9 aggregate raw/canonical identities;
- Stage-9 execution-plan identity.

No numerical or hash mismatch was found in the committed Stage-8/9 evidence chain.

## Blocking provenance defect

The five frozen System-A checkpoint files required by `system_a_v1.json` are not present in a clean clone and have not been recovered from an authoritative external source.

Frozen checkpoint SHA-256 values:

- seed 0: `514c6d552b3cd680ae966bbb568105bd2871bc68d3a47aded070a70ba0615bd1`
- seed 1: `07696c3f580645d9c96ac3e736cfb5eeaa8033f148bf64822e8ee105861cf552`
- seed 2: `7630514cf409256bd2bbe27eca59f881acb238be698b5fdb1ee12bca8e402491`
- seed 3: `cce1ce47db047b9d441bbe6dad9bd53f1ee6ff3ad7d404521cae72a38bccd4b4`
- seed 4: `9b9e56371f3246482998c4efea4829e1e6d5aaf549bb43e1af05e471dfcb9e93`

Repository-side retrieval checks found no GitHub releases, no committed checkpoint directory on the historical `stage3-system-a` branch, no checkpoint-path Git history, and no retained artifacts in the provenance-critical Stage-3 workflow runs checked. The current project session also contains no matching checkpoint files.

An attempted connector-wide sweep of every historical Stage-3 workflow artifact exceeded the connector's per-call ceiling, so this disposition does not claim exhaustive enumeration of every run.

## Classification and claim boundary

This is classified as **Class A for the Stage-9.5 assurance gate** because the frozen protocol treats material provenance/reconstructibility failures as invalidating until resolved.

It does **not** establish that the accepted Stage-8/9 numerical results are wrong: every committed evidence identity checked by the v1.1 verifier matched exactly.

The defect is narrower but still material: an independent clean clone cannot verify the exact frozen neural checkpoint bytes underlying the accepted System-A identity chain.

## Permitted resolution

The blocker may be resolved if the exact five original checkpoint files are recovered from an authoritative archive and each matches its frozen SHA-256.

Regenerating/retraining System A and substituting newly serialized checkpoints is **not** an acceptable resolution of this byte-identity requirement, even if model metrics or parameters appear equivalent.

Stage 9.5-1 therefore remains open. Stage 10 remains hard-gated.

Independent Stage-9.5 assurance packages that do not require those missing bytes may continue, but no later package may reinterpret this blocker as resolved.
