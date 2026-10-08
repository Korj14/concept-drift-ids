# C/D Shared Neural Adaptation and Replay Protocol

**Status:** PROSPECTIVE DESIGN FREEZE — SHARED NEURAL CONTROL PLANE  
**Branch:** `stage5-cd-design-audit`  
**Accepted parent:** `main` at `4c13d71a111ce7b72b3ef26a01b2918592425aa1`  
**Date:** 8 October 2026  
**Depends on:** `C_D_STREAM_TIME_CONTRACT.md`, `C_D_DRIFT_MONITOR_PROTOCOL.md`  
**Adaptive held-out execution:** PROHIBITED

## 1. Purpose

This protocol defines the shared neural adaptation received by Systems C and D after a confirmed
primary drift event.

The design objective is not to invent a new continual-learning algorithm. The adaptive neural
control must instead be:

- technically serious enough that System D cannot benefit from comparison against a straw-man C;
- simple enough to audit and reproduce;
- fixed before C/D adaptive held-out outcomes;
- identical for C and D by construction;
- resistant to catastrophic forgetting through explicit replay;
- independent of D symbolic state and C/D fused outputs.

The primary treatment contrast remains:

- C: shared neural trajectory + frozen accepted R0.v2;
- D: **the exact same shared neural trajectory** + evolving symbolic state.

## 2. Neural architecture and immutable substrate

The adaptive model preserves the accepted System-A architecture:

- input: 77 frozen preprocessed features;
- hidden layers: 128 -> 64;
- ReLU activations;
- dropout: 0.10;
- binary logit output.

The primary preprocessing state remains frozen. No imputer/scaler refit occurs.

Every seed begins from its accepted System-A checkpoint identity. All neural parameters are trainable
during an adaptation transaction; no layer is selectively frozen in the primary design.

## 3. Shared-checkpoint principle

C and D do **not** independently run equivalent neural updates.

For each seed/event, the shared control plane executes the neural update once and produces one
versioned checkpoint artifact. Both C and D reference the same checkpoint bytes/hash.

This is stronger than comparing two separately trained models with nominally identical
hyperparameters. It eliminates stochastic training divergence as a possible C-vs-D treatment
difference.

Required lineage:

`theta_(s,0) -> theta_(s,1) -> ... -> theta_(s,k)`

is a single per-seed checkpoint chain shared by C and D.

## 4. Adaptation transaction opening

A transaction opens only after the frozen shared detector emits a confirmed event.

At confirmation:

1. the detector epoch closes;
2. the detector is disarmed under the already frozen response/quarantine rule;
3. the parent neural checkpoint remains active for predictions while the adaptation evidence budget
   becomes available;
4. no second primary detector event is allowed while the transaction is outstanding.

The known synthetic boundary has no role in opening or sizing the transaction.

## 5. Primary current-evidence window

Define the primary current adaptation window size:

`W_current = 10,000 mature labeled observations`.

The current-evidence window for a transaction consists of the **most recent 10,000 observations**
that satisfy all of the following:

- their features have already arrived;
- their labels are mature under the frozen latency schedule;
- their stored prediction was produced by the transaction's parent neural checkpoint;
- their row identity belongs to the adaptive stream;
- they are not future or pending observations.

### 5.1 If 10,000 eligible rows already exist at event confirmation

Snapshot the most recent 10,000 eligible rows immediately.

### 5.2 If fewer than 10,000 eligible rows exist

Keep the parent checkpoint active and continue predicting while the detector remains disarmed.

As additional parent-checkpoint predictions mature, add them to eligibility. When 10,000 eligible
rows exist, snapshot the most recent 10,000 and begin the neural update.

### 5.3 Terminal censoring

If the stream ends before the 10,000-row current-evidence budget is available:

- preserve the confirmed event;
- mark the neural response as right-censored / not executable within the stream;
- do not shrink the window opportunistically;
- do not flush pending labels;
- do not perform a terminal update that cannot affect a subsequent primary-stream prediction.

This is a valid censored experimental trajectory, not a technical failure.

### 5.4 Why 10,000 rows

The fixed budget is prospective and outcome-independent.

It is large enough to provide a nontrivial recent labeled adaptation set under the primary class
imbalance while remaining small relative to the 138,530-row stream. It corresponds to two already
frozen 5,000-row reporting units but is not created by consulting the synthetic boundary.

The 10,000-row adaptation window and 5,000-row reporting window remain logically separate controls.

## 6. Replay memory

Primary replay uses two treatment-independent memory components.

### 6.1 Immutable historical anchor memory

Capacity:

