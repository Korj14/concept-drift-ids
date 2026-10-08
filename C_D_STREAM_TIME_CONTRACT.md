# C/D Stream-Time and Information-Availability Contract

**Status:** PROSPECTIVE DESIGN FREEZE — INFORMATION TIMING ONLY  
**Branch:** `stage5-cd-design-audit`  
**Accepted parent:** `main` at `4c13d71a111ce7b72b3ef26a01b2918592425aa1`  
**Date:** 8 October 2026  
**Adaptive held-out execution:** PROHIBITED

## 1. Purpose

This contract defines exactly when information exists in the prospective adaptive experiment.

It is deliberately frozen **before** choosing the primary drift-monitor signal, detector family, neural updater, replay policy, or symbolic lifecycle operator. Those later components must fit inside this information-time contract; the timing contract must not be retrofitted to make a preferred detector or updater easier to use.

The purpose is to prevent:

- same-row label leakage;
- post-trigger lookahead;
- synthetic-boundary leakage;
- treatment-dependent label/evidence acquisition;
- retrospective rescoring masquerading as prequential error;
- adaptation-window use of observations or labels that were not yet available;
- crediting an update with predictions made before the update could have been published.

## 2. Governing facts and constraints

### 2.1 Scenario chronology is row-order, not wall-clock time

The frozen scenario manifest states:

- chronology is pseudo-chronological;
- source-file order and original row order are preserved;
- timestamps are unavailable in the MachineLearningCSV feature tables used by the project;
- true timestamp chronology is not claimed.

Therefore the adaptive experiment uses an **observation-count logical clock**. No wall-clock label delay, SOC investigation time, packet-arrival rate, or real-time throughput claim may be inferred from this scenario.

### 2.2 Stream identity

The primary adaptive stream is the uninterrupted ordered concatenation:

`pre_drift -> post_drift`

with:

- pre-drift rows = 69,260;
- post-drift rows = 69,270;
- total stream rows = 138,530;
- logical row indices = 0 through 138,529.

The first post-drift row therefore has evaluator-side logical index 69,260.

That index and the pre/post partition identity are **scoring metadata only**. They must not be supplied to the detector, neural updater, replay selector, symbolic updater, threshold updater, or any adaptive decision rule.

### 2.3 No reset at the known synthetic boundary

The detector state, label queue, replay/buffer state, neural state, symbolic state, RNG state, and any other adaptive state continue through the synthetic boundary without reset or flush.

A boundary-triggered reset would leak the known change point and is prohibited.

## 3. Logical clock

Let `t` denote the zero-based logical index of the row currently being predicted.

Each stream row has:

- immutable audit identity;
- feature vector `x_t`;
- hidden true label `y_t`;
- prediction-time model/rule state identities;
- a label-maturity index defined below.

Audit identity may use repository provenance metadata such as source/row identity for hashing and reproducibility. Such metadata is not a model feature and may not influence adaptation decisions unless a later protocol explicitly defines a treatment-independent audit operation.

## 4. Primary label-availability model

### 4.1 Primary verification latency

The primary experiment uses a deterministic fixed verification latency of:

`L = 5,000 rows`

For a row predicted at logical index `j`, its label becomes mature at:

`m(j) = j + L`

If `m(j) < N`, where `N = 138,530`, `y_j` becomes visible to adaptive components **only after the prediction at logical index `m(j)` has been committed**.

If `m(j) >= N`, the label is never released to adaptive components during that stream execution.

### 4.2 Why row latency is used

The dataset does not provide a defensible wall-clock chronology for this experiment. A fixed row-count latency is therefore a controlled simulation assumption, not an empirical estimate of analyst/SOC turnaround time.

The value 5,000 is chosen prospectively because:

1. it creates a material nonzero separation between prediction and supervision rather than preserving an immediate-label oracle;
2. it reuses an already frozen stream granularity rather than introducing a new outcome-sensitive temporal scale;
3. it remains small relative to each approximately 69k-row pre/post regime, allowing delayed adaptation to remain observable;
4. its exact effect will be exposed through prespecified latency sensitivity rather than treated as universally realistic.

