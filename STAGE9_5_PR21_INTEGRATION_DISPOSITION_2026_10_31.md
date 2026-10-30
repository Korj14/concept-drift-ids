# PR #21 — Stage-9.5 accepted assurance integration disposition

**Record date:** 31 October 2026  
**Role:** Administrative, case-specific integration decision; subordinate to accepted Stage-9.5 technical evidence and frozen Stage-10 master v1.1.  
**Branch:** `stage9-5-q1-assurance` → intended `main`.  
**Original accepted technical head:** `cdc4b5eaea7e337802f93563b708b89f3025c3d8` (30 October 2026).  
**Prior documentary reconciliation:** `35f6f05dc354d8da6cfcae55261d2217d94ceb9b` (31 October 2026).  
**Scope:** Recorded exception to repository-wide green-CI *merge condition only*, for this accepted and independently dispositioned terminal assurance PR. Not a change to the underlying tests, their outcomes, or any future merge policy.  
**Stage-10 execution:** HOLD.

## Pre-merge scientific and ancestry findings

- `main` before this integration: `f3355680981e400c393443d338b70793e363ec55`; this is the historical Stage-8/9 merge commit with exactly the same tree `67eff46426ff74976fed68971968e62732e90824` as `4dca828acb3916feb3f30d61f1b587240a6eba19`.
- The assurance history descends from the Stage-8/9 baseline; `main` has a separate one-commit merge topology. Merge by **merge commit**, not squash, rebase, amend, or force-update, so both accepted histories remain ancestors.
- The reviewed comparison identified **zero `results/frozen/` changes** and no deletion of prior scientific evidence. The existing changed files are governance/navigation documentation and `.gitattributes`; new Stage-10A/B/C materials are pre-outcome source-only protocols and tests, not outcomes or release.
- Two tracked `data/transport/stage9_5_dropbox_secure_*.b64` files were boundedly inspected: encoded DER ASN.1/PKCS-style transport data, not plaintext original model checkpoints, raw heavy archive, or obvious plaintext secrets. This limited classification is **not** independent cryptographic verification. No secret-bearing new material is intentionally introduced by this documentation decision.
- The terminal technical acceptance and its exact SHA are recorded separately in `STAGE9_5_TERMINAL_ACCEPTANCE_ADMINISTRATIVE_RECONCILIATION_2026_10_31.md`. Earlier October blocked states are retained and not current.

## Explicit exceptional CI disposition

`REPOSITORY_GOVERNANCE.md` normally expects green current CI before merge. On this one PR, the accepted 30 October Stage-9.5 terminal technical decision exists despite **overall FAILURE** on both exact-head Stage-9.5 workflows because: (1) legacy static-discovery reports known, dispositioned findings; and (2) the hosted fresh-clone runner lacks the original external artifacts, while the governing external-provenance boundary allows independently machine-verified local recovery/replay.

Final required ordered CI passed at `cdc4b5e...`: predecessor/order gate → Stage-9.5-7 claim traceability → 9.5-8 independent reporting → 9.5-9 hostile review under the already-frozen Stage-10 master v1.1. Supplemental static CI passed in its own scope. Secure transport/recovery PR probe failures are preserved and not retroactively declared successful or new gating obligations.

**This is a recorded exception for this technically accepted terminal-assurance integration, not a claim that overall CI is green, an alteration of CI history, or a precedent excusing Stage-10A future execution checks.** The user explicitly instructed proceeding with the previously described integration process, with no Stage-10A treatment access. No unperformed independent GitHub review is claimed.

## Remaining repository protection and post-merge requirements

- GitHub `main` currently reports **no enforced branch protection, no required checks and no rulesets**. This administrative weakness is disclosed, not silently represented as enabled. After merge a repository administrator should enable PR review, prevent force-push and deletion, and select *appropriate prospectively valid* required checks. Historical intentionally red checks must not be falsified to satisfy protections.
- The merge must be verified by comparing `main`'s resulting tree to the reviewed assurance tree and confirming that the accepted technical SHA remains an ancestor. A short *post-merge* administrative closing record may cite the actual merge SHA; this pre-merge note must never invent that SHA.
- Keep PR #21, failed experiments, failed CI results, superseded protocols and audit evidence auditable; archive old status from active retrieval, not delete it.
- Stage-10A governance must use a new branch based on the integrated accepted `main`. **No Stage-10A treatment execution until a separately versioned, explicitly authorized RELEASE and satisfied Stage-10A source/implementation/exact-head freeze gates.**
