# Public API Reference — Version 2.0

## Core

```python
frame = AB.read_csv("data.csv")
inspection = AB.inspect(frame)
AB.report(frame)
cleaned = AB.clean(frame, risk="low")
```

## Explainability

```python
result = AB.inspect(frame, include_confidence=True, include_quality_profile=True)
```

## Evaluation

```python
corrupted, truth = AB.inject_issues(frame, missing_rate=0.05, duplicate_rate=0.05, random_state=42)
results = AB.run_evaluation(frame, corruption_config={"missing_rate": 0.05, "duplicate_rate": 0.05, "random_state": 42})
```

## Benchmarks

```python
benchmark = AB.benchmark_inspection(frame, repeats=3)
scaling = AB.benchmark_scaling(frame, sizes=[100, 1000, 5000], repeats=2)
```
