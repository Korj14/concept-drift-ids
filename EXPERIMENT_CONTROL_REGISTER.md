# Experimental Control Register

**Authority:** `MAIN - Concept_Drift_NIDS_Research_Gap_Doctrine.docx` and `Reconciled_Pre-Stage_3_and_Stage_3_Implementation_Plan.docx`.

**Purpose:** make every high-leverage experimental variable explicit before it can become a hidden confound. Values marked **FROZEN** are not changed after their freeze gate without creating a new version and preserving the prior artifact/audit trail. Values marked **TO FREEZE** must be resolved using permitted development/design evidence before untouched adaptive evaluation.

| Variable / control | Current value or rule | Permitted selection evidence | Match requirement | Freeze state / gate |
| --- | --- | --- | --- | --- |
| Python runtime | 3.11.9 exactly | Project environment contract | All systems/runs | **FROZEN** |
| Dependency environment | `requirements-lock.txt` | Project environment contract | All systems/runs | **FROZEN** |
| Primary scenario | `cicids2017_sudden_benign_v1` | Frozen Stage-2 design | A/B/C/D | **FROZEN** |
| Scenario interpretation | Controlled synthetic source-regime covariate shift; pseudo-chronological; not natural production drift | MAIN / scenario manifest | All reporting | **FROZEN** |
| Feature space | Exact ordered 77-feature contract | Frozen preprocessing/scenario spec | A/B/C/D | **FROZEN** |
| Target | Binary BENIGN=0, retained attack=1; original multiclass label preserved as metadata | Frozen scenario contract | A/B/C/D | **FROZEN** |
| Duplicate/conflict policy | Retain primary rows/labels; no silent dedup or majority relabel | Stage-1/2 audit | A/B/C/D | **FROZEN** |
| Initial imputation | Median fit on frozen training only | Pre-Stage-3 decision | A/B/C/D | **FROZEN** |
| Initial scaling | StandardScaler fit on imputed frozen training only | Pre-Stage-3 decision | A/B/C/D | **FROZEN** |
| Preprocessing adaptation | None in primary experiment | Governing doctrine | C and D identical; separate sensitivity only | **FROZEN** |
| Preprocessing state | `sudden_benign_v1_preprocessing_v1.json`, core hash `4527f77220f2cf6063108a7d71d80aaa0e82099ad282ff25408a2d9ce3488b1e` | Stage-3A acceptance | A/B/C/D initial representation | **FROZEN** |
| System-A architecture | 77→128→64→1 MLP, ReLU, dropout 0.10 | Development-only protocol freeze | Baseline/start-state role | **FROZEN** |
| System-A training | BCEWithLogitsLoss; training-only class weight; Adam lr 0.001; wd 1e-5; batch 4096; max 20; patience 3 | Training + development only | Five System-A seeds | **FROZEN** |
| System-A seeds | 0,1,2,3,4 | Prospective protocol | Matched later starting states where applicable | **FROZEN** |
| System-A backend | CPU for all five primary seeds | Execution-consistency rule | Five System-A seeds | **FROZEN** |
| System-A threshold | Per-seed development-only MCC maximization with frozen tie breaks | Development only | Reused for frozen System-A evaluation | **FROZEN** |
| System-A manifest | `system_a_v1.json`, hash `42004b5ed100b690023b9998bdc959fac41ab947b996fb7c58e44cee5e8dc6de` | Five-seed completion | Reference checkpoint/threshold identity | **FROZEN** |
| System-A evaluation manifest | `results/frozen/system_a_v1/evaluation_manifest.json`, hash `e721b641b5898976c76c0449dedf7152cb302be4447604525afb7ddf1c94c5b3` | Untouched evaluation | Immutable reference evidence | **FROZEN** |
| System B seed-to-`R_0` mapping | One seed-specific `R_0^(s)` derived from the corresponding frozen System-A checkpoint; same seed-matched `R_0^(s)` initializes B/C/D | Governing design + training/development only | B/C/D within seed | **FROZEN — System-B protocol v1** |
| Exact System-B `R_0` artifacts | Five validated `R0.v1` seed-specific rule bases; manifest `system_b_v1.json` canonical hash `6e3589056d4c252c1a6c7cfd87b891fb8a24f1e30e86b17833b6035ea9ee86a8`; active counts 7/8/7/8/6 | Training + rule-validation development slice only | Same seed-matched hashes carried into C/D | **FROZEN — commit `245ca52371d7cdbcf8475b1d86b4b95d2b9850f5`** |
| Initial rule-extraction method | Training-only SHAP feature restriction -> weighted shallow tree mimicking frozen neural decisions -> canonical path rules -> independent development validation | Training + development under frozen firewall | B/C/D initial `R_0` | **FROZEN — System-B protocol v1** |
| SHAP/background/sample configuration | DeepExplainer on raw attack logit; training-only class-balanced background 256 (128/128) and attribution sample 2,048 (1,024/1,024); fixed row sample seed 20261007; top-12 feature policy | Training only | B/C/D initial extraction contract | **FROZEN — System-B protocol v1** |
| Surrogate constraints | DecisionTreeClassifier; neural-decision target using frozen System-A threshold; all training rows; equal-total-weight neural classes; 12 selected features; max_depth=4; min_samples_leaf=1000; random_state=seed | Training only under frozen protocol | B/C/D initial extraction contract | **FROZEN — System-B protocol v1** |
| Fusion mechanism | Confidence fusion on resolved covered cases; neural fallback when uncovered/conflict; global neural weight `lambda=0.50`; fused thresholds seed0=0.692427396774292, seed1=0.9235901534557343, seed2=0.8299936652183533, seed3=0.9747405052185059, seed4=0.9527904391288757 | Fusion-tuning development slice only under frozen grid/tie policy | B/C/D initial fusion; C/D identical | **FROZEN with `R0.v1`** |
| Rule validation thresholds | support>=0.001 and covered>=100; class precision>=0.80; neural fidelity>=0.90; bootstrap pass-persistence stability>=0.90 over 100 stratified replicates; complexity<=4; same-class redundancy overlap coefficient>=0.95; potential cross-class conflict>=0.50 | Rule-validation development slice only | Initial B and future operator semantics unless separately versioned | **FROZEN — System-B protocol v1** |
| System-B backend | CPU for build, validation, fusion tuning, verification, and primary B evaluation | Prospective execution-consistency rule | Five B seeds; initial C/D state provenance | **FROZEN — System-B protocol v1** |
| Symbolic conflict/abstention policy | Rule-level Pareto dominance only; unresolved opposite-consequent relations remain auditable; any runtime opposite-consequent coactivation causes symbolic abstention and neural fallback | Design + rule-validation development slice | B/C/D reasoning | **FROZEN — System-B protocol v1** |
| System-B untouched evaluation | Original first-run evaluation manifest `f44cad2ed9674bcb7118f05f174f845b5dfb135f95e2cb2b4a230f0f998c3e42`; executed from clean `245ca52371d7cdbcf8475b1d86b4b95d2b9850f5`; committed at `4542108f61e01348e69a19ee642e5c01abb97491` | Untouched pre/post under frozen R0.v1 | Immutable primary B evidence; additive supplement only | **FROZEN — do not rerun/overwrite** |
| Longitudinal reporting window size | 5,000 scenario rows; final remainder >=1,000 retained, remainder <1,000 merged backward | Controlled design only; frozen before B held-out outcomes | A/B/C/D | **FROZEN — System-B protocol v1** |
| Longitudinal reporting stride | 5,000 rows; non-overlapping | Controlled design only | A/B/C/D | **FROZEN — System-B protocol v1** |
| Longitudinal transition handling | Pre/post scoring partitions windowed separately; no reporting window crosses the synthetic boundary; order preserved; boundary remains scoring-only and is not detector input | Controlled design only | A/B/C/D | **FROZEN — System-B protocol v1** |
| Known synthetic boundary use | Scoring only; never supplied to detector/updaters | Governing doctrine | C/D and trigger ablations | **FROZEN rule** |

