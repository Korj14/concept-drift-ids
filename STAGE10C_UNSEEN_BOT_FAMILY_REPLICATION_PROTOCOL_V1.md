# Stage-10C Controlled Unseen Bot-Family Introduction Protocol v1

**Status:** PROSPECTIVELY FROZEN BEFORE ANY STAGE-10 TREATMENT EXECUTION  
**Protocol ID:** `stage10c-unseen-bot-introduction-v1`  
**Scenario ID:** `cicids2017_controlled_unseen_bot_v1`  
**Stage-10 treatment execution:** PROHIBITED UNTIL STAGE-9.5 FORMAL CLOSURE  
**Stage-8/9 and Stage-10A/B evidence superseded:** NO  
**Treatment outcomes used to select source/scenario/parameters:** NONE

## 1. Scientific question and scope

Does the accepted drift-gated, validated, versioned symbolic lifecycle add
measurable value beyond an otherwise matched adaptive neural detector with
frozen symbolic knowledge when the binary attack class changes from an
historically **seen** DoS GoldenEye family to an historically **unseen** Bot
family, while benign background variation and attack-prevalence changes
are tightly controlled at the flow-feature level?

This is a prospectively controlled **unseen-family introduction** and
attack-family replacement test. It is **not** a natural sequence of evolving
attacks, a natural production stream, proof of formal `P(Y|X)` change,
or external-environment replication. Friday BENIGN background is deliberately
interleaved and sampled across regimes; original chronological row timing
is not preserved. The design cannot distinguish a family-mechanism effect
from all attack-source/day/port signatures. These limitations must remain
explicit in the manuscript.

The master Stage-10+ v1.1 protocol, MAIN doctrine, and Reconciled Plan govern.
The scenario does not alter accepted Stage-8/9 conclusions and cannot
substitute for future independent-dataset validation.

## 2. Frozen raw inputs

Use only:

- Wednesday `Wednesday-workingHours.pcap_ISCX.csv`, 225,166,395 bytes,
  SHA-256 `893c27dc968bf7a8adef1689f90be55ca4a4dc3088fb63d6ff247ac56856df2a`,
  source_order=2;
- Friday `Friday-WorkingHours-Morning.pcap_ISCX.csv`, 58,316,725 bytes,
  SHA-256 `53a41c24d570ea83b7ac55b2e94df94e7a8216aeb80a2af0246b6bc8bb543000`,
  source_order=5.

The accepted multiclass labels remain the audit truth. The model target is
binary: BENIGN=0 and GoldenEye/Bot=1. No corrected CICIDS, majority
relabeling, silent deduplication, feature refitting, or newly introduced
metadata feature may be used.

## 3. Historical initial-model firewall

Keep exactly the frozen historical training/development split:

- training: Monday all, Tuesday all, Wednesday source rows `[0,346352)`;
- development: Wednesday source rows `[346352,554162)`.

DoS GoldenEye is present in accepted training (1,118) and development
(2,013). Bot is **absent** from both; in the accepted raw-file manifest all
Bot-labeled flows occur in Friday morning, which was not included in the
initial train/development provenance.

Starting state is the accepted seed-specific System-A weights,
training-only preprocessing, R0.v2 and preselected thresholds. Required
inherited manifest identities:

- preprocessing core `4527f77220f2cf6063108a7d71d80aaa0e82099ad282ff25408a2d9ce3488b1e`;
- System-A manifest `42004b5ed100b690023b9998bdc959fac41ab947b996fb7c58e44cee5e8dc6de`;
- R0.v2 manifest `131027d2f136494eb388183f18dcb7eb0e9d7e9fe786f22dba25f4e1624c1483`.

The initial rule base may happen to cover unseen-family flows by feature
similarity. "Unseen" means **absent from historical labeled initial
training/development**, not logically guaranteed noncoverage by R0.

## 4. Fixed evaluation source pools

Pre and post scoring regimes have **69,260** and **69,270** ordered rows,
respectively. Both have exactly **1,966 attack rows**.

Source pools are established once, independently of any treatment:

