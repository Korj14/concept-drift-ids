# Stage 9.5-5 v1.1 Self-Scope Correction

**Status:** STATIC-ASSURANCE SCOPE CORRECTION AFTER FIRST DISCOVERY  
**v1 head:** `55151a8c588c27eea5ea5e207c854bdbec9debf6`  
**Workflow:** `38550422435`  
**Static job:** `115806748277`

## v1 discovery

The developer-only toolchain executed successfully with the historical runtime lock unchanged:

- Ruff: `0.17.0`;
- mypy: `2.4.0`;
- Ruff findings: **164**;
- mypy findings: **59**.

The raw discovery artifact is preserved. The run was intentionally non-closing because findings require triage.

## Concrete assurance-scope defect

The v1 static contract was frozen before the implementation files `tools/stage9_5/static_assurance.py` and `tests/stage9_5/test_static_assurance.py` existed.

Therefore v1 did not statically inspect the static-assurance harness itself. This is an assurance-harness scope defect, not a scientific-result defect.

v1.1 adds both files to the frozen Ruff scope and the executable harness module to the mypy scope, then repeats discovery before final triage.

## Initial finding review

The high-volume Ruff findings are dominated by import/style modernization and legacy annotation patterns.

The 19 B023 warnings in the accepted Phase-C trace generators were reviewed specially because late binding can be behavioral. In both Stage-8 and Stage-9 Phase-C, the generator is created and fully consumed synchronously by the trace writer before the enclosing arm loop advances. The warning therefore does not expose a delayed late-binding path in the accepted execution.

B008/RUF009 defaults were also reviewed: the flagged scientific defaults are frozen immutable configuration dataclasses (or immutable dtype objects), not mutable state containers.

The mypy findings remain subject to exact ledger triage. No blanket suppression is accepted as closure.

No historical scientific source or runtime-lock rewrite is authorized by this correction.
