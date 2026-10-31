# Stage 10A — G2 external launch signature gate

**Role:** WARM engineering component, not scientific authority, a production host attestation, frozen execution schema or RELEASE. Stage 10A treatment execution remains prohibited.

## Verified integration gaps

Inherited Stage 8 Phase A computes the full SharedTrajectory in memory and writes the evidence after the run. Its control plane ingests row.label at prediction time. Phase B reconstructs labeled symbolic rows and reads checkpoint bytes through torch.load(..., weights_only=False). The existing evidence writer lacks per-prediction fsync. These observations are not proof of Stage 8 scientific leakage; they do not satisfy Stage 10A's stronger prospective G2 production trust requirement.

## Concrete new control

The source-only stage10a_g2_signed_receipt.py verifies an actual detached Ed25519 signature using OpenSSL, canonical JSON, an **independently pinned public-key SPKI SHA-256**, exact-head Git identity, accepted master/Stage10A/source/checkpoint authority fingerprints, fixed Python 3.11.9 and thread settings, and distinct claimed writer/escrow/checkpoint principals. It rejects wrong keys, modified signed bytes, unsigned claims, unapproved RELEASE assertions, and arbitrary added fields. Unit tests use disposable test-only keys. No private signing key is committed, and no original data, real checkpoint or model is read.

**It verifies an authenticated claim, not independent control of the signing principal.** The private key and public-key pin must be separately controlled and provisioned outside the experiment writer; actual label access-denial and durable append observations must be collected by that custodian. A writer who controls both the signing key and the supplied pin can forge the claim. A signed JSON receipt alone is neither genuine physical fsync attestation nor OS access enforcement.

The verifier unconditionally reports stage10a_g2_accepted=false, stage10a_release_ready=false, and stage10a_treatment_execution_authorized=false. This component closes no release gate.

## Next integration boundary

Provide a truly independent launch controller and key pin, test actual writer read-denial of labeled raw data under protected host/mount principals, require independent prediction-commit acknowledgement before origin-clock-minus-5000 labels are released, preserve Stage 8 neural/ADWIN/replay and symbolic update semantics, and enforce protected original/child checkpoint custody with Phase B read-only controls. After G1 scientific approval and G2 integration review, a separate versioned Stage 10A RELEASE remains mandatory. Stage 11 environmental replication is not an execution prerequisite for GoldenEye.
