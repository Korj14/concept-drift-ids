# Stage 9.5 v1.2 Parameter-Scan Semantic-Protocol Correction

**Status:** VERSIONED ASSURANCE-TOOL CORRECTION AFTER PRESERVED v1.1 COMPLETENESS BLOCK  
**Governing protocol:** `STAGE9_5_Q1_INDEPENDENT_ASSURANCE_PROTOCOL.md`  
**Preserved v1.1 failure:** `results/audits/stage9_5_v1_1/parameter_scan_failure.json`  
**v1.1 blocked head:** `abef5d1f63a7654365728e79e7144af6f95855db`

## 1. Why v1.1 remained blocked

The v1.1 scanner reduced the initial 956 high-leverage candidates to 137 and exposed several genuine registry-mapping gaps. Inspection also showed a remaining scanner measurement defect in Markdown protocol parsing.

The numeric tokenizer treated document structure and formatted prose as independent scientific constants, including:

- section/stage numbers such as “Stage 8”, “Stage 9”, “Section 6”;
- enumerated-list numbers;
- seed-range notation such as `<0..4>`;
- comma-formatted integers such as `27,706`, split into `27` and `706`;
- leading-dot decimals such as `.50`, parsed incompletely;
- prose that mentions an already-completed sensitivity or audit requirement without defining a new control.

That behavior inflates the parameter surface and is not a valid mechanical audit of scientific choices.

## 2. Scientific status of the v1.1 block

The v1.1 block is preserved. It is not reclassified as a pass.

No Stage-10 treatment outcome was accessed. No Stage-8/9 scientific value, treatment, endpoint, threshold, seed, or evidence artifact was changed.

The same-head Stage-9 robustness/regression workflow passed, so the v1.1 block does not indicate a regression of accepted Stage-8/9 execution code.

## 3. v1.2 correction

### 3.1 Canonical machine-readable controls remain fail-closed

Canonical corrected Stage-8 and Stage-9 configs plus scientific Python source remain the primary machine-readable parameter surface.

Every material scalar/string/bool found there must map to a registered semantic control family or be retained in the exclusion log with a specific non-parameter reason.

### 3.2 Protocol scanning becomes declaration-based

Scientific protocols are still scanned mechanically, but a line is a parameter declaration only when it contains a parameter/control semantic plus an explicit value/policy declaration, for example:

- assignment/comparison syntax such as `lambda=.50`, `L=5,000`, `>= .80`, `<= 4`;
- an explicit set/range such as seeds `0..4` or `{8,12,16}`;
- an explicit row/window/budget quantity tied to a named control;
- exact clock/schedule declarations;
- deterministic runtime declarations such as `PYTHONHASHSEED=0`.

Headings, Stage numbers, list ordinals, evidence/result prose, and references to a completed analysis are not treated as new parameter declarations.

Formatted numeric values are normalized before comparison:
- comma separators are removed;
- leading-dot decimals are read as decimals;
- percentages remain percentages only when explicitly marked.

### 3.3 Q1 register and assurance-correction prose are not scientific parameter authorities

`Q1_ADVERSARIAL_AUDIT_REGISTER.md` remains a mandatory Stage-9.5 input, but it is an adversarial obligation/status register rather than a source of experimental parameter definitions. Its requirements are checked in the hostile-review closure and traceability stages, not by numeric-literal parameter discovery.

Likewise, Stage-9.5 correction documents are provenance for the assurance process; their version/stage numbers are not experimental hyperparameters.

The parameter scanner therefore limits Markdown parameter discovery to the frozen scientific execution/robustness protocols and the binding Stage-9.5 assurance protocol only for its explicit assurance tolerances/criteria.

## 4. Genuine registry mappings added in v1.2

The v1.1 report exposed valid control-family mappings that were missing or too narrow:

- primary online symbolic gate mirrored inside the corrected primary config;
- primary reference-boundary role;
- Stage-9 reference-boundary index/role mirror;
- the five primary seeds as a source-level constant;
- unchanged Stage-9 primary ADWIN/hard-error/5,000-latency semantics reused by conditions;
- Stage-9 condition `changed_factors` entries;
- frozen Stage-8 trace/source and threshold-source declarations for offline sensitivity;
- assurance numeric tolerances and 100%-kill requirement for the defined high-risk mutant set.

These are registry-completeness corrections only. They change no accepted scientific value.

## 5. Pass rule is unchanged

v1.2 still blocks if a material high-leverage control in canonical config/scientific source or an explicit parameter declaration in a governing scientific protocol has no registered disposition.

The correction changes measurement validity, not the scientific standard.
