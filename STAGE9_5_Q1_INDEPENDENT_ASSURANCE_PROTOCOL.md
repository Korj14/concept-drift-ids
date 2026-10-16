# Stage 9.5 Q1 Independent Assurance Protocol

**Status:** PROSPECTIVE BINDING ASSURANCE PROTOCOL — NO STAGE-10 OUTCOME ACCESS  
**Protocol ID:** `stage9.5-q1-assurance-v1`  
**Upstream accepted closure head:** `4dca828acb3916feb3f30d61f1b587240a6eba19`  
**Target integration branch:** `stage8-cd-primary-evaluation`

## 1. Purpose and authority

Stage 9.5 is an integrity stage, not a new treatment experiment. It does not replace, retune, or reinterpret the accepted Stage-8/Stage-9 primary and robustness evidence. It independently tests whether the frozen evidence chain is reconstructible, statistically reproducible, causally guarded, software-auditable, and traceable to publication claims.

The governing scientific authority remains `RESEARCH_DOCTRINE.md` / the project doctrine. The operational requirements are the reconciled implementation plan, the Q1 adversarial register, the frozen Stage-8/Stage-9 protocols, and the accepted evidence identities.

No Stage-10 adaptive/scientific treatment outcome may be accessed until:
1. Stage 9.5 is formally closed with zero unresolved Class-A defects; and
2. the Stage-10+ replication/sensitivity protocol is prospectively frozen.

## 2. Immutable upstream evidence

Stage 9.5 binds to, and must not modify, the accepted evidence chain:

- Stage-8 primary evidence commit: `c2ded83b8195b9321e715626c1f305f9627936e8`;
- Stage-8 compact manifest canonical identity: `409b516d75cbc5e71d3633019008432ea6088d1d923b4e4a95570263528ed523`;
- Stage-8 confirmatory aggregate identity: `1be77ce4be9f3faad021a3f3bfd636488e5de6aa1b2a6e7c596e48feb41bb54d`;
- corrected Stage-8 Phase-C config manifest: `d380fce5f9db8f0b639dc999298a263b10a10a3d02e35def226a121d098e2222`;
- Stage-9 v1.1 evidence commit: `9a05602b68cfaee7c45d2002a760b65115a581fd`;
- Stage-9 aggregate canonical identity: `6432dd5791f0baa9bdb2597c072b866814fb614f5a1f670dffec7f760bd1491a`;
- Stage-9 compact-manifest canonical identity: `d2d6f1a75aa427f2ba1769b8fef2d51253a5f10b5d3bfdb6c31de10d811aae22`;
- Stage-9 execution-plan SHA-256: `4ae426dd32ffed2384b4565710364459f4ee0ac2752543d6ec075facf66e53c8`;
- Stage-9 v1.1 config-manifest SHA-256: `b72fc0dce0df46974737cd0c33714cc17b23f31ce188e92d318b1787c0ae027e`;
- Stage-9 post-export closure head: `4dca828acb3916feb3f30d61f1b587240a6eba19`.

Any Stage-9.5 finding that requires changing these accepted scientific objects is a Class-A issue and invokes the versioned correction/restart doctrine. Ordinary robustness dependence cannot be used to overwrite them.

## 3. Evidence classes and stop rules

Every Stage-9.5 finding must be classified:

- **Class A — invalidating/restart:** future/boundary leakage, premature labels, treatment-dependent neural trajectories in a matched-isolation claim, wrong scenario/preprocessing/checkpoint/R0/threshold/seed, retrospective prediction replacement, forbidden generation/validation overlap, wrong endpoint, selective seed exclusion, material provenance/hash failure, or a treatment/estimand/information-set mismatch.
- **Class B — robustness-dependent:** accepted primary object remains valid but a prospectively frozen sensitivity/ablation/replication is required.
- **Class C — scope/external validity:** causal object remains valid but claim breadth must be narrowed and/or externally replicated.

Class A stops Stage 9.5 progression to Stage 10. Failures and failed audit attempts are preserved write-once; they are never overwritten.

## 4. Stage-9.5 output isolation

New assurance code must not modify frozen scientific execution modules merely to make an audit pass.

Preferred locations:

- assurance tools: `tools/stage9_5/`;
- assurance tests: `tests/stage9_5/`;
- developer-only static configuration: repository-root assurance config or `tools/stage9_5/`;
- machine-readable audit evidence: `results/audits/stage9_5_v1/`;
- heavy/local reconstruction evidence: `artifacts/stage9_5_v1/`.

The historical `requirements-lock.txt` remains unchanged. Developer-only lint/type/mutation dependencies, if needed, must use a separate assurance dependency file.

## 5. Work-package order

The order is binding.

### 9.5-0 — parameter/control completeness audit

Before any claim of parameter completeness:

1. mechanically enumerate material constants from frozen manifests/configs/protocols and scientific source;
2. scan Python source using AST-based literal extraction plus targeted semantic patterns;
3. compare scan results with a versioned parameter register;
4. classify every material choice using the frozen schema;
5. fail closure on any unclassified high-leverage constant.