`M_anchor = 10,000 rows`.

Source:

- frozen training partition only;
- selected once before adaptive stream execution;
- uniform row sampling without class conditioning, model-error conditioning, rule conditioning, or
  future information;
- duplicate rows remain eligible as distinct observations under the primary duplicate policy.

Selection RNG namespace/seed is frozen as:

`anchor_seed = 20261008`.

The selected row-identity list and its SHA-256 must be frozen before adaptive held-out execution.

The anchor is immutable throughout the stream.

### 6.2 Online mature-history reservoir

Capacity:

`M_online = 10,000 rows`.

Every adaptively mature stream row is eligible for treatment-independent uniform reservoir admission.

Admission must not depend on:

- neural error;
- attack/benign class;
- fused output;
- symbolic state;
- drift proximity;
- boundary proximity;
- current rule coverage/conflict.

The reservoir may store the mature label because admission occurs only when the label is legally
available, but the label is not used to decide admission.

The reservoir RNG seed is:

`online_reservoir_seed = 20261009`.

Its complete admission/eviction history or an equivalent replayable state record must be preserved.

### 6.3 Replay set used by one update

Primary replay budget:

`W_replay = 10,000 rows`.

The transaction replay set is:

- 5,000 rows uniformly sampled without replacement from the immutable anchor;
- 5,000 rows uniformly sampled without replacement from the eligible online reservoir.

Rows belonging to the current 10,000-row adaptation window are excluded from online replay for that
transaction so the same observation is not deliberately double-weighted.

If fewer than 5,000 eligible online-reservoir rows remain after exclusion, fill the deficit from the
anchor memory without replacement where possible.

Replay-set selection seed:

`replay_sample_seed(event_id) = 20261010 + event_id`,

where `event_id` is the one-based confirmed-event sequence number within that seed trajectory.

### 6.4 Why the replay memory is dual

The immutable anchor protects competence tied to the original training regime.

The online reservoir allows later adaptation events to retain experience from intermediate deployed
regimes rather than replaying only the original training distribution forever.

The design is intentionally simpler than task-aware/error-prioritized replay because model-error or
drift-prioritized admission would add another adaptive selection mechanism and additional
hyperparameters to the primary causal experiment.

## 7. Primary neural update dataset

For each executable transaction:

- current evidence: 10,000 rows;
- replay evidence: 10,000 rows;
- total update dataset: 20,000 rows.

Current and replay evidence therefore have a fixed 1:1 row budget.

No sample receives an additional importance weight based on detector error, symbolic behavior, or
distance from the known boundary.

The primary duplicate/conflict policy remains unchanged: observations are row-level evidence and are
not silently deduplicated or relabeled.

## 8. Loss and class weighting

Loss remains:

`BCEWithLogitsLoss`.

The positive-class weight remains fixed at the original accepted System-A training value:

`pos_weight = 4.138247558496975`.

It is **not** recomputed from the current window or replay set.

Rationale:

- changing the class weight after every event would itself be an additional adaptation mechanism;
- the fixed value preserves the original binary training objective across the neural trajectory;
- the primary scenario was constructed with closely matched pre/post attack prevalence;
- replay already provides historical stabilization.

All C/D matched runs therefore share the same loss definition.

## 9. Optimizer and fixed update budget

Each adaptation transaction initializes a **fresh Adam optimizer** on the parent checkpoint.

Primary update configuration:

- optimizer: Adam;
- learning rate: `1e-4`;
- weight decay: `1e-5`;
- batch size: `1024`;
- epochs: exactly `5`;
- DataLoader workers: `0`;
- all model parameters trainable;
- dropout active at the accepted 0.10 training setting;
- no learning-rate scheduler;
- no early stopping;
- no adaptive epoch selection;
- no gradient accumulation.

The learning rate is one tenth of the original System-A training rate. This is a conservative
fine-tuning response intended to reduce destructive overwriting while replay supplies explicit
retention evidence.

The smaller adaptation batch size is chosen because the fixed update dataset is only 20,000 rows;
retaining the original 4,096-row batch would yield very few optimizer steps per transaction.

With 20,000 rows and batch size 1,024, five epochs provide a bounded nontrivial update of roughly
100 minibatch steps without approaching full retraining from scratch.

These values are frozen prospectively rather than optimized against C/D adaptive held-out outcomes.

## 10. Deterministic training order

Use the existing repository deterministic controls:

- Python seed;
- NumPy seed;
- PyTorch seed;
- deterministic-algorithm request;
- CPU backend in the primary experiment;
- DataLoader `num_workers=0`.

Adaptation shuffle seed:

