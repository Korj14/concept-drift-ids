# Stage 9.5-6 Replay-Equivalence Correction Protocol v1.1

**Status:** PROSPECTIVELY FROZEN / EXECUTION BLOCKED  
**Supersedes for future 9.5-6:** v1 replay-equivalence correction  
**Historical v1 preserved:** yes

## Additional prerequisite

A 9.5-6 rerun may not begin until both are recovered from authoritative sources:

1. the five original System-A initial checkpoint files, with exact accepted SHA-256 values;
2. the original Stage-8 large artifact tree/archive rooted at `artifacts/cd_primary_v1`.

The recovered large archive must be verified against the accepted compact/run/arm/evaluation descriptors before any fresh-rerun comparison.

## No summary-only fallback

The committed compact evidence remains authoritative for accepted reported results, but it does not contain the full Phase-B maintenance streams.

Because the v1 correction removes only predeclared timing diagnostics from maintenance records, record-level accepted projections require the original `maintenance.jsonl` bytes.

If the large archive is unavailable, do not replace record-level replay equivalence with matching aggregate counts, final rules, or favorable metrics. 9.5-6 remains blocked.

## Historical replay procedure

After both external prerequisites are verified:

1. reconstruct Stage-1 interim tables under the frozen historical environment;
2. run all five Phase-A seeds at exact head `bfa14b942e4a5b2fbfa8aa3c43728a7f1cd81645`;
3. run all five Phase-B seeds at that head;
4. reproduce/preserve the expected original Phase-C v1 seed-0 NameError evidence;
5. regenerate the correction config from historical correction source `79ddc4c6d6dea52c7cabc55a6d082448fc24fcf9` using the fresh A/B artifacts;
6. verify all frozen scientific blocks equal the accepted corrected config;
7. run unmodified historical corrected Phase C for frozen rerun seed 0.

The regenerated correction config is a verification artifact, not replacement evidence.

## Comparison rules retained from v1

Phase-A projection may normalize only:

- `runtime.platform`;
- `runtime.processor`;
- `runtime.threadpool_info[*].filepath`.

Phase-B maintenance projection may remove only:

- `shap_seconds`;
- `surrogate_seconds`;
- `lifecycle_seconds`;
- nested `generation_payload.timing_seconds`;
- the six derived timing-only maintenance-summary fields frozen in v1.

Recovered accepted maintenance files are first verified by their original raw SHA-256, then projected. Fresh maintenance files are projected with the identical function. Projected records must match exactly.

All other fields remain fail-closed, including checkpoint bytes/state hashes, predictions, detector/label chronology, replay evidence, generation and validation evidence, rules, lifecycle decisions, publications, metrics, explanations, traces, and endpoints.

No additional exclusion may be added after fresh rerun outcomes are inspected.

## Closure meaning

A successful rerun remains verification evidence only. It does not replace accepted Stage-8/9 evidence and does not broaden claims.

This v1.1 protocol is itself blocked until both external artifact sets are recovered.
