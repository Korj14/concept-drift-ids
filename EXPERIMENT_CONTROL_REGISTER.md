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
| System B symbolic state | Initial validated rule base `R_0`, static after activation | Training/development evidence only | Same `R_0` used to initialize C/D | **TO FREEZE before B evaluation** |
| Initial rule-extraction method | Must implement governing validated extraction/lifecycle contract | Training/development only | B/C/D initial `R_0` | **TO FREEZE** |
| SHAP/background/sample configuration | Exact explainer, background and sampling policy | Training/development only | B/C/D rule-generation contexts | **TO FREEZE** |
| Surrogate constraints | Feature count, tree depth, min support/leaf constraints | Development only | B/C/D | **TO FREEZE** |
| Fusion mechanism | Exact neural-symbolic fusion function/parameters | Development only | B/C/D; C/D identical | **TO FREEZE** |
| Rule validation thresholds | Support, class precision, fidelity, stability, complexity, overlap/conflict criteria | Development only | C/D operator identical | **TO FREEZE** |
| Symbolic conflict/abstention policy | Exact dominance/tie/abstention semantics | Development/design only | B/C/D reasoning | **TO FREEZE** |
| Longitudinal window size | TBD | Development/controlled design only | A/B/C/D | **TO FREEZE before longitudinal rescoring** |
| Window stride | TBD | Development/controlled design only | A/B/C/D | **TO FREEZE** |
| Transition handling | TBD | Development/controlled design only | A/B/C/D | **TO FREEZE** |
| Known synthetic boundary use | Scoring only; never supplied to detector/updaters | Governing doctrine | C/D and trigger ablations | **FROZEN rule** |
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
