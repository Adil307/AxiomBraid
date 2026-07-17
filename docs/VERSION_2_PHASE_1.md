# AxiomBraid 2.0 — Phase 1 Development Alpha

**Development version:** `2.0.0a1`  
**Status:** Alpha — local/development testing only  
**Phase 1 feature:** Explainable issue-confidence layer

## What Phase 1 Adds

Version 1 features remain available. Phase 1 adds optional confidence metadata to detected issues.

The confidence value is **not a statistical probability**. It is a transparent, deterministic evidence-strength score.

## Backward-Compatible Usage

Existing code still works:

```python
import axiombraid as AB

df = AB.read_csv("data.csv")
result = AB.inspect(df)
AB.report(df)
cleaned = AB.clean(df, risk="low")
```

By default, `AB.inspect(df)` keeps the previous result shape and does not add confidence fields.

## New Phase 1 Usage

```python
result = AB.inspect(df, include_confidence=True)

for issue in result["issues"]:
    print(issue["code"])
    print(issue["confidence"]["score"])
    print(issue["confidence"]["level"])
    print(issue["confidence"]["evidence"])
```

Convenience function:

```python
result = AB.inspect_with_confidence(df)
```

Add confidence to an already-created inspection result:

```python
result = AB.inspect(df)
enhanced = AB.add_confidence(result)
```

Score one issue directly:

```python
confidence = AB.issue_confidence(result["issues"][0])
print(confidence)
```

## Confidence Meaning

- `score`: Evidence-strength heuristic from 0.0 to 1.0.
- `level`: `high`, `medium`, or `low`.
- `method`: `deterministic_rule` or `explainable_heuristic`.
- `evidence`: Human-readable reason for the score.
- `is_probability`: Always `False` in Phase 1.

## Why This Is Useful

A user can now distinguish between:

- Exact findings such as duplicates and missing values.
- Heuristic findings such as possible outliers and identifier-like columns.

This keeps AxiomBraid explainable instead of pretending that every detection has equal certainty.

## Safety

Phase 1 does not change the Version 1 cleaning behavior. Confidence metadata is advisory and does not automatically delete, replace, or modify data.
