"""Explainable multi-dimensional data-quality scoring for AxiomBraid 2.0.

The Version 2 quality profile is intentionally separate from the legacy
``data_quality`` score so existing users and downstream integrations keep the
same behaviour.  The new profile explains *why* a score is high or low by
reporting five measurable dimensions.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

import pandas as pd


DEFAULT_QUALITY_PROFILE_CONFIG: dict[str, Any] = {
    "weights": {
        "completeness": 0.30,
        "uniqueness": 0.20,
        "validity": 0.20,
        "consistency": 0.20,
        "integrity": 0.10,
    },
    "rating_thresholds": {
        "excellent": 90.0,
        "good": 75.0,
        "needs_attention": 50.0,
    },
    # Date-like text is a representation warning rather than a guaranteed
    # error, so it contributes only a fraction of a full inconsistency cell.
    "date_like_consistency_weight": 0.25,
}

_DIMENSIONS = (
    "completeness",
    "uniqueness",
    "validity",
    "consistency",
    "integrity",
)


def _clamp_score(value: float) -> float:
    return round(max(0.0, min(100.0, float(value))), 2)


def normalize_quality_profile_config(
    config: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Return validated Version 2 quality-profile configuration.

    User-supplied weights are normalized to sum to 1.0.  All five dimensions
    must remain present and non-negative so the final score stays transparent.
    """

    normalized = deepcopy(DEFAULT_QUALITY_PROFILE_CONFIG)
    if config is None:
        return normalized
    if not isinstance(config, Mapping):
        raise TypeError("quality profile config must be a mapping or None.")

    if "weights" in config:
        supplied = config["weights"]
        if not isinstance(supplied, Mapping):
            raise TypeError("quality profile weights must be a mapping.")
        weights = dict(normalized["weights"])
        for name, value in supplied.items():
            if name not in _DIMENSIONS:
                raise ValueError(f"Unknown quality dimension: {name}")
            numeric = float(value)
            if numeric < 0:
                raise ValueError("quality profile weights cannot be negative.")
            weights[name] = numeric
        total = sum(float(weights[name]) for name in _DIMENSIONS)
        if total <= 0:
            raise ValueError("At least one quality profile weight must be positive.")
        normalized["weights"] = {
            name: round(float(weights[name]) / total, 6)
            for name in _DIMENSIONS
        }

    if "rating_thresholds" in config:
        supplied = config["rating_thresholds"]
        if not isinstance(supplied, Mapping):
            raise TypeError("rating_thresholds must be a mapping.")
        thresholds = dict(normalized["rating_thresholds"])
        for name in thresholds:
            if name in supplied:
                thresholds[name] = float(supplied[name])
        if not (
            100 >= thresholds["excellent"]
            >= thresholds["good"]
            >= thresholds["needs_attention"]
            >= 0
        ):
            raise ValueError(
                "rating thresholds must satisfy 100 >= excellent >= good >= "
                "needs_attention >= 0."
            )
        normalized["rating_thresholds"] = thresholds

    if "date_like_consistency_weight" in config:
        value = float(config["date_like_consistency_weight"])
        if not 0 <= value <= 1:
            raise ValueError("date_like_consistency_weight must be between 0 and 1.")
        normalized["date_like_consistency_weight"] = value

    return normalized


def _rating(score: float, thresholds: Mapping[str, float]) -> str:
    if score >= float(thresholds["excellent"]):
        return "excellent"
    if score >= float(thresholds["good"]):
        return "good"
    if score >= float(thresholds["needs_attention"]):
        return "needs_attention"
    return "poor"


def _dimension(
    *,
    score: float,
    weight: float,
    explanation: str,
    evidence: dict[str, Any],
    recommendation: str,
    thresholds: Mapping[str, float],
    coverage_note: str | None = None,
) -> dict[str, Any]:
    score = _clamp_score(score)
    payload: dict[str, Any] = {
        "score": score,
        "rating": _rating(score, thresholds),
        "weight": round(float(weight), 6),
        "weighted_contribution": round(score * float(weight), 2),
        "explanation": explanation,
        "evidence": evidence,
        "recommendation": recommendation,
    }
    if coverage_note:
        payload["coverage_note"] = coverage_note
    return payload


def _text_inconsistency_cells(
    dataframe: pd.DataFrame,
    text_inconsistencies: Mapping[str, Any],
) -> int:
    affected = 0
    for column, groups in text_inconsistencies.items():
        if column not in dataframe.columns:
            continue
        raw = dataframe[column].dropna().astype(str)
        normalized = raw.str.strip().str.casefold()
        targets = {
            str(group.get("normalized_value", "")).strip().casefold()
            for group in groups
            if str(group.get("normalized_value", "")).strip()
        }
        if targets:
            affected += int(normalized.isin(targets).sum())
    return affected


