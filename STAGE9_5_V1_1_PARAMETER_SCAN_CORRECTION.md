# Stage 9.5 v1.1 Parameter-Scan Measurement Correction

**Status:** VERSIONED ASSURANCE-TOOL CORRECTION AFTER PRESERVED v1 SCAN FAILURE  
**Governing protocol:** `STAGE9_5_Q1_INDEPENDENT_ASSURANCE_PROTOCOL.md`  
**Failed scan head:** `3ca7a482ba3f71bd9c32863b033295492d112228`  
**Failed workflow run:** `38424890099`  
**Failed artifact ZIP SHA-256:** `6744bca3a726981c328f4016a4666728a57ee7cc8ef1d10265c3f10a979f7848`

## 1. What failed

The v1 Stage-9.5-0 scanner correctly failed closed, but its candidate model was too broad for the scientific question.

It reported 956 unclassified high-leverage candidates. Inspection of the preserved report showed that most were not distinct unregistered scientific controls. They were mainly:

1. historical outcome/statistic numbers in `METHODOLOGY_LEDGER.md`;
2. repeated mirrors of already-frozen controls inside corrected Stage-8 and Stage-9 manifests;
3. runtime/provenance fingerprints repeated once per seed;
4. development-selected per-seed threshold maps represented as many individual scalars instead of one registered control family;
5. prespecified Stage-9 sensitivity-condition values that were not yet represented as registry families.

The scanner unit tests passed. The failure was therefore a measurement/scope defect in the completeness audit, not a Stage-8/9 scientific defect.

## 2. Evidence-access boundary

No new Stage-10 scientific treatment outcome was accessed.  
No Stage-8 or Stage-9 scientific setting, endpoint, treatment, threshold, seed, evidence file, or interpretation was changed.

The failed v1 audit is preserved at:
`results/audits/stage9_5_v1/parameter_scan_failure.json`.

## 3. Smallest correction

Version 1.1 changes only how Stage-9.5-0 maps source/config literals to material control families.

### Canonical-source rule

For parameter completeness, scan the **accepted corrected canonical configs**:
- `data/manifests/cd_primary_run_config_v1_1.json`;
- `data/manifests/cd_stage9_run_config_v1_1.json`.

Historical v1 configs remain preserved and hash-audited but are not double-counted as independent parameter surfaces.

### Protocol-text rule

Literal extraction is restricted to prospective/binding protocol text. `METHODOLOGY_LEDGER.md` is a historical execution/outcome ledger and is removed from literal parameter discovery. It remains part of later provenance and claim-traceability audits.

### Semantic-family rule

A material control may legitimately be a family, for example:
- five seed-specific monitor thresholds;
- four lambda-specific five-seed fusion thresholds;
- deterministic RNG namespace set;
- Stage-9 latency family;
- Stage-9 detector family;
- Stage-9 reporting-window family;
- static symbolic-gate family.

The scanner matches these by semantic locator patterns to one registered control-family entry rather than requiring every repeated scalar to appear as a separate entry.

### Provenance/runtime-mirror rule

Repeated seed runtime fingerprints, hashes, platform strings, commit identities, and mirrored frozen-primary-contract blocks are provenance evidence, not additional hyperparameters. They are retained for the 9.5-1/9.5-7 hash/provenance audits and excluded from parameter-count inflation.

## 4. What does not change

The v1.1 correction does **not**:
- remove any genuinely high-leverage scientific control from consideration;
- change the allowed parameter classes;
- change the rule that an unclassified high-leverage control blocks Stage 9.5;
- alter any Stage-8/9 scientific value;
- redefine a failed scan as a pass;
- suppress negative or inconvenient findings.

The corrected scan must still fail if a material control name/key in canonical scientific source/config/protocol text has no registry family and disposition.

## 5. Additional registry families exposed by v1

The v1 failure usefully identified registry families that must be explicit in v1.1:
- seed-specific System-A monitor thresholds;
- seed/lambda-specific frozen fusion-threshold maps;
- no post-hoc threshold recalibration;
- Stage-9 prespecified lambda family;
- Stage-9 reporting-window family;
- Stage-9 latency family;
- Page-Hinkley threshold/delta;
- ADWIN-Brier detector signal;
- no-replay condition;
- static symbolic gate, including Wilson-LCB removal and minimum covered 100;
- boundary visibility to adaptive runner;
- replay-enabled primary condition;
- lifecycle evaluation switches such as complexity inclusion only where they represent policy rather than local function plumbing.

These are registry-completeness additions, not new experiments or retuning.
