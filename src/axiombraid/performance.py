"""Non-mutating performance and sampling modes for AxiomBraid."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

import pandas as pd


class PerformanceMixin:
    """Analyze deterministic samples while preserving the source object."""

    _PERFORMANCE_MODES = {"full", "sample", "auto"}
    _SAMPLE_STRATEGIES = {"random", "head", "systematic"}

    def performance_profile(self) -> dict[str, Any]:
        memory_bytes = int(self.dataframe.memory_usage(index=True, deep=True).sum())
        rows = int(len(self.dataframe))
        columns = int(self.dataframe.shape[1])
        return {
            "rows": rows,
            "columns": columns,
            "memory_bytes": memory_bytes,
            "memory_megabytes": round(memory_bytes / (1024 ** 2), 3),
            "recommended_mode": "auto" if rows >= 50000 else "full",
        }

    @staticmethod
    def _sample_frame(
        frame: pd.DataFrame,
        *,
        sample_rows: int,
        strategy: str,
        random_state: int,
    ) -> pd.DataFrame:
        if strategy == "head":
            return frame.head(sample_rows).copy(deep=True)
        if strategy == "random":
            return frame.sample(
                n=sample_rows,
                random_state=random_state,
                replace=False,
            ).copy(deep=True)
        step = max(len(frame) // sample_rows, 1)
        positions = list(range(0, len(frame), step))[:sample_rows]
        return frame.iloc[positions].copy(deep=True)

    def prepare_analysis(
        self,
        *,
        mode: str = "auto",
        sample_rows: int = 50000,
        strategy: str = "random",
        random_state: int = 42,
    ):
        """Return an analysis guide; the current object remains unchanged."""
        normalized_mode = str(mode).strip().lower()
        normalized_strategy = str(strategy).strip().lower()
        if normalized_mode not in self._PERFORMANCE_MODES:
            raise ValueError("mode must be 'full', 'sample', or 'auto'.")
        if normalized_strategy not in self._SAMPLE_STRATEGIES:
            raise ValueError("strategy must be 'random', 'head', or 'systematic'.")
        if not isinstance(sample_rows, int) or sample_rows < 1:
            raise ValueError("sample_rows must be a positive integer.")
        if not isinstance(random_state, int):
            raise TypeError("random_state must be an integer.")

        full_rows = int(len(self.dataframe))
        should_sample = (
            normalized_mode == "sample"
            or (normalized_mode == "auto" and full_rows > sample_rows)
        ) and full_rows > sample_rows

        if not should_sample:
            self._sampling_metadata = {
                "requested_mode": normalized_mode,
                "effective_mode": "full",
                "sampled": False,
                "strategy": None,
                "full_rows": full_rows,
                "analyzed_rows": full_rows,
                "sample_fraction": 1.0 if full_rows else 0.0,
                "random_state": None,
                "warning": None,
            }
            return self

        sampled_frame = self._sample_frame(
            self.dataframe,
            sample_rows=sample_rows,
            strategy=normalized_strategy,
            random_state=random_state,
        )
        sampled = type(self)(sampled_frame, **self._configuration())
        sampled._runtime_config = deepcopy(getattr(self, "_runtime_config", None))
        for name, plugin in self._plugins.items():
            sampled.register_plugin(name, plugin)
        sampled._sampling_metadata = {
            "requested_mode": normalized_mode,
            "effective_mode": "sample",
            "sampled": True,
            "strategy": normalized_strategy,
            "full_rows": full_rows,
            "analyzed_rows": int(len(sampled_frame)),
            "sample_fraction": round(len(sampled_frame) / full_rows, 6),
            "random_state": random_state if normalized_strategy == "random" else None,
            "warning": (
                "Results describe a sample, not every row. Cleaning is disabled "
                "on sampled analysis objects."
            ),
            "source_fingerprint": self.dataset_fingerprint()["combined_hash"],
        }
        return sampled

    def inspect_performance(
        self,
        language: str = "en",
        *,
        mode: str = "auto",
        sample_rows: int = 50000,
        strategy: str = "random",
        random_state: int = 42,
    ) -> dict[str, Any]:
        guide = self.prepare_analysis(
            mode=mode,
            sample_rows=sample_rows,
            strategy=strategy,
            random_state=random_state,
        )
        return guide.inspect(language=language)
