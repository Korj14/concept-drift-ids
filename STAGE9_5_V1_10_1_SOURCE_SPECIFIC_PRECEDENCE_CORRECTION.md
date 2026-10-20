# Stage 9.5 v1.10.1 Source-Specific Material Precedence Correction

**Status:** TECHNICAL SCANNER CLASSIFICATION CORRECTION BEFORE v1.10 COMPLETENESS SCAN  
**Governing protocol:** `STAGE9_5_Q1_INDEPENDENT_ASSURANCE_PROTOCOL.md`  
**Failed head:** `93a34e0d057608d0adc080caa5be2d129be48733`

The v1.10 assurance run stopped in the scanner regression suite with 19 passes and one failure. The real completeness scan did not execute. The same-head Stage-9 robustness contract passed.

The failing case was `streak = 1` in the symbolic lifecycle state-machine test. v1.10 correctly recognized `streak` as a source-specific material lifecycle control, but the older generic small-integer bookkeeping heuristic had already assigned an exclusion reason because `streak` is not part of the global semantic-name regex.

v1.10.1 changes only scanner precedence: an identifier that is **explicitly source-classified as material** may override the generic “small indexing/control integer” exclusion. It does not override dunder/internal, runtime-sentinel, file-I/O-mode, empty/hash, or any expression-level exclusions.

No register value, Stage-8/9 scientific parameter, treatment, endpoint, seed, threshold, scenario, information set, or inference rule changes.
