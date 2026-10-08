# C/D Adversarial Design Audit

**Status:** PROSPECTIVE DESIGN AUDIT — NO ADAPTIVE HELD-OUT EXECUTION AUTHORIZED  
**Audit branch:** `stage5-cd-design-audit`  
**Accepted parent:** `main` at `4c13d71a111ce7b72b3ef26a01b2918592425aa1`  
**Accepted System-B source head:** `317b8d957c3ac983598523215a1205b6869f8c17`  
**Date:** 8 October 2026

## 1. Purpose

This audit attempts to falsify the proposed C/D causal design before adaptive implementation.

The governing research question is not whether an adaptive hybrid IDS can be made to perform well. It is whether, under an otherwise matched adaptive system, **drift-gated symbolic rule evolution itself contributes measurable longitudinal value** while preserving an auditable and versioned explanation lifecycle.

Therefore any mechanism by which System D can change its own future drift alarms, neural updates, labels, replay data, thresholds, evidence availability, or evaluation schedule is a treatment-contamination risk and must be removed or explicitly versioned before untouched adaptive evaluation.

No C/D held-out result may be accessed to resolve the blocking items below.

## 2. Audit verdict

**Current verdict: NOT READY FOR ADAPTIVE IMPLEMENTATION.**

The project is ready to enter prospective C/D design freeze, but not yet ready to implement or execute the adaptive systems. The blockers are design-contract blockers rather than defects in accepted A/B evidence.

System B remains closed. Nothing in this audit reopens accepted R0.v2 or corrected System-B evaluation.

## 3. Blocking causal threats

### B1. Treatment-dependent drift-trigger feedback

**Threat:** If drift detection monitors fused C/D prediction error, fused confidence, symbolic conflict, or any signal affected by the evolving D rule base, D can alter its own future trigger timing. C and D would then differ in more than symbolic evolution.

**Required control:** Primary C and D must consume the **same treatment-independent confirmed drift-event stream**. The monitored signal and detector state must not depend on D symbolic state. A shared neural-only signal or a defensible label-free stream statistic may qualify after the signal/latency audit.

**Mechanical invariant:** for each seed, confirmed neural-adaptation event IDs and detector-state hashes must be identical for C and D.

### B2. Treatment-dependent label acquisition or evidence selection

**Threat:** If D alerts determine which rows are investigated, labeled, replayed, or admitted to symbolic validation, D changes its own future evidence distribution.

**Required control:** Primary C/D label availability, label maturity, replay membership, neural-update evidence, symbolic candidate evidence pool, and validation evidence pool must be defined independently of C/D fused decisions.

An active-learning or alert-conditioned labeling policy may be scientifically interesting later, but it would be a different treatment and cannot be silently mixed into the primary causal contrast.

### B3. Immediate-label oracle leakage

**Threat:** Stream evaluations that expose the label of row t at prediction time, or permit an update before the prediction being evaluated, use information unavailable at deployment.

**Required control:** Freeze an explicit information-time contract. At every stream index, it must be possible to determine whether X, prediction, label, detector statistic, replay eligibility, candidate-generation eligibility, validation eligibility, and publication eligibility are available or pending.

Prediction must precede any use of the same observation's newly available label.

### B4. Post-trigger lookahead in adaptation windows

**Threat:** A drift alarm at time t followed by construction of a model/rule update using future rows that had not arrived by the claimed publication time makes adaptation retrospectively clairvoyant.

**Required control:** Every update event must record: trigger time, evidence cutoff, label-maturity cutoff, generation rows, validation rows, update start/end, and publication-effective row. No prediction scored before publication may use the new state.

### B5. Neural-state divergence between C and D

**Threat:** Merely using the "same neural algorithm" does not prove the neural trajectories are identical. Differences can arise from buffer membership, RNG consumption, stopping, thread nondeterminism, threshold state, or D-dependent evidence.

**Required control:** Build a shared non-symbolic control plane per seed. C and D must have identical neural checkpoint hashes at every update, identical replay/buffer row-identity hashes, identical neural optimizer/update budgets, identical detector events, identical update chronology, and matched runtime controls.

