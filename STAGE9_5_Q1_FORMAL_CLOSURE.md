# Stage 9.5 Q1 Independent Assurance — formal closure record

**Status:** FORMAL CLOSURE CANDIDATE — becomes the project's governing Stage-9.5 closure declaration only when reviewed, committed and accepted on the intended assurance branch. This draft file is not itself a release.  
**Evidence-assessed assurance head:** `c20c15bcfdbb0177c2495c869012d5fd0f33b41a`.  
**Controlling protocol:** `STAGE9_5_Q1_INDEPENDENT_ASSURANCE_PROTOCOL.md`; original freeze commit `cf9bb49cc18c751872a12d3530df8ff78d26d67a`, restored frozen blob `01b4cf8e47afa4ca8ffec3b9c203db72f86283ab` (restoration commit `45021be79bd5a18e5df778820a2d85cef2d0058b`).  
**Order/provenance authority:** `STAGE9_5_WORK_PACKAGE_ORDER_CONFORMANCE_CORRECTION.md`, including its explicit externally verified recovery rule.  
**Mandatory reviewer-facing retrospective:** `STAGE9_5_ASSURANCE_DIVERSION_RETROSPECTIVE.md`.  
**Stage-10 treatment outcomes accessed:** no.

## Closure criterion and evidence-derived resolution

The accepted Stage-9.5-1/6 original-byte recovery and deterministic replay remain at their frozen historical evidence identities. The independently validated order gate passed with `later_packages_unlocked=true` on the exact assessed head. Historical negative recovery, original Phase-C v1 seed-0 failure and out-of-order 7/8/9 attempts are preserved, not erased or retroactively accepted.

