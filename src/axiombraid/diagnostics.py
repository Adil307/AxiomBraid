"""Runtime diagnostics for support, bug reports, and reproducible research."""

from __future__ import annotations

import importlib.util
import platform
import sys
from typing import Any

import pandas as pd


def about() -> dict[str, Any]:
    """Return version, platform, and optional-feature information."""
    from . import API_STATUS, BRAND_NAME, PUBLIC_API_VERSION, __version__

    optional = {
        "charts": importlib.util.find_spec("matplotlib") is not None,
        "yaml": importlib.util.find_spec("yaml") is not None,
        "toml_reader": (
            importlib.util.find_spec("tomllib") is not None
            or importlib.util.find_spec("tomli") is not None
        ),
    }
    return {
        "brand": BRAND_NAME,
        "version": __version__,
        "api_status": API_STATUS,
        "public_api_version": PUBLIC_API_VERSION,
        "python": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "pandas": pd.__version__,
        "optional_features": optional,
    }


def self_check() -> dict[str, Any]:
    """Run a small non-destructive smoke test and return structured results."""
    from .api import inspect

    checks: list[dict[str, Any]] = []
    try:
        sample = pd.DataFrame(
            {
                "Record_ID": ["R1", "R2", "R3"],
                "Category": ["A", " a ", "B"],
                "Value": [1.0, 2.0, 3.0],
            }
        )
        result = inspect(sample)
        passed = result["shape"] == {"rows": 3, "columns": 3}
        checks.append(
            {
                "name": "core_inspection",
                "passed": bool(passed),
                "details": result["shape"],
            }
        )
    except Exception as exc:  # defensive diagnostic boundary
        checks.append(
            {
                "name": "core_inspection",
                "passed": False,
                "details": f"{type(exc).__name__}: {exc}",
            }
        )

    checks.append(
        {
            "name": "python_supported",
            "passed": sys.version_info >= (3, 10),
            "details": platform.python_version(),
        }
    )
    return {
        "ok": all(item["passed"] for item in checks),
        "checks": checks,
        "environment": about(),
    }
