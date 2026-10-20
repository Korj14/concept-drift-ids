# Stage 9.5-5 Static Software Assurance — Implementation Freeze

**Status:** PROSPECTIVELY FROZEN BEFORE STATIC EXECUTION  
**Historical runtime lock:** immutable  
**Stage 9.5-1:** remains independently blocked  
**Stage 10:** prohibited

## Toolchain

Developer-only static tooling is pinned separately from the historical scientific runtime:

- Ruff `0.17.0`;
- mypy `2.4.0`.

The CI job installs the historical `requirements-lock.txt` first, verifies its frozen SHA-256, then installs these developer-only tools without writing to the lock file.

## Scope

Scientific scope is the exact 38-file Python union already bound by the accepted Stage-8 and Stage-9 scientific-source manifests.

Assurance scope includes every current Python module under `tools/stage9_5/` and every current Stage-9.5 assurance test.

Ruff runs over the entire frozen scientific + assurance surface with no auto-fix.

mypy runs over executable scientific and assurance tool modules. Test modules are excluded from mypy's first discovery pass but remain Ruff-checked; this avoids conflating pytest fixture typing noise with scientific implementation typing while preserving static coverage of executable assurance code.

## First-run rule

The first run is discovery, not style cleanup.

All findings are preserved and triaged:

- behavior-changing/scientific-risk -> correction/version or Class-A/B disposition;
- assurance-harness risk -> correction/version before 9.5-5 closure;
- cosmetic/legacy -> documented without rewriting frozen evidence-generating code solely for style;
- third-party typing limitation -> exact documented incompatibility, with equivalent static evidence only if necessary.

No auto-fix, formatter, import sorter, or source rewrite is permitted in the discovery job.

## Closure

Stage 9.5-5 closes only after every Ruff/mypy finding from the frozen scope has an explicit disposition and no unresolved scientific-risk or assurance-harness-risk finding remains.

Passing 9.5-5 cannot resolve the open Stage 9.5-1 checkpoint provenance blocker.
