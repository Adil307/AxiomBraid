"""Runtime diagnostics for support, bug reports, and reproducible workflows."""

from __future__ import annotations

import importlib.util
import platform
import sys
from typing import Any

import pandas as pd


def about() -> dict[str, Any]:
    """Return release, platform, and optional-feature information."""
    from . import API_STATUS, BRAND_NAME, PUBLIC_API_VERSION, RELEASE_STAGE, VERSION_INFO, __version__

    optional = {
        "charts": importlib.util.find_spec("matplotlib") is not None,
        "yaml": importlib.util.find_spec("yaml") is not None,
        "toml_reader": importlib.util.find_spec("tomllib") is not None or importlib.util.find_spec("tomli") is not None,
    }
    return {
        "brand": BRAND_NAME,
        "version": __version__,
        "version_info": VERSION_INFO,
        "api_status": API_STATUS,
        "public_api_version": PUBLIC_API_VERSION,
        "release_stage": RELEASE_STAGE,
        "python": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "pandas": pd.__version__,
        "optional_features": optional,
    }


def self_check() -> dict[str, Any]:
    """Run non-destructive Version 1 and Version 2 smoke checks."""
    from .api import inspect
    from .corruption import inject_issues
    from .evaluation import compatibility_check

    checks: list[dict[str, Any]] = []
    sample = pd.DataFrame({
        "Record_ID": ["R1", "R2", "R3", "R4"],
        "Category": ["A", " a ", "B", "B"],
        "Value": [1.0, 2.0, 3.0, 4.0],
    })

    try:
        result = inspect(sample, include_confidence=True, include_quality_profile=True)
        checks.append({"name": "core_inspection", "passed": result["shape"] == {"rows": 4, "columns": 3}, "details": result["shape"]})
        checks.append({"name": "confidence_reporting", "passed": "confidence_summary" in result, "details": result.get("confidence_summary", {}).get("issue_count")})
        checks.append({"name": "quality_profile", "passed": "quality_profile" in result, "details": result.get("quality_profile", {}).get("score")})
    except Exception as exc:
        checks.append({"name": "inspection_stack", "passed": False, "details": f"{type(exc).__name__}: {exc}"})

    try:
        original = sample.copy(deep=True)
        corrupted, truth = inject_issues(sample, missing_rate=0.25, duplicate_rate=0.25, random_state=42)
        checks.append({
            "name": "non_destructive_corruption",
            "passed": sample.equals(original) and len(truth.get("events", [])) >= 1,
            "details": {"source_unchanged": sample.equals(original), "event_count": len(truth.get("events", [])), "corrupted_rows": int(len(corrupted))},
        })
    except Exception as exc:
        checks.append({"name": "non_destructive_corruption", "passed": False, "details": f"{type(exc).__name__}: {exc}"})

    try:
        compatibility = compatibility_check()
        checks.append({"name": "public_api_compatibility", "passed": bool(compatibility.get("ok")), "details": compatibility.get("missing", [])})
    except Exception as exc:
        checks.append({"name": "public_api_compatibility", "passed": False, "details": f"{type(exc).__name__}: {exc}"})

    checks.append({"name": "python_supported", "passed": sys.version_info >= (3, 10), "details": platform.python_version()})
    return {"ok": all(item["passed"] for item in checks), "checks": checks, "environment": about()}