Materiality includes any choice capable of changing:
- scenario membership or chronology;
- target/feature semantics;
- prediction-before-label information timing;
- drift detection/event timing;
- adaptation evidence, replay, optimizer/update budget;
- fusion/threshold authority;
- symbolic generation, validation, gate, lifecycle, conflict, publication or retirement;
- endpoint/estimand/statistical family;
- RNG namespace, deterministic runtime or evidence identity.

Literal integers used only for indexing, serialization formatting, loop counters, dimensional plumbing, or deterministic IDs are not scientific hyperparameters, but the scanner must retain an auditable exclusion record rather than silently dropping them.

### 9.5-1 — fresh-clone reconstruction

In a clean clone/environment:
- verify exact repository/config/evidence identities;
- install the historical frozen runtime where historical execution is being reconstructed;
- verify scenario/preprocessing/System-A/R0 identities;
- verify accepted Stage-8/9 compact evidence;
- document every required external/heavy artifact and whether it is retrievable;
- fail if undocumented workstation-local state is necessary.

### 9.5-2 — independent statistical oracle

Implement a verification path that does **not** import production aggregation/reporting modules.

It must independently recompute, from immutable evidence:
- per-seed arm contrasts;
- MCC, F1, FPR and available explanation/coverage endpoints from primitive counts/fields where possible;
- E1/E2/E3 effects;
- mean, median and sample SD;
- 95% Student-t interval with df=4;
- exact one-sided Stage-8 sign probabilities;
- Holm correction for the frozen three-test Stage-8 family;
- sign counts;
- leave-one-seed-out mean ranges;
- Stage-9 robustness condition summaries without creating a new confirmatory p-value family.

Predeclared comparison rules:
- discrete counts, labels, seed sets, file sets and hashes: exact equality;
- values stored as exact JSON constants that can be recomputed without numerical model execution: absolute tolerance `1e-12`;
- recomputed floating metrics from stored probabilities/predictions where platform/library order can introduce harmless floating variation: absolute tolerance `1e-10`, with any larger discrepancy treated as a blocking finding until explained;
- rounded manuscript display values are never the authority.

### 9.5-3 — causal/information property tests

Add adversarial fixtures that must fail closed for at least:
- label release before prediction;
- detector observation before label maturity;
- boundary/reference supplied to adaptive components;
- stale/wrong checkpoint admitted to checkpoint-pure detector epoch;
- C/D shared-neural trajectory divergence;
- wrong R0 start identity;
- wrong seed or threshold binding;
- generation/validation evidence overlap;
- retrospective replacement/recomputation of prediction evidence;
- treatment-dependent detector input;
- symbolic operator/RNG mismatch across trigger arms;
- `lambda=1` symbolic predictive influence;
- write-after-freeze / partial write-once output reuse.

Existing production tests may satisfy a requirement only if Stage 9.5 records the exact test and adds an adversarial fixture where the current coverage is merely positive-path or metadata-only.

### 9.5-4 — targeted mutation testing

Mutation testing is scoped to scientific guards, not arbitrary mutation score.

The defined high-risk mutation set must include:
- `<` versus `<=` maturity and publication boundaries;
- prediction/label event-order inversion;
- boundary masking removal;
- checkpoint identity comparison bypass;
- seed/R0/threshold comparison bypass;
- generation-validation disjointness bypass;
- opportunity-budget off-by-one/fifth retry;
- no-op opportunity non-consumption;
- `lambda=1` symbolic contribution;
- manifest/hash verification bypass;
- arm/shared-neural identity comparison bypass.

Closure requires 100% kill of the defined high-risk mutant set. Equivalent/non-executable mutants must be justified explicitly and may not be silently removed.

### 9.5-5 — static software assurance

Use developer-only lint/type/static checks on scientific and assurance modules.

Minimum intended tools: Ruff plus mypy (or a documented equivalent if a concrete incompatibility is found). Static tooling must not rewrite the historical runtime lock.

Every finding is triaged:
- behavior-changing/scientific-risk -> resolve/version or Class-A/B disposition;
- cosmetic/legacy -> document without rewriting frozen evidence-generating code solely for style.

### 9.5-6 — clean deterministic full-seed rerun

Rerun at least one complete accepted Stage-8 seed in a clean environment using the exact historical execution/config identity required by the original exact-head contract.

The rerun is verification evidence, not a replacement result. Do not bypass exact-head protection by executing from the current Stage-9.5 head. If execution requires a historical checkout or worktree, use it.

