# Governing Source Register

This file records the exact project-source documents against which this repository milestone was synchronized.

The documents themselves remain in the project Sources area; their raw bytes are not duplicated into the Git repository. Hashes below make the governing versions unambiguous.

| Priority | Source document | SHA-256 | Size (bytes) | Role |
| ---: | --- | --- | ---: | --- |
| 1 | `MAIN - Concept_Drift_NIDS_Research_Gap_Doctrine.docx` | `f0700fc28e5c49ee50a6fab73db870725006ba52541a0d9cf4b285ccbe143a8f` | 55,780 | Highest scientific authority: research gap, causal logic, publication-level control standard, evidentiary conditions |
| 2 | `Reconciled_Pre-Stage_3_and_Stage_3_Implementation_Plan.docx` | `83d1e101a525e840a1235743ac5fc050ca560f228df047bee17a84e80cbf3082` | 50,623 | Authoritative operational protocol where it does not conflict with MAIN |

## Precedence

If the operational plan conflicts with MAIN on scientific validity, causal isolation, trigger semantics, preprocessing, information timing, inference, symbolic lifecycle, reproducibility, or external-validity limits, MAIN governs.

Where MAIN is silent on implementation detail, the Reconciled plan governs.

## Update rule

When either source document changes:

1. compute and record the new raw-file SHA-256;
2. compare the changed directives against repository code, manifests, protocols, analysis plans, and governance files;
3. document any required deviation or migration before new untouched evidence is evaluated;
4. preserve previously frozen experimental artifacts rather than silently rewriting them;
5. update `METHODOLOGY_LEDGER.md` with the synchronization decision;
6. commit the revised source register before the next scientific milestone is accepted.

A source-document update does not automatically invalidate prior evidence. Its implications must be assessed explicitly against the freeze point at which that evidence was produced.