The numerical equality between this latency and the primary 5,000-row reporting window is **not a semantic coupling**. Reporting windows and label maturity are separate mechanisms and must be represented separately in code/configuration.

### 4.3 Primary label coverage

The primary timing experiment assumes **complete eventual supervision** subject to the fixed delay.

There is no alert-conditioned or active-learning label selection in the primary C/D causal contrast.

Rows in the final `L` positions are right-censored with respect to adaptive label availability: their labels are never mature during the adaptive run.

This is a controlled delayed-label experiment, not a claim that real deployments label every flow.

### 4.4 Prespecified latency sensitivity

The later robustness package must include, subject to computational feasibility:

- `L = 0`: oracle-latency sensitivity, still using test-then-update ordering;
- `L = 10,000`: stronger delayed-supervision stress.

These are robustness conditions, not alternative primaries selected from C/D held-out performance.

A partial-label / sampled-label condition is not part of the primary design because it would introduce a second evidence-acquisition treatment. It may be added later only as a separately frozen robustness experiment.

## 5. Per-row prequential order

For every logical stream index `t`, the primary experiment follows this order.

### Step 1 — snapshot active state

Record the identities of the states that will produce the prediction at row `t`:

- neural checkpoint/state;
- C symbolic state or frozen R0.v2 identity;
- D symbolic rule-base version;
- threshold/fusion state where applicable;
- detector state before consuming row-`t` evidence.

### Step 2 — observe current features

Expose `x_t` to the predictor.

Do **not** expose `y_t`, pre/post partition identity, synthetic-boundary flag, or future rows.

### Step 3 — predict before supervision

Produce and persist:

- neural score/probability;
- neural decision under the monitor-relevant decision rule if needed;
- C fused output;
- D fused output;
- symbolic activation/abstention trace where applicable;
- all state/version identities used for those outputs.

The prediction record is immutable once committed.

### Step 4 — commit the prediction event

Only after prediction persistence is the current clock allowed to release supervision or perform adaptive actions.

No later model state may replace the original prediction for prequential error calculation.

### Step 5 — release newly mature labels

Release every label whose maturity index equals `t`.

For the primary fixed-lag schedule there is at most one newly mature label per clock index after warm-up.

For `L = 0` sensitivity, the current row's label is released here, after its prediction, which preserves test-then-train semantics.

### Step 6 — construct legally available drift-monitor evidence

The exact primary detector signal is not frozen by this document.

However:

- a label-free signal based on `x_t` and/or a treatment-independent neural-only prediction may become available after the row-`t` prediction;
- a supervised signal based on row `j` cannot become available before `y_j` matures;
- any supervised prequential error/loss for row `j` must be computed from the **prediction actually stored when row j originally arrived**, not by rescoring `x_j` with a later adapted model;
- C/D fused outputs and D symbolic state are forbidden detector inputs in the primary causal comparison.

### Step 7 — update detector and confirm events

The future detector protocol must define the exact update order and event-confirmation rule.

Any event confirmed at logical clock `t` has causal availability time `t`, regardless of the origin indices of delayed labels contributing to the statistic.

The detector may not be credited with an earlier event time by retrospectively assigning the event to the observation time of a delayed label.

### Step 8 — determine update eligibility

A confirmed event may make a neural and/or symbolic maintenance action eligible under the later frozen protocols.

At logical clock `t`, an update may use only:

- observations with origin index `<= t`;
- labels whose maturity index is `<= t`;
- historical training/development evidence legally frozen before stream execution;
- treatment-independent audit metadata solely where explicitly permitted.

It may not use any future stream row or any pending label.

### Step 9 — execute update under the later frozen protocol

The exact adaptation-window construction, replay policy, neural update procedure, symbolic generation/validation procedure, and update budget remain to be frozen.

If an update requires collecting additional post-trigger evidence, the old active state remains in force until that additional evidence has arrived, matured where required, and the update has completed.

### Step 10 — publish new state

A new neural, symbolic, or threshold state produced from clock-`t` evidence may become effective **no earlier than prediction index `t + 1`**.

The current row's prediction is never recomputed or replaced.

Every publication must record the causal evidence cutoff and publication-effective index.

## 6. Information-availability table

