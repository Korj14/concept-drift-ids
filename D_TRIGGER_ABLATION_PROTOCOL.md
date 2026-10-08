# D Trigger Ablation Protocol: Drift-Gated vs Periodic Symbolic Maintenance

**Status:** PROSPECTIVE DESIGN FREEZE — TRIGGER POLICY ABLATION  
**Branch:** `stage5-cd-design-audit`  
**Accepted parent:** `main` at `4c13d71a111ce7b72b3ef26a01b2918592425aa1`  
**Date:** 8 October 2026  
**Depends on:** `D_SYMBOLIC_LIFECYCLE_PROTOCOL.md` and all shared C/D control-plane protocols  
**Adaptive held-out execution:** PROHIBITED

## 1. Purpose

This ablation tests whether an explicit statistical drift event is a useful **gate** for symbolic
maintenance rather than merely showing that changing symbolic rules can help.

The compared symbolic arms are:

- **D-drift:** the frozen symbolic lifecycle operator is invoked by confirmed shared statistical drift
  events;
- **D-periodic:** the exact same lifecycle operator is invoked at fixed periodic logical clocks without
  consulting detector events for scheduling.

Both arms:

- start from the same accepted seed-matched R0.v2;
- consume the same shared neural checkpoint trajectory;
- use the same preprocessing;
- use the same fusion/threshold contract;
- use the same symbolic generation/validation budgets;
- use the same rule-quality/lifecycle/conflict semantics;
- use the same symbolic RNG namespace by opportunity index.

Only symbolic maintenance opportunity timing differs.

## 2. Shared neural trajectory is not part of the ablation

D-periodic does **not** trigger neural updates.

The shared detector and neural control plane continues exactly as frozen for C and D.

Therefore D-drift and D-periodic observe the same sequence:

`theta_0 -> theta_1 -> ...`

The periodic symbolic arm merely encounters whichever shared neural checkpoint is deployed at its
prespecified maintenance clock.

Detector alarms are not supplied to the periodic scheduler.

## 3. Equal maximum symbolic opportunity budget

Freeze the maximum symbolic maintenance opportunity budget at:

`K_symbolic = 4 opportunities per seed per trigger arm`.

Every scheduled/triggered opportunity consumes one budget slot whether its outcome is:

- successful rule-base publication;
- validated no-op;
- candidate-generation insufficiency;
- validation right-censoring;
- checkpoint supersession;
- pending-transaction skip;
- technical/protocol failure.

There is no retry that creates an extra fifth opportunity.

### 3.1 D-drift budget

The first four confirmed primary detector events for a seed are the four possible D-drift symbolic
opportunities.

A detector event with no executable/published neural child is still logged as a symbolic opportunity
blocked by the neural transaction and consumes its opportunity slot.

After four confirmed-event opportunity slots have been consumed:

- later detector events may still drive the already-frozen shared neural adaptation;
- D-drift performs no additional symbolic maintenance;
- each later event is logged `symbolic_budget_exhausted`.

### 3.2 Why cap both arms

Without a common maximum budget, a trigger policy that fires more often would receive more chances to
change the rule base and more labeled evidence, making trigger quality inseparable from raw
maintenance opportunity.

The common cap preserves a comparable maximum intervention budget while allowing realized successful
updates to differ naturally by trigger quality and evidence availability.

## 4. Symbolic evidence footprint

Each lifecycle opportunity uses:

- 10,000 mature rows for candidate-generation evidence;
- 10,000 independent future validation rows;
- primary label latency of 5,000 rows before the final validation labels are mature.

The nominal logical evidence footprint is therefore 25,000 stream rows when represented as:

`10,000 retrospective generation + 10,000 prospective validation + 5,000 verification lag`.

This fixed footprint is used to design the periodic cadence.

It is not a claim that all 25,000 rows are unique in every causal state under checkpoint
supersession; it is the prospective budget/spacing unit.

## 5. Primary D-periodic schedule

Primary stream length:

`N = 138,530`.

Use four equally spaced interior maintenance target clocks:

