# Stage 9.5-3 / 9.5-4 Causal Property and Targeted Mutation Assurance Freeze

**Status:** PROSPECTIVELY FROZEN BEFORE 9.5-3/4 EXECUTION  
**Stage 9.5-0:** closed  
**Stage 9.5-1:** open / Class-A blocked on missing exact System-A checkpoint bytes  
**Stage 9.5-2:** closed  
**Stage 10:** prohibited

## Stage 9.5-3 rule

The Stage-9.5 property suite will contain a dedicated adversarial fixture for every frozen causal/information invariant even when an existing production test already provides related coverage.

Existing tests are evidence anchors, not substitutes for the dedicated assurance fixture unless the new Stage-9.5 test explicitly exercises the same negative path.

The property suite covers prediction-before-label timing, detector maturity, boundary hiding, checkpoint-pure detector epochs, shared neural identity, R0 start identity, seed/threshold binding, generation-validation disjointness, prediction-evidence immutability, treatment-independent detector inputs, cross-trigger symbolic operator/RNG identity, lambda-1 predictive isolation, and write-once/freeze semantics.

Closure requires every dedicated property fixture to fail closed when its invariant is violated.

## Stage 9.5-4 rule

Mutation testing is targeted to the protocol-defined scientific guards rather than measured by an arbitrary project-wide mutation percentage.

The frozen mutation set contains 11 high-risk mutant families:

1. maturity `<` versus `<=`;
2. publication/effective-index `<` versus `<=`;
3. prediction/label event-order inversion;
4. boundary masking removal;
5. checkpoint identity bypass;
6. seed/R0/threshold comparison bypass;
7. generation-validation disjointness bypass;
8. opportunity-budget off-by-one or no-op non-consumption;
9. nonzero symbolic contribution at `lambda=1`;
10. manifest/hash verification bypass;
11. arm/shared-neural identity comparison bypass.

Closure requires **11/11 killed**. Equivalent or non-executable mutants require explicit machine-readable justification and remain part of the denominator until dispositioned; they may not disappear silently.

## Implementation isolation

New assurance tests and mutation harnesses belong under `tests/stage9_5/` and `tools/stage9_5/`.

Frozen scientific execution modules will not be rewritten merely to make mutation injection easier. Mutation execution should use controlled monkeypatching, source-level temporary copies, or function-level injected substitutes in test-only space while preserving the accepted source tree.

The 9.5-1 checkpoint blocker remains independent and unresolved. Passing 9.5-3/4 cannot downgrade or close it.
