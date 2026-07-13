"""Dataset comparison, schema comparison, and basic drift checks."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

import pandas as pd


class ComparisonMixin:
    """Compare dataset versions using transparent heuristics."""

    def _coerce_comparison_frame(self, data: Any) -> pd.DataFrame:
        if isinstance(data, pd.DataFrame):
            return data.copy(deep=True)
        if hasattr(data, "dataframe") and isinstance(data.dataframe, pd.DataFrame):
            return data.dataframe.copy(deep=True)
        return self._load_data(data).copy(deep=True)

    @staticmethod
    def _compare_frames(before: pd.DataFrame, after: pd.DataFrame) -> dict[str, Any]:
        left = before.reset_index(drop=True)
        right = after.reset_index(drop=True)
        common_columns = [column for column in left.columns if column in right.columns]
        common_rows = min(len(left), len(right))
        changed_cells = 0
        if common_columns and common_rows:
            a = left.loc[: common_rows - 1, common_columns]
            b = right.loc[: common_rows - 1, common_columns]
            equal = a.eq(b) | (a.isna() & b.isna())
            changed_cells = int((~equal).sum().sum())
        dtype_changes = {
            str(column): {"before": str(left[column].dtype), "after": str(right[column].dtype)}
            for column in common_columns
            if str(left[column].dtype) != str(right[column].dtype)
        }
        return {
            "before_shape": {"rows": int(len(left)), "columns": int(left.shape[1])},
            "after_shape": {"rows": int(len(right)), "columns": int(right.shape[1])},
            "row_change": int(len(right) - len(left)),
            "column_change": int(right.shape[1] - left.shape[1]),
            "missing_cells_before": int(left.isna().sum().sum()),
            "missing_cells_after": int(right.isna().sum().sum()),
            "missing_cell_change": int(right.isna().sum().sum() - left.isna().sum().sum()),
            "duplicate_rows_before": int(left.duplicated().sum()),
            "duplicate_rows_after": int(right.duplicated().sum()),
            "changed_cells_in_shared_area": changed_cells,
            "dtype_changes": dtype_changes,
            "added_columns": [str(c) for c in right.columns if c not in left.columns],
            "removed_columns": [str(c) for c in left.columns if c not in right.columns],
        }

    def compare_before_after(
        self,
        after: Any,
        *,
        before: Any | None = None,
    ) -> dict[str, Any]:
        """Compare a candidate cleaned dataset with the current or supplied baseline."""
        before_frame = self.dataframe.copy(deep=True) if before is None else self._coerce_comparison_frame(before)
        after_frame = self._coerce_comparison_frame(after)
        return self._compare_frames(before_frame, after_frame)

    def compare_schema(self, other: Any) -> dict[str, Any]:
        """Compare columns, dtypes, order, and missing-capable behavior."""
        baseline = self.dataframe
        candidate = self._coerce_comparison_frame(other)
        baseline_columns = list(baseline.columns)
        candidate_columns = list(candidate.columns)
        shared = [column for column in baseline_columns if column in candidate_columns]
        dtype_changes = {
            str(column): {
                "baseline": str(baseline[column].dtype),
                "candidate": str(candidate[column].dtype),
            }
            for column in shared
            if str(baseline[column].dtype) != str(candidate[column].dtype)
        }
        missing_presence_changes = {
            str(column): {
                "baseline_has_missing": bool(baseline[column].isna().any()),
                "candidate_has_missing": bool(candidate[column].isna().any()),
            }
            for column in shared
            if bool(baseline[column].isna().any()) != bool(candidate[column].isna().any())
        }
        return {
            "same_schema": not (
                [c for c in candidate_columns if c not in baseline_columns]
                or [c for c in baseline_columns if c not in candidate_columns]
                or dtype_changes
            ),
            "added_columns": [str(c) for c in candidate_columns if c not in baseline_columns],
            "removed_columns": [str(c) for c in baseline_columns if c not in candidate_columns],
            "shared_columns": [str(c) for c in shared],
            "dtype_changes": dtype_changes,
            "column_order_changed": [str(c) for c in baseline_columns if c in candidate_columns]
            != [str(c) for c in candidate_columns if c in baseline_columns],
            "missing_presence_changes": missing_presence_changes,
        }

    def detect_drift(
        self,
        other: Any,
        *,
        numeric_mean_threshold: float = 0.50,
        categorical_tv_threshold: float = 0.20,
        missing_change_threshold: float = 10.0,
        record: bool = True,
        label: str | None = None,
    ) -> dict[str, Any]:
        """Detect basic schema and distribution drift using transparent heuristics."""
        if numeric_mean_threshold <= 0:
            raise ValueError("numeric_mean_threshold must be greater than 0.")
        if not 0 < categorical_tv_threshold <= 1:
            raise ValueError("categorical_tv_threshold must be greater than 0 and at most 1.")
        if missing_change_threshold < 0:
            raise ValueError("missing_change_threshold must be at least 0.")

        baseline = self.dataframe
        candidate = self._coerce_comparison_frame(other)
        schema = self.compare_schema(candidate)
        numeric: dict[str, Any] = {}
        categorical: dict[str, Any] = {}
        missing: dict[str, Any] = {}
        severities: list[str] = []

        shared = [column for column in baseline.columns if column in candidate.columns]
        for column in shared:
            b_missing = float(baseline[column].isna().mean() * 100)
            c_missing = float(candidate[column].isna().mean() * 100)
            difference = round(c_missing - b_missing, 2)
            if abs(difference) >= missing_change_threshold:
                severity = "high" if abs(difference) >= 25 else "medium"
                severities.append(severity)
                missing[str(column)] = {
                    "baseline_percentage": round(b_missing, 2),
                    "candidate_percentage": round(c_missing, 2),
                    "change_percentage_points": difference,
                    "severity": severity,
                }

            if pd.api.types.is_numeric_dtype(baseline[column]) and pd.api.types.is_numeric_dtype(candidate[column]):
                b = pd.to_numeric(baseline[column], errors="coerce").dropna()
                c = pd.to_numeric(candidate[column], errors="coerce").dropna()
                if b.empty or c.empty:
                    continue
                pooled_std = float(((b.std(ddof=0) ** 2 + c.std(ddof=0) ** 2) / 2) ** 0.5)
                mean_difference = abs(float(c.mean() - b.mean()))
                standardized = mean_difference / pooled_std if pooled_std > 0 else (0.0 if mean_difference == 0 else float("inf"))
                if standardized >= numeric_mean_threshold:
                    severity = "high" if standardized >= numeric_mean_threshold * 2 else "medium"
                    severities.append(severity)
                    numeric[str(column)] = {
                        "baseline_mean": round(float(b.mean()), 6),
                        "candidate_mean": round(float(c.mean()), 6),
                        "baseline_median": round(float(b.median()), 6),
                        "candidate_median": round(float(c.median()), 6),
                        "standardized_mean_difference": round(standardized, 6) if standardized != float("inf") else "infinity",
                        "severity": severity,
                    }
            else:
                def distribution(series: pd.Series) -> dict[str, float]:
                    normalized = series.map(
                        lambda value: "<missing>" if pd.isna(value) else self._normalize_text(str(value))
                    )
                    return normalized.value_counts(normalize=True).to_dict()
                b_dist = distribution(baseline[column])
                c_dist = distribution(candidate[column])
                categories = set(b_dist) | set(c_dist)
                tv = 0.5 * sum(abs(b_dist.get(category, 0.0) - c_dist.get(category, 0.0)) for category in categories)
                if tv >= categorical_tv_threshold:
                    severity = "high" if tv >= min(1.0, categorical_tv_threshold * 2) else "medium"
                    severities.append(severity)
                    categorical[str(column)] = {
                        "total_variation_distance": round(float(tv), 6),
                        "severity": severity,
                        "baseline_top_categories": dict(sorted(b_dist.items(), key=lambda item: item[1], reverse=True)[:5]),
                        "candidate_top_categories": dict(sorted(c_dist.items(), key=lambda item: item[1], reverse=True)[:5]),
                    }

        schema_drift = bool(schema["added_columns"] or schema["removed_columns"] or schema["dtype_changes"])
        if schema_drift:
            severities.append("high")
        overall = "high" if "high" in severities else "medium" if "medium" in severities else "none"
        baseline_rows = len(baseline)
        row_change_percentage = (
            round(((len(candidate) - baseline_rows) / baseline_rows) * 100, 2)
            if baseline_rows else None
        )
        result = {
            "drift_detected": bool(severities),
            "overall_severity": overall,
            "schema_drift": schema,
            "numeric_distribution_drift": numeric,
            "categorical_distribution_drift": categorical,
            "missingness_drift": missing,
            "row_count": {
                "baseline": int(baseline_rows),
                "candidate": int(len(candidate)),
                "change_percentage": row_change_percentage,
            },
            "thresholds": {
                "numeric_mean_threshold": numeric_mean_threshold,
                "categorical_tv_threshold": categorical_tv_threshold,
                "missing_change_threshold": missing_change_threshold,
            },
            "method_note": (
                "This is a basic heuristic drift screen, not a statistical guarantee. "
                "Investigate flagged changes with domain context."
            ),
        }
        if record:
            entry = {
                "run_id": len(self._drift_history) + 1,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "label": label,
                "overall_severity": overall,
                "drift_detected": bool(severities),
                "baseline_fingerprint": self.dataset_fingerprint(baseline),
                "candidate_fingerprint": self.dataset_fingerprint(candidate),
                "result": deepcopy(result),
            }
            self._drift_history.append(entry)
        return result

    def drift_history(self) -> list[dict[str, Any]]:
        """Return recorded drift runs as a defensive copy."""
        return deepcopy(self._drift_history)

    def clear_drift_history(self) -> int:
        """Clear recorded drift runs and return the number removed."""
        count = len(self._drift_history)
        self._drift_history.clear()
        return count

    def export_drift_history(
        self,
        path: str | Path = "axiombraid_drift_history.json",
    ) -> Path:
        """Export drift runs and privacy-safe fingerprints as JSON."""
        output = Path(path)
        if output.suffix.lower() != ".json":
            output = output.with_suffix(".json")
        output.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "run_count": len(self._drift_history),
            "runs": self.drift_history(),
        }
        with output.open("w", encoding="utf-8") as file:
            json.dump(payload, file, ensure_ascii=False, indent=2, default=str)
        return output.resolve()
