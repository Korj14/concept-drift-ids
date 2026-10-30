# Stage 9.5-6 Clean Deterministic Full-Seed Rerun - Evidence-Based Closure

**Status:** evidence-derived Stage-9.5-6 closure / local order gate passed / later assurance pending  
**Audited assurance head H:** `c3356e6e062b41f3127cc022eb7571b52758272c`  
**Scientific source, estimands, treatments, and accepted Stage-8/9 results changed:** no  
**Stage-10 outcome access:** no

## Deterministic replay evidence

The frozen `stage9.5-6-replay-equivalence-correction-v1_1` protocol completed at the preserved
historical Phase-A/B head `bfa14b942e4a5b2fbfa8aa3c43728a7f1cd81645` and correction source `79ddc4c6d6dea52c7cabc55a6d082448fc24fcf9`.
All Phase-A and Phase-B seeds 0???4 were compared against the accepted Stage-8 archive,
including all three symbolic arms per seed and the original maintenance-record archive.
The original Phase-C v1 seed-0 `NameError` failure lineage was reproduced and verified,
and the corrected Phase-C v1.1 seed-0 replay was completed and independently verified.
No five-seed Phase-C aggregate was regenerated. The correction-config-only child commit
`431b8fa7de915c93706d4593109c35964be83b54` has frozen source parent `79ddc4c6d6dea52c7cabc55a6d082448fc24fcf9`.

The unchanged frozen comparator and finalizer produced zero mismatches, zero failures,
zero blockers, and zero unresolved Class-A defects. This record does not override or
recompute those verdicts.

- `results/audits/stage9_5_full_seed_rerun_v1/replay_comparison_evidence.json` ??? canonical SHA-256 `5563d38b002fe793c0bcaffdfdfe3c9b96f62d9b028a95ae9597a4dc672ab536`
- `results/audits/stage9_5_full_seed_rerun_v1/replay_equivalence_report.json` ??? canonical SHA-256 `f169ae5fd9dc246ad8e2abe7b321b5d2ad67cb1f2c7ec6a1d3bcb73d4ec58052`
- `results/audits/stage9_5_full_seed_rerun_v1/stage1_reconstruction_report.json` ??? canonical SHA-256 `4bafa772f9737d934f40c90bf7be8d80a62108cf89a9c74895fbe5c12c4a88af`
- `results/audits/stage9_5_full_seed_rerun_v1/phase_c_pre_rerun_verification_report.json` ??? canonical SHA-256 `bf9ea16957b0cfc48aacbb5f7ac582fc6242020b8939f581ee7473c26f7d2c66`

## Stage-9.5-1 external-artifact recovery provenance

The unchanged v1.2 verifier passed with 5/5 exact original System-A checkpoints and
145/145 original accepted Stage-8 archive requirements, no failures or blockers.
This subsequent PASS prospectively resolves the external-artifact predecessor gate;
it does **not** erase or retroactively alter the preserved historical negative closure
or earlier blocked attempts.

- `results/audits/stage9_5_full_seed_rerun_v1/fresh_clone_reconstruction_report.json` ??? canonical SHA-256 `35cbefc053ae910b0eb20ace3443b70ea4972a511b6549f430f3d2ced0980c7d`

## Frozen protocol and construction authority

- `STAGE9_5_6_REPLAY_REPORT_CONSTRUCTION_CONTRACT_V1.md`
- `data/manifests/stage9_5_6_replay_report_construction_v1.json`
- `data/manifests/stage9_5_6_closure_order_gate_v1.json`
- `STAGE9_5_6_HISTORICAL_REPLAY_EXECUTION_HANDOFF.md`
- `STAGE9_5_ASSURANCE_DIVERSION_RETROSPECTIVE_WORKING_NOTES.md` (working retrospective; not closure authority)

The replay report is produced solely by the frozen comparator/finalizer, not by a
manual success override. This closure evidence binds it to the verified predecessor report,
the original Stage-1 report, and the identical audited assurance head.

## Same-head Stage-9 robustness

GitHub Actions Stage 9 robustness contract: completed / success on exactly
`c3356e6e062b41f3127cc022eb7571b52758272c`, run `39415218195` (https://github.com/Korj14/concept-drift-ids/actions/runs/39415218195). This is the required
same-head success and does not authorize Stage-10 outcome access.

## Closure metadata and sequence

Machine-derived closure evidence:
`results/audits/stage9_5_full_seed_rerun_v1/success.json`

The frozen work-package order gate must report `later_packages_unlocked=true`
with no failures before Stage-9.5-7 can be rerun/revalidated. Stage-9.5-7/8/9
prior out-of-order executions remain provisional historical assurance evidence,
not retrospectively valid closure. Following the small-evidence commit, revalidate
9.5-7, then 9.5-8, then 9.5-9, and require zero remaining Class-A issues before
Stage-9.5 overall closure. Stage-10 treatments remain prohibited until then.
