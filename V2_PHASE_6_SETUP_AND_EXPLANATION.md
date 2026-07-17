# AxiomBraid 2.0.0a6 — Phase 6 Setup and Explanation

## What Phase 6 adds

- Detection precision, recall, F1, false-positive diagnostics
- Per-detector evaluation
- Baseline subtraction for pre-existing issues
- Confidence evidence diagnostics
- Empirical threshold suggestions
- Quality-score response checks
- Runtime and Python-tracked memory benchmarking
- Scaling benchmarks
- Version 1 and Version 2 API compatibility checks
- Human-readable evaluation and benchmark reports
- CLI `evaluate` and `benchmark` commands

## Install development dependencies

```powershell
py -m pip install -e ".[dev]"
```

## Run all tests

```powershell
py -m pytest
```

## Run the Phase 6 example

```powershell
py examples\v2_phase6_evaluation_benchmark.py
```

## CLI evaluation

```powershell
py -m axiombraid evaluate examples\students.csv --output reports\students_evaluation
```

The command saves:

```text
reports/students_evaluation.json
reports/students_evaluation_corrupted.csv
```

## CLI benchmark

```powershell
py -m axiombraid benchmark examples\students.csv --repeats 3 --output reports\benchmark.json
```

## Interpretation

Precision answers: Of the new findings, how many matched injected ground truth?

Recall answers: Of the scorable injected findings, how many were detected?

F1 balances precision and recall.

Metrics operate at issue/column granularity. They are not cell-level accuracy claims.