> **Prospective execution correction after replay-equivalence audit.** The original sentence above is preserved as the frozen base-protocol minimum, but it is not by itself an executable current 9.5-6 procedure. The historical implementation has global upstream barriers: Phase B verifies all five Phase-A seeds before symbolic treatment, and corrected Phase C verifies all five Phase-A plus all five Phase-B seeds before scoring any seed. In addition, the historical upstream manifest identities include non-replay-invariant runtime/timing diagnostics. Current 9.5-6 execution is therefore governed by `STAGE9_5_6_REPLAY_EQUIVALENCE_CORRECTION_PROTOCOL_V1_1.md`: recover both required external artifact sets; reconstruct all five Phase-A seeds and all five Phase-B seeds under the frozen historical environment; preserve/reproduce the original failed Phase-C v1 seed-0 lineage; regenerate and verify the correction config under unchanged scientific blocks; then execute the frozen corrected Phase-C rerun target. This correction narrows how the original requirement may be satisfied; it does not replace accepted Stage-8/9 evidence or broaden the assurance claim.

Compare promised exact identities exactly. Where a stored artifact explicitly permits canonical/numerical equivalence rather than byte identity, use only the predeclared equivalence rule.

### 9.5-7 — claim-to-evidence traceability

Create a machine-readable ledger mapping every intended quantitative manuscript claim to:
- claim ID and text/status;
- immutable evidence path;
- exact field/key/range;
- generating or verification code path;
- config/protocol identity;
- evidence commit/hash;
- interpretation status: confirmatory, secondary, exploratory, negative, limitation;
- display transformation/rounding rule.

No hand-entered orphan number is permitted. Because the manuscript is not final, Stage 9.5 may close with a complete current Stage-8/9 ledger plus an explicit final-submission gate requiring zero orphan manuscript numbers.

### 9.5-8 — independent table/figure regeneration

Build a reporting-only path from immutable evidence that does not import production aggregate/reporting code.

It must emit machine-readable table/figure source data and compare every included numerical value with the independent oracle. Presentation code may not alter evidence values.

### 9.5-9 — hostile-review closure audit

Re-run the Q1 adversarial register after 9.5-0 through 9.5-8.

Closure requires:
- zero unresolved Class-A defects;
- explicit completed or prospectively frozen disposition for every Class-B issue;
- explicit claim boundary/replication obligation for every Class-C issue;
- no hidden failed audit attempt;
- no Stage-10 outcome access;
- Stage-10+ master replication/sensitivity protocol frozen before Stage-10 treatment execution.

## 6. Parameter classification schema

Every registered material choice must be assigned exactly one primary class:

1. `scientific_hyperparameter`;
2. `algorithm_library_default`;
3. `causal_design_constant`;
4. `statistical_estimand_definition`;
5. `scenario_construction_constant`;
6. `reproducibility_rng_constant`;
7. `derived_quantity`.

Each entry must also record:
- accepted value/policy;
- source path and symbol/key;
- freeze provenance;
- rationale;
- leverage assessment;
- whether changing it would alter the accepted scientific object;
- completed sensitivity evidence, if any;
- Stage-10+ disposition;
- reviewer-facing justification.

Numerical appearance alone is never sufficient reason to sensitivity-test a constant.

## 7. Frozen Stage-8/9 choices that must not be retuned

Stage 9.5 must not reopen accepted:
- scenario row ranges/boundary/source assembly;
- original preprocessing state;
- System-A accepted checkpoints/seeds/threshold procedure;
- Stage-8/9 primary `lambda=0.50`;
- primary five seeds;
- E1/E2/E3 definitions;
- MCSC definition;
- 5,000-row primary reporting window;
- t interval/sign/Holm definitions;
- primary periodic schedule;
- accepted ADWIN primary defaults;
- primary replay policy;
- accepted lifecycle result.

A weakness discovered here is handled by Class A correction, Class B prospective sensitivity, or Class C replication/claim narrowing—not retrospective tuning.

## 8. Prospective Stage-10 obligations carried forward

Before Stage-10 treatment outcomes:
- freeze a direct attack-pattern/conditional-label-change scenario;
- freeze gradual and unseen/evolving-attack designs where defensible;
- freeze second-dataset inclusion/exclusion criteria before outcomes;
- strengthen candidate selection with independent confirmation or nested equivalent;
- prospectively test withdrawal/lifecycle authority semantics because the accepted mechanism is withdrawal-dominant;
- prospectively test a defensible symbolic evidence-horizon alternative;
- retain MCSC unchanged while triangulating explanation constructs;
- quantify 100-bootstrap gate granularity and include a higher-replicate sensitivity where feasible;
- add alternative periodic/random-clock schedules only if trigger superiority is claimed;
- add label-noise/missing-label/poisoning stress only if operational robustness is claimed;
- add a second neural backbone if architecture-invariant claims are made.

## 9. Freeze and amendment rule

This protocol must be committed before new Stage-9.5 audit evidence is generated.

Any later correction to this protocol must:
1. preserve the original version;
2. state whether any Stage-9.5 evidence had already been accessed;
3. identify the defect;
4. make the smallest correction necessary;
5. create a new version;
6. never use observed audit/scientific outcomes to weaken a guard or choose a favorable criterion.

The eventual Stage-9.5 closure report must cite the exact protocol/config freeze commit used for execution.
