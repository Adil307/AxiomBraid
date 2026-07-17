# AxiomBraid Version 2 — Phase 2 Setup and Explanation

## Development build

```text
AxiomBraid 2.0.0a2
```

This ZIP is a complete development copy built on the Phase 1 codebase. It keeps the existing AxiomBraid feature set and extends the optional confidence system.

## Phase 2 goal

Phase 1 answered:

> Can AxiomBraid attach a transparent confidence score to a detected issue?

Phase 2 answers:

> Can AxiomBraid explain the detector-specific evidence behind that score and show confidence per affected column?

## Main implementation

```text
src/axiombraid/confidence.py
```

The confidence layer now supports:

```text
DEFAULT_CONFIDENCE_CONFIG
normalize_confidence_config()
issue_confidence()
add_confidence()
confidence_report()
```

## Main user workflow

```python
import axiombraid as AB

result = AB.inspect(
    "data.csv",
    include_confidence=True,
)

for issue in result["issues"]:
    print(issue["code"])
    print(issue["confidence"]["score"])
    print(issue["confidence"]["evidence"])
    print(issue["confidence"]["per_column"])
```

## Detector-specific evidence

### Missing values

Direct counts and percentages are used.

### Duplicate rows

The finding remains a direct deterministic dataset check.

### Constant columns

Each affected column receives deterministic confidence.

### Text inconsistencies

Evidence includes normalized inconsistency groups and observed variant forms.

### Potential outliers

Evidence includes IQR-derived counts, percentages, lower/upper bounds, and the IQR multiplier.

### Suspicious numeric ranges

Evidence includes the applied conservative rule, invalid count/percentage, and expected bounds.

### Date-like text

Evidence includes parsed count, non-missing count, parse percentage, and suggested dtype.

### Possible identifiers and high-cardinality descriptive columns

The current result exposes detector membership, so confidence remains conservative. A later phase can expose richer raw detector metrics.

## Configurable thresholds

Default labels:

```text
high   >= 0.90
medium >= 0.75
low    <  0.75
```

Customize them:

```python
confidence_config = {
    "level_thresholds": {
        "high": 0.95,
        "medium": 0.85,
    }
}

result = AB.inspect(
    df,
    include_confidence=True,
    confidence_config=confidence_config,
)
```

## Compact report

```python
inspection = AB.inspect(df)
confidence = AB.confidence_report(inspection)

print(confidence["summary"])
```

The summary includes:

```text
issue_count
level_counts
average_score
lowest_score
highest_score
detector_counts
level_thresholds
```

## Safety and scientific honesty

The confidence score is still:

```text
is_probability = False
```

AxiomBraid does not claim calibrated probabilistic confidence. The current score is a transparent, deterministic evidence-strength heuristic.

## Installation for local development

From the extracted project folder:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install --upgrade pip
py -m pip install -e ".[dev]"
```

## Run all tests

```powershell
py -m pytest
```

Expected for this prepared Phase 2 package:

```text
164 passed
```

## Version check

```powershell
py -c "import axiombraid as AB; print(AB.__version__)"
```

Expected:

```text
2.0.0a2
```

## Run the Phase 2 example

```powershell
py examples\v2_phase2_evidence_confidence.py
```

## What was not added yet

Phase 2 does not yet claim:

- statistically calibrated probabilities,
- benchmark-proven confidence accuracy,
- synthetic corruption ground truth,
- precision/recall/F1 evaluation,
- final Version 2 quality-score redesign.

Those belong to later development phases.
