# Stage 9.5-2 Oracle v1.1 Summary-Schema Adapter Correction

**Status:** TECHNICAL ORACLE-HARNESS CORRECTION AFTER FIRST EXECUTION  
**Failed head:** `d828901609ca761fdfd9dcf343dd4529a7fc6f5f`  
**Workflow:** `38456294408`  
**Oracle job:** `115499777695`

## First-run result

The prospective oracle freeze verification passed and all eight oracle unit tests passed. The oracle then failed during its first Stage-8 confirmatory summary comparison with `KeyError: "values"`.

No Stage-8/9 scientific evidence mismatch was established by that run because the comparison traversal terminated before a complete mismatch ledger could be produced.

## Root cause

The independent oracle intentionally uses one generic internal summary representation with a per-seed vector named `values`.

The accepted Stage-9 aggregate uses that same `values` field. The accepted Stage-8 `confirmatory_analysis.json`, however, names the equivalent per-seed endpoint vector `effects`.

The v1 implementation incorrectly assumed the Stage-9 field name for both formats.

## v1.1 correction

v1.1:

1. compares oracle `values` to accepted Stage-8 `effects`;
2. leaves Stage-9 comparison against accepted `values` unchanged;
3. adds a regression test for the Stage-8 summary shape;
4. creates the output directory before evidence traversal; and
5. writes a machine-readable exception report if any future unexpected exception occurs before normal report finalization.

The statistical definitions, tolerances, frozen endpoint family, Stage-9 condition set, and immutable evidence inputs are unchanged.

No accepted scientific object or result is modified.
