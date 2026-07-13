# AxiomBraid

**Explainable, safety-first data quality for Python.**

AxiomBraid inspects, validates, cleans, compares, and monitors tabular datasets while
keeping automated changes conservative and visible.

```python
import axiombraid as AB

result = AB.inspect("students.csv")
AB.report("students.csv")

cleaned = AB.clean("students.csv", risk="low")
AB.export_html("students.csv", "reports/students.html", theme="dark")
```

## Why AxiomBraid?

- Detects missing values, duplicates, constant columns, identifiers, outliers, invalid
  ranges, text inconsistencies, and date-like text.
- Produces transparent dataset and column quality scores.
- Uses preview-first, risk-classified, reversible cleaning.
- Supports contracts, fingerprints, leakage screening, drift history, streaming CSV
  profiling, caching, plugins, parallel batch analysis, CLI usage, and Roman Urdu output.
- Does not silently delete outliers, clip invalid values, drop identifiers, or mutate
  input DataFrames through the functional API.

## Installation

Install the stable release from PyPI:

```bash
pip install axiombraid
```

On Windows:

```powershell
py -m pip install axiombraid
```

Optional chart support:

```bash
pip install "axiombraid[charts]"
```

### Development installation

```bash
git clone https://github.com/Adil307/AxiomBraid.git
cd AxiomBraid
pip install -e ".[dev]"
```

## Stable API

```python
import axiombraid as AB

df = AB.read_csv("data.csv")
inspection = AB.inspect(df)
validation = AB.validate(df, contract)
comparison = AB.compare(old_df, new_df)
drift = AB.detect_drift(old_df, new_df)
```

Advanced use:

```python
guide = AB.Guide("data.csv")
guide.report()
guide.cleaning_plan()
guide.export_json("report.json")
guide.export_html("report.html")
```

## Diagnostics

```python
print(AB.about())
print(AB.self_check())
```

## Command line

```powershell
axiombraid inspect data.csv
axiombraid batch datasets --output reports --workers 4 --format json --format html
axiombraid stream large.csv --chunksize 100000 --sample-rows 50000
python -m axiombraid --version
```

## Stability

Version 1.0 marks the supported public API. AxiomBraid follows semantic versioning:
compatible features and fixes belong in 1.x; incompatible public API changes require 2.0.

The old `dataguidepy` namespace and `dataguide` CLI were deprecated in 0.9 and are not
shipped in 1.0. See `docs/MIGRATION_FROM_DATAGUIDEPY.md`.

## Development

```powershell
py -m pytest
py -m pytest --cov=axiombraid
py benchmarks\benchmark_release.py
```

License: MIT.
