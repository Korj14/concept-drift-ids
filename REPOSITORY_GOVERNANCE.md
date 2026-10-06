# Repository and Milestone Governance

This repository supports a research program in which code history is part of the experimental audit trail.

## Authority

Scientific decisions are governed by:

1. `MAIN - Concept_Drift_NIDS_Research_Gap_Doctrine.docx`
2. `Reconciled_Pre-Stage_3_and_Stage_3_Implementation_Plan.docx` for operational details that do not conflict with MAIN.

Repository documents summarize and operationalize those sources; they do not silently supersede them.

## Branch roles

### `main`

`main` represents the **latest fully accepted scientific milestone**.

A commit belongs on `main` only after the relevant stage has:

- satisfied its prespecified scientific/implementation gate;
- passed repository tests;
- frozen any outcome-sensitive protocol/artifact required by that gate;
- preserved relevant hashes/provenance;
- recorded execution and interpretation in `METHODOLOGY_LEDGER.md`;
- passed the current CI workflow.

Direct experimental development on `main` is discouraged.

### Stage branches

New scientific stages are developed on a dedicated branch created from the latest accepted `main`.

Recommended pattern:

`stage<N>-<short-purpose>`

Examples:

- `stage4-system-b`
- `stage5-adaptive-neural`
- `stage6-symbolic-evolution`

The exact numbering may follow the final implementation roadmap, but a new major experimental component should not continue indefinitely on an already-closed stage branch.

## Merge policy

1. Complete the stage on its branch.
2. Run the local repository test/verification suite.
3. Push all compact versioned evidence/manifests required by the stage.
4. Confirm CI is green at the branch head.
5. Open a pull request into `main`.
6. Review the changed-file set against MAIN, the Reconciled plan, the control register, and the statistical-analysis plan.
7. Merge only after the stage is scientifically accepted.
8. Preserve the stage branch/history at least through publication.
9. Create an annotated milestone tag for accepted major stages.

Do not squash a scientifically meaningful stage history merely for cosmetic cleanliness. The implementation sequence, freeze points, and corrective commits are part of the reproducibility record.

## Milestone tags

Major accepted states should receive immutable annotated tags, for example:

- `system-a-v1`
- later System-B/C/D or pre-C/D-analysis-plan milestones as appropriate.

A tag identifies the exact repository state associated with a frozen evidence package even after `main` advances.

Tags must not be moved after publication-relevant evidence has been associated with them. A changed protocol receives a new version/tag.

## Merge checklist

Before merging a scientific milestone:

- [ ] Branch is based on an accepted prior milestone.
- [ ] CI passes on the exact head to be merged.
- [ ] No required local evidence remains uncommitted except intentionally ignored large artifacts.
- [ ] Every committed evaluation manifest verifies its referenced compact evidence files.
- [ ] `METHODOLOGY_LEDGER.md` records the completed execution and whether outcomes caused any change.
- [ ] `EXPERIMENT_CONTROL_REGISTER.md` reflects any newly frozen or changed variables.
- [ ] `STATISTICAL_ANALYSIS_PLAN.md` is updated when the stage affects inference/analysis.
- [ ] `RESEARCH_DOCTRINE.md` remains synchronized with the current governing sources.
- [ ] No result-driven retuning or silent artifact replacement occurred.
- [ ] The stage can be reproduced from its committed manifests plus intentionally external raw/large artifacts.

## Change/deviation policy

Improvements are encouraged when they strengthen scientific validity, reproducibility, robustness, efficiency, or publication quality.

If an improvement affects a frozen experimental variable or analysis choice:

- document the reason before applying it to untouched evidence;
- state whether it changes treatment definition or causal comparability;
- create a new version of the affected protocol/artifact;
- preserve the previous evidence;
- rerun matched conditions if required;
- update the control register and methodology ledger.

Observed poor performance is not by itself a valid reason to revise a frozen protocol.

## Branch protection target

The preferred GitHub configuration for `main` is:

- require pull requests before merge;
- require the repository CI/check to pass;
- prevent force pushes;
- prevent branch deletion;
- require the branch to be up to date before merge where practical.

These repository settings complement, but do not replace, the scientific freeze/versioning rules above.
