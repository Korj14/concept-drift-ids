# Stage 8 Symbolic-Value Mechanism Audit Protocol

**Status:** POST-PRIMARY EXPLORATORY MECHANISM FREEZE — ROW-LEVEL MECHANISM TRACE NOT YET INSPECTED  
**Parent immutable evidence commit:** `c2ded83b8195b9321e715626c1f305f9627936e8`  
**Parent compact-export manifest:** `409b516d75cbc5e71d3633019008432ea6088d1d923b4e4a95570263528ed523`  
**Parent confirmatory aggregate:** `1be77ce4be9f3faad021a3f3bfd636488e5de6aa1b2a6e7c596e48feb41bb54d`

## 1. Purpose

The Stage-8 primary result established a positive D-drift minus C post-regime MCC effect, while the
lambda=1 neural-only sensitivity showed that frozen symbolic C was substantially worse than the shared
adaptive neural trajectory.

This audit asks a narrower mechanism question:

> How much of the observed C -> D predictive change is associated with withdrawal of stale symbolic
> authority, addition of symbolic authority, or changed symbolic behavior on rows where both systems
> remain authoritative?

The audit is exploratory/secondary because it is frozen after primary outcomes are known.

It may clarify mechanism but may not replace, redefine, or promote itself above the Stage-8 primary
confirmatory endpoints.

## 2. Evidence boundary

The audit reads only already-frozen Stage-8 artifacts:

- Phase-C C-frozen-symbolic prediction trace;
- Phase-C D-drift prediction trace;
- Phase-C D-periodic prediction trace for matched comparator context;
- compact Phase-C arm evaluation summaries containing the frozen trace identities;
- compact Phase-B arm manifests containing symbolic publication/version identities.

No model is trained or rescored.

No candidate rule is regenerated.

No validation gate is rerun.

No threshold is refit.

No adaptive state is changed.

The original feature matrix is not required for the first mechanism audit.

## 3. Integrity preconditions

For every seed and comparison, the audit must verify trace hashes against the frozen Phase-C
evaluation summary before using row content.

For every row, C and target arm must agree exactly on:

- row identity;
- origin index;
- true label;
- neural checkpoint SHA-256;
- neural probability;
- lambda=1 fused probability;
- lambda=1 thresholded decision.

Any disagreement aborts the audit.

The parent compact-export manifest identity must match the frozen Stage-8 identity.

## 4. Scope

Primary mechanism target:

- D-drift versus C on the post-reference domain, because E1 is the main positive Stage-8 effect.

Matched contextual decomposition:

- D-periodic versus C on the same post-reference domain.

Pre-reference decomposition is reported descriptively because most D-drift symbolic publications
occurred before the designated reference boundary.

No mechanism-level p-value is computed.

## 5. Mutually exclusive authority strata

For C and target arm T, define `covered` exactly as stored in the frozen Phase-C trace.

Each row belongs to one of four authority states:

1. **withdrawal**:
   - C covered = true;
   - T covered = false.

   C exercises symbolic authority while T abstains from symbolic authority.

2. **addition**:
   - C covered = false;
   - T covered = true.

   T exercises symbolic authority where C abstains.

3. **revision**:
   - C covered = true;
   - T covered = true.

   Both exercise symbolic authority. Any prediction difference is therefore associated with changed
   symbolic score/class/rule state under the same neural trajectory and same fusion policy.

4. **neither-authoritative**:
   - C covered = false;
   - T covered = false.

   Under the matched neural trajectory and identical lambda=.50 threshold, C and T primary decisions
   must be identical on this stratum. A disagreement is treated as an invariant failure and aborts
   the audit.

These names describe observable authority states. They do not by themselves prove which individual
lifecycle transition caused the state.

## 6. Row-level correction accounting

Using the stored primary lambda=.50 decisions:

- **rescue**: C is wrong and T is correct;
- **harm**: C is correct and T is wrong;
- **same-correct**: both are correct;
- **same-wrong**: both are wrong.

For every authority stratum report:

- row count and fraction of the domain;
- attack/benign row counts;
- C and T error counts;
- rescue count;
- harm count;
- net corrected decisions = rescue - harm;
- C/T TP, TN, FP, FN contributions on those rows;
- target symbolic uncovered/conflict status where relevant.

Rescue/harm counts are descriptive and additive across disjoint strata.

## 7. MCC mechanism decomposition

MCC is nonlinear, so simple row-count attribution is insufficient.

For each domain and target arm, construct three disjoint switch mechanisms:

