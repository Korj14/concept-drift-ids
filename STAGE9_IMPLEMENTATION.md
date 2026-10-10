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

Every Stage-8 computational module reused by Stage 9 is re-hashed at config preparation/execution and
must equal its historical hash in the corrected Stage-8 config. Later legitimate changes to
non-executed Stage-8 governance files (for example mechanism archival attributes) are not confused
with computational-source drift. Additional helper modules not present in that historical source map
are frozen directly in the Stage-9 scientific source identity.

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

The export self-verifies every compact file and the aggregate/manifest identities before reporting
success. A separate `export --verify-only` path re-verifies the frozen compact package. During that
verification the worktree gate permits only untracked files beneath the Stage-9 compact root; any
other modified or untracked path aborts.

Stage-9-only nested Git attributes pin the run config and compact evidence tree to LF without
modifying the frozen root Stage-8 `.gitattributes`.

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


## 11. Pre-access hardening for Q1 defensibility

Before any Stage-9 robustness outcome is accessed, the implementation additionally enforces the
following controls.

### Frozen primary treatment contract

The Stage-9 config stores a canonical hash of the corrected Stage-8 treatment contract covering:

- scenario identity and row/boundary definitions;
- System-A checkpoint/threshold identities;
- accepted R0.v2 identity;
- primary control-plane parameters and RNG namespaces;
- primary symbolic-operator configuration;
- fusion weights/threshold table and no-post-hoc-recalibration rule;
- primary analysis contract.

Every Stage-9 condition stores:

- the same frozen primary-contract hash;
- its explicit `changed_factors` list.

Any difference not declared in that list is therefore reviewable as a contract violation rather than
an implicit code-default difference.

### Five-seed runtime reference

Stage-9 preparation reads the frozen Stage-8 Phase-A runtime manifest for all five primary seeds and
requires one common sanitized runtime fingerprint. The fingerprint includes platform/processor,
Python/Torch identities, deterministic-algorithm state, Torch thread counts, required thread
environment and the locked-distribution identity.

If the current Stage-9 runtime fingerprint differs from the common Stage-8 fingerprint, the matched
Stage-9 primary baseline is automatically included. The baseline cannot be removed after config
freeze.

### Preparation and no-outcome-access gate

Preparation requires:

- a clean worktree;
- ancestry from the accepted Stage-8 closure commit;
- absence of both Stage-9 heavy and compact output roots;
- exact Stage-8 evidence/config/source identities;
- exact Stage-9 source/test/runner/workflow identities.

The config records `stage9_outcomes_accessed_during_preparation=false`. The absence of Stage-9 output
roots makes that claim mechanically checkable rather than declarative only.

### Prediction-before-label trace invariant

The Stage-9 trajectory verifier checks event order directly. For every origin row:

1. prediction must appear first;
2. label release may appear only after that prediction;
3. detector observation may appear only after label release;
4. a drift event may appear only after the corresponding detector observation.

This remains true for L=0 even though prediction and label maturity share the same logical clock.

### Deterministic full-matrix execution plan

The preferred scientific execution path is `run_stage9.py execute-all`.

Before the first Stage-9 result is produced, it writes a canonical execution plan derived only from
the frozen config. The plan fixes:

- condition order;
- seed order;
- phase order;
- every required condition/seed/phase step;
- prohibition on outcome-dependent early stopping;
- abort-and-preserve behavior for technical failures.

A resumed execution may verify and skip a previously complete step. It must abort on an existing
partial or failed write-once step rather than delete, overwrite or silently rerun it.

`execute-all --verify-only` is non-mutating and requires the plan to already exist.

Final compact export requires the same verified pre-outcome execution-plan identity, so a manually
selected subset of conditions cannot produce the final Stage-9 evidence package.

### Offline Stage-8 input binding

Group-O lambda/window sensitivities bind each reused Stage-8 compact evaluation file to the exact raw
SHA-256 descriptor in the frozen Stage-8 compact export manifest and also verify the file's internal
canonical scientific hash.

Window sensitivities additionally verify the original heavy trace raw and canonical JSONL identities
against the frozen Stage-8 descriptor before recomputing reporting windows.

### Compact causal provenance

