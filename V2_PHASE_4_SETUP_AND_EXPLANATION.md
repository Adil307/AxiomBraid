# AxiomBraid V2 Phase 4 — Setup and Explanation

## Version

```text
2.0.0a4
```

## What Phase 4 adds

Phase 4 introduces an explainable multi-dimensional data-quality profile while preserving all previous Version 1 and Version 2 features.

The profile contains:

- Completeness
- Uniqueness
- Validity
- Consistency
- Integrity
- Overall weighted score
- Lowest dimension
- Improvement priorities
- Strengths
- Comparison with the legacy compatibility score

## Why this was added

A single score such as `82/100` does not tell a user *why* the dataset lost quality.

Phase 4 makes the score explainable:

```text
Overall: 82/100
Completeness: 96/100
Uniqueness: 80/100
Validity: 75/100
Consistency: 72/100
Integrity: 100/100
Lowest dimension: Consistency
```

## Recommended user command

```python
import axiombraid as AB

AB.report(
    "data.csv",
    include_quality_profile=True,
)
```

## Machine-readable API

```python
profile = AB.quality_profile("data.csv")
```

## Backward compatibility

This still works exactly as before:

```python
result = AB.inspect("data.csv")
print(result["data_quality"])
```

The new profile is opt-in:

```python
result = AB.inspect(
    "data.csv",
    include_quality_profile=True,
)

print(result["quality_profile"])
```

## Important limitation

The profile only scores evidence AxiomBraid can currently observe. In particular, the current Integrity dimension is not a claim of referential integrity across databases or tables.
