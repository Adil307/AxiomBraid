# AxiomBraid 2.0.0 — Phase 7 Setup and Release Guide

Phase 7 synchronizes stable metadata, protects compatibility, completes documentation, and verifies final distributions.

## Local test

Extract to a separate folder, then run:

```powershell
py -m venv .venv
.venv/Scripts/Activate.ps1
py -m pip install -e ".[dev]"
py -m pytest
py scripts/check_release.py
```

Expected metadata:

```text
2.0.0 stable 2
AxiomBraid 2.0.0
```

## Build

```powershell
Remove-Item -Recurse -Force dist, build -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force src/axiombraid.egg-info -ErrorAction SilentlyContinue
py -m build
py -m twine check dist/*
```

## Git and release

After review, commit to the Version 2 branch, merge to `main`, create tag `v2.0.0`, and publish GitHub Release `AxiomBraid 2.0.0`. The existing Trusted Publisher workflow can publish it to PyPI.

## Public verification

```powershell
py -m venv axiombraid-2-public-test
axiombraid-2-public-test/Scripts/python.exe -m pip install axiombraid==2.0.0
axiombraid-2-public-test/Scripts/python.exe -c "import axiombraid as AB; print(AB.__version__, AB.self_check()['ok'])"
```
