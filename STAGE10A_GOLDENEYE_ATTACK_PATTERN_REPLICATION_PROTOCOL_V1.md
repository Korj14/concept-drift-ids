# Stage-10A GoldenEye Attack-Pattern Replication Protocol v1

**Status:** PROSPECTIVELY FROZEN PRE-OUTCOME PROTOCOL  
**Protocol ID:** `stage10a-goldeneye-attack-pattern-v1`  
**Scenario ID:** `cicids2017_goldeneye_temporal_attack_shift_v1`  
**Stage-10 treatment execution:** PROHIBITED UNTIL STAGE 9.5 LEGITIMATELY CLOSES  
**Accepted Stage-8/9 evidence modified:** no  
**Stage-10 treatment outcomes accessed while preparing this protocol:** no

## 1. Scientific purpose

Stage 10A addresses the largest external-validity limitation of the accepted
`sudden_benign_v1` evidence: that scenario is dominated by a controlled BENIGN
source-regime/covariate shift. Stage 10A asks whether the already accepted
drift-gated symbolic lifecycle transfers to a stream in which the directly
observed distributional change is concentrated in the retained attack family
rather than being manufactured by replacing the BENIGN source regime.

The prospective question is:

> Under a fixed CICIDS2017 pseudo-chronological stream with an essentially
> stable BENIGN background and a same-family DoS GoldenEye attack-pattern
> shift, does drift-gated symbolic lifecycle maintenance add measurable value
> beyond an otherwise matched adaptive-neural trajectory with frozen symbolic
> knowledge, while preserving honest longitudinal explanation reporting?

This is an **attack-pattern / class-conditional-shift replication**. The
source-only diagnostics do not by themselves prove natural production drift or
an unconditional change in `P(Y|X)`. Those stronger wordings are prohibited
unless later evidence independently warrants them.

## 2. Authority and non-replacement rule

Scientific interpretation remains subordinate to
`MAIN - Concept_Drift_NIDS_Research_Gap_Doctrine.docx`. Operational behavior is
subordinate to `Reconciled_Pre-Stage_3_and_Stage_3_Implementation_Plan.docx`
and `STAGE10_PLUS_MASTER_REPLICATION_SENSITIVITY_PROTOCOL_V1_1.md`.

This protocol does not reopen or replace accepted Stage-8/9 evidence. Null,
mixed, or unfavorable Stage-10A findings remain valid evidence. No seed,
endpoint, threshold, scenario row, detector parameter, symbolic gate, or
analysis family may be changed after Stage-10A treatment-outcome access to
improve the result.

## 3. Execution firewall

This protocol may be inspected, tested, and source-audited while Stage 9.5 is
parked. It does **not** authorize C/D/D-periodic treatment execution.

Stage-10A treatment execution may begin only after the governing Stage-9.5 hard
gate is legitimately closed. Until then:

- no Stage-10A C/D/D-periodic predictions may be generated;
- no Stage-10A adaptive treatment metrics may be viewed;
- no Stage-10A symbolic lifecycle outcome may be viewed;
- no treatment-dependent scenario change is permitted.

The source-only readiness verifier introduced with this protocol stops before
any adaptive model execution.

## 4. Scenario identity

### 4.1 Raw source

Dataset: CICIDS2017 MachineLearningCSV working-day representation.

The Stage-10A evaluation stream uses only
`Wednesday-workingHours.pcap_ISCX.csv`.

Frozen raw identity:

- size: 225,166,395 bytes;
- SHA-256:
  `893c27dc968bf7a8adef1689f90be55ca4a4dc3088fb63d6ff247ac56856df2a`.

The accepted raw CICIDS manifest remains the authority for all eight original
source files. Corrected or deduplicated CICIDS is not substituted here.

### 4.2 Training and development inheritance

Stage 10A reuses the accepted historical training/development information set,
training-fitted preprocessing state, System-A seed checkpoints, R0.v2 symbolic
starting state, and development-selected thresholds. The evaluation stream
starts strictly after the accepted development range.

Frozen inherited identities include:

- preprocessing core state:
  `4527f77220f2cf6063108a7d71d80aaa0e82099ad282ff25408a2d9ce3488b1e`;
- System-A manifest:
  `42004b5ed100b690023b9998bdc959fac41ab947b996fb7c58e44cee5e8dc6de`;
- R0.v2 manifest:
  `131027d2f136494eb388183f18dcb7eb0e9d7e9fe786f22dba25f4e1624c1483`.

No initial model, preprocessing state, R0 rule, or threshold is selected using
Stage-10A treatment outcomes.

## 5. Exact source construction

Chronology is pseudo-chronological source-row order. True timestamp chronology
is not claimed.

### Pre regime

