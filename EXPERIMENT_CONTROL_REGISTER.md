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
| Primary C/D drift-event provenance | One treatment-independent shared control-plane event stream per seed; primary event = River 0.26.1 ADWIN detection on delayed neural-only hard-error stream; detector input/state cannot depend on D symbolic state or C/D fused outputs | Adversarial audit + prospective detector protocol | C and D neural adaptation; D-drift symbolic trigger | **FROZEN — `C_D_DRIFT_MONITOR_PROTOCOL.md`** |
| Primary C/D evidence acquisition | Neural current evidence = most recent 10,000 mature parent-checkpoint observations; replay = fixed 10,000-row budget; D candidate generation uses that 10,000-row neural-current window; D acceptance/lifecycle uses a separate future 10,000-row child-checkpoint-pure mature validation block | `C_D_NEURAL_ADAPTATION_PROTOCOL.md` + `D_SYMBOLIC_LIFECYCLE_PROTOCOL.md` | C/D neural path identical; D symbolic evidence time-respecting | **FROZEN** |
| Primary C/D non-symbolic state equality | Detector events, replay/buffer row identities, neural update row identities/budgets, neural checkpoint hashes, and shared threshold state where applicable must be mechanically identical within matched seed blocks | Adversarial causal audit | C vs D | **FROZEN CAUSAL PRINCIPLE — verifier TO IMPLEMENT AFTER PROTOCOL FREEZE** |
| Treatment-contamination abort rule | Any unexplained divergence in required matched non-symbolic state invalidates the paired C-vs-D run; preserve failure and do not silently continue | Adversarial causal audit | Primary C vs D | **FROZEN PRINCIPLE** |
| Alert-conditioned adaptation in primary C/D | Prohibited: fused/symbolic alerts may not determine labels, replay, neural adaptation, or evidence availability in the primary causal contrast | Adversarial causal audit | Primary C vs D | **FROZEN PRINCIPLE; separate future treatment only** |
| Independent fused-score threshold adaptation | Prohibited in primary C-vs-D; primary lambda and fused threshold remain fixed through the stream; no per-arm/per-window recalibration | Adversarial audit + `C_D_FUSION_THRESHOLD_PROTOCOL.md` | Primary C vs D | **FROZEN** |

