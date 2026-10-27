# Stage-10B Gradual BENIGN Source-Regime Replication Protocol v1

**Status:** PROSPECTIVELY FROZEN BEFORE ANY STAGE-10 TREATMENT OUTCOME  
**Protocol ID:** `stage10b-gradual-benign-source-v1`  
**Scenario ID:** `cicids2017_gradual_benign_source_v1`  
**Branch:** `stage10b-preoutcome-protocol`  
**Scientific role:** separate controlled gradual covariate/source-regime replication  
**Stage-10 treatment execution:** PROHIBITED UNTIL LEGITIMATE STAGE-9.5 CLOSURE  
**Historical Stage-8/9 evidence replaced:** no  
**Stage-10A frozen scenario/evidence replaced:** no

## 1. Authority, scope, and research question

This stage is subordinate to `MAIN - Concept_Drift_NIDS_Research_Gap_Doctrine.docx`,
`Reconciled_Pre-Stage_3_and_Stage_3_Implementation_Plan.docx`, and the
prospectively frozen `STAGE10_PLUS_MASTER_REPLICATION_SENSITIVITY_PROTOCOL_V1_1.md`.

The Stage-8 primary experiment used a controlled abrupt BENIGN source-regime
change; Stage-10A prospectively froze an attack-pattern/class-conditional
shift scenario. Stage-10B instead tests whether the same drift-gated, validated,
versioned symbolic lifecycle is useful when the controlled BENIGN source
transition is **gradual rather than abrupt**, compared with an otherwise matched
adaptive neural trajectory and frozen symbolic rule base.

This is a **designed gradual covariate/source-mixture shift** within the same
CICIDS2017 pseudo-chronology. It is not natural production drift, a proof that
`P(Y|X)` changed, an attack-pattern-evolution test, or a second environment.
Do not conflate the Stage-10A and Stage-10B external-validity questions.

## 2. Immutable scientific foundation

Keep historical training and development partitions, their information
firewalls, training-fitted 77-feature preprocessing, five System-A starting
checkpoints, R0.v2, initial thresholds, adaptive neural architecture, ADWIN
monitor semantics, label maturity, replay budget, symbolic operator, fusion
semantics, opportunity caps, paired-seed unit, and E1/E2/E3 definitions.

Inherited identity bindings:

- System-A manifest: `42004b5ed100b690023b9998bdc959fac41ab947b996fb7c58e44cee5e8dc6de`;
- preprocessing core state: `4527f77220f2cf6063108a7d71d80aaa0e82099ad282ff25408a2d9ce3488b1e`;
- R0.v2 manifest: `131027d2f136494eb388183f18dcb7eb0e9d7e9fe786f22dba25f4e1624c1483`;
- seeds: `0,1,2,3,4`;
- primary fusion lambda: `0.50`.

The original Stage-8/9 and Stage-10A controls are not retroactively modified.

## 3. Source identity and information partitions

The controlled composite uses exactly these original MachineLearningCSV files:

- `Wednesday-workingHours.pcap_ISCX.csv`; 225,166,395 bytes;
  SHA-256 `893c27dc968bf7a8adef1689f90be55ca4a4dc3088fb63d6ff247ac56856df2a`;
- `Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv`; 52,023,263 bytes;
  SHA-256 `d67066211fb1689c78406f1506f4c44704ecb92088353d5c96d96d6474eb819d`.

Historical training: Monday all, Tuesday all, Wednesday `[0,346352)`.
Historical development: Wednesday `[346352,554162)`.
Neither is refit, relabeled, rebalanced, or reselected.

Evaluation pre: Wednesday `[554162,623433)` with the original exclusion
of 11 Heartbleed rows; **69,260** rows = **65,671 BENIGN + 3,589 GoldenEye**.

Evaluation post: use Wednesday's `[623433,692703)` as the complete ordered
69,270-row **template**, with **65,697 BENIGN slots + 3,573 GoldenEye rows**.
Retain every GoldenEye row at its original template position. Never introduce
Thursday WebAttack rows into the evaluation stream. Only BENIGN template slots
may receive a Thursday BENIGN replacement.

Binary mapping: `BENIGN=0`, retained `DoS GoldenEye=1`; original multiclass
labels persist for source audit. Duplicate/conflict handling is inherited; no
future-informed deduplication, relabeling, or selective row removal.

## 4. Exact deterministic gradual transition

The evaluator-only start reference is **global stream index 69,260**.
The post template has local indices `t=0..69269`. Gradual ramp duration
`R=50000` post-template rows. Ramp completion is `t=50000`, at global
index **119,260**; remaining **19,270** post rows form the fully transitioned
plateau.

For a post-template row with local index `t`, define target replacement
probability:

