# Changelog

## 1.0.0 — 2026-07-13

Stable release:

- Froze the supported top-level `import axiombraid as AB` API.
- Marked the public API as stable and introduced public API version 1.
- Added `AB.about()` and `AB.self_check()` diagnostics.
- Added `python -m axiombraid` support and a PEP 561 `py.typed` marker.
- Removed the deprecated `dataguidepy` namespace and `dataguide` CLI from the release.
- Added modern packaging metadata and Python 3.10–3.14 classifiers.
- Added CI, CodeQL, documentation deployment, and PyPI Trusted Publishing workflows.
- Added documentation-site source, contribution/security/governance policies,
  citation metadata, release checklist, and research-readiness guidance.
- Added release benchmark tooling and a generated local baseline.
- Bumped cache format to avoid stale release-candidate results.


## 0.9.0

- Renamed DataGuidePy to **AxiomBraid**.
- Added official `import axiombraid as AB` documentation style.
- Added stable functional API and `Guide` alias.
- Added deprecation-compatible `dataguidepy` namespace and `dataguide` CLI.
- Added memory-bounded chunked CSV profiling with reservoir sampling.
- Added safe parallel batch workers and CLI progress.
- Added fingerprint-based inspection cache.
- Added migration, API, privacy/security, and benchmark documentation.
