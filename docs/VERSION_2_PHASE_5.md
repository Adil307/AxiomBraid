# AxiomBraid Version 2 — Phase 5

## Controlled Synthetic Corruption and Ground Truth

Phase 5 adds a non-destructive corruption engine for controlled product testing.
It is not a research-paper folder and it does not publish private research notes.

## Public API

```python
import axiombraid as AB

corrupted_df, ground_truth = AB.inject_issues(
    clean_df,
    missing_rate=0.05,
    duplicate_rate=0.05,
    text_case_rate=0.05,
    whitespace_rate=0.05,
    invalid_range_rate=0.05,
    outlier_rate=0.02,
    date_format_rate=0.10,
    constant_columns=1,
    identifier_columns=1,
    random_state=42,
)
```

## Supported controlled issues

- Missing values
- Exact duplicate rows
- Text case inconsistencies
- Leading/trailing whitespace
- Invalid conservative numeric ranges
- Numerical outliers
- Mixed date formatting
- Constant columns
- Identifier-like columns

## Ground-truth design

Every injected event records:

- issue code
- affected columns
- affected row indices
- cell locations where applicable
- original values
- injected values
- configuration and random state

AxiomBraid evaluates at issue/column granularity because that is the granularity
of public inspection findings.

## Safety

- The source DataFrame is never mutated.
- A fixed `random_state` makes corruption reproducible.
- The ground truth records only intentionally injected issues.
- Pre-existing source-data problems remain possible and are handled by Phase 6 baseline subtraction.