`p(t) = min(1, (t + 0.5) / 50000)`.

Only for BENIGN slots, compute a deterministic pseudo-uniform score from
the original Wednesday source-row index `i`:

`u64(i) = unsigned big-endian integer from the first 8 bytes of
SHA256(UTF8("stage10b-gradual-benign-v1:slot:" + decimal(i)))`.

Replace a BENIGN slot iff `t>=50000` or
`100000 * u64(i) < (2*t + 1) * 2^64`.
All arithmetic in this comparison is unbounded integer arithmetic; do
not use floating-point threshold comparisons, Python randomized `hash()`,
or a treatment-seed-specific RNG. Thus a slot's assignment is fixed before
any C/D run, the same for all arms/seeds, and exactly reproducible.

Thursday replacement candidates are the **same pre-frozen source mapping**
as the Stage-8 abrupt scenario:

1. Enumerate all **168,186** Thursday-morning BENIGN source-row indices
   in ascending original source order.
2. Enumerate **65,697** Wednesday post BENIGN template slots in ascending
   original source-row order. For zero-based BENIGN-slot ordinal `j`, choose
   Thursday eligible-row ordinal `floor(j * 168186 / 65697)`.
3. For each eligible slot, keep Wednesday bytes if the gradual assignment is
   false, otherwise use the corresponding already-selected Thursday BENIGN
   source feature values and its source identity, preserving the template
   clock/index and target.
4. GoldenEye template rows are never replaced.

The replacement schedule uses no neural prediction, drift alarm,
C/D outcome, explanation, or symbolic-rule feedback.

## 5. Frozen source-only construction checks

An independently performed **non-treatment** raw-file audit yielded:

- 65,697 eligible post BENIGN slots;
- **41,935** Thursday-BENIGN replacements;
- **23,762** original Wednesday BENIGN slots retained;
- **23,661** replacements during the 50,000-row ramp;
- **18,274** replacements in the 19,270-row plateau;
- all 3,573 post GoldenEye rows retained;
- exactly 69,260 pre and 69,270 post stream rows;
- unchanged post GoldenEye prevalence 3,573/69,270.

Key frozen SHA-256 identities (ordered int64 little-endian unless noted):

- pre included Wednesday row IDs:
  `ef7773f88374c82a663723c0c1125f4a8bfee75a58fe4d8e35355b492e07b354`;
- post template Wednesday row IDs:
  `186aec7f816faca89484c537b77ed8e729a9ac55982a7e1bec6f37750c1c30d8`;
- post BENIGN template slot IDs:
  `e393262d5ba7f02dd167aee8575e4980fa108b9471cef8034bb069a1340f5527`;
- all 65,697 candidate Thursday source-row IDs:
  `2ab5636a81923eae27faa0eac8de4dd8b55af9fb991bf0ddfdf5419e69c017c9`;
- selected 41,935 replaced Wednesday slot IDs:
  `9e38380ee80f3341883cd378dcacfc49d60f50feaba0d3798905f67238aa2e10`;
- selected 41,935 Thursday replacement source-row IDs:
  `927f09c807b6897353c26e0dec60f1f683595b9ff853eef6acdf439f54e3574a`;
- ordered replacement `(Wednesday_slot, Thursday_row)` pairs:
  `5c0649649b6b3ee3c8e04476272a6292616078cf579fc4735c8a898bafc985b4`;
- post BENIGN-slot replacement mask, `numpy.packbits(bitorder="little")`
  SHA-256: `145afea0b0b467698d7d9871d6cb40ca5731c75ae7bf8e6f132458f5eefe7513`.

The frozen window tallies in
`data/manifests/stage10b_gradual_benign_source_audit_v1.json`
verify that the observed replacement fraction rises through the successive
5,000-row post windows, approaching 0.95 in the last ramp window, and is
exactly 1.0 in the plateau. The source-only blended BENIGN pre/post
77-feature KS mean was 0.09832, max 0.21163, with 46/77 features >=0.10.
These measurements characterize the constructed input, **not** treatment
performance, adaptation recovery, or detector power.

## 6. Chronology, leakage, and boundary semantics

The Wednesday and Thursday input tables lack usable true timestamps under
the accepted MachineLearningCSV contract. This scenario is explicitly
pseudo-chronological and synthetically source-mixed. The replacement features
can originate from a later collection day; this is an explicitly offline,
controlled exogenous input stream, **not** a natural sequential observation
history. The predefined source mixture is constructed by an evaluator before
treatment and only the mixed feature/label row is presented at its logical
clock. The underlying source regime flag, original source-row IDs, assignment
probability, and evaluator-only ramp start/end may be used for provenance
and post-freeze diagnostics, but not for model prediction, ADWIN, shared
neural adaptation, replay selection, candidate generation, symbolic
validation, or rule publication.