def build_quality_profile(
    dataframe: pd.DataFrame,
    inspection: Mapping[str, Any],
    *,
    config: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build an explainable five-dimension quality profile.

    The score is heuristic and evidence-based.  It is not a universal data
    quality standard and does not claim domain validity beyond the checks that
    AxiomBraid can actually observe.
    """

    if not isinstance(dataframe, pd.DataFrame):
        raise TypeError("dataframe must be a pandas DataFrame.")
    if not isinstance(inspection, Mapping):
        raise TypeError("inspection must be an AxiomBraid inspection mapping.")

    cfg = normalize_quality_profile_config(config)
    weights = cfg["weights"]
    thresholds = cfg["rating_thresholds"]
    rows, columns = dataframe.shape
    total_cells = int(rows * columns)

    # Completeness: direct cell-level missingness.
    missing_cells = int(dataframe.isna().sum().sum())
    missing_percentage = (
        (missing_cells / total_cells) * 100 if total_cells else 100.0
    )
    completeness = _dimension(
        score=100.0 - missing_percentage,
        weight=weights["completeness"],
        explanation="Measures how much of the dataset is populated rather than missing.",
        evidence={
            "total_cells": total_cells,
            "missing_cells": missing_cells,
            "missing_percentage": round(missing_percentage, 2),
        },
        recommendation=(
            "Review missing values and choose a domain-appropriate strategy before imputation."
            if missing_cells
            else "No missing cells were detected."
        ),
        thresholds=thresholds,
    )

    # Uniqueness: direct row-level duplicate rate.
    duplicate_rows = int(dataframe.duplicated().sum()) if rows else 0
    duplicate_percentage = (duplicate_rows / rows * 100) if rows else 100.0
    uniqueness = _dimension(
        score=100.0 - duplicate_percentage,
        weight=weights["uniqueness"],
        explanation="Measures row-level uniqueness using exact duplicate detection.",
        evidence={
            "rows": int(rows),
            "duplicate_rows": duplicate_rows,
            "duplicate_percentage": round(duplicate_percentage, 2),
        },
        recommendation=(
            "Review and remove only confirmed duplicate records."
            if duplicate_rows
            else "No exact duplicate rows were detected."
        ),
        thresholds=thresholds,
    )

    # Validity: supported conservative numeric-range rules only.
    range_issues = inspection.get("numeric_range_issues", {}) or {}
    invalid_numeric_cells = sum(
        int(details.get("count", 0)) for details in range_issues.values()
    )
    covered_columns = [
        column for column in range_issues if column in dataframe.columns
    ]
    # The denominator uses columns for which the detector actually found a
    # supported rule violation.  When no violation is found, fall back to all
    # numerical non-missing cells and state the detector coverage limitation.
    numerical_columns = list(
        (inspection.get("column_groups", {}) or {}).get("numerical", [])
    )
    numerical_non_missing = sum(
        int(dataframe[column].notna().sum())
        for column in numerical_columns
        if column in dataframe.columns
    )
    invalid_percentage = (
        invalid_numeric_cells / numerical_non_missing * 100
        if numerical_non_missing
        else 0.0
    )
    validity = _dimension(
        score=100.0 - invalid_percentage,
        weight=weights["validity"],
        explanation=(
            "Measures values that violate AxiomBraid's supported conservative numeric range rules."
        ),
        evidence={
            "invalid_numeric_cells": invalid_numeric_cells,
            "numerical_non_missing_cells": numerical_non_missing,
            "invalid_percentage": round(invalid_percentage, 2),
            "affected_columns": covered_columns,
            "supported_rule_count": len(range_issues),
        },
        recommendation=(
            "Verify flagged values against source data and domain rules."
            if invalid_numeric_cells
            else "No violations were detected by the currently supported numeric range rules."
        ),
        thresholds=thresholds,
        coverage_note=(
            "A score of 100 means no supported range-rule violations were detected; "
            "it does not prove universal domain validity."
        ),
    )

    # Consistency: normalized text variants plus a light representation penalty
    # for strongly date-like strings stored as generic text.
    text_inconsistencies = inspection.get("text_inconsistencies", {}) or {}
    text_affected_cells = _text_inconsistency_cells(
        dataframe, text_inconsistencies
    )
    categorical_columns = list(
        (inspection.get("column_groups", {}) or {}).get("categorical", [])
    )
    categorical_non_missing = sum(
        int(dataframe[column].notna().sum())
        for column in categorical_columns
        if column in dataframe.columns
    )
    date_like = inspection.get("date_like_text_columns", {}) or {}
    date_like_cells = sum(
        int(details.get("parsed_count", 0)) for details in date_like.values()
    )
    weighted_date_like_cells = (
        date_like_cells * float(cfg["date_like_consistency_weight"])
    )
    inconsistency_units = text_affected_cells + weighted_date_like_cells
    inconsistency_percentage = (
        inconsistency_units / categorical_non_missing * 100
        if categorical_non_missing
        else 0.0
    )
    consistency = _dimension(
        score=100.0 - inconsistency_percentage,
        weight=weights["consistency"],
        explanation=(
            "Measures inconsistent text representation and lightly weights strongly date-like text stored as generic text."
        ),
        evidence={
            "text_inconsistency_columns": list(text_inconsistencies),
            "text_inconsistency_affected_cells": text_affected_cells,
            "date_like_text_columns": list(date_like),
            "date_like_parsed_cells": date_like_cells,
            "date_like_weight": float(cfg["date_like_consistency_weight"]),
            "categorical_non_missing_cells": categorical_non_missing,
            "estimated_inconsistency_percentage": round(
                inconsistency_percentage, 2
            ),
        },
        recommendation=(
            "Standardize confirmed equivalent text variants and review date-like text types."
            if inconsistency_units
            else "No supported representation inconsistencies were detected."
        ),
        thresholds=thresholds,
        coverage_note=(
            "Consistency is estimated from the representation checks currently supported by AxiomBraid."
        ),
    )

    # Integrity: current observable structural integrity signal is constant
    # columns.  Identifier columns are not penalized because valid IDs are often
    # necessary.  Referential integrity requires external keys/contracts and is
    # intentionally not claimed here.
    constant_columns = list(
        (inspection.get("special_columns", {}) or {}).get("constant", [])
    )
    constant_percentage = (
        len(constant_columns) / columns * 100 if columns else 100.0
    )
    integrity = _dimension(
        score=100.0 - constant_percentage,
        weight=weights["integrity"],
        explanation=(
            "Measures currently observable structural usefulness through constant-column detection."
        ),
        evidence={
            "column_count": int(columns),
            "constant_columns": constant_columns,
            "constant_column_percentage": round(constant_percentage, 2),
        },
        recommendation=(
            "Review constant columns and keep them only when they carry required context."
            if constant_columns
            else "No constant columns were detected."
        ),
        thresholds=thresholds,
        coverage_note=(
            "This is not referential-integrity validation; cross-table integrity requires explicit contracts or keys."
        ),
    )

    dimensions = {
        "completeness": completeness,
        "uniqueness": uniqueness,
        "validity": validity,
        "consistency": consistency,
        "integrity": integrity,
    }
    overall = round(
        sum(
            float(dimensions[name]["score"]) * float(weights[name])
            for name in _DIMENSIONS
        ),
        2,
    )

    sorted_dimensions = sorted(
        dimensions.items(), key=lambda item: float(item[1]["score"])
    )
    priorities = [
        {
            "dimension": name,
            "score": details["score"],
            "recommendation": details["recommendation"],
        }
        for name, details in sorted_dimensions
        if float(details["score"]) < 90.0
    ]
    strengths = [
        {
            "dimension": name,
            "score": details["score"],
        }
        for name, details in sorted_dimensions
        if float(details["score"]) >= 95.0
    ]
    legacy_score = (
        inspection.get("data_quality", {}) or {}
    ).get("score")

    return {
        "profile_version": "2.0",
        "method": "weighted_explainable_dimensions",
        "score": overall,
        "rating": _rating(overall, thresholds),
        "dimensions": dimensions,
        "weights": dict(weights),
        "lowest_dimension": {
            "name": sorted_dimensions[0][0],
            "score": sorted_dimensions[0][1]["score"],
        },
        "priorities": priorities,
        "strengths": strengths,
        "legacy_compatibility_score": legacy_score,
        "score_difference_from_legacy": (
            round(overall - float(legacy_score), 2)
            if legacy_score is not None
            else None
        ),
        "note": (
            "This explainable score summarizes checks AxiomBraid can observe. "
            "It is a transparent heuristic, not a universal scientific standard "
            "or proof of domain correctness."
        ),
        "configuration": cfg,
    }


def format_quality_profile_console(
    profile: Mapping[str, Any],
    *,
    language: str = "en",
    details: str = "full",
) -> str:
    """Format a quality profile for readable terminal output."""

    normalized_details = str(details).strip().lower()
    if normalized_details not in {"summary", "full"}:
        raise ValueError("quality details must be 'summary' or 'full'.")

    roman = str(language).strip().lower() == "roman_urdu"
    lines: list[str] = []
    if roman:
        lines.extend(
            [
                "EXPLAINABLE DATA QUALITY PROFILE",
                f"- Overall score: {profile['score']}/100",
                f"- Rating: {profile['rating']}",
                f"- Sab se kamzor dimension: {profile['lowest_dimension']['name'].title()} ({profile['lowest_dimension']['score']}/100)",
            ]
        )
    else:
        lines.extend(
            [
                "EXPLAINABLE DATA QUALITY PROFILE",
                f"- Overall score: {profile['score']}/100",
                f"- Rating: {profile['rating']}",
                f"- Lowest dimension: {profile['lowest_dimension']['name'].title()} ({profile['lowest_dimension']['score']}/100)",
            ]
        )

    if normalized_details == "summary":
        lines.append("- Dimensions: " + ", ".join(
            f"{name.title()} {item['score']}/100"
            for name, item in profile["dimensions"].items()
        ))
        return "\n".join(lines)

    lines.append("")
    for name, item in profile["dimensions"].items():
        lines.append(
            f"{name.title()}: {item['score']}/100 ({item['rating']}) | Weight: {int(round(float(item['weight']) * 100))}%"
        )
        lines.append(f"  Why: {item['explanation']}")
        lines.append(f"  Action: {item['recommendation']}")
        if item.get("coverage_note"):
            lines.append(f"  Note: {item['coverage_note']}")
    lines.append("")
    lines.append(str(profile["note"]))
    return "\n".join(lines)