- Wednesday source rows: `[554162, 623433)`;
- frozen Heartbleed exclusion: 11 rows;
- retained rows: 69,260;
- BENIGN: 65,671;
- DoS GoldenEye: 3,589.

### Post regime

- Wednesday source rows: `[623433, 692703)`;
- no synthetic BENIGN replacement;
- retained rows: 69,270;
- BENIGN: 65,697;
- DoS GoldenEye: 3,573.

The post regime is the original Wednesday source data in source-row order. No
Thursday rows are introduced.

The evaluator-only boundary is logical stream index **69,260** after the frozen
pre-regime Heartbleed exclusion. The boundary must never be supplied to the
drift detector, neural adaptation controller, replay policy, or symbolic
lifecycle.

Frozen row identities use the repository's little-endian int64 hashing
convention:

- pre included row IDs:
  `ef7773f88374c82a663723c0c1125f4a8bfee75a58fe4d8e35355b492e07b354`;
- post included row IDs:
  `186aec7f816faca89484c537b77ed8e729a9ac55982a7e1bec6f37750c1c30d8`;
- pre GoldenEye row IDs:
  `15fd308926f6fda0d74639fc9e55176ab4f97b51ec575f7763512a080a5ae5f2`;
- post GoldenEye row IDs:
  `bc584d69c0fdb7040a2a40ef105eea4cb514555872719718abeb21ee3c837646`;
- full stream row IDs:
  `81924f3c39cb49adfaebea11d9aef045ab73804dd61faee49dcfbd2dd5f33f25`;
- `(source_order,row_in_source)` stream pairs:
  `b6c3b7a14a08be6c6b186ed339a1f205cdff49d48de6fa16ce44cc776796c6a7`.

## 6. Why this is Stage 10A rather than another benign-source shift

The source-only audit was performed before any Stage-10 treatment outcome.

Attack prevalence is closely matched:

- pre: 0.051819231879873;
- post: 0.051580770896492;
- post-minus-pre: -0.023846098338 percentage points.

Across the same frozen 77 flow features:

- BENIGN pre/post mean KS: 0.002870611029698;
- BENIGN median KS: 0.002951515237810;
- BENIGN maximum KS: 0.010175276582649;
- BENIGN features with KS >= 0.10: 0;

while DoS GoldenEye shows:

- mean KS: 0.083928081902581;
- median KS: 0.111367983319995;
- maximum KS: 0.215376585653664;
- features with KS >= 0.10: 44;
- features with KS >= 0.20: 1.

This contrast is scenario-design evidence only. It may justify describing the
stream as attack-pattern-shift dominant. It must not be reused as an adaptive
treatment outcome or presented as proof of natural production drift.

Source-audit canonical SHA-256:
`5738c65009c22ef57845ba1adf06bfca198098af0d404120a76d958ac5998275`.

## 7. Target and information timing

Binary target remains:

- `BENIGN -> 0`;
- retained non-BENIGN attack -> `1`.

The original multiclass label remains available for audit/reporting.

The primary information-timing contract remains test-then-update. The accepted
label latency remains 5,000 logical rows. A row's label becomes usable only
after its prediction is committed and the frozen latency has matured.

No future label may influence preprocessing, initial model state, source
construction, detector state, replay contents, neural update eligibility,
candidate generation, symbolic validation, or threshold selection before its
permitted logical time.

## 8. Matched treatment structure

Primary arms retain the accepted causal isolation:

- **C:** adaptive neural trajectory + active frozen R0.v2;
- **D-drift:** the same neural trajectory + drift-gated symbolic lifecycle;
- **D-periodic:** the same neural-update semantics and symbolic operator under
  the already matched periodic-maintenance comparator.

Within seed, C and D-drift must receive identical:

- initial checkpoint;
- preprocessing;
- stream observations;
- label-release events;
- detector configuration and confirmed drift events used for neural adaptation;
- replay/buffer state and eligible adaptation rows;
- neural optimizer/update budget and RNG policy;
- fusion mechanism and threshold;
- evaluation windows.

The intended C-versus-D treatment difference remains the symbolic state
transition. Any treatment-dependent neural trajectory is Class A.

## 9. Frozen adaptive mechanism

Unless a future prospectively versioned Stage-10A correction demonstrates
scientific incompatibility before outcomes, Stage 10A inherits the accepted
primary mechanism:

- ADWIN, delta 0.002, clock 32;
- delayed hard-error primary monitor;
- label latency 5,000;
- current/adaptation window 10,000;
- anchor memory 10,000 with 5,000 anchor + 5,000 online update sample;
- Adam learning rate 1e-4;
- weight decay 1e-5;
- batch 1,024;
- 5 update epochs;
- primary fusion lambda 0.50;
- maximum four symbolic opportunities;
- generation and validation windows 10,000 each with mandatory separation;
- the accepted validated/versioned symbolic lifecycle and gates.

