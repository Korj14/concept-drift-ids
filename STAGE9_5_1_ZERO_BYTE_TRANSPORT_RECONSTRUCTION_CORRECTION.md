# Stage 9.5-1 Zero-Byte Transport Reconstruction Correction

**Status:** FROZEN BEFORE EXECUTION  
**Correction type:** additive assurance / transport reconstruction  
**Scientific object changed:** no  
**Accepted Stage-8/9 evidence replaced:** no  
**Stage-10 access authorized:** no

## Purpose

A newly connected authoritative Dropbox surface recovered the five exact
System-A checkpoint identities and 140/145 descriptor-linked Stage-8 heavy
archive paths.

The only five missing archive paths are:

- `phase_b_symbolic_arms/seed-0/c_frozen_symbolic/maintenance.jsonl`
- `phase_b_symbolic_arms/seed-1/c_frozen_symbolic/maintenance.jsonl`
- `phase_b_symbolic_arms/seed-2/c_frozen_symbolic/maintenance.jsonl`
- `phase_b_symbolic_arms/seed-3/c_frozen_symbolic/maintenance.jsonl`
- `phase_b_symbolic_arms/seed-4/c_frozen_symbolic/maintenance.jsonl`

Every accepted C-arm manifest binds its missing maintenance path to SHA-256:

`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`

which is exactly the SHA-256 of the empty byte string.

Each accepted C-arm manifest also records zero opportunities, zero
publications, zero candidates, and zero maintenance compute/timing.

## New forensic fact

The initial Dropbox discovery and ordinary revision-history checks did not
authorize recreating those five objects. A later exhaustive read-only Dropbox
restore-event audit added a materially stronger fact.

For `/cd_primary_v1`:

- current tree entries: **253**;
- restore/history events: **253**;
- operation types observed: **ADD only**;
- delete/move/rename/restore/rollback events: **0**;
- C-frozen folder ADD events: seeds 0-4;
- C-frozen `arm_manifest.json` ADD events: seeds 0-4;
- C-frozen `initial_state.json` ADD events: seeds 0-4;
- C-frozen `final_state.json` ADD events: seeds 0-4;
- D-drift and D-periodic `maintenance.jsonl` ADD events: seeds 0-4;
- C-frozen `maintenance.jsonl` ADD events: **0**.

The full history is exhausted. The five missing paths were therefore not
objects that Dropbox later deleted, moved, renamed, restored, or rolled back.
The connected archive was ingested without those zero-byte objects.

The machine record is:

`data/manifests/stage9_5_1_dropbox_restore_event_forensics_v1.json`

## Governing-plan interpretation

The reconciled plan requires the project to:

> archive or provide a reconstructible route to every non-Git heavy artifact
> needed to independently verify Stage 8/9 compact evidence.

This correction uses the **reconstructible-route** branch of that requirement.

It does not claim that the original Dropbox filesystem objects were recovered.
Instead, it reconstructs the exact byte streams already frozen by the accepted
Stage-8 manifests, after the Dropbox transport omission itself has been
forensically demonstrated.

This is a versioned correction to the earlier, appropriately conservative
decision not to recreate the files from their hashes alone. The new decision is
based on additional transport-history evidence, not on Stage-8/9 predictive
outcomes.

## Frozen contract

The machine contract is:

`data/manifests/stage9_5_1_zero_byte_transport_reconstruction_v1.json`

The implementation is:

`tools/stage9_5/zero_byte_transport_reconstruction.py`

Dedicated tests are:

`tests/stage9_5/test_zero_byte_transport_reconstruction.py`

The utility is intentionally narrow. It may operate only on the five paths
listed above.

Before any write, it requires all five entries to pass preflight. For each
seed it verifies:

1. the committed accepted C-arm manifest exists;
2. the accepted manifest's payload and manifest self-hashes are valid;
3. the materialized archive's C-arm `arm_manifest.json` is byte-identical to
   the committed accepted compact-evidence copy;
4. the accepted manifest declares exactly
   `files.maintenance.path = maintenance.jsonl`;
5. the descriptor SHA-256 is the frozen empty-file hash;
6. the accepted maintenance summary records zero opportunity/publication/
   candidate/compute/SHAP/surrogate/lifecycle values;
7. the accepted publications list is empty;
8. the destination path remains inside the supplied archive root;
9. an existing target is never overwritten.

The tool also verifies the pinned Git-blob identities of the Dropbox discovery
records and the exhaustive restore-event forensic record.

Only if **all five preconditions pass** may it create any missing file. Creation
uses exclusive-create semantics and writes exactly zero bytes.

## Execution

After the Dropbox Stage-8 tree has been materialized unchanged onto a
verifier-capable filesystem:

```bash
python tools/stage9_5/zero_byte_transport_reconstruction.py \
  --stage8-archive-root <materialized-cd_primary_v1-root> \
  --output results/audits/stage9_5_full_seed_rerun_v1/zero_byte_transport_reconstruction_report.json
```

The reconstruction report must have:

- `pass = true`;
- exactly five required paths;
- each path either `preexisting_verified` or
  `transport_reconstructed_zero_bytes`;
- zero failures;
- `original_dropbox_objects_recovered = false`;
- `transport_reconstruction_explicit = true`;
- `governing_verifier_unchanged = true`.

The report is **not** Stage-9.5-1 success authority.

## Unchanged Stage-9.5-1 authority

After the checkpoint files and reconstructed/completed Stage-8 tree are
available locally, run the unchanged v1.2 verifier:

```bash
python tools/stage9_5/fresh_clone_reconstruction.py \
  --output-dir results/audits/stage9_5_full_seed_rerun_v1 \
  --checkpoint-root <directory-containing-seed_0.pt-through-seed_4.pt> \
  --stage8-archive-root <materialized-cd_primary_v1-root>
```

Successful reopening/supersession of the historical negative closure still
requires verifier-produced evidence with:

- `pass = true`;
- verified checkpoint seeds `[0,1,2,3,4]`;
- Stage-8 archive requirement count **145**;
- Stage-8 archive verified count **145**;
- zero failures;
- zero blockers.

No verifier rule, accepted hash, file count, scientific treatment, Stage-8/9
result, or claim boundary is relaxed by this correction.

## Current execution limitation

The connected Dropbox plugin can identify the raw files and issue single-use
download URLs, but the current verifier container cannot directly consume those
connector URLs through its sanctioned raw-byte materialization path. Therefore
the Dropbox checkpoint/archive bytes still need to be materialized on a
verifier-capable filesystem outside this connector-to-container boundary before
the correction and unchanged verifier can execute.

This is an execution transport limitation, not a new scientific or evidence
criterion.

## Retrospective requirement

The final Stage-9.5 reviewer-facing retrospective must preserve all three
states distinctly:

1. the original negative closure when no personal-cloud source was connected;
2. the later Dropbox partial recovery at 140/145 and the conservative
   no-synthesis decision;
3. the exhaustive 253-event transport-forensics result and the resulting
   explicit reconstructible-route correction for the five uniquely defined
   zero-byte objects.

Collapsing those states into a claim that the negative closure was "wrong" is
not permitted.
