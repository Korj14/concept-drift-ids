# Stage 9.5 v1.5.1 Scanner Serialization Correction

**Status:** TECHNICAL HARNESS CORRECTION BEFORE ACCEPTED v1.5 COMPLETENESS EVIDENCE  
**Governing protocol:** `STAGE9_5_Q1_INDEPENDENT_ASSURANCE_PROTOCOL.md`

After freezing the v1.5 register, a direct source sanity check found two scanner serialization defects before accepting any v1.5 result:

1. a literal `\\n` token was inserted between raw-string fragments in `MATERIAL_RE`;
2. `ExpressionVisitor` referenced `EXPRESSION_CONTEXT_RE`, but the definition had not been inserted.

The v1.5 register, hash-bound scan scope, exact/unique matching rule, materiality policy, accepted Stage-8/9 values, and closure criteria are unchanged. This correction fixes only scanner source serialization.

Any workflow that executed the malformed head is technical failure evidence and is not accepted as a completeness result.