`t_i = floor(i*N/5), i in {1,2,3,4}`.

Thus the exact zero-based logical target clocks are:

- opportunity 1: `27,706`;
- opportunity 2: `55,412`;
- opportunity 3: `83,118`;
- opportunity 4: `110,824`.

The schedule is frozen before adaptive execution.

### 5.1 Why four fifth-spaced opportunities

Five equally spaced intervals produce spacing of approximately 27,706 rows, which exceeds the
25,000-row nominal symbolic evidence footprint.

A five-opportunity six-segment schedule would have spacing of approximately 23,088 rows, smaller than
that footprint and would systematically force overlapping nominal maintenance evidence.

Four is therefore the largest simple equally spaced interior schedule under the non-overlapping
nominal-footprint criterion.

This derivation uses:

- frozen total stream length;
- frozen symbolic evidence budgets;
- frozen label latency.

It does **not** use the evaluator-known drift boundary.

The synthetic boundary at 69,260 is not a scheduling input and none of the periodic target clocks is
equal to it.

## 6. Periodic opportunity ordering at a target clock

At periodic target clock `t`:

1. prediction `t` is committed under the ordinary stream-time contract;
2. labels scheduled to mature at `t` are released;
3. shared detector/neural control-plane actions caused by clock `t` complete;
4. the periodic opportunity is opened last;
5. it snapshots the shared neural checkpoint that will be effective for the next logical prediction;
6. the symbolic operator then follows the same generation/validation/publication rules as D-drift.

The periodic clock itself never changes prediction `t`.

This ordering resolves the case where a shared neural publication and a periodic target happen at the
same logical clock.

## 7. Periodic candidate-generation evidence

At the periodic target clock, use the most recent 10,000 adaptively mature stream rows available at
that clock as generation evidence.

These rows are treatment-independent and fixed before symbolic candidate acceptance.

The current shared neural checkpoint is evaluated on those feature rows to generate SHAP
attributions, surrogate targets and candidate structures.

The generation block may contain rows originally predicted by an earlier neural checkpoint. This is
permitted because candidate generation is a proposal mechanism and D-drift likewise applies the newly
updated neural model to the mature evidence that produced it.

Candidate acceptance still requires the separate checkpoint-pure future validation block.

If fewer than 10,000 mature rows exist at a target clock, the opportunity is
`insufficient_generation_rows` and consumes its budget slot. Under the frozen primary clocks this is
not expected, but the rule is explicit.

## 8. Periodic validation and neural supersession

After candidate generation, the periodic arm uses the same independent validation contract as
D-drift:

- 10,000 future rows predicted by the snapshotted shared neural checkpoint;
- labels must mature while that checkpoint remains active;
- both binary classes required;
- same Wilson/bootstrap gate;
- same incumbent staleness assessment;
- same lifecycle operator.

If the shared neural checkpoint is superseded before validation completes:

- the periodic transaction closes `superseded_before_validation`;
- no partial symbolic publication occurs;
- the next periodic clock remains unchanged.

The periodic scheduler does not move an opportunity to follow the new neural checkpoint.

## 9. No concurrent symbolic transactions

Each trigger arm may have at most one outstanding symbolic transaction per seed.

### D-drift

A later neural publication automatically supersedes any still-pending symbolic transaction tied to
the older checkpoint under the lifecycle protocol.

### D-periodic

If a periodic target clock occurs while the previous periodic symbolic transaction is still
outstanding for reasons other than neural supersession:

- the new scheduled opportunity is logged `pending_transaction_skip`;
- it consumes its opportunity slot;
- no concurrent candidate/validation transaction is opened.

The prespecified 27,706-row cadence is designed to make ordinary overlap unlikely without changing
this fail-closed rule.

## 10. Operator identity requirement

D-drift and D-periodic must call the same symbolic evolution implementation with the same immutable
operator configuration hash.

The trigger layer may provide only:

- arm identity;
- opportunity ID;
- target/trigger clock;
- generation evidence identity;
- current shared neural checkpoint identity.

It may not alter:

- SHAP method/sample limits;
- top-k;
- surrogate constraints;
- weighted consequent semantics;
- validation size;
- Wilson thresholds;
- bootstrap replicates/stability gate;
- complexity gate;
- redundancy/conflict thresholds;
- lifecycle transition rules;
- confidence formula;
- publication rule.

Any arm-specific operator configuration is treatment contamination.

## 11. RNG matching

For the same seed and one-based opportunity index `m`, D-drift and D-periodic use the identical
symbolic RNG namespace from `D_SYMBOLIC_LIFECYCLE_PROTOCOL.md`:

`20261020 + 1000*seed + 10*m`

with the same offsets for:

- SHAP background;
- SHAP attribution;
- surrogate random state;
- validation bootstrap.

Different evidence rows may cause different sampled identities, but no arm receives a different
randomness policy.

## 12. What counts as a symbolic update

Distinguish:

- **opportunity:** trigger/schedule opened one maintenance slot;
- **completed validation:** independent validation became available;
- **publication:** inference-relevant symbolic state changed and a new rule-base version was published;
- **no-op:** validation completed but inference state did not change;
- **censored/aborted:** opportunity could not reach valid publication decision.

Do not equate "opportunity count" with "rule-base update count."

This distinction is central to trigger efficiency.

## 13. Trigger-ablation outcomes

Per seed and arm report at minimum:

- scheduled/triggered opportunity count;
- candidate-generation count;
- completed-validation count;
- publication count;
- no-op count;
- superseded/censored/skipped count by reason;
- logical waiting rows;
- total symbolic compute time;
- accepted additions/refinements/merges/reactivations;
- demotions/retirements;
- candidate rejection count;
- active rule count trajectory;
- conflict/abstention trajectory;
- coverage/correctness/fidelity trajectory;
- predictive recovery trajectory;
- explanation recovery trajectory;
- symbolic maintenance cost per publication;
- recovery/improvement per maintenance opportunity;
- unnecessary maintenance relative to the controlled reference change.

"Unnecessary" must be operationally defined relative to the designated controlled scenario and
reported cautiously because internal pseudo-chronological variation may exist away from the known
boundary.

## 14. Boundary scoring

The synthetic boundary remains post-hoc evaluation metadata only.

After both symbolic trajectories are frozen, the evaluator may classify periodic/drift opportunities
as occurring before/after the designated controlled boundary and compute distances to it.

Neither trigger policy may use that boundary during execution.

## 15. Primary causal interpretation

The ablation asks:

> Given the same neural adaptation trajectory and the same symbolic maintenance operator/budget,
> does using confirmed statistical performance-drift events as the symbolic gate produce a more
> useful and/or more efficient symbolic evolution trajectory than ordinary fixed periodic
> maintenance?

Possible valid outcomes include:

- D-drift achieves similar explanation/predictive recovery with fewer maintenance publications;
- D-drift improves recovery relative to D-periodic;
- D-periodic is equally good or better;
- both are mostly no-op/censored;
- neither symbolic policy materially improves over frozen-symbolic C.

No outcome authorizes trigger-policy retuning after held-out inspection.

## 16. Sensitivity and scope

The primary periodic schedule is not claimed universally optimal.

A different cadence may be studied only as a separately labeled sensitivity after the primary
trajectory is frozen and must not replace the primary because it produces a favorable contrast.

D-continuous remains optional and is not required for the primary trigger hypothesis.

## 17. Remaining controls after this packet

Before adaptive implementation, the remaining blockers are:

- final confirmatory endpoint hierarchy, tests/intervals and multiplicity;
- runtime/thread/determinism and cost measurement scope;
- exact event/evidence serialization schemas;
- fail-closed treatment-contamination and lifecycle-integrity verifiers;
- implementation test matrix;
- stage/branch execution order and held-out access gate.

## 18. Gate

**D-drift versus D-periodic trigger-ablation packet: FROZEN.**

Adaptive implementation remains prohibited.

The next packet is the final statistical/runtime/reproducibility design freeze that must remove the
remaining material TBDs before code is authorized.
