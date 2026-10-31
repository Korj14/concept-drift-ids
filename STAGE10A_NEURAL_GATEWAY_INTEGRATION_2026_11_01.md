# Stage 10A — real neural-loop gateway integration (source-only engineering)

**WARM technical evidence, not new scientific authority or RELEASE.** This
change introduces a Stage-10A-specific `Stage10AControlPlaneRunner` subclass
and a feature-only sealed source adapter. The accepted frozen Stage-8
`src/concept_drift_ids/cd_shared_runner.py` **remains byte-for-byte unchanged**,
so the historical `scientific_source_tree_sha256` contract remains valid.

The Stage-10A run loop preserves the inherited prediction/ADWIN/replay/update
functions and event structures, but exclusively accepts feature-only
`UnlabeledStreamRow`, requires a non-null external prediction gateway and
the unchanged 5,000-row latency, obtains an acknowledgement/grant for each
real predicted row before any matured ground truth is processed, and rejects
premature, missing, reordered or malformed label grants. The gateway
signature contains the actual neural score and current checkpoint identity,
not synthetic tokens. The production future service must observe durable
bytes before issuing labels.

`stage10a_neural_input.py` accepts only a hashed, sealed
138,530×77 `float32` feature file from the **already accepted real-source
custodian**, with no labeled raw CSV, true targets or evaluator boundary
available in the writer's code path.

**Unresolved and non-authorized:** This method is a code integration point,
not a protected external service, a Stage-10A production entrypoint, an
attested exact-host runtime, complete checkpoint custody, a sealed five-seed
trajectory or G3 RELEASE. The inherited post-hoc Stage-8 journal freezer
alone is not a durable append witness. The detailed S scientific freeze
under §R remains open. No original checkpoint loaded or Stage-10A real
predictions performed by this change.

**Next required production work:** implement independently privileged
label escrow/append daemon with private `labels.npy` and tested principal
denial; connect the daemon to this live neural loop, then bind original/
child checkpoint custody and Phase-B reads before formal G2 review.
