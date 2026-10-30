# Stage 9.5 v1.4.1 Scanner Syntax Correction

**Status:** TECHNICAL HARNESS CORRECTION BEFORE v1.4 COMPLETENESS SCAN  
**Governing protocol:** `STAGE9_5_Q1_INDEPENDENT_ASSURANCE_PROTOCOL.md`  
**Failed head:** `585ce055633fd9c566af2e6d85ad126f3b2d5d2e`

The v1.4 Stage-9.5 assurance workflow failed during Python test collection, before the parameter scan executed. A literal `\\n` token was accidentally written between adjacent raw-string fragments in `MATERIAL_RE`, producing a Python `SyntaxError`.

This is a scanner-harness defect only. The same-head Stage-9 regression contract passed. No Stage-8/9 scientific artifact, treatment, outcome, parameter register entry, materiality criterion, or closure rule changes.

v1.4.1 removes only the malformed literal token. The frozen `stage9_5_parameter_register_v1_4.json` remains unchanged and is rerun under the same zero-unclassified-material closure rule.
