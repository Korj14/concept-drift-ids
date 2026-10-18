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
16. The Stage-1 reconstruction verifier was then implemented prospectively in
    `tools/stage9_5/stage1_reconstruction_evidence.py`. It executes the exact
    historical preprocessing Git blob after SHA-1 verification, independently
    recomputes the structural transformation, verifies the frozen dependency
    environment and all eight raw SHA-256 identities, and derives the canonical
    reconstruction report without a manual success path.
17. The replay comparator was bound to that canonical Stage-1 report rather
    than a manually supplied boolean. It verifies the report's canonical hash,
    required success fields, fixed evidence path, and Git ancestry before
    clearing the Stage-1 blocker, and carries the Stage-1 report hash into the
    comparison evidence.
18. The replay-report finalizer was additionally hardened to verify the
    comparator evidence's own embedded canonical SHA-256 before accepting it,
    closing the provenance chain from Stage-1 reconstruction through comparator
    evidence to the final replay report.
19. On 17 October 2026 the eight CICIDS2017 raw CSVs mounted in the current
    working environment were independently re-hashed and matched all eight
    frozen Stage-1 raw identities exactly. The same environment reported
    Python 3.13.5 rather than the required historical Python 3.11.9, so it was
    explicitly rejected as an authoritative Stage-1 execution environment.
    The exact operator procedure, success predicate, output path, and
    environment boundary were frozen in
    `STAGE9_5_6_STAGE1_RECONSTRUCTION_EXECUTION_HANDOFF.md` rather than
    weakening the historical-environment requirement.

20. The current execution environment was checked for a local authoritative
    Stage-1 route. All eight mounted raw CSVs were already known to match the
    frozen SHA-256 identities, but the container exposed only Python 3.13.5 and
    no installed Python 3.11.9 interpreter. The installed `uv` tool likewise
    reported no local 3.11.9 interpreter, and the container had no outbound
    GitHub/DNS access to provision one. The official UNB CIC-IDS2017 page still
    identifies `MachineLearningCSV.zip` as the published CSV bundle, but the
    linked CIC download form returned a server error during this tranche.
    Therefore no newly discovered network/mirror acquisition path was promoted
    to closure authority. Exact raw-file hashes plus the frozen historical
    environment remain authoritative, and the Stage-1 execution handoff
    remains the accepted route.


21. The Stage-1 reconstruction report provenance envelope was hardened after
    review showed that canonical content, success fields, path, and Git ancestry
    alone did not bind the report to the exact verifier implementation and
    frozen Stage-1 contract bytes. The verifier now embeds
    `contract_id`, `contract_canonical_sha256`, `verifier_id`, and
    `verifier_source_sha256`; the replay comparator recomputes and verifies
    those identities before accepting the report. Stage-9.5 assurance Python
    sources were also bound to repository-canonical LF via `.gitattributes`
    so source-byte SHA-256 identities remain portable across Windows/Linux
    checkouts. This changed assurance provenance only; Stage-1 structural
    preprocessing semantics and accepted Stage-8/9 science remained unchanged.

22. A final local-runtime preflight checked one additional execution surface not
    previously recorded: cached/local container or interpreter provisioning.
    The working environment exposed no `python3.11` or `python3.11.9`
    executable, no Docker/Podman/nerdctl runtime, no pyenv/conda/mamba-style
    environment manager, and no obvious cached Python-3.11 interpreter under
    the inspected local roots. This confirmed that the present container still
    cannot produce authoritative Stage-1 evidence without external provisioning
    of the frozen Python 3.11.9 environment. The historical-environment
    requirement was not weakened.

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
- none currently identified in the frozen Stage-9.5-6 replay construction
  pipeline. `stage1_reconstruction_evidence_not_verified` was resolved on
  17 October 2026 by the preserved canonical Stage-1 reconstruction report.

After the external blockers are resolved, the intended order remains:
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

23. On 17 October 2026 a subsequent chat resumed after the assurance branch had advanced externally by 43 commits from the previously observed Phase-A-only comparator head. The delta was reconciled before any mutation. It showed that Phase-B projection, Phase-C precondition/output comparison, Stage-1 reconstruction evidence, report-provenance binding, and the requested multi-chat retrospective notes had already been implemented prospectively. Exact-head CI at `dfc7b936014ff3f8201ab0727266023d1aa99cc8` showed 86 assurance-contract tests passing, the unchanged Stage-9.5-5 discovery baseline of Ruff 154 / mypy 55, fresh-clone reconstruction at 0 identity failures / 2 external-artifact blockers, the work-package order gate locked, and 9.5-7/8/9 skipped. The current execution environment was rechecked and still exposed Python 3.13.5 only, with no Python 3.11.9 interpreter. The connected GitHub capability could list/download existing workflow artifacts but exposed no authoritative arbitrary-binary upload/release-asset route for transferring the eight local raw CSVs into a Python-3.11.9 runner. No new transfer mechanism was invented or promoted after this observation; the frozen Stage-1 execution handoff remains authoritative.

24. The Stage-1 non-external blocker was then cleared through a prospectively
    added one-shot GitHub Actions execution path without changing the frozen
    Stage-1 scientific/reconstruction contract. The execution path itself
    preserved several failed attempts rather than hiding them. Run
    `39029867251` installed the exact Python 3.11.9 / frozen dependency
    environment but a guessed mirror-root URL returned HTTP 404 before any raw
    bytes were trusted. A subsequent workflow edit at `a34faee2...` was
    corrupted by JavaScript replacement-string semantics and produced a
    no-job YAML/startup failure (`39030072837`); the workflow was rebuilt
    whole-file rather than patched again. Run `39030232104`, job
    `117389044176`, then successfully acquired the transport bundle through
    Git LFS metadata, extracted it, and verified all eight frozen CICIDS2017
    CSV SHA-256 identities, but failed before verifier preflight with
    `ModuleNotFoundError: concept_drift_ids` because the harness omitted
    `PYTHONPATH=src`. That import-path defect was corrected without changing
    the verifier or contract.

25. Authoritative Stage-1 execution then succeeded on assurance head
    `58b3e42cdeeddea28f7cb20268ed9912684adba3`, GitHub Actions run
    `39030450159`, job `117389666439`. Python 3.11.9 and the complete
    frozen dependency lock installed successfully; the Git-LFS transport,
    extraction, and all eight frozen raw CSV SHA-256 checks passed before
    preprocessing. The unchanged frozen verifier reconstructed and
    independently recomputed all eight Stage-1 interim tables. Its canonical
    report passed with 8/8 raw files, 8/8 interim tables, zero semantic
    mismatches, empty failures/blockers, and accepted preprocessing-manifest
    canonical SHA-256. The report canonical SHA-256 is
    `4bafa772f9737d934f40c90bf7be8d80a62108cf89a9c74895fbe5c12c4a88af`.
    Independent post-run checks also recomputed the frozen contract canonical
    SHA-256 `049be3a211b613e3b37507182aa23bfd83c2289b9f08feeb033b39f8e0a29ca1`
    and verifier-source SHA-256
    `3c21500ae9faafd0a6588395662db71046e37978072e511e6519fa9bebff68a9`,
    exactly matching the report. The preserved report was committed unchanged
    at its frozen path; the additive closure record is
    `STAGE9_5_6_STAGE1_RECONSTRUCTION_EVIDENCE_CLOSURE.md`. The transport
    mirror remained supplemental only: authority came from the pre-frozen
    eight raw-file identities and the frozen verifier/contract.

26. On 17 October 2026 the next continuation found that the assurance branch had
    advanced externally by 54 commits from the previously observed
    `cf78ba076a12693bc1b89ac52181fc8f20091fdc` head to
    `3a0f4746cf76527796823b6147723400c1be1d1f`. The delta was reconciled
    before mutation. It showed that the replay comparator had already advanced
    to prospectively frozen Phase-A, Phase-B, Phase-C precondition/failure
    lineage, and corrected Phase-C seed-0 output comparison; the deterministic
    finalizer was frozen; Stage-1 authoritative reconstruction had been closed;
    and the requested multi-chat retrospective working notes were already being
    maintained. Exact-head CI on `3a0f4746...` showed Stage-9 robustness
    success, 87 assurance-contract tests passing, the unchanged Ruff 154 /
    mypy 55 static discovery baseline, fresh-clone reconstruction at 0 identity
    failures / 2 external-artifact blockers, the work-package order gate locked,
    and 9.5-7/8/9 skipped. During reconciliation, the human-readable replay
    construction contract was found to lag the machine contract by still
    naming `stage1_reconstruction_evidence_not_verified` as current. That
    stale governance text was corrected without changing the machine contract,
    comparator, finalizer, Stage-1 evidence, or accepted Stage-8/9 science.

27. The same continuation audited whether recovery of the two external artifact
    families would be sufficient to execute the frozen replay without another
    procedural design cycle. The comparator/finalizer CLIs were complete, but
    the repository lacked one end-to-end operator handoff joining Stage-9.5-1
    recovery, historical Phase-A/B execution at
    `bfa14b942e4a5b2fbfa8aa3c43728a7f1cd81645`, reproduction of the
    original Phase-C v1 seed-0 failure, regeneration of the correction config
    from `79ddc4c6d6dea52c7cabc55a6d082448fc24fcf9`, the required
    correction-config-only child commit, corrected Phase-C seed-0 execution,
    deterministic comparator/finalizer, closure metadata, and the fail-closed
    order gate. That procedural gap was closed by prospectively freezing
    `STAGE9_5_6_HISTORICAL_REPLAY_EXECUTION_HANDOFF.md`. The handoff adds no
    scientific semantics: it only sequences already-frozen commands and
    identities, keeps heavy recovered/fresh replay bytes external, requires the
    same-head Stage-9 success, and ends with
    `later_packages_unlocked=true` as the only acceptable predecessor-gate
    result. At the end of this episode there remained no identified
    non-external Stage-9.5-6 implementation blocker; the two unresolved blockers
    remained `system_a_checkpoint_bytes_missing` and
    `stage8_large_artifact_archive_missing`.

28. A final top-level status sweep after freezing the historical replay handoff
    found that `README.md` still described
    `stage1_reconstruction_evidence_not_verified` as the remaining
    non-external Stage-9.5-6 blocker, even though the machine construction
    contract, Stage-1 closure record, order-governance overlay, and preserved
    report already showed that blocker resolved. The README was corrected to
    name the authoritative Stage-1 report/canonical SHA-256, state that no
    non-external Stage-9.5-6 implementation/evidence blocker is currently
    identified, and direct future operators to
    `STAGE9_5_6_HISTORICAL_REPLAY_EXECUTION_HANDOFF.md`. This was a
    documentation-status reconciliation only; no verifier, comparator,
    finalizer, Stage-8/9 evidence, claim boundary, or Stage-10 gate changed.

