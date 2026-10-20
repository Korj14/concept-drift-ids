# Stage 9.5-8 v1.1 Module-Invocation Correction

**Status:** ASSURANCE-HARNESS CORRECTION AFTER FIRST 9.5-8 RUN  
**Failed head:** `f582a377cbae8e36804148786e986b90ae485c1c`  
**Workflow:** `38650032906`  
**Job:** `116146254079`

The first 9.5-8 test suite passed **3/3**. The subsequent standalone reporting command failed before evidence comparison with:

`ModuleNotFoundError: No module named 'tools'`.

The implementation imports `tools.stage9_5.claim_traceability` and `tools.stage9_5.statistical_oracle`. Direct execution by file path changes Python's import root to `tools/stage9_5`, whereas the pytest invocation runs with the repository root importable.

The correction changes only the workflow invocation to:

`python -m tools.stage9_5.independent_reporting ...`

No reporting selector, tolerance, output definition, claim definition, scientific source, or accepted evidence changes.

A supplemental static-assurance scope is also required because Stage 9.5-7/8 introduced new assurance modules after the Stage 9.5-5 closure.
