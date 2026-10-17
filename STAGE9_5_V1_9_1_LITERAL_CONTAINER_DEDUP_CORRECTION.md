# Stage 9.5 v1.9.1 Literal-Container Deduplication Correction

**Status:** TECHNICAL SCANNER CLASSIFICATION CORRECTION BEFORE v1.9 COMPLETENESS SCAN  
**Governing protocol:** `STAGE9_5_Q1_INDEPENDENT_ASSURANCE_PROTOCOL.md`  
**Failed head:** `08c9687a777d18b4fe9aa38d302c985ee65a582e`

## 1. Failure

The v1.9 scanner regression suite reached 17 passes and one failure before the real completeness scan executed. The failing test showed that `EXPECTED_ACTIVE_COUNTS = {0:7,1:6,2:7,3:6,4:6}` was correctly discovered at assignment level, but dictionary keys `3` and `4` were then rediscovered by the expression visitor as separate material literals.

The same-head Stage-9 regression contract passed.

## 2. Cause

For literal assignments, the scanner already emits the assigned scalar/list/tuple/dictionary **values** under the semantic assignment name. Its duplicate-suppression bookkeeping recorded emitted values, but dictionary keys are not returned by `_flatten_values`. Expression traversal therefore revisited some dictionary keys and treated them as if they were independent parameter literals.

Seed keys in a per-seed identity/count mapping are identifiers, not additional scientific parameter values.

## 3. v1.9.1 correction

When `ast.literal_eval` succeeds for an assignment value, v1.9.1 records every `ast.Constant` node inside that literal container as already handled. The expression visitor skips those exact AST locations.

This preserves:
- assignment-level discovery and strict register matching for all actual assigned values;
- expression-level discovery for literals that are genuinely embedded in calculations, comparisons, slices, calls, or control logic;
- the v1.9 parameter register unchanged.

A dedicated regression assertion requires dictionary keys inside an already-parsed literal assignment not to reappear as `python_expression` candidates.

No Stage-8/9 scientific value, scan scope, treatment, endpoint, seed, threshold, scenario, information set, or inference rule changes.
