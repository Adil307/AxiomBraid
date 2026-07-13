"""Dataset fingerprints and conservative target-leakage screens."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

import pandas as pd


class GovernanceMixin:
    """Provide privacy-safe fingerprints and transparent leakage checks."""

    @staticmethod
    def _dtype_family(series: pd.Series) -> str:
        if pd.api.types.is_bool_dtype(series):
            return "boolean"
        if pd.api.types.is_datetime64_any_dtype(series):
            return "datetime"
        if pd.api.types.is_numeric_dtype(series):
            return "number"
        return "string"

    def dataset_fingerprint(
        self,
        data: Any | None = None,
        *,
        include_index: bool = True,
    ) -> dict[str, Any]:
        """Return deterministic SHA-256 fingerprints without exposing raw values."""
        frame = (
            self.dataframe.copy(deep=True)
            if data is None
            else self._coerce_comparison_frame(data)
        )
        schema_payload = {
            "columns": [str(column) for column in frame.columns],
            "dtypes": {str(column): str(frame[column].dtype) for column in frame.columns},
            "include_index": bool(include_index),
        }
        schema_bytes = json.dumps(
            schema_payload,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
        schema_hash = hashlib.sha256(schema_bytes).hexdigest()

        try:
            row_hashes = pd.util.hash_pandas_object(
                frame,
                index=include_index,
                categorize=True,
            ).astype("uint64")
        except TypeError:
            safe = frame.copy(deep=True)
            for column in safe.columns:
                safe[column] = safe[column].map(
                    lambda value: "<missing>" if pd.isna(value) else repr(value)
                )
            row_hashes = pd.util.hash_pandas_object(
                safe,
                index=include_index,
                categorize=True,
            ).astype("uint64")

        ordered_bytes = row_hashes.to_numpy().tobytes()
        ordered_content_hash = hashlib.sha256(ordered_bytes).hexdigest()
        unordered_bytes = row_hashes.sort_values().to_numpy().tobytes()
        unordered_content_hash = hashlib.sha256(unordered_bytes).hexdigest()
        combined_hash = hashlib.sha256(
            (schema_hash + ordered_content_hash).encode("ascii")
        ).hexdigest()
        return {
            "algorithm": "sha256",
            "rows": int(len(frame)),
            "columns": int(frame.shape[1]),
            "schema_hash": schema_hash,
            "ordered_content_hash": ordered_content_hash,
            "order_insensitive_content_hash": unordered_content_hash,
            "combined_hash": combined_hash,
            "include_index": bool(include_index),
            "privacy_note": (
                "Fingerprints contain hashes and metadata only; raw cell values are "
                "not included. Hash stability is intended within compatible pandas "
                "environments."
            ),
        }

    def compare_fingerprint(
        self,
        other: Any,
        *,
        include_index: bool = True,
    ) -> dict[str, Any]:
        """Compare current dataset fingerprints with another dataset."""
        baseline = self.dataset_fingerprint(include_index=include_index)
        candidate = self.dataset_fingerprint(other, include_index=include_index)
        return {
            "exact_match": baseline["combined_hash"] == candidate["combined_hash"],
            "same_schema": baseline["schema_hash"] == candidate["schema_hash"],
            "same_ordered_content": (
                baseline["ordered_content_hash"]
                == candidate["ordered_content_hash"]
            ),
            "same_content_ignoring_row_order": (
                baseline["order_insensitive_content_hash"]
                == candidate["order_insensitive_content_hash"]
            ),
            "baseline": baseline,
            "candidate": candidate,
        }

    def export_fingerprint(
        self,
        path: str | Path = "axiombraid_fingerprint.json",
        *,
        data: Any | None = None,
        include_index: bool = True,
    ) -> Path:
        """Export a privacy-safe dataset fingerprint as JSON."""
        output = Path(path)
        if output.suffix.lower() != ".json":
            output = output.with_suffix(".json")
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("w", encoding="utf-8") as file:
            json.dump(
                self.dataset_fingerprint(data, include_index=include_index),
                file,
                ensure_ascii=False,
                indent=2,
            )
        return output.resolve()

    @staticmethod
    def _comparable_series(series: pd.Series) -> pd.Series:
        if pd.api.types.is_numeric_dtype(series):
            return pd.to_numeric(series, errors="coerce")
        if pd.api.types.is_datetime64_any_dtype(series):
            return pd.to_datetime(series, errors="coerce")
        return series.map(
            lambda value: "<missing>"
            if pd.isna(value)
            else " ".join(str(value).split()).casefold()
        )

    def check_target_leakage(
        self,
        target: str,
        *,
        data: Any | None = None,
        correlation_threshold: float = 0.98,
    ) -> dict[str, Any]:
        """Screen for obvious target leakage; findings always require review."""
        if not 0 < correlation_threshold <= 1:
            raise ValueError(
                "correlation_threshold must be greater than 0 and at most 1."
            )
        frame = (
            self.dataframe.copy(deep=True)
            if data is None
            else self._coerce_comparison_frame(data)
        )
        if target not in frame.columns:
            raise ValueError(f"Target column was not found: {target}")

        issues: list[dict[str, Any]] = []
        target_series = frame[target]
        target_comparable = self._comparable_series(target_series)
        target_key = re.sub(r"[^a-z0-9]+", "_", str(target).lower()).strip("_")
        derived_tokens = {
            "copy", "encoded", "encoding", "prediction", "predicted",
            "probability", "prob", "score", "label", "output",
        }

        special = self._special_columns()
        if target in special["possible_identifiers"] or (
            self._identifier_name_hint(target)
            and target_series.dropna().is_unique
        ):
            issues.append({
                "code": "identifier_as_target",
                "severity": "high",
                "column": target,
                "message": (
                    "The target appears to be an identifier. A model may memorize "
                    "records instead of learning a generalizable outcome."
                ),
                "metric": None,
            })

        for column in frame.columns:
            column_name = str(column)
            if column_name == target:
                continue
            candidate = frame[column]
            candidate_comparable = self._comparable_series(candidate)

            equal = candidate_comparable.eq(target_comparable) | (
                candidate_comparable.isna() & target_comparable.isna()
            )
            if len(frame) and bool(equal.all()):
                issues.append({
                    "code": "exact_target_copy",
                    "severity": "high",
                    "column": column_name,
                    "message": "The column is an exact copy of the target.",
                    "metric": 1.0,
                })
                continue

            cleaned_name = re.sub(
                r"[^a-z0-9]+", "_", column_name.lower()
            ).strip("_")
            name_tokens = set(cleaned_name.split("_"))
            if target_key and target_key in cleaned_name and name_tokens & derived_tokens:
                issues.append({
                    "code": "target_derived_name",
                    "severity": "medium",
                    "column": column_name,
                    "message": (
                        "The column name suggests it may have been derived from the "
                        "target or from a model output."
                    ),
                    "metric": None,
                })

            if (
                pd.api.types.is_numeric_dtype(target_series)
                and pd.api.types.is_numeric_dtype(candidate)
            ):
                pair = pd.DataFrame({
                    "target": pd.to_numeric(target_series, errors="coerce"),
                    "candidate": pd.to_numeric(candidate, errors="coerce"),
                }).dropna()
                if len(pair) >= 3 and pair["target"].nunique() > 1 and pair["candidate"].nunique() > 1:
                    correlation = float(pair["target"].corr(pair["candidate"]))
                    if pd.notna(correlation) and abs(correlation) >= correlation_threshold:
                        issues.append({
                            "code": "near_perfect_target_correlation",
                            "severity": "high" if abs(correlation) >= 0.999 else "medium",
                            "column": column_name,
                            "message": (
                                "The column has near-perfect numerical correlation "
                                "with the target and may contain leaked outcome information."
                            ),
                            "metric": round(abs(correlation), 6),
                        })

        severity_order = {"high": 0, "medium": 1, "low": 2, "info": 3}
        issues.sort(key=lambda item: (severity_order[item["severity"]], item["code"], item["column"]))
        counts = {
            severity: sum(issue["severity"] == severity for issue in issues)
            for severity in severity_order
        }
        return {
            "target": target,
            "leakage_risk_detected": bool(issues),
            "issue_count": len(issues),
            "severity_counts": counts,
            "issues": issues,
            "correlation_threshold": correlation_threshold,
            "method_note": (
                "This is a conservative leakage screen, not proof of leakage. "
                "Validate every finding using feature timing and domain knowledge."
            ),
        }

    def export_leakage_report(
        self,
        target: str,
        path: str | Path = "axiombraid_leakage_report.json",
        *,
        data: Any | None = None,
        correlation_threshold: float = 0.98,
    ) -> Path:
        """Export a conservative target-leakage screen as JSON."""
        output = Path(path)
        if output.suffix.lower() != ".json":
            output = output.with_suffix(".json")
        output.parent.mkdir(parents=True, exist_ok=True)
        payload = self.check_target_leakage(
            target,
            data=data,
            correlation_threshold=correlation_threshold,
        )
        with output.open("w", encoding="utf-8") as file:
            json.dump(payload, file, ensure_ascii=False, indent=2, default=str)
        return output.resolve()