- Stage-9.5-1: original System-A checkpoint identities **5/5**, accepted Stage-8 archive **145/145**, zero actual local-verifier failures/blockers. Canonical recovery SHA-256 `35cbefc053ae910b0eb20ace3443b70ea4972a511b6549f430f3d2ced0980c7d`.
- Stage-9.5-6: original Stage-1 and frozen historical replay verified, Phase-A/B seeds 0–4, original Phase-C v1 seed-0 failure preserved, corrected Phase-C seed-0 verified, **0 mismatches**, canonical replay SHA-256 `f169ae5fd9dc246ad8e2abe7b321b5d2ad67cb1f2c7ec6a1d3bcb73d4ec58052`. Same historical audited-head Stage-9 robustness run [39415218195](https://github.com/Korj14/concept-drift-ids/actions/runs/39415218195) **SUCCESS**.
- Stage-9.5-7: exact-head [PR run 41080352744](https://github.com/Korj14/concept-drift-ids/actions/runs/41080352744) and [push run 41080344081](https://github.com/Korj14/concept-drift-ids/actions/runs/41080344081) **SUCCESS** after the binding predecessor gate. Machine claim ledger: **23 claims / 20 families**, canonical SHA-256 `04ef9b09c42469750b7f6db773ab182d964e0063828263d03be52b5a47f7943f`.
- Stage-9.5-8: exact-head successor independent reporting **SUCCESS**, **210 oracle comparisons**, no mismatches or missing outputs, no production reporting imports; canonical SHA-256 `0868171892cf67fbf2a8ae19ed79b9a6da0d49aa485aa670bf82d279ad557b8f`.
- Stage-9.5-9: exact-head final hostile-review audit **SUCCESS** on both runs; canonical SHA-256 `c31a0f05f58079bf4fb4f2b5fc7b25548863775a1f01b40cc0bb0f98ecfa0ba4`. Audit execution PASS, **0 current unresolved Class A**, 1 preserved historical Class-A record, all **6 Class B** and **14 Class C** reviewer attacks dispositioned, **25** preserved historical failed-audit JSON records, source identities verified, no Stage-10 outcome access. Its report states `stage9_5_closure_eligible=true`, but *also* `formal_stage9_5_closure_established=false` until this independent documentation/governance act.

Stages 9.5-0/2/3/4 also passed on the same assessed assurance head. The accepted Stage-9.5-5 v1.4 static triage previously dispositioned all **210** original findings. At the assessed head its red discovery job showed 154 Ruff / 55 mypy, comprising **the exact original 134 scientific Ruff and 55 scientific mypy findings**, with one formerly triaged assurance-only `I001` warning removed. The separately required supplemental v1.9 assurance-code check was **SUCCESS**, Ruff 0, mypy 0 ([41080344141](https://github.com/Korj14/concept-drift-ids/actions/runs/41080344141)), report SHA-256 `50c0107d5cdacd0dcc6d0a842421ea662fa84a842574b2b381091a591bc65775`. There is no newly discovered untriaged scientific/static finding.

## Explicit negative-CI disposition (not greenwashed)

The overall Stage-9.5 CI workflow **FAILURE** is preserved. It contains two known independently classified failures:

1. The v1.4 static-discovery runner deliberately exits nonzero for the already-triaged legacy findings. The exact current and accepted archived reports were compared record for record; all scientific findings match, and the new supplemental static scope is green. Do not mark this old CI job as SUCCESS or substitute zero counts.
2. The unprovisioned hosted fresh-clone reconstruction job reports **0 identity failures / 2 missing-external-artifact blockers** on its particular GitHub runner. This is a factual failure *of that environment*. The binding order correction's **External-artifact execution provenance boundary** expressly permits recovery/replay outside GitHub Actions and establishes canonical reports as the closure authority while the originals remain external. The local original-byte success was machine verified and bound in the frozen order gate; it is not a manual assertion. No post-hoc condition requiring heavy-file upload to every GitHub runner is introduced. Do not claim that every fresh checkout independently contains/retrieves the external artifacts without provisioning.

A separate secure-hosted transport probe may remain pending/failed; it is *supplemental* unless its own prospectively frozen requirements are independently activated as a new governing obligation. Its mere existence, handshake or waiting status is not a substitute for source-byte recovery nor a mandatory retroactive closure condition.

## Formal closure decision boundary

All binding scientific/provenance assurances and the original 9.5-0 through 9.5-9 work-package obligations have evidence-backed positive dispositions, with **zero currently unresolved Class A** and explicit Class-B/C treatment, under the original frozen protocol and its prior order/external-provenance correction. The candidate **supports a Stage-9.5 formal closure decision**, subject to this exact retrospective and closure record being preserved and accepted in the correct branch. It does **not** reclassify past red jobs as successful, rewrite prior artifacts, change the frozen Q1 register or change any accepted scientific estimate.

**Scope limitations:** This is a Q1 independent integrity gate on the already frozen Stage-8/9 scientific object. It is not proof of external-dataset generalization, natural drift causality, universal detector superiority, production real-time security or complete offline availability of 5 original checkpoints/145 heavy files in all environments. The final manuscript must still pass the pending **zero-orphan-number** audit.

**Stage-10 release:** This closure candidate does not itself execute, preauthorize or inspect Stage-10 treatment outcomes. The Stage-10+ master replication/sensitivity protocol has been prospectively frozen with its required obligations. Any downstream treatment launch requires acceptance of this formal Stage-9.5 closure on the governing branch **and a separate explicit Stage-10 execution-release decision** with the applicable frozen scenario/protocol constraints. No new Stage-10 numerical outcomes may be obtained by treating the present draft as already published.

## Preservation and terminal guard

Only the two new closure-supporting Markdown files are contemplated for this publication, with exact source-head/branch and remote SHA guards. No scientific file, frozen contract, source code, existing canonical report, historical failure or Stage-10 protocol is within the allowed modification set. If the exact-head evidence or governed external-provenance rule is contradicted, **STOP and reopen only that named evidence conflict**; do not rerun Stage-9.5-1/6 or automatically generate further assurance corrections.
