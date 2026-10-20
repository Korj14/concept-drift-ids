# Stage 9.5-9 v1.1 Git-Blob Identity Correction

**Status:** ASSURANCE-HARNESS CORRECTION AFTER FIRST 9.5-9 RUN  
**Failed head:** `0f00bfa1c567d3663a47eca956bbc88b5d15916f`  
**Workflow:** `38662040377`  
**Job:** `116185341201`

The first hostile-review audit tests established that the A–T classification contract and the Stage-10 hard gate were coherent, but the full audit exited before artifact upload.

The repository-side checks independently confirmed that all nine Stage-9.5 package evidence files exist, all 24 named failed-audit JSON artifacts are preserved, and no committed Stage-10 results exist.

The defect was the source-identity implementation: it reconstructed a Git blob SHA-1 from checked-out Markdown bytes. That is platform-sensitive on Windows when checkout line endings differ from repository blob bytes.

v1.1 changes only this identity mechanism. It now queries the immutable repository object directly with:

`git rev-parse HEAD:<repository-relative-path>`

No A–T classification, Class-A criterion, Stage-10 obligation, scientific source, accepted evidence, or historical runtime lock changes.
