# AxiomBraid 2.0

**Explainable, safety-first data quality for Python.**

AxiomBraid inspects, validates, cleans, compares, and monitors tabular datasets while keeping automated changes conservative, visible, and reproducible.

## Installation

```bash
pip install axiombraid
```

Windows:

```powershell
py -m pip install axiombraid
```

Optional charts:

```bash
pip install "axiombraid[charts]"
```

## Quick start

```python
import axiombraid as AB

result = AB.inspect("students.csv")
AB.report("students.csv")
cleaned = AB.clean("students.csv", risk="low")
AB.export_html("students.csv", "reports/students.html", theme="dark")
```

## Version 2 explainability

```python
result = AB.inspect(
    "students.csv",
    include_confidence=True,
    include_quality_profile=True,
)

AB.report(
    "students.csv",
    include_confidence=True,
    include_quality_profile=True,
)
```

The quality profile explains Completeness, Uniqueness, Validity, Consistency, and Integrity. Confidence represents evidence strength, not calibrated probability.

## Controlled evaluation

```python
clean = AB.read_csv("clean.csv")
corrupted, truth = AB.inject_issues(clean, missing_rate=0.05, duplicate_rate=0.05, invalid_range_rate=0.05, random_state=42)
results = AB.run_evaluation(clean, corruption_config={"missing_rate": 0.05, "duplicate_rate": 0.05, "invalid_range_rate": 0.05, "random_state": 42})
```

Evaluation metrics operate at issue/column granularity.

## Main capabilities

- Missing values, duplicates, constants, identifiers, outliers, suspicious ranges, text inconsistencies, and date-like text
- Explainable dataset, column, and five-dimensional quality scoring
- Evidence-aware confidence with readable console and HTML reports
- Preview-first, risk-classified, reversible cleaning
- Validation contracts, fingerprints, leakage screening, schema comparison, and drift history
- Controlled synthetic corruption with exact ground truth
- Precision, recall, F1, confidence diagnostics, quality-response evaluation, and benchmarks
- Streaming, caching, plugins, batch processing, CLI, and Roman Urdu reports

## Safety

AxiomBraid does not silently delete outliers, clip invalid values, drop identifiers, or mutate input DataFrames through the functional API.

## Diagnostics

```python
print(AB.about())
print(AB.self_check())
print(AB.compatibility_check())
```

## CLI

```powershell
py -m axiombraid --version
py -m axiombraid inspect data.csv --confidence --quality-profile
py -m axiombraid evaluate clean.csv --output reports/evaluation
py -m axiombraid benchmark data.csv --repeats 3 --output reports/benchmark.json
```

License: MIT  
Repository: https://github.com/Adil307/AxiomBraid

## Source-code documentation with Doxygen

AxiomBraid 2.0.0 includes final Doxygen configuration for modules, classes, functions, docstrings, source browsing, examples, and Graphviz diagrams.

Install the tools on Windows:

```powershell
winget install --id DimitriVanHeesch.Doxygen -e
winget install --id Graphviz.Graphviz -e
```

Generate and open the documentation without PowerShell execution-policy issues:

```powershell
.\generate_doxygen.cmd
```

The generated main page is:

```text
docs/doxygen/html/index.html
```

See [`docs/DOXYGEN.md`](docs/DOXYGEN.md) for setup, troubleshooting, CI artifact generation, and reviewer-sharing instructions.