- W = withdrawal rows;
- A = addition rows;
- R = revision rows.

Start from the complete C primary decision vector.

For any subset S of {W,A,R}, create a hybrid prediction vector by replacing C decisions with the
target-arm stored decisions only on rows belonging to mechanisms in S.

Let:

`v(S) = MCC(y, hybrid_decision(S))`.

Compute the exact three-player Shapley value for W, A and R:

`phi_i = sum_{S subset N\{i}} |S|!(|N|-|S|-1)!/|N|! * [v(S union {i}) - v(S)]`.

Required invariants:

- v(empty) = stored C MCC;
- v({W,A,R}) = stored target-arm MCC;
- phi_W + phi_A + phi_R = target MCC - C MCC within numerical tolerance;
- neither-authoritative rows have identical C/T primary decisions.

The Shapley values are an order-independent descriptive allocation of the realized MCC difference
across observable authority-change strata.

They are **not** causal effects of hypothetical interventions on individual rules.

## 8. Accuracy/error decomposition

Because correctness is row-additive, also report exact net correction contributions:

- withdrawal net corrections;
- addition net corrections;
- revision net corrections.

This provides an interpretable companion to the nonlinear MCC Shapley decomposition.

## 9. Rule-version timing context

For the target arm, aggregate each domain by stored `rule_base_version_id`.

For every realized rule-base version report:

- first/last origin index;
- row count;
- covered count/rate;
- rescue count;
- harm count;
- net corrected decisions;
- authority-stratum row counts.

This identifies whether post-regime gains are associated with:

- the accepted initial R0.v2;
- a version published before the designated boundary;
- a version published after the boundary.

The audit does not claim that a rule-base version is itself an independent experimental unit.

## 10. Interpretation rules

### 10.1 Withdrawal-dominant result

If most realized MCC gain / net corrected decisions are attributed to withdrawal rows, the defensible
mechanism claim is:

> lifecycle evolution mitigated stale symbolic interference primarily by withdrawing symbolic
> authority and falling back to the shared adaptive neural predictor.

This is a valid symbolic-lifecycle contribution but is not evidence that newly evolved rules
themselves dominate neural-only prediction.

### 10.2 Addition/revision-dominant result

If addition and/or revision contribute materially and consistently, the defensible claim may include
that evolved symbolic states added useful predictive information on rows where symbolic authority was
retained or newly established.

Any such claim remains conditional on the fixed scenario and must be replicated.

### 10.3 Mixed result

If contributions vary strongly by seed/version, report the heterogeneity directly and avoid a single
mechanism headline.

## 11. Comparator interpretation

D-periodic versus C uses the identical decomposition only as matched trigger-policy context.

It is not a new confirmatory endpoint.

Comparing mechanism allocations between D-drift and D-periodic may suggest whether authority
withdrawal/addition is specific to drift-trigger timing, but no trigger superiority claim is made
without the frozen Stage-9 robustness package.

## 12. Output policy

Heavy Stage-8 traces remain Git-ignored and unchanged.

The mechanism audit writes compact, write-once JSON only to:

`results/frozen/cd_primary_mechanism_v1/`

Required outputs:

- one per-seed JSON containing D-drift-vs-C and D-periodic-vs-C decompositions;
- one five-seed aggregate JSON;
- one audit manifest binding:
  - parent evidence identities;
  - source Git commit;
  - protocol path/version;
  - every input trace hash;
  - every output hash.

No row-level trace is copied into Git.

## 13. Aggregate reporting

Across five seeds, report for each target arm and mechanism:

- per-seed Shapley MCC contribution;
- mean, median, sample SD, min/max;
- sign count;
- per-seed net corrected decisions;
- mean/median net corrected decisions;
- authority-stratum row fractions.

These are descriptive exploratory summaries.

No new p-value family is created.

## 14. Publication use

This mechanism audit may:

- refine the mechanistic interpretation of E1;
- motivate later prospectively frozen ablations;
- identify whether stale-rule withdrawal is a central contribution.

It may not:

- turn a post-hoc mechanism result into a prospectively confirmatory claim;
- replace the primary E1/E2/E3 family;
- delete or reinterpret the negative MCSC result;
- justify retuning the symbolic gate or detector in the primary experiment.

## 15. Restart rule

A mechanism-audit failure triggers Stage-8 restart only if it exposes an underlying primary invariant
violation, such as non-identical neural trajectories, mismatched labels/rows, trace identity failure,
or lambda=1 inequality.

A surprising mechanism allocation by itself is a scientific finding, not a restart condition.