| Drift monitor signal | Exact statistic monitored by ADWIN/primary detector (e.g. delayed prediction error versus label-free stream statistic) | Development/design only | C/D and trigger comparison | **TO FREEZE BEFORE C/D** |
| Symbolic-validation label timing | Exact label availability/latency and mature-label rule for class precision | Deployment/design + development only | C/D evidence timing; D trigger variants | **TO FREEZE BEFORE C/D** |
| Adaptation evidence chronology | Time-respecting generation/validation construction and rule-publication time | Development/design only | C/D; D-drift/D-periodic operator identical | **TO FREEZE BEFORE C/D** |
| D rule-gate sample-size semantics | Effective support/count/uncertainty rule for actual adaptation-validation window | Development/design only; primary B unchanged | D-drift/D-periodic identical | **TO FREEZE BEFORE D** |
| C/D fused-threshold policy | Fixed B threshold or matched threshold-adaptation operator | Development/design only | C and D identical | **TO FREEZE BEFORE C/D** |
| Rule-confidence update policy | Evidence source/timing for q after evolution; treatment of unlabeled/pending evidence | Development/design only | D trigger variants identical; no future labels | **TO FREEZE BEFORE D** |
| Drift detector family/config | TBD | Development/controlled design only | C/D same confirmed-event policy | **TO FREEZE** |
| Drift persistence/confirmation | TBD | Development/controlled design only | C/D | **TO FREEZE** |
| Label availability/latency | TBD and must reflect stream-time availability | Development/design only | C/D identical | **TO FREEZE** |
| Adaptation-window construction | TBD | Development/controlled design only | C/D identical | **TO FREEZE** |
| Neural adaptation algorithm | TBD serious drift-aware update procedure | Development only | C/D identical | **TO FREEZE** |
| Neural update budget | TBD | Development only | C/D identical | **TO FREEZE** |
| Replay/buffer policy | TBD | Development only | C/D identical | **TO FREEZE** |
| Neural adaptation stopping rule | TBD | Development only | C/D identical | **TO FREEZE** |
| C symbolic treatment | Active `R_0` held frozen | MAIN | Treatment definition | **FROZEN** |
| D symbolic treatment | Same initial `R_0`, evolved `R_t` only after confirmed drift in primary condition | MAIN | Treatment definition | **FROZEN** |
| D-drift trigger | Confirmed statistical drift | MAIN | Compare with D-periodic | **FROZEN treatment definition** |
| D-periodic trigger | Prespecified periodic maintenance without detector consultation | MAIN | Same evolution operator; matched evidence/update opportunity | **TO FREEZE cadence/budget** |
| Optional D-continuous | Secondary only if feasible | Design decision before use | Same operator where meaningful | **NOT YET COMMITTED** |
| Primary C-vs-D comparison | Paired by seed/start state and all non-symbolic controls | MAIN | C/D | **FROZEN** |
| Computational backend for C/D | Same backend/configuration wherever feasible | Available hardware before runs | C/D paired blocks | **TO FREEZE** |
| Thread/determinism controls | Record and hold matched within causal blocks | Runtime environment | Matched systems | **TO FREEZE/record** |
| Primary inferential unit | Matched seed-level treatment effect within scenario; windows are longitudinal repeated observations, not independent replicates | Governing doctrine | Primary C-vs-D inference | **FROZEN principle** |
| Primary/secondary endpoints | Defined in `STATISTICAL_ANALYSIS_PLAN.md`; exact scenario-specific endpoint set frozen before C/D evaluation | Doctrine + development/design only | All final contrasts | **TO FREEZE before C/D** |
| Failed-run/exclusion policy | Technical failure only under prespecified criteria; retain original failure/reason | Statistical plan | All systems | **FROZEN principle** |
| Multiplicity handling | Must be prespecified before C/D | Statistical plan | Final confirmatory comparisons | **TO FREEZE** |
| Sensitivity analyses | Window/detector, duplicate/conflict policy where relevant, rule thresholds, other high-leverage choices | Prespecified only | Final robustness package | **TO FREEZE before untouched C/D** |
| Additional drift scenarios | Gradual + attack-pattern/real-concept-drift and unseen-attack where defensible | Governing design | Publication evidence | **REQUIRED later** |
| Second dataset | Required where feature/label semantics permit without artificial harmonization | Governing design | External validation | **REQUIRED if defensible** |
| Figure/table source | Immutable hash-linked JSON/CSV only; no hand-edited numerical summaries | Visualization policy | All reporting | **FROZEN rule** |
| Literature watch | Refresh adversarially at major milestones/submission/revision | MAIN | Novelty claims | **ONGOING** |

