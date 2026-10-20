# Stage 9.5 v1.9 Material-Name Coverage Correction

**Status:** VERSIONED SCANNER/REGISTRY COMPLETENESS CORRECTION FOUND BY EXCLUSION-LOG REVIEW  
**Governing protocol:** `STAGE9_5_Q1_INDEPENDENT_ASSURANCE_PROTOCOL.md`

## 1. Finding

A focused review of the retained v1.7 exclusion log found direct source mirrors of accepted scientific controls being excluded before register matching because their identifiers were not recognized by the material-name matcher:

- `ADWIN_CONFIG = (0.002, 32, 5, 5, 10)`;
- `PAGE_HINKLEY_CONFIG = (30, 0.005, 50.0, 0.9999, "both")`.

Both control families were already present in the parameter register with correct accepted values and source locations. The defect was scanner material-name coverage, not missing scientific prespecification.

The same review found `EXPECTED_ACTIVE_COUNTS = {0:7,1:6,2:7,3:6,4:6}` in the accepted R0.v2 loader. Those counts are redundant with stronger hash/canonical identity checks, but they are executable acceptance assertions and therefore should be explicitly classified rather than silently excluded.

## 2. Disposition

- ADWIN values remain the frozen primary detector library/default controls.
- Page-Hinkley values remain the frozen Stage-9 robustness detector controls.
- R0 active counts are classified as a `derived_quantity` tied to the accepted hash-bound R0.v2 identity.

No scientific value changes.

## 3. v1.9 correction

v1.9:
1. extends material-name discovery to `adwin`, `page_hinkley`, and active-count identifiers;
2. adds the R0 expected active-count assertion to the register as a derived identity check;
3. adds a regression test requiring all three direct-source constant families to be discovered as material and successfully mapped;
4. retains strict locator-plus-value matching and the hash-bound scientific-source scope.

The earlier v1.8/v1.8.1 runs are not accepted as 9.5-0 closure evidence even if technically green, because this exclusion-log defect was discovered before closure.

Closure remains zero unclassified material candidates and zero ambiguous material mappings, followed by exclusion-log sanity review.
