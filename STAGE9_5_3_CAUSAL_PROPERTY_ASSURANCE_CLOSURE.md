# Stage 9.5-3 Causal / Information Property Assurance Closure

**Status:** CLOSED — STAGE 9.5-3 ONLY  
**Audited head:** `ed2ea612b06d48c6880f54d8048cd3357a9234ec`  
**Workflow:** `38544323625`  
**Property job:** `115786498737`

## Closure result

Stage 9.5-3 is closed.

The prospectively frozen property contract required 13 dedicated adversarial fail-closed fixtures. The accepted run collected exactly those 13 node IDs, with no missing or extra fixtures, and all 13 passed.

Evidence:

- artifact: `stage9-5-causal-properties-v1`;
- artifact ID: `11884001912`;
- artifact ZIP SHA-256: `24fa95251939b69d092bc5cb05836f86237879c9f27ba34d7dd9f7cb74a03940`;
- report canonical SHA-256: `e80084fc8d1972d26955f22331585e9501954a9dea7ca03a2966cc8640fb6c8d`;
- same-head Stage-9 robustness contract: success.

## Frozen properties exercised

The accepted suite negatively exercised:

1. prediction before label release;
2. detector use before label maturity;
3. boundary/reference contamination;
4. checkpoint-impure detector admission;
5. shared-neural/control-plane divergence across matched arms;
6. R0 starting-state divergence;
7. seed/threshold binding mismatch;
8. generation/validation evidence overlap;
9. retrospective prediction-evidence replacement;
10. treatment-dependent detector input;
11. cross-trigger symbolic operator/RNG mismatch;
12. nonzero symbolic predictive influence at lambda=1;
13. write-after-freeze / partial write-once reuse.

Each fixture required the implementation to fail closed when the invariant was violated.

## Scope

No production scientific module was modified for test convenience. No Stage-8/9 scientific object or result changed. No Stage-10 outcomes were accessed.

This closure does not resolve the independent Stage 9.5-1 Class-A checkpoint provenance blocker.

Current gate state after this closure:

- 9.5-0: closed;
- 9.5-1: open / Class-A blocked;
- 9.5-2: closed;
- 9.5-3: closed;
- 9.5-4: next assurance package;
- Stage 10: prohibited.
