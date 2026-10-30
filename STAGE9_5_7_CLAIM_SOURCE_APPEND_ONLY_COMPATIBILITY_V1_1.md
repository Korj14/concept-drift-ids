# Stage 9.5-7 Claim-Source Append-Only Compatibility Correction v1.1

**Status:** PROPOSED ADDITIVE ASSURANCE-ONLY CORRECTION; no Stage-9.5 closure asserted.
**Observed failing branch:** `stage9-5-q1-assurance` at `207c05e5e99568fb4cb7f89996af3314be0d5ef3`.
**Failed PR run:** [40991029098](https://github.com/Korj14/concept-drift-ids/actions/runs/40991029098), `claim-traceability` job `123853373929` (1 failed, 3 passed).
**Immediate downstream outcomes:** Stage-9.5-8 and Stage-9.5-9 skipped.
**Scope:** The Stage-9.5-7 *source-identity assurance verifier* only. The original v1 freeze and all accepted scientific evidence remain unchanged.

## Failure and scope of correction

The frozen Stage-9.5 claim contract records the exact original Git blob of `METHODOLOGY_LEDGER.md` as
`9b977705b9748138bb12745e9f0fb3d77d73c2b2` at historical commit
`b141a65033fee1ffbe7709a54838ea1af1324225`. The old verifier incorrectly
required this exact blob to remain at `HEAD` indefinitely. Subsequent append-only
chronological history (including pre-outcome Stage-10 source documentation) yielded
`8a14bd17528851e26748b993b7ae85cd90c40db3` at
`207c05e5e99568fb4cb7f89996af3314be0d5ef3`.

The original claim-source interpretation remains the *frozen historical blob*.
Newer ledger entries do not expand the frozen claim universe or authorize new
numeric values. The 23 original claims and 20 families, their immutable-evidence
selectors, and claim definitions are unchanged.

## Versioned fail-closed v1.1 verification

`data/manifests/stage9_5_claim_source_compatibility_v1_1.json` narrowly
records this exception. The verifier must:

1. Require exact `HEAD` Git blob identities of both original v1 claim contract
   (`b38302c509bda9af65e2dbf319e7e903a00ab111`) and definitions
   (`18157779d5860b366b568926d6a89a2205e75480`), and reject any v1.1
   policy change from its explicitly pinned contents.
2. Verify the frozen historical commit resolves `METHODOLOGY_LEDGER.md` to
   `9b977705...` and that the published pre-correction commit resolves it to
   `8a14bd...`, and require that pre-correction commit to be a current ancestor.
3. Reject uncommitted modifications to the original v1 contract, definitions or any of the four claim-source files, including on Windows checkouts via Git-native diff normalization. Read all three ledger Git *blob objects* as bytes and require the published
   pre-correction blob to begin with every byte of the historical frozen blob,
   and the current `HEAD` blob to begin with every byte of the pre-correction blob.
   Rewriting or truncating either historically preserved section must fail.
4. Continue to require **exact `HEAD` Git blob equality** for each of the three
   Stage-8/9 interpretation documents. No additional source has an exception.
5. Record the historical **frozen** blob, *not* the current ledger blob, in each
   claim row's `source_blob_sha`; explicitly record the v1.1 compatibility
   policy and preserved witness at the report level.
6. Preserve all numerical evidence selectors, display transformations,
   rounding rules, interpretation status, scientific parameters and accepted
   evidence objects. Do not read later ledger additions as numeric authority.

## Execution boundaries and negative evidence

The old run's failure and the historical out-of-order 9.5-7/8/9 closures remain
unaltered. Local success of this code is not Stage-9.5-7 protocol closure:
rerun the valid Stage-9.5-6 predecessor order gate, test 9.5-7 on its new exact
head, then 9.5-8 and 9.5-9 in order. Diagnose the independent static baseline
(`ruff=154`, `mypy=55`) and hosted missing-external-artifact failures separately.
The verified local 145/145 heavy archive and original five checkpoints do not
imply those bytes are present on an ephemeral GitHub runner.

**No Stage-10 adaptive/treatment outcome access is permitted by this correction.
No overall Stage-9.5 closure is asserted.**
