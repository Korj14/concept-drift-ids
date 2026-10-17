# Stage 9.5 v1.7 Residual-Disposition Correction

**Status:** VERSIONED COMPLETENESS CORRECTION AFTER v1.6 SCAN BLOCK  
**Governing protocol:** `STAGE9_5_Q1_INDEPENDENT_ASSURANCE_PROTOCOL.md`

The v1.6.1 scanner passed all scanner unit tests and then executed the real hash-bound completeness scan. It reduced the strict v1.5 block from 317 unclassified / 5 ambiguous candidates to 53 unclassified / 3 ambiguous candidates, while the same-head Stage-9 regression contract remained green.

Every v1.6 residual was reviewed individually. No new Stage-8/9 treatment, endpoint, seed, threshold, scenario, or information-set mismatch was discovered.

v1.7:
- links remaining execution mirrors to already accepted controls;
- resolves the three ambiguous mappings by assigning each occurrence to one scientific role;
- registers deterministic seed derivation, seed-count, output-subdir and preprocessing-chunk identities explicitly;
- excludes only named runtime state/sentinel values, binary file-I/O modes, and safe mathematical zero fallbacks from scientific parameter status.

The closure rule is unchanged: zero unclassified material candidates and zero ambiguous material mappings. Stage 10 remains locked.
