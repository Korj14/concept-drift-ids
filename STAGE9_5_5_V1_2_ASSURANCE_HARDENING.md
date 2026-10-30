# Stage 9.5-5 v1.2 Assurance-Harness Hardening

**Status:** PROSPECTIVE ASSURANCE-ONLY CORRECTION AFTER v1.1 DISCOVERY

The v1.1 self-scoped discovery is preserved unchanged. It reported 167 Ruff findings and 59 mypy findings over 51 Ruff-scoped files and 44 mypy-scoped files.

## Corrections selected

v1.2 changes only Stage-9.5 assurance code.

1. **Parameter scanner literal extraction**
   - expected non-literal AST values remain skipped;
   - only the documented `ast.literal_eval` failure classes are treated as non-literal;
   - unexpected exceptions are no longer swallowed and therefore fail the assurance run.

2. **Static-report parser**
   - Ruff JSON decode failure is caught specifically;
   - non-list JSON is reported as an explicit type/tooling error;
   - broad `Exception` swallowing is removed.

3. **Fresh-clone verifier**
   - scenario version is explicitly checked for presence before integer comparison;
   - the historical ancestry subprocess explicitly records `check=False`.

4. **Independent statistical oracle**
   - count-derived denominators use distinct typed locals;
   - Stage-9 nested metric containers receive explicit types.

No scientific source module, accepted evidence object, parameter, statistical definition, or historical runtime dependency lock is modified by this correction.

The remaining static findings after v1.2 will be fingerprinted and dispositioned individually. Style/legacy findings in frozen scientific source will not be rewritten solely to satisfy current lint conventions.
