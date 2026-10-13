# Stage 9.5 v1.6.1 Scanner Classification-Logging Correction

**Status:** TECHNICAL HARNESS CORRECTION BEFORE v1.6 PARAMETER SCAN  
**Governing protocol:** `STAGE9_5_Q1_INDEPENDENT_ASSURANCE_PROTOCOL.md`  
**Failed exact head:** `26f19abc209e210cdd3083c7a84539325f01e183`

The v1.6 assurance run passed environment/freeze verification but failed two scanner unit tests before the parameter scan executed.

The defects are limited to scanner classification mechanics:

1. a mathematical/probability zero fallback was correctly not promoted to a material candidate, but the expression visitor returned before recording the exclusion reason;
2. the intended Markdown range normalization for forms such as `<0..4>` had not been inserted, allowing the numeric parser to interpret the range as decimal `0.4`.

v1.6.1 records explicit mathematical exclusions before expression-relevance filtering and applies the range normalization before Markdown numeric discovery.

The frozen v1.6 parameter register, hash-bound source scope, exact/unique matching rule, accepted Stage-8/9 values, and closure criteria are unchanged. No Stage-8/9 scientific outcome was accessed or altered.
