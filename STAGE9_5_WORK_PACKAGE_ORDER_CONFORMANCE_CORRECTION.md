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
