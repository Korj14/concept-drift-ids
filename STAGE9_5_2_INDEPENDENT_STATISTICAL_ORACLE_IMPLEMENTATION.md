# Stage 9.5-2 Independent Statistical Oracle — Implementation Freeze

**Status:** PROSPECTIVELY FROZEN BEFORE ORACLE EXECUTION  
**Package:** 9.5-2  
**Stage 9.5-1 status:** OPEN/BLOCKED on unrecovered System-A checkpoint bytes  
**Stage 10:** PROHIBITED

## Independence rule

The oracle implementation must not import production aggregation/reporting modules. It may read immutable JSON evidence directly and use standard mathematical/statistical libraries, but all endpoint extraction, primitive metric recomputation, paired contrasts, summary statistics, sign probabilities, and Holm adjustment must be implemented inside `tools/stage9_5/`.

## Stage-8 primary reconstruction

For each seed 0–4 and arm C / D-drift / D-periodic, the oracle reads the accepted Phase-C evaluation JSON.

At primary neural weight `0.5` and partition `post`:

- F1 is recomputed from `tp/fp/fn`;
- FPR is recomputed from `fp/tn`;
- MCC is recomputed from `tn/fp/fn/tp`;
- MCSC is recomputed as the mean of benign and attack correct-symbolic coverage;
- resolved coverage is recomputed as `1 - uncovered_rate - conflict_abstain_rate`.

The oracle then reconstructs the frozen E1/E2/E3 per-seed effects and independently computes mean, median, sample SD, extrema, sign counts, leave-one-seed-out mean range, 95% Student-t interval (df=4), exact one-sided sign probability, and the frozen three-test Holm adjustment.

The accepted `confirmatory_analysis.json` is comparison authority only; it is not the source of the recomputed effects.

## Stage-9 robustness reconstruction

The oracle covers all 11 accepted Stage-9 conditions.

For scored conditions, predictive and explanation endpoints are recomputed from each condition/seed/arm evaluation file.

For offline lambda conditions, predictive metrics are recomputed from the per-seed offline result confusion counts. Explanation endpoints were not newly recomputed by those offline artifacts; the oracle therefore verifies that the accepted aggregate inherits the corresponding immutable Stage-8 explanation values rather than fabricating an unavailable primitive source.

Window-size conditions do not change whole-post endpoints. The oracle verifies this frozen invariance and treats window/recovery summaries separately where primitive evidence permits.

Stage-9 summaries remain descriptive robustness summaries. **No new confirmatory p-value family is created.**

## Comparison rules

- counts, seeds, labels, file/hash identities: exact;
- exact JSON-derived recomputations: absolute tolerance `1e-12`;
- floating metrics recomputed from primitive numerical fields: absolute tolerance `1e-10`;
- rounded manuscript displays are never authority.

Any larger discrepancy blocks 9.5-2 until explained and preserved.

## Isolation from the 9.5-1 blocker

The 9.5-2 oracle operates only on committed immutable evidence and does not require the unavailable System-A checkpoint bytes. Completing 9.5-2 cannot resolve or downgrade the open Class-A 9.5-1 provenance blocker.