A mismatch is an experimental abort condition, not a minor diagnostic.

### B6. Threshold adaptation as a hidden second treatment

**Threat:** If C and D independently adapt thresholds from their own fused-score streams, D symbolic evolution changes the evidence used to choose its future operating point. The treatment becomes symbolic evolution plus a treatment-dependent threshold trajectory.

**Required control:** The primary threshold policy must be matched and causally isolated. Candidate policies to adjudicate prospectively are:
1. fixed accepted R0.v2 fused thresholds;
2. a shared threshold trajectory derived from treatment-independent neural/control-plane evidence;
3. a separately labeled sensitivity where threshold adaptation is itself part of the treatment.

Independent C/D fused-score threshold optimization is not admissible for the primary contrast.

### B7. Replay-buffer contamination

**Threat:** If replay selection uses current fused error, symbolic confidence, conflict, or D alarm status, replay differs across C/D.

**Required control:** Replay selection and eviction must be based on treatment-independent quantities and identical row IDs for matched C/D seeds.

### B8. Trigger-ablation opportunity mismatch

**Threat:** D-drift versus D-periodic is uninterpretable if the periodic arm gets more evidence, more maintenance opportunities, more labels, or a different update budget.

**Required control:** Freeze the periodic cadence and budget rule before held-out execution. The symbolic operator, eligibility rules, evidence horizon, label-maturity rules, validation gates, maximum update opportunity, neural trajectory, and cost accounting must be identical. Only the symbolic trigger schedule may differ.

The known synthetic boundary is forbidden from selecting the periodic cadence.

### B9. Symbolic gate/sample-size incompatibility

**Threat:** The static R0 covered-count gate of 100 may imply a radically different effective support in smaller online validation windows and can silently suppress or favor evolution.

**Required control:** Before D, derive the implied effective support for the actual evidence window. Freeze either a sufficiently large window, a separately versioned size-scaled count rule, or an uncertainty-based evidence criterion. Apply identically to D-drift and D-periodic.

### B10. Rule-confidence temporal ambiguity

**Threat:** Updating confidence q from pending/future labels, mixing pre-update and post-update evidence, or allowing confidence to evolve on a different clock from rule validity produces hidden lookahead and uninterpretable lifecycle state.

**Required control:** Freeze confidence evidence source, label maturity, decay/retention policy, update clock, and relationship to rule publication. Every q change must be versioned and attributable to evidence available at that time.

### B11. Undefined lifecycle semantics

**Threat:** "Evolve rules" is not a reproducible treatment unless add/refine/merge/retain/demote/retire/reactivate/conflict/abstain behavior is algorithmically complete.

**Required control:** Freeze the lifecycle state machine before implementation. Every attempted operation must produce an immutable event with trigger ID, parent/source IDs, evidence IDs, candidate metrics, accept/reject reason, resulting rule/version IDs, conflict resolution, publication time, and cost.

### B12. Neural adaptation too weak to be a credible control

**Threat:** If C uses token or underpowered adaptation, D can appear valuable because the neural comparator was not serious.

**Required control:** Select and freeze a defensible continual/adaptive neural procedure using training/development/design evidence only. Catastrophic forgetting must be measured, not assumed absent.

Recent NIDS literature strongly supports replay as a serious baseline:
- Fathima A.H. et al., "Adaptive memory replay for network intrusion detection: Tackling data drift and catastrophic forgetting," Computer Networks 272 (2025), 111712, DOI 10.1016/j.comnet.2025.111712.
- Costagliola et al., "Replay or Regret: Evaluating Continual Learning Methods for Robust Intrusion Detection," MILCOM 2025, DOI 10.1109/MILCOM64451.2025.11310341.
- 2026 domain-incremental NIDS evaluations likewise report replay-based methods as materially stronger against forgetting than naive or regularization-only updates.

This literature motivates replay as a candidate baseline; it does not authorize choosing a replay variant from future C/D held-out outcomes.

