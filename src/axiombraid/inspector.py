"""Core dataset inspection tools for AxiomBraid."""

from __future__ import annotations

import json
import re
from copy import deepcopy
from html import escape
from pathlib import Path
from typing import Any

import pandas as pd

from ._version import __version__
from .cleaning import CleaningMixin
from .comparison import ComparisonMixin
from .governance import GovernanceMixin
from .validation import ValidationMixin
from .config import ConfigMixin
from .performance import PerformanceMixin
from .plugins import PluginMixin
from .themes import get_theme


class DataGuide(
    CleaningMixin, ComparisonMixin, ValidationMixin, GovernanceMixin,
    ConfigMixin, PerformanceMixin, PluginMixin,
):
    """Load and inspect a dataset without modifying the original data."""

    def __init__(
        self,
        data: str | Path | pd.DataFrame,
        *,
        high_cardinality_threshold: float = 0.90,
        min_unique_for_high_cardinality: int = 3,
        structured_identifier_threshold: float = 0.80,
        low_missing_threshold: float = 5.0,
        high_missing_threshold: float = 30.0,
        outlier_iqr_multiplier: float = 1.5,
        min_outlier_sample_size: int = 4,
        date_like_threshold: float = 0.80,
        min_date_like_non_missing: int = 3,
    ) -> None:
        self._validate_configuration(
            high_cardinality_threshold=high_cardinality_threshold,
            min_unique_for_high_cardinality=min_unique_for_high_cardinality,
            structured_identifier_threshold=structured_identifier_threshold,
            low_missing_threshold=low_missing_threshold,
            high_missing_threshold=high_missing_threshold,
            outlier_iqr_multiplier=outlier_iqr_multiplier,
            min_outlier_sample_size=min_outlier_sample_size,
            date_like_threshold=date_like_threshold,
            min_date_like_non_missing=min_date_like_non_missing,
        )
        self.high_cardinality_threshold = float(high_cardinality_threshold)
        self.min_unique_for_high_cardinality = int(min_unique_for_high_cardinality)
        self.structured_identifier_threshold = float(structured_identifier_threshold)
        self.low_missing_threshold = float(low_missing_threshold)
        self.high_missing_threshold = float(high_missing_threshold)
        self.outlier_iqr_multiplier = float(outlier_iqr_multiplier)
        self.min_outlier_sample_size = int(min_outlier_sample_size)
        self.date_like_threshold = float(date_like_threshold)
        self.min_date_like_non_missing = int(min_date_like_non_missing)
        self.source = data
        self.dataframe = self._load_data(data).copy(deep=True)
        self._cleaning_history: list[pd.DataFrame] = []
        self._last_cleaning_result: dict[str, Any] | None = None
        self._cleaning_audit_log: list[dict[str, Any]] = []
        self._drift_history: list[dict[str, Any]] = []
        self._plugins: dict[str, Any] = {}
        self._runtime_config: dict[str, Any] | None = None
        rows = int(len(self.dataframe))
        self._sampling_metadata: dict[str, Any] = {
            "requested_mode": "full",
            "effective_mode": "full",
            "sampled": False,
            "strategy": None,
            "full_rows": rows,
            "analyzed_rows": rows,
            "sample_fraction": 1.0 if rows else 0.0,
            "random_state": None,
            "warning": None,
        }

    @staticmethod
    def _validate_configuration(
        *,
        high_cardinality_threshold: float,
        min_unique_for_high_cardinality: int,
        structured_identifier_threshold: float,
        low_missing_threshold: float,
        high_missing_threshold: float,
        outlier_iqr_multiplier: float,
        min_outlier_sample_size: int,
        date_like_threshold: float,
        min_date_like_non_missing: int,
    ) -> None:
        if not 0 < high_cardinality_threshold <= 1:
            raise ValueError(
                "high_cardinality_threshold must be greater than 0 and at most 1."
            )
        if (
            not isinstance(min_unique_for_high_cardinality, int)
            or min_unique_for_high_cardinality < 2
        ):
            raise ValueError(
                "min_unique_for_high_cardinality must be an integer of at least 2."
            )
        if not 0 < structured_identifier_threshold <= 1:
            raise ValueError(
                "structured_identifier_threshold must be greater than 0 and at most 1."
            )
        if not 0 <= low_missing_threshold < high_missing_threshold <= 100:
            raise ValueError(
                "Missing thresholds must satisfy 0 <= low < high <= 100."
            )
        if outlier_iqr_multiplier <= 0:
            raise ValueError("outlier_iqr_multiplier must be greater than 0.")
        if (
            not isinstance(min_outlier_sample_size, int)
            or min_outlier_sample_size < 4
        ):
            raise ValueError(
                "min_outlier_sample_size must be an integer of at least 4."
            )
        if not 0 < date_like_threshold <= 1:
            raise ValueError(
                "date_like_threshold must be greater than 0 and at most 1."
            )
        if (
            not isinstance(min_date_like_non_missing, int)
            or min_date_like_non_missing < 2
        ):
            raise ValueError(
                "min_date_like_non_missing must be an integer of at least 2."
            )

    @staticmethod
    def _load_data(data: str | Path | pd.DataFrame) -> pd.DataFrame:
        if isinstance(data, pd.DataFrame):
            return data
        if not isinstance(data, (str, Path)):
            raise TypeError(
                "Data must be a CSV/Excel path or a pandas DataFrame."
            )

        path = Path(data)
        if not path.exists():
            raise FileNotFoundError(f"Dataset not found: {path}")
        if not path.is_file():
            raise ValueError(f"The provided path is not a file: {path}")

        extension = path.suffix.lower()
        try:
            if extension == ".csv":
                return pd.read_csv(path)
            if extension in {".xlsx", ".xls"}:
                return pd.read_excel(path)
        except Exception as exc:
            raise ValueError(
                f"AxiomBraid could not read '{path.name}': {exc}"
            ) from exc

        raise ValueError(
            "Unsupported file type. Use CSV (.csv), Excel (.xlsx/.xls), "
            "or a pandas DataFrame."
        )

    @staticmethod
    def _language_code(language: str) -> str:
        normalized = language.strip().lower().replace("-", "_").replace(" ", "_")
        if normalized in {"en", "english"}:
            return "en"
        if normalized in {"ur", "roman_urdu", "romanurdu"}:
            return "roman_urdu"
        raise ValueError("Unsupported language. Use 'en' or 'roman_urdu'.")

    def _configuration(self) -> dict[str, float | int]:
        return {
            "high_cardinality_threshold": self.high_cardinality_threshold,
            "min_unique_for_high_cardinality": self.min_unique_for_high_cardinality,
            "structured_identifier_threshold": self.structured_identifier_threshold,
            "low_missing_threshold": self.low_missing_threshold,
            "high_missing_threshold": self.high_missing_threshold,
            "outlier_iqr_multiplier": self.outlier_iqr_multiplier,
            "min_outlier_sample_size": self.min_outlier_sample_size,
            "date_like_threshold": self.date_like_threshold,
            "min_date_like_non_missing": self.min_date_like_non_missing,
        }

    def _column_groups(self) -> dict[str, list[str]]:
        numerical = (
            self.dataframe.select_dtypes(include="number")
            .columns.astype(str)
            .tolist()
        )
        boolean = (
            self.dataframe.select_dtypes(include="bool")
            .columns.astype(str)
            .tolist()
        )
        datetime = (
            self.dataframe.select_dtypes(include=["datetime64", "datetimetz"])
            .columns.astype(str)
            .tolist()
        )
        excluded = set(numerical + boolean + datetime)
        categorical = [
            str(column)
            for column in self.dataframe.columns
            if str(column) not in excluded
        ]
        return {
            "numerical": numerical,
            "categorical": categorical,
            "boolean": boolean,
            "datetime": datetime,
        }

    @staticmethod
    def _normalize_text(value: str) -> str:
        return " ".join(value.split()).casefold()

    def _normalized_unique_count(self, series: pd.Series) -> int:
        values = series.dropna()
        if values.empty:
            return 0
        if pd.api.types.is_object_dtype(values.dtype) or isinstance(
            values.dtype, pd.StringDtype
        ):
            normalized = values.astype(str).map(self._normalize_text)
            return int(normalized.nunique(dropna=True))
        return int(values.nunique(dropna=True))

    @staticmethod
    def _identifier_name_hint(column_name: str) -> bool:
        cleaned = re.sub(
            r"[^a-z0-9]+", "_", column_name.strip().lower()
        ).strip("_")
        exact_names = {
            "id",
            "uuid",
            "guid",
            "identifier",
            "index",
            "roll_no",
            "roll_number",
            "registration_no",
            "registration_number",
            "serial_no",
            "serial_number",
        }
        if cleaned in exact_names:
            return True
        return cleaned.endswith(
            ("_id", "_uuid", "_guid", "_code", "_number", "_no", "_key")
        ) or cleaned.startswith(("id_", "code_"))

    @staticmethod
    def _structured_identifier_ratio(series: pd.Series) -> float:
        values = series.dropna().astype(str).str.strip()
        if values.empty:
            return 0.0

        uuid_pattern = re.compile(
            r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-"
            r"[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$"
        )
        letter_digit_pattern = re.compile(
            r"^(?=.*[A-Za-z])(?=.*\d)[A-Za-z0-9_-]+$"
        )
        separated_code_pattern = re.compile(
            r"^[A-Za-z0-9]+(?:[-_][A-Za-z0-9]+)+$"
        )
        matched = sum(
            1
            for value in values
            if uuid_pattern.fullmatch(value)
            or letter_digit_pattern.fullmatch(value)
            or separated_code_pattern.fullmatch(value)
        )
        return matched / len(values)

    def _special_columns(self) -> dict[str, list[str]]:
        constant: list[str] = []
        possible_identifiers: list[str] = []
        descriptive: list[str] = []

        analysis_frame = self.dataframe.drop_duplicates()
        numerical_names = set(
            analysis_frame.select_dtypes(include="number")
            .columns.astype(str)
            .tolist()
        )

        for column in analysis_frame.columns:
            column_name = str(column)
            series = analysis_frame[column]
            non_missing_count = int(series.notna().sum())
            unique_count = self._normalized_unique_count(series)

            if unique_count <= 1:
                constant.append(column_name)
                continue
            if non_missing_count == 0:
                continue

            uniqueness_ratio = unique_count / non_missing_count
            is_high = (
                unique_count >= self.min_unique_for_high_cardinality
                and uniqueness_ratio >= self.high_cardinality_threshold
            )
            if not is_high:
                continue

            has_name_hint = self._identifier_name_hint(column_name)
            has_structured_values = (
                self._structured_identifier_ratio(series)
                >= self.structured_identifier_threshold
            )
            date_structure_ratio = (
                series.dropna().astype(str).map(self._looks_date_structured).mean()
                if int(series.notna().sum())
                else 0.0
            )
            likely_date_text = (
                self._date_name_hint(column_name)
                or date_structure_ratio >= self.date_like_threshold
            )
            if likely_date_text:
                continue
            if has_name_hint or (
                column_name not in numerical_names and has_structured_values
            ):
                possible_identifiers.append(column_name)
            elif column_name not in numerical_names:
                descriptive.append(column_name)

        return {
            "constant": constant,
            "possible_identifiers": possible_identifiers,
            "high_cardinality_descriptive": descriptive,
        }

    def _text_inconsistencies(self) -> dict[str, list[dict[str, Any]]]:
        issues: dict[str, list[dict[str, Any]]] = {}
        for column_name in self._column_groups()["categorical"]:
            series = self.dataframe[column_name].dropna()
            if series.empty:
                continue

            groups: dict[str, set[str]] = {}
            for value in series.astype(str):
                groups.setdefault(self._normalize_text(value), set()).add(value)

            column_issues: list[dict[str, Any]] = []
            for normalized, variants_set in groups.items():
                variants = sorted(variants_set)
                has_spacing_issue = any(
                    variant != " ".join(variant.split()) for variant in variants
                )
                if len(variants) > 1 or has_spacing_issue:
                    column_issues.append(
                        {"normalized_value": normalized, "variants": variants}
                    )
            if column_issues:
                issues[column_name] = column_issues
        return issues

    def _missing_values(self) -> dict[str, dict[str, float | int]]:
        rows = len(self.dataframe)
        result: dict[str, dict[str, float | int]] = {}
        for column in self.dataframe.columns:
            count = int(self.dataframe[column].isna().sum())
            result[str(column)] = {
                "count": count,
                "percentage": round((count / rows) * 100, 2) if rows else 0.0,
            }
        return result

    def _numerical_summary(self) -> dict[str, dict[str, Any]]:
        numerical = self.dataframe.select_dtypes(include="number")
        if numerical.empty:
            return {}
        summary = numerical.describe().round(3)
        return {
            str(column): {
                str(statistic): self._python_value(value)
                for statistic, value in summary[column].items()
            }
            for column in summary.columns
        }

    @staticmethod
    def _python_value(value: Any) -> Any:
        if pd.isna(value):
            return None
        if hasattr(value, "item"):
            return value.item()
        return value

    def _outliers(self) -> dict[str, dict[str, Any]]:
        """Detect potential numerical outliers using the IQR rule."""
        results: dict[str, dict[str, Any]] = {}
        identifiers = set(self._special_columns()["possible_identifiers"])

        for column in self._column_groups()["numerical"]:
            if column in identifiers:
                continue
            series = pd.to_numeric(self.dataframe[column], errors="coerce").dropna()
            if len(series) < self.min_outlier_sample_size:
                continue

            q1 = float(series.quantile(0.25))
            q3 = float(series.quantile(0.75))
            iqr = q3 - q1
            lower = q1 - self.outlier_iqr_multiplier * iqr
            upper = q3 + self.outlier_iqr_multiplier * iqr
            mask = (series < lower) | (series > upper)
            detected = series[mask]
            if detected.empty:
                continue

            results[column] = {
                "method": "iqr",
                "iqr_multiplier": self.outlier_iqr_multiplier,
                "q1": round(q1, 6),
                "q3": round(q3, 6),
                "lower_bound": round(lower, 6),
                "upper_bound": round(upper, 6),
                "count": int(mask.sum()),
                "percentage": round((int(mask.sum()) / len(series)) * 100, 2),
                "example_values": [
                    self._python_value(value)
                    for value in detected.head(10).tolist()
                ],
            }
        return results

    @staticmethod
    def _numeric_range_rule(column_name: str) -> dict[str, Any] | None:
        """Infer conservative expected numeric ranges from common column names."""
        cleaned = re.sub(
            r"[^a-z0-9]+", "_", column_name.strip().lower()
        ).strip("_")
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
            {
                "percentage",
                "percent",
                "pct",
                "attendance",
                "marks",
                "mark",
                "score",
                "grade",
            }
        ):
            return {"name": "percentage_or_score", "minimum": 0.0, "maximum": 100.0}
        if tokens.intersection({"probability", "prob"}):
            return {"name": "probability", "minimum": 0.0, "maximum": 1.0}
        return None

    def _numeric_range_issues(self) -> dict[str, dict[str, Any]]:
        """Detect values outside conservative ranges inferred from column names."""
        results: dict[str, dict[str, Any]] = {}
        identifiers = set(self._special_columns()["possible_identifiers"])

        for column in self._column_groups()["numerical"]:
            if column in identifiers:
                continue
            rule = self._numeric_range_rule(column)
            if rule is None:
                continue

            series = pd.to_numeric(self.dataframe[column], errors="coerce").dropna()
            if series.empty:
                continue
            mask = (series < rule["minimum"]) | (series > rule["maximum"])
            invalid = series[mask]
            if invalid.empty:
                continue

            results[column] = {
                "rule": rule["name"],
                "expected_minimum": rule["minimum"],
                "expected_maximum": rule["maximum"],
                "count": int(mask.sum()),
                "percentage": round((int(mask.sum()) / len(series)) * 100, 2),
                "example_values": [
                    self._python_value(value)
                    for value in invalid.head(10).tolist()
                ],
            }
        return results

    @staticmethod
    def _date_name_hint(column_name: str) -> bool:
        cleaned = re.sub(
            r"[^a-z0-9]+", "_", column_name.strip().lower()
        ).strip("_")
        tokens = set(cleaned.split("_"))
        return bool(
            tokens.intersection(
                {"date", "datetime", "timestamp", "dob", "birthdate", "birthday"}
            )
        )

    @staticmethod
    def _looks_date_structured(value: str) -> bool:
        text = value.strip()
        if not text:
            return False
        if re.search(r"\d{1,4}[-/.]\d{1,2}[-/.]\d{1,4}", text):
            return True
        month_pattern = (
            r"\b(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|"
            r"jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|"
            r"nov(?:ember)?|dec(?:ember)?)\b"
        )
        return bool(re.search(month_pattern, text, flags=re.IGNORECASE))

    def _date_like_text_columns(self) -> dict[str, dict[str, Any]]:
        """Detect text columns whose values are mostly parseable dates."""
        results: dict[str, dict[str, Any]] = {}

        for column in self._column_groups()["categorical"]:
            if self._identifier_name_hint(column):
                continue
            series = self.dataframe[column].dropna().astype(str).str.strip()
            series = series[series.ne("")]
            if len(series) < self.min_date_like_non_missing:
                continue

            structured = series.map(self._looks_date_structured)
            candidate_series = series[structured]
            if candidate_series.empty:
                continue

            try:
                parsed = pd.to_datetime(
                    candidate_series,
                    errors="coerce",
                    format="mixed",
                )
            except TypeError:
                parsed = pd.to_datetime(candidate_series, errors="coerce")

            parsed_count = int(parsed.notna().sum())
            parse_ratio = parsed_count / len(series)
            if parse_ratio < self.date_like_threshold:
                continue

            results[column] = {
                "non_missing_count": int(len(series)),
                "parsed_count": parsed_count,
                "parse_percentage": round(parse_ratio * 100, 2),
                "suggested_dtype": "datetime64[ns]",
                "example_values": series.head(5).tolist(),
            }
        return results

    @staticmethod
    def _quality_rating(score: float) -> str:
        if score >= 90:
            return "excellent"
        if score >= 75:
            return "good"
        if score >= 50:
            return "needs_attention"
        return "poor"

    def _column_quality(self) -> dict[str, dict[str, Any]]:
        """Calculate transparent quality scores for individual columns."""
        missing = self._missing_values()
        special = self._special_columns()
        text_issues = self._text_inconsistencies()
        outliers = self._outliers()
        range_issues = self._numeric_range_issues()
        date_like = self._date_like_text_columns()
        constant = set(special["constant"])
        scores: dict[str, dict[str, Any]] = {}

        for column in self.dataframe.columns:
            name = str(column)
            penalties = {
                "missing_values": round(
                    min(40.0, float(missing[name]["percentage"]) * 0.80), 2
                ),
                "constant_column": 20.0 if name in constant else 0.0,
                "text_inconsistency": 10.0 if name in text_issues else 0.0,
                "outliers": round(
                    min(15.0, float(outliers.get(name, {}).get("percentage", 0)) * 0.50),
                    2,
                ),
                "numeric_range": round(
                    min(
                        20.0,
                        float(range_issues.get(name, {}).get("percentage", 0)) * 0.80,
                    ),
                    2,
                ),
                "date_stored_as_text": 5.0 if name in date_like else 0.0,
            }
            score = round(max(0.0, 100.0 - sum(penalties.values())), 2)
            scores[name] = {
                "score": score,
                "rating": self._quality_rating(score),
                "penalties": penalties,
            }
        return scores

    def _quality_metrics(self) -> dict[str, float | int]:
        rows, columns = self.dataframe.shape
        total_cells = rows * columns
        missing_cells = int(self.dataframe.isna().sum().sum())
        duplicate_rows = int(self.dataframe.duplicated().sum())
        special = self._special_columns()
        text_issues = self._text_inconsistencies()
        outliers = self._outliers()
        range_issues = self._numeric_range_issues()
        date_like = self._date_like_text_columns()
        categorical_count = len(self._column_groups()["categorical"])
        numerical_count = len(self._column_groups()["numerical"])

        return {
            "total_cells": int(total_cells),
            "missing_cells": missing_cells,
            "missing_percentage": (
                round((missing_cells / total_cells) * 100, 2)
                if total_cells
                else 0.0
            ),
            "duplicate_rows": duplicate_rows,
            "duplicate_percentage": (
                round((duplicate_rows / rows) * 100, 2) if rows else 0.0
            ),
            "constant_columns": len(special["constant"]),
            "constant_column_percentage": (
                round((len(special["constant"]) / columns) * 100, 2)
                if columns
                else 0.0
            ),
            "text_inconsistency_columns": len(text_issues),
            "text_inconsistency_percentage": (
                round((len(text_issues) / categorical_count) * 100, 2)
                if categorical_count
                else 0.0
            ),
            "outlier_columns": len(outliers),
            "outlier_column_percentage": (
                round((len(outliers) / numerical_count) * 100, 2)
                if numerical_count
                else 0.0
            ),
            "numeric_range_issue_columns": len(range_issues),
            "numeric_range_issue_percentage": (
                round((len(range_issues) / numerical_count) * 100, 2)
                if numerical_count
                else 0.0
            ),
            "date_like_text_columns": len(date_like),
            "date_like_text_percentage": (
                round((len(date_like) / categorical_count) * 100, 2)
                if categorical_count
                else 0.0
            ),
        }

    def _data_quality(self) -> dict[str, Any]:
        rows, columns = self.dataframe.shape
        metrics = self._quality_metrics()
        if rows == 0 or columns == 0:
            return {
                "score": 0.0,
                "rating": "poor",
                "penalties": {
                    "missing_values": 0.0,
                    "duplicates": 0.0,
                    "constant_columns": 0.0,
                    "text_inconsistencies": 0.0,
                    "outliers": 0.0,
                    "numeric_ranges": 0.0,
                    "date_stored_as_text": 0.0,
                    "empty_dataset": 100.0,
                },
                "metrics": metrics,
            }

        penalties = {
            "missing_values": round(
                min(35.0, float(metrics["missing_percentage"]) * 0.70), 2
            ),
            "duplicates": round(
                min(20.0, float(metrics["duplicate_percentage"]) * 0.40), 2
            ),
            "constant_columns": round(
                min(15.0, float(metrics["constant_column_percentage"]) * 0.15), 2
            ),
            "text_inconsistencies": round(
                min(10.0, float(metrics["text_inconsistency_percentage"]) * 0.10), 2
            ),
            "outliers": round(
                min(8.0, float(metrics["outlier_column_percentage"]) * 0.08), 2
            ),
            "numeric_ranges": round(
                min(10.0, float(metrics["numeric_range_issue_percentage"]) * 0.10), 2
            ),
            "date_stored_as_text": round(
                min(5.0, float(metrics["date_like_text_percentage"]) * 0.05), 2
            ),
            "empty_dataset": 0.0,
        }
        score = round(max(0.0, 100.0 - sum(penalties.values())), 2)
        return {
            "score": score,
            "rating": self._quality_rating(score),
            "penalties": penalties,
            "metrics": metrics,
        }

    def _issues(self, language: str = "en") -> list[dict[str, Any]]:
        language_code = self._language_code(language)
        issues: list[dict[str, Any]] = []
        missing = self._missing_values()
        duplicate_count = int(self.dataframe.duplicated().sum())
        duplicate_percentage = float(self._quality_metrics()["duplicate_percentage"])
        special = self._special_columns()
        text_issues = self._text_inconsistencies()
        outliers = self._outliers()
        range_issues = self._numeric_range_issues()
        date_like = self._date_like_text_columns()
        rows, columns = self.dataframe.shape

        affected_missing = [
            column for column, details in missing.items() if details["count"] > 0
        ]
        if affected_missing:
            max_percentage = max(
                float(missing[column]["percentage"])
                for column in affected_missing
            )
            severity = (
                "high"
                if max_percentage >= self.high_missing_threshold
                else "medium"
                if max_percentage >= self.low_missing_threshold
                else "low"
            )
            issues.append(
                {
                    "code": "missing_values",
                    "severity": severity,
                    "message": (
                        "Missing values were detected."
                        if language_code == "en"
                        else "Missing values detect hui hain."
                    ),
                    "columns": affected_missing,
                    "metric": max_percentage,
                    "metric_name": "maximum_column_missing_percentage",
                }
            )

        if duplicate_count:
            severity = (
                "high"
                if duplicate_percentage >= 20
                else "medium"
                if duplicate_percentage >= 5
                else "low"
            )
            issues.append(
                {
                    "code": "duplicate_rows",
                    "severity": severity,
                    "message": (
                        "Duplicate rows were detected."
                        if language_code == "en"
                        else "Duplicate rows detect hui hain."
                    ),
                    "columns": [],
                    "metric": duplicate_percentage,
                    "metric_name": "duplicate_row_percentage",
                }
            )

        if special["constant"]:
            severity = (
                "high"
                if columns and len(special["constant"]) / columns >= 0.50
                else "medium"
            )
            issues.append(
                {
                    "code": "constant_columns",
                    "severity": severity,
                    "message": (
                        "Constant columns may provide little analytical value."
                        if language_code == "en"
                        else "Constant columns analysis mein kam value deti hain."
                    ),
                    "columns": special["constant"],
                    "metric": len(special["constant"]),
                    "metric_name": "constant_column_count",
                }
            )

        if text_issues:
            issues.append(
                {
                    "code": "text_inconsistencies",
                    "severity": "medium",
                    "message": (
                        "Inconsistent text forms were detected."
                        if language_code == "en"
                        else "Text ki inconsistent forms detect hui hain."
                    ),
                    "columns": list(text_issues),
                    "metric": len(text_issues),
                    "metric_name": "affected_column_count",
                }
            )

        if outliers:
            maximum = max(float(item["percentage"]) for item in outliers.values())
            severity = "high" if maximum >= 20 else "medium" if maximum >= 5 else "low"
            issues.append(
                {
                    "code": "potential_outliers",
                    "severity": severity,
                    "message": (
                        "Potential numerical outliers were detected using the IQR rule."
                        if language_code == "en"
                        else "IQR rule se possible numerical outliers detect huay hain."
                    ),
                    "columns": list(outliers),
                    "metric": maximum,
                    "metric_name": "maximum_column_outlier_percentage",
                }
            )

        if range_issues:
            maximum = max(float(item["percentage"]) for item in range_issues.values())
            severity = "high" if maximum >= 20 else "medium" if maximum >= 5 else "low"
            issues.append(
                {
                    "code": "suspicious_numeric_ranges",
                    "severity": severity,
                    "message": (
                        "Values outside conservative expected numeric ranges were detected."
                        if language_code == "en"
                        else "Expected numeric range se bahar values detect hui hain."
                    ),
                    "columns": list(range_issues),
                    "metric": maximum,
                    "metric_name": "maximum_invalid_range_percentage",
                }
            )

        if date_like:
            issues.append(
                {
                    "code": "date_like_text",
                    "severity": "info",
                    "message": (
                        "Text columns that appear to contain dates were detected."
                        if language_code == "en"
                        else "Text columns mein date jaisi values detect hui hain."
                    ),
                    "columns": list(date_like),
                    "metric": len(date_like),
                    "metric_name": "date_like_text_column_count",
                }
            )

        if special["possible_identifiers"]:
            issues.append(
                {
                    "code": "possible_identifiers",
                    "severity": "info",
                    "message": (
                        "Possible identifier columns were detected."
                        if language_code == "en"
                        else "Possible identifier columns detect hui hain."
                    ),
                    "columns": special["possible_identifiers"],
                    "metric": len(special["possible_identifiers"]),
                    "metric_name": "identifier_column_count",
                }
            )

        if special["high_cardinality_descriptive"]:
            issues.append(
                {
                    "code": "high_cardinality_descriptive",
                    "severity": "info",
                    "message": (
                        "Descriptive columns with many unique values were detected."
                        if language_code == "en"
                        else "Zyada unique values wali descriptive columns detect hui hain."
                    ),
                    "columns": special["high_cardinality_descriptive"],
                    "metric": len(special["high_cardinality_descriptive"]),
                    "metric_name": "affected_column_count",
                }
            )

        if rows == 0 or columns == 0:
            issues.append(
                {
                    "code": "empty_dataset",
                    "severity": "high",
                    "message": (
                        "The dataset is empty."
                        if language_code == "en"
                        else "Dataset khali hai."
                    ),
                    "columns": [],
                    "metric": 0,
                    "metric_name": "row_count",
                }
            )

        if self.dataframe.select_dtypes(include="number").columns.empty:
            issues.append(
                {
                    "code": "no_numerical_columns",
                    "severity": "info",
                    "message": (
                        "No numerical columns were detected."
                        if language_code == "en"
                        else "Koi numerical column detect nahi hui."
                    ),
                    "columns": [],
                    "metric": 0,
                    "metric_name": "numerical_column_count",
                }
            )

        severity_order = {"high": 0, "medium": 1, "low": 2, "info": 3}
        return sorted(
            issues,
            key=lambda issue: (severity_order[issue["severity"]], issue["code"]),
        )

    def _recommendations(self, language: str = "en") -> list[str]:
        language_code = self._language_code(language)
        missing = self._missing_values()
        duplicate_count = int(self.dataframe.duplicated().sum())
        special = self._special_columns()
        text_issues = self._text_inconsistencies()
        outliers = self._outliers()
        range_issues = self._numeric_range_issues()
        date_like = self._date_like_text_columns()
        affected = [
            column for column, details in missing.items() if details["count"] > 0
        ]
        recommendations: list[str] = []

        if language_code == "en":
            recommendations.append(
                "Review missing values in: " + ", ".join(affected) + "."
                if affected
                else "No missing values were detected."
            )
            recommendations.append(
                f"Review {duplicate_count} duplicate row(s) before analysis."
                if duplicate_count
                else "No duplicate rows were detected."
            )
            if special["constant"]:
                recommendations.append(
                    "Constant columns may not provide useful analytical information: "
                    + ", ".join(special["constant"])
                    + "."
                )
            if special["possible_identifiers"]:
                recommendations.append(
                    "Possible identifier columns should usually not be used directly "
                    "as Machine Learning features: "
                    + ", ".join(special["possible_identifiers"])
                    + "."
                )
            if special["high_cardinality_descriptive"]:
                recommendations.append(
                    "Review descriptive columns with many unique values: "
                    + ", ".join(special["high_cardinality_descriptive"])
                    + "."
                )
            if text_issues:
                recommendations.append(
                    "Standardize inconsistent text in: "
                    + ", ".join(text_issues)
                    + "."
                )
            if outliers:
                recommendations.append(
                    "Investigate potential outliers before removing or changing them: "
                    + ", ".join(outliers)
                    + "."
                )
            if range_issues:
                recommendations.append(
                    "Validate values that fall outside expected ranges in: "
                    + ", ".join(range_issues)
                    + "."
                )
            if date_like:
                recommendations.append(
                    "Consider converting these text columns to datetime: "
                    + ", ".join(date_like)
                    + "."
                )
        else:
            recommendations.append(
                "In columns ki missing values review karein: "
                + ", ".join(affected)
                + "."
                if affected
                else "Koi missing value detect nahi hui."
            )
            recommendations.append(
                f"Analysis se pehle {duplicate_count} duplicate row(s) review karein."
                if duplicate_count
                else "Koi duplicate row detect nahi hui."
            )
            if special["constant"]:
                recommendations.append(
                    "Constant columns analysis mein zyada useful information nahi detin: "
                    + ", ".join(special["constant"])
                    + "."
                )
            if special["possible_identifiers"]:
                recommendations.append(
                    "Possible identifier columns ko Machine Learning feature ke taur "
                    "par direct use na karein: "
                    + ", ".join(special["possible_identifiers"])
                    + "."
                )
            if special["high_cardinality_descriptive"]:
                recommendations.append(
                    "Zyada unique values wali descriptive columns review karein: "
                    + ", ".join(special["high_cardinality_descriptive"])
                    + "."
                )
            if text_issues:
                recommendations.append(
                    "In columns ka inconsistent text standardize karein: "
                    + ", ".join(text_issues)
                    + "."
                )
            if outliers:
                recommendations.append(
                    "Outliers ko remove ya change karne se pehle investigate karein: "
                    + ", ".join(outliers)
                    + "."
                )
            if range_issues:
                recommendations.append(
                    "Expected range se bahar values validate karein: "
                    + ", ".join(range_issues)
                    + "."
                )
            if date_like:
                recommendations.append(
                    "In text columns ko datetime mein convert karne par ghour karein: "
                    + ", ".join(date_like)
                    + "."
                )
        return recommendations

    def inspect(self, language: str = "en") -> dict[str, Any]:
        language_code = self._language_code(language)
        result = {
            "language": language_code,
            "configuration": self._configuration(),
            "performance": deepcopy(self._sampling_metadata),
            "shape": {
                "rows": int(self.dataframe.shape[0]),
                "columns": int(self.dataframe.shape[1]),
            },
            "column_names": [str(column) for column in self.dataframe.columns],
            "data_types": {
                str(column): str(dtype)
                for column, dtype in self.dataframe.dtypes.items()
            },
            "column_groups": self._column_groups(),
            "special_columns": self._special_columns(),
            "text_inconsistencies": self._text_inconsistencies(),
            "missing_values": self._missing_values(),
            "duplicate_rows": int(self.dataframe.duplicated().sum()),
            "numerical_summary": self._numerical_summary(),
            "outliers": self._outliers(),
            "numeric_range_issues": self._numeric_range_issues(),
            "date_like_text_columns": self._date_like_text_columns(),
            "column_quality": self._column_quality(),
            "data_quality": self._data_quality(),
            "issues": self._issues(language_code),
            "cleaning_plan": self.cleaning_plan(),
            "dataset_fingerprint": self.dataset_fingerprint(),
            "recommendations": self._recommendations(language_code),
        }
        plugin_context = {
            "language": language_code,
            "shape": deepcopy(result["shape"]),
            "data_quality": deepcopy(result["data_quality"]),
            "issues": deepcopy(result["issues"]),
            "performance": deepcopy(result["performance"]),
        }
        result["plugin_results"] = self.run_plugins(context=plugin_context)
        return result

    def export_json(
        self,
        path: str | Path = "axiombraid_report.json",
        language: str = "en",
        *,
        include_confidence: bool = False,
        confidence_config: dict[str, Any] | None = None,
        include_quality_profile: bool = False,
        quality_config: dict[str, Any] | None = None,
    ) -> Path:
        """Export a machine-readable JSON report with optional V2 enhancements."""
        output_path = Path(path)
        if output_path.suffix.lower() != ".json":
            output_path = output_path.with_suffix(".json")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        result = self.inspect(language=language)
        if include_confidence:
            from .confidence import add_confidence

            result = add_confidence(result, config=confidence_config)
        if include_quality_profile:
            from .scoring_v2 import build_quality_profile

            result["quality_profile"] = build_quality_profile(
                self.dataframe, result, config=quality_config
            )
        with output_path.open("w", encoding="utf-8") as file:
            json.dump(
                result,
                file,
                ensure_ascii=False,
                indent=2,
                default=str,
            )
        return output_path.resolve()

    @staticmethod
    def _html_list(items: list[str], empty_text: str) -> str:
        return (
            ", ".join(escape(item) for item in items)
            if items
            else f"<span>{escape(empty_text)}</span>"
        )

    @staticmethod
    def _safe_filename(value: str) -> str:
        cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("._")
        return cleaned or "column"

    def export_charts(
        self,
        output_directory: str | Path = "axiombraid_charts",
        *,
        max_categories: int = 10,
        max_charts: int | None = None,
    ) -> list[Path]:
        """Export optional PNG charts for numerical and categorical columns."""
        if not isinstance(max_categories, int) or max_categories < 2:
            raise ValueError("max_categories must be an integer of at least 2.")
        if max_charts is not None and (
            not isinstance(max_charts, int) or max_charts < 1
        ):
            raise ValueError("max_charts must be None or an integer of at least 1.")

        try:
            import matplotlib

            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
        except ImportError as exc:
            raise ImportError(
                "Chart export requires matplotlib. Install with "
                "'py -m pip install -e .[charts]'."
            ) from exc

        output_dir = Path(output_directory)
        output_dir.mkdir(parents=True, exist_ok=True)
        saved: list[Path] = []
        identifiers = set(self._special_columns()["possible_identifiers"])

        def can_continue() -> bool:
            return max_charts is None or len(saved) < max_charts

        for column in self._column_groups()["numerical"]:
            if not can_continue():
                break
            if column in identifiers:
                continue
            values = pd.to_numeric(self.dataframe[column], errors="coerce").dropna()
            if values.empty:
                continue
            figure, axis = plt.subplots(figsize=(8, 5))
            axis.hist(values, bins="auto")
            axis.set_title(f"Distribution of {column}")
            axis.set_xlabel(column)
            axis.set_ylabel("Frequency")
            figure.tight_layout()
            path = output_dir / f"{self._safe_filename(column)}_histogram.png"
            figure.savefig(path, dpi=140)
            plt.close(figure)
            saved.append(path.resolve())

        for column in self._column_groups()["categorical"]:
            if not can_continue():
                break
            if column in identifiers:
                continue
            values = self.dataframe[column].dropna().astype(str)
            if values.empty:
                continue
            counts = values.value_counts().head(max_categories)
            figure, axis = plt.subplots(figsize=(8, 5))
            counts.plot(kind="bar", ax=axis)
            axis.set_title(f"Top categories in {column}")
            axis.set_xlabel(column)
            axis.set_ylabel("Count")
            axis.tick_params(axis="x", rotation=45)
            figure.tight_layout()
            path = output_dir / f"{self._safe_filename(column)}_bar.png"
            figure.savefig(path, dpi=140)
            plt.close(figure)
            saved.append(path.resolve())

        return saved

    def export_html(
        self,
        path: str | Path = "axiombraid_report.html",
        language: str = "en",
        *,
        theme: str = "light",
        report_title: str | None = None,
        include_confidence: bool = False,
        confidence_config: dict[str, Any] | None = None,
        include_quality_profile: bool = False,
        quality_config: dict[str, Any] | None = None,
    ) -> Path:
        language_code = self._language_code(language)
        theme_values = get_theme(theme)
        normalized_theme = str(theme).strip().lower().replace("-", "_")
        result = self.inspect(language_code)
        if include_confidence:
            from .confidence import add_confidence

            result = add_confidence(result, config=confidence_config)
        if include_quality_profile:
            from .scoring_v2 import build_quality_profile

            result["quality_profile"] = build_quality_profile(
                self.dataframe, result, config=quality_config
            )
        output_path = Path(path)
        if output_path.suffix.lower() != ".html":
            output_path = output_path.with_suffix(".html")
        output_path.parent.mkdir(parents=True, exist_ok=True)

        quality = result["data_quality"]
        missing_rows = "".join(
            "<tr>"
            f"<td>{escape(column)}</td>"
            f"<td>{details['count']}</td>"
            f"<td>{details['percentage']}%</td>"
            "</tr>"
            for column, details in result["missing_values"].items()
        )
        issue_rows = "".join(
            "<tr>"
            f"<td>{escape(issue['severity'].upper())}</td>"
            f"<td>{escape(issue['code'])}</td>"
            f"<td>{escape(issue['message'])}</td>"
            f"<td>{escape(', '.join(issue['columns']) or '-')}</td>"
            "</tr>"
            for issue in result["issues"]
        ) or '<tr><td colspan="4">No issues detected.</td></tr>'
        recommendations = "".join(
            f"<li>{escape(item)}</li>" for item in result["recommendations"]
        )
        cleaning_plan_rows = "".join(
            "<tr>"
            f"<td>{escape(action['action_id'])}</td>"
            f"<td>{escape(action['risk'])}</td>"
            f"<td>{escape(action['operation'])}</td>"
            f"<td>{escape(str(action['column']) if action['column'] is not None else '-')}</td>"
            f"<td>{escape(action['reason'])}</td>"
            "</tr>"
            for action in result["cleaning_plan"]["actions"]
        ) or '<tr><td colspan="5">No cleaning actions suggested.</td></tr>'
        outlier_rows = "".join(
            "<tr>"
            f"<td>{escape(column)}</td>"
            f"<td>{details['count']}</td>"
            f"<td>{details['percentage']}%</td>"
            f"<td>{escape(str(details['lower_bound']))} to {escape(str(details['upper_bound']))}</td>"
            f"<td>{escape(', '.join(map(str, details['example_values'])))}</td>"
            "</tr>"
            for column, details in result["outliers"].items()
        ) or '<tr><td colspan="5">No potential outliers detected.</td></tr>'
        range_rows = "".join(
            "<tr>"
            f"<td>{escape(column)}</td>"
            f"<td>{escape(str(details['expected_minimum']))} to {escape(str(details['expected_maximum']))}</td>"
            f"<td>{details['count']}</td>"
            f"<td>{details['percentage']}%</td>"
            f"<td>{escape(', '.join(map(str, details['example_values'])))}</td>"
            "</tr>"
            for column, details in result["numeric_range_issues"].items()
        ) or '<tr><td colspan="5">No suspicious numeric ranges detected.</td></tr>'
        date_rows = "".join(
            "<tr>"
            f"<td>{escape(column)}</td>"
            f"<td>{details['parse_percentage']}%</td>"
            f"<td>{escape(details['suggested_dtype'])}</td>"
            f"<td>{escape(', '.join(details['example_values']))}</td>"
            "</tr>"
            for column, details in result["date_like_text_columns"].items()
        ) or '<tr><td colspan="4">No date-like text columns detected.</td></tr>'
        column_quality_rows = "".join(
            "<tr>"
            f"<td>{escape(column)}</td>"
            f"<td>{details['score']}</td>"
            f"<td>{escape(details['rating'])}</td>"
            "</tr>"
            for column, details in result["column_quality"].items()
        )
        confidence_section = ""
        if include_confidence:
            from .confidence import (
                confidence_recommendation,
                humanize_issue_code,
                simple_issue_evidence,
            )

            summary = result["confidence_summary"]
            level_counts = summary["level_counts"]
            average_percent = int(round((summary.get("average_score") or 0.0) * 100))
            confidence_cards = (
                '<div class="grid confidence-grid">'
                f'<div class="card"><span class="small">Issues assessed</span><div class="value">{summary["issue_count"]}</div></div>'
                f'<div class="card"><span class="small">High confidence</span><div class="value confidence-high">{level_counts["high"]}</div></div>'
                f'<div class="card"><span class="small">Medium confidence</span><div class="value confidence-medium">{level_counts["medium"]}</div></div>'
                f'<div class="card"><span class="small">Low confidence</span><div class="value confidence-low">{level_counts["low"]}</div></div>'
                f'<div class="card"><span class="small">Average evidence strength</span><div class="value">{average_percent}%</div></div>'
                '</div>'
            )
            issue_cards = []
            for issue in result["issues"]:
                confidence = issue["confidence"]
                score_percent = int(round(float(confidence["score"]) * 100))
                level = escape(str(confidence["level"]).upper())
                severity = escape(str(issue.get("severity", "info")).upper())
                columns = escape(", ".join(map(str, issue.get("columns", []))) or "-")
                display_name = escape(
                    humanize_issue_code(str(issue.get("code", "unknown")), language=language_code)
                )
                simple_evidence = escape(simple_issue_evidence(issue, language=language_code))
                recommendation = escape(confidence_recommendation(issue, language=language_code))
                technical = escape(json.dumps(confidence.get("factors", {}), ensure_ascii=False, default=str, indent=2))
                issue_cards.append(
                    '<article class="confidence-issue">'
                    '<div class="confidence-issue-head">'
                    f'<h3>{display_name}</h3>'
                    f'<span class="badge badge-{confidence["level"]}">{score_percent}% {level}</span>'
                    '</div>'
                    f'<p><strong>Severity:</strong> {severity} &nbsp; <strong>Column(s):</strong> {columns}</p>'
                    f'<p><strong>Evidence:</strong> {simple_evidence}</p>'
                    f'<p><strong>Recommended action:</strong> {recommendation}</p>'
                    '<details><summary>Technical details</summary>'
                    f'<pre>{technical}</pre>'
                    '</details>'
                    '</article>'
                )
            confidence_section = (
                '<section id="confidence">'
                '<h2>Confidence Overview</h2>'
                '<p class="small">Confidence represents the strength of available detection evidence, not statistical probability.</p>'
                + confidence_cards
                + '<h3 style="margin-top:24px">Issue Evidence</h3>'
                + ''.join(issue_cards)
                + '</section>'
            )

        quality_profile_section = ""
        if include_quality_profile and "quality_profile" in result:
            profile = result["quality_profile"]
            dimension_cards = "".join(
                '<div class="card">'
                f'{escape(name.title())}<div class="value">{details["score"]}/100</div>'
                f'<div class="small">Weight: {int(round(float(details["weight"]) * 100))}% · {escape(details["rating"])}</div>'
                '</div>'
                for name, details in profile["dimensions"].items()
            )
            dimension_rows = "".join(
                "<tr>"
                f"<td>{escape(name.title())}</td>"
                f"<td>{details['score']}/100</td>"
                f"<td>{int(round(float(details['weight']) * 100))}%</td>"
                f"<td>{escape(details['explanation'])}</td>"
                f"<td>{escape(details['recommendation'])}</td>"
                "</tr>"
                for name, details in profile["dimensions"].items()
            )
            priorities = "".join(
                f'<li><strong>{escape(item["dimension"].title())}:</strong> '
                f'{item["score"]}/100 — {escape(item["recommendation"])}</li>'
                for item in profile["priorities"]
            ) or "<li>No dimension is currently below 90/100.</li>"
            quality_profile_section = (
                '<section id="quality-profile">'
                '<h2>Explainable Data Quality Profile</h2>'
                f'<p><strong>Overall score:</strong> {profile["score"]}/100 '
                f'({escape(profile["rating"])})</p>'
                f'<p class="small">{escape(profile["note"])}</p>'
                '<div class="grid">' + dimension_cards + '</div>'
                '<h3 style="margin-top:24px">Dimension breakdown</h3>'
                '<table><thead><tr><th>Dimension</th><th>Score</th><th>Weight</th><th>What it measures</th><th>Recommended action</th></tr></thead>'
                f'<tbody>{dimension_rows}</tbody></table>'
                '<h3 style="margin-top:24px">Improvement priorities</h3><ul>'
                + priorities + '</ul>'
                '<details><summary>Scoring configuration and legacy comparison</summary>'
                f'<pre>{escape(json.dumps({"weights": profile["weights"], "legacy_compatibility_score": profile["legacy_compatibility_score"], "score_difference_from_legacy": profile["score_difference_from_legacy"]}, indent=2, default=str))}</pre>'
                '</details>'
                '</section>'
            )

        groups = result["column_groups"]
        special = result["special_columns"]
        title = report_title or (
            "AxiomBraid Dataset Inspection Report"
            if language_code == "en"
            else "AxiomBraid Dataset Jaiza Report"
        )

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(title)}</title>
<style>
body {{ font-family: Arial, sans-serif; margin: 0; background: {theme_values["background"]}; color: {theme_values["text"]}; }}
main {{ max-width: 1120px; margin: 32px auto; padding: 0 20px 40px; }}
header, section {{ background: {theme_values["surface"]}; border: 1px solid {theme_values["border"]}; border-radius: 12px; padding: 22px; margin-bottom: 18px; }}
h1, h2 {{ margin-top: 0; }}
h1 {{ color: {theme_values["accent"]}; }}
.grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; }}
.card {{ background: {theme_values["surface_alt"]}; border: 1px solid {theme_values["border"]}; border-radius: 9px; padding: 14px; }}
.value {{ font-size: 1.6rem; font-weight: bold; margin-top: 5px; }}
table {{ width: 100%; border-collapse: collapse; }}
th, td {{ text-align: left; border-bottom: 1px solid {theme_values["border"]}; padding: 10px; vertical-align: top; }}
th {{ background: {theme_values["surface_alt"]}; }}
a {{ color: {theme_values["accent"]}; }}
.small {{ color: {theme_values["muted"]}; font-size: 0.92rem; }}
.confidence-grid {{ margin: 14px 0 18px; }}
.confidence-issue {{ background: {theme_values["surface_alt"]}; border: 1px solid {theme_values["border"]}; border-radius: 10px; padding: 16px; margin: 12px 0; }}
.confidence-issue-head {{ display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap; }}
.confidence-issue-head h3 {{ margin: 0; }}
.badge {{ display: inline-block; padding: 5px 10px; border-radius: 999px; font-weight: bold; font-size: 0.85rem; }}
.badge-high {{ background: #dcfce7; color: #166534; }}
.badge-medium {{ background: #fef3c7; color: #92400e; }}
.badge-low {{ background: #fee2e2; color: #991b1b; }}
.confidence-high {{ color: #166534; }}
.confidence-medium {{ color: #92400e; }}
.confidence-low {{ color: #991b1b; }}
details {{ margin-top: 10px; }}
summary {{ cursor: pointer; font-weight: bold; }}
pre {{ white-space: pre-wrap; overflow-wrap: anywhere; background: {theme_values["background"]}; border: 1px solid {theme_values["border"]}; border-radius: 8px; padding: 12px; }}
</style>
</head>
<body>
<main>
<header>
<h1>{escape(title)}</h1>
<p class="small">Generated by AxiomBraid {__version__} · Theme: {escape(normalized_theme)}</p>
<div class="grid">
<div class="card">Rows<div class="value">{result['shape']['rows']}</div></div>
<div class="card">Columns<div class="value">{result['shape']['columns']}</div></div>
<div class="card">Quality score<div class="value">{quality['score']}/100</div></div>
<div class="card">Rating<div class="value">{escape(quality['rating'])}</div></div>
<div class="card">Fingerprint<div class="value" style="font-size:0.9rem;word-break:break-all">{escape(result['dataset_fingerprint']['combined_hash'][:16])}...</div></div>
<div class="card">Analysis mode<div class="value" style="font-size:1rem">{escape(result['performance']['effective_mode'])}</div></div>
</div>
</header>
{quality_profile_section}
<section>
<h2>Column groups</h2>
<p><strong>Numerical:</strong> {self._html_list(groups['numerical'], 'None')}</p>
<p><strong>Categorical:</strong> {self._html_list(groups['categorical'], 'None')}</p>
<p><strong>Boolean:</strong> {self._html_list(groups['boolean'], 'None')}</p>
<p><strong>Datetime:</strong> {self._html_list(groups['datetime'], 'None')}</p>
</section>
<section>
<h2>Special columns</h2>
<p><strong>Constant:</strong> {self._html_list(special['constant'], 'None')}</p>
<p><strong>Possible identifiers:</strong> {self._html_list(special['possible_identifiers'], 'None')}</p>
<p><strong>High-cardinality descriptive:</strong> {self._html_list(special['high_cardinality_descriptive'], 'None')}</p>
</section>
<section>
<h2>Issues and severity</h2>
<table><thead><tr><th>Severity</th><th>Code</th><th>Message</th><th>Columns</th></tr></thead>
<tbody>{issue_rows}</tbody></table>
</section>
{confidence_section}
<section>
<h2>Cleaning plan preview</h2>
<p class="small">Preview only. Manual-review actions are never automatically applied.</p>
<table><thead><tr><th>Action</th><th>Risk</th><th>Operation</th><th>Column</th><th>Reason</th></tr></thead>
<tbody>{cleaning_plan_rows}</tbody></table>
</section>
<section>
<h2>Potential outliers</h2>
<table><thead><tr><th>Column</th><th>Count</th><th>Percentage</th><th>IQR bounds</th><th>Examples</th></tr></thead>
<tbody>{outlier_rows}</tbody></table>
</section>
<section>
<h2>Suspicious numeric ranges</h2>
<table><thead><tr><th>Column</th><th>Expected range</th><th>Count</th><th>Percentage</th><th>Examples</th></tr></thead>
<tbody>{range_rows}</tbody></table>
</section>
<section>
<h2>Date-like text columns</h2>
<table><thead><tr><th>Column</th><th>Parsed</th><th>Suggested dtype</th><th>Examples</th></tr></thead>
<tbody>{date_rows}</tbody></table>
</section>
<section>
<h2>Column quality scores</h2>
<table><thead><tr><th>Column</th><th>Score</th><th>Rating</th></tr></thead>
<tbody>{column_quality_rows}</tbody></table>
</section>
<section>
<h2>Missing values</h2>
<table><thead><tr><th>Column</th><th>Count</th><th>Percentage</th></tr></thead>
<tbody>{missing_rows}</tbody></table>
</section>
<section><h2>Recommendations</h2><ul>{recommendations}</ul></section>
</main>
</body>
</html>"""
        output_path.write_text(html, encoding="utf-8")
        return output_path.resolve()

    def report(
        self,
        language: str = "en",
        *,
        include_confidence: bool = False,
        confidence_config: dict[str, Any] | None = None,
        confidence_details: str = "full",
        include_quality_profile: bool = False,
        quality_config: dict[str, Any] | None = None,
        quality_details: str = "full",
    ) -> dict[str, Any]:
        """Print a readable console report with optional Version 2 enhancements."""
        language_code = self._language_code(language)
        result = self.inspect(language_code)
        if include_confidence:
            from .confidence import add_confidence

            result = add_confidence(result, config=confidence_config)
        if include_quality_profile:
            from .scoring_v2 import build_quality_profile

            result["quality_profile"] = build_quality_profile(
                self.dataframe, result, config=quality_config
            )
        quality = result["data_quality"]
        none_text = "None" if language_code == "en" else "Koi nahi"
        title = (
            "AXIOMBRAID — DATASET INSPECTION REPORT"
            if language_code == "en"
            else "AXIOMBRAID — DATASET JAIZA REPORT"
        )
        suggestions = "RECOMMENDATIONS" if language_code == "en" else "SUGGESTIONS"

        print("=" * 72)
        print(title)
        print("=" * 72)
        print(f"Rows: {result['shape']['rows']}")
        print(f"Columns: {result['shape']['columns']}")
        print("Column names: " + (", ".join(result["column_names"]) or none_text))
        print(f"Duplicate rows: {result['duplicate_rows']}")
        performance = result["performance"]
        print(
            "Analysis mode: "
            f"{performance['effective_mode']} "
            f"({performance['analyzed_rows']} of {performance['full_rows']} rows)"
        )
        if performance.get("warning"):
            print(f"Analysis note: {performance['warning']}")

        print("\nDATA QUALITY")
        print(f"- Score: {quality['score']}/100")
        print(f"- Rating: {quality['rating']}")
        print(f"- Fingerprint: {result['dataset_fingerprint']['combined_hash'][:16]}...")

        if include_quality_profile and "quality_profile" in result:
            from .scoring_v2 import format_quality_profile_console

            print("\n" + format_quality_profile_console(
                result["quality_profile"],
                language=language_code,
                details=quality_details,
            ))

        plan = result["cleaning_plan"]
        print("\nCLEANING PLAN PREVIEW")
        print(f"- Total actions: {plan['action_count']}")
        print(f"- Default low-risk actions: {len(plan['default_action_ids'])}")
        print(f"- Risk counts: {plan['risk_counts']}")

        print("\nCOLUMN GROUPS")
        for group, columns in result["column_groups"].items():
            displayed = ", ".join(columns) if columns else none_text
            print(f"- {group.title()}: {displayed}")

        special = result["special_columns"]
        print("\nSPECIAL COLUMNS")
        print("- Constant: " + (", ".join(special["constant"]) or none_text))
        print(
            "- Possible identifiers: "
            + (", ".join(special["possible_identifiers"]) or none_text)
        )
        print(
            "- High-cardinality descriptive: "
            + (", ".join(special["high_cardinality_descriptive"]) or none_text)
        )

        print("\nISSUES BY SEVERITY")
        if result["issues"]:
            for issue in result["issues"]:
                columns = ", ".join(issue["columns"])
                suffix = f" [{columns}]" if columns else ""
                confidence_suffix = ""
                if include_confidence and "confidence" in issue:
                    confidence = issue["confidence"]
                    confidence_suffix = (
                        f" | Confidence: {int(round(float(confidence['score']) * 100))}% "
                        f"({str(confidence['level']).upper()})"
                    )
                print(
                    f"- {issue['severity'].upper()}: {issue['message']}{suffix}"
                    f"{confidence_suffix}"
                )
        else:
            print(f"- {none_text}")

        if include_confidence:
            from .confidence import format_confidence_console

            print("\n" + format_confidence_console(
                result,
                language=language_code,
                details=confidence_details,
            ))

        print("\nPOTENTIAL OUTLIERS")
        if result["outliers"]:
            for column, details in result["outliers"].items():
                print(
                    f"- {column}: {details['count']} ({details['percentage']}%), "
                    f"bounds {details['lower_bound']} to {details['upper_bound']}, "
                    f"examples {details['example_values']}"
                )
        else:
            print(f"- {none_text}")

        print("\nSUSPICIOUS NUMERIC RANGES")
        if result["numeric_range_issues"]:
            for column, details in result["numeric_range_issues"].items():
                print(
                    f"- {column}: expected {details['expected_minimum']} to "
                    f"{details['expected_maximum']}; examples {details['example_values']}"
                )
        else:
            print(f"- {none_text}")

        print("\nDATE-LIKE TEXT COLUMNS")
        if result["date_like_text_columns"]:
            for column, details in result["date_like_text_columns"].items():
                print(
                    f"- {column}: {details['parse_percentage']}% parsed; "
                    f"suggest {details['suggested_dtype']}"
                )
        else:
            print(f"- {none_text}")

        print("\nCOLUMN QUALITY")
        for column, details in result["column_quality"].items():
            print(f"- {column}: {details['score']}/100 ({details['rating']})")

        print("\nTEXT INCONSISTENCIES")
        if not result["text_inconsistencies"]:
            print(f"- {none_text}")
        else:
            for column, issues in result["text_inconsistencies"].items():
                print(f"- {column}:")
                for issue in issues:
                    variants = ", ".join(repr(v) for v in issue["variants"])
                    print(f"  {issue['normalized_value']} -> {variants}")

        print("\nMISSING VALUES")
        missing_found = False
        for column, details in result["missing_values"].items():
            if details["count"]:
                missing_found = True
                print(f"- {column}: {details['count']} ({details['percentage']}%)")
        if not missing_found:
            print(f"- {none_text}")

        print(f"\n{suggestions}")
        for recommendation in result["recommendations"]:
            print(f"- {recommendation}")
        print("=" * 72)
        return result
