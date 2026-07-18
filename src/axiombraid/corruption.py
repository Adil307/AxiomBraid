"""Controlled synthetic data-quality corruption with exact ground truth.

The corruption engine is intended for testing and evaluation. It never mutates
its input and every injected change is recorded in a machine-readable ground
truth document.
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import random
import re
from typing import Any, Iterable

import pandas as pd


GROUND_TRUTH_VERSION = "1.0"


def _load_frame(data: Any) -> pd.DataFrame:
    if isinstance(data, pd.DataFrame):
        return data.copy(deep=True)
    path = Path(data)
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(path)
    if suffix in {".xlsx", ".xls"}:
        return pd.read_excel(path)
    raise ValueError("Synthetic corruption supports DataFrames, CSV, and Excel files.")


def _rate(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a number between 0 and 1.")
    number = float(value)
    if not 0.0 <= number <= 1.0:
        raise ValueError(f"{name} must be between 0 and 1.")
    return number


def _positive_int(value: Any, name: str, *, allow_zero: bool = True) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer.")
    minimum = 0 if allow_zero else 1
    if value < minimum:
        raise ValueError(f"{name} must be >= {minimum}.")
    return value


def _count(rate: float, population: int) -> int:
    if rate <= 0 or population <= 0:
        return 0
    return min(population, max(1, int(round(rate * population))))


def _column_key(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(name).strip().lower()).strip("_")


def _identifier_name_hint(name: str) -> bool:
    cleaned = _column_key(name)
    tokens = set(cleaned.split("_"))
    return (
        cleaned in {"id", "uuid", "guid"}
        or cleaned.endswith("_id")
        or cleaned.startswith("id_")
        or bool(tokens.intersection({"identifier", "uuid", "guid"}))
    )


def _numeric_range_rule(column_name: str) -> dict[str, float | str] | None:
    cleaned = _column_key(column_name)
    tokens = set(cleaned.split("_"))
    if "latitude" in tokens or cleaned in {"lat", "latitude"}:
        return {"name": "latitude", "minimum": -90.0, "maximum": 90.0}
    if "longitude" in tokens or cleaned in {"lon", "lng", "longitude"}:
        return {"name": "longitude", "minimum": -180.0, "maximum": 180.0}
    if "age" in tokens or cleaned.endswith("_age"):
        return {"name": "age", "minimum": 0.0, "maximum": 120.0}
    if "month" in tokens:
        return {"name": "month", "minimum": 1.0, "maximum": 12.0}
    if "year" in tokens:
        return {"name": "year", "minimum": 1900.0, "maximum": 2100.0}
    if tokens.intersection(
        {"percentage", "percent", "pct", "attendance", "marks", "mark", "score", "grade"}
    ):
        return {"name": "percentage_or_score", "minimum": 0.0, "maximum": 100.0}
    if tokens.intersection({"probability", "prob"}):
        return {"name": "probability", "minimum": 0.0, "maximum": 1.0}
    return None


def _select_columns(
    frame: pd.DataFrame,
    requested: Iterable[str] | None,
    eligible: Iterable[str],
) -> list[str]:
    eligible_list = [str(column) for column in eligible]
    if requested is None:
        return eligible_list
    requested_list = [str(column) for column in requested]
    missing = [column for column in requested_list if column not in frame.columns]
    if missing:
        raise KeyError("Unknown corruption column(s): " + ", ".join(missing))
    return [column for column in requested_list if column in eligible_list]


def _event(
    issue_code: str,
    *,
    columns: list[str] | None = None,
    row_indices: list[int] | None = None,
    cell_locations: list[dict[str, Any]] | None = None,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "issue_code": issue_code,
        "columns": list(columns or []),
        "row_indices": list(row_indices or []),
        "cell_locations": deepcopy(cell_locations or []),
        "details": deepcopy(details or {}),
    }


def _text_candidates(frame: pd.DataFrame, columns: list[str]) -> list[tuple[int, str]]:
    candidates: list[tuple[int, str]] = []
    for column in columns:
        series = frame[column]
        values = series.dropna().astype(str)
        normalized = values.str.strip().str.casefold()
        repeated = set(normalized.value_counts()[lambda counts: counts >= 2].index)
        for index, value in values.items():
            if value.strip().casefold() in repeated and value.strip():
                candidates.append((int(index), column))
    return candidates


def inject_issues(
    data: Any,
    *,
    missing_rate: float = 0.0,
    duplicate_rate: float = 0.0,
    text_case_rate: float = 0.0,
    whitespace_rate: float = 0.0,
    invalid_range_rate: float = 0.0,
    outlier_rate: float = 0.0,
    date_format_rate: float = 0.0,
    constant_columns: int = 0,
    identifier_columns: int = 0,
    columns: dict[str, list[str]] | None = None,
    random_state: int = 42,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Inject controlled issues and return ``(corrupted_dataframe, ground_truth)``.

    Rates are fractions between 0 and 1. The optional ``columns`` mapping may
    restrict a corruption type, for example ``{"missing_values": ["Age"]}``.
    The input object is never modified.
    """

    rates = {
        "missing_rate": _rate(missing_rate, "missing_rate"),
        "duplicate_rate": _rate(duplicate_rate, "duplicate_rate"),
        "text_case_rate": _rate(text_case_rate, "text_case_rate"),
        "whitespace_rate": _rate(whitespace_rate, "whitespace_rate"),
        "invalid_range_rate": _rate(invalid_range_rate, "invalid_range_rate"),
        "outlier_rate": _rate(outlier_rate, "outlier_rate"),
        "date_format_rate": _rate(date_format_rate, "date_format_rate"),
    }
    constant_columns = _positive_int(constant_columns, "constant_columns")
    identifier_columns = _positive_int(identifier_columns, "identifier_columns")
    if isinstance(random_state, bool) or not isinstance(random_state, int):
        raise TypeError("random_state must be an integer.")
    if columns is not None and not isinstance(columns, dict):
        raise TypeError("columns must be a dictionary or None.")

    rng = random.Random(random_state)
    original = _load_frame(data)
    frame = original.copy(deep=True).reset_index(drop=True)
    events: list[dict[str, Any]] = []
    restrictions = columns or {}

    # Missing values -------------------------------------------------------
    eligible_columns = _select_columns(
        frame,
        restrictions.get("missing_values"),
        frame.columns,
    )
    cells = [
        (int(row), str(column))
        for column in eligible_columns
        for row in frame.index
        if pd.notna(frame.at[row, column])
    ]
    selected = rng.sample(cells, _count(rates["missing_rate"], len(cells)))
    if selected:
        locations = []
        for row, column in selected:
            previous = frame.at[row, column]
            frame.at[row, column] = pd.NA
            locations.append({"row": row, "column": column, "original": previous})
        events.append(
            _event(
                "missing_values",
                columns=sorted({column for _, column in selected}),
                row_indices=sorted({row for row, _ in selected}),
                cell_locations=locations,
                details={"injected_cell_count": len(selected), "requested_rate": rates["missing_rate"]},
            )
        )

    # Text case and whitespace inconsistency ------------------------------
    text_columns = [
        str(column)
        for column in frame.select_dtypes(include=["object", "string", "category"]).columns
    ]
    case_columns = _select_columns(frame, restrictions.get("text_case"), text_columns)
    case_candidates = _text_candidates(frame, case_columns)
    case_selected = rng.sample(
        case_candidates,
        _count(rates["text_case_rate"], len(case_candidates)),
    )
    if case_selected:
        locations = []
        for position, (row, column) in enumerate(case_selected):
            previous = str(frame.at[row, column])
            changed = previous.upper() if position % 2 == 0 else previous.lower()
            if changed == previous:
                changed = previous.swapcase()
            frame.at[row, column] = changed
            locations.append({"row": row, "column": column, "original": previous, "injected": changed})
        events.append(
            _event(
                "text_inconsistencies",
                columns=sorted({column for _, column in case_selected}),
                row_indices=sorted({row for row, _ in case_selected}),
                cell_locations=locations,
                details={"kind": "case", "injected_cell_count": len(case_selected)},
            )
        )

    whitespace_columns = _select_columns(frame, restrictions.get("whitespace"), text_columns)
    whitespace_candidates = _text_candidates(frame, whitespace_columns)
    whitespace_selected = rng.sample(
        whitespace_candidates,
        _count(rates["whitespace_rate"], len(whitespace_candidates)),
    )
    if whitespace_selected:
        locations = []
        for position, (row, column) in enumerate(whitespace_selected):
            previous = str(frame.at[row, column])
            changed = f" {previous}" if position % 2 == 0 else f"{previous} "
            frame.at[row, column] = changed
            locations.append({"row": row, "column": column, "original": previous, "injected": changed})
        events.append(
            _event(
                "text_inconsistencies",
                columns=sorted({column for _, column in whitespace_selected}),
                row_indices=sorted({row for row, _ in whitespace_selected}),
                cell_locations=locations,
                details={"kind": "whitespace", "injected_cell_count": len(whitespace_selected)},
            )
        )

    # Invalid numeric ranges ----------------------------------------------
    numeric_columns = [str(column) for column in frame.select_dtypes(include="number").columns]
    range_columns = [column for column in numeric_columns if _numeric_range_rule(column)]
    range_columns = _select_columns(frame, restrictions.get("invalid_ranges"), range_columns)
    range_cells = [
        (int(row), column)
        for column in range_columns
        for row in frame.index
        if pd.notna(frame.at[row, column])
    ]
    range_selected = rng.sample(
        range_cells,
        _count(rates["invalid_range_rate"], len(range_cells)),
    )
    if range_selected:
        locations = []
        for row, column in range_selected:
            rule = _numeric_range_rule(column)
            assert rule is not None
            previous = frame.at[row, column]
            if not pd.api.types.is_float_dtype(frame[column].dtype):
                frame[column] = pd.to_numeric(frame[column], errors="coerce").astype(float)
            span = float(rule["maximum"]) - float(rule["minimum"])
            injected = float(rule["maximum"]) + max(1.0, span * 0.25)
            frame.at[row, column] = injected
            locations.append(
                {
                    "row": row,
                    "column": column,
                    "original": previous,
                    "injected": injected,
                    "rule": deepcopy(rule),
                }
            )
        affected_columns = sorted({column for _, column in range_selected})
        affected_rows = sorted({row for row, _ in range_selected})
        events.append(
            _event(
                "suspicious_numeric_ranges",
                columns=affected_columns,
                row_indices=affected_rows,
                cell_locations=locations,
                details={"injected_cell_count": len(range_selected)},
            )
        )
        # The injected values are deliberately far beyond conservative bounds,
        # so they are also expected to trigger IQR outlier screening. Ground
        # truth records this legitimate multi-label effect explicitly.
        events.append(
            _event(
                "potential_outliers",
                columns=affected_columns,
                row_indices=affected_rows,
                cell_locations=locations,
                details={
                    "source": "invalid_range_injection",
                    "injected_cell_count": len(range_selected),
                },
            )
        )

    # Numerical outliers ---------------------------------------------------
    preferred_outlier_columns = [
        column for column in numeric_columns
        if not _identifier_name_hint(column) and _numeric_range_rule(column) is None
    ]
    fallback_outlier_columns = [
        column for column in numeric_columns if not _identifier_name_hint(column)
    ]
    outlier_eligible = preferred_outlier_columns or fallback_outlier_columns
    outlier_columns = _select_columns(frame, restrictions.get("outliers"), outlier_eligible)
    outlier_profiles: dict[str, dict[str, Any]] = {}
    outlier_cells: list[tuple[int, str]] = []

    for column in outlier_columns:
        numeric = pd.to_numeric(frame[column], errors="coerce")
        valid = numeric.dropna()
        if len(valid) < 4:
            continue

        q1 = float(valid.quantile(0.25))
        q3 = float(valid.quantile(0.75))
        iqr = q3 - q1
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        scale = iqr if iqr > 0 else max(abs(float(valid.mean())), 1.0)

        # Only replace source cells that are not baseline IQR outliers. This
        # prevents a synthetic "injection" from merely replacing one existing
        # outlier with another and producing ambiguous ground truth.
        candidate_rows = numeric.index[
            numeric.notna() & numeric.ge(lower) & numeric.le(upper)
        ].tolist()

        if not candidate_rows:
            continue

        outlier_profiles[column] = {
            "q1": q1,
            "q3": q3,
            "iqr": iqr,
            "lower_bound": lower,
            "upper_bound": upper,
            "scale": scale,
        }
        outlier_cells.extend((int(row), column) for row in candidate_rows)

    outlier_selected = rng.sample(
        outlier_cells,
        _count(rates["outlier_rate"], len(outlier_cells)),
    )
    if outlier_selected:
        locations = []
        for row, column in outlier_selected:
            profile = outlier_profiles[column]
            previous = frame.at[row, column]
            if not pd.api.types.is_float_dtype(frame[column].dtype):
                frame[column] = pd.to_numeric(frame[column], errors="coerce").astype(float)

            # A large deterministic margin keeps the injected observation well
            # beyond the IQR boundary after normal quartile recomputation.
            injected = (
                float(profile["upper_bound"])
                + 1000.0 * float(profile["scale"])
                + 1.0
            )
            frame.at[row, column] = injected
            locations.append(
                {
                    "row": row,
                    "column": column,
                    "original": previous,
                    "injected": injected,
                    "source_row_was_baseline_non_outlier": True,
                    "baseline_lower_bound": profile["lower_bound"],
                    "baseline_upper_bound": profile["upper_bound"],
                }
            )
        if locations:
            events.append(
                _event(
                    "potential_outliers",
                    columns=sorted({item["column"] for item in locations}),
                    row_indices=sorted({int(item["row"]) for item in locations}),
                    cell_locations=locations,
                    details={"injected_cell_count": len(locations)},
                )
            )

    # Mixed date formatting ------------------------------------------------
    date_columns = []
    for column in text_columns:
        key = _column_key(column)
        tokens = set(key.split("_"))
        if (
            tokens.intersection({"date", "dob", "birthday", "timestamp"})
            or key.endswith("date")
            or key.endswith("timestamp")
        ):
            date_columns.append(column)
    date_columns = _select_columns(frame, restrictions.get("date_formats"), date_columns)
    date_candidates: list[tuple[int, str, pd.Timestamp]] = []
    for column in date_columns:
        try:
            parsed = pd.to_datetime(frame[column], errors="coerce", format="mixed")
        except TypeError:
            parsed = pd.to_datetime(frame[column], errors="coerce")
        for row, value in parsed.items():
            if pd.notna(value):
                date_candidates.append((int(row), column, pd.Timestamp(value)))
    date_selected = rng.sample(
        date_candidates,
        _count(rates["date_format_rate"], len(date_candidates)),
    )
    if date_selected:
        formats = ["%d/%m/%Y", "%b %d, %Y", "%Y.%m.%d"]
        locations = []
        for position, (row, column, timestamp) in enumerate(date_selected):
            previous = frame.at[row, column]
            injected = timestamp.strftime(formats[position % len(formats)])
            frame.at[row, column] = injected
            locations.append({"row": row, "column": column, "original": previous, "injected": injected})
        events.append(
            _event(
                "date_like_text",
                columns=sorted({column for _, column, _ in date_selected}),
                row_indices=sorted({row for row, _, _ in date_selected}),
                cell_locations=locations,
                details={"kind": "mixed_date_formats", "injected_cell_count": len(date_selected)},
            )
        )

    # Constant and identifier columns -------------------------------------
    constant_names = []
    for number in range(1, constant_columns + 1):
        name = f"Injected_Constant_{number}"
        while name in frame.columns:
            name += "_X"
        frame[name] = "CONSTANT"
        constant_names.append(name)
    if constant_names:
        events.append(
            _event(
                "constant_columns",
                columns=constant_names,
                details={"injected_column_count": len(constant_names)},
            )
        )

    identifier_names = []
    for number in range(1, identifier_columns + 1):
        name = f"Injected_ID_{number}"
        while name in frame.columns:
            name += "_X"
        frame[name] = [f"AB-{number}-{row:08d}" for row in range(len(frame))]
        identifier_names.append(name)
    if identifier_names:
        events.append(
            _event(
                "possible_identifiers",
                columns=identifier_names,
                details={"injected_column_count": len(identifier_names)},
            )
        )

    # Exact duplicate rows are injected last so later column additions or
    # cell-level corruptions cannot accidentally make them non-identical.
    duplicate_count = _count(rates["duplicate_rate"], len(frame))
    if duplicate_count:
        source_indices = rng.sample(list(frame.index), min(duplicate_count, len(frame)))
        duplicated = frame.loc[source_indices].copy(deep=True)
        start = len(frame)
        frame = pd.concat([frame, duplicated], ignore_index=True)
        added_indices = list(range(start, start + len(duplicated)))
        events.append(
            _event(
                "duplicate_rows",
                row_indices=added_indices,
                details={
                    "source_row_indices": [int(value) for value in source_indices],
                    "added_row_indices": added_indices,
                    "injected_row_count": len(added_indices),
                    "requested_rate": rates["duplicate_rate"],
                },
            )
        )

    issue_summary: dict[str, dict[str, Any]] = {}
    for item in events:
        code = item["issue_code"]
        summary = issue_summary.setdefault(code, {"event_count": 0, "columns": [], "row_indices": []})
        summary["event_count"] += 1
        summary["columns"] = sorted(set(summary["columns"]) | set(item["columns"]))
        summary["row_indices"] = sorted(set(summary["row_indices"]) | set(item["row_indices"]))

    ground_truth = {
        "ground_truth_version": GROUND_TRUTH_VERSION,
        "random_state": random_state,
        "original_shape": {"rows": int(original.shape[0]), "columns": int(original.shape[1])},
        "corrupted_shape": {"rows": int(frame.shape[0]), "columns": int(frame.shape[1])},
        "requested_configuration": {
            **rates,
            "constant_columns": constant_columns,
            "identifier_columns": identifier_columns,
            "columns": deepcopy(restrictions),
        },
        "events": events,
        "issue_summary": issue_summary,
        "event_count": len(events),
        "note": (
            "Ground truth records only issues intentionally injected by AxiomBraid. "
            "A source dataset may contain additional pre-existing issues."
        ),
    }
    return frame, ground_truth


def ground_truth_pairs(ground_truth: dict[str, Any]) -> set[tuple[str, str]]:
    """Return expected ``(issue_code, column)`` pairs for evaluation."""
    if not isinstance(ground_truth, dict):
        raise TypeError("ground_truth must be a dictionary.")
    pairs: set[tuple[str, str]] = set()
    for item in ground_truth.get("events", []):
        if not isinstance(item, dict):
            continue
        code = str(item.get("issue_code", "")).strip()
        if not code:
            continue
        columns = item.get("columns", [])
        if isinstance(columns, list) and columns:
            pairs.update((code, str(column)) for column in columns)
        else:
            pairs.add((code, "__dataset__"))
    return pairs