29. A subsequent live-state reconciliation at head `ddcc8c21dff5c30d01c2a5935ae609406b804e8f` found one remaining historical/current-status ambiguity: the prospectively frozen replay-construction manifest still retained its earlier status-only fields `deterministic_producer.comparator_status = phase_a_b_c_implemented_stage1_evidence_blocked` and `current_blocker = stage1_reconstruction_evidence_not_verified`, even though the authoritative Stage-1 closure/report, README, order-governance overlay, comparator/finalizer stack, and historical replay handoff all showed Stage-1 resolved and no identified non-external Stage-9.5-6 blocker. The frozen construction contract was deliberately **not** rewritten after the fact. Instead, additive machine-readable status overlay `data/manifests/stage9_5_6_current_status_v1.json` was committed. It binds the historical frozen construction-contract blob identity and the canonical Stage-1 report identity, marks the stale fields explicitly as historical freeze state, records the current replay pipeline as implemented/frozen, and states that the only unresolved Stage-9.5-6 blockers are the two external artifact families. This preserved the historical audit trail while eliminating ambiguity for future closure work and the final retrospective.

30. On 17 October 2026 a later continuation resumed from the previously
    observed Phase-A-era head but found the assurance branch already at
    `ffb2645cce0724916f385bbd59b9d652b8aec0f0`, 61 commits ahead of
    `cf78ba076a12693bc1b89ac52181fc8f20091fdc`. The delta was reconciled
    before mutation. It confirmed that the full deterministic replay stack
    (Phase A, Phase B, Phase-C failure-lineage/correction-config checks, and
    corrected Phase-C seed-0 output comparison), replay-report finalizer,
    authoritative Stage-1 reconstruction evidence/closure, historical replay
    execution handoff, current-status overlay, and the requested multi-chat
    retrospective working notes were already in place. The exact-head Stage-9
    robustness run `39033910515` completed successfully. Stage-9.5 assurance
    run `39033910546` had the intended top-level failure shape: the
    assurance-contract job passed with **87 tests**, statistical oracle,
    targeted mutations, causal properties, and the semantic work-package order
    gate all passed; static discovery remained the already-accepted
    `ruff=154, mypy=55` baseline; fresh-clone reconstruction remained
    `0 identity failures / 2 external-artifact blockers`; and
    Stage-9.5-7/8/9 were skipped because
    `later_packages_unlocked=false`. During this reconciliation, PR #21's
    descriptive body was found stale: it still presented the historical
    replay-invariance defect and Stage-1 predecessor issue as current blockers.
    The PR metadata was corrected to match
    `data/manifests/stage9_5_6_current_status_v1.json`: no non-external
    Stage-9.5-6 implementation/evidence blocker is currently identified, and
    the only unresolved blockers are
    `system_a_checkpoint_bytes_missing` and
    `stage8_large_artifact_archive_missing`. This was governance/status
    reconciliation only; no repository science, verifier, comparator,
    finalizer, Stage-1 report, accepted Stage-8/9 evidence, claim boundary, or
    Stage-10 gate was changed.

31. On 17 October 2026 the continuation at exact assurance head
    `309f32c595dca8b06a3bcea2c2db233506c424a3` performed a closure-readiness
    audit after reconciling the externally advanced branch. Exact-head Stage-9
    robustness run `39034242366` completed successfully. Stage-9.5 assurance
    run `39034242363` had the expected fail-closed shape: the assurance-contract
    job passed with **87 tests**; statistical oracle, targeted mutations, causal
    properties, and the work-package order gate all passed; static discovery
    remained the accepted `ruff=154, mypy=55` baseline; fresh-clone
    reconstruction remained `0 identity failures / 2 external-artifact
    blockers`; and Stage-9.5-7/8/9 were skipped with
    `later_packages_unlocked=false`.

    The closure-readiness audit mapped every field required by
    `data/manifests/stage9_5_6_closure_order_gate_v1.json` to an already-frozen
    authoritative source: Stage-9.5-1 recovery report, deterministic replay
    comparator/finalizer report, same-head Stage-9 success, historical replay
    identities, canonical report hashes, and explicit closure references. The
    end-to-end operator sequence is already frozen in
    `STAGE9_5_6_HISTORICAL_REPLAY_EXECUTION_HANDOFF.md`. No additional
    non-external implementation, protocol, provenance, or closure-metadata
    blocker was identified. Further software hardening was deliberately not
    added merely to consume time or create a new gate.

    Therefore the only unresolved prerequisites to advancing Stage-9.5 are the
    two original external evidence families:
    `system_a_checkpoint_bytes_missing` and
    `stage8_large_artifact_archive_missing`. Once recovered, the accepted
    sequence is Stage-9.5-1 verification/closure -> historical replay ->
    comparator/finalizer -> Stage-9.5-6 closure/order-gate unlock -> 9.5-7 ->
    9.5-8 -> 9.5-9 -> zero unresolved Class-A defects -> finalize the multi-chat
    assurance-diversion retrospective -> close Stage 9.5 -> only then Stage 10.

32. On 17 October 2026 this continuation resumed from the previously observed
    Phase-A-era head `cf78ba076a12693bc1b89ac52181fc8f20091fdc` but found the
    assurance branch already at `bd44bb9198acc11e837d47c938c213e86eb500d7`,
    **63 commits ahead**. The delta was reconciled before any mutation. It
    confirmed that the deterministic replay comparator had already been
    prospectively frozen for Phase A, Phase B, Phase-C failure-lineage and
    correction-config preconditions, and corrected Phase-C seed-0 output
    comparison; the replay-report finalizer was frozen; authoritative Stage-1
    reconstruction evidence had been closed; an end-to-end historical replay
    execution handoff had been frozen; and the multi-chat diversion notes were
    already being maintained. Exact-head Stage-9 robustness run
    `39036358382` passed. Stage-9.5 assurance run `39036358349` had the
    expected fail-closed top-level shape: the assurance-contract job passed
    with **87 tests**; statistical oracle, causal properties, targeted
    mutations, and the semantic work-package order gate all passed; static
    discovery remained the accepted `ruff=154, mypy=55` baseline; fresh-clone
    reconstruction remained `0 identity failures / 2 external-artifact
    blockers`; `later_packages_unlocked=false`; and Stage-9.5-7/8/9 were
    skipped. The additive current-status overlay at
    `data/manifests/stage9_5_6_current_status_v1.json` was checked against the
    live branch and remained accurate: no non-external Stage-9.5-6
    implementation/evidence blocker is currently identified. The only
    unresolved prerequisites remain
    `system_a_checkpoint_bytes_missing` and
    `stage8_large_artifact_archive_missing`. No additional comparator,
    protocol, scientific, or gate hardening was added merely to consume time;
    this continuation instead preserved the reconciliation in the working
    retrospective for final Stage-9.5 closure documentation.

33. On 17 October 2026 this continuation resumed after the user explicitly
    reiterated that the entire multi-chat Stage-9.5 assurance diversion must be
    documented at closure. The live assurance branch had advanced from the
    previously observed Phase-A-era head
    `cf78ba076a12693bc1b89ac52181fc8f20091fdc` to
    `4c49f772d30739c5119f49eba4081de81651f9eb`, **64 commits ahead**.
    The delta was reconciled before mutation. It confirmed that the deterministic
    replay comparator is prospectively frozen for Phase A, Phase B, Phase-C
    preconditions/failure lineage, and corrected Phase-C seed-0 output
    comparison; the replay-report finalizer is frozen; authoritative Stage-1
    reconstruction evidence is closed; the historical replay execution handoff
    is frozen; and the additive current-status overlay identifies no remaining
    non-external Stage-9.5-6 implementation/evidence blocker.

    Exact-head Stage-9 robustness run `39036901931` passed. Stage-9.5
    assurance run `39036901857` had the expected fail-closed top-level
    shape: assurance-contract passed with **87 tests**; statistical oracle,
    causal properties, targeted mutations, and the semantic work-package order
    gate all passed; static discovery remained the already accepted
    `ruff=154, mypy=55` baseline; fresh-clone reconstruction remained
    `0 identity failures / 2 external-artifact blockers`;
    `later_packages_unlocked=false`; and Stage-9.5-7/8/9 were skipped because
    the Stage-9.5-6 closure/success records do not yet exist.

    The only unresolved prerequisites therefore remain the two original
    external evidence families:
    `system_a_checkpoint_bytes_missing` and
    `stage8_large_artifact_archive_missing`. No additional comparator,
    finalizer, protocol, provenance, or gate hardening was introduced in this
    continuation. Instead, this episode was added to the working retrospective
    so the eventual reviewer-facing Stage-9.5 closure document can reconstruct
    the diversion from repository evidence rather than chat memory.

34. On 17 October 2026 this continuation resumed after the user again
    emphasized that the entire Stage-9.5 assurance diversion, spanning multiple
    chats, must be documented at final Stage-9.5 closure rather than left in
    transient conversation history. The live assurance branch had advanced from
    the previously observed Phase-A-era head
    `cf78ba076a12693bc1b89ac52181fc8f20091fdc` to
    `bad2bbd3c20b8b557d25b63eb144d74aea6b3728`, **65 commits ahead**.
    The delta was reconciled before mutation.

    The reconciliation confirmed that the work which had previously appeared
    to remain ahead was already complete and prospectively frozen in the
    repository: deterministic replay comparison for Phase A, Phase B,
    Phase-C failure-lineage/correction-config preconditions, and corrected
    Phase-C seed-0 outputs; the deterministic replay-report finalizer;
    authoritative Stage-1 reconstruction evidence and closure; the historical
    replay execution handoff; the additive current-status overlay; and this
    multi-chat retrospective working record. The authoritative current-status
    overlay records **no identified non-external Stage-9.5-6 blocker**. The only
    unresolved prerequisites remain the two external evidence families:
    `system_a_checkpoint_bytes_missing` and
    `stage8_large_artifact_archive_missing`.

    Exact-head Stage-9 robustness run `39038815811` completed successfully.
    Stage-9.5 assurance run `39038815677` showed the expected fail-closed
    shape. The assurance-contract job passed with **87 tests**; statistical
    oracle, causal properties, targeted mutations, and the semantic
    work-package order gate passed; fresh-clone reconstruction reported
    **0 identity failures / 2 external-artifact blockers**; static discovery
    remained the already accepted **ruff=154 / mypy=55** baseline;
    `later_packages_unlocked=false`; and Stage-9.5-7/8/9 were skipped because
    the Stage-9.5-6 closure/success records do not yet exist.

    No new comparator, finalizer, protocol, scientific, provenance, or gate
    semantics were added in this continuation. That restraint is intentional:
    further software work would not remove the actual blockers. This entry
    exists to preserve the cross-chat chronology requested by the user and to
    ensure the eventual reviewer-facing Stage-9.5 closure retrospective can be
    assembled from committed repository evidence. The remaining authoritative
    sequence is: recover/verify the five exact original System-A checkpoints ->
    recover/verify the original Stage-8 heavy archive at 145/145 ->
    close Stage-9.5-1 -> execute the frozen historical replay handoff ->
    comparator/finalizer -> Stage-9.5-6 closure/order-gate unlock -> revalidate
    9.5-7 -> rerun/revalidate 9.5-8 -> run 9.5-9 hostile review last -> require
    zero unresolved Class-A defects -> finalize the multi-chat diversion
    retrospective -> close Stage 9.5 -> only then authorize Stage 10.

