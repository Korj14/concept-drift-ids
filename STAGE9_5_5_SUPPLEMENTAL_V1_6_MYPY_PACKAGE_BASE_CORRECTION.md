# Stage 9.5-5 Supplemental v1.6 Mypy Package-Base Correction

**Status:** PROSPECTIVE TOOLING CORRECTION AFTER INVALID v1.5 SUPPLEMENT

The v1.5 supplemental static run is not valid closure evidence because mypy returned code 2 before checking the new Stage 9.5-7/8 assurance modules.

Exact diagnostic:

`Source file found twice under different module names: "stage9_5.claim_traceability" and "tools.stage9_5.claim_traceability"`

Cause: `tools/` is used as a namespace-package root while the same source files are also passed explicitly to mypy. Without an explicit package base, mypy assigns inconsistent module names.

v1.6 changes only the developer-tool invocation by adding:

`--explicit-package-bases`

The frozen source scope, Ruff invocation, historical runtime lock, accepted scientific code, claim definitions, reporting selectors, and Stage 9.5-8 numerical logic remain unchanged.

The three Ruff findings newly attributable to Stage 9.5-7/8 are import-style findings only:

- `claim_traceability.py` — UP035;
- `independent_reporting.py` — I001;
- `independent_reporting.py` — UP035.

They are provisionally cosmetic and will be finalized only after a valid v1.6 mypy run confirms there are no unresolved assurance typing findings.