| Drift monitor signal | Primary e_j = 1[stored neural decision at frozen seed-specific System-A monitor threshold != mature y_j]; fixed monitor thresholds throughout stream; original stored prediction only; no fused/symbolic input. Robustness: ADWIN on delayed Brier loss | Accepted A development thresholds + prospective timing/causal design | Shared C/D control plane; D trigger comparison | **FROZEN — `C_D_DRIFT_MONITOR_PROTOCOL.md`** |
| Symbolic-validation label timing | Primary fixed verification latency L=5,000 rows; label released only after prediction at maturity index j+L; pending labels cannot enter class precision or other label-dependent validation | Prospective timing design; no C/D outcomes | C/D evidence timing; D trigger variants | **FROZEN — `C_D_STREAM_TIME_CONTRACT.md`** |
| Adaptation evidence chronology | Prediction -> label release -> detector event -> shared neural update -> child publication -> candidate generation from prior 10k neural-current evidence -> separate 10k child-checkpoint-pure future validation -> staleness/candidate lifecycle resolution -> symbolic publication next logical row; no future/pending-label lookahead | Prospective timing/lifecycle design | C/D neural path shared; D trigger variants use same operator | **FROZEN** |
| D rule-gate sample-size semantics | Online validation N=10,000; support>=.001; covered>=25; point precision>=.80 and one-sided 95% Wilson LCB>=.80; point fidelity>=.90 and Wilson LCB>=.90; 100-replicate stratified full-gate persistence>=.90; complexity<=4 | Prospective uncertainty design; static B unchanged | D-drift/D-periodic identical | **FROZEN — `D_SYMBOLIC_LIFECYCLE_PROTOCOL.md`** |
| D candidate-generation evidence | Exact 10,000-row neural current-evidence window that produced child checkpoint; candidate generation may reuse it but acceptance may not | Prospective lifecycle design | D trigger variants same operator/evidence budget | **FROZEN** |
| D symbolic validation evidence | First 10,000 future rows predicted by child checkpoint whose labels mature while child remains active; chronological; both classes required; no random split from generation evidence | Prospective lifecycle design | D trigger variants matched | **FROZEN** |
| D validation supersession rule | If child checkpoint is superseded before full symbolic validation matures, transaction closes `superseded_before_validation`; no partial rule publication | Causal model-version purity | D | **FROZEN** |
| D online SHAP | DeepExplainer raw attack logit; balanced background up to 128/class; attribution up to 1024/class; at least 128/class required; top-12 same normalized score family as R0 | Preserve extraction family without synthetic oversampling | D operator | **FROZEN** |
| D online surrogate | Weighted CART leaf consequent; gini/best; max_depth=4; min_samples_leaf=100; equal-total neural decision weights; target child neural decision at frozen System-A neural threshold | Preserve R0 family + online proposal granularity | D operator | **FROZEN** |
| D rule confidence | Refresh only at completed symbolic maintenance opportunity from independent validation; confidence=min(point class precision, point neural fidelity); constant between publications; no per-row decay | Prospective lifecycle design | D only; C R0.v2 confidence frozen | **FROZEN** |
| D incumbent staleness transition | Active pass->retained; first completed fail->demoted/inactive; second consecutive completed fail->retired; demoted/retired exact semantic rule may reactivate on later full-gate pass | Prospective lifecycle design | D operator | **FROZEN** |
| D same-class lifecycle relation | overlap>=.95 => deterministic merge/consolidation; overlap [.50,.95) => refinement only if candidate Pareto-dominates or incumbent is stale; overlap<.50 => new addition | Reuse accepted overlap scales; lifecycle doctrine | D operator | **FROZEN** |
| D cross-class lifecycle relation | opposite consequent overlap>=.50; Pareto domination rejects/demotes loser; unresolved relation remains active but runtime coactivation abstains to neural fallback | Preserve accepted R0 conflict semantics | D operator | **FROZEN** |
| D symbolic versioning | Immutable maintenance event every opportunity; new rule-base version only for inference-relevant symbolic state change; write-once parent-hash chain, rule revisions, lineage, rejected-change evidence | Lifecycle/governance doctrine | D | **FROZEN PRINCIPLE** |
| Symbolic recovery claim | Requires documented valid->stale/demoted->accepted refinement/reactivation/replacement->post-publication explanation improvement chain; new addition alone is not recovery | Governing doctrine | Manuscript/evaluation | **FROZEN CLAIM RULE** |
| C/D fused-threshold policy | Primary lambda=.50 and accepted R0.v2 per-seed thresholds fixed across all neural checkpoints/D rule versions; sensitivities lambda=.70/.90 with accepted dev-grid thresholds; lambda=1.0 neural-only negative control | Accepted R0.v2 development grid only; no C/D outcomes | C/D same lambda/threshold within seed | **FROZEN — `C_D_FUSION_THRESHOLD_PROTOCOL.md`** |
| Primary C/D fusion weight | lambda=.50 on resolved symbolic coverage; neural fallback when uncovered/conflict; no online lambda adaptation | Accepted R0.v2 | C/D identical | **FROZEN** |
| Primary R0.v2 fused thresholds | seed0=.692427396774292; seed1=.9354645609855652; seed2=.8299936652183533; seed3=.9747405052185059; seed4=.9527904391288757 | Accepted R0.v2 dev-only fusion selection | C/D identical within seed | **FROZEN** |
| Fusion-authority sensitivity | lambda=.70 and .90 using already accepted R0.v2 development-grid thresholds; cannot replace primary based on outcome | Accepted R0.v2 dev grid | C/D matched | **FROZEN SECONDARY** |
| lambda=1 causal negative control | Symbolic predictive authority zero; C/D fused scores and thresholded predictions must be identical for matched seed/rows; any predictive difference = implementation defect | Causal design + accepted dev-grid threshold | C/D | **FROZEN NEGATIVE CONTROL** |
| Rule-confidence update policy | D confidence refresh only at completed independent symbolic validation; q=min(point class precision, point neural fidelity); constant between publications; no pending-label/per-row/decay update; C R0.v2 confidence permanently frozen | `D_SYMBOLIC_LIFECYCLE_PROTOCOL.md` | D trigger variants identical | **FROZEN** |
| Drift detector family/config | Primary `river.drift.ADWIN` under river==0.26.1 with delta=.002, clock=32, max_buckets=5, min_window_length=5, grace_period=10; no held-out tuning. Detector-family robustness: default River PageHinkley | Prospective design + locked dependency + literature; no adaptive held-out outcomes | One shared detector/control-plane trajectory per seed | **FROZEN — `C_D_DRIFT_MONITOR_PROTOCOL.md`** |
| Drift persistence/confirmation | One ADWIN `drift_detected=True` = confirmed event; event closes epoch; detector disarmed through fixed neural response transaction; re-arm only on mature errors generated by published child checkpoint; no arbitrary cooldown | `C_D_DRIFT_MONITOR_PROTOCOL.md` + `C_D_NEURAL_ADAPTATION_PROTOCOL.md` | Shared C/D control plane | **FROZEN** |
| Detector monitor thresholds | Fixed accepted System-A development thresholds per seed: 0=.939024031162262; 1=.9333740472793579; 2=.9121250510215759; 3=.9789621233940125; 4=.954619288444519; never adapted for primary monitor | Accepted System-A development-only freeze | Shared control plane; independent of C/D fused threshold policy | **FROZEN** |
| Detector initialization | Fresh ADWIN per seed; no training/development preload; no boundary initialization; supervised inputs begin only as labels mature | Prospective detector design | Shared control plane | **FROZEN** |
| Detector checkpoint-purity rule | Each armed detector epoch admits only errors whose stored prediction was produced by that epoch's neural checkpoint; delayed old-checkpoint errors after a new publication are logged but excluded from the new detector epoch | Information-time audit | Shared control plane | **FROZEN** |
| Detector trigger-quality scoring | Boundary used only after event log freeze; report pre-reference alarms, first post-boundary event, end-to-end delay, latency-adjusted descriptive excess delay, repeated events, counts/inter-event spacing, epoch input counts, blind duration and suppressed stale-error counts | Prospective analysis design | Primary and detector sensitivities | **FROZEN** |
| Label availability/latency | Primary L=5,000 ordered stream rows; complete eventual supervision subject to delay and terminal right-censoring; no alert-conditioned acquisition; sensitivities L=0 and L=10,000 | Prospective design + scenario chronology constraint | C/D identical; D trigger variants identical | **FROZEN — `C_D_STREAM_TIME_CONTRACT.md`** |
| Primary adaptive stream clock | Zero-based ordered row index over uninterrupted pre_drift -> post_drift concatenation; no wall-clock chronology claim | Frozen scenario manifest + prospective timing design | C/D and trigger variants | **FROZEN** |
| Synthetic-boundary state handling | No detector/label-queue/buffer/model/rule/RNG reset or flush at evaluator-known boundary | Causal-isolation audit | C/D and trigger variants | **FROZEN** |
| Prediction/label order | Test-then-update: prediction is committed before any labels mature at that logical clock; L=0 sensitivity still releases label only after its prediction | Prospective timing design | C/D and trigger variants | **FROZEN** |
| Adaptive vs evaluation label channels | Adaptive components see labels only at maturity; offline scorer may use all labels only after predictions are frozen; evaluation labels never feed the running state early | Prospective timing design | All adaptive systems | **FROZEN** |
| End-of-stream pending labels | No adaptive queue flush and no terminal update that cannot affect a later primary-stream prediction; pending labels retained as censored evidence | Prospective timing design | C/D and trigger variants | **FROZEN** |
| Update execution semantics | Synchronous logical stream; maintenance runs between predictions and new state is effective next logical row at earliest; wall-clock cost reported separately, no production-throughput claim | Scenario lacks trustworthy timestamps | C/D and trigger variants | **FROZEN** |
| Adaptation-window construction | 10,000 most recent mature labeled observations whose stored prediction used the parent neural checkpoint; if fewer exist at event, detector remains disarmed and parent stays active until budget matures; no shrinking; terminal shortfall is right-censored | Prospective design under frozen timing/detector contracts | Shared C/D control plane | **FROZEN — `C_D_NEURAL_ADAPTATION_PROTOCOL.md`** |
| Neural adaptation algorithm | Shared fixed-budget experience-replay fine-tuning of all MLP parameters; one physical child checkpoint produced once per seed/event and referenced by both C and D | Prospective design + current continual-NIDS evidence | C/D literally share checkpoint bytes/hash | **FROZEN** |
| Neural update budget | Current 10,000 + replay 10,000 = 20,000 rows; Adam lr=1e-4, wd=1e-5, batch=1024, exactly 5 epochs, no scheduler/early stopping; fixed original pos_weight=4.138247558496975 | Prospective conservative adaptation design; no C/D outcomes | Shared C/D control plane | **FROZEN** |
| Replay/buffer policy | Dual uniform memory: immutable 10,000-row training anchor (seed 20261008) + 10,000-row mature-stream reservoir (seed 20261009); each update replays 5,000 anchor + 5,000 eligible online rows, excluding current-window IDs; deficit filled from anchor | Prospective replay design; no error/rule/class-conditioned admission | Shared C/D control plane | **FROZEN** |
| Neural adaptation stopping rule | Exactly 5 epochs; no performance-based early stopping or publish gate; finite protocol-conformant child checkpoint always published, harmful update retained as evidence | Prospective causal design | Shared C/D control plane | **FROZEN** |
| Neural optimizer-state policy | Fresh Adam state each event; no carryover of historical or prior-event moments | Frozen System-A checkpoint lacks deployable optimizer continuation; reproducibility | Shared C/D | **FROZEN** |
| Neural replay/current ratio | 1:1 by row count (10,000 current + 10,000 replay) | Prospective stability/plasticity design | Shared C/D | **FROZEN** |
| Neural adaptation RNG | anchor seed 20261008; online reservoir seed 20261009; replay sample seed=20261010+event_id; training shuffle seed=20261011+1000*seed+event_id; CPU deterministic controls | Prospective reproducibility design | Shared C/D; checkpoint replayability | **FROZEN** |
| Neural publication identity | Child checkpoint records parent hash, event/evidence hashes, config/RNG, losses, child SHA; publication effective next logical row at earliest; C/D reference same artifact | Causal-isolation audit | Shared C/D | **FROZEN PRINCIPLE** |
| Neural retention diagnostics | Whole development partition diagnostic after each checkpoint; pre-drift checkpoint rescoring only offline after adaptive trajectory freeze; never used for update/publish decisions | Prospective forgetting evaluation | Shared trajectory | **FROZEN** |
| Neural no-replay ablation | Same current window and optimizer/update budget but omit replay; secondary only, cannot replace primary based on held-out direction | Prospective robustness | Separate neural adaptation ablation | **FROZEN SECONDARY** |
| C symbolic treatment | Active `R_0` held frozen | MAIN | Treatment definition | **FROZEN** |
| D symbolic treatment | Same initial `R_0`, evolved `R_t` only after confirmed drift in primary condition | MAIN | Treatment definition | **FROZEN** |
| D-drift trigger | Confirmed statistical drift | MAIN | Compare with D-periodic | **FROZEN treatment definition** |
| D-periodic trigger | Four fixed symbolic opportunity clocks per seed: 27,706; 55,412; 83,118; 110,824 (floor(i*N/5), N=138,530); schedule never consults detector/boundary | `D_TRIGGER_ABLATION_PROTOCOL.md` | Same symbolic operator/config hash/evidence budget as D-drift | **FROZEN** |
| Symbolic opportunity budget | K_symbolic=4 maximum opportunities per seed per trigger arm; every triggered/scheduled slot consumes budget regardless publication/no-op/censoring; no retries beyond slot budget | Prospective fair-trigger design | D-drift/D-periodic same maximum intervention budget | **FROZEN** |
| D-drift symbolic slots | First four confirmed primary detector events consume symbolic slots; later detector events may still update shared neural state but symbolic maintenance logs `symbolic_budget_exhausted` | Trigger-ablation design | D-drift | **FROZEN** |
| D-periodic evidence at target | Most recent 10,000 mature rows at target clock for generation; current shared neural checkpoint applied to them; same 10,000 future checkpoint-pure validation contract as D-drift | Trigger-ablation design | D-periodic | **FROZEN** |
| Trigger-arm operator identity | D-drift/D-periodic call same symbolic operator with identical config hash and RNG namespace by seed/opportunity; only opportunity timing/source differs | Causal trigger ablation | D trigger arms | **FROZEN** |
| Trigger opportunity outcome taxonomy | opportunity / completed_validation / publication / no_op / censored_or_aborted kept distinct; opportunity count must not be equated with update count | Trigger-efficiency analysis | D trigger arms | **FROZEN** |
| Concurrent symbolic transaction policy | At most one outstanding symbolic transaction per seed/arm; periodic target while pending logs `pending_transaction_skip` and consumes slot; neural supersession aborts checkpoint-tied validation | Lifecycle/trigger design | D trigger arms | **FROZEN** |
| Optional D-continuous | Secondary only if feasible | Design decision before use | Same operator where meaningful | **NOT YET COMMITTED** |
| Primary C-vs-D comparison | Paired by seed/start state and all non-symbolic controls | MAIN | C/D | **FROZEN** |
| Computational backend for C/D | CPU-only primary adaptive execution under Python 3.11.9 and frozen requirements | `C_D_FINAL_ANALYSIS_REPRODUCIBILITY_PROTOCOL.md` | Shared control plane and all primary arms | **FROZEN** |
| Thread/determinism controls | PYTHONHASHSEED=0; OMP/MKL/OpenBLAS/NumExpr threads=1; torch intra/inter-op threads=1; deterministic algorithms; DataLoader workers=0; threadpoolctl inventory recorded/fail-closed | Final reproducibility protocol | All primary adaptive runs | **FROZEN** |
| Primary inferential unit | Matched seed-level treatment effect within scenario; windows are longitudinal repeated observations, not independent replicates | Governing doctrine | Primary C-vs-D inference | **FROZEN principle** |
| Primary/secondary endpoints | Confirmatory E1 post MCC D-drift-C; E2 post MCSC D-drift-C; E3 post MCSC D-drift-D-periodic. Remaining detection/explanation/trigger/cost metrics secondary | SAP v1.0 + final reproducibility protocol | All primary contrasts | **FROZEN** |
| Failed-run/exclusion policy | Technical failure only under prespecified criteria; retain original failure/reason | Statistical plan | All systems | **FROZEN principle** |
| Multiplicity handling | Three confirmatory one-sided exact sign tests form one family; Holm-Bonferroni FWER .05; effect magnitude/raw pairs remain primary evidentiary emphasis | SAP v1.0 | E1-E3 | **FROZEN** |
| Primary paired effect estimate | Arithmetic mean of five matched seed differences; retain all raw pairs, median, SD, min/max, sign pattern, leave-one-seed-out mean range | SAP v1.0 | E1-E3 | **FROZEN** |
| Primary paired interval | 95% Student-t interval over five paired differences, df=4; conditional stochastic-seed uncertainty only; raw values mandatory; no bootstrap primary | SAP v1.0 | E1-E3 | **FROZEN** |
| Confirmatory sign test | Exact one-sided binomial sign test for positive paired effect; zero ties excluded from n_effective; secondary calibration, not sole success criterion | SAP v1.0 | E1-E3 | **FROZEN** |
| Recovery definition | Baseline=row-weighted mean final three pre windows; first two consecutive post windows meeting/exceeding baseline (reverse for lower-is-better); otherwise right-censored | SAP v1.0 | Secondary longitudinal outcomes | **FROZEN** |
| MCSC definition | 0.5*(benign correct symbolic coverage + attack correct symbolic coverage); unresolved/uncovered/wrong symbolic rows contribute zero; components reported separately | Final analysis protocol | E2/E3 | **FROZEN** |
| Sensitivity analyses | L=0/10k; Page-Hinkley; ADWIN-Brier; no-replay; lambda=.70/.90/1.0; 2.5k/10k reporting windows; static-style symbolic gate; later attack-pattern scenario/second dataset for external validity | Prespecified only; no primary-outcome selection | Robustness package | **FROZEN SET** |
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
| Thread/determinism controls for C/D | Exact single-thread CPU environment and deterministic PyTorch controls per final reproducibility protocol; threadpoolctl inventory mandatory | Runtime contract before execution | Matched C/D blocks | **FROZEN** |


