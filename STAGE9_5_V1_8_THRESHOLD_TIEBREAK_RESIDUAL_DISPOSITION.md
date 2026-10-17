# Stage 9.5 v1.8 Threshold-Tiebreak Residual Disposition

**Status:** VERSIONED REGISTRY COMPLETENESS CORRECTION AFTER v1.7 BLOCK  
**Governing protocol:** `STAGE9_5_Q1_INDEPENDENT_ASSURANCE_PROTOCOL.md`  
**v1.7 scan canonical SHA-256:** `c58e7da9ded76831304bac5c7421a056cc1458bb8f4bd2bec040e49ef90b712a`  
**v1.7 CI artifact ZIP SHA-256:** `071ca1604171fafd186722475570c779809f07fbede6ae38b81cc80ff9d10eb7`

## 1. v1.7 result

The v1.7 scanner and its 17 unit tests passed. The real completeness scan then blocked on exactly one unclassified high-leverage material occurrence and zero ambiguous mappings:

- `src/concept_drift_ids/neural.py:201`
- `select_mcc_threshold :: -abs(float(thresholds[i]) - 0.5)`
- literal value: `0.5`

The same-head Stage-9 regression contract passed.

## 2. Disposition

The literal is the final development-time tie-break target in the already-frozen System-A threshold-selection policy: maximize MCC, then F1, then lower FPR, then choose the threshold closest to 0.5.

It is not an observed threshold, not a Stage-8/9 outcome-derived value, and not a new treatment parameter.

The v1.7 register already contained the scientific control `system_a.threshold_policy`, including the semantic policy `closest_to_0.5`, but its strict `scan_values` list omitted the numeric literal `0.5`. Therefore the residual is a registry-completeness defect only.

## 3. v1.8 correction

v1.8 adds numeric `0.5` to `system_a.threshold_policy.scan_values`.

No scanner matching rule, scan scope, accepted Stage-8/9 scientific value, treatment, endpoint, seed, threshold, scenario, information set, or inference rule changes.

Closure still requires:
- zero unclassified material candidates; and
- zero ambiguous material mappings.
