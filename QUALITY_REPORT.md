# AxiomBraid 2.0.0 Quality Report

Generated: 2026-07-16

## Verification summary

- Automated tests: **213 passed**
- Measured statement/branch coverage: **87%** in the verification environment
- Python source compilation: passed
- Critical Ruff checks: passed
- Release metadata checker: passed
- Wheel build: passed
- Source distribution build: passed
- Twine metadata and README checks: passed
- Fresh virtual-environment installation with dependencies: passed
- `AB.self_check()`: passed
- `AB.compatibility_check()`: passed
- `python -m axiombraid --version`: passed
- PEP 561 `py.typed` marker: included

## Verification environment

- Python: 3.13.5
- pandas: 2.2.3
- Platform: Linux verification environment

## Distribution artifacts

- `axiombraid-2.0.0-py3-none-any.whl`
- `axiombraid-2.0.0.tar.gz`

## Interpretation boundaries

- Confidence scores express evidence strength and are not calibrated probabilities.
- Evaluation metrics operate at issue/column granularity.
- Runtime and memory results depend on hardware, Python, pandas, dataset shape, and storage.
- Safety-first cleaning intentionally leaves risky changes for review.
