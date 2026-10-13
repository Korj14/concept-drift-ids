# Stage 9.5-1 v1.1 Hash-Semantics Correction

**Status:** TECHNICAL RECONSTRUCTION-VERIFIER CORRECTION AFTER FIRST CLEAN-CLONE RUN  
**First-run head:** `29ed8900946266efd643d2fa070885f42760062f`  
**First-run workflow:** `38452707344`  
**Fresh-clone job:** `115487417958`

## First-run result

The independent verifier tests passed (6/6), the historical frozen runtime installed exactly, Stage 9.5-0 remained green, and the same-head Stage-9 robustness contract passed.

The reconstruction run reported six identity failures plus one external-artifact blocker.

The substantive committed evidence bytes were intact:

- Stage-8 compact export: 109/109 files matched their frozen byte hashes;
- Stage-9 compact evidence: 357/357 files matched;
- all five R0 rule artifacts matched;
- preprocessing identity matched;
- frozen runtime identity matched;
- System-A manifest and all five checkpoint declarations matched.

## Harness defect 1 — writer payload-hash ordering

Accepted JSON writers use two identity layers. The scientific inner identity (`manifest_sha256`, `aggregate_sha256`, or `plan_sha256`) is computed first. `write_json_new` then appends a separate `payload_sha256` over the already-hashed object.

The v1 verifier removed only the inner hash before recomputation, incorrectly leaving `payload_sha256` in the inner-hash domain.

v1.1 reproduces the accepted verification order exactly:

1. remove and verify `payload_sha256` over the remaining object;
2. remove and verify the inner scientific identity over its original core.

## Harness defect 2 — Windows checkout line endings

The frozen scenario raw SHA-256 is the repository LF text identity:
`c864cd53b155ae1b29f2321d28b18562381fb6d1a77dc563b5f5eba3ec3eb82c`.

On the Windows clean runner, checkout converts the otherwise identical file to CRLF, yielding:
`1771b2dbdf0f6b8b47207af04d31a6d6b015f8ea2bdadfe5dfdb293f0a552fd1`.

The semantic canonical JSON identity remains exactly:
`3d1c3f9775ac5c8a73053634784be513bb1714ef7f26fa9db406ccd78c4344e3`.

v1.1 therefore verifies the frozen repository text identity by normalizing EOLs to LF before the raw-text SHA comparison, while independently retaining the canonical JSON check.

## Unchanged blocker

The five frozen System-A checkpoint byte files remain unavailable in the clean clone. Their absence remains a blocking 9.5-1 finding. This correction does not weaken, bypass, regenerate, or substitute that requirement.

No accepted scientific value, treatment, endpoint, evidence result, or identity is changed.