## System-B protocol-conformance correction controls — 7 October 2026

| Control | Frozen value / rule | Evidence permitted | Matching scope | Status |
|---|---|---|---|---|
| R0.v1 conformance status | Historical R0.v1 has 7 weighted-leaf consequent mismatches, 4 active; preserved unchanged | Frozen training-only audit | Historical B v1 only | **FROZEN NONCONFORMANT IMPLEMENTATION** |
| R0.v2 correction scope | Reuse exact v1 selected features/paths/gates; weighted CART leaf argmax consequent; revalidate; no SHAP recompute | Training + development only | Corrected B and future C/D initial state | **FROZEN BEFORE V2 BUILD** |
| R0.v2 unexpected-change rule | Any active-rule change beyond the four audited active mismatches aborts the build before fusion freeze | Training + development + frozen audit | V2 correction integrity | **FROZEN** |
| R0.v2 fusion | Accepted lambda=.50 with seed thresholds 0=.692427396774292; 1=.9354645609855652; 2=.8299936652183533; 3=.9747405052185059; 4=.9527904391288757 | Accepted R0.v2 development fusion evidence | Corrected B / future C/D | **FROZEN VALUES** |
| Future C/D initial symbolic state | Accepted seed-matched R0.v2 only; manifest canonical SHA `131027d2f136494eb388183f18dcb7eb0e9d7e9fe786f22dba25f4e1624c1483` | Accepted corrected System-B milestone | C/D within seed | **FROZEN BY MANIFEST HASH** |
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


