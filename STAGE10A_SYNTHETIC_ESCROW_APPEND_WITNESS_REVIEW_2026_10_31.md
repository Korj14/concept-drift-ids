# Stage-10A — supplemental synthetic escrow / append witness engineering review

**Role:** WARM engineering test evidence only. Not production evidence, scientific protocol, second state authority or RELEASE. **Stage-10A treatment: HOLD.**

## Prior accepted design

The Stage-8-compatible shared Phase-A writer per seed and three read-only Phase-B symbolic consumers remain the chosen *synthetic-only design direction*. Do not change accepted Stage-8/9 evidence, frozen master v1.1, Stage-10A GoldenEye manifest, or accepted original Wednesday/checkpoint receipts. Existing Phase-A six JSONL streams and supplemental seal are retained without modification. This experiment does not replace the existing synthetic schema or independent envelope audits.

## Bounded new test

`tools/stage10/stage10a_escrow_append_synthetic.py` models an append/fsync acknowledgement before opening a 5,000-logical-row matured-label gate. It emits only deterministic fake neural hashes and deterministic fixture labels. The script is intentionally limited to 5,001 or 5,002 rows, seed IDs 0–4; 138,530 rows are rejected. The test suite verifies five seeds, duplicate writer rejection, prediction preceding matured labels, failed fsync not granting the current label, cross-seed and duplicate escrow grants, boundary/label contamination, altered journal event/hash chains and changed RELEASE claims. A separate independent read-only module (`stage10a_escrow_append_synthetic_audit.py`) reconstructs fixture events without importing the writer or trusting the writer's file hashes.

**Critical limitation:** this is a same-process simulation, *not* an OS/process-separated label escrow, independently trusted wall-clock or durable disk witness, authenticated GitHub Actions runtime, or proof that any accepted Stage-8 neural runner has been instrumented. Tests use a stubbed `os.fsync` to observe call order and do not assert persistence across power failure. The verifier cannot prove an `fsync` happened merely from a retrospective JSON log. It validates raw fixture consistency, not external causality. No original CSV, checkpoints, model imports, neural predictions, adaptation, real arm execution, or treatment outcomes are accessed.

## Outstanding prospective production design choices

1. Choose an external, independently observable exact-head runtime witness, dependency/environment lock, and attempt identity; self-declared Git hashes remain insufficient.
2. Decide between OS/process-separated mature-label escrow or equivalent enforceable label-access separation; prove no change to the frozen adaptation semantics.
3. Decide protected initial/child checkpoint byte custody and read-only model resolver access; validate true parent/child optimizer/replay/RNG provenance.
4. Confirm production append-before-label durability and chronology via a trusted external observer, not this simulated acknowledgement.
5. Specify Phase-B read-only access controls and an independent evaluator that cannot leak the known 69,260 boundary upstream.
6. Clarify S10-04 program-wide dependencies versus the Stage-10A stage-specific RELEASE requirement, without treating criteria freeze as replication.

No governing production-schema freeze is claimed. The HOT `STAGE10A_CURRENT_STATE_AND_RESUME.md` alone carries progress. After source-only CI succeeds at an exact commit, update HOT with a minimal pointer; retain prior synthetic reviews as WARM. A separate versioned RELEASE remains required before real treatment.
