# Stage-10A — cross-process synthetic label-escrow handshake candidate

**Role:** WARM bounded engineering evidence, **not** scientific protocol, changing-state authority, production attestation, operational schema freeze, or RELEASE. **Status:** SYNTHETIC-ONLY DESIGN CHECK / Stage-10A treatment **HOLD**. The sole HOT changing state remains `STAGE10A_CURRENT_STATE_AND_RESUME.md`; frozen Stage-10+ master v1.1 and GoldenEye protocol outrank this document.

## Why this checkpoint exists

The prior same-process synthetic append/escrow check passed but explicitly did **not** exercise a separate process boundary. The production schema review candidate v0.1 kept exact-head runtime witness, enforceable label access, original/child checkpoint custody, and S10-04 release scope **pending**. This is a narrower engineering response to the label-handshake portion only; it does not select or freeze the production trust model.

## Executed synthetic contract

- `tools/stage10/stage10a_process_escrow_synthetic.py` starts a **distinct OS subprocess** for a synthetic escrow worker. A parent fixture writer appends a deterministic fake-neural prediction to `predictions.jsonl`, calls `flush` and `os.fsync`, then sends only `(seed, clock)` over a private subprocess pipe. The worker independently reads the actual next append record, checks exact seed/clock/chain and returns an acknowledgement, with a matured synthetic label only when `clock >= 5,000`. The worker separately appends and fsyncs `escrow_receipts.jsonl` before its response. No arbitrary future-label query is implemented. The writer retains only the label returned for a matured origin.
- Exactly five synthetic seed IDs (0–4); exactly **5,001 or 5,002** synthetic rows per accepted fixture. Both sides reject the real 138,530-row count. No original Wednesday CSV, trained model, original/child neural checkpoint, symbolic maintenance, detector, replay, real outcome or network API is touched.
- `tools/stage10/stage10a_process_escrow_audit.py` imports **neither** the writer nor a model. It re-derives all fake-token and row identities, raw prediction hash chains, maturation clocks, simulated labels, separate reported PIDs, seal file hashes and negative production-claim flags from bytes. It checks exactly the five seed directories and expected file inventory.
- `tests/stage10/test_stage10a_process_escrow_synthetic.py` exercises all five real subprocess handshakes, duplicate/out-of-order/future-label/cross-seed requests, replaced or partially forged journal and receipt bytes, tampered production claims, missing seeds, repeated writers and prohibited real-sized rows. **Local Python 3.13.5: 18 tests PASS**. Hosted Python 3.11.9 CI is required at an exact commit before HOT promotion.

## What this evidence cannot prove

This remains **same-user, unprivileged subprocess separation**. The synthetic label function is public and derivable; the parent can potentially access files/code or forge a PID or a retrospective receipt. Separate PIDs and a JSON audit do **not** prove least-privilege access, confidential labels, independent fsync chronology, power-loss durability, true original Git/runtime identity, checkpoint/RNG/optimizer ancestry, real neural-state equivalence or treatment effects. A retrospective verifier cannot independently certify the writer's `fsync` call, merely inspect the writer-side call path and escrow-observed bytes. No trusted independent signature or external custody witness is used.

The fixture writes a *supplemental* `predictions.jsonl` and `escrow_receipts.jsonl` under isolated test directories. They are **not** a new accepted experimental Phase-A shape, and must not supplant the inherited six Stage-8 Phase-A journals, five-seed seals, three read-only Phase-B arms, or offline Phase-C evaluator.

## Prospectively recommended trust model (NOT approved/frozen)

1. **Execution attestation:** a separately controlled job/runner or observer records exact immutable checkout, runtime/dependency environment and attempt identity, with independently retained signed or otherwise trusted receipts. A self-declared Git SHA is insufficient.
2. **Label principal:** move actual true-label custody into a distinct principal/sandbox with enforceable filesystem permissions or mount isolation; make the model/control process unable to read future labels, not merely promise not to use them. Preserve the accepted test-before-update semantics and 5,000-row maturity exactly. Consider Windows and Linux implementations independently; this POSIX-like filesystem test is not platform authorization.
3. **Append custody:** independently observable append/commit event chain and barrier enforced by the escrow service before any matured label is returned, including interruptions and partial attempts; actual fsync/persistence requires trusted host-level witness or equivalent control.
4. **Checkpoint and Phase-B custody:** retain original and child checkpoint bytes in protected custody; independent byte/state-parent chain, replay/RNG/optimizer and next-row-effective clock audit; expose Phase-A and child checkpoints to all symbolic consumers as read-only only after all five Phase-A seals complete.
5. **Scientific governance:** separate versioned production review and explicit Stage-10A RELEASE remain mandatory; S10-04 criteria freeze is not a second dataset experiment; do not infer generalization.

**Disposition:** This **narrows the implementation risk** for a proposed process-boundary handshake but closes **no production release gate**. Keep this WARM, preserve earlier synthetic and original receipts, and update the sole HOT state with a short pointer **only after exact-commit hosted CI succeeds**. Scientific treatment and outcomes remain prohibited.
