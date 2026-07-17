# Start Here — AxiomBraid Version 2 Phase 6

## 1. Extract this ZIP into a new folder

Recommended:

```text
C:\Users\adilv\Desktop\AxiomBraid-V2-Phase6
```

Do not overwrite your stable Version 1 folder.

## 2. Open PowerShell in the extracted folder

```powershell
cd C:\Users\adilv\Desktop\AxiomBraid-V2-Phase6
```

## 3. Create and activate a virtual environment

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

## 4. Install the development project

```powershell
py -m pip install -e ".[dev]"
```

## 5. Run all tests

```powershell
py -m pytest
```

Expected:

```text
203 passed
```

## 6. Check the version

```powershell
py -c "import axiombraid as AB; print(AB.__version__)"
```

Expected:

```text
2.0.0a6
```

## 7. Run Phase 5 and Phase 6 examples

```powershell
py examples\v2_phase5_synthetic_corruption.py
py examples\v2_phase6_evaluation_benchmark.py
```

## 8. Use your own dataset

```python
import axiombraid as AB

result = AB.evaluation_report(
    "your_clean_dataset.csv",
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

## 9. CLI evaluation

```powershell
py -m axiombraid evaluate your_clean_dataset.csv --output reports\evaluation
```

## 10. CLI benchmark

```powershell
py -m axiombraid benchmark your_clean_dataset.csv --repeats 3 --output reports\benchmark.json
```

This is still an alpha development build. Do not publish final `2.0.0` yet.