## 4. Blocking information-timing controls

The design freeze must specify, at minimum:

1. feature-arrival time;
2. prediction time;
3. label-arrival model;
4. detector-statistic update time;
5. drift-confirmation time;
6. replay admission/eviction time;
7. neural update eligibility and execution time;
8. symbolic candidate-generation evidence cutoff;
9. symbolic validation evidence cutoff;
10. rule publication-effective time;
11. threshold-update time if applicable;
12. scoring/evaluation time.

A row cannot simultaneously serve as an already-known label for adaptation and as a pre-update prediction without an explicit prequential ordering rule.

Recent stream-learning work makes this a publication-level concern rather than an implementation detail:
- Komorniczak, Ksieniewicz, and Zyblewski, "Structuring the processing frameworks for data stream evaluation and application," Pattern Recognition 172 (2026), 112516, DOI 10.1016/j.patcog.2025.112516.
- Alencar et al., "Concept drift detection in delayed and partially labeled data streams: An experimental survey," Digital Signal Processing 182 (2026), 106325, DOI 10.1016/j.dsp.2026.106325.

## 5. Statistical threats

### S1. Seeds are not independent deployment environments

The five matched seeds quantify stochastic model/training variation within a fixed scenario. They do not constitute five independent network environments.

Primary C-vs-D inference remains seed-paired within scenario. Claims must not inflate n by treating windows, rules, drift events, or lifecycle events as independent replicates.

### S2. Windows are repeated dependent observations

Longitudinal windows are descriptive/repeated observations. Window-level trajectories are important for recovery and staleness, but naive independent-window tests are prohibited.

### S3. Event multiplicity

Multiple drift alarms within one stream are dependent events. Trigger precision/delay/repeated-alarm summaries must not be converted into pseudo-replicated treatment tests.

### S4. Small-n confirmatory testing

With five paired seeds, exact tests have coarse resolution and parametric intervals are assumption-sensitive. The final statistical plan should emphasize prespecified effect sizes, paired uncertainty, direction consistency, longitudinal mechanisms, scenario replication, and bounded claims rather than treating a conventional p-value threshold as the sole evidence criterion.

### S5. Multiplicity across endpoint families

Detection, trigger quality, explanation validity, lifecycle behavior, forgetting, and cost create many possible outcomes. A small confirmatory endpoint family and explicit secondary/exploratory hierarchy must be frozen before C/D held-out execution.

## 6. Publication-strength additions recommended

These are not all required to begin implementation, but the design should reserve them prospectively where feasible.

### P1. Explicit catastrophic-forgetting endpoint

Report retention/forgetting of pre-change behavior after neural adaptation. A model that recovers current-stream F1 while erasing prior competence is not a satisfactory adaptive control.

### P2. Label-delay primary or prespecified sensitivity

Immediate labels are operationally optimistic. Prefer a nonzero fixed or otherwise defensible label-delay model in the primary stream-time contract, with zero-delay oracle sensitivity if useful. If the dataset cannot justify a natural delay, present the chosen delay as an experimental operating assumption rather than an empirical property of CICIDS2017.

### P3. Trigger-quality reporting

Report false alarms, missed relevant changes where reference events exist, detection delay, repeated alarms, refractory suppression, update count, and recovery-per-update. The synthetic boundary remains scoring-only and must never be fed to the detector.

### P4. Attack-pattern / actual-concept-change scenario

The frozen primary scenario is BENIGN-source-regime-dominant. It is useful as a controlled proving ground but is weak evidence for claims about stale attack rules. Add at least one later scenario where attack-pattern or conditional-label behavior changes and symbolic staleness has a direct mechanistic opportunity to occur.

### P5. Second dataset

A defensible second flow-oriented dataset materially strengthens external validity. Do not force incompatible features into a fake common representation; use a dataset-specific model/rule substrate while preserving the higher-level causal protocol where semantics permit.

### P6. Explanation lifecycle outcomes beyond coverage

