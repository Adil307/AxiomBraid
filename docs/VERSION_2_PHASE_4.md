# AxiomBraid Version 2 — Phase 4

## Explainable Multi-Dimensional Data Quality Profile

Phase 4 adds a new, opt-in quality profile that explains *why* a dataset score is high or low.

The existing `data_quality` score is preserved for backward compatibility.

## Quick usage

```python
import axiombraid as AB

profile = AB.quality_profile("data.csv")
print(profile["score"])
print(profile["dimensions"])
```

Or include it in a normal inspection:

```python
result = AB.inspect(
    "data.csv",
    include_quality_profile=True,
)

print(result["quality_profile"])
```

Human-readable console report:

```python
AB.report(
    "data.csv",
    include_quality_profile=True,
)
```

HTML report:

```python
AB.export_html(
    "data.csv",
    "report.html",
    include_quality_profile=True,
)
```

CLI:

```powershell
py -m axiombraid inspect data.csv --quality-profile
```

## Dimensions

### Completeness
Measures missing cells.

### Uniqueness
Measures exact duplicate rows.

### Validity
Measures violations detected by supported conservative numeric-range rules.

A score of 100 does not prove universal domain validity.

### Consistency
Measures supported text-representation inconsistencies and lightly weights strongly date-like text stored as generic text.

### Integrity
Currently measures observable structural usefulness through constant-column detection.

It does not claim relational or referential integrity without explicit external keys or contracts.

## Default weights

```text
Completeness  30%
Uniqueness    20%
Validity      20%
Consistency   20%
Integrity     10%
```

Weights can be customized:

```python
profile = AB.quality_profile(
    df,
    quality_config={
        "weights": {
            "completeness": 4,
            "uniqueness": 1,
            "validity": 1,
            "consistency": 1,
            "integrity": 1,
        }
    },
)
```

AxiomBraid normalizes the supplied non-negative weights so they sum to 1.0.

## Important scientific limitation

The Version 2 quality profile is a transparent heuristic summary of checks that AxiomBraid can observe. It is not a universal scientific standard and does not prove semantic or domain correctness.
