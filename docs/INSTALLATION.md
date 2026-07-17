# Installation

## Stable PyPI installation

```bash
pip install axiombraid
```

Windows:

```powershell
py -m pip install axiombraid
```

Upgrade:

```powershell
py -m pip install --upgrade axiombraid
```

Optional charts:

```bash
pip install "axiombraid[charts]"
```

Development:

```powershell
git clone https://github.com/Adil307/AxiomBraid.git
cd AxiomBraid
py -m pip install -e ".[dev]"
```

Local wheel:

```powershell
py -m pip install dist/axiombraid-2.0.0-py3-none-any.whl
```

Verify:

```powershell
py -c "import axiombraid as AB; print(AB.__version__, AB.API_STATUS)"
py -m axiombraid --version
```

Expected:

```text
2.0.0 stable
AxiomBraid 2.0.0
```

Python 3.10 through 3.14 are supported.
