# AxiomBraid 2.0 Phase 3 — Setup and Explanation

## Development version

```text
2.0.0a3
```

## What Phase 3 solves

Phase 2 produced technically strong confidence information, but printing the raw dictionary exposed nested structures such as `per_column`, detector method names, and internal factors. Those structures are useful for software and research, but they are difficult for normal users to read.

Phase 3 keeps the machine-readable data and adds a separate human-friendly presentation layer.

## New user-facing command

```python
AB.report(
    df,
    include_confidence=True,
)
```

This displays:

- Confidence overview.
- Number of high, medium, and low-confidence findings.
- Average evidence strength.
- Friendly issue names.
- Confidence percentages.
- Simple evidence.
- Recommended actions.

It does not dump raw nested dictionaries.

## HTML

```python
AB.export_html(
    df,
    "report.html",
    include_confidence=True,
    theme="dark",
)
```

The report contains visual confidence cards and collapsible technical details.

## JSON

```python
guide.export_json(
    "report.json",
    include_confidence=True,
)
```

JSON remains designed for developers and automation.

## CLI

```powershell
py -m axiombraid inspect data.csv --confidence
```

Export all main formats:

```powershell
py -m axiombraid inspect data.csv --confidence --format console --format json --format html --output reports\data
```

## Backward compatibility

These old calls still work without adding confidence:

```python
AB.inspect(df)
AB.report(df)
AB.export_html(df, "report.html")
guide.export_json("report.json")
```

Confidence remains opt-in.

## How to test

```powershell
py -m pip install -e ".[dev]"
py -m pytest
```

Run the Phase 3 example:

```powershell
py examples\v2_phase3_human_friendly_confidence.py
```

Check the version:

```powershell
py -c "import axiombraid as AB; print(AB.__version__)"
```

Expected:

```text
2.0.0a3
```
