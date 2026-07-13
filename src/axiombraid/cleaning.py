"""Preview-first, reversible cleaning support for AxiomBraid."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

import pandas as pd


class CleaningMixin:
    """Provide safe cleaning plans and reversible cleaning actions."""

    _RISK_ORDER = {"low": 1, "medium": 2, "high": 3, "manual": 4}

    def _canonical_text_mapping(self, column: str) -> dict[str, str]:
        series = self.dataframe[column].dropna().astype(str)
        mapping: dict[str, str] = {}
        for normalized, values in series.groupby(series.map(self._normalize_text)):
            cleaned = values.map(lambda value: " ".join(value.split()))
            counts = cleaned.value_counts()
            maximum = int(counts.max())
            candidates = set(counts[counts == maximum].index.tolist())
            canonical = next(value for value in cleaned.tolist() if value in candidates)
            mapping[str(normalized)] = str(canonical)
        return mapping

    def cleaning_plan(self) -> dict[str, Any]:
        """Return a preview-only plan; this method never changes the dataset."""
        actions: list[dict[str, Any]] = []
        duplicate_count = int(self.dataframe.duplicated().sum())
        if duplicate_count:
            actions.append({
                "action_id": "remove_duplicates",
                "operation": "remove_duplicates",
                "column": None,
                "risk": "low",
                "auto_applicable": True,
                "default_enabled": True,
                "reason": f"{duplicate_count} exact duplicate row(s) were detected.",
                "preview": {"rows_to_remove": duplicate_count},
            })

        for column, groups in self._text_inconsistencies().items():
            mapping = self._canonical_text_mapping(column)
            actions.append({
                "action_id": f"normalize_text:{column}",
                "operation": "normalize_text",
                "column": column,
                "risk": "low",
                "auto_applicable": True,
                "default_enabled": True,
                "reason": "Case or whitespace variants appear to represent the same value.",
                "preview": {"mapping": mapping, "inconsistency_groups": groups},
            })

        for column, details in self._date_like_text_columns().items():
            parse_percentage = float(details["parse_percentage"])
            risk = "low" if parse_percentage == 100.0 else "medium"
            actions.append({
                "action_id": f"convert_datetime:{column}",
                "operation": "convert_datetime",
                "column": column,
                "risk": risk,
                "auto_applicable": True,
                "default_enabled": risk == "low",
                "reason": "The text column appears to contain dates.",
                "preview": {
                    "parse_percentage": parse_percentage,
                    "suggested_dtype": details["suggested_dtype"],
                },
            })

        groups = self._column_groups()
        for column, details in self._missing_values().items():
            if not details["count"]:
                continue
            series = self.dataframe[column]
            if column in groups["numerical"]:
                numeric = pd.to_numeric(series, errors="coerce")
                fill_value = self._python_value(numeric.median()) if numeric.notna().any() else None
                operation = "fill_missing_numeric"
                strategy = "median"
            elif column in groups["boolean"]:
                mode = series.mode(dropna=True)
                fill_value = self._python_value(mode.iloc[0]) if not mode.empty else None
                operation = "fill_missing_boolean"
                strategy = "mode"
            elif column in groups["categorical"]:
                mode = series.dropna().astype(str).map(lambda value: " ".join(value.split())).mode()
                fill_value = str(mode.iloc[0]) if not mode.empty else None
                operation = "fill_missing_categorical"
                strategy = "mode"
            else:
                continue
            if fill_value is None:
                continue
            actions.append({
                "action_id": f"{operation}:{column}",
                "operation": operation,
                "column": column,
                "risk": "medium",
                "auto_applicable": True,
                "default_enabled": False,
                "reason": f"{details['count']} missing value(s) were detected.",
                "preview": {
                    "strategy": strategy,
                    "fill_value": fill_value,
                    "missing_count": details["count"],
                },
            })

        for column, details in self._outliers().items():
            actions.append({
                "action_id": f"review_outliers:{column}",
                "operation": "manual_review_outliers",
                "column": column,
                "risk": "manual",
                "auto_applicable": False,
                "default_enabled": False,
                "reason": "Potential outliers require domain knowledge before modification.",
                "preview": details,
            })

        for column, details in self._numeric_range_issues().items():
            actions.append({
                "action_id": f"review_numeric_range:{column}",
                "operation": "manual_review_numeric_range",
                "column": column,
                "risk": "manual",
                "auto_applicable": False,
                "default_enabled": False,
                "reason": "Values outside an expected range require validation, not automatic clipping.",
                "preview": details,
            })

        special = self._special_columns()
        for column in special["constant"]:
            actions.append({
                "action_id": f"review_constant:{column}",
                "operation": "manual_review_constant",
                "column": column,
                "risk": "manual",
                "auto_applicable": False,
                "default_enabled": False,
                "reason": "A constant column may be removable, but the decision is context-dependent.",
                "preview": {},
            })
        for column in special["possible_identifiers"]:
            actions.append({
                "action_id": f"exclude_identifier_from_ml:{column}",
                "operation": "manual_review_identifier",
                "column": column,
                "risk": "manual",
                "auto_applicable": False,
                "default_enabled": False,
                "reason": "Identifiers are normally excluded from ML features but retained in the dataset.",
                "preview": {},
            })

        counts = {risk: sum(a["risk"] == risk for a in actions) for risk in self._RISK_ORDER}
        return {
            "preview_only": True,
            "dataset_shape": {
                "rows": int(self.dataframe.shape[0]),
                "columns": int(self.dataframe.shape[1]),
            },
            "action_count": len(actions),
            "risk_counts": counts,
            "default_action_ids": [a["action_id"] for a in actions if a["default_enabled"]],
            "actions": actions,
            "safety_note": (
                "Low-risk actions can be applied automatically. Medium-risk imputation "
                "requires explicit permission. Outliers and invalid ranges are never "
                "automatically removed or clipped."
            ),
        }

    def apply_cleaning(
        self,
        plan: dict[str, Any] | None = None,
        *,
        max_risk: str = "low",
        selected_actions: list[str] | None = None,
        inplace: bool = False,
        confirm: bool = False,
    ) -> dict[str, Any]:
        """Apply selected auto-applicable actions to a deep copy or in place."""
        if getattr(self, "_sampling_metadata", {}).get("sampled"):
            raise ValueError(
                "Cleaning is disabled on sampled analysis objects. Create a full-mode "
                "DataGuide instance before applying changes."
            )
        if max_risk not in {"low", "medium"}:
            raise ValueError("max_risk must be 'low' or 'medium'.")
        if inplace and not confirm:
            raise ValueError("inplace=True requires confirm=True for safety.")
        plan = plan or self.cleaning_plan()
        actions = plan.get("actions")
        if not isinstance(actions, list):
            raise ValueError("Invalid cleaning plan: 'actions' must be a list.")

        selected = set(selected_actions) if selected_actions is not None else None
        before = self.dataframe.copy(deep=True)
        working = before.copy(deep=True)
        applied: list[str] = []
        skipped: list[dict[str, str]] = []
        maximum = self._RISK_ORDER[max_risk]

        for action in actions:
            action_id = str(action.get("action_id"))
            risk = str(action.get("risk"))
            operation = str(action.get("operation"))
            column = action.get("column")
            if selected is not None and action_id not in selected:
                continue
            if selected is None and not action.get("default_enabled", False) and risk != "medium":
                continue
            if not action.get("auto_applicable", False):
                skipped.append({"action_id": action_id, "reason": "manual_review_required"})
                continue
            if self._RISK_ORDER.get(risk, 99) > maximum:
                skipped.append({"action_id": action_id, "reason": "risk_above_maximum"})
                continue
            if column is not None and column not in working.columns:
                skipped.append({"action_id": action_id, "reason": "column_not_found"})
                continue

            if operation == "remove_duplicates":
                working = working.drop_duplicates().reset_index(drop=True)
            elif operation == "normalize_text":
                mapping = action["preview"]["mapping"]
                working[column] = working[column].map(
                    lambda value: value
                    if pd.isna(value)
                    else mapping.get(self._normalize_text(str(value)), " ".join(str(value).split()))
                )
            elif operation == "convert_datetime":
                try:
                    working[column] = pd.to_datetime(working[column], errors="coerce", format="mixed")
                except TypeError:
                    working[column] = pd.to_datetime(working[column], errors="coerce")
            elif operation in {
                "fill_missing_numeric",
                "fill_missing_categorical",
                "fill_missing_boolean",
            }:
                working[column] = working[column].fillna(action["preview"]["fill_value"])
            else:
                skipped.append({"action_id": action_id, "reason": "unsupported_operation"})
                continue
            applied.append(action_id)

        comparison = self._compare_frames(before, working)
        if inplace:
            self._cleaning_history.append(before)
            self.dataframe = working.copy(deep=True)
        self._last_cleaning_result = {
            "applied_actions": applied,
            "skipped_actions": skipped,
            "comparison": comparison,
            "inplace": inplace,
        }
        audit_entry = {
            "event": "apply_cleaning",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "inplace": inplace,
            "max_risk": max_risk,
            "selected_actions": sorted(selected) if selected is not None else None,
            "applied_actions": list(applied),
            "skipped_actions": deepcopy(skipped),
            "comparison": deepcopy(comparison),
            "before_fingerprint": self.dataset_fingerprint(before),
            "after_fingerprint": self.dataset_fingerprint(working),
        }
        self._cleaning_audit_log.append(audit_entry)
        return {
            "dataframe": working,
            "applied_actions": applied,
            "skipped_actions": skipped,
            "comparison": comparison,
            "inplace": inplace,
            "can_undo": bool(self._cleaning_history),
        }

    def undo_last_cleaning(self) -> dict[str, Any]:
        """Restore the last in-place snapshot."""
        if not self._cleaning_history:
            raise RuntimeError("No in-place cleaning action is available to undo.")
        current = self.dataframe.copy(deep=True)
        restored = self._cleaning_history.pop()
        self.dataframe = restored.copy(deep=True)
        comparison = self._compare_frames(current, self.dataframe)
        self._cleaning_audit_log.append({
            "event": "undo_cleaning",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "comparison": deepcopy(comparison),
            "before_fingerprint": self.dataset_fingerprint(current),
            "after_fingerprint": self.dataset_fingerprint(self.dataframe),
            "remaining_undo_steps": len(self._cleaning_history),
        })
        return {
            "dataframe": self.dataframe.copy(deep=True),
            "comparison": comparison,
            "remaining_undo_steps": len(self._cleaning_history),
        }

    def cleaning_audit_log(self) -> list[dict[str, Any]]:
        """Return a defensive copy of cleaning and undo audit events."""
        return deepcopy(self._cleaning_audit_log)

    def clear_cleaning_audit_log(self) -> int:
        """Clear audit events and return the number removed."""
        count = len(self._cleaning_audit_log)
        self._cleaning_audit_log.clear()
        return count

    def export_cleaning_audit_log(
        self,
        path: str | Path = "axiombraid_cleaning_audit.json",
    ) -> Path:
        """Export cleaning audit events without raw dataset values."""
        output = Path(path)
        if output.suffix.lower() != ".json":
            output = output.with_suffix(".json")
        output.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "event_count": len(self._cleaning_audit_log),
            "events": self.cleaning_audit_log(),
            "privacy_note": (
                "The audit contains actions, comparisons, and fingerprints; it "
                "does not include a raw dataset snapshot."
            ),
        }
        with output.open("w", encoding="utf-8") as file:
            json.dump(payload, file, ensure_ascii=False, indent=2, default=str)
        return output.resolve()
