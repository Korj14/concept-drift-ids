# Stage 9.5 v1.10 Final Exclusion-Review Correction

**Status:** VERSIONED COMPLETENESS CORRECTION AFTER GREEN v1.9.1 SCAN, BEFORE 9.5-0 CLOSURE  
**Governing protocol:** `STAGE9_5_Q1_INDEPENDENT_ASSURANCE_PROTOCOL.md`  
**v1.9.1 scan canonical SHA-256:** `f15eb59e75c5d382ebdf6a228e238e7ea9c65ef2d9b7bed0d0b2e249e3360e0a`  
**v1.9.1 parameter-register SHA-256:** `d66edb5d9a8741339996e62c102203dd37ba6ce14fab20a40acd8518a96d6064`  
**v1.9.1 CI artifact ZIP SHA-256:** `ae1eb5db0faf0249cbf2c3e66a296f75c676589466993fa4879afd423b67f8fe`

## 1. v1.9.1 result

The v1.9.1 scanner passed with 462 material candidates, zero unclassified material candidates, zero ambiguous mappings, and zero unclassified high-leverage candidates. The same-head Stage-9 robustness contract also passed.

The green scan is preserved but is not accepted as final 9.5-0 closure evidence because the required exclusion-log sanity review identified two source-specific classification gaps before closure.

## 2. Exclusion-review findings

### Stage-9 detector default mirror

`Stage9ControlPlaneConfig` contains executable defaults:

- `detector_family = "adwin"`
- `detector_signal = "hard_error"`

These mirror the already-frozen primary detector definition. They were excluded only because the generic material-name matcher did not treat `detector_family` / `detector_signal` as material identifiers.

### Symbolic lifecycle state-machine vocabulary

The lifecycle implementation contains categorical state/status/transition values such as `evidence_insufficient`, `demoted`, `retired`, `reactivated`, `refined`, and merge/consolidation states. These labels are not free hyperparameters, but the transition semantics are part of the symbolic treatment and therefore warrant explicit classification rather than remaining as unexplained high-leverage exclusions.

The already-registered first-failure, second-failure, evidence-insufficient, and overlap policies remain unchanged.

## 3. v1.10 correction

v1.10:

1. maps the Stage-9 shared-runner detector defaults to the existing `drift.primary_detector` control;
2. adds a source-specific material rule for those two detector identifiers;
3. registers the symbolic lifecycle state-machine policy as a causal-design constant and source-specifically discovers its state/status/transition assignments;
4. retains strict locator-plus-value matching and hash-bound scientific-source scope;
5. fixes the stale human-readable scan-report heading so the Markdown and machine-readable audit versions agree;
6. adds a regression test for both source-specific classifications.

No accepted Stage-8/9 scientific value, outcome, treatment, endpoint, seed, threshold, scenario, information set, or inference rule changes.

Final 9.5-0 closure still requires zero unclassified material candidates, zero ambiguous mappings, same-head Stage-9 regression success, and a clean targeted exclusion review.