1. Wednesday `[554162,623433)` contains 3,589 DoS GoldenEye flows
   after the accepted historical-development end and the same frozen
   Heartbleed exclusion region. Choose exactly 1,966 GoldenEye flows
   by `goldeneye[floor(k*3589/1966)]` for `k=0..1965` from the sorted
   source-row indices. No Wednesday `[0,554162)` row is eligible.
2. Friday morning has 189,067 BENIGN and 1,966 Bot flows. Preserve all
   1,966 Bot flow feature vectors and source order for the post pool.
   No Bot flow is eligible for pre or historical starting-state evidence.
3. Enumerate all Friday BENIGN rows by ascending source-row index. Assign
   even zero-based BENIGN ordinals to the pre **candidate** pool and odd
   ordinals to post candidates. This partitions background source rows
   disjointly while sampling across the same Friday collection.
4. Select exactly 67,294 pre BENIGN from the even-ordinal candidate pool,
   using candidate index `floor(k*len(even_pool)/67294)` for
   `k=0..67293`.
5. Select exactly 67,304 post BENIGN from the odd-ordinal candidate pool,
   using `floor(k*len(odd_pool)/67304)` for `k=0..67303`.

Every selected Friday BENIGN flow occurs in at most one regime. The pre
GoldenEye and post Bot source sets do not overlap either training/development
or one another. All source-order/row-id provenance is retained as
evaluation-only metadata, not model features.

The pre attack fraction is 1,966/69,260 and post is 1,966/69,270;
no future-dependent attack rows are dropped to improve predictive outcomes.

## 5. Deterministic attack-position insertion

For regime size `N` and `K=1966`, attack slot for attack ordinal `k`
is:

`slot(k,N) = floor((2*k+1)*N/(2*K)), k=0..1965.`

These distinct integer slots are derived without treatment results,
randomized hash state, detector alarms, or labels at runtime. For each
regime, place the selected attack flow at its designated slot in ascending
source-row order. Fill the remaining slots with its selected Friday BENIGN
flows in ascending source-row order.

No row is resampled with replacement. The insertion creates a synthetic
regular attack-rate pattern—an important limitation, not an empirical
property of natural Bot traffic.

- Pre: 67,294 Friday BENIGN + 1,966 Wednesday GoldenEye.
- Post: 67,304 Friday BENIGN + 1,966 Friday Bot.
- Reference change is at global logical stream index **69,260**, **evaluator
  only**. Total stream length **138,530**.

The source-only audit fixes all selected source-row, attack-slot, full-stream,
and ordered `(source_order,row_in_source)` SHA-256 identities using the
repository's little-endian signed-int64 contract.

## 6. Source-only design diagnostics

Preselection was based on the scientific challenge, source provenance,
adequate attack counts for the frozen 10,000-row lifecycle evidence windows,
and a stable benign background—not on treatment outcomes.

77-feature raw-source class-conditional two-sample KS diagnostics:

- Friday BENIGN pre vs post: mean **0.002478607776839007**,
  median **0.002945025924851352**, max **0.006115708493194316**,
  **0/77** features KS >= 0.10;
- selected Wednesday GoldenEye vs all Friday Bot: mean
  **0.4964198156972249**, median **0.6347914547304171**,
  max **1.0**, **58/77** features KS >= 0.10.

In particular, Destination Port attains KS=1.0 between attack families;
the difference therefore includes strong feature/port/source signatures,
not a source-independent causal demonstration of attack behavior evolution.

These are scenario-construction diagnostics only. They must not be reported
as ADWIN detections, future-treatment performance, or proof of a
natural conditional-label drift.

## 7. Pre-outcome information and causal isolation

The source designer may inspect original multiclass labels **solely** to
construct and source-audit the prospective scenario. The *running learner*
may never see original multiclass family labels, candidate-pool selectors,
source identities, even/odd partition membership, regime index, injected
attack slot, or known boundary. It receives the frozen 77 feature vector,
commits its prediction, and only receives the binary target after the
accepted **5,000-row** maturity delay (or separately frozen sensitivity).

No future Bot label may reach the historical checkpoint/R0, preprocessing,
neural replay, ADWIN, symbolic-generation evidence, or validation before its
logical maturity. Pending labels are never flushed merely because the
source regime changes. No detector, model, queue, or symbolic state resets
at the evaluator-only boundary.

