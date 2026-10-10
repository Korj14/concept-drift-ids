# Stage 9 Prespecified Robustness Implementation Freeze

**Status:** PRE-OUTCOME IMPLEMENTATION FREEZE — NO STAGE-9 ROBUSTNESS OUTCOME ACCESSED  
**Parent Stage-8 evidence commit:** `c2ded83b8195b9321e715626c1f305f9627936e8`  
**Parent compact manifest:** `409b516d75cbc5e71d3633019008432ea6088d1d923b4e4a95570263528ed523`  
**Parent confirmatory aggregate:** `1be77ce4be9f3faad021a3f3bfd636488e5de6aa1b2a6e7c596e48feb41bb54d`  
**Parent corrected primary config manifest:** `d380fce5f9db8f0b639dc999298a263b10a10a3d02e35def226a121d098e2222`

## 1. Purpose

This document freezes implementation decisions needed to execute the already-prespecified Stage-9
robustness protocol. It does not add a new scientific condition, remove a prespecified condition, or
change a Stage-8 endpoint.

The implementation is additive. Stage-8 scientific source and evidence are treated as immutable
inputs and are not overwritten.

## 2. Condition identities

### Group O — offline-only

- `O_LAMBDA_070`: frozen Stage-8 lambda=.70 decisions/metrics;
- `O_LAMBDA_090`: frozen Stage-8 lambda=.90 decisions/metrics;
- `O_LAMBDA_100`: frozen Stage-8 lambda=1.00 neural-only negative control;
- `O_WINDOW_2500`: 2,500-row reporting-window sensitivity from immutable Stage-8 traces;
- `O_WINDOW_10000`: 10,000-row reporting-window sensitivity from immutable Stage-8 traces.

Both window sensitivities inherit the primary reporting helper's 1,000-row minimum-remainder merge
rule and the frozen recovery definition (weighted three-window pre baseline, two consecutive qualifying
post windows, right censoring when unrecovered).

No threshold is refit and no adaptive state is rerun in Group O.

### Group G — symbolic-gate sensitivity

- `G_STATIC_GATE`

This condition reuses the exact frozen Stage-8 Phase-A shared neural trajectories and changes only the
symbolic validation gate.

The gate is frozen as:

- support >= .001;
- covered >= 100;
- point class precision >= .80;
- point neural fidelity >= .90;
- 100 stratified bootstrap replicates;
- full point-gate persistence >= .90;
- complexity <= 4;
- no Wilson-LCB requirement.

The existing lifecycle implementation is used with `min_precision_lcb=0.0` and
`min_fidelity_lcb=0.0`. Wilson values may still be computed as diagnostics, but they do not enter
accept/reject decisions in this Stage-9 condition.

C, D-drift and D-periodic use the identical static-gate operator configuration.

### Group A — adaptive robustness

- `A_BASELINE`: primary L=5,000, ADWIN hard error, replay enabled. Required only when the
  Stage-9 runtime differs materially from the Stage-8 runtime;
- `A_LATENCY_0`: L=0, ADWIN hard error, replay enabled;
- `A_LATENCY_10000`: L=10,000, ADWIN hard error, replay enabled;
- `A_PAGE_HINKLEY`: L=5,000, Page-Hinkley over delayed checkpoint-pure hard neural errors,
  replay enabled;
- `A_ADWIN_BRIER`: L=5,000, ADWIN over delayed checkpoint-pure Brier loss, replay enabled;
- `A_NO_REPLAY`: L=5,000, ADWIN hard error, replay disabled.

All Group-A conditions retain the primary current mature window, optimizer, learning rate, weight
decay, batch size, epochs, deterministic seed namespaces, symbolic operator and fusion policy unless
the condition definition explicitly changes that component.

## 3. Page-Hinkley numerical freeze

The prespecified protocol required Page-Hinkley parameters to be frozen before Stage-9 execution and
forbids choosing them from Stage-8 trigger timing or outcome direction.

This implementation uses the explicit defaults from the locked River 0.26.1
`river.drift.PageHinkley` constructor:

- `min_instances=30`;
- `delta=0.005`;
- `threshold=50.0`;
- `alpha=0.9999`;
- `mode="both"`.

No Stage-8 alarm clock, MCC, MCSC, publication count or mechanism result was used to select these
values.

## 4. Detector information contract

Every Stage-9 adaptive detector:

1. receives a label only at or after the condition's frozen maturity index;
2. observes only the neural prediction that was actually made for that row;
3. admits an observation only when the prediction checkpoint equals the active detector epoch
   checkpoint;
