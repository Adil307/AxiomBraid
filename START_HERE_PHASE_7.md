# Start Here — AxiomBraid Version 2 Phase 7

This is the complete stable `2.0.0` release package, ready for local verification before GitHub/PyPI publication.

```powershell
py -m venv .venv
.venv/Scripts/Activate.ps1
py -m pip install -e ".[dev]"
py -m pytest
py scripts/check_release.py
py -m axiombraid --version
```

Build:

```powershell
Remove-Item -Recurse -Force dist, build -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force src/axiombraid.egg-info -ErrorAction SilentlyContinue
py -m build
py -m twine check dist/*
```

Do not publish until the exact files are pushed and GitHub Actions is green.
