# Architecture

AxiomBraid separates responsibilities into focused modules:

- `inspector`: profiling, issues, quality scores, reports
- `cleaning`: preview-first actions, audit logs, undo
- `validation`: reusable data contracts
- `comparison`: before/after, schema, and drift screens
- `governance`: fingerprints and leakage checks
- `streaming`: memory-bounded CSV profiling
- `batch`: folder analysis and safe parallel execution
- `cache`: content- and configuration-aware result caching
- `plugins`: read-only extension hooks
- `api`: stable pandas-style functional surface

The main safety boundary is that automated outlier deletion, invalid-range clipping,
constant-column dropping, and identifier removal are not performed silently.
