# Stage 9.5 v1.11.1 Validation-Guard / Provenance False-Positive Correction

**Status:** TECHNICAL SCANNER CORRECTION AFTER REAL v1.11 SCAN BLOCK  
**Governing protocol:** `STAGE9_5_Q1_INDEPENDENT_ASSURANCE_PROTOCOL.md`  
**v1.11 exact head:** `10c43bb9d049b8bcee34b5a167efb5b431495af8`

## 1. v1.11 result

The v1.11 scanner suite passed all 21 tests, then the real hash-bound scan executed and blocked on exactly four high-leverage material candidates with zero ambiguity.

The same-head Stage-9 robustness contract passed.

The four residuals are:

1. `DelayedLabelQueue.__init__: if latency < 0`;
2. primary shared-runner `validate: if self.label_latency < 0`;
3. Stage-9 shared-runner `validate: if self.label_latency < 0`;
4. preserved failed Phase-C correction identity: `attempt["seed"] != 0 or failure["seed"] != 0`.

These are not treatment values. The first three are non-negativity domain-validation guards; the fourth is a historical failed-run provenance assertion.

## 2. Verification of the intended v1.11 fixes

The v1.11 artifact confirms the previously missed scientific controls are now material and registered:

- Stage-9 `label_latency: 0` -> `stage9.latency_family`;
- all executable `replay_enabled=True/False` mirrors -> primary replay / no-replay controls;
- lifecycle `0.95/0.50/0.50` overlap defaults -> `lifecycle.overlap_thresholds`;
- lifecycle failure-streak `+1` / `max(1,...)` semantics -> `lifecycle.state_machine_policy`.

Therefore the four remaining blockers are scanner false positives rather than unresolved scientific controls.

## 3. v1.11.1 correction

v1.11.1 keeps the v1.11 scientific register unchanged and adds only two source-aware expression exclusions:

- numeric zero used solely as the lower bound in a latency non-negativity validation guard;
- numeric zero used solely in the preserved failed-attempt seed-identity assertion in `cd_primary_correction.py`.

A regression test requires these guards to remain excluded while `label_latency: 0` in executable Stage-9 treatment construction remains material and registered.

No Stage-8/9 scientific value, treatment, endpoint, seed, threshold, scenario, information set, or inference rule changes.
