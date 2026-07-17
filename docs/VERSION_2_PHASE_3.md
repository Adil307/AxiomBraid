# AxiomBraid Version 2 — Phase 3

**Development version:** `2.0.0a3`

Phase 3 makes the confidence system understandable to normal users while preserving the machine-readable structures added in Phases 1 and 2.

## Main improvements

- Human-friendly terminal confidence reports.
- `AB.report(..., include_confidence=True)`.
- Summary-only or full confidence detail levels.
- User-friendly issue names instead of raw detector codes.
- Simple evidence explanations.
- Confidence-aware recommended actions.
- Confidence sections in HTML reports.
- Confidence metadata in JSON exports.
- Collapsible technical details in HTML.
- Roman Urdu confidence explanations.
- CLI `--confidence` support for console, JSON, and HTML inspection reports.

## Recommended user workflow

```python
import axiombraid as AB

# Load data
df = AB.read_csv("Messy_Employee_dataset.csv")

# Human-readable terminal report with confidence
AB.report(
    df,
    include_confidence=True,
)
```

The terminal now shows readable sections such as:

```text
CONFIDENCE OVERVIEW
- Issues assessed: 6
- High confidence: 4
- Medium confidence: 2
- Low confidence: 0
- Average evidence strength: 90%

CONFIDENCE DETAILS
1. Potential Outliers
   Severity: HIGH
   Confidence: 82% (MEDIUM)
   Column(s): Age
   Evidence: 1 potential outlier was detected in 'Age'...
   Recommended action: Review the flagged values before changing or removing them...
```

The terminal output intentionally does not print nested `per_column` dictionaries or internal detector method names.

## Summary-only console mode

```python
AB.report(
    df,
    include_confidence=True,
    confidence_details="summary",
)
```

Available values:

```text
summary
full
```

## Confidence-only readable report

The Phase 2 compact dictionary behavior remains unchanged:

```python
inspection = AB.inspect(df)
compact = AB.confidence_report(inspection)
```

To print a readable confidence-only report:

```python
AB.confidence_report(
    inspection,
    display=True,
)
```

## HTML report with confidence

```python
AB.export_html(
    df,
    "employee_report.html",
    include_confidence=True,
    theme="dark",
)
```

The HTML report contains:

- Confidence overview cards.
- High/medium/low confidence counts.
- Average evidence strength.
- One readable card for each issue.
- Severity and affected columns.
- Simple evidence.
- Recommended action.
- Collapsible technical details.

## JSON report with confidence

```python
guide = AB.Guide(df)

guide.export_json(
    "employee_report.json",
    include_confidence=True,
)
```

The JSON contains machine-readable fields including:

```text
confidence_summary
confidence_recommendations
issues[*].confidence
```

Default JSON export remains backward compatible and does not include confidence unless requested.

## Roman Urdu confidence report

```python
AB.report(
    df,
    language="roman_urdu",
    include_confidence=True,
)
```

## Command line

Readable terminal report:

```powershell
py -m axiombraid inspect data.csv --confidence
```

Summary-only confidence:

```powershell
py -m axiombraid inspect data.csv --confidence --confidence-details summary
```

Console, JSON, and HTML together:

```powershell
py -m axiombraid inspect data.csv `
  --confidence `
  --format console `
  --format json `
  --format html `
  --output reports\data
```

## Interpretation rule

A confidence score represents **evidence strength**, not a calibrated probability.

For example:

```text
Confidence: 82%
```

means the detector has an evidence-strength score of `0.82`. It does **not** mean there is an 82% statistical probability that the finding is correct.
