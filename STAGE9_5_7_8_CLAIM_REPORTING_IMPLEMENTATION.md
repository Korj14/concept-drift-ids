# Stage 9.5-7 / 9.5-8 Claim Traceability and Independent Reporting Freeze

**Status:** PROSPECTIVELY FROZEN BEFORE 9.5-7/8 EXECUTION  
**Stage 9.5-6:** open / blocked by the unrecovered exact System-A checkpoint bytes  
**Stage 10:** prohibited

## Claim-source freeze

The current publication-facing claim universe is anchored to four accepted repository documents:

- `STAGE8_PRIMARY_RESULTS_INTERPRETATION.md`;
- `STAGE8_SYMBOLIC_MECHANISM_AUDIT_INTERPRETATION.md`;
- `STAGE9_ROBUSTNESS_INTERPRETATION.md`;
- `METHODOLOGY_LEDGER.md`.

Their exact Git blob identities are frozen in `data/manifests/stage9_5_claim_reporting_v1.json`.

These interpretation files are claim-source documents, not numerical authority. Numerical authority remains the immutable Stage-8/Stage-9 evidence and the independent Stage-9.5 oracle.

## 9.5-7 — claim-to-evidence ledger

The ledger will cover methodology, primary confirmatory results, descriptive operating trade-offs, detector/publication timing, maintenance/recovery, lambda-1 isolation, mechanism decomposition, all Stage-9 robustness conditions, trigger comparisons, explanation trade-offs, and quantitative scope/limitation statements.

No evidence number may be manually typed into a claim definition and then treated as authority. Each displayed number must come from an exact evidence selector or a prospectively declared deterministic transform.

Each claim records:

- claim ID and text template/status;
- interpretation class;
- claim-source document/section;
- immutable evidence path and exact selector;
- generating and independent verification code;
- config/protocol identity;
- evidence commit/hash;
- display/rounding transform;
- claim boundary.

Because the final manuscript does not yet exist, Stage 9.5-7 retains a mandatory final-submission gate: after the manuscript is finalized, a manuscript-number audit must return **zero orphan quantitative numbers**. Dates, citation numbers, section numbers, versions, and hashes require explicit classification rather than silent exclusion.

## 9.5-8 — independent reporting path

The reporting path will be implemented under `tools/stage9_5/` and may read only immutable evidence, the claim ledger, and independent-oracle outputs.

It must not import production aggregation/reporting modules.

It will emit unrounded machine-readable source data for:

- primary confirmatory table;
- primary prediction/explanation operating trade-off;
- symbolic mechanism decomposition;
- Stage-9 robustness matrix;
- timing/recovery material;
- primary effect figure source;
- robustness effect figure source;
- mechanism figure source.

Every numeric output datum carries its claim ID and exact immutable evidence selector.

Oracle-recomputable values must agree with the independent 9.5-2 oracle within the frozen tolerance. Descriptive mechanism/timing values that are outside the oracle's endpoint domain must match their immutable evidence selectors exactly or under an explicitly predeclared deterministic transform.

Presentation rounding never becomes evidence authority.

## Independence from the 9.5-1/6 blocker

9.5-7/8 operate on already accepted immutable evidence and do not require the unavailable checkpoint bytes. Completing them cannot resolve or downgrade the Stage-9.5-1/6 reconstructibility blocker.