Retain class-conditional coverage/correctness/fidelity, but additionally report rule age, time-to-staleness, validation survival, retire/reactivate counts, conflict/abstention, lineage length, update churn, and explanation recovery after confirmed drift.

### P7. Budget-normalized value

Report symbolic benefit per accepted update, per maintenance attempt, per CPU time, and where possible per labeled evidence volume. A trigger mechanism should be evaluated partly on whether it avoids unnecessary maintenance.

## 7. Design choices that must NOT be made from C/D held-out outcomes

The following must be frozen using design/training/development evidence or external methodological justification:

- drift detector family and hyperparameters;
- monitored signal;
- label latency/maturity;
- persistence/confirmation/refractory policy;
- adaptation evidence horizon;
- replay capacity and sampling/eviction;
- neural update learning rate/epochs/budget/stopping;
- C/D threshold policy;
- symbolic candidate operator;
- gate/sample-size rule;
- confidence update policy;
- lifecycle transitions;
- D-periodic cadence/opportunity budget;
- confirmatory endpoints/statistical test/interval/multiplicity;
- runtime/thread/determinism policy.

Poor C/D held-out performance is not permission to revise these silently.

## 8. Required mechanical invariants

For every matched seed, primary C and D must be able to prove equality of all non-symbolic treatment state:

- initial A checkpoint SHA-256;
- preprocessing identity;
- initial accepted R0.v2 identity;
- stream row order;
- label-availability schedule;
- drift detector inputs;
- drift detector confirmed-event sequence;
- neural adaptation event sequence;
- replay/buffer membership at each update;
- neural update row identities;
- neural optimizer/update budget;
- resulting neural checkpoint hashes;
- non-symbolic RNG policy;
- threshold state when threshold is defined as shared;
- backend/thread/determinism configuration.

A verifier should fail closed on divergence.

## 9. Primary architecture recommendation emerging from the audit

Subject to the later detector/label/adaptation freeze, the lowest-assumption causal architecture is:

```
shared per-seed control plane
  frozen A checkpoint
      |
  ordered stream
      |
  treatment-independent drift monitor
      |
  confirmed event log
      |
  shared replay/buffer + neural updater
      |
  shared neural checkpoint trajectory
      |
      +--------------------+
      |                    |
      v                    v
C: frozen R0.v2       D: evolving Rt
      |                    |
      +------ matched ------+
           evaluation
```

The symbolic treatment must not feed upstream into the shared control plane in the primary experiment.

This architecture operationalizes the statement "C and D differ only in symbolic evolution" as a set of verifiable state-equality constraints rather than a prose intention.

## 10. Remaining blockers before implementation

The following remain unresolved after this audit and belong to the subsequent design-freeze packets:

1. exact stream-time/label-latency model;
2. exact drift-monitor signal and detector;
3. confirmation/persistence/reset/cooldown semantics;
4. exact neural continual-learning/replay procedure;
5. replay capacity/evidence horizon/update budget/stopping;
6. exact C/D threshold policy;
7. exact D symbolic evolution operator/state machine;
8. exact online rule-validation evidence rule and sample-size semantics;
9. exact confidence update semantics;
10. D-periodic cadence/opportunity matching;
11. confirmatory endpoint/statistical/multiplicity freeze;
12. runtime/thread/cost benchmark freeze.

No adaptive implementation should begin until these are reduced to an executable protocol with no material TBD affecting treatment or inference.

## 11. Audit conclusion

The C/D research question remains defensible, but only if symbolic evolution is isolated from every upstream adaptive mechanism.

The most important strengthening action is to make the non-symbolic adaptive trajectory a **shared, hash-verifiable control plane**. This prevents a superficially matched C/D comparison from becoming a comparison of two self-modifying systems with different trigger, replay, label, or neural histories.

The second major strengthening action is to formalize information timing and label maturity before selecting the detector or updater.

The third is to treat replay/forgetting, trigger efficiency, and external scenario replication as publication-strength obligations rather than optional engineering details.

**Gate:** adversarial design audit completed; adaptive implementation remains prohibited pending prospective control freeze.
