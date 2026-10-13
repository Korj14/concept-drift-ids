# Stage 8 Symbolic Mechanism Audit v1.1 Correction

**Status:** VERSIONED POST-PRIMARY MECHANISM-AUDIT CORRECTION  
**Historical v1 config:** `data/manifests/cd_primary_mechanism_audit_v1.json`  
**Historical v1 manifest:** `b5ea68cebdbbe5c316544bcc187f2b771babbdf01b1c4dcb3373763f0e72fd87`  
**Historical v1 source commit:** `bf33f2312733ae183a03ce3816ab4d31a4b3d267`

## Why v1.1 exists

The historical v1 mechanism config was validly frozen before row-level mechanism trace inspection.

Subsequent adversarial source review, performed while preparing execution, found several issues in the
mechanism-audit implementation/protocol:

1. the observable both-covered stratum was named `revision`, which over-interpreted coverage state
   as a specific lifecycle transition;
2. same-correct and same-wrong counts required by the protocol were not explicitly persisted;
3. post-write verification required a fully clean worktree, which would reject the audit's own
   untracked result tree;
4. verify-only checked saved JSON/aggregate consistency but did not regenerate every seed result from
   the frozen heavy traces;
5. config preparation was not explicitly exposed as a no-row-trace-access freeze gate.

These are mechanism-audit implementation/governance issues. They do not alter Stage-8 primary
predictions, endpoints, treatment trajectories, thresholds, or confirmatory statistics.

## Historical v1 preservation

The v1 config is immutable and must never be overwritten.

Any historical v1 output found locally is also preserved unchanged.

v1.1 preparation records whether the historical v1 output root exists and, if present, hashes every
file under it. This makes prior local execution visible rather than silently erasing it.

## v1.1 changes

The corrected observable strata are:

- withdrawal;
- addition;
- retained_authority;
- neither_authoritative.

The mathematical three-component Shapley decomposition is unchanged in substance: it still allocates
the realized C-to-target MCC difference across the three mutually exclusive authority-change strata.

v1.1 additionally:

- records same-correct and same-wrong counts;
- enforces exhaustive row-accounting invariants;
- uses a fully clean worktree only at execution start;
- allows post-write verification with untracked result files while rejecting tracked changes;
- re-reads/re-hashes frozen traces and regenerates every seed result during verify-only;
- writes corrected evidence under `results/frozen/cd_primary_mechanism_v1_1/`;
- uses `data/manifests/cd_primary_mechanism_audit_v1_1.json`.

## Interpretation

The audit remains explicitly exploratory/post-primary. No new p-value family is created.

If historical v1 outputs exist, v1.1 is a versioned correction and v1 remains part of the audit trail.
If historical v1 outputs do not exist, v1.1 is still used because the v1 config had already frozen a
different source/terminology identity.

No Stage-8 primary restart is implied by this correction.
