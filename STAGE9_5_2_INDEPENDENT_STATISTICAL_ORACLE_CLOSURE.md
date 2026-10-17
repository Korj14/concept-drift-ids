# Stage 9.5-2 Independent Statistical Oracle Closure

**Status:** CLOSED — STAGE 9.5-2 ONLY  
**Audited head:** `57648fd670bfe6117bbcdf06d1e1536599439c79`  
**Oracle workflow:** `38457351694`  
**Oracle job:** `115503380475`  
**Same-head Stage-9 regression:** `38457351772` — success

## 1. Closure decision

Stage 9.5-2 independent statistical oracle is closed.

This closure does **not** close Stage 9.5 as a whole. Stage 9.5-1 remains open/blocked on the unrecovered exact System-A checkpoint byte files, and Stage 10 remains prohibited.

## 2. Accepted oracle evidence

Accepted oracle iteration: **v1.1**.

- oracle tests: **9 passed, 0 failed**;
- independent comparisons: **8,285**;
- mismatches: **0**;
- production aggregation/reporting imports used: **false**;
- artifact: `stage9-5-statistical-oracle-v1-1`;
- artifact ID: `11844092522`;
- artifact ZIP SHA-256: `a8c9de0e66e8c3fe577df278ba3c9562c1667ab0c981e30c9f2a63fc41f7e967`;
- report canonical SHA-256: `b36f8f9b2cf2237762298d139139bd5160c0805054b1540c3c56e6acf915819d`.

The same-head Stage-9 robustness contract passed, and the closed Stage 9.5-0 assurance job remained green.

## 3. Stage-8 independent reconstruction

The oracle independently recomputed per-seed predictive metrics from primitive confusion counts and explanation metrics from primitive coverage fields, then reconstructed E1/E2/E3 and their inferential summaries.

E1 D-drift minus C post-drift MCC effects were independently recovered as:

`[0.048420827244952336, 0.06331523927252902, 0.07004419703990727, 0.06008466317941408, 0.0568933489745701]`

with:

- mean: `0.05975165514227456`;
- sample SD: `0.007989117909816433`;
- 95% t interval: `[0.04983185505625059, 0.06967145522829853]`;
- exact one-sided sign probability: `0.03125`;
- Holm-adjusted p: `0.09375`.

E2 and E3 were also independently reproduced:

- E2 mean `-0.06310305816233135`, raw sign p `0.96875`, Holm `1.0`;
- E3 mean `-0.012999429344654279`, raw sign p `0.8125`, Holm `1.0`.

These values match the accepted confirmatory evidence within the prospectively frozen oracle tolerances.

## 4. Stage-9 robustness reconstruction

The oracle independently covered all 11 accepted robustness conditions:

- `adwin_brier`;
- `lambda_0_7`;
- `lambda_0_9`;
- `lambda_1_0`;
- `latency_0`;
- `latency_10000`;
- `no_replay`;
- `page_hinkley_hard_error`;
- `static_symbolic_gate`;
- `window_10000`;
- `window_2500`.

For scored conditions, predictive metrics were recomputed from per-seed confusion counts and explanation metrics from explanation primitives.

For lambda conditions, predictive metrics were independently recomputed from offline per-seed confusion counts, while explanation endpoints were checked against the immutable Stage-8 per-seed evidence as prospectively specified.

For window-size conditions, recovery summaries and paired deltas were reconstructed from Stage-9 alternative per-seed recovery records plus the immutable Stage-8 5,000-row primary recovery records.

No new confirmatory p-value family was introduced.

## 5. Isolation negative control

The oracle independently confirmed the lambda-1 control produces exact zero D-drift/C, D-drift/D-periodic, and D-periodic/C contrasts for MCC, F1, and FPR across all five seeds.

This preserves the intended isolation interpretation: at neural weight 1.0, symbolic differences cannot change the predictive outputs.

## 6. Failure preservation

The first oracle execution remains preserved as a failed harness attempt. Its failure was a schema-adapter defect: Stage-8 accepted summaries store per-seed endpoint vectors under `effects`, whereas Stage-9 uses `values`.

The v1.1 correction changed only the assurance comparator and report fail-safety. It did not change statistical definitions, tolerances, endpoint families, conditions, or scientific evidence.

## 7. Scientific-change classification

No Stage-8 or Stage-9 scientific object, endpoint, estimate, seed, condition, inference rule, or accepted result was modified.

No Stage-10 outcomes were accessed.

## 8. Remaining gate state

- Stage 9.5-0: **closed**.
- Stage 9.5-1: **open / Class-A blocked** on missing exact System-A checkpoint bytes.
- Stage 9.5-2: **closed**.
- Stage 9.5 overall: **open / blocked**.
- Stage 10: **prohibited**.

Independent assurance packages that do not require the missing checkpoint bytes may continue, but no later package may reinterpret the 9.5-1 blocker as resolved.
