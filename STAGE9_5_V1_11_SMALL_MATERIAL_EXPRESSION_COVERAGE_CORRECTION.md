# Stage 9.5 v1.11 Small Material-Expression Coverage Correction

**Status:** VERSIONED PRE-CLOSURE COMPLETENESS CORRECTION AFTER GREEN v1.10.1 SCAN  
**Governing protocol:** `STAGE9_5_Q1_INDEPENDENT_ASSURANCE_PROTOCOL.md`  
**v1.10.1 exact head:** `328b062d47200f7f55d49af08a5289603f1111e0`  
**v1.10.1 scan canonical SHA-256:** `35cd6e1206b47c638814e0aa9bc2c0f7d0a10b22a2af266d99317ec88d367a02`  
**v1.10.1 register SHA-256:** `741752e9701dd0a508426c95a0231b78db224bfd7080833fbc41f5715f161881`  
**v1.10.1 CI artifact ZIP SHA-256:** `1020548a53cfce551aa2f31a665f7ccc34808d6c9b022a024c1a1f2bb45bde52`

## 1. v1.10.1 result

v1.10.1 passed its 20 scanner tests and the real hash-bound completeness scan:

- 88 registered entries;
- 498 material candidates;
- 1,451 retained exclusions;
- 0 unclassified material candidates;
- 0 ambiguous material mappings;
- 0 unclassified high-leverage candidates.

The same-head Stage-9 robustness contract passed.

The green scan is preserved but is not accepted as final 9.5-0 closure evidence because the mandatory exclusion-log sanity review found small-valued executable scientific controls still being excluded by the generic small-literal heuristic.

## 2. Exclusion-review findings

Confirmed examples include:

- Stage-9 robustness treatment: `"label_latency": 0` in `cd_stage9_config.py`;
- lifecycle overlap defaults: `same_class_redundancy=0.95`, `refinement_overlap=0.50`, `cross_class_overlap=0.50`;
- lifecycle failure persistence increments: `failure_streak + 1` / `max(1, failure_streak)`.

These controls are already represented in the scientific register. The defect is discovery/classification precedence for small expression literals, not missing prespecification or a scientific value change.

The executable `replay_enabled=True/False` mirrors inside the Stage-9 condition-construction dictionary are also material causal-design values and are now scanned explicitly by dictionary key.

## 3. v1.11 correction

v1.11:

1. keeps the generic small-literal exclusion as the default;
2. allows small expression literals through when their source expression explicitly names a material scientific family such as latency, overlap/redundancy/refinement/conflict, or lifecycle failure/streak semantics;
3. scans boolean dictionary values under the material key `replay_enabled`;
4. maps Stage-9 source-level `replay_enabled=True` to the matched primary replay control and `False` to the prespecified no-replay sensitivity;
5. broadens the existing Stage-9 latency locator only enough to map source-level `label_latency: 0` and `10000`;
6. adds regression tests for latency-zero, overlap defaults, failure-streak increments, and replay booleans.

No Stage-8/9 scientific value, treatment, endpoint, seed, threshold, scenario, information set, or inference rule changes.

Final 9.5-0 closure still requires a clean v1.11 scan, same-head Stage-9 regression success, and one last focused exclusion review.