| Information | Available at current prediction? | Available after prediction at t? | May affect future adaptation? |
| --- | --- | --- | --- |
| `x_t` | Yes | Yes | Yes, subject to later protocol |
| `y_t` primary L=5000 | No | No, unless t is its maturity clock in another run convention | Only at maturity |
| mature `y_j`, j+L=t | No for prediction t | Yes | Yes |
| stored neural prediction from row j | Historical | Yes | Yes for treatment-independent monitoring |
| C fused prediction | Yes for C output | Yes | No upstream primary control-plane decisions |
| D fused prediction / D symbolic state | Yes for D output | Yes | No upstream primary control-plane decisions |
| synthetic-boundary flag | No | No to adaptive components | Never |
| pre/post partition label | No | No to adaptive components | Never |
| future row `x_{t+k}` | No | No | Never before arrival |
| pending label with maturity > t | No | No | Never before maturity |
| audit row identity/hash metadata | Audit only | Audit only | Only for integrity/equality verification |

## 7. Separation of adaptive labels from evaluation labels

The adaptive system and the offline evaluator use different logical label channels.

### Adaptive label channel

Labels are visible only according to the maturity schedule above.

This channel controls any supervised drift signal, replay admission requiring labels, neural supervised adaptation, rule class precision, and any other label-dependent adaptive statistic.

### Evaluation label channel

The offline scorer may use all true labels **after predictions are frozen** to compute detection and explanation metrics.

Evaluation labels may never feed back into the running adaptive state before their adaptive maturity time.

This separation must be enforced mechanically in implementation rather than relying only on programmer discipline.

## 8. Boundary-crossing label maturity

No label queue flush occurs at the synthetic boundary.

Consequently, under primary `L=5000`:

- some pre-drift labels mature after post-drift observations have already begun;
- the first post-drift label cannot mature until 5,000 post-drift rows have been predicted;
- a supervised detector therefore cannot legitimately react to post-drift ground truth before that latency has elapsed.

This is intended. It prevents the evaluator-known boundary from becoming an implicit oracle.

## 9. End-of-stream handling

At the end of the 138,530-row stream:

- do not flush pending labels into the adaptive components;
- do not perform a terminal adaptation that cannot affect any subsequent primary-stream prediction;
- preserve pending-label counts and identities as right-censored adaptive evidence;
- the offline evaluator may still use their true labels to score already-frozen predictions.

A separate post-stream training exercise, if ever studied, would be a different experiment.

## 10. Synchronous logical execution

Because the scenario lacks trustworthy event timestamps, the primary experiment does not simulate flows arriving while an update job consumes wall-clock time.

The logical stream pauses between row predictions while any synchronous maintenance job runs.

Therefore:

- publication occurs at the next logical row at earliest;
- measured neural/symbolic update wall-clock cost is reported separately;
- no claim is made that the system can process a production arrival rate without backlog;
- no rows are dropped or silently buffered because of compute duration in the primary logical simulation.

A true asynchronous/throughput deployment simulation would require defensible arrival timestamps and is outside this scenario's evidentiary scope.

## 11. Detector-signal consequences of this contract

The next design packet may compare candidate signals/detectors, but they must satisfy this contract.

### Admissible supervised class

A treatment-independent neural-only prequential loss/error stream is admissible if it:

- uses the prediction stored at original observation time;
- updates only when the associated label matures;
- is identical for matched C/D runs;
- never uses fused C/D output.

### Admissible label-free class

A treatment-independent covariate, representation, or neural-score distribution statistic is admissible if it:

- uses only currently arrived information;
- is identical for matched C/D runs;
- does not use the synthetic boundary;
- is described accurately as detecting distribution/prediction shift rather than automatically proving a change in `P(Y|X)`.

### Not admissible in the primary causal contrast

- D symbolic confidence/conflict/coverage as the upstream drift signal;
- C/D fused prediction error as separate detector signals;
- alerts used to decide which labels become available;
- post-hoc rescoring of historical rows with the current model to fabricate an earlier error stream.

## 12. Required event provenance for implementation

The later implementation must make it possible to reconstruct every causal event.

At minimum, prediction, label-release, drift, update, and publication records must contain enough information to recover:

