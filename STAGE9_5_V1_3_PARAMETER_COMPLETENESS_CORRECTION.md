# Stage 9.5 v1.3 Parameter-Completeness Closure Correction

**Status:** VERSIONED REGISTRY/PARSER CORRECTION AFTER PRESERVED v1.2 BLOCK  
**Governing protocol:** `STAGE9_5_Q1_INDEPENDENT_ASSURANCE_PROTOCOL.md`  
**Preserved v1.2 result:** `results/audits/stage9_5_v1_2/parameter_scan_failure.json`

## 1. v1.2 result

The v1.2 scanner was technically valid: all five scanner tests passed and the same-head Stage-9 robustness/regression workflow passed. The completeness scan blocked with 8 unclassified high-leverage occurrences and 17 total unclassified material occurrences.

Inspection found no newly hidden treatment or outcome-selected setting. The residuals were:
- duplicate declarations of already-registered primary lambda, lambda=1 and 5,000-row reporting-window controls in Stage-9/Stage-9.5 text;
- one structural-token parser artifact from the phrase `Stage-8/9`;
- missing registry mappings for the confirmatory unit, adaptation LR/weight-decay mirror, same-class redundancy mirror;
- an inference-only Phase-C scoring batch size;
- detector epoch IDs used as state-machine identifiers;
- the Stage-9.5 reference to quantifying the 100-bootstrap gate granularity.

## 2. v1.3 changes

v1.3 makes only completeness/audit changes:

1. supporting protocol source locations are added to the already-frozen primary lambda, lambda=1, reporting-window and gate families;
2. `Stage-8/9` and analogous structural stage references are removed before Markdown numeric discovery;
3. the confirmatory-unit string is registered as part of the frozen statistical estimand;
4. primary-control-plane learning rate and weight decay are mapped to the already-registered adaptation optimizer family;
5. the primary-config same-class redundancy mirror is mapped to the lifecycle overlap-threshold family;
6. Phase-C `batch_size=4096` used only for deterministic offline probability scoring is explicitly classified as an inference-engineering/reproducibility constant, not a model-training hyperparameter;
7. detector `epoch_id=0/1` values are explicitly classified as state-machine identifiers, not drift-detector hyperparameters;
8. the Stage-9.5 `100-bootstrap` statement is linked to the already-registered primary gate/bootstrap family.

No accepted Stage-8/9 scientific value changes.

## 3. Closure standard

The v1.3 scan must have:
- zero unclassified high-leverage candidates; and
- zero unclassified material candidates.

This is stricter than the minimum “unknown high-leverage blocks closure” rule and is adopted prospectively before the v1.3 scan executes.

Any later residual must be preserved and dispositioned; no allow-list may be introduced merely to force a pass.