## 8. Frozen treatment arms and update mechanism

- **C:** matched adaptive neural + frozen R0.v2;
- **D-drift:** exactly the same neural trajectory + ADWIN drift-gated
  validated/versioned symbolic lifecycle;
- **D-periodic:** matched neural trajectory + same symbolic operator/budget
  on previously frozen periodic maintenance clocks.

Seeds remain exactly **0,1,2,3,4**, paired within each scenario.
Within seed, the C/D neural starting checkpoint, scaler, stream rows and
labels, label-release clock, ADWIN/neural-only error signal, replay/anchor
row identities, update budgets/RNG, neural weights and publication clocks,
fusion mechanism, and thresholds must match. Symbolic evolution is the
intended treatment difference. If non-symbolic state differs, preserve and
invalidate the pair as Class A.

Inherit ADWIN delta=.002 and clock=32, 5,000-row label latency,
10,000 current-evidence/replay capacity, 5,000 anchor plus 5,000 online
neural update sample, Adam learning rate 1e-4, batch1,024, five epochs,
frozen lambda=.50, accepted per-seed thresholds, 10,000 candidate generation
and distinct later 10,000 mature validation rows, and maximum four symbolic
maintenance opportunities. All treatment availability/budget rules are
unchanged unless a prospectively documented incompatibility correction
is frozen **before** any Stage-10 outcome access.

Neither alerts nor fused/symbolic outputs may influence supervised-label
release or neural adaptation in the primary contrast.

## 9. Confirmatory family, diagnostics, and interpretation

Preserve the accepted Stage-8 E1/E2/E3 definitions, with **the entire
69,270-row post-Bot regime** as the primary post estimand:

- E1: D-drift minus C on post MCC;
- E2: D-drift minus C on post MCSC;
- E3: D-drift minus D-periodic on post MCSC.

Report all five paired seed effects, signed effect means/SD, 95% paired
t interval, directional sign tests, and Holm familywise correction.
The five paired seeds are the causal unit. Do not treat 5,000-row windows,
events, rule versions, or bootstrap replicates as additional causal units.
Do not add seeds, replace the family, or redefine the endpoint after outcome
access. Retain unfavorable, negative and null findings.

Mandatory descriptive secondary diagnostics include per-regime
attack recall/FNR, confusion and calibration, attack-conditional symbolic
coverage/correctness, novelty response/latency relative to known reference,
separate first 5,000/10,000 mature-label regions, ADWIN/no-event rates,
rule proposals/validations/rejections, authority withdrawal and version
history, MCSC components, cost, timing, censoring, and operational
limitations. The first-window and zero-shot period are descriptive,
not a post hoc confirmatory primary endpoint.

Stage-10C evidence is reported separately from Stage-8/9 and Stage-10A/B;
any cross-scenario pooling is secondary and requires a separately defensible
shared estimand. No claim of universal symbolic benefit, ADWIN trigger
superiority, architecture invariance, or natural deployment generalization
is licensed by this controlled scenario alone.

## 10. Hard stop and implementation limits

Only source-only protocol, raw-data audit, static tests, provenance and
engineering assurance are permitted now. No C/D/D-periodic treatment,
model predictions, detector performance, or symbolic adaptation results
may be generated or accessed until Stage-9.5 legitimately closes.

The source-only verifier must independently rebuild these row selections,
attack slots, stream identity hashes, source labels and class-conditional
KS statistics from exact raw bytes. It must explicitly set:

`stage10_treatment_outcomes_accessed=false`,
`stage10_treatment_execution_authorized=false`.

A pass is **not** proof of a tested Stage-10C adaptive loader. Before any
eventual treatment run, a separate implementation handoff must establish
correct source-aware feature assembly, exact inherited checkpoint and
R0 availability, fixed label/metadata firewall, per-seed matched-state
verification, write-once evidence, and execution freeze on an exact head
after the Stage-9.5 hard gate closes.

The Stage-9.5 assurance detour remains parked and unresolved; this
pre-outcome package does not weaken or bypass its closure criteria.
