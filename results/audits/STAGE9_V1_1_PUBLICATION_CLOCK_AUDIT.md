# Stage 9 v1.1 Publication-Clock Audit

**Status:** POST-EXPORT DESCRIPTIVE AUDIT — NOT PART OF THE PRESPECIFIED ROBUSTNESS FAMILY  
**Source evidence commit:** `9a05602b68cfaee7c45d2002a760b65115a581fd`  
**Controlled boundary:** row `69260`  
**Output:** `results/audits/stage9_v1_1_publication_clock_audit.json`

## Purpose

This audit preserves the publication-clock diagnostic used during the post-execution interpretation
of Stage 9 v1.1. It changes no treatment, comparator, endpoint, threshold, seed, trigger policy,
statistical family, or frozen compact evidence.

It is descriptive only. It creates no p-value, confirmatory test, or additional inferential unit.

## Deterministic derivation

For each scored Stage-9 condition:

- `latency_0`;
- `latency_10000`;
- `page_hinkley_hard_error`;
- `adwin_brier`;
- `no_replay`;
- `static_symbolic_gate`;

and for each seed `0..4` and each treatment arm `d_drift` / `d_periodic`:

1. read the frozen arm manifest at
   `results/frozen/cd_robustness_v1_1/provenance/<condition>/seed-<seed>/phase_b/<arm>/arm_manifest.json`;
2. take `publications[*].effective_index` in stored order;
3. classify a publication as pre-reference when `effective_index < 69260`;
4. classify it as post-reference when `effective_index >= 69260`;
5. compute `relative_to_boundary = effective_index - 69260`.

The audit JSON contains exactly 60 records: 6 conditions × 5 seeds × 2 treatment arms.

Because every input arm manifest is already hash-bound by the accepted compact export manifest,
this audit is reproducible from the frozen Stage-9 evidence without rerunning any adaptive model or
symbolic lifecycle.

## Interpretation boundary

The audit may be used to describe when already-accepted symbolic publications occurred. It must not
be used to redefine the controlled boundary, select favorable conditions, alter the Stage-9
robustness family, or rescue an unfavorable primary/robustness result.
