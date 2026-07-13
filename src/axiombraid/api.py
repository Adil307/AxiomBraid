"""Stable functional API for AxiomBraid 1.0.

The recommended style is::

    import axiombraid as AB
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from .cache import cached_inspect
from .inspector import DataGuide
from .streaming import stream_csv


def read_csv(path: str | Path, **kwargs: Any) -> pd.DataFrame:
    """Read a CSV file using pandas and return a DataFrame."""
    return pd.read_csv(path, **kwargs)


def read_excel(path: str | Path, **kwargs: Any) -> pd.DataFrame:
    """Read an Excel file using pandas and return a DataFrame."""
    return pd.read_excel(path, **kwargs)


def guide(data: Any, *, config: Any = None, **analysis_options: Any) -> DataGuide:
    """Create an AxiomBraid guide from a path or DataFrame."""
    if config is not None:
        if analysis_options:
            raise ValueError("Use either config or analysis_options, not both.")
        return DataGuide.from_config(data, config)
    return DataGuide(data, **analysis_options)


def inspect(
    data: Any,
    *,
    language: str = "en",
    config: Any = None,
    **analysis_options: Any,
) -> dict[str, Any]:
    """Inspect a dataset and return a structured result."""
    return guide(data, config=config, **analysis_options).inspect(language)


def report(
    data: Any,
    *,
    language: str = "en",
    config: Any = None,
    **analysis_options: Any,
) -> dict[str, Any]:
    """Print and return a complete console report."""
    return guide(data, config=config, **analysis_options).report(language)


def clean(
    data: Any,
    *,
    risk: str = "low",
    selected_actions: list[str] | None = None,
    return_details: bool = False,
    config: Any = None,
    **analysis_options: Any,
) -> pd.DataFrame | dict[str, Any]:
    """Safely clean a deep copy; the supplied dataset is never changed."""
    result = guide(data, config=config, **analysis_options).apply_cleaning(
        max_risk=risk,
        selected_actions=selected_actions,
        inplace=False,
    )
    return result if return_details else result["dataframe"]


def validate(
    data: Any,
    contract: dict[str, Any] | str | Path,
    *,
    config: Any = None,
    **analysis_options: Any,
) -> dict[str, Any]:
    """Validate a dataset against a full contract or simple column-rule mapping."""
    instance = guide(data, config=config, **analysis_options)
    if isinstance(contract, (str, Path)):
        resolved = instance.load_validation_contract(contract)
    elif isinstance(contract, dict) and "contract_version" not in contract:
        rules = contract.get("columns", contract)
        if not isinstance(rules, dict):
            raise TypeError("Contract shorthand must contain column rules.")
        normalized_rules = {}
        for column, definition in rules.items():
            if not isinstance(definition, dict):
                raise TypeError(f"Rules for '{column}' must be a dictionary.")
            item = dict(definition)
            if item.get("dtype") == "numeric":
                item["dtype"] = "number"
            normalized_rules[str(column)] = item
        resolved = instance.create_validation_contract(
            normalized_rules,
            strict_columns=False,
        )
    else:
        resolved = contract
    return instance.validate_contract(resolved)
def compare(
    baseline: Any,
    candidate: Any,
    *,
    mode: str = "data",
    config: Any = None,
    **analysis_options: Any,
) -> dict[str, Any]:
    """Compare dataset contents or schemas."""
    instance = guide(baseline, config=config, **analysis_options)
    normalized = mode.strip().lower()
    if normalized in {"data", "before_after", "before-after"}:
        return instance.compare_before_after(candidate)
    if normalized == "schema":
        return instance.compare_schema(candidate)
    raise ValueError("mode must be 'data' or 'schema'.")


def detect_drift(
    baseline: Any,
    candidate: Any,
    *,
    config: Any = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Run AxiomBraid's transparent drift screen."""
    return guide(baseline, config=config).detect_drift(candidate, **kwargs)


def export_html(
    data: Any,
    path: str | Path = "axiombraid_report.html",
    *,
    language: str = "en",
    theme: str = "light",
    report_title: str | None = None,
    config: Any = None,
    **analysis_options: Any,
) -> Path:
    """Create a standalone HTML report."""
    return guide(data, config=config, **analysis_options).export_html(
        path,
        language,
        theme=theme,
        report_title=report_title,
    )