- logical clock index;
- row/audit identity;
- observation-origin index for delayed evidence;
- label maturity index;
- prediction-state identity;
- stored neural prediction/score required by the chosen detector;
- detector state/event identity;
- trigger/confirmation index;
- evidence cutoff;
- matured-label cutoff;
- adaptation generation/validation row identities;
- old/new neural checkpoint identities;
- old/new symbolic version identities;
- publication-effective index;
- failure/deviation reason where applicable.

The exact serialized schema will be frozen before implementation.

## 13. Statistical interpretation

Detection delay, recovery time, update latency, and explanation recovery must use causal availability/publication time rather than retrospective origin time.

In particular:

- drift-event delay is measured to the **confirmed event clock**;
- neural/symbolic recovery cannot be credited before the relevant updated state is published;
- windowed evaluation remains based on prediction-origin rows;
- reporting windows remain repeated observations, not independent replicates;
- label delay sensitivity is a robustness factor, not a source of additional independent sample size.

## 14. Limitations intentionally retained

This contract does not claim operational realism beyond what the data support.

Known limitations:

- row-count latency is not wall-clock latency;
- complete eventual supervision is optimistic relative to many SOC environments;
- the synchronous logical stream does not model throughput/backlog during adaptation;
- a fixed delay is simpler than real heterogeneous investigation delays;
- CICIDS2017 source ordering is pseudo-chronological, not production chronology.

These limitations are preferred to inventing unsupported timestamps or label processes.

## 15. Freeze decisions from this packet

The following are now frozen prospectively for the primary C/D experiment:

1. logical clock = ordered stream row index;
2. continuous `pre_drift -> post_drift` adaptive stream;
3. no reset/flush at synthetic boundary;
4. prediction-before-label-release prequential order;
5. primary label latency `L=5000` rows;
6. complete eventual label coverage subject to delay and terminal censoring;
7. no alert-conditioned label acquisition;
8. label release only after prediction at maturity index;
9. supervised monitoring uses stored original prediction, never later rescore;
10. only observed rows and mature labels may enter adaptive evidence;
11. new state effective at next logical prediction at earliest;
12. no end-of-stream adaptive queue flush;
13. offline scoring labels are separated from adaptive label availability;
14. synchronous logical update semantics, with compute cost reported separately;
15. latency sensitivities `L=0` and `L=10000` are prespecified robustness conditions.

## 16. Still unresolved after this packet

This contract intentionally does **not** freeze:

- primary drift-monitor signal;
- detector family/hyperparameters;
- detector warm-up/reference state;
- persistence/confirmation/reset/refractory policy;
- adaptation evidence horizon/window;
- replay buffer;
- neural update procedure/budget/stopping;
- C/D matched threshold policy;
- symbolic evolution lifecycle;
- symbolic validation count/uncertainty rule;
- D-periodic cadence;
- final inference/multiplicity plan.

Those must be resolved in later prospective design packets without violating this timing contract.

## 17. Literature context

The timing freeze is motivated by methodological evidence, not by borrowing an arbitrary latency value from another dataset.

- Komorniczak, Ksieniewicz & Zyblewski, *Pattern Recognition* 172 (2026), 112516, DOI 10.1016/j.patcog.2025.112516, show that stream-processing framework and delayed-label handling materially affect evaluation conclusions and criticize unrestricted immediate-label assumptions.
- Cassales et al., *Digital Signal Processing* 182 (2026), 106325, DOI 10.1016/j.dsp.2026.106325, specifically survey concept-drift detection under delayed and partial labels.
- Pederzoli et al., *IEEE Access* 13 (2025), 197899-197911, DOI 10.1109/ACCESS.2025.3633419, demonstrate that delayed and sampled labels are already an explicit NIDS operating constraint and evaluate multiple delay levels.

These papers support treating label availability as a first-class experimental variable. They do not establish that 5,000 rows is a real-world SOC delay for CICIDS2017; this project therefore states that value only as a controlled prospective simulation assumption.

## 18. Gate

**Stream-time / information-availability packet: FROZEN.**

This packet does not authorize adaptive implementation.

The next design packet is the treatment-independent drift-monitor signal/detector audit under the timing rules above.
