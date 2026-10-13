# Stage 9.5 v1.5 Strict Matching and Hash-Bound Scope Correction

**Status:** VERSIONED COMPLETENESS-METHODOLOGY CORRECTION AFTER v1.4 BLOCK  
**Governing protocol:** `STAGE9_5_Q1_INDEPENDENT_ASSURANCE_PROTOCOL.md`

The technically corrected v1.4 scanner executed and blocked with four unclassified material candidates and zero unclassified high-leverage candidates. Adversarial review then found two additional scanner-methodology weaknesses: common values could map ambiguously to multiple register entries, and a locator-pattern match could register a value without checking that the value itself matched the accepted control. The hand-curated Python scan scope also omitted scientific source files hash-bound by the accepted Stage-8/Stage-9 configs.

v1.5 therefore changes assurance methodology only:

1. scientific Python scan scope is the exact union of `scientific_source_hashes` Python paths in the accepted Stage-8 and Stage-9 v1.1 configs;
2. locator patterns identify a control but never bypass accepted-value matching;
3. string matching is exact rather than substring-based;
4. every material candidate must map to exactly one register entry; zero mappings and multiple mappings both block;
5. singular arm/phase/condition/group/metric/weight identifiers and Page-Hinkley min-instances/alpha/mode are material discovery terms;
6. the Stage-9 condition family, execution routing, paired metric set, full Page-Hinkley config, full static-gate config, duplicated arm identity, stream row counts, and lambda=1 guard are explicitly registered.

No accepted Stage-8/9 scientific value is changed. v1.5 is intentionally allowed to expose a larger residual set; a larger honest block is preferable to a false completeness pass.