## Deviation rule

A deviation from a frozen row is not automatically prohibited, but it is never silent. Before the revised condition touches untouched evidence:

1. identify the scientific or technical reason;
2. state whether the change alters a treatment, confound, data access, or analysis choice;
3. create a new versioned protocol/artifact where applicable;
4. preserve the previous version and its hashes/results;
5. update this register, the methodology ledger, and the statistical-analysis plan if affected;
6. rerun matched conditions required to restore causal comparability.

A result being inconvenient is not a valid reason for deviation.

| System-B Q1 closure diagnostic | Training-only weighted CART leaf consequent reconstruction | Training only; no development/pre/post | Determines realized R0.v1 protocol conformance | **REQUIRED BEFORE C/D INHERITANCE** |
| System-B robustness plan | `SYSTEM_B_ROBUSTNESS_PLAN.md`; B post-hoc robustness, C/D prospective | Structural/literature audit; no C/D outcomes | Publication robustness | **FROZEN BEFORE C/D OUTCOMES** |
| Class-conditional symbolic reporting | Benign/attack coverage and correctness separately | Immutable B evidence; prospective C/D | B/C/D explanation reporting | **REQUIRED** |
| Thread/determinism controls for C/D | Record/freeze torch thread counts, threadpoolctl inventory and OMP/MKL/OpenBLAS settings | Runtime before C/D | Matched C/D blocks | **TO FREEZE BEFORE C/D** |


