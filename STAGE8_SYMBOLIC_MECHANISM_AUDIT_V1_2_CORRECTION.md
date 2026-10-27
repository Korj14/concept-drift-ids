# Stage 8 Symbolic Mechanism Audit v1.2 Correction

**Status:** VERSIONED POST-PRIMARY MECHANISM-AUDIT IMPLEMENTATION CORRECTION  
**Parent v1.1 config commit:** `533063c72e8e11afb3530e05aa56dcb7c1a3f7a6`  
**Parent v1.1 config manifest:** `de33a7b09b26adefe1b5b574b958930e7f83a756aba9956ac243396a01690946`  
**Parent Stage-8 evidence:** `c2ded83b8195b9321e715626c1f305f9627936e8`

## Why v1.2 exists

The first execution attempt under the correctly frozen v1.1 mechanism configuration failed with:

`KeyError: 'manifest_sha256'`

The failure occurred in `analyze_seed()` when it attempted to persist
`phase_b_arm_manifest_sha256`.

The root cause is an implementation bug in `_phase_b_arm_manifest()`:
the function correctly verified the stored `manifest_sha256`, but used
`pop()` during verification and therefore removed that field from the
returned manifest. Downstream code then attempted to read the removed
field.

This is a mechanism-audit reader defect. It does not alter or invalidate
the frozen Stage-8 primary predictions, treatments, symbolic trajectories,
thresholds, endpoints, or confirmatory statistics.

## Failed v1.1 attempt preservation

The v1.1 configuration remains immutable and must not be overwritten.

The v1.2 configuration records that the v1.1 execution attempt:

- accessed row-level frozen traces;
- failed before any accepted seed result was written;
- raised `KeyError: 'manifest_sha256'`;
- failed at the Phase-B arm-manifest identity capture step;
- made no scientific-scope change.

Any files left under `results/frozen/cd_primary_mechanism_v1_1/` are
historical failed-attempt evidence and must be preserved unchanged and
hashed by the v1.2 configuration preparation.

## v1.2 implementation change

The only scientific-path code change is to preserve the already-verified
`manifest_sha256` field when returning a Phase-B arm manifest:

- read the stored manifest hash without removing it;
- verify canonical integrity against a copy with the hash field excluded;
- return the original manifest, including `manifest_sha256`.

A regression test is added that fails under the v1.1 behavior and passes
only when the verified Phase-B manifest retains its stored identity.

## Versioned identities

v1.2 uses:

- `data/manifests/cd_primary_mechanism_audit_v1_2.json`;
- `results/frozen/cd_primary_mechanism_v1_2/`;
- schema version 3 for the mechanism config.

The v1.2 config must be prepared before any new row-level mechanism
execution under v1.2, committed as the sole changed path in its freeze
commit, and pass exact-head Research Contract CI before execution.

## Interpretation boundary

The mechanism audit remains exploratory/descriptive and post-primary.
No p-value family is created, no Stage-8 result is replaced, and no
scientific treatment, endpoint, threshold, or estimand is changed.
