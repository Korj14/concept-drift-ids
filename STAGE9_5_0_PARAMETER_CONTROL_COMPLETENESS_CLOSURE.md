# Stage 9.5-0 Parameter / Control Completeness Closure

**Status:** CLOSED — STAGE 9.5-0 ONLY  
**Governing protocol:** `STAGE9_5_Q1_INDEPENDENT_ASSURANCE_PROTOCOL.md`  
**Protocol freeze commit:** `cf9bb49cc18c751872a12d3530df8ff78d26d67a`  
**Accepted upstream Stage-9 closure head:** `4dca828acb3916feb3f30d61f1b587240a6eba19`  
**Audited implementation/evidence head:** `1ba03046562138907d1c616293f5300bbaffb025`

## 1. Closure decision

Stage 9.5-0 parameter/control completeness is closed.

This closure is limited to the completeness/classification gate. It does **not** close Stage 9.5 as a whole, does not authorize Stage-10 outcome access, and does not replace the required 9.5-1 through 9.5-9 assurance sequence.

## 2. Accepted final evidence

Final accepted scanner iteration: **v1.11.1**.

- Stage-9.5 assurance run: `38450785661` (run 171), success.
- Same-head Stage-9 robustness regression: `38450785384` (run 361), success.
- Scanner tests: **22 passed, 0 failed**.
- CI artifact: `stage9-5-parameter-scan-v1-11-1`.
- Artifact ID: `11840900286`.
- Artifact ZIP SHA-256: `2514a9085ba271e1533a40259f50f2e1c6d7da285baedaa6bac3433a3bd200fd`.
- Canonical scan SHA-256: `3c53bbc026f8cb3a1a21ba8e9160cf692472f9df3ca152c23867dfe8a504727c`.
- Parameter-register SHA-256: `294ea5e76c4266d2011c963f737c492a1944c5d59e31f05fcaf99b4cda5057a0`.

Final counts:

- registered entries: **88**;
- material candidates: **511**;
- retained exclusions: **1,444**;
- unclassified material candidates: **0**;
- ambiguous material mappings: **0**;
- unclassified high-leverage candidates: **0**.

## 3. Scope and matching guarantees

The scanner verifies that its scientific Python scan scope equals the union of `scientific_source_hashes` from the accepted Stage-8 and Stage-9 run manifests. The accepted v1.11.1 report confirms that binding exactly, covering **38 scientific/test Python source files**.

Registration remains fail-closed and requires:

1. the candidate source path to be listed for the register entry;
2. the candidate locator to satisfy the entry locator pattern when one is defined; and
3. the candidate value to match the entry `scan_values` or accepted value using typed exact matching.

The final scanner includes assignment-level literal extraction, targeted material-expression discovery, source-specific lifecycle/detector classification, material dictionary-value discovery for replay controls, and retained auditable exclusions rather than silent dropping.

## 4. Final adversarial exclusion review

The final v1.11.1 exclusion review specifically rechecked every scanner gap discovered during 9.5-0 development.

Confirmed material and registered, with no matching exclusion:

- Stage-9 `label_latency: 0` treatment;
- all executable Stage-9 `replay_enabled=True/False` source mirrors;
- lifecycle overlap defaults `0.95 / 0.50 / 0.50`;
- lifecycle failure-streak `+1` / minimum-one semantics;
- direct-source `ADWIN_CONFIG`;
- direct-source `PAGE_HINKLEY_CONFIG`;
- accepted R0 active-count identity assertions;
- Stage-9 shared-runner detector family/signal defaults;
- symbolic lifecycle status/state/transition semantics.

The remaining high-leverage exclusions were reviewed by reason and source. They are retained as auditable exclusions because they are provenance/runtime mirrors, hash identities, validation/domain guards, arithmetic identities, historical outcome/provenance statements, or preserved failed-run checks rather than independent treatment/control declarations.

## 5. Failure preservation and correction history

All failed and superseded scanner iterations remain preserved. This includes the initial gross-overcount failure and subsequent scanner/register methodology defects, fixture/version errors, syntax failure, strict-matching residuals, source-scope/material-name gaps, literal-container duplicate discovery, source-specific precedence defects, small-material-expression discovery gaps, and validation/provenance false positives.

The accepted v1.11.1 closure does not erase or reinterpret those failures. They form the audit trail showing how the completeness harness was tightened until the final fail-closed result was defensible.

## 6. Scientific-change classification

No accepted Stage-8/Stage-9 treatment, endpoint, scenario, preprocessing object, seed set, threshold, information set, inference rule, or observed result was changed during Stage 9.5-0.

The corrections were assurance-harness/register-completeness corrections only. The v1.11 scientific register classifies numeric/categorical controls according to scientific role; numeric appearance alone was not treated as a requirement for sensitivity testing.

No Stage-10 outcomes were accessed.

## 7. Next authorized step

The next authorized assurance work is **Stage 9.5-1 fresh-clone reconstruction** under the already-frozen Stage-9.5 protocol.

Stage 10 remains hard-gated until Stage 9.5 is formally closed through 9.5-9 and the Stage-10+ master protocol is prospectively frozen.
