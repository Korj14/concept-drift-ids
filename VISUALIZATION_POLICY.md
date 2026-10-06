# Visualization and Reporting Policy

**Status:** prospective reporting rule; does not modify any frozen numerical result.

The project stores statistical results exactly as computed. Visualization code may change how those values are displayed, but must not overwrite, round-trip, clip, or otherwise alter the underlying frozen data.

## 1. Metric domains

- accuracy: [0, 1]
- balanced_accuracy: [0, 1]
- precision: [0, 1]
- recall: [0, 1]
- f1: [0, 1]
- fpr: [0, 1]
- roc_auc: [0, 1]
- average_precision: [0, 1]
- mcc: [-1, 1]

Paired deltas retain their mathematically valid difference ranges and are not clipped in stored data.

## 2. Confidence intervals and bounded metrics

The current aggregate CSVs store raw t-based confidence intervals across seeds. With small n, these intervals can extend beyond the natural domain of bounded metrics. This is a property of the interval construction, not a data corruption.

Rules:

1. Never alter the stored CI endpoints.
2. Prefer paired seed-point/slope plots for n=5 comparisons.
3. For mean-with-CI plots of bounded metrics, either:
   - draw the raw CI and use the natural metric axis, allowing the whisker to meet the plot boundary; or
   - clip only the graphical whisker to the metric domain and state in the caption that the stored statistical interval is unchanged.
4. Never report a clipped graphical endpoint as though it were the statistical CI.
5. For paired effects, prefer the post-minus-pre delta and its interval because the delta scale directly answers the comparison question.

## 3. Plot-ready data contract

Every core system should emit, where applicable:

- long-form per-seed metrics;
- aggregate mean, sample SD, and interval;
- paired deltas by matched seed;
- aggregate paired deltas;
- training/adaptation history by step/window;
- system/scenario/version identifiers;
- frozen decision threshold or other operating-point identifier;
- later: drift-event, rule-version, explanation-quality, and computational-cost identifiers.

Equivalent schemas across Systems A/B/C/D should be concatenable without reverse engineering.

For frozen System A, exact TP/TN/FP/FN, sample count, and prevalence are preserved in the separately versioned `results/frozen/system_a_v1_supplement_v1/` evidence supplement. Future systems should emit those audit/count fields prospectively rather than requiring reconstruction.

## 4. Preferred figure types

- paired pre/post seed slope plots;
- forest plots of paired effect sizes;
- longitudinal window curves with the detected drift event marked;
- rule/explanation-quality trajectories;
- rule-churn/version-event timelines;
- grouped system comparisons with seed points visible;
- recovery-per-update and cost-versus-recovery plots for trigger ablations.

Avoid relying on accuracy-only figures for imbalanced intrusion detection.

## 5. Integrity rule

Figures are derivatives of frozen CSV/JSON artifacts. A figure may be regenerated, reformatted, or restyled without changing the experimental result. Any transformation that changes the numeric analytical result requires a new explicitly versioned analysis artifact.
