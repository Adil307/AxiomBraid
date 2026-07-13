"""Memory-bounded CSV profiling with exact row/missing counts and a reservoir sample."""

from __future__ import annotations

import random
from pathlib import Path
from typing import Any

import pandas as pd


def stream_csv(
    path: str | Path,
    *,
    chunksize: int = 100_000,
    sample_rows: int = 50_000,
    random_state: int = 42,
    config: Any = None,
    language: str = "en",
    read_csv_kwargs: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Profile a CSV without loading every row into memory at once.

    Row counts and missing-value counts are exact. Rich issue detection is based on
    a deterministic reservoir sample and is clearly labelled as sample-based.
    """
    from .inspector import DataGuide

    source = Path(path)
    if not source.exists() or not source.is_file():
        raise FileNotFoundError(f"CSV file not found: {source}")
    if source.suffix.lower() != ".csv":
        raise ValueError("stream_csv currently supports .csv files only.")
    if not isinstance(chunksize, int) or chunksize < 1:
        raise ValueError("chunksize must be a positive integer.")
    if not isinstance(sample_rows, int) or sample_rows < 1:
        raise ValueError("sample_rows must be a positive integer.")
    if not isinstance(random_state, int):
        raise TypeError("random_state must be an integer.")

    kwargs = dict(read_csv_kwargs or {})
    forbidden = {"chunksize", "iterator"} & set(kwargs)
    if forbidden:
        raise ValueError("read_csv_kwargs must not override chunksize or iterator.")

    rng = random.Random(random_state)
    reservoir: list[dict[str, Any]] = []
    total_rows = 0
    columns: list[str] | None = None
    missing_counts: dict[str, int] = {}
    numeric_stats: dict[str, dict[str, float | int | None]] = {}
    chunk_count = 0

    for chunk in pd.read_csv(source, chunksize=chunksize, **kwargs):
        chunk_count += 1
        current_columns = [str(column) for column in chunk.columns]
        if columns is None:
            columns = current_columns
            missing_counts = {column: 0 for column in columns}
        elif current_columns != columns:
            raise ValueError("CSV columns changed between chunks.")

        for column in columns:
            missing_counts[column] += int(chunk[column].isna().sum())
            if pd.api.types.is_numeric_dtype(chunk[column]):
                values = pd.to_numeric(chunk[column], errors="coerce").dropna()
                if not values.empty:
                    state = numeric_stats.setdefault(
                        column,
                        {"count": 0, "sum": 0.0, "min": None, "max": None},
                    )
                    state["count"] = int(state["count"]) + int(values.count())
                    state["sum"] = float(state["sum"]) + float(values.sum())
                    value_min, value_max = float(values.min()), float(values.max())
                    state["min"] = value_min if state["min"] is None else min(float(state["min"]), value_min)
                    state["max"] = value_max if state["max"] is None else max(float(state["max"]), value_max)

        for record in chunk.to_dict(orient="records"):
            if total_rows < sample_rows:
                reservoir.append(record)
            else:
                position = rng.randint(0, total_rows)
                if position < sample_rows:
                    reservoir[position] = record
            total_rows += 1

    if columns is None:
        empty = pd.read_csv(source, nrows=0, **kwargs)
        columns = [str(column) for column in empty.columns]
        missing_counts = {column: 0 for column in columns}

    sample = pd.DataFrame(reservoir, columns=columns)
    guide = DataGuide.from_config(sample, config)
    guide._sampling_metadata = {
        "requested_mode": "stream",
        "effective_mode": "stream_sample",
        "sampled": total_rows > len(sample),
        "strategy": "reservoir",
        "full_rows": total_rows,
        "analyzed_rows": len(sample),
        "sample_fraction": round(len(sample) / total_rows, 6) if total_rows else 0.0,
        "random_state": random_state,
        "warning": "Rich findings are sample-based; row and missing counts are exact.",
    }
    inspection = guide.inspect(language)
    missing = {
        column: {
            "count": count,
            "percentage": round(count / total_rows * 100, 2) if total_rows else 0.0,
        }
        for column, count in missing_counts.items()
    }
    aggregates = {}
    for column, state in numeric_stats.items():
        count = int(state["count"])
        aggregates[column] = {
            "count": count,
            "mean": round(float(state["sum"]) / count, 6) if count else None,
            "min": state["min"],
            "max": state["max"],
        }
    return {
        "source": str(source.resolve()),
        "streaming": {
            "chunksize": chunksize,
            "chunk_count": chunk_count,
            "exact_rows": total_rows,
            "columns": len(columns),
            "sample_rows": len(sample),
            "sample_strategy": "reservoir",
            "random_state": random_state,
            "memory_bounded": True,
        },
        "exact_missing_values": missing,
        "exact_numeric_aggregates": aggregates,
        "sample_inspection": inspection,
    }