35. On 17 October 2026 this continuation resumed after the user explicitly
    instructed the assurance work to proceed autonomously unless genuine user
    input became necessary, while reiterating that the full Stage-9.5 diversion
    spanning multiple chats must be documented at closure. The live assurance
    branch had advanced from the previously observed Phase-A-era head
    `cf78ba076a12693bc1b89ac52181fc8f20091fdc` to
    `a5da4cb9b9924ee34ef031f94bda9aac9cc31748`, **66 commits ahead**.
    The delta was reconciled before any mutation.

    The reconciliation showed that no Phase-B/Phase-C implementation work
    remained to be done: deterministic replay comparison for Phase A, Phase B,
    Phase-C failure-lineage/correction-config preconditions, and corrected
    Phase-C seed-0 outputs was already prospectively frozen; the deterministic
    replay-report finalizer was frozen; authoritative Stage-1 reconstruction
    evidence and closure were complete; the end-to-end historical replay
    execution handoff was frozen; the additive current-status overlay was in
    place; and the multi-chat retrospective working record was already being
    maintained. The current-status overlay continued to identify **no
    non-external Stage-9.5-6 implementation/evidence blocker**.

    Exact-head Stage-9 robustness run `39039063193` completed successfully.
    Stage-9.5 assurance run `39039063211` had the expected fail-closed shape:
    the assurance-contract job passed with **87 tests**; statistical oracle,
    causal properties, targeted mutations, and the semantic work-package order
    gate passed; fresh-clone reconstruction remained **0 identity failures / 2
    external-artifact blockers**; static discovery remained the already
    accepted **ruff=154 / mypy=55** baseline;
    `later_packages_unlocked=false`; and Stage-9.5-7/8/9 were skipped because
    the Stage-9.5-6 closure/success records do not yet exist.

    No new comparator, finalizer, protocol, scientific, provenance, or gate
    semantics were introduced. The only unresolved prerequisites remain
    `system_a_checkpoint_bytes_missing` and
    `stage8_large_artifact_archive_missing`. This continuation therefore
    deliberately stopped software hardening at the genuine external-evidence
    boundary and preserved the episode in this working retrospective so the
    eventual reviewer-facing Stage-9.5 closure account can be reconstructed
    from repository evidence rather than transient chat history.

36. On 17 October 2026 this continuation resumed after the user again requested
    autonomous progress and explicitly reminded the project that the entire
    Stage-9.5 assurance diversion spanning multiple chats must be documented at
    final closure. The live assurance branch had advanced from the previously
    observed Phase-A-era head
    `cf78ba076a12693bc1b89ac52181fc8f20091fdc` to
    `432ddd2c559375bc706330dd375ea36aebc9e84a`, **67 commits ahead**.
    The delta was reconciled before any mutation.

    That reconciliation confirmed the authoritative current frontier rather
    than repeating obsolete Phase-B/Phase-C implementation work. The branch
    already contains prospectively frozen deterministic comparison for Phase A,
    Phase B, Phase-C failure-lineage/correction-config preconditions, and
    corrected Phase-C seed-0 outputs; the deterministic replay-report
    finalizer; authoritative Stage-1 reconstruction evidence and closure; the
    frozen historical replay execution handoff; the additive current-status
    overlay; and this multi-chat retrospective working record. The current
    status manifest continues to identify **no non-external Stage-9.5-6
    implementation/evidence blocker**.

    Exact-head Stage-9 robustness run `39039358856` completed successfully.
    Stage-9.5 assurance run `39039358894` had the expected fail-closed
    top-level shape: assurance-contract passed with **87 tests**; statistical
    oracle, causal properties, targeted mutations, and the semantic
    work-package order gate all passed; fresh-clone reconstruction remained
    **0 identity failures / 2 external-artifact blockers**; static discovery
    remained the already accepted **ruff=154 / mypy=55** baseline;
    `later_packages_unlocked=false`; and Stage-9.5-7/8/9 were skipped because
    the Stage-9.5-6 closure/success records do not yet exist.

    The only unresolved prerequisites remain the two original external evidence
    families: `system_a_checkpoint_bytes_missing` and
    `stage8_large_artifact_archive_missing`. No new comparator, finalizer,
    protocol, scientific, provenance, or gate semantics were introduced in
    this continuation. The sole repository mutation was this retrospective
    entry, preserving the cross-chat chronology so the eventual reviewer-facing
    Stage-9.5 closure retrospective can be assembled from committed evidence
    rather than conversation memory. The authoritative sequence remains:
    recover/verify five exact original System-A checkpoints -> recover/verify
    the original Stage-8 heavy archive at 145/145 -> close Stage-9.5-1 ->
    execute the frozen historical replay handoff -> comparator/finalizer ->
    Stage-9.5-6 closure/order-gate unlock -> revalidate 9.5-7 ->
    rerun/revalidate 9.5-8 -> run 9.5-9 hostile review last -> require zero
    unresolved Class-A defects -> finalize the multi-chat assurance-diversion
    retrospective -> close Stage 9.5 -> only then authorize Stage 10.

37. On 17 October 2026 this continuation resumed after the user again instructed
    the assurance work to proceed and explicitly reiterated that the complete
    Stage-9.5 diversion spanning multiple chats must be documented at final
    closure. The live assurance branch had advanced from the previously
    observed Phase-A-era head
    `cf78ba076a12693bc1b89ac52181fc8f20091fdc` to
    `b84f636205846fe06ef5fed67da61c05844f342d`, **68 commits ahead**.
    The delta was reconciled before any mutation.

    The reconciliation confirmed that the apparent remaining comparator work
    was obsolete. The branch already contains prospectively frozen
    deterministic replay comparison for Phase A, Phase B, Phase-C
    failure-lineage/correction-config preconditions, and corrected Phase-C
    seed-0 outputs; the deterministic replay-report finalizer; authoritative
    Stage-1 reconstruction evidence and closure; the frozen end-to-end
    historical replay execution handoff; the additive current-status overlay;
    and the multi-chat assurance-diversion working record. The authoritative
    current-status overlay identifies **no remaining non-external Stage-9.5-6
    implementation/evidence blocker**.

    Exact-head Stage-9 robustness run `39039998351` completed successfully.
    Stage-9.5 assurance run `39039998269` had the expected fail-closed shape:
    the assurance-contract job passed with **87 tests**; statistical oracle,
    causal properties, targeted mutations, and the semantic work-package order
    gate all passed; static discovery remained the already accepted
    **ruff=154 / mypy=55** baseline; fresh-clone reconstruction remained
    **0 identity failures / 2 external-artifact blockers**;
    `later_packages_unlocked=false`; and Stage-9.5-7/8/9 were skipped because
    the Stage-9.5-6 closure/success records do not yet exist.

    No new comparator, finalizer, protocol, scientific, provenance, or gate
    semantics were introduced in this continuation. The only repository
    mutation was this retrospective entry, preserving the requested cross-chat
    chronology. The only unresolved prerequisites remain
    `system_a_checkpoint_bytes_missing` and
    `stage8_large_artifact_archive_missing`. The authoritative sequence
    remains: recover/verify the five exact original System-A checkpoints ->
    recover/verify the original Stage-8 heavy archive at 145/145 -> close
    Stage-9.5-1 -> execute the frozen historical replay handoff ->
    comparator/finalizer -> Stage-9.5-6 closure/order-gate unlock -> revalidate
    9.5-7 -> rerun/revalidate 9.5-8 -> run 9.5-9 hostile review last -> require
    zero unresolved Class-A defects -> finalize the multi-chat
    assurance-diversion retrospective -> close Stage 9.5 -> only then authorize
    Stage 10.

38. On 17 October 2026 this continuation resumed after the user explicitly
    instructed the project to proceed but to regroup if the forward path was
    genuinely blocked, while retaining the standing requirement that the full
    Stage-9.5 assurance diversion across multiple chats be documented at final
    closure. The live assurance branch had again advanced externally from the
    previously observed Phase-A-era head
    `cf78ba076a12693bc1b89ac52181fc8f20091fdc` to
    `1cbae90534bcb8fd3a824daf85ae4df0e7630d7c`, **69 commits ahead**.
    The delta was reconciled before any mutation.

    That reconciliation confirmed that further comparator/protocol hardening
    would be artificial rather than blocker-removing work. The branch already
    contains prospectively frozen deterministic replay comparison for Phase A,
    Phase B, Phase-C failure-lineage/correction-config preconditions, and
    corrected Phase-C seed-0 outputs; the deterministic replay-report
    finalizer; authoritative Stage-1 reconstruction evidence and closure; the
    frozen historical replay execution handoff; the additive current-status
    overlay; and this multi-chat retrospective. The authoritative current-status
    manifest states that **no non-external Stage-9.5-6 implementation/evidence
    blocker is currently identified**.

    Exact-head Stage-9 robustness run `39041093691` completed successfully.
    Stage-9.5 assurance run `39041093826` had the expected fail-closed shape:
    assurance-contract passed with **87 tests**; statistical oracle, causal
    properties, targeted mutations, and the semantic work-package order gate
    passed; static discovery remained the accepted **ruff=154 / mypy=55**
    baseline; fresh-clone reconstruction remained **0 identity failures / 2
    external-artifact blockers**; `later_packages_unlocked=false`; and
    Stage-9.5-7/8/9 were skipped because the Stage-9.5-6 closure/success records
    do not yet exist.

    In response to the explicit regroup instruction, no new comparator,
    finalizer, protocol, scientific, provenance, or gate semantics were added.
    The project deliberately stopped software expansion at the genuine external
    evidence boundary. The only unresolved prerequisites remain
    `system_a_checkpoint_bytes_missing` and
    `stage8_large_artifact_archive_missing`. The authoritative path remains:
    recover/verify the five exact original System-A checkpoints -> recover/verify
    the original Stage-8 heavy archive at 145/145 -> close Stage-9.5-1 ->
    execute the frozen historical replay handoff -> comparator/finalizer ->
    Stage-9.5-6 closure/order-gate unlock -> revalidate 9.5-7 ->
    rerun/revalidate 9.5-8 -> run 9.5-9 hostile review last -> require zero
    unresolved Class-A defects -> finalize this multi-chat diversion
    retrospective -> close Stage 9.5 -> only then authorize Stage 10.

    This continuation therefore records a deliberate boundary decision rather
    than another hardening cycle: progress is presently blocked by recovery of
    original external evidence bytes, not by missing repository implementation.

