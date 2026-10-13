# Stage 9.5 v1.8.1 Test-Fixture Version Correction

**Status:** TECHNICAL HARNESS CORRECTION BEFORE v1.8 COMPLETENESS SCAN  
**Governing protocol:** `STAGE9_5_Q1_INDEPENDENT_ASSURANCE_PROTOCOL.md`  
**Failed head:** `eff8802c42f7597c2c3e6671a6c49a175f291cff`

The v1.8 assurance workflow failed in four temporary-root scanner tests before the real completeness scan executed. The scanner correctly referenced `stage9_5_parameter_register_v1_8.json`, while those fixtures still wrote the prior `v1_7` filename.

Thirteen scanner tests passed. The same-head Stage-9 robustness contract passed.

v1.8.1 changes only the four fixture filenames from `v1_7` to `v1_8`. It does not change scanner semantics, scan scope, the v1.8 register, any Stage-8/9 scientific value, treatment, endpoint, seed, threshold, scenario, information set, or inference rule.
