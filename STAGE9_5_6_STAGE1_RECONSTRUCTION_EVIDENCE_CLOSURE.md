# Stage 9.5-6 Stage-1 Reconstruction Evidence Closure

**Status:** CLOSED — AUTHORITATIVE STAGE-1 RECONSTRUCTION EVIDENCE VERIFIED  
**Closure date:** 17 October 2026  
**Scientific evidence changed:** no  
**Accepted Stage-8/9 evidence replaced:** no  
**Stage-10 outcomes accessed:** no

## Scope

This closure resolves only the non-external Stage-9.5-6 predecessor blocker:

`stage1_reconstruction_evidence_not_verified`

It does not close Stage 9.5-1, does not close the complete Stage 9.5-6 replay, and does not authorize Stage 10. The two unresolved external artifact blockers remain:

- `system_a_checkpoint_bytes_missing`;
- `stage8_large_artifact_archive_missing`.

## Frozen authority

The authoritative prospective contract remains unchanged:

`data/manifests/stage9_5_6_stage1_reconstruction_evidence_v1.json`

The authoritative verifier remains:

`tools/stage9_5/stage1_reconstruction_evidence.py`

The preserved verifier-produced report is:

`results/audits/stage9_5_full_seed_rerun_v1/stage1_reconstruction_report.json`

No post-outcome relaxation or contract rewrite was used.

## Successful authoritative execution

The successful execution occurred on assurance head:

`58b3e42cdeeddea28f7cb20268ed9912684adba3`

GitHub Actions:

- workflow: `Stage 9.5 Stage-1 reconstruction`;
- run: `39030450159`;
- job: `117389666439`;
- Python: `3.11.9`;
- frozen dependency lock installed exactly;
- all eight CICIDS2017 raw CSV SHA-256 identities verified before preprocessing;
- historical Stage-1 preprocessing source executed only after frozen Git-blob verification;
- independent structural preprocessing recomputation completed for all eight tables.

The small uploaded evidence artifact was:

- artifact ID: `12099849424`;
- artifact digest: `sha256:2676f9bdd8aba01f97415c7761d78495170891ea579d6f66f7b3fd401e4f15c3`.

The GitHub Actions identifiers and artifact digest are supplemental execution provenance. Closure authority remains the frozen contract/verifier identities plus the preserved canonical report.

## Report identity

The preserved report records:

- `audit_id = stage9.5-6-stage1-reconstruction-v1`;
- `contract_id = stage9.5-6-stage1-reconstruction-evidence-v1`;
- `status = pass`;
- `pass = true`;
- `repository_head = 58b3e42cdeeddea28f7cb20268ed9912684adba3`;
- `raw_file_count_verified = 8`;
- `interim_table_count_verified = 8`;
- `semantic_mismatch_count = 0`;
- `failures = []`;
- `blockers = []`;
- `preprocessing_manifest_canonical_sha256 = d33ea433973d4f685812ec3dfbd22424fdcf715d2052bf557dc9e61e2c847ef0`;
- `contract_canonical_sha256 = 049be3a211b613e3b37507182aa23bfd83c2289b9f08feeb033b39f8e0a29ca1`;
- `verifier_id = stage9.5-6-stage1-reconstruction-verifier-v1`;
- `verifier_source_sha256 = 3c21500ae9faafd0a6588395662db71046e37978072e511e6519fa9bebff68a9`;
- `canonical_sha256 = 4bafa772f9737d934f40c90bf7be8d80a62108cf89a9c74895fbe5c12c4a88af`.

Independent post-run checks recomputed the report canonical SHA-256, the frozen contract canonical SHA-256, and the verifier source SHA-256 and matched all three embedded identities exactly.

Every one of the eight table records reports `semantic_equal_to_independent_recompute = true`.

## Transport provenance boundary

The successful runner acquired the published `MachineLearningCSV.zip` bytes through an external mirror strictly as a transport mechanism. The mirror was not treated as evidence authority.

Supplemental transport provenance from the successful run:

- mirror repository commit: `811c007f08d693a8a8b4226c197c138391806ce6`;
- mirror tracked path: `csvs/MachineLearningCSV.zip`;
- transported ZIP SHA-256:
  `c3f26274b36c837ccf28ffd2dbf4582941c30b3ee70a635c6e5b2f87c4727928`.

The extracted data became eligible for verification only because every one of the eight source CSVs matched the exact SHA-256 values already frozen in the Stage-1 contract. A mirror mismatch would have failed before preprocessing.

## Preserved failed execution history

The execution path was not linear. The following failed attempts are preserved and are not hidden:

1. Run `39029867251` used a guessed mirror root URL and failed with HTTP 404 before any raw data was trusted or preprocessing occurred.
2. Run `39030072837` did not start a job because a workflow-edit string-replacement defect corrupted the YAML definition. This was a harness-only failure.
3. Run `39030232104`, job `117389044176`, successfully installed Python 3.11.9, acquired the transport bundle, extracted it, and verified all eight frozen raw SHA-256 identities. It then failed before Stage-1 preflight with `ModuleNotFoundError: concept_drift_ids` because the workflow omitted `PYTHONPATH=src`. This was a harness-only import-path defect. Its supplemental artifact ID was `12099759200`.
4. The harness import path was corrected prospectively. Run `39030450159` then passed the unchanged frozen verifier.

None of these failures caused a scientific contract change, diagnostic relaxation, raw-hash change, or accepted Stage-8/9 evidence replacement.

## Closure conclusion

The Stage-1 reconstruction prerequisite required by replay-equivalence v1.1 is now machine-verified and preserved.

Therefore:

- `stage1_reconstruction_evidence_not_verified` is resolved;
- Stage-9.5-6 replay mechanics now have no remaining non-external implementation/evidence blocker identified by the frozen construction pipeline;
- Stage-9.5-1 remains open because the exact original System-A checkpoints and original Stage-8 heavy archive remain unrecovered;
- full Stage-9.5-6 execution remains blocked by those same external prerequisites;
- Stage-9.5-7/8/9 remain locked/provisional until a valid Stage-9.5-6 closure;
- Stage 10 remains prohibited.

This closure changes assurance provenance only. It does not alter any Stage-8/9 estimand, treatment, comparator, metric, numerical result, inference family, or claim boundary.
