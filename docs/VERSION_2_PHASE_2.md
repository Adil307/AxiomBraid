# AxiomBraid 2.0 Phase 2 — Evidence-Aware Confidence

**Development version:** `2.0.0a2`  
**Status:** Alpha development build  
**Public release status:** Not intended as the final 2.0.0 release

Phase 2 extends the optional confidence layer introduced in Phase 1. The core Version 1 workflow remains available, and confidence remains opt-in.

## What Phase 2 adds

- Detector-specific evidence instead of one generic explanation.
- Per-column confidence for column-based findings.
- Configurable confidence-level thresholds.
- Configurable detector base scores.
- Rich confidence factors for auditability.
- Aggregate confidence statistics.
- A compact `AB.confidence_report()` helper.

## Backward-compatible default

```python
result = AB.inspect(df)
```

The default inspection result is unchanged by the confidence layer.

## Enable confidence

```python
result = AB.inspect(
    df,
    include_confidence=True,
)
```

Or:

```python
result = AB.inspect_with_confidence(df)
```

## Inspect evidence for one issue

```python
for issue in result["issues"]:
    confidence = issue["confidence"]

    print(issue["code"])
    print(confidence["score"])
    print(confidence["level"])
    print(confidence["method"])
    print(confidence["evidence"])
    print(confidence["factors"])
    print(confidence["per_column"])
```

## Per-column example

For a potential-outlier finding, a column-level result can include:

```text
score
level
method
IQR evidence
outlier count
outlier percentage
lower bound
upper bound
IQR multiplier
```

For date-like text, evidence can include:

```text
parsed count
non-missing count
parse percentage
suggested dtype
```

For text inconsistencies, evidence can include:

```text
normalized group count
variant count
```

## Custom confidence thresholds

```python
custom_confidence = {
    "level_thresholds": {
        "high": 0.95,
        "medium": 0.85,
    }
}

result = AB.inspect(
    df,
    include_confidence=True,
    confidence_config=custom_confidence,
)
```

The score does not have to change when thresholds change; only the label can change.

## Customize a detector base score

```python
custom_confidence = {
    "detectors": {
        "potential_outliers": {
            "base_score": 0.72,
        }
    }
}
```

AxiomBraid merges partial confidence configuration with safe defaults.

## Compact confidence report

```python
inspection = AB.inspect(df)
report = AB.confidence_report(inspection)

print(report["summary"])
print(report["issues"])
```

## Important interpretation rule

Confidence is explicitly returned with:

```text
is_probability: false
```

The score represents deterministic evidence strength. It is not a calibrated probability that a finding is correct.

## Research relevance

Phase 2 makes confidence output more suitable for future evaluation because the system now exposes:

- the detector used,
- the evidence supporting the score,
- the factors used,
- per-column assessments,
- configurable thresholds,
- aggregate confidence statistics.

Calibration against controlled ground truth is a later phase and should not be claimed yet.