30. On 17 October 2026 the next continuation resumed after the assurance branch
    had advanced externally by 70 commits from the previously observed
    Phase-A comparator head `cf78ba076a12693bc1b89ac52181fc8f20091fdc`
    to `b6b45ddc09cde0ae4b6ec96eb363d34d190797fe`. The delta was
    reconciled before any mutation. It showed that Phase-B comparison,
    Phase-C precondition/failure-lineage validation, corrected Phase-C seed-0
    output comparison, authoritative Stage-1 reconstruction evidence, the
    deterministic finalizer, and the end-to-end historical replay execution
    handoff had already been prospectively frozen. The additive current-status
    overlay reported no identified non-external Stage-9.5-6 blocker; the only
    unresolved blockers remained `system_a_checkpoint_bytes_missing` and
    `stage8_large_artifact_archive_missing`.

    Exact-head CI on `b6b45ddc09cde0ae4b6ec96eb363d34d190797fe`
    showed Stage-9 robustness success, 87 assurance-contract tests passing,
    the unchanged Stage-9.5-5 discovery baseline of Ruff 154 / mypy 55,
    fresh-clone reconstruction at 0 identity failures / 2 external-artifact
    blockers, the work-package order gate locked with
    `later_packages_unlocked=false`, and Stage-9.5-7/8/9 skipped. A direct
    CLI audit of `STAGE9_5_6_HISTORICAL_REPLAY_EXECUTION_HANDOFF.md`
    against the live Stage-9.5-1 verifier, replay comparator, replay-report
    finalizer, and order-gate interfaces found the frozen handoff command
    surface consistent with the implementations. The 11 commits after the
    current-status overlay's observed head `ddcc8c21...` changed only the
    additive status/retrospective documentation and introduced no new replay,
    assurance, or scientific semantics. No additional assurance mechanism was
    added in this continuation because the remaining bottleneck is external
    recovery rather than an identified repository-side implementation gap.

39. On 17 October 2026 this continuation resumed after the user again instructed
    the project to proceed and reiterated that the complete Stage-9.5 assurance
    diversion spanning multiple chats must be documented at final closure. The
    live assurance branch had advanced from the previously observed
    Phase-A-era head
    `cf78ba076a12693bc1b89ac52181fc8f20091fdc` to
    `25b864c19ef75f847f698f8c6e30f6f3e024d793`, **71 commits ahead**.
    The delta was reconciled before any mutation.

    Reconciliation showed that the apparent Phase-B design work was obsolete:
    the repository already contains prospectively frozen deterministic replay
    comparison for Phase A, Phase B, Phase-C failure-lineage/correction-config
    preconditions, and corrected Phase-C seed-0 outputs; the deterministic
    replay-report finalizer; authoritative Stage-1 reconstruction evidence and
    closure; the frozen end-to-end historical replay execution handoff; the
    additive current-status overlay; and this multi-chat assurance-diversion
    working record. The current-status overlay identifies **no non-external
    Stage-9.5-6 implementation/evidence blocker**.

    The 12 commits after the status-overlay observation head
    `ddcc8c21dff5c30d01c2a5935ae609406b804e8f` changed only the additive
    current-status/retrospective documentation and introduced no new replay,
    assurance, or scientific semantics. Exact-head Stage-9 robustness run
    `39044660057` completed successfully. Stage-9.5 assurance run
    `39044659874` had the expected fail-closed shape: assurance-contract
    passed with **87 tests**; statistical oracle, causal properties, targeted
    mutations, and the semantic work-package order gate passed; static
    discovery remained the accepted **ruff=154 / mypy=55** baseline;
    fresh-clone reconstruction remained **0 identity failures / 2
    external-artifact blockers**; `later_packages_unlocked=false`; and
    Stage-9.5-7/8/9 were skipped because Stage-9.5-6 closure/success evidence
    does not yet exist.

    This continuation deliberately introduced no new comparator, finalizer,
    protocol, scientific, provenance, or order-gate semantics. The project is
    genuinely blocked at the external-evidence boundary. The only unresolved
    prerequisites remain `system_a_checkpoint_bytes_missing` and
    `stage8_large_artifact_archive_missing`. The authoritative next sequence
    remains: recover/verify the five exact original System-A checkpoints ->
    recover/verify the original Stage-8 heavy archive at 145/145 -> close
    Stage-9.5-1 -> execute the frozen historical replay handoff ->
    comparator/finalizer -> Stage-9.5-6 closure/order-gate unlock -> revalidate
    9.5-7 -> rerun/revalidate 9.5-8 -> run 9.5-9 hostile review last -> require
    zero unresolved Class-A defects -> finalize the multi-chat assurance-
    diversion retrospective -> close Stage 9.5 -> only then authorize Stage 10.

    This entry is intentionally part of the final-retrospective evidence chain:
    it records that software expansion was stopped once repository-side
    assurance work was complete, rather than obscuring the true external
    provenance bottleneck.

40. On 17 October 2026 this continuation resumed after the user again instructed
    the assurance work to proceed and reiterated that the entire Stage-9.5
    diversion spanning multiple chats must be documented at final closure. The
    live assurance branch had advanced from the previously observed Phase-A-era
    head `cf78ba076a12693bc1b89ac52181fc8f20091fdc` to
    `6013f6dcc2568f26f05682720dc5a10394dd48ec`, **72 commits ahead**.
    The delta was reconciled before mutation.

    Reconciliation confirmed that the apparent remaining Phase-B/Phase-C work
    was obsolete. The repository already contains prospectively frozen
    deterministic replay comparison for Phase A, Phase B, Phase-C
    failure-lineage/correction-config preconditions, and corrected Phase-C
    seed-0 outputs; the deterministic replay-report finalizer; authoritative
    Stage-1 reconstruction evidence and closure; the frozen end-to-end
    historical replay execution handoff; the additive current-status overlay;
    and this multi-chat assurance-diversion working record. The authoritative
    current-status overlay records **no identified non-external Stage-9.5-6
    implementation/evidence blocker**.

    Exact-head Stage-9 robustness run `39046437404` completed successfully.
    Stage-9.5 assurance run `39046437384` had the expected fail-closed
    top-level shape: the assurance-contract job passed with **87 tests**;
    statistical oracle, causal properties, targeted mutations, and the semantic
    work-package order gate passed; static discovery remained the accepted
    **ruff=154 / mypy=55** baseline; fresh-clone reconstruction remained
    **0 identity failures / 2 external-artifact blockers**;
    `later_packages_unlocked=false`; and Stage-9.5-7/8/9 were skipped because
    the Stage-9.5-6 closure/success records do not yet exist.

    The 17 October Stage-1 reconstruction work introduced a new external-data
    transport surface through the unofficial `bencorn/CICIDS2017` mirror on
    Hugging Face. A targeted recovery check was performed against that new
    surface for the missing System-A checkpoint/archive identifiers. The mirror
    exposes original CICIDS2017 distribution material such as
    `MachineLearningCSV.zip` and related dataset files, not the project-
    generated System-A checkpoints or `artifacts/cd_primary_v1` replay
    archive. It therefore remains supplemental transport for Stage-1 raw inputs
    only and does not reduce either unresolved provenance blocker.

    No new comparator, finalizer, protocol, scientific, provenance, or
    order-gate semantics were added. The project again stopped software
    expansion at the genuine external-evidence boundary. The only unresolved
    prerequisites remain `system_a_checkpoint_bytes_missing` and
    `stage8_large_artifact_archive_missing`. The authoritative next sequence
    remains: recover/verify the five exact original System-A checkpoints ->
    recover/verify the original Stage-8 heavy archive at 145/145 -> close
    Stage-9.5-1 -> execute the frozen historical replay handoff ->
    comparator/finalizer -> Stage-9.5-6 closure/order-gate unlock -> revalidate
    9.5-7 -> rerun/revalidate 9.5-8 -> run 9.5-9 hostile review last -> require
    zero unresolved Class-A defects -> finalize the multi-chat
    assurance-diversion retrospective -> close Stage 9.5 -> only then authorize
    Stage 10.

    This entry is specifically preserved so the final Stage-9.5 reviewer-facing
    retrospective can reconstruct the multi-chat diversion from committed
    repository evidence rather than relying on conversation history.

41. On 17 October 2026 the user again instructed the project to proceed and
    explicitly reiterated that the full Stage-9.5 assurance diversion spanning
    multiple chats must be documented at final closure. The live assurance
    branch had advanced externally from the previously observed Phase-A-era
    head `cf78ba076a12693bc1b89ac52181fc8f20091fdc` to
    `3937ade9b044cf92c7d1baf6d1b7cdfb8d7a450f`, **73 commits ahead**.
    The delta was reconciled before any repository mutation.

    Reconciliation showed that the apparent next task—Phase-B comparator
    design—was obsolete. The branch already contains prospectively frozen
    deterministic comparison for Phase A, Phase B, Phase-C
    failure-lineage/correction-config preconditions, and corrected Phase-C
    seed-0 outputs; the deterministic replay-report finalizer; authoritative
    Stage-1 reconstruction evidence and closure; the frozen end-to-end
    historical replay execution handoff; the additive current-status overlay;
    and this multi-chat diversion record. The authoritative status overlay
    records **no remaining non-external Stage-9.5-6 implementation/evidence
    blocker**.

    The 14 commits after status-observation head
    `ddcc8c21dff5c30d01c2a5935ae609406b804e8f` changed only the additive
    current-status manifest and retrospective working notes; they introduced no
    comparator, finalizer, protocol, gate, or scientific semantic change.

    Exact-head Stage-9 robustness run `39046729976` completed successfully.
    Stage-9.5 assurance run `39046729981` had the expected fail-closed shape:
    the assurance-contract job passed with **87 tests**; statistical oracle,
    causal properties, targeted mutations, and the semantic work-package order
    gate all passed; static discovery remained the accepted **ruff=154 /
    mypy=55** baseline; fresh-clone reconstruction remained **0 identity
    failures / 2 external-artifact blockers**;
    `later_packages_unlocked=false`; and Stage-9.5-7/8/9 were skipped because
    Stage-9.5-6 closure/success evidence does not yet exist.

    This continuation therefore deliberately introduced no new assurance
    mechanism. The only unresolved prerequisites remain
    `system_a_checkpoint_bytes_missing` and
    `stage8_large_artifact_archive_missing`. The authoritative next sequence
    remains: recover/verify the five exact original System-A checkpoints ->
    recover/verify the original Stage-8 heavy archive at 145/145 -> close
    Stage-9.5-1 -> execute the frozen historical replay handoff ->
    comparator/finalizer -> Stage-9.5-6 closure/order-gate unlock -> revalidate
    9.5-7 -> rerun/revalidate 9.5-8 -> run 9.5-9 hostile review last -> require
    zero unresolved Class-A defects -> finalize the reviewer-facing multi-chat
    assurance-diversion retrospective -> close Stage 9.5 -> only then authorize
    Stage 10.

    This entry is preserved specifically to support the user's final-closure
    requirement that the diversion be reconstructed from repository evidence,
    including the repeated live-head reconciliations and the deliberate choice
    to stop software expansion once the true external-evidence boundary was
    reached.

