"""Fail fast when stable release metadata is inconsistent."""
from __future__ import annotations
from pathlib import Path
import os
import subprocess
import sys
try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import axiombraid as AB
EXPECTED = "2.0.1"

def main() -> int:
    errors = []
    metadata = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    if AB.__version__ != EXPECTED:
        errors.append(f"Runtime version is {AB.__version__}, expected {EXPECTED}.")
    if metadata["project"]["version"] != EXPECTED:
        errors.append("pyproject.toml version mismatch.")
    if AB.API_STATUS != "stable":
        errors.append("API status is not stable.")
    if not AB.self_check()["ok"]:
        errors.append("AB.self_check() failed.")
    if not AB.compatibility_check()["ok"]:
        errors.append("AB.compatibility_check() failed.")
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(ROOT / "src")
    cli = subprocess.run([sys.executable, "-m", "axiombraid", "--version"], capture_output=True, text=True, check=False, env=environment)
    if cli.returncode != 0 or cli.stdout.strip() != f"AxiomBraid {EXPECTED}":
        errors.append("CLI version mismatch.")
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("AxiomBraid 2.0.1 release checks passed.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
