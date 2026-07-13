"""User-defined schema rules and reusable validation contracts."""

from __future__ import annotations

import json
import re
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


class ValidationMixin:
    """Create, export, and enforce transparent dataset contracts."""

    @staticmethod
    def _contract_dtype_family(series: pd.Series) -> str:
        if pd.api.types.is_bool_dtype(series):
            return "boolean"
        if pd.api.types.is_datetime64_any_dtype(series):
            return "datetime"
        if pd.api.types.is_numeric_dtype(series):
            return "number"
        return "string"

    def create_validation_contract(
        self,
        rules: dict[str, dict[str, Any]] | None = None,
        *,
        strict_columns: bool = True,
        infer_allowed_values_max: int = 0,
    ) -> dict[str, Any]:
        """Create an inferred contract and merge optional user-defined rules."""
        if not isinstance(strict_columns, bool):
            raise TypeError("strict_columns must be a Boolean value.")
        if not isinstance(infer_allowed_values_max, int) or infer_allowed_values_max < 0:
            raise ValueError("infer_allowed_values_max must be an integer of at least 0.")
        if rules is not None and not isinstance(rules, dict):
            raise TypeError("rules must be a dictionary keyed by column name.")

        identifiers = set(self._special_columns()["possible_identifiers"])
        columns: dict[str, dict[str, Any]] = {}
        for column in self.dataframe.columns:
            name = str(column)
            series = self.dataframe[column]
            definition: dict[str, Any] = {
                "required": True,
                "dtype": self._contract_dtype_family(series),
                "nullable": bool(series.isna().any()),
            }
            if name in identifiers or (
                self._identifier_name_hint(name)
                and series.dropna().is_unique
            ):
                definition["unique"] = True
            range_rule = self._numeric_range_rule(name)
            if range_rule and definition["dtype"] == "number":
                definition["minimum"] = range_rule["minimum"]
                definition["maximum"] = range_rule["maximum"]
            if (
                infer_allowed_values_max >= 2
                and definition["dtype"] in {"string", "boolean"}
            ):
                values = series.dropna().map(
                    lambda value: " ".join(str(value).split())
                ).unique().tolist()
                if 0 < len(values) <= infer_allowed_values_max:
                    definition["allowed_values"] = [
                        self._python_value(value) for value in values
                    ]
            columns[name] = definition

        for column, overrides in (rules or {}).items():
            if not isinstance(overrides, dict):
                raise TypeError(f"Rules for '{column}' must be a dictionary.")
            columns.setdefault(str(column), {"required": False, "nullable": True})
            columns[str(column)].update(deepcopy(overrides))

        return {
            "contract_version": "1.0",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "strict_columns": strict_columns,
            "columns": columns,
            "source_fingerprint": self.dataset_fingerprint(),
            "rule_notes": {
                "dtype": "Supported families: number, string, boolean, datetime.",
                "optional_rules": [
                    "required", "nullable", "unique", "minimum", "maximum",
                    "allowed_values", "pattern", "min_length", "max_length",
                ],
            },
        }

    @staticmethod
    def load_validation_contract(path: str | Path) -> dict[str, Any]:
        """Load a JSON validation contract."""
        contract_path = Path(path)
        with contract_path.open("r", encoding="utf-8") as file:
            contract = json.load(file)
        if not isinstance(contract, dict):
            raise ValueError("Validation contract must contain a JSON object.")
        return contract

    def export_validation_contract(
        self,
        path: str | Path = "axiombraid_contract.json",
        *,
        contract: dict[str, Any] | None = None,
        rules: dict[str, dict[str, Any]] | None = None,
        strict_columns: bool = True,
        infer_allowed_values_max: int = 0,
    ) -> Path:
        """Export a validation contract as JSON."""
        output = Path(path)
        if output.suffix.lower() != ".json":
            output = output.with_suffix(".json")
        output.parent.mkdir(parents=True, exist_ok=True)
        payload = contract or self.create_validation_contract(
            rules,
            strict_columns=strict_columns,
            infer_allowed_values_max=infer_allowed_values_max,
        )
        with output.open("w", encoding="utf-8") as file:
            json.dump(payload, file, ensure_ascii=False, indent=2, default=str)
        return output.resolve()

    @staticmethod
    def _validation_examples(series: pd.Series, mask: pd.Series, limit: int = 5) -> list[Any]:
        values = series[mask].head(limit).tolist()
        result: list[Any] = []
        for value in values:
            if pd.isna(value):
                result.append(None)
            elif hasattr(value, "item"):
                result.append(value.item())
            else:
                result.append(value)
        return result

    def validate_contract(
        self,
        contract: dict[str, Any] | str | Path,
        *,
        data: Any | None = None,
    ) -> dict[str, Any]:
        """Validate a dataset against a reusable contract."""
        if isinstance(contract, (str, Path)):
            contract = self.load_validation_contract(contract)
        if not isinstance(contract, dict) or not isinstance(contract.get("columns"), dict):
            raise ValueError("Invalid contract: a 'columns' dictionary is required.")
        frame = self.dataframe.copy(deep=True) if data is None else self._coerce_comparison_frame(data)
        definitions: dict[str, Any] = contract["columns"]
        strict = bool(contract.get("strict_columns", True))
        violations: list[dict[str, Any]] = []

        def add(code: str, severity: str, column: str | None, message: str, count: int = 0, examples: list[Any] | None = None) -> None:
            violations.append({
                "code": code,
                "severity": severity,
                "column": column,
                "message": message,
                "count": int(count),
                "examples": examples or [],
            })

        expected = set(definitions)
        actual = {str(column) for column in frame.columns}
        for column, rules in definitions.items():
            if not isinstance(rules, dict):
                add("invalid_rule_definition", "high", column, "Column rules must be a dictionary.")
                continue
            required = bool(rules.get("required", True))
            if column not in actual:
                if required:
                    add("missing_required_column", "high", column, "A required column is missing.")
                continue
            series = frame[column]
            expected_dtype = rules.get("dtype")
            actual_dtype = self._contract_dtype_family(series)
            if expected_dtype is not None and expected_dtype not in {"number", "string", "boolean", "datetime"}:
                add("invalid_dtype_rule", "high", column, f"Unsupported dtype rule: {expected_dtype}")
            elif expected_dtype and expected_dtype != actual_dtype:
                add(
                    "dtype_mismatch", "high", column,
                    f"Expected dtype family '{expected_dtype}' but found '{actual_dtype}'.",
                )

            missing_mask = series.isna()
            if not bool(rules.get("nullable", True)) and missing_mask.any():
                add(
                    "null_not_allowed", "high", column,
                    "Missing values are not allowed.", int(missing_mask.sum()),
                    [None],
                )
            if bool(rules.get("unique", False)):
                duplicate_mask = series.notna() & series.duplicated(keep=False)
                if duplicate_mask.any():
                    add(
                        "duplicate_values", "high", column,
                        "Values must be unique.", int(duplicate_mask.sum()),
                        self._validation_examples(series, duplicate_mask),
                    )

            if "minimum" in rules or "maximum" in rules:
                numeric = pd.to_numeric(series, errors="coerce")
                invalid = pd.Series(False, index=series.index)
                if "minimum" in rules:
                    invalid |= numeric < float(rules["minimum"])
                if "maximum" in rules:
                    invalid |= numeric > float(rules["maximum"])
                invalid &= numeric.notna()
                if invalid.any():
                    add(
                        "numeric_range_violation", "high", column,
                        "Values fall outside the contract range.", int(invalid.sum()),
                        self._validation_examples(series, invalid),
                    )

            if "allowed_values" in rules:
                allowed = rules["allowed_values"]
                if not isinstance(allowed, list):
                    add("invalid_allowed_values_rule", "high", column, "allowed_values must be a list.")
                else:
                    normalized_allowed = {
                        " ".join(str(value).split()).casefold() for value in allowed
                    }
                    normalized = series.map(
                        lambda value: None if pd.isna(value) else " ".join(str(value).split()).casefold()
                    )
                    invalid = series.notna() & ~normalized.isin(normalized_allowed)
                    if invalid.any():
                        add(
                            "disallowed_value", "medium", column,
                            "Values outside allowed_values were detected.", int(invalid.sum()),
                            self._validation_examples(series, invalid),
                        )

            if "pattern" in rules:
                try:
                    pattern = re.compile(str(rules["pattern"]))
                except re.error as exc:
                    add("invalid_pattern_rule", "high", column, f"Invalid regex pattern: {exc}")
                else:
                    invalid = series.notna() & ~series.astype(str).map(lambda value: bool(pattern.fullmatch(value)))
                    if invalid.any():
                        add(
                            "pattern_mismatch", "medium", column,
                            "Values do not match the required pattern.", int(invalid.sum()),
                            self._validation_examples(series, invalid),
                        )

            if "min_length" in rules or "max_length" in rules:
                text = series.astype("string")
                lengths = text.str.len()
                invalid = pd.Series(False, index=series.index)
                if "min_length" in rules:
                    invalid |= lengths < int(rules["min_length"])
                if "max_length" in rules:
                    invalid |= lengths > int(rules["max_length"])
                invalid &= series.notna()
                if invalid.any():
                    add(
                        "length_violation", "medium", column,
                        "Text length falls outside the contract limits.", int(invalid.sum()),
                        self._validation_examples(series, invalid),
                    )

        if strict:
            for column in sorted(actual - expected):
                add("unexpected_column", "medium", column, "An unexpected column is present.")

        severity_order = {"high": 0, "medium": 1, "low": 2, "info": 3}
        violations.sort(key=lambda item: (severity_order[item["severity"]], item["code"], str(item["column"])))
        counts = {
            severity: sum(item["severity"] == severity for item in violations)
            for severity in severity_order
        }
        return {
            "valid": not violations,
            "violation_count": len(violations),
            "severity_counts": counts,
            "violations": violations,
            "dataset_fingerprint": self.dataset_fingerprint(frame),
            "contract_version": contract.get("contract_version", "unknown"),
            "strict_columns": strict,
        }