4. is disarmed after a detected event until a child neural checkpoint is published;
5. resets on child-checkpoint publication;
6. receives no scenario-boundary metadata;
7. cannot read symbolic state or symbolic-arm outcomes.

Signals are:

- hard-error conditions: `int((p >= frozen_seed_threshold) != y)`;
- Brier condition: `(p - y)^2`.

## 5. Neural-treatment isolation

Within each Stage-9 adaptive condition and seed, C, D-drift and D-periodic share exactly one
condition-specific neural trajectory.

Symbolic state cannot influence detector observations, replay selection, neural updates or checkpoint
publication.

The condition-specific shared identity is frozen before symbolic treatment.

Cross-condition neural trajectories are allowed to differ because the robustness treatment itself
changes latency, detector signal/family, or replay.

## 6. No-replay semantics

`A_NO_REPLAY` changes only replay inclusion.

At each otherwise executable neural response:

- the current mature window remains 10,000 rows;
- the optimizer, learning rate, weight decay, batch size, epochs and shuffle namespace remain primary;
- replay contains exactly zero rows;
- no anchor or online-reservoir row is substituted;
- detector semantics and symbolic treatment logic remain otherwise matched.

The implementation passes a correctly shaped zero-row replay matrix to the frozen neural update
function so the update math is unchanged apart from replay omission.

## 7. Runtime and matched-baseline rule

Stage-9 configuration preparation freezes:

- Python version and implementation;
- platform and processor;
- locked distribution identity;
- PyTorch version;
- deterministic-algorithm status;
- thread environment and threadpool inventory.

The Stage-8 runtime identity is read from the frozen compact Phase-A run manifests.

If the Stage-9 runtime differs materially in platform, Python version, locked-distribution identity,
PyTorch version, deterministic status, or required thread settings, `A_BASELINE` becomes mandatory
before adaptive variants may be interpreted.

A runtime-matched Stage-9 baseline is not permitted to replace Stage 8.

## 8. Evidence separation

Heavy Stage-9 evidence is write-once under:

`artifacts/cd_robustness_v1/`

Compact verified evidence is exported later under:

`results/frozen/cd_robustness_v1/`

No Stage-8 file is modified.

Every Stage-9 artifact binds:

- Stage-8 parent evidence identities;
- Stage-9 config manifest;
- condition ID;
- seed;
- runtime identity;
- scenario/preprocessing identity;
- accepted System-A/R0.v2 identities;
- condition-specific neural/shared identity;
- symbolic-operator identity where applicable.

## 9. Configuration freeze gate

Before any new Stage-9 adaptive row is processed or any Group-G symbolic gate is rerun:

1. Stage-9 source, this implementation freeze and tests must pass repository CI;
2. `cd-stage9-prepare` may read repository metadata and frozen compact Stage-8 provenance only;
3. it must not load heavy Phase-C traces, primary feature partitions, or execute a Stage-9 treatment;
4. it writes only `data/manifests/cd_stage9_run_config_v1.json`;
5. that config must be the sole changed path in its freeze commit;
6. the config commit parent must equal the source head recorded during preparation;
7. exact-head CI must pass;
8. execution must occur only at that exact config commit.

After the first Stage-9 robustness outcome is accessed, no condition parameter may be altered because
of observed direction. A software defect must be preserved and versioned rather than silently
rewritten.

## 10. Fail-closed reviewer checks

Execution aborts on any of the following:

- boundary metadata in adaptive payloads;
- label-dependent action before maturity;
- checkpoint-impure detector admission;
- symbolic-to-neural feedback;
- condition/config/seed identity mismatch;
- wrong parent Stage-8 evidence;
- replay/current overlap;
- non-zero replay in `A_NO_REPLAY`;
- generation/validation overlap;
- wrong symbolic operator identity;
- treatment-arm neural identity mismatch;
- output-root reuse;
- untracked or non-exact Stage-9 config head;
- runtime mismatch not reflected in the frozen config;
- selective seed execution in aggregate construction;
- overwrite of any Stage-8 artifact.

## 11. Statistical and claim boundary

Stage 9 is robustness evidence on the same fixed scenario.

Results are reported condition-by-condition across the same five matched seeds. Conditions are not
pooled as independent replicates, and no variant replaces the Stage-8 primary.

Stage 9 cannot by itself establish external validity, natural production drift robustness, human
explanation usefulness, production real-time performance, adversarial robustness, or ADWIN trigger
superiority beyond the frozen comparisons.