| Retrospective scenario audit | Exact-pattern dependence + BENIGN/GoldenEye feature-distribution diagnostics; write-once/post-hoc robustness evidence completed and retained | Frozen evidence only; no model selection | Scenario attribution / publication robustness | **FROZEN COMPLETED ROBUSTNESS** |


| A/B exact-pattern rescore | Frozen A checkpoints and accepted R0.v2; exact raw 77-feature training membership; seen/unseen strata only; completed as additive robustness | Training for membership + frozen pre/post rescore; no tuning | Publication-strength B robustness | **FROZEN COMPLETED ROBUSTNESS** |


| B selection robustness stage | Destination Port, SHAP aggregation, alternate dev splits, one-factor gates; freeze variant rules/lambda/thresholds before held-out robustness rescore | Training + development only | Publication-strength B robustness | **IMPLEMENTATION ADDED; EXECUTION BLOCKED UNTIL DTYPE AUDIT ACCEPTED** |


| Duplicate-aware B validation | Equal-weight exact feature-pattern validation + whole-pattern bootstrap; preserve within-pattern label contradictions | Development validation only | B rule-validity robustness | **IMPLEMENTATION ADDED; EXECUTION BLOCKED UNTIL DTYPE AUDIT ACCEPTED** |


| Pattern-deduplicated System-A teacher | Frozen alternate teacher/full-chain robustness preserving binary label conflicts and original preprocessor; additive robustness only | Training + development only | Upstream duplicate-dependence robustness | **FROZEN COMPLETED ROBUSTNESS** |


