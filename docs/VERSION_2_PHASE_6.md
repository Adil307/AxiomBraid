# AxiomBraid Version 2 — Phase 6

## Evaluation, Tuning, Performance, and Compatibility

Phase 6 turns the Phase 5 corruption engine into a complete product-validation workflow.

## One-command evaluation

```python
import axiombraid as AB

result = AB.evaluation_report(
    clean_df,
    corruption_config={
        "missing_rate": 0.05,
        "duplicate_rate": 0.05,
        "invalid_range_rate": 0.05,
        "outlier_rate": 0.02,
        "constant_columns": 1,
        "random_state": 42,
    },
)
```

The result includes:

- corrupted DataFrame
- exact ground truth
- clean baseline inspection
- corrupted inspection
- overall detection metrics
- per-detector metrics
- confidence diagnostics
- quality-score response

## Detection metrics

```python
metrics = result["detection_evaluation"]["overall"]

print(metrics["precision"])
print(metrics["recall"])
print(metrics["f1"])
```

Metrics are calculated at issue/column granularity.
Injected issue types already present in the clean baseline are listed as
`preexisting_expected_pairs` and excluded from scoring.

## Direct evaluation

```python
corrupted_df, truth = AB.inject_issues(clean_df, missing_rate=0.05)

baseline = AB.inspect(clean_df, include_confidence=True)
candidate = AB.inspect(corrupted_df, include_confidence=True)

metrics = AB.evaluate_detection(
    candidate,
    truth,
    baseline_inspection=baseline,
)
```

## Quality-score response

```python
response = AB.evaluate_quality_response(clean_df, corrupted_df)

print(response["clean_score"])
print(response["corrupted_score"])
print(response["dimension_deltas"])
```

## Runtime and memory benchmark

```python
benchmark = AB.benchmark_inspection(
    clean_df,
    repeats=3,
)

print(AB.format_benchmark_console(benchmark))
```

## Scaling benchmark

```python
scaling = AB.benchmark_scaling(
    clean_df,
    sizes=[100, 1000, 5000],
    repeats=2,
)
```

Peak memory uses Python `tracemalloc`; native-library allocations may not all be included.

## Empirical confidence-threshold suggestion

```python
suggestion = AB.suggest_confidence_thresholds(
    result["detection_evaluation"],
    minimum_true_positives=3,
)
```

This is a transparent tuning aid, not probability calibration. Validate any suggestion on independent datasets before adopting it.

## Compatibility check

```python
print(AB.compatibility_check())
```

The compatibility check verifies the stable Version 1 API and the new Version 2 APIs.

## CLI

```powershell
py -m axiombraid evaluate data.csv --output reports\evaluation
py -m axiombraid benchmark data.csv --repeats 3 --output reports\benchmark.json
py -m axiombraid benchmark data.csv --sizes 100,1000,5000 --repeats 2
```
