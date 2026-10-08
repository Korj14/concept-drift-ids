# Stage 7 R0.v2 Cross-Platform Hash Portability Correction

**Date:** 8 October 2026  
**Classification:** implementation-defect correction; no scientific-object change  
**Correction branch:** `stage7-r0-v2-portability-fix`  
**Parent:** accepted Stage-7 merge `a5fb8e5a00262ce59c3e4029821d0990bd9b933a`  
**Historical tag preserved:** `cd-implementation-ready-v1`

## Observed failure

The first local execution of:

`python run.py cd-preflight`

on Windows failed in `load_accepted_r0_v2_rules` with:

`ValueError: R0.v2 raw rule artifact hash mismatch.`

The failure occurred before any primary adaptive pre/post execution.

## Diagnosis

The accepted R0.v2 manifest stores SHA-256 values for the repository-canonical LF UTF-8 rule JSON
files.

All five rule artifacts on accepted `main` were independently rechecked:

| Seed | Manifest/repository LF SHA-256 | CRLF-materialized SHA-256 |
|---:|---|---|
| 0 | `d84aecb25c1645745bab08449e8b79f5c5485631847673a274ec9b3bcbef627f` | `b79b3fd841171a89f3801af7a26c41a622dca2148a8a5c88fc73348b159e3e10` |
| 1 | `bb59e5ef4e819df785dbb2af55a376f2a9ef62d87c78cdb9ea1d2d5502cc50e6` | `9f051242e2ba2d210b2e4e5af49e62525f55e8920d696171506eb2075934c8ae` |
| 2 | `ea04c858de1b7a74ab33c07dac34b3b3cf507d2b0239dc4e9d82cb81d7f88829` | `8e29439570db7389457e21f4a2ec71094a9d8c927df971710f7463faa9640c8b` |
| 3 | `ed11d3e769174cab4d09a7a8c1ad8dd031d729e3d4b8c6ddb984eb6284808899` | `eddbd2f6ce57b89015854f4880a92b955b45c26e8ab26fce2e87375461bcd166` |
| 4 | `b6fa780fb10a3b4802aa334e929e0480a863bce5ffc593e457dbf2516b3760db` | `276e81751ffad5f9c23fef823764a902f0d1ce200dc5646d26e5ac6cf02d843f` |

The repository's prior `.gitattributes` did not specify an EOL policy for these rule JSON files.
A Windows checkout using Git text conversion can therefore materialize semantically identical JSON
with CRLF line endings, causing the raw byte SHA-256 comparison to fail.

The accepted canonical JSON artifact hash had not changed. The R0 rules themselves had not changed.

## Correction

The loader now compares the manifest's accepted repository-canonical LF hash against a dedicated UTF-8 verifier that normalizes only CRLF/CR line endings to LF before hashing.

The independent canonical JSON artifact-hash verification remains unchanged and is still required.

Therefore the corrected verification requires both:

1. exact accepted UTF-8 textual content modulo platform EOL materialization; and
2. exact accepted canonical JSON semantic identity.

No rule, confidence, consequent, antecedent, lifecycle state, fusion setting, threshold, dataset,
statistical endpoint, or causal-treatment definition changed.

`.gitattributes` now also pins:

- `data/rules/system_b_r0_v2/*.json text eol=lf`
- `data/manifests/system_b_v2.json text eol=lf`

for deterministic future checkouts.

## Regression tests

Added tests prove that:

- an accepted R0.v2 rule artifact materialized with Windows CRLF is accepted;
- a content mutation is still rejected;
- the accepted manifest/canonical rule identities and counts remain unchanged.

## Tag/version policy

The existing annotated tag `cd-implementation-ready-v1` is immutable historical evidence and is
not moved or deleted.

Because its local preflight exposed this portability defect, it must not be used as the Stage-8
execution parent.

After this correction is merged, exact-head CI is green, and the local corrected preflight succeeds,
the corrected implementation-ready state must receive a new annotated tag:

`cd-implementation-ready-v1.1`

Stage 8 must branch from that corrected tag/commit, not from `cd-implementation-ready-v1`.

## Held-out status

Primary adaptive pre/post execution remains **LOCKED and untouched**.
