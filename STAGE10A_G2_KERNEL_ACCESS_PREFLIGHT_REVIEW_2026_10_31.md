# Stage 10A — G2 host-kernel access preflight (prospective integration review)

**Role:** WARM subordinate engineering evidence only. **NOT** an operational-schema freeze, proof of production custody, scientific approval, Stage 10A RELEASE, or changing-state authority. The only canonical state remains `STAGE10A_CURRENT_STATE_AND_RESUME.md`. Stage 10A real model/treatment execution is prohibited.

## Concrete gap this closes partially

The inherited Stage-8 Phase-A runner receives `row.label` at prediction time and writes the completed shared trajectory to its six evidence journals after in-memory execution. Phase B currently reconstructs labeled symbolic rows, and model checkpoints are read from the inherited resolver. Existing hash audits, a same-UID subprocess escrow and the authenticated-launch-claim signature verifier **do not themselves enforce** future-label confidentiality or the Phase-B file permission boundary. Retain all accepted Stage-8/9 results unchanged.

`tools/stage10/stage10a_g2_kernel_access_preflight.py` is a **real Linux host-readiness probe** to check one OS/DAC boundary without touching experiment data. A trusted root controller provides a strictly canonical, root-owned policy and five protected directories containing only disposable `.stage10a_access_probe` markers. The controller invokes `setpriv` to run Python probe processes as **five distinct nonroot UIDs and GIDs**, with supplementary groups and Linux capabilities dropped. The probes call actual `open(2)` for read and write capability, report the effective UID/GID, and fail closed when an expected permission is absent **or** an unexpected permission is present.

### Host role matrix checked

| Principal | Only permitted probe access | Required denials |
|---|---|---|
| Writer | Read/write own live Phase A | Future-label vault, original checkpoint vault, sealed Phase A and evaluator boundary |
| Label custodian | Read/write label vault | Writer/other vaults |
| Checkpoint custodian | Read/write initial-checkpoint vault | Writer/other vaults |
| Phase B reader | **Read** root-controlled sealed Phase A via its dedicated group, **no write** | Future labels, raw checkpoint vault, live writer and evaluator boundary |
| Evaluator | Read/write dedicated evaluator-boundary probe | Adaptive and custody probe roots |

The Phase-B checkpoint resolver must eventually use a *separately staged, explicitly read-only, post-seal child-checkpoint view*; the Phase B probe is intentionally denied access to the original-checkpoint vault. **All five real Phase A seals must precede any real Phase B mount activation.** The proposed OS role model is not yet accepted for real deployment or Windows. A trusted operator must not confuse a probe marker's permissions with guarantees about all files, open file descriptors, processes, Linux namespaces, root privileges, ACLs or changing mounts. A production access policy must deny `ptrace`/capability escape, control inherited file descriptors and supervise process/mount/cgroup ownership; this narrow check alone does not do those jobs.

### Evidence from this turn

The disposable Linux container test used a root controller, five isolated **numeric** UID/GID pairs, root-owned canonical policy and physically created probe files with ownership and mode checks (private vaults `0700/0600`, root-owned sealed Phase A `0750/0640`, Phase-B group-read-only). **13 tests passed in Python 3.13.5**, including the real UID-switching kernel matrix. A world-readable label probe, world-writable policy, invalid UID/GID, symlink and wrong directory permission fail closed. The tests never use CICIDS2017, actual labels, original checkpoint bytes, models, drift-control code or outcomes. In unprivileged CI, the test requiring root is **skipped**, never simulated as passed; deterministic policy-negative tests still run.

**Host-specific limitation:** This verified a disposable **local test environment**, not a separately controlled production runner. Only the exact probe targets and the tested host policies were checked. The output always sets `production_label_custody_verified=false`, `production_prediction_durability_verified=false`, `trusted_runtime_attestation_accepted=false`, `g1_method_approval_signed=false`, `g2_production_accepted=false`, `stage10a_treatment_execution_authorized=false`, and `stage10a_release_ready=false`.

### Exact deployment interface and remaining G2 closure

The privileged independent launch controller must provision the **real** role identities and protected roots *before* access to Stage-10A input. Provide a root-controlled canonical policy naming `attempt_id`, externally expected exact Git HEAD, five UIDs/GIDs, and the five **nonsecret probe** directory roots; ensure the phase-B sealed view is mounted read-only only after all five shared seeds seal. Invoke `python -m tools.stage10.stage10a_g2_kernel_access_preflight --policy /trusted/controller/policy.json` **from the protected host controller**, not from the adaptive writer; capture stdout and exit status outside writer control. File hashes from this observation can then be bound through the already implemented **externally pinned Ed25519 signed launch-receipt** verifier, but signer/key custody and this binding require independent review. Do not place the actual labeled source, keys, binaries or protected checkpoint URLs in the policy or test fixtures.

**Remaining non-circular G2 prerequisites:** a live source custodian that splits unlabeled 77-feature events from original private labels *before* writer access; non-bypassable authenticated append/fsync acknowledgement before each origin `clock-5000` grant; trusted exact-head controller/signing key; original/child neural byte and optimizer/replay/RNG lineage; Phase-B read-only mounts; evaluator-only 69,260 boundary and offline Phase C; failure-preserving five-seed artifact sealing. Demonstrate these controls on the actual designated execution host without loading the original model during the preflight. After G1 scientific signoff and G2 review, an independently authorized G3 treatment RELEASE is still required. No amount of successful nonsecret access-probe testing alone grants RELEASE.

**Disposition:** bounded G2 kernel-access **implementation checkpoint**, not G2 acceptance. Preserve prior synthetic and source-only receipts without rerunning them. The next task must connect the real label-custodian/append service and independent controller to the inherited neural event order without changing the frozen scientific mechanism; avoid further standalone synthetic trajectory variants.