42. On 17 October 2026 this continuation resumed after the user again instructed
    the project to proceed and reiterated that the complete Stage-9.5 assurance
    diversion spanning multiple chats must be documented at final closure. The
    live assurance branch had advanced externally from the previously observed
    Phase-A-era head
    `cf78ba076a12693bc1b89ac52181fc8f20091fdc` to
    `972e4922f6ab94d6219dabdc6d4cd5ce8e2ec429`, **74 commits ahead**.
    The delta was reconciled before any repository mutation.

    Reconciliation confirmed that the apparent planned Phase-B comparator
    tranche was obsolete. The repository already contains prospectively frozen
    deterministic replay comparison for Phase A, Phase B, Phase-C
    failure-lineage/correction-config preconditions, and corrected Phase-C
    seed-0 outputs; the deterministic replay-report finalizer; authoritative
    Stage-1 reconstruction evidence and closure; the frozen end-to-end
    historical replay execution handoff; the additive current-status overlay;
    and this multi-chat diversion record. The current-status overlay records
    **no identified non-external Stage-9.5-6 implementation/evidence blocker**.

    Exact-head Stage-9 robustness run `39047079013` completed successfully.
    Stage-9.5 assurance run `39047078981` had the intended fail-closed shape:
    the assurance-contract job passed with **87 tests**; statistical oracle,
    causal properties, targeted mutations, and the semantic work-package order
    gate all passed; static discovery remained the accepted **ruff=154 /
    mypy=55** baseline; fresh-clone reconstruction remained **0 identity
    failures / 2 external-artifact blockers**; the order gate reported
    `later_packages_unlocked=false`; and Stage-9.5-7/8/9 were skipped because
    Stage-9.5-6 closure/success evidence does not yet exist.

    This continuation deliberately added no comparator, finalizer, protocol,
    gate, or scientific semantics. The only unresolved prerequisites remain
    `system_a_checkpoint_bytes_missing` and
    `stage8_large_artifact_archive_missing`. The authoritative next sequence
    remains: recover/verify the five exact original System-A checkpoints ->
    recover/verify the original Stage-8 heavy archive at 145/145 -> close
    Stage-9.5-1 -> execute the frozen historical replay handoff ->
    comparator/finalizer -> Stage-9.5-6 closure/order-gate unlock -> revalidate
    9.5-7 -> rerun/revalidate 9.5-8 -> run 9.5-9 hostile review last -> require
    zero unresolved Class-A defects -> finalize the reviewer-facing multi-chat
    assurance-diversion retrospective -> close Stage 9.5 -> only then authorize
    Stage 10.

    This entry is preserved specifically to support the final reviewer-facing
    retrospective and to show that the project stopped generating additional
    software work once the assurance architecture was complete and the true
    remaining bottleneck was external provenance recovery.

43. On 17 October 2026 this continuation resumed after the user again instructed
    the assurance work to proceed and reiterated that the complete Stage-9.5
    diversion spanning multiple chats must be documented at final closure. The
    live assurance branch had advanced externally from the previously observed
    Phase-A-era head
    `cf78ba076a12693bc1b89ac52181fc8f20091fdc` to
    `0476f3ebeaa9be0d7dba498ded58b2811564297f`, **75 commits ahead**.
    The delta was reconciled before any repository mutation.

    Reconciliation confirmed that the apparent planned Phase-B design work was
    obsolete. The repository already contains prospectively frozen deterministic
    replay comparison for Phase A, Phase B, Phase-C
    failure-lineage/correction-config preconditions, and corrected Phase-C
    seed-0 outputs; the deterministic replay-report finalizer; authoritative
    Stage-1 reconstruction evidence and closure; the frozen end-to-end
    historical replay execution handoff; the additive current-status overlay;
    and this multi-chat assurance-diversion working record. The authoritative
    current-status overlay records **no identified non-external Stage-9.5-6
    implementation/evidence blocker**.

    Exact-head Stage-9 robustness run `39047534085` completed successfully.
    Stage-9.5 assurance run `39047534073` had the expected fail-closed shape:
    the assurance-contract job passed with **87 tests**; statistical oracle,
    causal properties, targeted mutations, and the semantic work-package order
    gate all passed; static discovery remained the accepted **ruff=154 /
    mypy=55** baseline; fresh-clone reconstruction remained **0 identity
    failures / 2 external-artifact blockers**; the order gate reported
    `later_packages_unlocked=false`; and Stage-9.5-7/8/9 were skipped because
    Stage-9.5-6 closure/success evidence does not yet exist.

    No new comparator, finalizer, protocol, scientific, provenance, or gate
    semantics were introduced in this continuation. The project deliberately
    stopped software expansion at the genuine external-evidence boundary. The
    only unresolved prerequisites remain
    `system_a_checkpoint_bytes_missing` and
    `stage8_large_artifact_archive_missing`.

    The authoritative next sequence remains: recover/verify the five exact
    original System-A checkpoints -> recover/verify the original Stage-8 heavy
    archive at 145/145 -> close Stage-9.5-1 -> execute the frozen historical
    replay handoff -> run comparator/finalizer -> close Stage-9.5-6 and require
    `later_packages_unlocked=true` -> revalidate Stage-9.5-7 ->
    rerun/revalidate Stage-9.5-8 -> run Stage-9.5-9 hostile review last ->
    require zero unresolved Class-A defects -> finalize the reviewer-facing
    multi-chat assurance-diversion retrospective -> close Stage 9.5 -> only then
    authorize Stage 10.

    This entry is preserved specifically to support the user's final-closure
    requirement that the full diversion be reconstructed from committed
    repository evidence rather than transient chat memory.

44. On 17 October 2026 this continuation again resumed from the previously
    remembered Phase-A-era planning point, but the live assurance branch was
    already at `37d544b10b7aebb9bc06dccc21cdcbdb733e07cb`, **76 commits
    ahead** of `cf78ba076a12693bc1b89ac52181fc8f20091fdc`. The delta was
    reconciled before any repository mutation.

    Reconciliation showed that the intended Phase-B design tranche was obsolete.
    The live repository already contains prospectively frozen deterministic
    replay comparison for Phase A, Phase B, Phase-C failure-lineage and
    correction-config preconditions, and corrected Phase-C seed-0 outputs; the
    deterministic replay-report finalizer; authoritative Stage-1 reconstruction
    evidence and closure; the frozen end-to-end historical replay execution
    handoff; the additive current-status overlay; and this multi-chat
    assurance-diversion record. The machine-readable current-status overlay
    records **no identified non-external Stage-9.5-6 implementation/evidence
    blocker**.

    Exact-head Stage-9 robustness run `39048295074` completed successfully.
    Stage-9.5 assurance run `39048295136` had the expected fail-closed
    top-level shape: the assurance-contract job passed with **87 tests**;
    statistical oracle, causal properties, targeted mutations, and the semantic
    work-package order gate all passed; static discovery remained the accepted
    **ruff=154 / mypy=55** baseline; fresh-clone reconstruction remained
    **0 identity failures / 2 external-artifact blockers**;
    `later_packages_unlocked=false`; and Stage-9.5-7/8/9 were skipped because
    Stage-9.5-6 closure/success evidence does not yet exist.

    The post-status-overlay delta was audited and found to contain only the
    additive current-status/retrospective record; it introduced no new
    comparator, finalizer, protocol, order-gate, or scientific semantics. This
    continuation therefore deliberately made no new assurance-mechanism change.
    The only unresolved prerequisites remain
    `system_a_checkpoint_bytes_missing` and
    `stage8_large_artifact_archive_missing`.

    The authoritative next sequence remains unchanged: recover and hash-verify
    the five exact original System-A checkpoints -> recover and verify the
    original Stage-8 heavy archive at 145/145 descriptor-linked requirements ->
    close Stage-9.5-1 -> execute the frozen historical replay handoff -> run the
    deterministic comparator/finalizer -> close Stage-9.5-6 and require
    `later_packages_unlocked=true` -> revalidate 9.5-7 -> rerun/revalidate
    9.5-8 -> run 9.5-9 hostile review last -> require zero unresolved Class-A
    defects -> finalize the reviewer-facing multi-chat assurance-diversion
    retrospective -> close Stage 9.5 -> only then authorize Stage 10.

    This entry is specifically preserved to satisfy the user's requirement that
    the full two-to-three-chat assurance diversion be documented at Stage-9.5
    closure from committed repository evidence rather than reconstructed from
    transient conversation memory.