The primary monitor consumes delayed neural-only errors, not boundary
positions or symbolic/fused outputs. Labels mature after the frozen
5,000-row latency and only after their own predictions are committed.
No resets, flushes, or reinitialization at ramp start or completion.
No source-domain-aware adaptive policy is introduced.

## 7. Matched treatments and clocks

The primary arms remain:

- `C`: adaptive neural trajectory + frozen R0.v2 symbolic authority;
- `D-drift`: exactly matched neural trajectory + drift-gated symbolic lifecycle;
- `D-periodic`: matched neural update/control-plane policy + periodic symbolic
  maintenance using the same operator and opportunity budget.

Within each seed, C/D must share the same initial weights, preprocessing,
delayed-label event stream, ADWIN neural-event trajectory, replay row identities,
neural updates/checkpoint hashes, and all non-symbolic states. D-drift versus
D-periodic may differ only by its prospectively frozen maintenance schedule
and consequent symbolic-state trajectory.

Primary inherited parameter values: ADWIN delta 0.002 and clock 32;
5,000-row label maturity; 10,000 current-evidence and replay capacities;
5,000 anchor + 5,000 online update sample; neural Adam lr 1e-4, weight
decay 1e-5, batch 1,024, five epochs; symbolic generation and subsequent
separate mature validation each 10,000; maximum four symbolic opportunities;
lambda 0.50 and accepted seed-specific fusion thresholds.

The original comparator clock/budget policy is not selected from Stage-10B
outcomes. Claims of trigger-specific superiority require the separately frozen
future comparator-clock sensitivity.

## 8. Frozen inferential family and reporting

Five paired seeds `0..4` remain the causal replication unit. No post-view
seed extension, favorable-seed deletion, or window/rule/event/bootstrap
pseudo-replication.

Carry the accepted primary E1/E2/E3 definitions prospectively:

- **E1:** D-drift minus C, post-regime MCC;
- **E2:** D-drift minus C, post-regime MCSC;
- **E3:** D-drift minus D-periodic, post-regime MCSC.

`post-regime` includes the **entire** 69,270-row gradual-ramp-plus-plateau
portion, not whichever subperiod is favorable. Report the five paired
effects, means/SD, 95% paired-seed t intervals, directional sign tests,
and the inherited familywise Holm correction without replacing a
failed endpoint or redefining multiplicity post hoc.

Required descriptive secondary outputs: separated ramp (indices
`[69260,119260)`) and plateau (`[119260,138530)`) trajectories,
pre and post confusion/recall/FPR/FNR/AP/Brier where defined, symbolic
coverage/correctness and rule authority changes, MCSC components,
detector events/timing, zero-opportunity/no-alarm cases, cost/budgets,
information-time violations, model-state equality and explanation
longitudinal stability. Ramp-specific and plateau-specific effects are
secondary; they do **not** silently become confirmatory E1/E2/E3.

No cross-scenario pooling with Stage-8 primary or Stage-10A without a
prospectively justified common estimand. Preserve null, mixed and
unfavorable results.

## 9. Invalid runs, implementation status, and stop rules

Retain write-once failure evidence. Class-A defects include provenance or
source mapping mismatch; treatment-dependent source assignment; wrong
checkpoint/R0/threshold/preprocessing/label; premature label release;
unmatched neural path; boundary leakage; future-informed change;
generation/validation overlap; missing seed; incorrect primary score;
or changed post-period estimand. Any such run is invalid until a
prospectively controlled correction is versioned; unfavorable metrics
alone never invalidate a run.

A source-only preflight pass is **not** an executed adaptive scenario or a
proof of runtime-loader equivalence. New Stage-10B scenario loader/adapter,
end-to-end matched-state verifier, run-config freeze, execution exact-head
governance and artifact-output policy must be independently verified
before any later treatment run, after Stage-9.5 closes.

## 10. Hard execution firewall and next action

Until Stage-9.5 legitimately closes (including the required independent
reconstruction and historical replay/hostile review), Stage-10B permits
only source-only construction, protocol, repository tests, and
pre-treatment static assurance. It prohibits generating or viewing any
Stage-10B C/D/D-periodic prediction, neural adaptation trace, rule
lifecycle result, or treatment performance.

The corresponding verifier must always set
`stage10_treatment_outcomes_accessed=false` and
`stage10_treatment_execution_authorized=false`. Passing verification
never unlocks Stage 10.

This protocol's scenario choice and deterministic transition were frozen
using source-only scientific compatibility, not treatment success. A
failure to support a broad claim narrows the research conclusion instead
of restarting or substituting a favorable scenario.
