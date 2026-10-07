# System B R0.v2 Protocol-Conformance Correction Plan

**Status:** EXECUTED AND FROZEN; R0.v2 MANIFEST ACCEPTED; CORRECTED HELD-OUT EVALUATION NOT YET RUN  
**Date:** 7 October 2026  
**Source rule base:** R0.v1  
**Source manifest:** `6e3589056d4c252c1a6c7cfd87b891fb8a24f1e30e86b17833b6035ea9ee86a8`  
**Source protocol audit file SHA-256:** `abfcb3af93531369427489fc27773f41e500a57279b0fa752b946c3985ebbf32`

## 1. Why a correction is required

The training-only frozen protocol audit reconstructed all 62 original weighted CART leaves from the exact frozen System-A checkpoints, training rows, feature selections and surrogate constraints.

It found:

- 7 candidate consequents where the stored R0.v1 consequent differed from the fitted weighted CART leaf class;
- 4 of those candidates were active in R0.v1;
- 0 path reconstruction mismatches;
- 0 mismatches between the stored artifact and the historical unweighted-majority implementation.

The four active mismatches are all stored as BENIGN while the fitted weighted CART leaf predicts ATTACK. Re-evaluating those same paths on the already-frozen development validation slice under the protocol-correct ATTACK consequent shows that all four fail the original class-precision and neural-fidelity gates. They therefore should not be active rules under the prospectively frozen System-B protocol.

This is an implementation defect, not a performance-driven redesign.

## 2. Governance decision frozen before corrected held-out evaluation

R0.v1 and its first evaluation remain immutable historical evidence.

A new rule base, **R0.v2**, will implement the original weighted-surrogate consequent semantics. If the R0.v2 build satisfies this plan, **R0.v2 will supersede R0.v1 for all future C/D initialization regardless of whether the eventual corrected System-B held-out metrics are better or worse than v1**.

This choice is made now, before R0.v2 exists and before any R0.v2 pre/post evaluation.

R0.v1 must never be deleted, rewritten, or presented as protocol-conformant.

## 3. Narrow correction scope

R0.v2 must preserve every System-B v1 design element not implicated by the defect:

- same five System-A checkpoints;
- same frozen preprocessing;
- same training rows;
- same deterministic 60/40 development split;
- same 12 selected features per seed, inherited exactly from R0.v1;
- no SHAP recomputation;
- same weighted DecisionTreeClassifier fit and constraints;
- same candidate tree paths;
- same support, precision, neural-fidelity, bootstrap-stability and complexity gates;
- same redundancy/conflict policy;
- same fusion-weight grid and tie breaks;
- same per-seed fused-threshold selection procedure;
- CPU / Python 3.11.9.

The only candidate semantic correction is:

`consequent = argmax(weighted CART leaf class mass)`.

Every candidate is then revalidated under that consequent.

## 4. Hard correction invariants

The R0.v2 build must abort if:

- source R0.v1 or the frozen audit hash differs;
- training/development row identities differ from R0.v1;
- a reconstructed path differs from the corresponding R0.v1 path;
- the set of changed consequents differs from the seven mismatches in the frozen audit;
- any unaffected active R0.v1 rule disappears or changes;
- any change beyond the audited consequent defect appears before fusion reselection;
- pre_drift or post_drift is loaded.

Development-only evidence predicts active counts of 7, 6, 7, 6, 6 after rejecting the four affected active paths. These counts are frozen as a build-integrity expectation, not as an outcome target.

## 5. Fusion and thresholds

Because rule coverage changes for seeds 1 and 3, R0.v1 lambda and fused thresholds are not automatically carried forward.

R0.v2 must re-run the **same frozen development-only fusion grid** and tie-break procedure. Whatever lambda and per-seed thresholds that procedure selects become the R0.v2 fusion identities.

No pre/post result may inform this selection.

## 6. Artifact/version policy

Expected new committed artifacts:

- `data/rules/system_b_r0_v2/seed_0.json` ... `seed_4.json`;
- `data/manifests/system_b_v2.json`.

The v2 manifest must hash-link:

- R0.v1 manifest identity;
- protocol-audit identity;
- preprocessing/System-A identities;
- training/development row identities;
- inherited feature selections;
- corrected candidate logs;
- accepted R0.v2 rules;
- development fusion grid and selected lambda/thresholds;
- runtime/build commit.

The v2 build must refuse overwrite.

## 7. Corrected B evaluation status

After R0.v2 is frozen, committed, verified and CI-accepted, a corrected System-B v2 pre/post evaluation is required so that the static B reference uses the same symbolic substrate later supplied to C/D.

That evaluation is **not described as an untouched first-look evaluation**, because System-B v1 held-out outcomes are historically known.

It is instead a deterministic implementation-defect correction whose rule/fusion identities were fixed from training/development evidence before the corrected run.

The first R0.v1 evaluation remains archived and reportable as historical defect evidence / sensitivity.

No choice between v1 and v2 may be made from their held-out performance.

## 8. Publication interpretation

For the manuscript:

- protocol-conformant System B = corrected v2;
- R0.v1 = preserved historical implementation-defect run;
- disclose discovery timing and the deterministic correction;
- report whether substantive conclusions are robust to v1 vs v2 where relevant;
- use R0.v2 as the common initial symbolic state for C and D.

This correction strengthens causal validity because C/D have not yet been executed.


## 9. Accepted correction outcome

R0.v2 was successfully generated under the correction contract.

- manifest canonical SHA-256: `131027d2f136494eb388183f18dcb7eb0e9d7e9fe786f22dba25f4e1624c1483`;
- artifact-freeze commit: `16cd22a448e43e598b03446b978fb762fbd42523`;
- active counts: 7/6/7/6/6;
- selected lambda: 0.50;
- thresholds: 0.692427396774292 / 0.9354645609855652 / 0.8299936652183533 / 0.9747405052185059 / 0.9527904391288757.

All hard correction invariants passed. The corrected B held-out evaluation remains unexecuted at this point.
