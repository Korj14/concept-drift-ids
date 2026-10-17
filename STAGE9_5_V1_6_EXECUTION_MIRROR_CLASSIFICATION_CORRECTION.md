# Stage 9.5 v1.6 Execution-Mirror and False-Positive Classification Correction

**Status:** VERSIONED COMPLETENESS CORRECTION AFTER STRICT v1.5 DISCOVERY BLOCK

v1.5 successfully enforced the intended hostile-review standard: 38 hash-bound Python sources were scanned, material candidates required exact value+locator matching, ambiguous mappings blocked, and hard-coded material expression literals were surfaced. It therefore exposed 317 unclassified material candidates (196 high-leverage) and 5 ambiguous mappings.

Review shows three categories:

1. accepted controls mirrored in their execution modules but not yet linked in the register;
2. derived scenario/provenance/reporting fingerprints that should be registered but never tuned;
3. false-positive literals from test fixtures, anonymous-lambda tuple indices, probability-domain guards, and mathematical zero fallbacks.

v1.6 adds source-level mappings for the primary control plane, System-A configuration, symbolic lifecycle/generation/RNG controls, scenario fingerprints, Stage-9 detector/gate/window implementations, and secondary recovery/reporting definitions. It also classifies hash-bound test modules as verification fixtures rather than scientific parameter sources, and narrows expression discovery so mathematical identities and indexing syntax are logged as exclusions rather than parameters.

No Stage-8/9 accepted value changes. The v1.6 scan remains fail-closed on any unclassified or multiply-mapped material candidate.
