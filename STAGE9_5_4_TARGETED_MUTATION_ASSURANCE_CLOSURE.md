# Stage 9.5-4 Targeted Mutation Assurance Closure

**Status:** CLOSED — STAGE 9.5-4 ONLY  
**Audited head:** `f20d0bf2b122b263d27d966700bfbdee209d3287`  
**Workflow:** `38546139132`  
**Mutation job:** `115792552457`

## Closure result

Stage 9.5-4 is closed.

The frozen mutation contract defined 11 high-risk mutant families and required 100% kill.

Accepted v1.1 result:

- defined mutants: **11**;
- executed mutants: **11**;
- killed mutants: **11**;
- survivors: **0**;
- kill rate: **1.0**;
- required kill rate: **1.0**.

Evidence:

- artifact: `stage9-5-targeted-mutations-v1-1`;
- artifact ID: `11884388614`;
- artifact ZIP SHA-256: `8d02cd659be84de34efd7fc271db035cfb8ac9e72129bc939203c0a316aaf603`;
- report canonical SHA-256: `c2729d7a5e20e6ed1c54d233085b909d2a1c273b71a28ab52f1b59cdbf07fc9a`;
- same-head Stage-9 robustness contract: success.

## Mutant families killed

All frozen mutant families were killed:

1. maturity `<` versus `<=`;
2. publication/effective-index boundary mutation;
3. prediction/label event-order inversion;
4. boundary masking removal;
5. checkpoint identity bypass;
6. seed/R0/threshold comparison bypass;
7. generation-validation disjointness bypass;
8. opportunity-budget off-by-one/fifth opportunity;
9. nonzero symbolic contribution at `lambda=1`;
10. manifest/hash verification bypass;
11. arm/shared-neural identity comparison bypass.

The mutation tests use actual production function source as the mutation substrate. Each transformation asserts the target source pattern occurs exactly as expected before compiling the mutated function in test-only memory.

## Failed-iteration preservation

The first v1 mutation run remains preserved. It killed 10/11 and reported M06 as a survivor because the R0 sub-fixture created two canonically identical empty R0 states that differed only in neural checkpoint label. The production verifier correctly accepted those states. v1.1 corrected only that test fixture by creating genuinely different R0 starting rule states.

The frozen mutation family, kill criterion, production scientific source tree, and accepted Stage-8/9 evidence were unchanged.

## Scope

No production scientific source file was modified for mutation convenience. No accepted scientific result changed. No Stage-10 outcomes were accessed.

Current gate state after this closure:

- 9.5-0: closed;
- 9.5-1: open / Class-A blocked;
- 9.5-2: closed;
- 9.5-3: closed;
- 9.5-4: closed;
- 9.5-5: next assurance package;
- Stage 10: prohibited.