45. On 17 October 2026 this continuation resumed after the user again instructed
    the assurance work to proceed and explicitly reiterated that the entire
    Stage-9.5 assurance diversion spanning multiple chats must be documented at
    final closure. The live assurance branch had advanced externally from the
    previously remembered Phase-A-era head
    `cf78ba076a12693bc1b89ac52181fc8f20091fdc` to
    `3e33373353731962fd80d97e7e4939c5f29c8de6`, **77 commits ahead**.
    The delta was reconciled before any repository mutation.

    Reconciliation confirmed that the planned Phase-B design work was obsolete.
    The live repository already contains prospectively frozen deterministic
    replay comparison for Phase A, Phase B, Phase-C failure-lineage and
    correction-config preconditions, and corrected Phase-C seed-0 outputs; the
    deterministic replay-report finalizer; authoritative Stage-1 reconstruction
    evidence and closure; the frozen end-to-end historical replay execution
    handoff; the additive current-status overlay; and this multi-chat
    assurance-diversion working record. The machine-readable current-status
    overlay records **no identified non-external Stage-9.5-6
    implementation/evidence blocker**.

    Exact-head Stage-9 robustness run `39049302746` completed successfully.
    Stage-9.5 assurance run `39049302755` had the intended fail-closed shape:
    the assurance-contract job passed with **87 tests**; statistical oracle,
    causal properties, targeted mutations, and the semantic work-package order
    gate passed; static discovery remained the accepted **ruff=154 / mypy=55**
    baseline; fresh-clone reconstruction remained **0 identity failures / 2
    external-artifact blockers**; the order gate reported
    `later_packages_unlocked=false`; and Stage-9.5-7/8/9 were skipped because
    Stage-9.5-6 closure/success evidence does not yet exist.

    No new comparator, finalizer, protocol, scientific, provenance, or
    order-gate semantics were introduced in this continuation. The project
    deliberately stopped software expansion at the genuine external-evidence
    boundary. The only unresolved prerequisites remain
    `system_a_checkpoint_bytes_missing` and
    `stage8_large_artifact_archive_missing`.

    The authoritative next sequence remains: recover and hash-verify the five
    exact original System-A checkpoints -> recover and verify the original
    Stage-8 heavy archive at 145/145 descriptor-linked requirements -> close
    Stage-9.5-1 -> execute the frozen historical replay handoff -> run the
    deterministic comparator/finalizer -> close Stage-9.5-6 and require
    `later_packages_unlocked=true` -> revalidate Stage-9.5-7 ->
    rerun/revalidate Stage-9.5-8 -> run Stage-9.5-9 hostile review last ->
    require zero unresolved Class-A defects -> finalize the reviewer-facing
    multi-chat assurance-diversion retrospective -> close Stage 9.5 -> only
    then authorize Stage 10.

    This entry is preserved specifically to satisfy the user's requirement that
    the full multi-chat assurance diversion be documented at Stage-9.5 closure
    from committed repository evidence rather than reconstructed from transient
    conversation memory.

46. On 17 October 2026 this continuation resumed after the user again instructed
    the assurance work to proceed and explicitly reiterated that the complete
    Stage-9.5 diversion spanning two to three chats must be documented at final
    closure. The live assurance branch had advanced externally from the
    previously remembered Phase-A-era head
    `cf78ba076a12693bc1b89ac52181fc8f20091fdc` to
    `df4f94a4b05619936bee29785098cd9a8efc4645`, **78 commits
    ahead**. The delta was reconciled before any repository mutation.

    Reconciliation confirmed that the apparent planned Phase-B design work was
    obsolete. The live repository already contains prospectively frozen
    deterministic replay comparison for Phase A, Phase B, Phase-C
    failure-lineage/correction-config preconditions, and corrected Phase-C
    seed-0 outputs; the deterministic replay-report finalizer; authoritative
    Stage-1 reconstruction evidence and closure; the frozen end-to-end
    historical replay execution handoff; the additive current-status overlay;
    and this multi-chat assurance-diversion working record. The machine-readable
    current-status overlay records **no identified non-external Stage-9.5-6
    implementation/evidence blocker**.

    The 19 commits after the current-status observation head
    `ddcc8c21dff5c30d01c2a5935ae609406b804e8f` were audited and found
    to change only the additive current-status/retrospective record; they
    introduced no new comparator, finalizer, replay protocol, order-gate, or
    scientific semantics.

    Exact-head Stage-9 robustness run `39049858993` completed successfully.
    Stage-9.5 assurance run `39049858987` had the intended fail-closed shape:
    the assurance-contract job passed with **87 tests**; statistical oracle,
    causal properties, targeted mutations, and the semantic work-package order
    gate passed; static discovery remained the accepted **ruff=154 / mypy=55**
    baseline; fresh-clone reconstruction remained **0 identity failures / 2
    external-artifact blockers**; `later_packages_unlocked=false`; and
    Stage-9.5-7/8/9 were skipped because the Stage-9.5-6 closure/success records
    do not yet exist.

    No new assurance mechanism was added. The project again stopped software
    expansion at the genuine external-evidence boundary. The only unresolved
    prerequisites remain `system_a_checkpoint_bytes_missing` and
    `stage8_large_artifact_archive_missing`.

    The authoritative next sequence remains: recover and hash-verify the five
    exact original System-A checkpoints -> recover and verify the original
    Stage-8 heavy archive at 145/145 descriptor-linked requirements -> close
    Stage-9.5-1 from verifier-produced recovery evidence -> execute the frozen
    historical replay handoff -> run the frozen comparator/finalizer -> close
    Stage-9.5-6 and require `later_packages_unlocked=true` -> revalidate
    Stage-9.5-7 -> rerun/revalidate Stage-9.5-8 -> run Stage-9.5-9 hostile
    review last -> require zero unresolved Class-A defects -> finalize the
    reviewer-facing multi-chat assurance-diversion retrospective -> close
    Stage 9.5 -> only then authorize Stage 10.

    This entry is preserved specifically to satisfy the user's closure
    requirement that the full assurance diversion be reconstructed from
    committed repository evidence rather than transient conversation memory.

47. On 17 October 2026 this continuation resumed after the user again instructed
    the assurance work to proceed and explicitly reiterated that the complete
    Stage-9.5 assurance diversion spanning multiple chats must be documented at
    final closure. The live assurance branch had advanced externally from the
    previously remembered Phase-A-era head
    `cf78ba076a12693bc1b89ac52181fc8f20091fdc` to
    `8f69a57e25fecc11996535eb444f2d28d3b2c8bc`, **79 commits ahead**.
    The delta was reconciled before any repository mutation.

    Reconciliation showed that the previously planned Phase-B comparator design
    work was obsolete. The live repository already contains prospectively
    frozen deterministic replay comparison for Phase A, Phase B, Phase-C
    failure-lineage/correction-config preconditions, and corrected Phase-C
    seed-0 output comparison; the deterministic replay-report finalizer;
    authoritative Stage-1 reconstruction evidence and closure; the frozen
    historical replay execution handoff; the additive machine-readable
    current-status overlay; and this multi-chat assurance-diversion working
    record.

    The current-status overlay
    `data/manifests/stage9_5_6_current_status_v1.json` was re-audited against
    the live branch. From its scientific/assurance observation point
    `ddcc8c21dff5c30d01c2a5935ae609406b804e8f` to the live head, repository
    changes were confined to the additive current-status overlay and further
    retrospective entries; no comparator, finalizer, verifier, order-gate,
    accepted Stage-8/9 evidence, claim boundary, or Stage-10 gate changed.
    Therefore its statement remains authoritative: **no identified
    non-external Stage-9.5-6 implementation/evidence blocker remains**.

    Exact-head Stage-9 robustness run `39050370370` completed successfully.
    Stage-9.5 assurance run `39050370349` was still completing when this entry
    was written, so no unsettled job was represented as closed. Already-settled
    results had the expected fail-closed shape: the semantic work-package order
    gate passed and reported `later_packages_unlocked=false` because the
    Stage-9.5-6 closure/success records do not yet exist; statistical oracle and
    causal properties passed; fresh-clone reconstruction reported **0 identity
    failures / 2 external-artifact blockers**; static discovery remained the
    already accepted **ruff=154 / mypy=55** baseline; and Stage-9.5-7/8/9 were
    skipped. Assurance-contract and targeted-mutations were still in progress
    at the time of this factual snapshot and are intentionally not claimed here
    as settled.

    No new comparator, finalizer, protocol, scientific, provenance, or gate
    semantics were added. This continuation deliberately stopped software
    expansion at the genuine external-evidence boundary. The only unresolved
    prerequisites remain `system_a_checkpoint_bytes_missing` and
    `stage8_large_artifact_archive_missing`.

    The authoritative next sequence remains: recover and hash-verify the five
    exact original System-A checkpoints -> recover and verify the original
    Stage-8 heavy archive at 145/145 descriptor-linked requirements -> close
    Stage-9.5-1 from verifier-produced recovery evidence -> execute the frozen
    historical replay handoff -> run the frozen comparator/finalizer -> close
    Stage-9.5-6 and require `later_packages_unlocked=true` -> revalidate
    Stage-9.5-7 -> rerun/revalidate Stage-9.5-8 -> run Stage-9.5-9 hostile
    review last -> require zero unresolved Class-A defects -> finalize the
    reviewer-facing multi-chat assurance-diversion retrospective -> close
    Stage 9.5 -> only then authorize Stage 10.

    This entry is preserved specifically to satisfy the user's closure
    requirement that the entire multi-chat assurance diversion be reconstructed
    from committed repository evidence rather than transient conversation
    memory.

