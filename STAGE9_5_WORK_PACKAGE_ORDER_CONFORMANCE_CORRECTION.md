# Stage 9.5 Work-Package Order Conformance Correction

**Status:** ACTIVE CORRECTION — supersedes premature package-closure labels for Stage 9.5-7/8/9  
**Correction applies from assurance head:** `0f646b2d4e9e6bc17ecbc9229c2ab44fda945e2a`  
**Scientific evidence changed:** no  
**Historical runtime lock changed:** no  
**Stage-10 outcomes accessed:** no

## Defect

The frozen `STAGE9_5_Q1_INDEPENDENT_ASSURANCE_PROTOCOL.md` states that the Stage-9.5 work-package order is binding.

The protocol places:

1. Stage 9.5-6 clean deterministic historical rerun;
2. Stage 9.5-7 claim-to-evidence traceability;
3. Stage 9.5-8 independent table/figure regeneration;
4. Stage 9.5-9 hostile-review closure audit.

It also requires Stage 9.5-9 to run after Stage 9.5-0 through Stage 9.5-8, and states that closure requires zero unresolved Class-A defects.

The repository subsequently executed and labeled Stage 9.5-7, Stage 9.5-8, and Stage 9.5-9 as closed while Stage 9.5-6 remained blocked by the unrecovered exact System-A checkpoint bytes. That sequencing is not conformant with the still-frozen protocol.

## Classification

**Class A — assurance-gate/protocol-conformance defect.**

This classification applies to the validity of the Stage-9.5 closure state and package-order claim. It does **not** establish that the accepted Stage-8 or Stage-9 numerical results are wrong, and it does not alter any accepted scientific estimand, treatment, comparator, metric, or result artifact.

The pre-existing Class-A provenance blocker remains independently open:

`system_a_checkpoint_bytes_missing`.

## Preservation rule

No existing Stage 9.5-7/8/9 artifact, closure document, workflow run, failed run, or evidence hash is deleted, rewritten, or replaced.

The already executed 9.5-7/8/9 artifacts remain useful assurance evidence, but their current **closure labels are not protocol-valid** while 9.5-6 is incomplete.

For gate accounting, reclassify them prospectively as:

- 9.5-7: **EXECUTED / PROVISIONAL — closure held open by unmet 9.5-6 predecessor**;
- 9.5-8: **EXECUTED / PROVISIONAL — closure held open by unmet 9.5-6 predecessor**;
- 9.5-9: **EXECUTED / PROVISIONAL — closure invalid as final hostile-review closure until the binding sequence is satisfied and zero unresolved Class-A defects remain**.

Stage 9.5-5 remains closed. Its accepted v1.4 baseline and later supplemental static evidence are not reopened by this correction.

## Required resolution path

Do not regenerate or substitute System-A checkpoints.

Only after the exact accepted checkpoint byte files are recovered from an authoritative archive and hash-verified may Stage 9.5-1 close and Stage 9.5-6 proceed.

After a valid Stage 9.5-6 exact historical rerun:

1. rerun/revalidate Stage 9.5-7 on the then-current exact assurance head;
2. rerun/revalidate Stage 9.5-8 after 9.5-7;
3. rerun Stage 9.5-9 last, after 9.5-0 through 9.5-8 are all validly closed;
4. require zero unresolved Class-A defects for final Stage-9.5 closure;
5. preserve the earlier out-of-order 7/8/9 executions as historical assurance evidence rather than replacing them.

If the exact checkpoint bytes remain unavailable, 9.5-6 and therefore protocol-valid 9.5-7/8/9 closure remain blocked.

## Current gate state after correction

- 9.5-0: closed;
- 9.5-1: **open / Class-A blocked**;
- 9.5-2: closed;
- 9.5-3: closed;
- 9.5-4: closed;
- 9.5-5: closed;
- 9.5-6: **blocked by 9.5-1 checkpoint-byte provenance defect**;
- 9.5-7: **executed / provisional; not protocol-closed**;
- 9.5-8: **executed / provisional; not protocol-closed**;
- 9.5-9: **executed / provisional; not protocol-closed**;
- Stage 9.5 overall: **OPEN / BLOCKED**;
- Stage 10: **PROHIBITED**.

This correction narrows assurance-status claims only. It does not modify accepted Stage-8/9 evidence or authorize any Stage-10 outcome access.

## Prospective CI order enforcement

The assurance workflow must not continue generating Stage 9.5-7/8/9 executions while the binding Stage 9.5-6 predecessor is blocked.

Prospectively, the workflow order gate requires both of the following before Stage 9.5-7 may execute:

- `STAGE9_5_6_CLEAN_DETERMINISTIC_FULL_SEED_RERUN_CLOSURE.md`;
- `results/audits/stage9_5_full_seed_rerun_v1/success.json`.

