# System B Protocol — Static Neuro-Symbolic Baseline

**Status:** PROTOCOL FROZEN; IMPLEMENTATION / R0 ARTIFACTS NOT YET ACCEPTED  
**Stage:** 4 / System B  
**Python:** 3.11.9 exactly  
**Scenario:** `cicids2017_sudden_benign_v1`

System B is the static neuro-symbolic baseline:

- the accepted System-A neural checkpoint is unchanged;
- symbolic reasoning is active through a validated initial rule base `R_0`;
- symbolic adaptation is disabled;
- the same seed-matched `R_0` must later initialize Systems C and D.

This protocol is frozen before any System-B pre/post evaluation. System-A pre/post outcomes already known historically are prohibited as System-B design evidence.

## 1. Governing purpose

System B must establish:

1. a reproducible and auditable initial symbolic representation;
2. a reusable versioned `R_0` for later B/C/D pairing;
3. static-symbolic staleness evidence under the controlled shift.

High detection performance alone is insufficient. Rule support, class precision, neural fidelity, coverage, activation, stability, conflict/abstention, complexity, and per-rule pre/post behavior are required evidence.

## 2. Seed-to-R0 mapping

The project uses **one seed-specific initial rule base per frozen System-A checkpoint**:

`R_0^(s)` is derived from the accepted System-A checkpoint for seed `s in {0,1,2,3,4}`.

This mapping is mandatory because the symbolic rules are intended to explain the corresponding neural detector. It also preserves the strongest later causal pairing:

- B(seed s): frozen neural checkpoint s + `R_0^(s)`;
- C(seed s): matched adaptive neural trajectory initialized from checkpoint s + frozen `R_0^(s)`;
- D(seed s): the same matched neural start + the same `R_0^(s)`, later evolved.

No global cross-seed rule base is used in the primary experiment.

## 3. Information firewall and development split

### Candidate generation

Only the frozen **training** partition may be used for:

- SHAP background construction;
- SHAP attribution sampling;
- influential-feature selection;
- surrogate fitting;
- candidate path extraction.

### Candidate acceptance and System-B tuning

Only the frozen **development** partition may be used for:

- candidate-rule validation;
- redundancy/conflict audit;
- fusion-weight selection;
- fused decision-threshold selection.

The development partition is split once, identically for all seeds, using a deterministic binary-label-stratified split:

- rule-validation slice: 60%;
- fusion/threshold-tuning slice: 40%;
- `random_state = 20261007`;
- implementation: `StratifiedShuffleSplit(n_splits=1, test_size=0.40, random_state=20261007)`.

The split is based only on the development binary target and is independent of any pre/post outcome. Scenario-row identities and hashes for both slices must be written to the System-B development/freeze record.

The rule-validation slice is not reused to select fusion weight or the final fused threshold.

### Untouched firewall

`pre_drift` and `post_drift` are forbidden in all rule generation, validation, fusion selection, and threshold selection. The build/freeze command must not load those partitions.

## 4. SHAP configuration

SHAP is used only to select a compact feature subset. SHAP values are not symbolic rules.

For every seed-specific frozen neural checkpoint:

- explainer: `shap.DeepExplainer`;
- explained model output: **raw binary attack logit**, not sigmoid probability;
- model state: evaluation mode; no retraining or recalibration;
- preprocessing: accepted frozen training-fitted representation;
- background: 256 training observations, exactly 128 BENIGN and 128 attack;
- attribution sample: 2,048 training observations, exactly 1,024 BENIGN and 1,024 attack;
- sampling seed: `20261007`;
- the same sampled training scenario-row identities are used across all five neural seeds;
- sampling is without replacement inside each class;
- background and attribution row-ID hashes are recorded.

The raw-logit explanation target is intentional: the accepted neural probabilities are uncalibrated weighted-BCE outputs, and explaining the logit avoids changing the frozen neural state or silently introducing calibration.

## 5. Influential-feature selection

For each feature compute mean absolute SHAP magnitude:

1. globally over the balanced 2,048-row attribution sample;
2. within true BENIGN rows;
3. within true attack rows.

Each of the three 77-feature vectors is normalized by its own maximum (all-zero vectors remain zero). The feature selection score is the elementwise maximum of those three normalized vectors.