| System-B fusion-authority sensitivity | Reuse accepted R0.v2; lambda in {0.70, 0.90, 1.00}; threshold selected on original development fusion slice under original MCC tie policy; held-out evaluation only after selection freeze | Development selection, then pre/post rescore | Publication-strength B robustness; informs future C/D fusion-policy risk | **IMPLEMENTATION ADDED; PRIMARY lambda=0.50 IMMUTABLE** |

| Pattern-deduplicated teacher R0 chain | Exact frozen alternate teacher manifest/checkpoints; reconstruct exact retained training rows; reuse frozen preprocessing, SHAP sample sizes/seeds, surrogate protocol, development split, validation gates, weighted CART consequents and fusion-selection procedure; no pre/post until R0 manifest is committed | Training + development only | Full upstream duplicate-dependence chain | **IMPLEMENTATION WIRED TO CLI; R0 MANIFEST MUST FREEZE BEFORE HELD-OUT RESCORE** |

| Pattern-deduplicated full-chain held-out evaluation | Frozen alternate teacher + frozen alternate R0 only; pre/post scoring only; report alternate A and alternate B seed-level/aggregate/paired deltas; no training/development access; cannot replace accepted primary artifacts | Pre/post fixed rescore only | Full upstream duplicate-dependence robustness closure | **IMPLEMENTATION ADDED; EXECUTE ONLY AFTER ALTERNATE R0 FREEZE** |


## Current System-B closure overlay — 8 October 2026

This overlay records the present state after completion of the mandatory retrospective robustness tranche. Earlier row text documenting pre-execution gates is retained as history.

| Control | Current state |
| --- | --- |
| System-B Q1 closure diagnostic / weighted CART consequent defect | **CLOSED by accepted R0.v2 correction** |
| Stage-3A dtype conformance | **FROZEN / ACCEPTED AS NUMERICALLY INERT** |
| Retrospective scenario audit | **FROZEN** |
| A/B exact-pattern seen/unseen rescore | **FROZEN** |
| Duplicate-aware B validation / group bootstrap | **FROZEN** |
| B selection robustness (Destination Port, SHAP aggregation/background, dev split, rule gates) | **SELECTION + HELD-OUT EVALUATION FROZEN** |
| Fusion-authority sensitivity | **SELECTION + HELD-OUT EVALUATION FROZEN** |
| Pattern-deduplicated System-A teacher | **FROZEN** |
| Pattern-deduplicated teacher R0 chain | **FROZEN** |
| Pattern-deduplicated full-chain held-out evaluation | **FROZEN** |
| Future C/D initial symbolic state | **ACCEPTED R0.v2 FROZEN BY MANIFEST HASH** |

No unresolved System-B implementation defect blocks transition to C/D design freeze.

All material primary C/D design controls affecting treatment definition, causal isolation, confirmatory analysis, runtime, and held-out access are now prospectively frozen. Any residual historical wording elsewhere in this register is superseded only where an explicit later accepted/frozen row records completion; it is not permission to reopen accepted System B.

## Stage 9.5 independent-assurance gate overlay — 16 October 2026

This overlay records the current assurance state without reopening accepted Stage-8/9 scientific evidence or earlier control rows.

