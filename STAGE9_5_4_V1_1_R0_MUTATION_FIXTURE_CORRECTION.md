# Stage 9.5-4 v1.1 R0 Mutation-Fixture Correction

**Status:** TEST-HARNESS CORRECTION AFTER FIRST 9.5-4 RUN  
**Failed head:** `1b7278429a8472b17d5670159e5af313efdf6745`  
**Workflow:** `38545333519`  
**Mutation job:** `115789845764`

## First-run result

The first targeted-mutation run executed all 11 frozen mutant families and killed 10/11.

The sole reported survivor was `M06_seed_r0_threshold_bypass`.

Within M06, the seed-bypass and threshold-bypass probes behaved as intended. The failure occurred before the R0 bypass mutant itself could be evaluated.

## Root cause

The R0 sub-probe created two migrated empty-rule states with the same seed and identical rule content, differing only in `neural_checkpoint_sha256`.

The production isolation verifier compares the canonical R0 starting-state identity. The checkpoint label is not part of that R0 canonical state identity, so the two fixtures were not actually different R0 starts. The unmutated production verifier therefore correctly accepted them.

This is a mutation-fixture construction defect, not a surviving scientific mutant.

## v1.1 correction

The R0 sub-probe now constructs two genuinely different starting rule states: one empty state and one state containing a deterministic toy R0 rule. It first proves that the unmutated production verifier rejects the divergent R0 identities, then applies the exact source mutation that bypasses the R0 identity comparison and proves the mutated verifier accepts them.

The frozen 11-family mutation contract, required 100% kill rate, production scientific source tree, and all accepted Stage-8/9 evidence remain unchanged.