No Stage-10A-specific retuning is permitted after treatment access.

## 10. Seeds and causal unit

Seeds are exactly `0,1,2,3,4`.

The paired seed is the causal replication unit. Windows, detector events,
symbolic opportunities, rules, predictions, bootstrap samples, and explanation
records are nested evidence and must not be treated as independent replicates.

The seed count may not be extended after inspection to chase significance.

## 11. Primary and secondary endpoints

The primary Stage-10A causal family preserves the accepted definitions:

- E1: post-regime MCC, `D-drift - C`;
- E2: post-regime MCSC, `D-drift - C`;
- E3: post-regime MCSC, `D-drift - D-periodic`.

The same paired-seed inferential definitions and multiplicity discipline used
by the accepted primary analysis are retained. Raw seed effects remain
mandatory. A Stage-10A result does not replace the Stage-8/9 result.

Mandatory descriptive supporting endpoints include the accepted detection,
adaptation/trigger, explanation/lifecycle, class-conditional symbolic, and
computational-cost families. In particular, attack-class recall/FNR and
attack-class symbolic coverage/correctness must remain visible so an aggregate
gain cannot hide worsening attack behavior.

No new confirmatory endpoint may be promoted after outcome access.

## 12. Missing, failed, and invalid runs

All attempted seeds are preserved.

A run is invalid only for a prospectively defined Class-A identity,
information-set, treatment-isolation, endpoint, or execution defect. An
unfavorable metric is never an invalid-run reason.

Implementation failures remain write-once evidence. Correction requires a
versioned diagnosis and prospectively frozen correction before re-execution.

## 13. Claim boundary

A successful Stage-10A replication may support a statement that the accepted
symbolic lifecycle effect transfers to a same-family GoldenEye attack-pattern
shift under the frozen CICIDS2017 pseudo-chronology.

It does not by itself establish:

- natural production concept drift;
- universal `P(Y|X)` change;
- drift-trigger superiority over all maintenance clocks;
- universal symbolic benefit;
- architecture invariance;
- external environmental generalization beyond CICIDS2017.

Failure or mixed evidence narrows the claim rather than triggering retrospective
scenario redesign.

## 14. Adversarial pre-outcome review

Before any treatment execution, the following must all remain true:

1. source rows are selected without treatment outcomes;
2. the stream is original Wednesday data, not another BENIGN source swap;
3. the same attack family exists on both sides of the boundary;
4. Heartbleed handling is the already frozen exclusion, not a new cleanup;
5. attack prevalence remains descriptive and is not post-hoc matched by deleting
   inconvenient attack rows;
6. the known boundary is evaluator-only;
7. training/development/preprocessing/checkpoint/R0 identities remain historical
   and do not use Stage-10A future information;
8. C/D neural adaptation is exactly matched within seed;
9. symbolic adaptation is the intended treatment difference;
10. paired seed remains the causal unit;
11. no window/rule/event pseudo-replication enters inference;
12. Stage-8/9 evidence remains immutable;
13. Stage-9.5 remains a hard execution gate;
14. no claim of natural or formal real concept drift is inferred solely from
    source-only KS diagnostics.

## 15. Literature refresh at protocol freeze

The pre-outcome refresh did not justify broad novelty claims. Relevant 2026
work further raises the evaluation standard:

- Costa et al., REFINE, ICAART 2026, DOI
  `10.5220/0014447100004052`: controlled drift construction and bias-resistant
  online evaluation;
- Yuan et al., ADAWU-IDS, 2026, DOI
  `10.1007/s44443-026-00964-4`: chronological validation-selected drift response
  with class-conditional drift diagnostics and explicit mixed/null findings;
- DSALSTM, ICFTIC 2025 / indexed 2026, DOI
  `10.1109/ICFTIC68075.2025.11324708`: drift-aware neural adaptation on
  CICIDS2017;
- FIRCE, SmartNets 2026, DOI
  `10.1109/SmartNets69662.2026.11604738`: drift detection and adaptive response
  evaluated on testbed and public IDS datasets.

These works reinforce the need for prospective temporal/scenario control. They
do not establish the project's full conjunction of endogenous statistical
trigger + validated/versioned symbolic lifecycle + matched neural causal
isolation + longitudinal explanation evaluation.

## 16. Freeze and next permitted action

After this protocol and its machine manifest are committed, the permitted
Stage-10A action is **source-only readiness verification**.

Treatment execution remains locked until Stage 9.5 is legitimately closed.
Passing the Stage-10A source verifier must never be interpreted as
`stage10_execution_authorized=true`.