| Control | Current state |
| --- | --- |
| Stage 9.5 overall | **OPEN / BLOCKED** |
| Stage 9.5-1 fresh-clone reconstruction | **0 repository/runtime/compact-evidence identity failures; 2 external-artifact blockers** |
| External blocker 1 | `system_a_checkpoint_bytes_missing` — recover and SHA-256 verify the five original System-A checkpoint files; no retraining/regeneration/substitution |
| External blocker 2 | `stage8_large_artifact_archive_missing` — recover and verify the original `artifacts/cd_primary_v1` archive; compact summaries are not a substitute for the frozen replay-equivalence target |
| Stage 9.5-2 statistical oracle | **CLOSED** |
| Stage 9.5-3 causal/information properties | **CLOSED** |
| Stage 9.5-4 targeted mutations | **CLOSED — 11/11 frozen mutants killed** |
| Stage 9.5-5 static assurance | **CLOSED; current discovery baseline 154 Ruff / 55 mypy remains triage-only and does not reopen the accepted scientific fingerprint set** |
| Stage 9.5-6 historical rerun | **OPEN / BLOCKED** — also subject to the prospectively frozen replay-equivalence correction because historical upstream manifest hashes include non-replay-invariant runtime/timing diagnostics |
| Stage 9.5-7 claim traceability | **HISTORICALLY EXECUTED / PROVISIONAL; NOT PROTOCOL-CLOSED** |
| Stage 9.5-8 independent reporting | **HISTORICALLY EXECUTED / PROVISIONAL; NOT PROTOCOL-CLOSED** |
| Stage 9.5-9 hostile review | **HISTORICALLY EXECUTED / PROVISIONAL; NOT PROTOCOL-CLOSED** |
| Work-package order | **ENFORCED PROSPECTIVELY IN CI: 9.5-7/8/9 remain locked until valid 9.5-6 closure evidence exists** |
| Stage 10 | **PROHIBITED until Stage 9.5 legitimately closes with zero unresolved Class-A defects** |

Interpretation boundary: these assurance blockers concern reconstructibility/provenance and the literal historical replay gate. They do not by themselves establish that accepted Stage-8/9 numerical results are wrong, and they do not authorize replacement of accepted evidence with regenerated artifacts or summary-only approximations.

## Stage 9.5-1 negative-closure overlay — 17 October 2026

This additive overlay supersedes only the **current-status interpretation** of the 16 October Stage-9.5 table above. Historical open/blocking rows remain part of the assurance chronology.

| Control | Current state |
| --- | --- |
| Stage 9.5-1 fresh-clone reconstruction | **CLOSED — FAILED / EXTERNAL PROVENANCE UNRESOLVED** |
| Negative closure authority | `STAGE9_5_1_FRESH_CLONE_RECONSTRUCTION_NEGATIVE_CLOSURE.md` + `data/manifests/stage9_5_1_negative_closure_v1.json` |
| Final verifier disposition | **0 identity failures / 2 unresolved external-artifact blockers** |
| Frozen success criterion | **UNCHANGED** — exact five original System-A checkpoints + original Stage-8 heavy archive at **145/145**, zero failures/blockers |
| External blocker 1 | `system_a_checkpoint_bytes_missing` |
| External blocker 2 | `stage8_large_artifact_archive_missing` |
| Regeneration/substitution | **PROHIBITED as closure evidence** |
| Stage 9.5-6 historical rerun | **BLOCKED BY CLOSED-FAILED 9.5-1** under the current evidence package |
| Stage 9.5-7/8/9 | **LOCKED as authoritative closure packages** |
| Stage 9.5 overall | **NOT CLOSABLE UNDER THE CURRENT EVIDENCE PACKAGE** because the Class-A provenance defect remains unresolved |
| Stage 10 | **PROHIBITED** |

Interpretation boundary: the negative closure terminates the Stage-9.5-1 assurance attempt without falsifying success. It does not assert that accepted Stage-8/9 numerical results are wrong, and it does not change any accepted treatment, estimand, metric, or result. It records that publication-grade clean-clone reconstruction of the full original checkpoint/heavy-artifact chain has not been demonstrated.

Reopening is permitted only if the exact original bytes are later recovered and the unchanged v1.2 verifier independently passes the frozen five-seed / 145-of-145 predicate. Otherwise any continuation requires a separately governed restart/new evidence-generation campaign rather than substitution into the accepted evidence chain.

---

## Stage 10A pre-outcome attack-pattern replication controls — 27 October 2026