48. On 17 October 2026 the user explicitly instructed the project to **close
    Stage 9.5-1 in the next response**, while also requiring that academic and
    scientific rigor be preserved. The live assurance head was first reconciled
    at `260351e3cd77c5e5ddff6b40b810d9e75c1fe5f4`; this head already
    contained the fully implemented replay comparator/finalizer stack,
    authoritative Stage-1 reconstruction closure, the frozen historical replay
    handoff, and no identified non-external Stage-9.5-6 blocker.

    Exact-head evidence at that observation point was:
    Stage-9 robustness run `39050628185` **success**; Stage-9.5 assurance
    run `39050628180`; assurance-contract **87 tests passed**; fresh-clone
    job `117448298396` **13 tests passed** and reported **0 identity
    failures / 2 external-artifact blockers**; order-gate job
    `117448298419` passed with `later_packages_unlocked=false`;
    Stage-9.5-7/8/9 were skipped; and the accepted Stage-9.5-5 discovery
    baseline remained `ruff=154 / mypy=55`.

    A final recovery sweep was performed before deciding closure. It checked
    Project/conversation files, local mounted/container paths, repository and
    previously audited history surfaces, GitHub Releases, the System-A manifest
    freeze run `37531241834`, all four Actions runs attached to accepted
    Stage-8 evidence commit
    `c2ded83b8195b9321e715626c1f305f9627936e8`, exact public-web searches
    for all five checkpoint SHA-256 identities and Stage-8 archive identifiers,
    and the later Stage-1 transport/mirror surface. No authoritative
    System-A checkpoint bytes or original Stage-8 heavy archive were found.
    Google Drive, Dropbox, Box, and SharePoint plugins were discoverable but not
    installed/connected, so the search did not claim global physical
    irrecoverability of every user-held copy.

    Because successful closure remained impossible without weakening the frozen
    evidence criterion, the project did **not** fabricate a pass, regenerate
    checkpoints, rebuild the heavy archive and call it original, reclassify the
    Class-A defect, or relax the 145-file requirement. Instead Stage 9.5-1 was
    closed explicitly as a **negative assurance closure**:
    `STAGE9_5_1_FRESH_CLONE_RECONSTRUCTION_NEGATIVE_CLOSURE.md` plus
    `data/manifests/stage9_5_1_negative_closure_v1.json`.

    The negative closure records `pass=false`, zero identity mismatches, both
    unresolved external blockers, the exact five checkpoint hashes, the
    145-file Stage-8 requirement, the exact-head CI evidence, prohibited
    substitute resolutions, and a strict reopening predicate. It does not
    declare the accepted Stage-8/9 numerical results false. It declares that
    publication-grade independent reconstruction of the full original
    checkpoint/heavy-artifact chain was not demonstrated.

    The downstream status was changed only in additive current-status overlays:
    Stage 9.5-1 is **CLOSED — FAILED / EXTERNAL PROVENANCE UNRESOLVED**;
    Stage 9.5-6 is blocked by that closed-failed predecessor; Stage 9.5-7/8/9
    remain locked as authoritative closure packages; Stage 9.5 cannot obtain
    zero-unresolved-Class-A closure under the current evidence package; and
    Stage 10 remains **PROHIBITED**.

    Reopening is permitted only if the exact original checkpoint and archive
    bytes are later supplied and the unchanged v1.2 verifier passes five seeds,
    **145/145** archive files, zero failures, and zero blockers. Otherwise any
    future continuation must be a separately governed restart/new evidence-
    generation campaign rather than silent substitution into the accepted
    Stage-8/9 evidence chain.

    This entry is a required part of the final reviewer-facing Stage-9.5
    retrospective because it records the point at which the assurance diversion
    terminated not in a successful reconstruction, but in a deliberate,
    scientifically honest negative closure rather than indefinite or fabricated
    gate satisfaction.

## Dropbox recovery surface discovered after negative closure — 17 October 2026

A materially new authoritative surface became available after the Stage-9.5-1 negative closure: the user's Dropbox connector was connected.

This event must remain explicit in the final retrospective because it changes the external-provenance search history without invalidating the historical negative closure. The negative closure itself already stated that connected personal-cloud storage had not been available and allowed reopening if exact originals were later recovered.

### Checkpoint discovery

Dropbox root contained `seed_0.pt` through `seed_4.pt`, each 76,105 bytes.

The Dropbox API returned content hashes:

- seed 0 — `ddc75eaaae68cf1e6ee34a5a68c264f922d64543ca883cd03234763a182a1719`
- seed 1 — `b6288356dd06f134aa18ea886c5ec17e695488f57074a455115f0cd17fef4feb`
- seed 2 — `f9ad4465f34aa3e525722a989bcf7b3588a1e57973cdbe2e1fe5e30a00378b05`
- seed 3 — `0f6d6b65cdadc92f7aaf3e345845bdb6c9014f7512f8fff7a7026a8e3c0fd716`
- seed 4 — `2cbb2afd97b9be46964901e8a66413a09b5cbbb9e041dd8530fc5834ab7e722e`

Dropbox's documented content-hash algorithm uses 4 MiB blocks, SHA-256 per block, concatenation of binary block digests, then a final SHA-256. Because every checkpoint is smaller than one block, each observed Dropbox content hash equals
`SHA256(binary(frozen_checkpoint_SHA256))`.

All five observed values matched that transform of the five already-frozen checkpoint SHA-256 identities exactly. This established that the Dropbox checkpoint candidates correspond to the exact required byte streams under Dropbox's documented content-hash construction. The frozen Stage-9.5-1 verifier has not yet been rerun with those files materialized on a verifier-capable filesystem, so this discovery does not itself create a successful closure report.

### Stage-8 archive discovery

Dropbox also contained `/cd_primary_v1` with:

- 253 entries;
- 203 files;
- 50 folders;
- 1,863,975,043 total file bytes.

The tree contained the expected major Phase-A/B/C families, including all five Phase-A run manifests/prediction files, all five Phase-B seed manifests, all ten D-arm maintenance logs, all five corrected Phase-C seed manifests, all fifteen corrected arm evaluations/prediction traces, and the original Phase-C seed-0 attempt/failure pair.

The accepted Stage-8 compact evidence was used to reconstruct the unchanged v1.2 descriptor-linked archive inventory. Per-seed results were:

- seed 0: 30/31 paths present;
- seed 1: 27/28;
- seed 2: 28/29;
- seed 3: 27/28;
- seed 4: 28/29.

Total: **140/145** required paths present.

The only five missing paths were the C-arm `maintenance.jsonl` files for seeds 0–4. Each accepted arm manifest binds that path to SHA-256
`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`,
the zero-byte file hash, and each accepted C-arm maintenance summary records zero opportunities/publications/compute.

A Dropbox-wide title search found only the ten D-arm maintenance files. Revision lookup for the exact missing seed-0 path returned `FILE_NOT_FOUND`. No compressed `cd_primary_v1` or Stage-8 backup was found.

### Governance decision

The five missing files were **not** silently recreated even though their exact byte content is cryptographically specified as empty. Doing so without authoritative provenance would weaken the already-frozen recovery rule after observing a recovery gap.

Therefore:

- the historical negative closure remains preserved;
- the new surface materially narrows the external-provenance defect;
- checkpoint originals are located with exact identity evidence;
- the Stage-8 archive remains incomplete at 140/145;
- Stage-9.5-1 is not yet reopened to successful closure;
- Stage-9.5-6 remains blocked until the unchanged v1.2 verifier succeeds;
- Stage-9.5-7/8/9 remain locked;
- Stage 10 remains prohibited.

The authoritative records for this event are:

- `STAGE9_5_1_DROPBOX_RECOVERY_DISCOVERY.md`;
- `data/manifests/stage9_5_1_dropbox_recovery_discovery_v1.json`;
- the additive current-status update in `data/manifests/stage9_5_6_current_status_v1.json`.

This episode is part of the final multi-chat assurance-diversion retrospective and must not be omitted or collapsed into a claim that the negative closure was simply "wrong"; it was correct for the surfaces available at that time.

## Dropbox revision-history exhaustion follow-up — 17 October 2026

After the Dropbox recovery surface had narrowed the accepted Stage-8 archive to
140/145 required paths, one final read-only recovery check was performed before
treating that source as exhausted.

An advanced Dropbox-wide title search for `maintenance.jsonl` returned exactly
the ten active D-arm maintenance logs and no C-frozen maintenance file. Search
for `cd_primary_v1` returned only the already-audited archive tree. Dropbox
revision history was then queried separately for each of the five exact missing
paths:

- seed 0 C-frozen `maintenance.jsonl`;
- seed 1 C-frozen `maintenance.jsonl`;
- seed 2 C-frozen `maintenance.jsonl`;
- seed 3 C-frozen `maintenance.jsonl`;
- seed 4 C-frozen `maintenance.jsonl`.

All five revision-history calls returned `FILE_NOT_FOUND`. No recoverable
historical revision was exposed for any missing path.

The scientific/governance decision did not change: the known SHA-256 of the
empty file does not authorize creating substitute files and relabeling them as
recovered originals. Dropbox is therefore exhausted for this narrow recovery
question, the authoritative archive state remains 140/145, and any further
successful recovery must come from a genuinely new authoritative source or
original archive representation.

This follow-up is retained so the final reviewer-facing Stage-9.5 retrospective
can distinguish (a) discovery of a materially useful personal-cloud surface,
(b) partial recovery on that surface, and (c) explicit exhaustion of that
surface without relaxing the frozen success criterion.

## Zero-byte transport-omission forensics and reconstructible-route correction — 17 October 2026

After the Dropbox recovery discovery had narrowed Stage-9.5-1 to five missing
C-frozen `maintenance.jsonl` objects, the user instructed the project to
complete the next step that materially moved Stage 9.5 toward closure rather
than continuing abstract hardening.

The live assurance head was first reconciled at
`bae55fd79302bf564e409d11874f06a430d62510`. That head already contained
substantial work completed across the assurance diversion: Phase-A/B/C replay
comparison, the deterministic finalizer, authoritative Stage-1 reconstruction,
the historical replay handoff, the Stage-9.5-1 negative closure, Dropbox
recovery discovery, and this running multi-chat retrospective. The current
status at that head reported no identified non-external Stage-9.5-6 blocker.
The remaining recovery state was five exact checkpoints located in Dropbox and
a Stage-8 archive physically present at **140/145** descriptor-linked paths.

### Connector-to-verifier transport attempt

A direct attempt was made to materialize the five Dropbox checkpoint byte
streams into the verifier container.

Dropbox successfully issued temporary raw-byte download links for all five
checkpoint files. The ordinary verifier container could not consume those links
because its direct network path has no external DNS access. The platform's
sanctioned container downloader in turn requires a prior web-view authorization,
while Dropbox temporary download links are single-use and the web fetch layer
does not support those private binary URLs. The Dropbox connector exposes
metadata, text extraction, previews, and temporary links, but not a raw-byte
file object that the Project/conversation `files.materialize` layer can place
directly into the verifier container.

No scientific or provenance rule was changed to work around that product
boundary. The raw bytes therefore remain to be materialized on a
verifier-capable filesystem outside this connector-to-container bridge.

### Exhaustive Dropbox restore-event audit

A new read-only Dropbox surface was then audited:
`list_restore_events` for the live `/cd_primary_v1` folder.

The full history was paginated to exhaustion:

- **26 pages**;
- **253 total events**;
- current Dropbox tree: **253 entries**;
- operation types observed: **ADD only**;
- non-ADD events: **0**;
- DELETE/MOVE/RENAME/RESTORE/ROLLBACK events: **0**.

This provided a stronger provenance fact than the earlier title/revision
searches.

For every seed 0-4, the history contains ADD events for the
`c_frozen_symbolic` folder and its `arm_manifest.json`,
`initial_state.json`, and `final_state.json`. It also contains the D-drift
and D-periodic `maintenance.jsonl` ADD events. It contains **no ADD event** for
any of the five C-frozen `maintenance.jsonl` paths.

Combined with the earlier exact-path revision checks returning
`FILE_NOT_FOUND`, this establishes that the five empty C-arm maintenance
objects were omitted during the Dropbox archive ingestion itself; they were not
objects that Dropbox later deleted, moved, renamed, restored, or rolled back.

The machine record is:

