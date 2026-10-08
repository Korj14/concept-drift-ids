# Governing Source Register

This file records the exact project-source documents governing future work. The documents themselves remain in the project Sources area; their raw bytes are not duplicated into the Git repository.

## Current authority set

| Priority | Source document | SHA-256 | Size (bytes) | Role |
| ---: | --- | --- | ---: | --- |
| 1 | `MAIN - Concept_Drift_NIDS_Research_Gap_Doctrine.docx` | `c3f1fed692ff0478c221925fca5c311380617a993e7ebf0021af2e05a362ab66` | 58,895 | Highest scientific authority: research gap, causal logic, retrospective-assumption doctrine, publication-level control standard, evidentiary conditions |
| 2 | `Reconciled_Pre-Stage_3_and_Stage_3_Implementation_Plan.docx` | `05378ef14437f037bab0aa77853a16980b4fc60ac303398acc1cc293bdd32bdb` | 56,775 | Authoritative operational protocol, including retrospective audit, B robustness closure, pre-C/D freeze gates and later validation obligations |

## Historical authority set for already-frozen A/B evidence

The following hashes were the governing source identities when the frozen Stage-3/System-A/System-B artifacts were created. They remain historically correct provenance and MUST NOT be rewritten inside accepted manifests:

| Source document | Historical SHA-256 | Historical size |
| --- | --- | ---: |
| `MAIN - Concept_Drift_NIDS_Research_Gap_Doctrine.docx` | `f0700fc28e5c49ee50a6fab73db870725006ba52541a0d9cf4b285ccbe143a8f` | 55,780 |
| `Reconciled_Pre-Stage_3_and_Stage_3_Implementation_Plan.docx` | `83d1e101a525e840a1235743ac5fc050ca560f228df047bee17a84e80cbf3082` | 50,623 |

The revised documents were created after corrected System-B v2 evidence had been frozen. Their directives therefore govern new diagnostics, robustness analyses and future C/D work prospectively. They do not retroactively alter A/B treatment identities.

## Precedence

If the operational plan conflicts with MAIN on scientific validity, causal isolation, trigger semantics, preprocessing, information timing, inference, symbolic lifecycle, reproducibility, or external-validity limits, MAIN governs.

Where MAIN is silent on implementation detail, the Reconciled plan governs.

## Update rule

When either source document changes:

1. compute and record the new raw-file SHA-256;
2. compare the changed directives against repository code, manifests, protocols, analysis plans, and governance files;
3. document whether the change is a restart-triggering defect, an additive sensitivity/diagnostic, or a later generalization obligation;
4. preserve previously frozen experimental artifacts rather than silently rewriting them;
5. update `METHODOLOGY_LEDGER.md` and the experimental-control register;
6. commit the revised source register before the next scientific milestone is accepted.

A source-document update does not automatically invalidate prior evidence. Its implications must be assessed explicitly against the freeze point at which that evidence was produced.
