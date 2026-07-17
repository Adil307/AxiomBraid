# Changelog

## 2.0.0 — Stable Version 2 release — 2026-07-16

### Added

- Stable evidence-aware confidence and human-readable confidence reports.
- Explainable five-dimensional data-quality profile.
- Controlled synthetic corruption with exact ground truth.
- Detection evaluation with precision, recall, F1, baseline subtraction, and per-detector diagnostics.
- Quality-response analysis, runtime benchmarks, scaling benchmarks, and empirical threshold suggestions.
- Final migration, API stability, release, and publication documentation.

### Hardened

- Centralized runtime release metadata.
- Expanded `AB.self_check()` and public API compatibility verification.
- Isolated final cache entries from alpha cache entries.
- Added stable metadata, project URLs, final release tests, and production classifiers.

### Compatibility

- Supported Version 1 workflows remain available.
- Confidence and quality-profile output remain opt-in.
- Confidence is evidence strength, not probability.
- Evaluation metrics operate at issue/column granularity.

## 2.0.0a6 — Version 2 Phase 6 — 2026-07-16

### Added

- Detection evaluation at issue/column granularity.
- Precision, recall, F1, false-positive, and false-negative diagnostics.
- Baseline subtraction for pre-existing source-data findings.
- Per-detector metrics and confidence evidence diagnostics.
- Explainable quality-score response comparison.
- Runtime and Python-tracked memory benchmarks.
- Dataset-size scaling benchmarks.
- Empirical confidence-threshold suggestions with explicit non-probability semantics.
- Version 1 and Version 2 API compatibility checks.
- Human-readable evaluation and benchmark reports.
- CLI `evaluate` and `benchmark` commands.

## 2.0.0a5 — Version 2 Phase 5 — 2026-07-16

### Added

- Non-destructive synthetic data-quality corruption engine.
- Reproducible missing-value, duplicate, text, range, outlier, date, constant-column, and identifier injection.
- Exact machine-readable ground truth with rows, columns, cells, original values, and injected values.
- Column restrictions and deterministic random-state behavior.
- Explicit multi-label ground truth for invalid-range values that also produce outliers.

## 2.0.0a4 — Version 2 Phase 4

### Added

- Explainable five-dimension data-quality profile: Completeness, Uniqueness, Validity, Consistency, and Integrity.
- Configurable dimension weights with transparent normalization.
- `AB.quality_profile(...)` public API.
- Optional quality-profile integration in inspection, console reports, JSON exports, HTML reports, and CLI.
- Human-readable improvement priorities and dimension-specific recommendations.
- Legacy-score comparison while preserving the existing Version 1 `data_quality` score.

### Compatibility

- Existing Version 1 and earlier Version 2 APIs remain available.
- The new profile is opt-in and does not replace the legacy score by default.

## 2.0.0a3 — Version 2 Phase 3 — 2026-07-15

### Added

- Human-friendly confidence reporting for console users.
- Confidence-aware recommendations and readable issue names.
- Confidence cards and collapsible technical details in HTML reports.
- Confidence-enabled JSON export and CLI flags.
- Roman Urdu confidence presentation.

## 2.0.0a2 — Phase 2 development alpha — 2026-07-15

- Added detector-specific confidence evidence.
- Added per-column confidence for column-based findings.
- Added configurable confidence-level thresholds and detector base scores.
- Added confidence factors for transparent auditing.
- Added aggregate confidence statistics and detector counts.
- Added `AB.confidence_report()` for a compact confidence-only view.
- Added confidence configuration validation and safe deep-merge behavior.
- Preserved opt-in confidence and the existing Version 1 feature set.
- Expanded the full automated test suite to 164 passing tests.

## 2.0.0a1 — Phase 1 development alpha — 2026-07-14

- Preserved the Version 1 inspection, reporting, cleaning, validation, comparison, drift, streaming, caching, batch, and plugin APIs.
- Added optional `include_confidence=True` support to `AB.inspect()`.
- Added `AB.inspect_with_confidence()`.
- Added `AB.issue_confidence()` for one issue.
- Added `AB.add_confidence()` for existing inspection results.
- Added deterministic evidence-strength metadata and explicit `is_probability=False`.
- Added Phase 1 tests, documentation, and an example.

## 1.0.1 — 2026-07-14

- Corrected public PyPI installation instructions.
- Separated stable installation from development installation.
- Updated version consistency across CLI, HTML reports, cache metadata, citation, and tests.

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