`data/manifests/stage9_5_1_dropbox_restore_event_forensics_v1.json`.

### Governing-plan reinterpretation after new transport evidence

The earlier no-synthesis decision was deliberately conservative and remains part
of the historical record. At that point, the project knew only that the five
files were absent and cryptographically expected to be empty. That alone was
not accepted as authority to recreate them.

The exhaustive transport history added a materially different fact: the
connected archive representation demonstrably omitted those zero-byte objects
at ingestion while preserving their sibling objects.

The reconciled governing plan requires the project to **archive or provide a
reconstructible route** to every non-Git heavy artifact needed for independent
Stage-8/9 verification. The five missing byte streams are uniquely determined:
each accepted C-arm manifest binds `maintenance.jsonl` to SHA-256

`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`

and records zero maintenance opportunities, zero publications, zero candidates,
and zero maintenance compute/timing.

On that basis, the project froze a versioned **transport reconstruction
correction** rather than silently relabeling newly created files as recovered
Dropbox originals.

The frozen contract is:

`data/manifests/stage9_5_1_zero_byte_transport_reconstruction_v1.json`.

The implementation is:

`tools/stage9_5/zero_byte_transport_reconstruction.py`.

Dedicated tests are:

`tests/stage9_5/test_zero_byte_transport_reconstruction.py`.

The human correction note is:

`STAGE9_5_1_ZERO_BYTE_TRANSPORT_RECONSTRUCTION_CORRECTION.md`.

### Fail-closed reconstruction mechanics

The correction does not weaken or modify the Stage-9.5-1 v1.2 verifier.

Before creating any file, the reconstruction utility validates **all five**
entries. It verifies:

- pinned Git-blob identities for the earlier Dropbox discovery records and the
  new restore-event forensic record;
- committed accepted C-arm manifest payload/manifest self-hashes;
- byte identity between the materialized archive's C-arm manifest and the
  committed accepted compact-evidence manifest;
- the exact maintenance descriptor path and frozen empty-file SHA-256;
- zero maintenance opportunities/publications/candidates/compute/SHAP/
  surrogate/lifecycle;
- an empty publications list;
- path containment inside the supplied archive root;
- no overwrite of any existing file.

Only if every precondition passes may any write occur. Missing files are created
with exclusive-create semantics and exactly zero bytes. Preexisting correct
zero-byte files are preserved and reported separately rather than relabeled as
reconstructed.

The machine report explicitly states:

- `original_dropbox_objects_recovered = false`;
- `transport_reconstruction_explicit = true`;
- `governing_verifier_unchanged = true`.

The reconstruction report is not Stage-9.5-1 success authority.

### Unchanged closure authority

After the checkpoint family and 140 present archive files are materialized on a
verifier-capable filesystem, the frozen transport correction can complete the
five manifest-bound empty byte streams. The unchanged Stage-9.5-1 v1.2 verifier
must then independently produce:

- `pass=true`;
- checkpoint seeds `[0,1,2,3,4]`;
- archive requirement count **145**;
- archive verified count **145**;
- zero failures;
- zero blockers.

Only such verifier-produced success may reopen/supersede the historical
negative closure and permit the frozen Stage-9.5-6 historical replay handoff.

The current-status overlay was updated additively to reflect this state. The
physical Dropbox tree remains 140/145, but a frozen reconstructible route now
exists for the five uniquely defined transport omissions. The remaining
execution barriers are raw-byte materialization to a verifier-capable
filesystem and the unchanged v1.2 verifier rerun.

This entire episode must remain visible in the final reviewer-facing
retrospective: historical negative closure -> partial Dropbox recovery ->
conservative no-synthesis decision -> exhaustive restore-event forensics ->
versioned transport-reconstruction correction. None of those states should be
collapsed or rewritten after the fact.

## Current-chat reconciliation and Dropbox materialization preflight — 17 October 2026

A later chat resumed after the assurance branch had advanced externally by
**107 commits** from the previously observed Phase-A comparator head
`cf78ba076a12693bc1b89ac52181fc8f20091fdc` to
`8947848e337074096689de7d62b0c46850182b9a`. The delta was reconciled before
any mutation.

The reconciled head showed that several tasks which had still been pending in
the earlier chat were already complete prospectively:

- Phase-A, Phase-B, and corrected Phase-C replay comparison are implemented and
  frozen;
- the deterministic replay-report finalizer is implemented and frozen;
- authoritative Stage-1 reconstruction evidence is closed;
- the historical replay execution handoff is frozen;
- the multi-chat assurance-diversion retrospective is already maintained in
  this file;
- no identified non-external Stage-9.5-6 implementation blocker remains.

The current-status overlay instead places the live bottleneck at Stage-9.5-1:
the Dropbox recovery bytes must be materialized on a verifier-capable
filesystem, the frozen zero-byte transport correction must complete the five
manifest-bound omissions, and the unchanged v1.2 verifier must then produce a
successful 145/145 report before Stage-9.5-6 may execute.

### Read-only Dropbox revalidation

The connected Dropbox surface was rechecked without mutation. All five
checkpoint objects remain present at `/seed_0.pt` through `/seed_4.pt`;
each reports the expected size of **76,105 bytes**. The
`/cd_primary_v1` folder remains present and reports the same aggregate size
recorded by the frozen discovery evidence: **1,863,975,043 bytes**.

The Dropbox connector also successfully issued direct temporary download links,
confirming that the source files are downloadable from the connected cloud
surface.

### One-file materialization preflight

A deliberately conservative materialization test was attempted on
`seed_0.pt` only. No archive transfer was attempted.

The verifier container tried to consume the connector-issued temporary URL
directly with a single HTTP GET. The request failed at DNS resolution before
any file bytes were written:

`Could not resolve host: ...dl.dropboxusercontent.com`.

No partial checkpoint file was accepted, no hash claim was made, and no
Dropbox object was mutated.

A public-web workaround was deliberately not used: the temporary URL is private
and single-use, and routing it through an unrelated public web-fetch surface
would weaken the intended connector-to-verifier provenance boundary merely to
work around this container's network restriction.

Therefore the authoritative conclusion remains unchanged: the Dropbox recovery
surface is present, but this specific container is not the verifier-capable
filesystem on which the recovered byte streams can presently be materialized.

### Exact-head assurance state during this preflight

At head `8947848e337074096689de7d62b0c46850182b9a`:

- the work-package order gate completed successfully and emitted
  `later_packages_unlocked=false`;
- Stage-9.5-7/8/9 remained skipped/locked;
- fresh-clone reconstruction tests reported **13 passed**;
- the unchanged v1.2 reconstruction result remained
  **0 identity failures / 2 external-artifact blockers**.

This chat therefore made no scientific, comparator, verifier, or closure-rule
change. Its contribution was reconciliation of the externally advanced branch,
read-only revalidation of the connected Dropbox recovery surface, and explicit
preservation of the remaining connector-to-verifier materialization boundary
for the final reviewer-facing Stage-9.5 retrospective.

## Integrated Stage-9.5-6 comparison-evidence producer tranche — 18 October 2026

This chat resumed with an explicit instruction to keep the tranche small,
re-read PR #21 before mutation, integrate the already-frozen Phase-A/Phase-B/
Phase-C/failure-lineage/correction-config checks into the deterministic
comparison-evidence producer, bind that output to the frozen replay-report
finalizer, add synthetic-only integration tests, and **not execute the real
historical replay**.

The live PR head had advanced from the previously observed
`cf78ba076a12693bc1b89ac52181fc8f20091fdc` to
`2e67f176cf9ec4e9cf8499d1d489c29f0fe47b38`, a 154-commit descendant. That
delta was reconciled before mutation. It showed that Phase-A, Phase-B,
Phase-C preconditions, exact failed-v1 lineage, corrected Phase-C seed-0 output,
Stage-1 reconstruction evidence, correction-config comparison, and the
replay-report finalizer were already implemented with extensive synthetic
tests. The tranche therefore did **not** reimplement those components.

The integration gap was narrower:

- the deterministic producer did not yet require the frozen Stage-9.5-1 v1.2
  recovery report as an explicit upstream proof that both external artifact
  families were verified;
- the comparator and replay-report finalizer remained two operator steps rather
  than one bound producer-to-finalizer path.

The producer was therefore extended prospectively, before any historical replay
outcome access, to verify a canonical Stage-9.5-1 v1.2 recovery report. It
requires:

- `audit_id = stage9.5-1-fresh-clone-reconstruction-v1_2`;
- `status = pass` and `pass = true`;
- zero report failures and blockers;
- canonical report SHA-256 integrity;
- a repository head in the current assurance ancestry;
- System-A verified seeds exactly `[0,1,2,3,4]`, with no missing or
  mismatched checkpoint bytes;
- Stage-8 large-archive `requirement_count = 145` and
  `verified_count = 145`, with no missing or mismatched descriptor-linked
  files.

A missing or incomplete checkpoint family produces the explicit
`system_a_checkpoint_family_not_verified` blocker. A missing or incomplete
Stage-8 heavy archive produces
`stage8_large_artifact_archive_not_verified`. Either condition also produces
the Class-A closure blocker `stage9_5_1_recovery_not_verified`.

The integrated producer now also emits explicit blockers for failed Phase-A,
failed Phase-B, unverified accepted Phase-B maintenance records, failed
Phase-C preconditions, failed corrected Phase-C output, and unverified Stage-1
reconstruction evidence. Any such state keeps
`comparison_complete = false`, `source_evidence_complete = false`, and
`unresolved_class_a` non-empty.

The exact comparison-evidence file written by the producer is now passed
directly to the already-frozen replay-report finalizer. The finalizer additionally
requires and preserves the canonical SHA-256 of the successful Stage-9.5-1
recovery report. This removes a manual handoff point between comparator output
and replay-report construction.

Synthetic integration tests were added for:

- complete recovery + Phase-A/B/C + finalizer success;
- each external artifact family missing independently;
- incomplete Phase-B / unavailable accepted maintenance evidence;
- failed exact failure-lineage or correction-config scientific-block equality;
- direct Stage-9.5-1 recovery-report verification;
- finalizer rejection when the recovery-report canonical SHA is absent.

No recovered checkpoint bytes, Stage-8 heavy archive bytes, fresh replay
artifacts, or historical Phase-A/B/C execution were accessed or produced in
this tranche. The real historical replay remained unexecuted. No accepted
Stage-8/9 scientific result, treatment, estimand, metric, or claim boundary was
changed.

This integration tranche must remain visible in the final reviewer-facing
retrospective as the point where the previously separate frozen assurance
components were joined into a single fail-closed producer/finalizer pipeline
without outcome access.

