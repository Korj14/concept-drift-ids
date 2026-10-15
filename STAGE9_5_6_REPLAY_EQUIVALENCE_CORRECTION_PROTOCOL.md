# Stage 9.5-6 Replay-Equivalence Correction Protocol v1

**Status:** PROSPECTIVELY FROZEN / EXECUTION BLOCKED  
**Purpose:** resolve the historical identity-replay defect without rewriting Stage-8/9 evidence  
**Stage-10 access:** prohibited

## Preconditions

No rerun may begin until the five original System-A checkpoint files are recovered and match their accepted SHA-256 identities. The eight raw CICIDS2017 files must also match the frozen raw manifest.

## Historical execution path

1. In an isolated clean worktree at `bfa14b942e4a5b2fbfa8aa3c43728a7f1cd81645`, reconstruct Stage-1 interim tables from the exact raw files under the frozen Python/dependency environment.
2. Require the frozen structural-preprocessing manifest identity and scenario/input identities to match. Interim gzip container bytes are not themselves an accepted scientific identity.
3. Place the five recovered initial checkpoints at `artifacts/system_a/checkpoints/seed_<n>.pt` and require exact byte hashes.
4. Execute all five historical Phase-A seeds.
5. Execute all five historical Phase-B seeds.
6. Execute the original Phase-C v1 seed-0 path and preserve the expected NameError attempt/failure evidence exactly.
7. At correction source head `79ddc4c6d6dea52c7cabc55a6d082448fc24fcf9`, run the historical correction-config generator against the fresh A/B artifacts and preserved failed attempt. Commit only the generated `cd_primary_run_config_v1_1.json` in an isolated rerun worktree.
8. Verify that every frozen scientific block in that regenerated correction config is identical to accepted corrected config `d380fce5f9db8f0b639dc999298a263b10a10a3d02e35def226a121d098e2222`. Differences are permitted only in provenance identities derived from fresh A/B manifests and their dependent top-level hashes.
9. Run the unmodified historical corrected Phase-C code at that isolated correction-config commit for at least one prespecified seed. Seed 0 is the frozen rerun seed.

The regenerated correction config and its commit are verification artifacts only. They do not replace the accepted corrected config or accepted Stage-8 evidence.

## Replay-equivalence rules

### Phase A

Require exact equality for the scientific/configuration content, including:

- initial checkpoint byte SHA;
- preprocessing/scenario/input identities;
- predictions and logical row order;
- label schedule and detector observations;
- replay transactions and adaptation chronology;
- child model state identities;
- checkpoint publication indices;
- shared-neural identity;
- frozen protocol/source/dependency versions.

For the Phase-A run-manifest projection only, normalize these diagnostic machine-description fields before comparison:

- `runtime.platform`;
- `runtime.processor`;
- `runtime.threadpool_info[*].filepath`.

All other runtime fields remain exact. Generated child checkpoint file hashes remain exact in v1; they are not predeclared diagnostic exclusions.

### Phase B

Compare every arm's scientific projection exactly.

Strip only measured duration fields:

- maintenance records: `shap_seconds`, `surrogate_seconds`, `lifecycle_seconds`;
- nested `generation_payload.timing_seconds`;
- maintenance summary: `compute_seconds`, `shap_seconds`, `surrogate_seconds`, `lifecycle_seconds`, `compute_seconds_per_opportunity`, `compute_seconds_per_publication`.

Because the maintenance JSONL byte hash and arm/seed manifest hashes transitively contain those durations, compare canonical projected records/manifests rather than demanding their original raw hashes.

Everything else remains exact, including generation/validation row IDs, SHAP ranking, selected features, surrogate seeds, candidate rules, lifecycle decisions, publication clocks, rule versions, canonical rule-base/history hashes, control-plane isolation, and non-timing maintenance counts.

### Phase C

Require exact equality of prediction-trace canonical JSONL content, metrics, explanations, windows, recovery outputs, trigger diagnostics, retention probes, lambda=1 equality, row counts, and all non-diagnostic scientific fields.

For comparison only, project away:

- the regenerated correction-config manifest SHA;
- raw Phase-A/B manifest references replaced by their already-verified replay projections;
- the same Phase-B timing fields propagated into `maintenance_summary`;
- summary/seed manifest hashes that change solely because of those projected provenance fields.

The gzip trace writer has frozen `mtime=0`; raw trace bytes remain exact unless a predeclared projection says otherwise. No new exclusion may be added after rerun outcomes are inspected.

## Fail-closed rules

Any mismatch outside the fields above is a Class-A stop. In particular, do not relax after the fact:

- initial or adaptive model state identity;
- generated child checkpoint byte identity;
- predictions/probabilities;
- detector events or label maturity;
- replay rows;
- candidate/rule content;
- lifecycle decisions/publications;
- endpoints or explanation values;
- scenario/preprocessing/R0/seed/threshold/operator identities.

If a supposedly diagnostic field later proves behaviorally influential, this protocol fails and must not be broadened retrospectively.

## Interpretation

A successful v1 rerun is verification evidence only. It does not replace accepted Stage-8/9 results, create a new confirmatory family, or broaden external-validity claims.

This protocol remains blocked until the original five initial checkpoint bytes are recovered.
