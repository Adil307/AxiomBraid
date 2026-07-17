# AxiomBraid Version 2 Phase 1 — How to Use This ZIP

This ZIP is a complete development copy containing the existing Version 1 codebase plus the first Version 2 feature.

## Important

- Development version: `2.0.0a1`
- Do not publish this alpha to PyPI as the final Version 2 release.
- Keep the current stable release safe.
- Work on a separate Git branch such as `v2-development`.

## Recommended Setup

1. Extract this ZIP to a new folder, for example:

```text
C:\Users\adilv\Desktop\AxiomBraid-V2
```

2. Open PowerShell in that folder.

3. Create a virtual environment:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

4. Install in development mode:

```powershell
py -m pip install --upgrade pip
py -m pip install -e ".[dev]"
```

5. Run tests:

```powershell
py -m pytest
```

6. Run the new example:

```powershell
cd examples
py v2_phase1_confidence.py
```

## New Feature

```python
import axiombraid as AB

df = AB.read_csv("data.csv")
result = AB.inspect(df, include_confidence=True)

for issue in result["issues"]:
    print(issue["code"], issue["confidence"])
```

## What Was Not Changed

Version 1 features remain available, including:

- Inspection and reports
- Safe cleaning
- Validation
- Fingerprints
- Comparison and drift
- Streaming and caching
- Batch analysis
- Plugins
- HTML/JSON/chart reporting
- Roman Urdu reports

## Next Phase

Phase 2 should improve the confidence model with detector-specific evidence and configurable thresholds after Phase 1 is reviewed and tested on real datasets.
