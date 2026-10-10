# Stage 8 Symbolic Mechanism Audit v1.2 Execution Correction

**Status:** VERSIONED POST-PRIMARY EXECUTION CORRECTION  
**Parent v1.1 config:** `data/manifests/cd_primary_mechanism_audit_v1_1.json`  
**Parent v1.1 manifest:** `de33a7b09b26adefe1b5b574b958930e7f83a756aba9956ac243396a01690946`  
**Parent v1.1 config commit:** `533063c72e8e11afb3530e05aa56dcb7c1a3f7a6`

## Why v1.2 exists

The first execution attempt under the validly frozen v1.1 config aborted with:

```text
KeyError: 'manifest_sha256'
```

at the metadata-recording step in `analyze_seed()`.

The frozen Phase-B arm manifests are valid and do contain `manifest_sha256`. The defect was internal
to the mechanism-audit reader: `_phase_b_arm_manifest()` verified the embedded canonical hash and
then removed it with `pop()`, while `analyze_seed()` subsequently attempted to record the same
verified identity in the seed result.

This failure occurred after frozen row-level Phase-C traces had been read for the first comparison,
but before a seed result, aggregate, or audit manifest was written. Accordingly, v1.2 does **not**
claim a pre-trace preparation state.

## Scientific classification

This is an execution/software correction to the post-primary exploratory mechanism audit. It does not
change any Stage-8 primary prediction, treatment, endpoint, threshold, detector event, symbolic
trajectory, confirmatory statistic, mechanism stratum, Shapley definition, seed set, comparison arm,
or reporting domain.

The correction is outcome-agnostic: the code change retains already-verified Phase-B manifest
metadata after verification. It does not alter row classification or any mechanism calculation.

The immutable Stage-8 primary evidence remains unchanged and is not restarted.

## Historical preservation

The v1 and v1.1 configs remain immutable.

v1.2 preparation records:

- the historical v1 identity/output state;
- the frozen v1.1 config identity and commit;
- whether the local v1.1 output root exists;
- hashes of any files present under the v1.1 output root;
- that row-level traces were accessed during the failed v1.1 execution before v1.2 preparation.

Any partial v1.1 files, if present, must remain unchanged and are treated as failed-attempt evidence.

## v1.2 code correction

`_phase_b_arm_manifest()` now:

1. reads the frozen arm manifest;
2. removes the embedded `manifest_sha256` only for canonical verification;
3. verifies it against the canonical payload;
4. restores the verified `manifest_sha256` into the returned in-memory object.

A regression test requires the verified identity to survive the reader and therefore prevents the
specific v1.1 failure from recurring silently.

Corrected outputs use new identities:

- config: `data/manifests/cd_primary_mechanism_audit_v1_2.json`;
- output: `results/frozen/cd_primary_mechanism_v1_2/`.

## Interpretation boundary

The mechanism audit remains exploratory/descriptive and post-primary. No new p-value family is
created, and no result from this audit may replace the frozen Stage-8 primary confirmatory analysis.
