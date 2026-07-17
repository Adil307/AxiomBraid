# AxiomBraid 2.0.0a5 — Phase 5 Setup and Explanation

Phase 5 introduced the controlled synthetic corruption engine and exact ground-truth recording.

## Run the example

```powershell
py examples\v2_phase5_synthetic_corruption.py
```

## Main API

```python
corrupted_df, ground_truth = AB.inject_issues(clean_df, missing_rate=0.05)
```

The engine is for repeatable product testing. It never modifies the supplied DataFrame.
