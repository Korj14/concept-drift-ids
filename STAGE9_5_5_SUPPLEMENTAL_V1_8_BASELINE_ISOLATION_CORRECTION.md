# Stage 9.5-5 Supplemental Static Assurance v1.8 — Baseline Isolation Correction

**Status:** PROSPECTIVELY FROZEN BEFORE EXECUTION  
**Accepted core baseline:** Stage 9.5-5 v1.4  
**Failed supplemental predecessor:** v1.7

v1.7 did not produce valid supplemental static evidence. Its compile guard found a malformed literal backslash-n sequence in the typed `series` dictionary of `tools/stage9_5/independent_reporting.py`. No static artifact was produced.

v1.7 also repointed the shared static-assurance runner to the delta contract. That wiring was methodologically undesirable because the accepted v1.4 closure must remain the authority for the untouched baseline.

v1.8 therefore makes two assurance-only corrections:

1. repair the malformed reporting dictionary block without changing any selector, formula, tolerance, or output definition;
2. restore `stage9_5_static_assurance_v1_4.json` as the default core static contract and add an explicit `--contract` option for the supplemental delta run.

The supplemental v1.8 scope is exactly the post-v1.4 assurance-code delta:

- `tools/stage9_5/claim_traceability.py`;
- `tools/stage9_5/independent_reporting.py`;
- `tools/stage9_5/static_assurance.py`;
- `tests/stage9_5/test_claim_traceability.py`;
- `tests/stage9_5/test_independent_reporting.py`;
- `tests/stage9_5/test_supplemental_static_assurance.py`.

Ruff must report **0 findings** on all six files. mypy must report **0 findings** on the three executable tools using `--explicit-package-bases`.

No scientific `src/concept_drift_ids/**` file, accepted Stage-8/9 evidence, reporting selector, or historical runtime lock is modified.