Select exactly the top **12** features by descending score. Ties are resolved by the frozen 77-feature order.

This fixed class-aware rule prevents the majority benign class from dominating feature selection while keeping the symbolic input compact. The selected-feature identities and ranked attribution summary are recorded per seed.

## 6. Surrogate target and constraints

The surrogate approximates the **actual frozen neural decision rule**, not ground truth.

For seed `s`:

- target = `1[p_neural_attack >= frozen_system_a_threshold_s]`;
- training rows = all frozen training observations;
- inputs = the 12 selected SHAP features;
- learner = `sklearn.tree.DecisionTreeClassifier`;
- criterion = `gini`;
- splitter = `best`;
- max depth = **4**;
- minimum samples per leaf = **1,000**;
- class balancing = sample weights chosen so the total training weight of the two **neural-predicted** classes is equal;
- random state = seed `s`;
- no pruning selected from pre/post evidence;
- no development labels are used to fit the surrogate.

If either neural-predicted class is absent in training, extraction fails rather than inventing a symbolic class.

Every root-to-leaf path becomes one candidate rule.

## 7. Canonical rule representation

A rule is represented as:

`IF antecedent(x) THEN class = c, confidence = q`

Each atomic condition is one of:

- `feature <= threshold`;
- `feature > threshold`.

Repeated splits on the same feature are canonicalized into the tightest non-contradictory lower/upper bounds. Conditions are serialized deterministically in frozen feature-order, then lower bound before upper bound.

Minimum rule metadata:

- persistent `rule_id`;
- `lineage_id`;
- `rule_base_version`;
- seed;
- antecedent conditions;
- consequent;
- confidence;
- support and covered count;
- class precision;
- neural fidelity;
- stability;
- complexity;
- activation count/rate fields;
- lifecycle state;
- source candidate identifier;
- validation evidence identity;
- conflict/redundancy relations.

Initial lifecycle vocabulary supports:

`active, new, refined, merged, conflict, retained, demoted, retired, reactivated, rejected`.

System B itself does not transition `R_0` during evaluation.

## 8. Rule-quality definitions and gates

All candidate quality metrics are computed on the 60% development rule-validation slice.

### Support

`support = covered_rows / validation_rows`.

Acceptance requires both:

- support >= **0.001**;
- covered rows >= **100**.

### Class precision

Among covered rows:

`class_precision = P(y_true = consequent | rule fires)`.

Acceptance threshold:

- `class_precision >= 0.80`.

### Neural fidelity

Among covered rows:

`neural_fidelity = P(frozen_neural_decision = consequent | rule fires)`.

Acceptance threshold:

- `neural_fidelity >= 0.90`.

### Complexity

`complexity = number of canonical atomic antecedent conditions`.

Acceptance threshold:

- `complexity <= 4`.

### Validation stability

System-B candidate stability is explicitly **resampling stability of rule validity**, not unconstrained feature perturbation stability.

For each seed, generate 100 binary-label-stratified bootstrap resamples of the rule-validation slice with replacement, preserving each class stratum size. The bootstrap index sets are generated once per seed with `random_state = 20261007 + seed` and reused for all candidates from that seed.

For every bootstrap replicate recompute support, covered count, class precision, and neural fidelity.

`stability = fraction of bootstrap replicates that still satisfy the support, minimum-covered-count, class-precision, and neural-fidelity gates`.

Acceptance threshold:

- `stability >= 0.90`.

This avoids inventing semantically invalid network-flow perturbations and makes the stability claim explicitly scoped to empirical rule validity under resampling.

### Confidence

Accepted-rule confidence is conservative and parameter-free:

`q = min(class_precision, neural_fidelity)`.

Support is reported separately and is not folded into confidence.

### Conjunctive gate

A candidate is eligible only if **all** support, precision, fidelity, stability, and complexity gates pass. No weighted “explainability score” is optimized.

## 9. Redundancy and conflict semantics

All overlap calculations use empirical activation on the rule-validation slice.

For rules A and B:

- Jaccard overlap = `|A∩B| / |A∪B|`;
- overlap coefficient = `|A∩B| / min(|A|, |B|)`.

### Same-consequent redundancy