`adaptation_shuffle_seed(seed, event_id) = 20261011 + 1000 * seed + event_id`.

The complete update-data row list and shuffle seed are serialized.

A rerun of the same parent checkpoint/evidence/configuration must reproduce the same child checkpoint
hash on the frozen primary environment; failure is an implementation/reproducibility defect.

## 11. Optimizer-state policy

The System-A frozen checkpoint does not define a deployable continuation of its historical Adam
moment state.

Therefore every adaptive transaction starts a fresh Adam optimizer.

Optimizer moments are not carried across drift events.

This avoids hidden dependence on unavailable historical optimizer state and makes each update
transaction a deterministic transformation of:

- parent checkpoint;
- current evidence;
- replay evidence;
- frozen update configuration;
- frozen RNG state.

## 12. No performance-based publication gate

After exactly five epochs, the resulting finite candidate checkpoint is the transaction result and is
published.

There is no hidden "publish only if it improves" rule based on current-stream, development, pre-drift
or future evaluation performance.

Rationale:

- a response gate would add another adaptive decision whose objective/threshold would itself require
  prospective validation;
- selecting only favorable updates would bias adaptation-cost and recovery analysis;
- replay plus the conservative fixed update budget provides the primary stability mechanism.

A harmful but protocol-conformant update is a scientific result, not permission to suppress the
checkpoint.

The only reasons a transaction may fail publication are technical invalidity such as non-finite
loss/parameters, corrupt evidence identity, hash/integrity failure, or a violated frozen protocol.

Such a failure follows the project's failed-run/deviation policy.

## 13. Checkpoint publication transaction

For each executable event, preserve at minimum:

- seed;
- event ID and confirmation clock;
- parent checkpoint file/hash;
- parent effective-index range;
- current-window row identities and SHA-256;
- anchor-memory identity/hash;
- online-reservoir snapshot identity/hash;
- replay-set row identities and SHA-256;
- exact positive class weight;
- optimizer/configuration;
- shuffle seed;
- epoch-level training loss;
- child model state;
- child checkpoint SHA-256;
- transaction start/finish cost measurements;
- publication-effective logical index.

The child checkpoint is published no earlier than the next logical prediction after the synchronous
transaction completes.

The child artifact must record its parent hash, producing an immutable checkpoint lineage.

C and D then both reference that one published child checkpoint.

## 14. Detector re-arm consequence

The detector protocol's checkpoint-pure re-arm rule now has an exact neural publication event.

After child checkpoint publication at effective index `p`:

- the parent detector epoch remains closed;
- delayed parent-checkpoint errors that arrive after publication are logged but quarantined;
- the new detector epoch is associated with the child checkpoint;
- its first eligible supervised input becomes available only when a prediction made by the child
  checkpoint has matured under the label-latency contract.

The neural and detector protocols therefore form one explicit causal state machine.

## 15. Catastrophic-forgetting and retention diagnostics

Replay is not assumed successful merely because it is present.

### 15.1 Historical development retention probe

After each published neural checkpoint, score the entire frozen development partition using the
unchanged preprocessing.

This probe is **diagnostic only**:

- it is never used for optimizer stopping;
- never used to accept/reject a child checkpoint;
- never used to change replay;
- never used to change detector behavior.

Report at minimum:

- average precision;
- ROC-AUC;
- MCC;
- F1;
- recall;
- precision;
- FPR.

Thresholded development probe metrics use the seed's fixed accepted System-A monitor threshold so
the retention trajectory is measured against a stable operating rule.

Because development data helped select the initial System-A model/threshold and R0, this is a
historical retention probe, not an independent test set.

### 15.2 Primary-stream pre-regime retention probe

For each published checkpoint, retrospective rescoring of the frozen pre-drift partition is permitted
**only as an offline forgetting diagnostic after the adaptive trajectory is fixed**.

Those rescored predictions must never feed the detector, replay, neural update, threshold selection,
symbolic update, or publication decision.

Report the same metric family and label it explicitly as retrospective checkpoint retention, not
prequential performance.

### 15.3 Forgetting summaries

For a larger-is-better probe metric `M`, report:

- retention delta from the initial checkpoint: `M_k - M_0`;
- forgetting from best historical checkpoint on that fixed probe:
  `max_{h<=k} M_h - M_k`.

These are descriptive longitudinal quantities within seed. Checkpoints/events are not independent
replicates.

## 16. Computational accounting

For every neural transaction, record separately:

- evidence-window waiting rows;
- current/replay row counts;
- optimizer minibatch count;
- CPU training wall-clock time;
- peak process memory where feasible;
- checkpoint serialization time;
- checkpoint size;
- detector-disarmed logical duration attributable to evidence collection and delayed feedback.