## System-B protocol-conformance correction controls — 7 October 2026

| Control | Frozen value / rule | Evidence permitted | Matching scope | Status |
|---|---|---|---|---|
| R0.v1 conformance status | Historical R0.v1 has 7 weighted-leaf consequent mismatches, 4 active; preserved unchanged | Frozen training-only audit | Historical B v1 only | **FROZEN NONCONFORMANT IMPLEMENTATION** |
| R0.v2 correction scope | Reuse exact v1 selected features/paths/gates; weighted CART leaf argmax consequent; revalidate; no SHAP recompute | Training + development only | Corrected B and future C/D initial state | **FROZEN BEFORE V2 BUILD** |
| R0.v2 unexpected-change rule | Any active-rule change beyond the four audited active mismatches aborts the build before fusion freeze | Training + development + frozen audit | V2 correction integrity | **FROZEN** |
| R0.v2 fusion | Re-run original lambda grid/tie breaks and fused threshold selection on same development fusion slice | Development fusion slice only | Corrected B / future C/D | **FROZEN PROCEDURE; VALUES TO FREEZE** |
| Future C/D initial symbolic state | Use accepted R0.v2, not R0.v1, once v2 manifest is frozen | Deterministic protocol correction; no C/D outcomes | C/D within seed | **FROZEN PRINCIPLE; HASH TO FREEZE** |
| Corrected System-B v2 evaluation | Required after committed/CI-accepted R0.v2; same pre/post scenario; cannot be described as first-look untouched | Frozen held-out partitions after v2 identity freeze | Corrected B static reference | **REQUIRED; NO RETUNING** |
| R0.v1 evaluation role | Preserve as first historical evaluation of nonconformant implementation; never delete/overwrite | Existing immutable evidence | Audit/sensitivity/provenance | **FROZEN** |


## Accepted R0.v2 identity — 7 October 2026

