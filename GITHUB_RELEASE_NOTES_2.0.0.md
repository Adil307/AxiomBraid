# AxiomBraid 2.0.0

AxiomBraid 2.0 is the stable release of the Version 2 safety-first data-quality framework.

## Highlights

- Evidence-aware confidence with human-readable explanations
- Five-dimensional quality profile: Completeness, Uniqueness, Validity, Consistency, and Integrity
- Controlled synthetic corruption with exact ground truth
- Precision, recall, F1, per-detector metrics, and baseline subtraction
- Quality-score response analysis
- Runtime, Python-tracked memory, and scaling benchmarks
- Version 1-compatible core workflow
- Expanded diagnostics, API stability policy, and migration documentation
- **213 automated tests passed**

## Installation

```bash
pip install axiombraid
```

Windows:

```powershell
py -m pip install axiombraid
```

## Basic usage

```python
import axiombraid as AB

result = AB.inspect(
    "data.csv",
    include_confidence=True,
    include_quality_profile=True,
)

AB.report(
    "data.csv",
    include_confidence=True,
    include_quality_profile=True,
)
```

## Verification

```python
print(AB.__version__)
print(AB.self_check())
print(AB.compatibility_check())
```

Confidence values represent evidence strength, not calibrated probability. Evaluation metrics operate at issue/column granularity.
