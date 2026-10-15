# Stage 9.5-1 v1.2.1 Static Cleanup

**Parent assurance head:** `49ea4376884f375fc8d05b8b911eccf264046fd2`  
**Scope:** assurance-test cleanup only  
**Scientific source/evidence changed:** no

The first Stage-9.5-1 v1.2 run validated the corrected heavy-artifact inventory and produced the intended semantic state:

- identity failures: 0;
- external-artifact blockers: 2.

The same run's static artifact increased Ruff findings from 154 to 156. Artifact inspection identified exactly two new findings:

- `F841` at the two legacy test functions that retained an unused local `root` assignment after their manifest reads were changed to the shared `IDENTITY_PATH`.

v1.2.1 removes only those two unused assignments.

No verifier logic, external-artifact classification, accepted Stage-8/9 object, historical runtime lock, or blocker disposition is changed.
