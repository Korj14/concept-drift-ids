# Stage 9.5-6 Stage-1 Reconstruction Execution Handoff

**Status:** EXECUTION HANDOFF / NOT CLOSURE AUTHORITY  
**Date frozen:** 17 October 2026  
**Governing contract:** `data/manifests/stage9_5_6_stage1_reconstruction_evidence_v1.json`  
**Verifier:** `tools/stage9_5/stage1_reconstruction_evidence.py`

## Purpose

This document defines the exact operator handoff for producing the still-missing
Stage-9.5-6 Stage-1 reconstruction evidence. It does not replace the machine
contract, verifier, replay-equivalence protocol, or eventual canonical report.

The authoritative success object is:

`results/audits/stage9_5_full_seed_rerun_v1/stage1_reconstruction_report.json`

A passing report must be derived by the frozen verifier. It must not be
hand-authored or reconstructed from copied booleans. The downstream replay
comparator recomputes the report's frozen contract identity and verifier-source
identity before accepting it, in addition to checking the report's canonical
hash, success fields, fixed path, and Git ancestry.

## Frozen runtime prerequisite

Execution is authoritative only under the historical frozen environment:

- Python: **3.11.9**
- dependency lock: `requirements-lock.txt`
- raw lock SHA-256:
  `5ef6553f286b84c117cd67febaf20292baf9930e7f4b6cf57918e2e00f965dd4`
- normalized-text lock SHA-256:
  `9f63cbe19dcb1b916c16603f5b7c01a2fa33ac11271ce2ef0014910158d6741d`
- historical replay head:
  `bfa14b942e4a5b2fbfa8aa3c43728a7f1cd81645`
- historical preprocessing Git blob:
  `52d71b6769671847af5b0c6d94e46156a45483e9`

The verifier itself checks the installed locked distributions and historical
source identity. A different Python version or dependency environment is not
acceptable closure evidence even if all reconstructed tables appear equal.

## Exact raw-input prerequisite

The raw root must contain exactly the authoritative CICIDS2017 source CSVs used
by the frozen contract. Their required SHA-256 identities are:

- `Monday-WorkingHours.pcap_ISCX.csv`  
  `852c4beb34eda186f32561fa79df7a0747e92e1a6535b01270820dd9ffe17f34`
- `Tuesday-WorkingHours.pcap_ISCX.csv`  
  `52b8692ae8c7d2ed04671fe2b98335693c0a92c7ab157d8c8b534d6523080851`
- `Wednesday-workingHours.pcap_ISCX.csv`  
  `893c27dc968bf7a8adef1689f90be55ca4a4dc3088fb63d6ff247ac56856df2a`
- `Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv`  
  `d67066211fb1689c78406f1506f4c44704ecb92088353d5c96d96d6474eb819d`
- `Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv`  
  `6bcda3857c2504676034e3ea57762d38393cc734cb377a726bd5cb153961b1b5`
- `Friday-WorkingHours-Morning.pcap_ISCX.csv`  
  `53a41c24d570ea83b7ac55b2e94df94e7a8216aeb80a2af0246b6bc8bb543000`
- `Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv`  
  `ca1824c51bfbb7b3c72290a11be04366ba8815878c6a1cc5c44cb1cee269e99b`
- `Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv`  
  `6ff1580f5f81c0ae28a26f7631721018577f5f7c5e0feac28b795fcfe7b411ee`

## Exact execution command

From a full checkout of the assurance branch with complete Git history and the
historical runtime installed:

```bash
python tools/stage9_5/stage1_reconstruction_evidence.py \
  --raw-root <directory-containing-the-eight-authoritative-csv-files> \
  --reconstructed-root artifacts/stage9_5_stage1_reconstruction_v1/interim/cicids2017 \
  --report results/audits/stage9_5_full_seed_rerun_v1/stage1_reconstruction_report.json \
  --contract data/manifests/stage9_5_6_stage1_reconstruction_evidence_v1.json
```

Do not edit the report after generation. Preserve the verifier-produced JSON
bytes unchanged for the subsequent replay comparator and closure linkage.

## Required success state

The generated canonical report must show all of the following:

- `audit_id = stage9.5-6-stage1-reconstruction-v1`;
- `contract_id = stage9.5-6-stage1-reconstruction-evidence-v1`;
- `contract_canonical_sha256` equal to the canonical SHA-256 of the exact
  frozen Stage-1 reconstruction contract used for execution;
- `verifier_id = stage9.5-6-stage1-reconstruction-verifier-v1`;
- `verifier_source_sha256` equal to the exact LF-canonical
  `tools/stage9_5/stage1_reconstruction_evidence.py` source bytes in the
  checkout whose `repository_head` is recorded by the report;
- `status = pass`;
- `pass = true`;
- `raw_file_count_verified = 8`;
- `interim_table_count_verified = 8`;
- `preprocessing_manifest_canonical_sha256 =
  d33ea433973d4f685812ec3dfbd22424fdcf715d2052bf557dc9e61e2c847ef0`;
- `semantic_mismatch_count = 0`;
- `failures = []`;
- `blockers = []`;
- a valid embedded `canonical_sha256`.

The verifier independently recomputes the structural preprocessing and compares
all decompressed reconstructed tables exactly. Gzip container byte identity is
not the scientific identity and must not be promoted to one.

## Failure handling

Any environment mismatch, raw-file mismatch, historical-source mismatch,
manifest mismatch, semantic table mismatch, missing file, or verifier exception
remains fail-closed. Preserve the failed report/logs; do not patch the evidence
or relax the contract after observing a failure.

A failed execution does not authorize retraining, regenerated System-A
checkpoints, substitution of the missing Stage-8 archive, or Stage-10 access.

## Current environment observation — 17 October 2026

The eight raw CSVs mounted in the current project working environment were
independently SHA-256 checked on 17 October 2026 and matched all eight frozen
identities above.

That same environment reports **Python 3.13.5**, not the required **3.11.9**.
Therefore it is suitable only for raw-input preflight and is **not** an
authoritative Stage-1 reconstruction execution environment.

This observation is operational context, not closure evidence.

## Relationship to the wider Stage-9.5 diversion

The multi-chat assurance diversion is being preserved in
`STAGE9_5_ASSURANCE_DIVERSION_RETROSPECTIVE_WORKING_NOTES.md`.

When Stage 9.5 closes, the final
`STAGE9_5_ASSURANCE_DIVERSION_RETROSPECTIVE.md` must include this Stage-1
handoff/execution episode, the environment mismatch that prevented execution in
the present container, the eventual authoritative report identity, and the
exact Git/CI lineage that cleared this blocker.