Because the primary stream has no trustworthy wall-clock arrival process, compute time is reported as
cost and is not converted into production backlog.

## 17. Prespecified neural-adaptation ablation

A **no-replay sequential fine-tuning** condition is prespecified as a secondary adaptation ablation.

It uses:

- the same 10,000-row current evidence window;
- the same parent checkpoint;
- the same Adam configuration;
- the same learning rate;
- the same batch size;
- the same five epochs;
- the same deterministic controls;

but omits replay rows.

Purpose:

- quantify how much retention/forgetting behavior depends on replay;
- demonstrate that System C's primary replay mechanism is substantive rather than ceremonial.

This ablation is not a replacement candidate for the primary neural trajectory based on favorable
held-out results.

No broad continual-learning method tournament is required for the primary causal paper.

## 18. Why more elaborate continual-learning methods are not primary

Recent NIDS continual-learning work supports replay as a strong retention mechanism and reports
regularization-only/naive sequential updating as substantially more vulnerable to forgetting.

More elaborate task-aware replay, strategic forgetting, A-GEM, DER++, EWC+ER or meta-learning may
improve predictive adaptation in some settings, but they introduce additional:

- task definitions;
- importance functions;
- memory-selection hyperparameters;
- regularization coefficients;
- distillation targets;
- optimization schedules.

The project contribution is symbolic lifecycle causality, not a new neural continual-learning
algorithm. A simple fixed-budget experience-replay baseline therefore provides the cleaner primary
control.

## 19. Literature basis

Relevant recent evidence includes:

- Ansam Khraisat and Gang Li, "Adaptive memory replay for network intrusion detection: Tackling
  data drift and catastrophic forgetting," Computer Networks 272 (2025), 111712,
  DOI 10.1016/j.comnet.2025.111712. The work directly motivates memory replay as a practical
  NIDS continual-learning mechanism.
- Nicholas Costagliola et al., "Replay or Regret: Evaluating Continual Learning Methods for Robust
  Intrusion Detection," MILCOM 2025, DOI 10.1109/MILCOM64451.2025.11310341. Their comparative
  evaluation reports replay as more effective against forgetting than the tested regularization
  strategies and warns that some repair strategies improve selected classes while degrading others.
- O. Delgado et al., "Continual learning for adaptive IoT network intrusion detection via
  domain-incremental learning methods," Applied Soft Computing 203 (2026), 116022. Their
  multi-method evaluation across NIDS datasets reports strong retention for replay-based approaches
  relative to naive/regularization-only updating.
- Xinchen Zhang et al., "Continual Learning with Strategic Selection and Forgetting for Network
  Intrusion Detection," IEEE INFOCOM 2025. This work further demonstrates that replay-memory
  composition and forgetting policy can materially change adaptive NIDS behavior.

These studies justify taking replay seriously. They do not justify choosing a task-aware or
strategically optimized replay method from future C/D outcomes.

## 20. Remaining limitations

The primary replay design is intentionally not claimed to be globally optimal.

Important limitations to disclose:

- the 10,000-row current window is a controlled evidence budget, not a natural task boundary;
- uniform memory may underrepresent rare attack subclasses in later multiclass scenarios;
- the fixed original positive class weight may be suboptimal under substantial future prior drift;
- development retention is conditioned by its historical use in System-A/R0 development;
- replay memory stores historical raw preprocessed observations, which has privacy/storage
  implications outside this benchmark setting;
- the no-replay ablation tests replay necessity but does not exhaust the continual-learning design
  space.

Later datasets/scenarios may require a separately versioned replay policy if task/label semantics make
this binary primary protocol incompatible. Such changes cannot be chosen because they improve the
original held-out result.

## 21. Still unresolved after this packet

The following remain to freeze before adaptive implementation:

- matched C/D operational/fusion threshold policy after neural updates;
- symbolic lifecycle/operator state machine;
- symbolic candidate-generation and independent validation evidence semantics;
- online symbolic support/count/uncertainty gates;
- rule-confidence update semantics;
- D-periodic cadence/opportunity matching;
- final confirmatory endpoints, intervals/tests and multiplicity;
- final runtime/thread/cost benchmark scope;
- exact serialized schemas/verifiers and implementation failure tests.

## 22. Gate

**Shared neural adaptation/replay packet: FROZEN.**

Adaptive implementation remains prohibited.

The next packet is the matched C/D operational/fusion-threshold policy, followed by the symbolic
lifecycle design.