| Control | Frozen value / rule | Evidence permitted | Matching scope | Status |
|---|---|---|---|---|
| Exact accepted R0.v2 manifest | `data/manifests/system_b_v2.json`; canonical SHA-256 `131027d2f136494eb388183f18dcb7eb0e9d7e9fe786f22dba25f4e1624c1483` | Training + development under frozen correction plan | Corrected B; future C/D start | **FROZEN — commit `16cd22a448e43e598b03446b978fb762fbd42523`** |
| R0.v2 active rule counts | seed 0/1/2/3/4 = 7/6/7/6/6 | Development validation only | Corrected B; future C/D | **FROZEN** |
| R0.v2 fusion weight | neural weight lambda = 0.50, rank-1 mean development MCC under frozen grid | Development fusion slice only | Corrected B; future C/D | **FROZEN** |
| R0.v2 fused thresholds | seed0 0.692427396774292; seed1 0.9354645609855652; seed2 0.8299936652183533; seed3 0.9747405052185059; seed4 0.9527904391288757 | Development fusion slice only | Corrected B; future C/D initial operating point | **FROZEN** |


## Corrected System-B v2 evaluation controls — 7 October 2026

| Control | Frozen value / rule | Evidence permitted | Matching scope | Status |
|---|---|---|---|---|
| Corrected B-v2 evaluation status | Implementation-defect correction; explicitly not untouched first-look | Governance/provenance | Manuscript interpretation | **FROZEN** |
| Corrected B-v2 evaluation inputs | Accepted R0.v2 + same System-A checkpoints + frozen preprocessing + pre/post only | Pre/post after R0.v2 freeze | Corrected B static reference | **FROZEN** |
| Corrected B-v2 output path | `results/frozen/system_b_v2_corrected_v1/`; write-once | Evaluation only | Corrected B evidence | **FROZEN** |
| Corrected B-v2 explanation reporting | Overall + benign/attack resolved coverage, correctness and neural fidelity | Pre/post descriptive | B/C/D explanation standard | **FROZEN BEFORE V2 EVALUATION** |
| Corrected B-v2 imputation diagnostic | Per-rule imputed-antecedent activation and imputation-free quality; no preprocessing change | Raw pre-imputation X for diagnostic only | Explanation robustness | **FROZEN BEFORE V2 EVALUATION** |
| Corrected B-v2 timing | Single-pass neural descriptive timing; symbolic+fusion 1 warm-up + 5 exact-repeat timings; thread state recorded | Runtime only | Cost instrumentation convention | **FROZEN BEFORE V2 EVALUATION** |


## Accepted corrected System-B v2 evaluation identity — 7 October 2026

| Control | Frozen value / rule | Evidence permitted | Matching scope | Status |
|---|---|---|---|---|
| Corrected System-B v2 evaluation manifest | `results/frozen/system_b_v2_corrected_v1/evaluation_manifest.json`; canonical SHA-256 `583fa356c291bd7b2b275d726bb9eee31ae9aa5470cca50f0146c91642873710` | Frozen pre/post under accepted R0.v2 | Protocol-conformant B baseline evidence | **FROZEN — commit `03b7e52da3a24ebc2c28b26f8293bcbea2413ed3`** |
| Corrected B-v2 evidence status | Implementation-defect correction, not first-look untouched evidence | Provenance | Manuscript/statistical interpretation | **FROZEN** |
| Corrected B-v2 staleness transitions | 18 pass→pass; 7 fail→pass; 6 fail→fail; 1 pass→fail across 32 accepted rules | Frozen v2 evidence | RQ1 descriptive symbolic staleness | **FROZEN OBSERVATION** |
| Corrected B-v2 imputation diagnostic | 0/64 rule×partition records had imputed-antecedent activations | Frozen v2 evidence | Explanation robustness for this scenario | **FROZEN OBSERVATION** |


## Retrospective-assumption audit controls — 7 October 2026