| Variable / control | Frozen Stage-10A value or rule | Selection evidence | Match / gate requirement | Freeze state |
| --- | --- | --- | --- | --- |
| Stage-10A scenario | `cicids2017_goldeneye_temporal_attack_shift_v1` | Pre-outcome source audit only; no Stage-10 treatment outcomes | All Stage-10A arms | **FROZEN PRE-OUTCOME** |
| Scenario interpretation | Same-family DoS GoldenEye attack-pattern / class-conditional feature shift under an essentially stationary BENIGN background; CICIDS2017 pseudo-chronology; no natural-production or unqualified `P(Y|X)` claim | Source-only row/feature audit | All Stage-10A reporting | **FROZEN PRE-OUTCOME** |
| Stage-10A pre regime | Wednesday rows `[554162,623433)`, excluding the already frozen 11 Heartbleed rows; 69,260 retained = 65,671 BENIGN + 3,589 DoS GoldenEye | Exact raw source identity and row audit | All Stage-10A arms | **FROZEN PRE-OUTCOME** |
| Stage-10A post regime | Wednesday rows `[623433,692703)`; no BENIGN source replacement; 69,270 retained = 65,697 BENIGN + 3,573 DoS GoldenEye | Exact raw source identity and row audit | All Stage-10A arms | **FROZEN PRE-OUTCOME** |
| Stage-10A boundary | Logical stream index 69,260 after the frozen Heartbleed exclusion; evaluator/scoring diagnostics only | Prospective scenario design | Never supplied to detector/updater/symbolic lifecycle | **FROZEN PRE-OUTCOME** |
| Stage-10A raw source | `Wednesday-workingHours.pcap_ISCX.csv`; SHA-256 `893c27dc968bf7a8adef1689f90be55ca4a4dc3088fb63d6ff247ac56856df2a`; 225,166,395 bytes | Accepted CICIDS raw source identity | Exact bytes required | **FROZEN PRE-OUTCOME** |
| Stage-10A inherited start state | Existing training/development information set, preprocessing core `4527f77220f2cf6063108a7d71d80aaa0e82099ad282ff25408a2d9ce3488b1e`, System-A manifest `42004b5ed100b690023b9998bdc959fac41ab947b996fb7c58e44cee5e8dc6de`, R0.v2 manifest `131027d2f136494eb388183f18dcb7eb0e9d7e9fe786f22dba25f4e1624c1483` | Accepted pre-existing evidence only | Same within matched seed | **FROZEN PRE-OUTCOME** |
| Stage-10A seeds | 0,1,2,3,4 exactly; no extension after outcome access | Accepted paired-seed design | C/D/D-periodic matched by seed | **FROZEN PRE-OUTCOME** |
| Stage-10A primary family | E1 post MCC D-drift−C; E2 post MCSC D-drift−C; E3 post MCSC D-drift−D-periodic; paired seed is causal unit | Accepted confirmatory family carried prospectively | No window/event/rule pseudo-replication | **FROZEN PRE-OUTCOME** |
| Stage-10A adaptive mechanism | Accepted primary detector, timing, neural update, fusion and symbolic-lifecycle semantics inherited unless a prospectively versioned pre-outcome incompatibility correction is required | Accepted Stage-8 design | C/D neural path matched; symbolic state transition remains intended C-vs-D difference | **FROZEN PRE-OUTCOME** |
| Stage-10A execution gate | Source-only protocol/readiness work is permitted; C/D/D-periodic treatment execution and outcome access remain prohibited until legitimate Stage-9.5 closure | Post-Stage-9 governance addendum + Stage-10+ master protocol | Hard gate; no local or CI bypass | **FROZEN GOVERNANCE RULE** |
| Stage-10A source verifier | `tools/stage10/stage10a_source_readiness.py`; source identities/counts/row hashes/class-conditional diagnostics only; report must always state treatment execution unauthorized | Pre-outcome engineering assurance | Must stop before adaptive treatment execution | **FROZEN PRE-OUTCOME** |

---

## Stage 10B pre-outcome gradual BENIGN source-regime controls — 28 October 2026

| Variable / control | Prospective value | Match / use requirement | Freeze state |
| --- | --- | --- | --- |
| Stage-10B scenario | `cicids2017_gradual_benign_source_v1` | Separate controlled gradual covariate/source-mixture replication, not attack evolution or natural production drift | **FROZEN PRE-OUTCOME** |
| Raw source identities | Wednesday 225,166,395 bytes SHA-256 `893c27dc968bf7a8adef1689f90be55ca4a4dc3088fb63d6ff247ac56856df2a`; Thursday morning 52,023,263 bytes SHA-256 `d67066211fb1689c78406f1506f4c44704ecb92088353d5c96d96d6474eb819d` | Exact bytes, no corrected/deduplicated substitute | **FROZEN PRE-OUTCOME** |
| Training/development and initial model | Same frozen Stage-8 training/development, 77-feature preprocessing core, System-A checkpoints/seeds/thresholds, R0.v2 | No refit or future-outcome selection | **FROZEN PRE-OUTCOME** |
| Evaluation pre | Wednesday `[554162,623433)` excluding original 11 Heartbleed; 69,260 retained; BENIGN 65,671; GoldenEye 3,589 | Source order and frozen exclusion | **FROZEN PRE-OUTCOME** |
| Evaluation post | Wednesday `[623433,692703)` template 69,270; BENIGN 65,697; GoldenEye 3,573; no attack replacement | Preserve every template position and GoldenEye label | **FROZEN PRE-OUTCOME** |
| Source mapping | For BENIGN slot ordinal j, frozen Thursday BENIGN eligible index `floor(j*168186/65697)` | Same eligible mapping as accepted Stage-8 abrupt scenario; source-only deterministic | **FROZEN PRE-OUTCOME** |
| Gradual schedule | Post local clock t, 50,000-row ramp, `p(t)=min(1,(t+0.5)/50000)`; SHA-256 salt `stage10b-gradual-benign-v1`; first 8 digest bytes big-endian uint64; integer comparison `100000*u64<(2*t+1)*2^64`; t>=50,000 always replaces | One exogenous source schedule shared across all arms/seeds, no outcome/trigger dependence | **FROZEN PRE-OUTCOME** |
| Source-only observed assembly | 41,935/65,697 eligible BENIGN slots replaced: 23,661 ramp, 18,274 plateau; 23,762 Wednesday BENIGN slots retained; GoldenEye unchanged | Verify ordered slot and mapping hashes; no favorable source reselection | **FROZEN PRE-OUTCOME** |
| Reference clocks | Ramp start global index 69,260; ramp complete 119,260; stream ends 138,530 | Evaluator/diagnostic only; never detector/updater input | **FROZEN PRE-OUTCOME** |
| Primary inference | Seeds 0–4; paired-seed causal unit; E1 post MCC D-drift−C; E2 post MCSC D-drift−C; E3 post MCSC D-drift−D-periodic; **full post 69,270 rows** as primary estimand | Reporting separately from Stage-8/9 and Stage-10A, no event/window pseudo-replication or seed extension | **FROZEN PRE-OUTCOME** |
| Secondary reporting | Separate ramp/plateau descriptive trajectories, attacks/FNR/coverage, explanation, timing, cost, failures | Cannot promote subperiod findings into the frozen primary family | **FROZEN PRE-OUTCOME** |
| Treatment isolation | Match C/D neural and non-symbolic states within seed; identical detector/latency/replay; symbolic lifecycle is intended difference; periodic arm shares symbolic operator/budget | Abort on unmatched causal state; inherited fusion lambda=.50 | **FROZEN PRE-OUTCOME** |
| Stage-10B stage gate | `tools/stage10/stage10b_source_readiness.py` may inspect only raw source labels/mapping/protocol/source hashes; no treatment output | Stage-9.5 closure remains prerequisite to any Stage-10 adaptive run | **FROZEN GOVERNANCE** |

