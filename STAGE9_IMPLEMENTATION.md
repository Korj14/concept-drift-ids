# Stage 9 Prespecified Robustness Implementation

**Status:** PRE-ACCESS IMPLEMENTATION — NO STAGE-9 OUTCOMES ACCESSED  
**Binding protocol:** `STAGE9_PRESPECIFIED_ROBUSTNESS_PROTOCOL.md`  
**Parent Stage-8 evidence:** `c2ded83b8195b9321e715626c1f305f9627936e8`

## 1. Purpose

This implementation executes only the robustness conditions already frozen in the Stage-9 protocol.
It is additive to Stage 8 and cannot replace the immutable primary evidence.

No Stage-9 held-out/adaptive robustness outcome may be accessed until:

1. Stage-9 source and tests are accepted;
2. a no-outcome-access Stage-9 config is generated;
3. that config is the sole path in its freeze commit;
4. exact-head CI passes.

## 2. Isolation from Stage 8

Stage-9 implementation is additive. The frozen primary runner, primary PowerShell entrypoint, primary
control-plane implementation, primary symbolic lifecycle, and primary scoring implementation are not
modified.

Stage 9 has separate entrypoints:

- `run_stage9.py`;
- `scripts/run_stage9.ps1`.

Stage 9 imports tested Stage-8 helpers where semantics are intentionally unchanged. It does not mutate
Stage-8 artifacts.

## 3. Condition families

### Group O — offline-only

- lambda=.70;
- lambda=.90;
- lambda=1.00;
- 2,500-row reporting windows;
- 10,000-row reporting windows.

Lambda results are read directly from immutable Stage-8 summaries. No threshold is refit.

Window sensitivities re-read the original heavy Stage-8 prediction traces only after verifying both
raw compressed-file and canonical JSONL identities against frozen compact Stage-8 descriptors.

No adaptive state is rerun.

### Group G — static-style symbolic gate

The frozen Stage-8 Phase-A shared neural trajectories are reused.

The Stage-9 gate uses:

- support >= .001;
- covered >= 100;
- point precision >= .80;
- point neural fidelity >= .90;
- 100 bootstrap replicates;
- persistence/stability >= .90;
- complexity <= 4;
- no Wilson-LCB acceptance requirement.

The existing lifecycle evaluator is reused by setting both Wilson-LCB minimum thresholds to 0.0.
Wilson statistics may still be computed and stored as diagnostics, but they cannot reject an
otherwise passing rule. Point thresholds, bootstrap persistence, complexity and all lifecycle
semantics remain explicit.

C, D-drift and D-periodic share the exact frozen Stage-8 neural trajectory for each seed.

### Group A — adaptive robustness

The implementation supports:

- matched primary baseline when runtime identity differs from Stage 8;
- L=0;
- L=10,000;
- PageHinkley on delayed checkpoint-pure hard error;
- ADWIN on delayed checkpoint-pure Brier loss;
- no replay.

Every condition keeps all five seeds.

## 4. Detector semantics

The Stage-9 detector wrapper preserves the primary epoch semantics:

- observation only after label maturity;
- signal admitted only when the prediction checkpoint equals the active detector epoch checkpoint;
- stale-checkpoint observations are rejected;
- detector disarms after a confirmed event;
- a child neural checkpoint starts a fresh detector epoch only after publication.

ADWIN-Brier uses:

`(stored_prediction_probability - mature_label)^2`

and retains the primary ADWIN structural parameters.

PageHinkley uses the locked River 0.26.1 constructor defaults, frozen explicitly in source. A
repository test checks the configured values against the installed locked-library signature. If that
test fails, the implementation must be corrected prospectively before config generation rather than
silently substituting parameters.

## 5. No-replay semantics

No-replay changes only the adaptation training set.

The condition keeps:

- the same detector;
- L=5,000;
- the same current mature window;
- optimizer;
- learning rate;
- weight decay;
- batch size;
- epoch count;
- deterministic shuffle namespace.

The replay matrices are explicit zero-row arrays with the unchanged feature dimension. The frozen
neural updater therefore trains on the current window only. No anchor or online-reservoir row is
substituted.

The Stage-9 verifier rejects any no-replay transaction containing a replay row.

## 6. Runtime and matched-baseline rule

Stage-9 config preparation records:

- platform;
- processor;
- machine;
- Python version and implementation;
- Torch version;
- CPU-only status;
- required thread environment;
- deterministic-algorithm state;
- Torch intra-op and inter-op thread counts;
- exact installed-distribution identity.

It also reads the frozen Stage-8 Phase-A runtime identity.

If platform, processor, Python, Torch, or installed-distribution identity differs, the matched
Stage-9 primary baseline is automatically included and cannot be disabled after the config freeze.

Adaptive variants are then compared primarily against that matched Stage-9 baseline.

The static-gate sensitivity is always compared with the Stage-8 primary reference because it reuses
the Stage-8 shared neural trajectory. Comparing it with a different-runtime adaptive baseline would
break comparator matching.

## 7. Boundary and chronology controls

The Stage-9 config freezes:

- stream rows = 138,530;
- reference boundary = 69,260;
- pre-reference rows = 69,260;
- post-reference rows = 69,270;
- boundary role = offline scoring/diagnostics only;
- adaptive boundary visibility = false;
- reshuffling = forbidden.

Phase A writes unscored trajectories and cannot receive boundary metadata.

Phase B freezes symbolic trajectories before Phase C boundary-aware scoring.

Phase C computes trigger diagnostics only after adaptive trajectories are frozen.

Latency-adjusted detector delay uses the active condition's frozen latency rather than assuming the
primary L=5,000.

## 8. Comparator and inference rules

The inferential unit remains the matched seed within the fixed scenario.

The exporter requires all five seeds for every configured condition. It will not export a partial
condition family.

It reports:

- all per-seed values;
- mean/median/sample SD/min/max;
- sign counts;
- within-condition C/D contrasts;
- paired effects versus the correct matched reference.

It does not pool:

- windows;
- detector events;
- rules;
- opportunities;
- robustness conditions

as independent replicates.

Stage-9 results remain prespecified robustness evidence, not a new confirmatory family.

## 9. Write-once evidence and failure handling

Heavy evidence is written only below:

`artifacts/cd_robustness_v1/`

Compact verified evidence is exported only after full verification to:

`results/frozen/cd_robustness_v1/`

Existing condition/seed output directories are never reused.

A failed execution preserves its partial write-once directory. It is not deleted and rerun merely
because the result or failure is inconvenient.

An implementation failure discovered before successful scientific output is versioned prospectively.
An underlying violation of causal isolation, chronology, label maturity, boundary blindness, identity
binding, or endpoint semantics is restart-level for the affected Stage-9 evidence.

An unfavorable but valid robustness outcome is preserved.

## 10. Q1 claim discipline

Stage 9 tests sensitivity of the fixed primary scenario only.

It cannot by itself establish:

- natural production concept-drift robustness;
- independent-dataset generalization;
- direct conditional-label-change robustness;
- human explanation usefulness;
- adversarial robustness;
- real-time deployment performance.

Those remain separate evidence obligations.

The Stage-8 mechanism interpretation is not used to tune Stage 9. In particular, Stage 9 is not
modified to force more symbolic addition or retained-authority contribution. The prespecified
conditions are executed whether they strengthen, weaken or reverse the Stage-8 interpretation.