| Control | Frozen value / rule | Evidence permitted | Matching scope | Status |
|---|---|---|---|---|
| Current MAIN source identity | `c3f1fed692ff0478c221925fca5c311380617a993e7ebf0021af2e05a362ab66` | Source document bytes | Future robustness + C/D | **FROZEN CURRENT AUTHORITY** |
| Current reconciled-plan identity | `05378ef14437f037bab0aa77853a16980b4fc60ac303398acc1cc293bdd32bdb` | Source document bytes | Future robustness + C/D | **FROZEN CURRENT AUTHORITY** |
| Historical A/B governing hashes | Preserve prior hashes already embedded in accepted manifests | Historical provenance only | Frozen A/B | **IMMUTABLE** |
| Restart trigger | Leakage, wrong frozen identity, treatment contamination, or realized protocol mismatch changing the scientific object | Audit evidence independent of favorable held-out performance | All stages | **FROZEN RULE** |
| Ordinary robustness dependence | Additive sensitivity; primary artifact remains immutable | Prespecified secondary analysis | A/B/C/D | **FROZEN RULE** |
| Controlled-shift attribution | `sudden_benign_v1` is BENIGN-source-regime-dominant, not attack-invariant | Scenario diagnostics | Interpretation | **FROZEN RULE** |
| Seen/unseen exact-pattern reporting | Reproduce Stage-2 exact-pattern dependence in repository and report fixed A/B on training-seen vs unseen held-out rows | Frozen models + held-out rescore only; no tuning | Publication-strength B | **REQUIRED BEFORE B ROBUSTNESS CLOSURE** |
| Stage-3A dtype conformance | Compare float64 symbolic-consumer contract with realized float32 B extraction using train/dev only before classifying as inert or defect | Training + development only | R0.v2 conformance | **REQUIRED FIRST** |


| Dtype audit decision rule | Version correction only for discrete float64-vs-float32 changes in topology/assignment, weighted consequent, gate decision or active candidate set; numerical threshold roundoff alone is additive provenance | Training + development only | R0.v2 conformance | **FROZEN BEFORE AUDIT EXECUTION** |


| Retrospective scenario audit | Exact-pattern dependence + BENIGN/GoldenEye feature-distribution diagnostics; write-once and post-hoc | Frozen training/development/pre/post; no model selection | Scenario attribution / publication robustness | **IMPLEMENTATION ADDED; ARTIFACT TO FREEZE** |


| A/B exact-pattern rescore | Frozen A checkpoints and accepted R0.v2; exact raw 77-feature training membership; seen/unseen strata only | Training for membership + pre/post fixed rescore; no development/tuning | Publication-strength B robustness | **IMPLEMENTATION ADDED; ARTIFACT TO FREEZE** |


| B selection robustness stage | Destination Port, SHAP aggregation, alternate dev splits, one-factor gates; freeze variant rules/lambda/thresholds before held-out robustness rescore | Training + development only | Publication-strength B robustness | **IMPLEMENTATION ADDED; EXECUTION BLOCKED UNTIL DTYPE AUDIT ACCEPTED** |


| Duplicate-aware B validation | Equal-weight exact feature-pattern validation + whole-pattern bootstrap; preserve within-pattern label contradictions | Development validation only | B rule-validity robustness | **IMPLEMENTATION ADDED; EXECUTION BLOCKED UNTIL DTYPE AUDIT ACCEPTED** |


| Pattern-deduplicated System-A teacher | Collapse exact raw 77-feature+binary-label multiplicities in training; preserve binary label conflicts; same A protocol and fixed preprocessor | Training + development only | Upstream duplicate-dependence robustness | **IMPLEMENTATION ADDED; MANIFEST TO FREEZE BEFORE DOWNSTREAM USE** |


| System-B fusion-authority sensitivity | Reuse accepted R0.v2; lambda in {0.70, 0.90, 1.00}; threshold selected on original development fusion slice under original MCC tie policy; held-out evaluation only after selection freeze | Development selection, then pre/post rescore | Publication-strength B robustness; informs future C/D fusion-policy risk | **IMPLEMENTATION ADDED; PRIMARY lambda=0.50 IMMUTABLE** |

| Pattern-deduplicated teacher R0 chain | Exact frozen alternate teacher manifest/checkpoints; reconstruct exact retained training rows; reuse frozen preprocessing, SHAP sample sizes/seeds, surrogate protocol, development split, validation gates, weighted CART consequents and fusion-selection procedure; no pre/post until R0 manifest is committed | Training + development only | Full upstream duplicate-dependence chain | **IMPLEMENTATION WIRED TO CLI; R0 MANIFEST MUST FREEZE BEFORE HELD-OUT RESCORE** |
