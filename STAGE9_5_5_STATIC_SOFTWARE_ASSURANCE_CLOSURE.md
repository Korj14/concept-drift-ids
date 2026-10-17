# Stage 9.5-5 Static Software Assurance Closure

**Status:** CLOSED — STAGE 9.5-5 ONLY  
**Audited head:** `7e48418f98ad4115c1ae63644ee333f3bc268ae1`  
**Stage-9.5 workflow:** `38646749987`  
**Static job:** `116135369558`  
**Same-head Stage-9 regression:** `38646749995` — success

## Closure decision

Stage 9.5-5 is closed.

The v1.4 developer-only static toolchain executed validly against the frozen 38-file scientific source union plus the Stage-9.5 assurance surface:

- Ruff `0.17.0`;
- mypy `2.4.0`;
- historical `requirements-lock.txt` identity unchanged;
- Ruff findings: **155**;
- mypy findings: **55**.

The static discovery job is red by design because the discovery runner returns nonzero whenever findings exist. Closure is therefore based on the separately frozen finding triage, not on treating the discovery job color as a pass/fail proxy.

## Exact finding triage

All **210** static findings are accounted for with deterministic, hash-bound dispositions:

- 189 scientific findings;
- 21 assurance findings;
- unmatched: **0**;
- multiply matched: **0**;
- unresolved: **0**.

Normalized finding fingerprint-set SHA-256:

`2cffcdaa4a53f608336b4336df833877c6f5ad65f57877c63fb37c0c8b1b5a69`

Scientific fingerprint-set SHA-256:

`268693732ad427a3e21482634b75b7c0d72bf61d70847340bf14cc45678754df`

The scientific finding set is exactly unchanged from the previously reviewed valid static discovery.

### Scientific dispositions

The 134 Ruff findings are legacy/style/static-modernization findings. Potentially behavioral Ruff families received explicit source review:

- all 19 B023 loop-closure warnings occur in trace generators that are synchronously and fully consumed before the enclosing arm loop advances;
- B008/RUF009 defaults are frozen immutable configuration dataclasses or immutable dtype objects;
- exception-type recommendations do not change the fail-closed conditions.

The 55 scientific mypy findings contain:

- **4** third-party typing limitations: two broad PyTorch `nn.Module` return types and two NumPy heterogeneous-payload typing cases;
- **51** legacy static annotation/narrowing findings. Reviewed clusters include lifecycle local-name reuse/Optional narrowing, Stage-9 detector dictionaries, nominally distinct but structurally identical Stage-8/9 row dataclasses, JSON manifest object typing, and aggregate-export narrowing.

No behavior-changing scientific defect was identified.

### Assurance dispositions

All assurance mypy findings were eliminated by the v1.2 hardening.

Of the 21 remaining assurance Ruff findings:

- 20 are import/style/type-spelling/regex-alias/exception-taxonomy findings;
- one S102 finding is the deliberate dynamic compilation mechanism used by the source-derived mutation tests. It is resolved as an intentional test-only mechanism: only repository-controlled production source is compiled, mutation substrings are exact-occurrence asserted, and execution occurs in the isolated mutation test process.

## Same-head regression state

At the audited head:

- Stage 9.5-0 scanner/parameter assurance: **success**;
- Stage 9.5-2 independent statistical oracle: **success**;
- Stage 9.5-3 causal/information properties: **success**;
- Stage 9.5-4 targeted mutation assurance: **success**;
- Stage-9 robustness contract: **success**;
- Stage 9.5-1 fresh clone: still **blocked**, with **0 identity failures and 1 external-artifact blocker**.

The remaining 9.5-1 blocker is the unrecovered exact System-A checkpoint byte set. This closure does not downgrade or resolve it.

## Change boundary

No accepted scientific `src/concept_drift_ids/**` implementation was rewritten to satisfy current lint/type conventions. The historical runtime lock was not modified. No Stage-10 outcomes were accessed.

Current gate state:

- 9.5-0: closed;
- 9.5-1: open / Class-A blocked;
- 9.5-2: closed;
- 9.5-3: closed;
- 9.5-4: closed;
- 9.5-5: closed;
- Stage 10: prohibited.