For each scored Stage-9 condition/seed, compact export includes the small provenance artifacts needed
to audit causal isolation without the heavy workspace:

- Phase-A run manifest;
- Phase-A input identity;
- Phase-A shared identity;
- Phase-B seed manifest;
- each C/D arm manifest;
- Phase-C seed manifest and arm evaluations.

Large prediction traces, checkpoints and maintenance JSONL remain in the heavy artifact archive.

### Statistical and reference policy

Stage-9 aggregation reports every frozen condition and all five seeds. It computes no new p-values and
does not create a replacement confirmatory family.

The aggregate records an explicit reference policy:

- offline sensitivities -> frozen Stage-8 primary;
- static symbolic-gate sensitivity -> frozen Stage-8 primary;
- matched Stage-9 baseline -> frozen Stage-8 primary;
- adaptive variants -> matched Stage-9 baseline when runtime mismatch requires it, otherwise frozen
  Stage-8 primary.

Any t-based 95% interval emitted by the robustness summary is labeled descriptive stochastic-seed
dispersion conditional on the fixed scenario, not environmental/deployment-population inference.

No robustness condition may be omitted, promoted or suppressed according to outcome direction.


## 12. Explicit artifact identity context

To satisfy the protocol's per-artifact provenance requirement directly, Stage-9 run-level scientific
artifacts now carry canonical identity context instead of relying only on transitive config lookup.

Per-seed contexts bind:

- Stage-8 parent evidence and closure commits;
- Stage-9 config manifest;
- current Stage-9 runtime identity;
- scenario-manifest identity;
- preprocessing-state hash;
- System-A manifest and seed-specific starting checkpoint;
- accepted R0.v2 manifest;
- primary control-plane config;
- primary symbolic-operator config;
- fusion contract;
- frozen primary-contract hash;
- exact Stage-9 condition-spec hash;
- condition ID and seed.

The context is recorded and verified in Group-O results, Phase-A run identity, Phase-B seed/arm
manifests, and Phase-C seed/arm summaries.

Global aggregate and compact-export manifests carry the corresponding run-global identity context.

Low-level row traces, checkpoint files and maintenance streams remain transitively bound through their
verified run/arm/seed manifests rather than duplicating the same metadata on every row or binary
checkpoint.


## 13. Stage-9 v1.1 execution correction

The first Stage-9 `execute-all` attempt under frozen config v1 did not produce an accepted robustness
result.

The predetermined first step was Group-O `lambda_0_7`, seed 0. The runner wrote the pre-outcome
execution plan and the step `attempt.json`, then failed in the Stage-8 compact-manifest provenance
reader with:

`AttributeError: 'list' object has no attribute 'values'`

The immutable Stage-8 compact export manifest stores `files` as a list of descriptor objects. The
Stage-9 v1 reader incorrectly treated it as a mapping. The original unit tests reproduced that wrong
synthetic shape and therefore did not expose the defect.

The governing correction protocol is:

`STAGE9_V1_1_EXECUTION_CORRECTION.md`

The correction is implementation/provenance-only. It does not alter:

- the Stage-8 primary evidence or analysis;
- the Stage-9 robustness estimand;
- the frozen condition family;
- any treatment or comparator;
- any seed;
- any threshold;
- any detector parameter;
- replay policy;
- latency;
- symbolic gate;
- endpoint;
- statistical family.

Historical v1 artifacts remain immutable under `artifacts/cd_robustness_v1`. Corrected execution
uses new identities:

- `data/manifests/cd_stage9_run_config_v1_1.json`;
- run ID `cd-robustness-v1_1`;
- `artifacts/cd_robustness_v1_1`;
- `results/frozen/cd_robustness_v1_1`.

Before v1.1 config preparation, the implementation verifies the exact historical failed-v1 file set,
writer hashes, execution-plan hash, first condition/seed, exception, absence of any historical
`result.json`, and absence of a historical compact export. The v1.1 config records raw hashes of the
preserved historical files.

The corrected reader requires the real Stage-8 `files` list schema and fails closed on a mapping
shape. Regression tests include the governing Stage-8 compact manifest.

A wrapper-safe `verify-config` command is provided so config verification runs under the same frozen
PowerShell runtime environment as scientific execution.
