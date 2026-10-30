# Stage 9.5-6 Large Artifact Archive Blocker

**Status:** OPEN / BLOCKED  
**Classification:** Class A — provenance/reconstructibility  
**Stage-8/9 numerical evidence changed:** no

## Accepted archive requirement

The accepted Stage-8 compact manifest explicitly records:

- `adaptive_checkpoint_bytes_in_git: false`;
- `large_prediction_traces_in_git: false`;
- `large_artifact_archive_required_for_publication: true`;
- `large_artifact_root: artifacts/cd_primary_v1`.

The compact export retains 109 selected evidence files plus hashes/descriptors for omitted heavy outputs. It was never declared to replace the full large artifact archive.

## Current recovery state

The declared `artifacts/cd_primary_v1` archive is not present in:

- the repository tree;
- retained artifacts for the accepted Stage-8 workflow runs checked;
- GitHub releases;
- the current Project file surface.

No new archive source has been identified.

## Why this now blocks 9.5-6

The separately preserved identity-replay defect requires diagnostic execution timings to be removed from fresh-vs-accepted Phase-B comparison.

The accepted arm manifests retain the original `maintenance.jsonl` raw hashes, but the actual maintenance records are not in the compact export. Because those records contain both scientific lifecycle content and measured timing fields, the original bytes are required to construct the accepted timing-stripped record projection without guessing.

A summary-only comparison would be weaker and was not the frozen replay-equivalence claim. The project must not lower the assurance target after discovering that the original detailed evidence is unavailable.

## Interpretation

This is independent of:

1. `system_a_checkpoint_bytes_missing`; and
2. the historical non-replayable upstream-manifest identity defect.

It does not show that Stage-8/9 metrics or causal findings are wrong. It shows that the full accepted heavy evidence required for strong external reconstruction is presently unavailable.

## Valid resolution

Recover an authoritative copy of the original `artifacts/cd_primary_v1` tree/archive and verify every recovered file against the accepted committed descriptors before use.

Do not regenerate a new archive and label it the original accepted archive.

Until recovery, Stage 9.5-6 remains Class-A blocked and Stage 10 remains prohibited.