Same-consequent rules are considered redundant/nested when overlap coefficient >= **0.95**.

Retain one deterministically by:

1. higher confidence `q`;
2. higher support;
3. lower complexity;
4. lexical `rule_id` tie break.

The other candidate is logged as rejected/merged-redundant; it is not silently discarded.

### Different-consequent conflict audit

Different-consequent rules are flagged as a rule-level potential conflict when overlap coefficient >= **0.50**.

A rule may dominate the other only by strict Pareto evidence:

- class precision no worse;
- neural fidelity no worse;
- support no worse;
- complexity no greater;
- at least one criterion strictly better.

If neither rule Pareto-dominates, both identities and the conflict relation remain auditable.

### Runtime symbolic abstention

At inference time, **any observation that activates accepted rules from both consequents is a symbolic conflict-abstention case**, regardless of aggregate confidence. The final score falls back to the neural output and no contradictory symbolic explanation is emitted.

This conservative runtime rule prevents a confidence-weighted vote from hiding contradictory active knowledge.

## 10. Symbolic inference

For accepted active rules `r_i`:

`m_i(x)=1` when the antecedent is satisfied, else 0.

When one or more non-conflicting rules fire, the symbolic class confidence is the normalized active confidence mass:

`p_rule(c|x) = sum_i[m_i(x) q_i I(c_i=c)] / sum_i[m_i(x) q_i]`.

For binary System B, resolved active rules all support the same consequent, so `p_rule(attack|x)` is 0 or 1 under the conservative conflict policy.

Statuses are explicit:

- `covered`: at least one accepted rule fires and no opposite-consequent rule cofires;
- `uncovered`: no accepted rule fires;
- `conflict_abstain`: opposite-consequent rules cofire.

The primary explanation coverage metric uses resolved `covered` cases. Raw activation coverage and conflict-abstention rate are also recorded.

## 11. Neural-symbolic fusion and fused decision threshold

No probability calibration is introduced.

For resolved covered observations:

`p_fused = lambda * p_neural + (1-lambda) * p_rule_attack`.

For uncovered or conflict-abstention observations:

`p_fused = p_neural`.

### Fusion-weight policy

One **global lambda shared by all five seeds** is selected from:

`{0.50, 0.60, 0.70, 0.80, 0.90, 1.00}`.

Selection uses only the 40% development fusion/threshold-tuning slice.

For each candidate lambda and each seed:

1. compute fused development scores using that seed's validated `R_0^(s)`;
2. select that seed's fused decision threshold by the existing System-A MCC procedure and tie breaks;
3. record MCC, F1, and FPR.

Select the global lambda by:

1. highest mean MCC across the five seeds;
2. highest mean F1;
3. lowest mean FPR;
4. higher lambda (more conservative / closer to the frozen neural detector).

The selected global lambda and the five corresponding seed-specific fused thresholds are frozen in the System-B manifest.

Including `lambda=1.00` is intentional: development evidence is allowed to conclude that symbolic explanations are useful while symbolic score adjustment adds no detection value. The protocol does not force symbolic influence merely to create a favorable result.

The selected lambda and thresholds are then held unchanged for untouched B evaluation and become the matched initial fusion configuration for later C/D unless a separately versioned prospective design explicitly supersedes them.

## 12. R0 versioning and freeze artifacts

The accepted initial symbolic state is version `R0.v1`, with one seed-specific rule-base artifact.

Before any B pre/post evaluation, the freeze must record and hash:

- governing source identities;
- scenario manifest identity;
- preprocessing-state identity;
- System-A manifest identity;
- each seed's checkpoint SHA-256;
- SHAP operator/configuration;
- background/attribution row-ID hashes;
- selected-feature list/ranking;
- surrogate configuration;
- development split row-ID hashes;
- candidate rules and acceptance/rejection reasons;
- accepted `R_0^(s)` bytes/hash;
- validation summary;
- global lambda;
- per-seed fused thresholds;
- Python / lockfile / library / runtime identity;
- code commit used to generate the freeze.

The build command must refuse to overwrite an accepted System-B manifest or accepted `R_0` artifact.

A read-only `system-b verify` path must validate the compact freeze identities without loading pre/post partitions.

## 13. Longitudinal reporting grid

