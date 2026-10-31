# Stage-10A — production provenance schema review candidate v0.1

**Role:** WARM, explicitly **NON-GOVERNING**, non-executable review material. **Status: PENDING EXPLICIT DESIGN REVIEW; NO production freeze; NO Stage-10A RELEASE.** The frozen master v1.1 and GoldenEye Stage-10A protocol remain above this candidate. Only `STAGE10A_CURRENT_STATE_AND_RESUME.md` controls changing Stage-10A status.

## Scope and hard limit

`data/manifests/stage10a_production_schema_review_candidate_v0_1.json` is a **proposal**, not a production run manifest, accepted attestation, or experimental input. The independent repository-only verifier `tools/stage10/stage10a_production_schema_review.py` binds that proposal to exact original master/Stage-10A/primary-config Git blobs and the two immutable accepted original-source and checkpoint source-only receipt bytes. It independently derives the only acceptable candidate values and rejects any extra/changed fields, unapproved design decision, substituted original provenance, or asserted RELEASE. There is no real data/model/optimizer input or production executor in this package.

**Preserved:** one common Stage-8-compatible Phase-A neural/control writer for each of seeds 0–4; the six inherited Phase-A JSONL streams; full five-seed seal before three strictly read-only Phase-B symbolic arms; independent offline Phase C only after sealing and separate authority; 138,530 retained GoldenEye rows, 77 inherited features, 5,000-row label maturity, logical split 69,260 visible to evaluator only. Under the frozen no-tail-release schedule, the corresponding expected values are 133,530 within-stream matured labels and 5,000 censored labels per seed. These are **derived design quantities**, not observed production counts.

## Four decisions still open (none silently approved)

| Decision | Review direction | Proof required before acceptance |
|---|---|---|
| Runtime identity | Exact clean Git HEAD, Python 3.11.9, frozen lock and thread environment, paired with independently observable runner/job evidence | A self-reported SHA or standalone JSON signature is not trusted runtime attestation; specify protected job identity, source/executor isolation, and external custody chain |
| Label access | Separate-process matured-label escrow, or demonstrably equivalent enforced isolation, integrated without changing frozen neural semantics | External append/fsync witness, current-clock prediction committed before a label grant, and no future-label access by monitor/replay/symbolic consumers; historical Stage-8 in-memory batching and the new same-process fixture are insufficient |
| Checkpoint and Phase-B custody | Protected original and child checkpoint bytes, read-only model resolver and Phase-A artifacts for all arms | Independently validated parent/child, state and byte hashes, optimizer/RNG/replay provenance and enforced read-only boundaries; do not expose checkpoint binaries or signed links publicly |
| S10-04 scope | Preserve frozen independent-environment eligibility criteria and the master program obligation, without inventing a selected dataset | Decide which independently frozen program-wide steps are prerequisites to Stage-10A RELEASE versus later external-generalization claims; criteria-only freeze is **not** environmental replication |

## Negative and acceptance boundaries

The verifier rejects incorrect arm/seed sets, changed chronology or boundary firewall, label latency, missing Phase-A journals, removed all-seed sealing requirement, weakened inherited neural-hard-error monitor rule, forged claim that an unresolved decision is approved, all affirmative execution flags, and accepted-source/checkpoint receipt substitution. The new tests use synthetic dictionaries and immutable repository bytes only. The repository check does **not** authenticate a real append sequence, file-system access control, GitHub runner trust, checkpoint chain or scientific treatment.

**Before any future promotion:** select and review the four trust/custody/scope decisions, test their actual enforceability with separate non-treatment evidence, freeze one versioned operational schema with independent hostile review, and obtain a separately signed Stage-10A RELEASE. A synthetic candidate CI pass never authorizes real checkpoint loading, model inference, adaptive update, C/D/D-periodic treatment, or outcome scoring.

This document supplements, rather than duplicates as authority, the accepted Stage-8-layout, trace-envelope and append/escrow synthetic WARM reviews. Do not alter Stage-8/9 evidence or either original source-only receipt.
