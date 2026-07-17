# AxiomBraid 2.0

AxiomBraid is an explainable, safety-first toolkit for dataset inspection, validation, conservative cleaning, reporting, comparison, drift screening, controlled corruption, and evaluation.

```python
import axiombraid as AB
result = AB.inspect("students.csv", include_confidence=True, include_quality_profile=True)
AB.report("students.csv", include_confidence=True, include_quality_profile=True)
```

## Principles

- Preview before mutation
- Safe functional defaults
- Explainable findings
- Reproducible workflows
- Version 1-compatible workflows in Version 2

See [Version 2 Release Notes](RELEASE_NOTES_2_0.md) and [Migration from 1.x](MIGRATION_1_TO_2.md).
