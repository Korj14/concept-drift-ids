# Stage 9.5-5 v1.4 Escape-Repair Correction

**Status:** ASSURANCE-HARNESS CORRECTION AFTER FAILED v1.3 RUN  
**Failed head:** `536b0f9e59bc3f3f6f84074724935c63a3bd5a3e`  
**Workflow:** `38557446376`

v1.3 correctly added a compile-scope regression test, and that test exposed that the intended syntax repair had not actually removed the literal backslash+n escape in two assurance files.

The exact malformed lines were:

- `tools/stage9_5/parameter_scan.py`: `from collections.abc import Iterable\nfrom typing import Any`;
- `tests/stage9_5/test_targeted_mutations.py`: `from collections.abc import Callable\nfrom typing import Any`.

The previous repair targeted the wrong escaped representation. v1.4 replaces the actual literal backslash+n characters with a real newline, retains the compile-scope guard, and reruns all exact-head assurance jobs.

No scientific source module, accepted Stage-8/9 evidence, statistical definition, or historical runtime lock is modified.
