# Stage 9.5-8 Independent Table/Figure Regeneration Closure

**Status:** CLOSED — STAGE 9.5-8 ONLY  
**Audited head:** `e2db8b7fab8c184707280cea1045809c1b26ec13`  
**Reporting workflow:** `38661230961`  
**Reporting job:** `116182709403`  
**Same-head Stage-9 regression:** `38661230724` — success

## Closure decision

Stage 9.5-8 is closed.

The independent reporting path regenerated the frozen table/figure source data from immutable evidence without importing production aggregation/reporting code.

Accepted reporting evidence:

- artifact: `stage9-5-independent-reporting-v1`;
- artifact ID: `11938319361`;
- artifact ZIP SHA-256: `c510adec8c9c64736cc8b23f7faba28835f4a16dbdc58c2845b6e6faa3ab17e2`;
- report canonical SHA-256: `ec5f0fe7894ad8e2fa2cb94da03eb6fb734c4ce3f97cedf440183da64aa957b8`.

## Independent numerical verification

The reporting path compared included oracle-recomputable numerical values to the closed Stage 9.5-2 independent oracle:

- comparisons: **210**;
- mismatches: **0**;
- oracle canonical SHA-256: `b36f8f9b2cf2237762298d139139bd5160c0805054b1540c3c56e6acf915819d`.

The claim ledger authority is:

`a4960cba4c12e983e764340044ee87cc1448f104af2142041fc342b906f88ecb`.

All 9 required machine-readable outputs were present:

- claim ledger;
- primary confirmatory table;
- primary operating trade-off table;
- mechanism decomposition table;
- Stage-9 robustness table;
- timing/recovery table;
- primary-effects figure source;
- robustness-effects figure source;
- mechanism figure source.

Across those generated table/figure sources, **88/88** records carried claim ID, evidence selector, value name, verification authority, and unrounded source value.

Presentation rounding was not applied to source values.

## Independence

The reporting implementation records:

- production reporting imports used: **false**;
- scientific objects modified: **false**;
- Stage-10 outcomes accessed: **false**.

## Supplemental implementation assurance

The new Stage 9.5-7/8 assurance-code delta was checked separately under the accepted v1.4 static baseline:

- Ruff: **0 findings**;
- mypy: **0 findings**;
- historical runtime lock unchanged;
- artifact ZIP SHA-256: `0635f924b2b64fba3bdf99ca685fd986601c42247097b08cc12eb530a3871706`;
- report canonical SHA-256: `50c0107d5cdacd0dcc6d0a842421ea662fa84a842574b2b381091a591bc65775`.

## Remaining gate state

This closure does not resolve the independent checkpoint provenance/reconstructibility blocker.

- 9.5-1: open / Class-A blocked;
- 9.5-6: open / blocked by 9.5-1;
- 9.5-7: closed;
- 9.5-8: closed;
- 9.5-9: next package;
- Stage 10: prohibited.
