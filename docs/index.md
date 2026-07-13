# AxiomBraid 1.0

AxiomBraid is an explainable, safety-first Python toolkit for dataset inspection,
validation, cleaning, reporting, comparison, and drift screening.

```python
import axiombraid as AB

result = AB.inspect("students.csv")
AB.report("students.csv")
```

## Design principles

- **Preview before mutation**: cleaning plans are visible before actions run.
- **Safe defaults**: input DataFrames are not mutated by the functional API.
- **Explainable findings**: scores and issues include transparent reasons.
- **Reproducible workflows**: fingerprints, audit logs, contracts, and cache keys.
- **Beginner-accessible**: concise functions, CLI commands, and Roman Urdu reports.