The common A/B/C/D **reporting** grid is frozen now, before System-B held-out outcomes:

- window size: **5,000 rows**;
- stride: **5,000 rows**;
- windows are non-overlapping;
- pre-drift and post-drift scoring partitions are windowed separately so the controlled boundary is never mixed inside a reporting window;
- a final partition remainder >=1,000 rows is retained as a final partial window;
- a final remainder <1,000 rows is merged into the preceding window so no row is discarded;
- source/scenario order is preserved;
- the known synthetic boundary is evaluator metadata only and is not supplied to a drift detector or updater.

This is a common visualization/longitudinal evidence grid, not the internal window of a future drift detector.

After this freeze, frozen System-A checkpoints should be rescored on the same grid without retraining or retuning.

## 14. System-B untouched evaluation

Only after the complete five-seed System-B manifest and all `R_0` hashes are frozen and committed may pre/post evaluation run.

Required detection evidence per seed/partition/window includes:

- sample count and prevalence;
- TN, FP, FN, TP;
- precision, recall, F1, FPR, MCC, ROC-AUC, average precision;
- accuracy and balanced accuracy as secondary descriptive metrics.

Required symbolic evidence includes:

- resolved coverage and raw activation coverage;
- uncovered rate;
- conflict-abstention rate;
- symbolic-vs-neural fidelity on resolved covered cases;
- per-rule support;
- per-rule class precision;
- per-rule neural fidelity;
- per-rule activation count/rate;
- per-rule complexity;
- rule-base size;
- pre/post change for every accepted rule, including stable/improving/inactive rules as well as degrading rules.

The frozen `R_0` is never modified during System-B evaluation.

No post-evaluation retuning is permitted. A genuine implementation defect requires a documented new version and preserved prior evidence.

## 15. Computational evidence

Development/freeze records should capture at minimum:

- neural prediction duration used by extraction;
- SHAP duration;
- surrogate fit duration;
- candidate count;
- validation/bootstrap duration;
- accepted-rule count;
- fusion-tuning duration.

Untouched evaluation should record symbolic inference overhead in a reusable form for later B/C/D cost comparisons.

## 16. Required repository tests

Repository-only tests must cover at least:

- deterministic canonical rule serialization and IDs;
- `<=` and `>` activation boundaries;
- interval canonicalization;
- support / precision / fidelity / complexity calculations;
- bootstrap stability determinism;
- uncovered neural fallback;
- cross-class conflict abstention;
- normalized symbolic confidence;
- redundancy handling;
- fusion arithmetic;
- no symbolic score effect when uncovered/abstaining;
- global-lambda selection tie policy;
- feature-order contract;
- System-A checkpoint identity preservation;
- no preprocessing refit;
- build path incapable of loading pre/post;
- no overwrite of accepted System-B freeze/evaluation artifacts.

## 17. Evidence status at protocol freeze

System-B v1 rule construction and untouched evaluation use **CPU only**, matching the accepted System-A primary backend and avoiding backend-dependent attribution/tree inputs as a new uncontrolled variable. A future backend change requires a separately versioned prospective protocol.\n\nCandidate stability and held-out staleness stability use the same named quantity at different evidence stages: the candidate gate is bootstrap pass persistence on the development validation slice; after freeze, the same pass-persistence calculation is recomputed separately on the complete pre-drift and post-drift partitions. The 5,000-row longitudinal windows report support, class precision, neural fidelity, activation/coverage and conflict behavior, but are not treated as independent bootstrap experiments.\n\nUntouched evaluation additionally requires the generated System-B manifest and all `R_0` files to have been committed: the evaluator must refuse to start from a dirty worktree. This makes the pre/post firewall mechanically auditable.\n\nAt this protocol freeze:

- the governing DOCX hashes match `GOVERNING_SOURCES.md`;
- remote `main` and `stage4-system-b` both point to `5d5cb67dda1abcda720eac785c29fa259f6bf5b8`;
- no System-B pre/post result has been generated or inspected;
- System-A pre/post results are historically known but were not used to select any System-B parameter above;
- exact accepted `R_0` bytes, selected global lambda, and per-seed fused thresholds remain to be generated from permitted training/development evidence under this frozen procedure.
