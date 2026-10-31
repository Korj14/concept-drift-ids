# Stage-10A — independent trace envelope candidate and audit (synthetic only)

**31 October 2026 (Asia/Riyadh).**  
**Role:** WARM prospective engineering evidence/schema candidate; not a scientific protocol amendment, RELEASE authorization, second active state authority, or acceptance of a real neural trajectory. Current stage status remains solely in `STAGE10A_CURRENT_STATE_AND_RESUME.md`. Frozen Stage-10+ master and GoldenEye Stage-10A manifest govern.

## Provenance model and limitations

The accepted Stage-8 pattern is one common Phase-A control/neural writer per seed, immutable after sealing, with C, D-drift and D-periodic as read-only Phase-B symbolic consumers. Its hard-error monitor is driven by the neural probability, not the arm's fused symbolic probability. This isolates the intended symbolic-lifecycle intervention under the frozen conditional-on-shared-neural-trajectory estimand. If implementation introduces any arm-specific feedback into neural monitoring, label admission, replay, RNG, updates, or checkpoint publication, **STOP**: a new prospectively reviewed scientific decision would be required.

`tools/stage10/stage10a_independent_trace_envelope.py` implements a **different, read-only verifier** from the synthetic fixture generator. It imports neither the generator nor any neural or treatment module. A synthetic envelope binds:

- the exact byte hashes of all six per-seed fixture artifacts, including the shared event journal and all three arm bindings;
- source and original-checkpoint acceptance receipt identities, frozen original source SHA-256 and ordered-row SHA-256, training-fitted preprocessing core, original System-A checkpoint seed hash and accepted R0.v2 manifest identity;
- exactly one shared writer, frozen seed 0–4, frozen C/D-drift/D-periodic arm names, 5,000-row label delay, and a bounded 5,001–5,003-row synthetic fixture;
- explicit negative production claims, including `git_head_independently_authenticated=false`, `neural_control_raw_state_independently_verified=false`, `stage10a_treatment_execution_authorized=false`, and `stage10a_release_ready=false`.

The verifier pins accepted source/checkpoint receipt bytes and frozen master/Stage-10A Git blobs before reading the fixture. It re-derives each synthetic neural token and each legal label-release event independently from raw JSONL bytes, verifies canonical JSON, sealed writer identities and all arm bindings, and rejects extra files, missing seeds, source/seed swaps, changed checkpoint or symbolic hashes, premature/future labels, prohibited boundary/label leakage, changed release claims, second writers, and falsified envelope SHA-256s. This does **not** authenticate actual Git runtime identity, control-plane RNG/optimizer/replay states, checkpoint model deserialization or treatment fidelity.

## Prospective real schema — UNRESOLVED, not implemented

Before allowing real Phase-A/Phase-B execution, review a separate versioned *production* evidence schema. The current tool deliberately accepts only synthetic fixtures and **rejects the real 138,530-row count**. Production schema requirements to decide and freeze prospectively:

1. **Writer trust:** exact-head clean tracked checkout; pinned Python 3.11.9, dependency lock and runtime thread controls; accepted initial checkpoint bytes, preprocessing/R0 hashes, monitor thresholds, raw stream feature/row identities and label-gate provenance, all independently witnessed.
2. **Sealed raw event family:** separate write-once files for 138,530 prediction commits, 5,000-row matured-label admissions, detector observations/events, replay/reservoir transactions, optimizer RNG/shuffle budgets, parent/child neural checkpoint chain and publication-effective clocks. The evaluator-only boundary 69,260 must not reach any writer/arm adaptation input.
3. **Causal firewall:** one Phase-A writer per seed, complete trace and checkpoint chain sealed before any Phase-B symbolic maintenance; arms have read-only file access; all C/D/D-periodic consumers linked by raw, independently recomputed artifact digests and verified provenance. Any neural/control divergence is Class A, not an excluded unfavorable result.
4. **Failure semantics:** durable `attempt` before any work, exclusive outputs without overwrite, failure/incomplete receipts retained. No partial completion may be interpreted as success; five attempted seed identities fixed without outcome-driven substitutions.
5. **Offline evaluator:** independent reader of sealed artifacts only; frozen post-only E1/E2/E3 and paired-seed (n=5) analysis with sign/t/Holm, no window/prediction/event pseudoreplication and no post-outcome retuning.
6. **Review boundary:** the second-environment S10-04 experiment and separate Stage-10A RELEASE remain unfulfilled. This document neither selects a second dataset nor authorizes outcome access.

A future reviewer must resolve production provenance witnesses, the checkpoint-chain artifact access model, and trustworthy separation of writer and evaluator **before** promoting any schema candidate. Keeping this review WARM prevents it from competing with the single HOT current-state authority.

**Decision:** synthetic envelope audit only; Stage-10A treatment execution **HOLD**.
