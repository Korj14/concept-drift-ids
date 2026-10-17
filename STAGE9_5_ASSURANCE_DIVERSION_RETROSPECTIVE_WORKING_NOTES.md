# Stage 9.5 Assurance Diversion — Working Retrospective Notes

**Status:** WORKING NOTES / NOT CLOSURE AUTHORITY  
**Purpose:** Preserve the chronology, decisions, reversals, and rationale of the
multi-chat Stage-9.5 assurance diversion so that a complete retrospective can
be written when Stage 9.5 closes.

Do not cite this file as scientific evidence or as a closure artifact. The
authoritative sources remain the frozen protocols, manifests, verification
reports, closure records, Git history, and CI records.

## Why the diversion occurred

Stage 9 itself was already scientifically frozen. Stage 9.5 exposed
reconstructibility and assurance defects that did not justify changing the
accepted Stage-8/9 scientific results, but did prevent a reviewer-resistant
claim that the evidence could be independently reconstructed and replayed.

The work therefore shifted from result generation to fail-closed assurance:
artifact recovery, exact identity verification, replay-equivalence semantics,
order gating, canonical report binding, and explicit prevention of
post-outcome/manual success construction.

## Major arc to preserve in the final retrospective

1. Stage-9.5-0 through -5 were progressively closed or frozen, while
   Stage-9.5-1 remained blocked by missing original external artifacts.
2. Recovery searches established that the five original System-A checkpoints
   and the original Stage-8 heavy archive were not present in the repository or
   known retained GitHub artifacts. Regeneration/retraining was explicitly
   rejected as a substitute for the authoritative bytes.
3. Stage-9.5-6 initially inherited a historical full-seed rerun design whose
   exact-hash gating mixed scientific content with non-replayable runtime and
   timing diagnostics.
4. Replay-equivalence v1.1 froze the permitted diagnostic projections while
   preserving all scientific fields fail-closed.
5. The work-package order gate was hardened so 9.5-7/8/9 cannot unlock from
   file existence, placeholders, malformed records, wrong historical lineage,
   unresolved Class-A defects, or unlinked hashes.
6. A temporary attempt to require GitHub Actions workflow/job/artifact IDs for
   recovery/replay closure was backed out after recognizing that the governing
   checkpoint/archive bytes are external and no authoritative CI transfer
   mechanism had been prospectively frozen. Canonical report hashes plus frozen
   scientific/recovery identities remain the closure authority; CI IDs are
   supplemental.
7. Stage-9.5-1 recovery evidence was bound directly to its preserved canonical
   report rather than copied closure booleans, including all five checkpoint
   seeds and all 145 descriptor-linked Stage-8 heavy-file requirements.
8. Stage-9.5-6 replay evidence was likewise bound directly to a canonical
   replay report, audited-head lineage, zero failures/blockers, and
   repository-contained paths.
9. JSON assurance parsing was hardened against malformed contracts,
   non-canonical numbers, duplicate keys, path traversal, hidden failures, and
   report/closure identity mismatches.
10. A replay-report construction contract was frozen so a successful
    replay report cannot be hand-authored after outcomes. The deterministic
    finalizer and comparator identities were separated.
11. The replay-report finalizer was implemented and tested. It derives report
    state from machine comparison evidence and cannot waive comparator
    mismatches.
12. The replay-equivalence comparator was implemented prospectively for
    Phase A, then expanded externally to Phase B and corrected Phase C,
    including frozen self-/transitive-hash projection rules and dedicated
    tests.
13. At head `ba67928766ce4183846db2e08f3819b1fbaedfa8`, the comparator/finalizer
    stack had 75 assurance tests passing. Phase A/B/C projection implementation
    was no longer the non-external blocker.
14. The remaining non-external Stage-9.5-6 blocker became machine-verifiable
    evidence for replay step 1: reconstruction of Stage-1 interim tables under
    the frozen historical environment.
15. Stage-1 reconstruction evidence was prospectively frozen in
    `data/manifests/stage9_5_6_stage1_reconstruction_evidence_v1.json`.
    Gzip container bytes are explicitly non-authoritative; the required
    identity is exact raw provenance, historical environment/source identity,
    accepted preprocessing-manifest identity, and semantic equality of all
    eight decompressed reconstructed tables to an independently recomputed
    historical structural preprocessing result.

## Scientific invariants maintained throughout

- No accepted Stage-8/9 result was retuned or replaced.
- No confirmatory family was relabeled.
- No Stage-10 outcome was authorized for inspection.
- The frozen Stage-8/9 claim boundary remained unchanged.
- The dominant Stage-8 predictive mechanism remains validated withdrawal of
  stale symbolic authority, not a claim that evolved rules broadly outperform
  neural adaptation.
- Drift-trigger superiority over periodic maintenance remains unestablished.
- Explanation/coverage outcomes remain mixed and often worse.
- Five seeds remain stochastic replication, not environmental replication.
- External validity remains unresolved.

## Current blockers to carry forward

External:
- `system_a_checkpoint_bytes_missing`
- `stage8_large_artifact_archive_missing`

Non-external:
- `stage1_reconstruction_evidence_verifier_not_implemented`

After these are resolved, the intended order remains:
Stage-9.5-1 recovery closure -> Stage-9.5-6 historical replay closure ->
revalidate 9.5-7 -> rerun/revalidate 9.5-8 -> run 9.5-9 hostile review last ->
zero unresolved Class A -> Stage 9.5 closure -> only then Stage 10 access.

## Final retrospective requirements

When Stage 9.5 closes, replace these working notes with a reviewer-facing
retrospective that includes:

- chronological timeline across the chats and Git commits;
- original defect or uncertainty at each turn;
- classification as scientific, provenance, software-assurance, or scope;
- what was changed and what was deliberately not changed;
- reversals/backouts and why they were necessary;
- exact evidence showing accepted Stage-8/9 science remained unchanged;
- final blocker-resolution chain;
- CI/run/report identities supporting closure;
- lessons for preventing this assurance diversion in future stages.

The final document should distinguish historical dead ends from the accepted
final procedure rather than presenting the path as if it had been linear.