If either is absent, the order-gate job records the later packages as locked and Stage 9.5-7/8/9 are skipped. After a valid 9.5-6 closure, Stage 9.5-7 runs first; Stage 9.5-8 depends on successful 9.5-7 completion; Stage 9.5-9 depends on successful 9.5-8 completion.

This is prospective workflow enforcement only. It does not delete, rewrite, or retroactively relabel the preserved out-of-order historical artifacts beyond the provisional status already recorded above. It does not modify scientific source, accepted Stage-8/9 evidence, or the historical runtime lock.

## Prospective unlock-predicate hardening — 16 October 2026

A further fail-open risk was identified before any valid Stage 9.5-6 closure existed: the initial CI order gate treated the mere presence of the closure Markdown file and `success.json` as sufficient to unlock Stage 9.5-7. A placeholder, malformed, or semantically incomplete pair could therefore have satisfied the filename predicate without proving a valid 9.5-6 closure.

The prospective contract `data/manifests/stage9_5_6_closure_order_gate_v1.json` now freezes the machine-readable unlock predicate before Stage 9.5-6 execution. The validator `tools/stage9_5/work_package_order_gate.py` requires, at minimum:

- the exact Stage 9.5-6 audit/status identity;
- Stage 9.5-1 closed with zero identity failures and zero external-artifact blockers;
- same-head Stage-9 contract success;
- replay-equivalence protocol v1.1 identity and pass status;
- complete Phase-A seeds 0–4 and Phase-B seeds 0–4;
- preservation of the original Phase-C v1 seed-0 failure lineage;
- completed corrected Phase-C seed-0 rerun;
- verification of the accepted maintenance archive needed for record-level replay equivalence;
- zero unresolved Class-A defects;
- no scientific-object replacement and no Stage-10 outcome access;
- a preserved `results/audits/stage9_5_full_seed_rerun_v1/replay_equivalence_report.json` whose embedded canonical SHA-256 recomputes exactly, equals the Stage-9.5-6 report hash in `success.json`, carries the same `audited_head` as the closure success record, explicitly contains zero failures and zero blockers, and whose frozen replay-equivalence fields pass direct validation; that hash and report path must be linked from the closure document;
- a successful Stage-9.5-1 recovery record bound to `stage9.5-1-fresh-clone-reconstruction-v1_2`, with checkpoint seeds 0–4 verified, the Stage-8 heavy archive at **145 required / 145 verified**, and its own canonical report SHA-256 linked from the same closure document.

Missing, malformed, placeholder, incomplete, mismatched, or unlinked evidence remains locked. The validator produces a machine-readable order-gate report in CI, and its unit tests include explicit placeholder, unresolved-Class-A, unlinked-hash, missing-file, and complete-valid-evidence cases.

This hardening changes only the assurance unlock predicate. It does not alter accepted Stage-8/9 evidence, the frozen Stage-9.5 base protocol, or the replay-equivalence scientific object.

### External-artifact execution provenance boundary

Stage 9.5-1 recovery verification and the Stage 9.5-6 historical replay may legitimately execute outside GitHub Actions because the governing external checkpoint/archive bytes are not committed and no authoritative CI handoff mechanism is presently frozen. Therefore the closure authority is the frozen scientific/recovery identity plus canonical verification-report hashes and their explicit linkage from the closure record. The small native Stage-9.5-1 `fresh_clone_reconstruction_report.json` and prospective Stage-9.5-6 `replay_equivalence_report.json` must be preserved unchanged under `results/audits/stage9_5_full_seed_rerun_v1/`; the order gate directly parses both, rejects evidence paths that escape the repository, recomputes their canonical hashes, and verifies their frozen successful-recovery/replay fields. The Stage-9.5-1 report may be produced before the later 9.5-6 replay closure, but its recorded `repository_head` must be a valid Git ancestor of the 9.5-6 `audited_head`; equality is not required. The recovered checkpoint/archive bytes remain external and must not be committed merely to satisfy closure. GitHub Actions workflow/job/artifact IDs are supplemental provenance when available; they must not become mandatory closure predicates unless a prospective, authoritative transfer/execution mechanism is first frozen before recovery or rerun outcomes are inspected.
### Current assurance status — 16 October 2026

The historical gate-state section above records the state at the time of the original order correction. The current Stage-9.5-1 reconstruction state is **0 identity failures / 2 external-artifact blockers**: `system_a_checkpoint_bytes_missing` and `stage8_large_artifact_archive_missing`. Stage 9.5-6 is therefore blocked by both unresolved external prerequisites and by the prospectively frozen replay-equivalence execution requirements; checkpoint recovery alone is not closure. Stage 9.5-7/8/9 remain provisional/locked in the current workflow, Stage 9.5 overall remains **OPEN / BLOCKED**, and Stage 10 remains **PROHIBITED**.