---

## Stage 10C pre-outcome unseen Bot-family introduction controls — 28 October 2026

| Variable / control | Prospective frozen value | Match / gate requirement | Freeze state |
| --- | --- | --- | --- |
| Stage-10C scenario | `cicids2017_controlled_unseen_bot_v1` | Controlled attack-family replacement, not natural attack evolution or independent-environment replication | **FROZEN PRE-OUTCOME** |
| Raw sources | Wednesday 225,166,395 bytes SHA-256 `893c27dc968bf7a8adef1689f90be55ca4a4dc3088fb63d6ff247ac56856df2a`; Friday morning 58,316,725 bytes SHA-256 `53a41c24d570ea83b7ac55b2e94df94e7a8216aeb80a2af0246b6bc8bb543000` | Exact source bytes, no corrected/deduplicated substitution | **FROZEN PRE-OUTCOME** |
| Historical initial evidence | Accepted Monday+Tuesday+Wednesday `[0,346352)` training and Wednesday `[346352,554162)` development; GoldenEye seen 1,118 training/2,013 development; Bot not present | Exact inherited System-A/preprocessing/R0.v2/threshold identities; no Bot future label in historical initial state | **FROZEN PRE-OUTCOME** |
| Pre attack pool | Exactly 1,966 source-ordered GoldenEye from Wednesday `[554162,623433)` original 3,589 candidate rows, selecting candidate ordinal `floor(k*3589/1966)` | No training/development overlap, no treatment-dependent choice | **FROZEN PRE-OUTCOME** |
| Post attack pool | All 1,966 Friday-morning Bot rows in original source-row order | Unseen-family definition is historical family-label absence, not guaranteed rule noncoverage | **FROZEN PRE-OUTCOME** |
| BENIGN background | Friday-morning BENIGN source rows 189,067, alternating zero-based benign candidate ordinals into disjoint pre-even/post-odd pools | Same collection source on both sides; prospective even sampling, no BENIGN reuse | **FROZEN PRE-OUTCOME** |
| BENIGN sample counts | Pre 67,294 from even candidates via `floor(k*even_pool_size/67294)`; post 67,304 from odd via `floor(k*odd_pool_size/67304)` | Source-ordered samples without replacement; source metadata evaluator only | **FROZEN PRE-OUTCOME** |
| Synthetic attack positions | For each regime N, attack slot `floor((2*k+1)*N/(2*1966))`, k=0..1965 | 1,966 unique slots/regime, fill remaining slots with sampled BENIGN rows; no per-arm seed RNG | **FROZEN PRE-OUTCOME** |
| Source stream identity | Pre 69,260, post 69,270, boundary global 69,260, 138,530 total; pre GoldenEye, post Bot | Exact ordered `(source_order,row_in_source)` hashes in source audit; evaluator-only boundary | **FROZEN PRE-OUTCOME** |
| Source diagnostic selection | BENIGN mean KS 0.00247861, max 0.00611571, 0/77 features >=0.1; GoldenEye/Bot mean KS 0.49642, 58/77 >=0.1 | Source-only; no treatment success selection; strong attack-family/port/day signatures remain confounded | **FROZEN PRE-OUTCOME** |
| Primary treatment | C adaptive neural+frozen symbolic; D-drift same neural+drift-gated lifecycle; D-periodic matched operator/budget periodic clock | Matched within-seed non-symbolic state, fail-closed on divergence | **FROZEN PRE-OUTCOME** |
| Primary inferential family | Seeds 0–4; E1 post MCC D-drift−C, E2 post MCSC D-drift−C, E3 post MCSC D-drift−D-periodic; entire post Bot regime | Paired seed causal unit; no pseudo-replication, post-hoc endpoint/seed changes, or replacement of accepted evidence | **FROZEN PRE-OUTCOME** |
| Source verifier | `tools/stage10/stage10c_source_readiness.py` reconstructs exact raw labels, BENIGN/attack selection and slot hashes; recomputes both 77-feature KS comparisons | Raw-only verification, no C/D predictions/outcomes, explicit treatment lock in all reports | **FROZEN PRE-OUTCOME** |
| Stage 9.5 execution firewall | Source-only protocol/static checks permitted; C/D/D-periodic execution prohibited until legitimate Stage-9.5 closure | No local/GitHub workaround, no false treatment authorization after preflight pass | **FROZEN GOVERNANCE** |

