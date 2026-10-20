# Stage 9.5-5 v1.3 Syntax-Regession Correction

**Status:** ASSURANCE-HARNESS CORRECTION AFTER FAILED v1.2 RUN  
**Failed head:** `509e796bc7deba313cad212719494bd2b31cbda4`  
**Workflow:** `38554239204`

## Failure

v1.2 was not a valid static-assurance discovery.

Two assurance-only source edits contained the literal characters `\n` inside import lines rather than an actual newline:

- `tools/stage9_5/parameter_scan.py`;
- `tests/stage9_5/test_targeted_mutations.py`.

Consequences:

- Stage 9.5-0 scanner tests failed during collection;
- Stage 9.5-4 mutation tests failed during collection and therefore reported 0/11 killed;
- Stage 9.5-5 mypy reported three syntax errors and the static runner correctly classified the run as `tooling_error`.

The same-head Stage-9 regression remained successful, the independent statistical oracle remained successful, and causal-property assurance remained successful.

## Correction

v1.3:

1. replaces the malformed literal `\n` imports with real newlines;
2. adds a Stage-9.5 compile regression test over the assurance Python scope;
3. reruns the closed 9.5-0 and 9.5-4 regressions as part of the normal Stage-9.5 workflow;
4. reruns static assurance before any triage ledger is frozen.

No scientific source module, accepted evidence object, parameter, or historical dependency lock is modified.
