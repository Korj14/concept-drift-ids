# Stage 9.5-1 Dropbox Recovery Discovery

**Status:** NEW AUTHORITATIVE SURFACE LOCATED / SUCCESS CRITERION NOT YET MET  
**Date:** 17 October 2026  
**Machine record:** `data/manifests/stage9_5_1_dropbox_recovery_discovery_v1.json`  
**Historical negative closure modified:** no  
**Stage-10 access authorized:** no

## Why this note exists

The Stage-9.5-1 negative closure was correct for the surfaces available when it
was written. Its own reopening rule explicitly allowed later recovery from a
new authoritative user-held source.

Dropbox was subsequently connected and inspected read-only. This note records
that new evidence without rewriting the historical negative closure or weakening
the frozen Stage-9.5-1 success criterion.

## System-A checkpoints

Dropbox contains five root-level files:

- `/seed_0.pt`
- `/seed_1.pt`
- `/seed_2.pt`
- `/seed_3.pt`
- `/seed_4.pt`

Each file is 76,105 bytes, below Dropbox's 4 MiB content-hash block size.

Dropbox documents its content hash as:

1. split the file into 4 MiB blocks;
2. SHA-256 each block;
3. concatenate the binary block digests;
4. SHA-256 that concatenation.

For a non-empty one-block file this reduces to
`SHA256(binary(SHA256(file_bytes)))`.

For each of the five Dropbox checkpoint candidates, the observed Dropbox
`content_hash` exactly equals that transform of the already-frozen ordinary
SHA-256 checkpoint identity. Therefore the Dropbox files are byte-identical to
the five required original checkpoint byte streams under the documented
content-hash construction.

This is a recovery discovery, not yet a frozen-verifier pass. The files still
must be materialized unchanged onto a verifier-capable filesystem and supplied
to the unchanged Stage-9.5-1 v1.2 verifier.

## Stage-8 heavy archive

Dropbox also contains:

`/cd_primary_v1`

The recursive tree currently contains:

- 253 total entries;
- 203 files;
- 50 folders;
- 1,863,975,043 total file bytes.

The expected major families are present, including:

- all five Phase-A run manifests;
- all five Phase-A prediction traces;
- all five Phase-B seed manifests;
- all ten non-frozen-symbolic maintenance logs;
- all five corrected Phase-C seed manifests;
- all fifteen corrected Phase-C arm evaluations;
- all fifteen corrected Phase-C prediction traces;
- the preserved original Phase-C seed-0 attempt/failure pair.

The accepted Stage-8 compact evidence was then used to reconstruct the exact
same descriptor-linked inventory used by
`fresh_clone_reconstruction.py::_stage8_archive_requirements`.

Result:

- frozen requirement count: **145**;
- Dropbox-present required paths: **140**;
- missing required paths: **5**.

The only missing paths are:

- `phase_b_symbolic_arms/seed-0/c_frozen_symbolic/maintenance.jsonl`
- `phase_b_symbolic_arms/seed-1/c_frozen_symbolic/maintenance.jsonl`
- `phase_b_symbolic_arms/seed-2/c_frozen_symbolic/maintenance.jsonl`
- `phase_b_symbolic_arms/seed-3/c_frozen_symbolic/maintenance.jsonl`
- `phase_b_symbolic_arms/seed-4/c_frozen_symbolic/maintenance.jsonl`

Every accepted C-arm manifest declares the missing file with SHA-256:

`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`

which is the SHA-256 of a zero-byte file. The corresponding accepted
maintenance summaries record zero opportunities, zero publications, and zero
maintenance compute.

A Dropbox-wide title search found only the ten D-arm `maintenance.jsonl`
files. Revision lookup on the exact missing seed-0 C-arm path returned
`FILE_NOT_FOUND`. No compressed `cd_primary_v1`/Stage-8 backup was found in
Dropbox.

## Assurance interpretation

This materially changes the recovery picture but does **not** yet satisfy the
frozen success rule.

The checkpoint family is now located with exact byte identity evidence.

The Stage-8 archive is nearly complete but remains structurally **140/145**.
The fact that the five absent objects are cryptographically specified empty
files does not authorize silently recreating them and relabeling the Dropbox
tree as the recovered original archive.

Therefore:

- the historical negative closure remains preserved as the correct historical
  state at the time it was written;
- Stage-9.5-1 is not yet reopened to successful closure;
- Stage-9.5-6 remains blocked by Stage-9.5-1;
- Stage-9.5-7/8/9 remain locked;
- Stage 10 remains prohibited.

## Next authoritative sequence

1. Recover the five missing zero-byte C-arm maintenance files from an
   authoritative original source/archive representation if one exists.
2. Materialize the five exact Dropbox checkpoint files and the complete
   Stage-8 archive unchanged onto a verifier-capable filesystem.
3. Run the unchanged Stage-9.5-1 v1.2 verifier.
4. Require:
   - `pass=true`;
   - verified checkpoint seeds `[0,1,2,3,4]`;
   - Stage-8 archive `145/145`;
   - zero failures;
   - zero blockers.
5. Only after that verifier-produced success may the historical negative
   closure be superseded/reopened and the frozen Stage-9.5-6 execution handoff
   begin.

No accepted Stage-8/9 scientific result, estimand, comparator, metric, or claim
boundary is changed by this recovery discovery.

### Exhaustive Dropbox revision-history follow-up — 17 October 2026

A later read-only follow-up repeated the Dropbox-wide filename search with
advanced/title-only search semantics. It again returned exactly the ten active
D-arm `maintenance.jsonl` files and no C-frozen maintenance file or second
`cd_primary_v1` tree.

Dropbox revision history was then queried independently for all five exact
missing C-frozen paths, seeds 0 through 4. Every path returned
`FILE_NOT_FOUND`; no current or recoverable historical revision was exposed
for any of the five files.

This closes the presently connected Dropbox surface for this specific recovery
question. It does **not** authorize synthesizing the known-empty files, and it
does not establish that no original copy exists anywhere outside Dropbox. The
governing archive state therefore remains **140/145**, with the same five
zero-byte C-arm maintenance files as the only unresolved archive paths.

