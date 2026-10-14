# Stage 9.5-6 Clean Deterministic Full-Seed Rerun — BLOCKED

**Status:** OPEN / BLOCKED  
**Dependency:** existing Stage 9.5-1 Class-A provenance/reconstructibility blocker  
**Stage 10:** prohibited

The frozen 9.5-6 protocol requires at least one complete accepted Stage-8 seed to be rerun in a clean environment using the exact historical execution/config identity.

That rerun cannot currently be performed without violating the protocol because the five original frozen System-A checkpoint byte files remain unavailable.

The required SHA-256 identities are:

- seed 0: `514c6d552b3cd680ae966bbb568105bd2871bc68d3a47aded070a70ba0615bd1`
- seed 1: `07696c3f580645d9c96ac3e736cfb5eeaa8033f148bf64822e8ee105861cf552`
- seed 2: `7630514cf409256bd2bbe27eca59f881acb238be698b5fdb1ee12bca8e402491`
- seed 3: `cce1ce47db047b9d441bbe6dad9bd53f1ee6ff3ad7d404521cae72a38bccd4b4`
- seed 4: `9b9e56371f3246482998c4efea4829e1e6d5aaf549bb43e1af05e471dfcb9e93`

The exact historical runtime, scenario, preprocessing, R0 identities, and raw-data hashes are already frozen. The eight exact raw CICIDS2017 files have also been byte-verified in the current project context. The immediate stopping condition is the unavailable original neural checkpoint serialization.

Regenerating/retraining System A is not a valid substitute. Likewise, running the historical procedure from the current Stage-9.5 branch would violate the protocol's exact-head protection.

Stage 9.5-6 therefore remains open. It can resume only if the original checkpoint bytes are recovered from an authoritative archive and match all frozen hashes.

This blocker does not establish that accepted Stage-8/9 numerical evidence is wrong; the independent 9.5-2 oracle reproduced that evidence with zero discrepancies.
