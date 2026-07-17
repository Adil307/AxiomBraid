"""Explainable confidence scoring for AxiomBraid issue findings.

Version 2 confidence scores represent deterministic evidence strength, not
calibrated statistical probabilities. Phase 2 adds detector-specific evidence,
per-column confidence, configurable thresholds, compact reports, and Phase 3 human-friendly presentation helpers.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any


DEFAULT_CONFIDENCE_CONFIG: dict[str, Any] = {
    "level_thresholds": {
        "high": 0.90,
        "medium": 0.75,
    },
    "severity_adjustments": {
        "high": 0.04,
        "medium": 0.02,
        "low": 0.01,
        "info": 0.00,
    },
    "detectors": {
        "text_inconsistencies": {"base_score": 0.82},
        "potential_outliers": {"base_score": 0.68},
        "suspicious_numeric_ranges": {"base_score": 0.84},
        "date_like_text": {"base_score": 0.78},
        "possible_identifiers": {"base_score": 0.78},
        "high_cardinality_descriptive": {"base_score": 0.80},
        "unknown": {"base_score": 0.70},
    },
}

_EXACT_CODES = {
    "missing_values",
    "duplicate_rows",
    "constant_columns",
    "empty_dataset",
    "no_numerical_columns",
}


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = deepcopy(value)
    return result


def normalize_confidence_config(
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return a validated confidence configuration merged with safe defaults."""
    if config is None:
        return deepcopy(DEFAULT_CONFIDENCE_CONFIG)
    if not isinstance(config, dict):
        raise TypeError("confidence config must be a dictionary or None.")

    allowed = {"level_thresholds", "severity_adjustments", "detectors"}
    unexpected = sorted(set(config) - allowed)
    if unexpected:
        raise ValueError(
            "Unsupported confidence configuration section(s): "
            + ", ".join(unexpected)
        )

    merged = _deep_merge(DEFAULT_CONFIDENCE_CONFIG, config)

    thresholds = merged["level_thresholds"]
    high = _number_between_zero_and_one(thresholds.get("high"), "high threshold")
    medium = _number_between_zero_and_one(
        thresholds.get("medium"), "medium threshold"
    )
    if medium > high:
        raise ValueError("The medium confidence threshold cannot exceed high.")

    for severity, value in merged["severity_adjustments"].items():
        merged["severity_adjustments"][severity] = _number_between_zero_and_one(
            value, f"severity adjustment '{severity}'"
        )

    if not isinstance(merged["detectors"], dict):
        raise TypeError("confidence config 'detectors' must be a dictionary.")
    for code, settings in merged["detectors"].items():
        if not isinstance(settings, dict):
            raise TypeError(f"Detector confidence settings for '{code}' must be a dictionary.")
        if "base_score" not in settings:
            raise ValueError(f"Detector confidence settings for '{code}' need base_score.")
        settings["base_score"] = _number_between_zero_and_one(
            settings["base_score"], f"base score for '{code}'"
        )

    return merged


def _number_between_zero_and_one(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a number between 0 and 1.")
    number = float(value)
    if not 0.0 <= number <= 1.0:
        raise ValueError(f"{name} must be between 0 and 1.")
    return number


def _clamp(score: float) -> float:
    return round(max(0.0, min(1.0, float(score))), 2)


def _level(score: float, config: dict[str, Any]) -> str:
    thresholds = config["level_thresholds"]
    if score >= float(thresholds["high"]):
        return "high"
    if score >= float(thresholds["medium"]):
        return "medium"
    return "low"


def _base_score(code: str, config: dict[str, Any]) -> float:
    detector = config["detectors"].get(code, config["detectors"]["unknown"])
    return float(detector["base_score"])


def _severity_bonus(severity: str, config: dict[str, Any]) -> float:
    return float(config["severity_adjustments"].get(severity, 0.0))


def _column_result(
    *,
    score: float,
    evidence: str,
    method: str,
    factors: dict[str, Any],
    config: dict[str, Any],
) -> dict[str, Any]:
    normalized = _clamp(score)
    return {
        "score": normalized,
        "level": _level(normalized, config),
        "method": method,
        "evidence": evidence,
        "factors": factors,
        "is_probability": False,
    }


def _per_column_confidence(
    issue: dict[str, Any],
    context: dict[str, Any] | None,
    config: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    code = str(issue.get("code", "unknown"))
    severity = str(issue.get("severity", "info")).lower()
    columns = issue.get("columns", [])
    if not isinstance(columns, list):
        return {}

    context = context or {}
    results: dict[str, dict[str, Any]] = {}

    for column in columns:
        column_name = str(column)

        if code == "missing_values":
            detail = context.get("missing_values", {}).get(column_name, {})
            count = int(detail.get("count", 0))
            percentage = float(detail.get("percentage", 0.0))
            results[column_name] = _column_result(
                score=1.0,
                method="deterministic_rule",
                evidence=(
                    f"Direct null-count check found {count} missing value(s) "
                    f"in '{column_name}' ({percentage:.2f}%)."
                ),
                factors={"missing_count": count, "missing_percentage": percentage},
                config=config,
            )
            continue

        if code == "constant_columns":
            results[column_name] = _column_result(
                score=1.0,
                method="deterministic_rule",
                evidence=(
                    f"'{column_name}' was directly identified as constant by the "
                    "dataset inspection rule."
                ),
                factors={"direct_check": True},
                config=config,
            )
            continue

        if code == "text_inconsistencies":
            groups = context.get("text_inconsistencies", {}).get(column_name, [])
            group_count = len(groups) if isinstance(groups, list) else 0
            variant_count = 0
            if isinstance(groups, list):
                variant_count = sum(
                    len(group.get("variants", []))
                    for group in groups
                    if isinstance(group, dict)
                )
            score = (
                _base_score(code, config)
                + min(0.10, group_count * 0.02 + variant_count * 0.01)
                + _severity_bonus(severity, config)
            )
            results[column_name] = _column_result(
                score=score,
                method="detector_specific_heuristic",
                evidence=(
                    f"'{column_name}' contains {group_count} normalized text group(s) "
                    f"with {variant_count} observed variant form(s)."
                ),
                factors={
                    "normalized_group_count": group_count,
                    "variant_count": variant_count,
                },
                config=config,
            )
            continue

        if code == "potential_outliers":
            detail = context.get("outliers", {}).get(column_name, {})
            percentage = float(detail.get("percentage", issue.get("metric", 0.0)) or 0.0)
            count = int(detail.get("count", 0) or 0)
            score = (
                _base_score(code, config)
                + min(0.15, percentage / 100.0 * 0.50)
                + _severity_bonus(severity, config)
            )
            results[column_name] = _column_result(
                score=score,
                method="detector_specific_heuristic",
                evidence=(
                    f"IQR screening found {count} potential outlier(s) in "
                    f"'{column_name}' ({percentage:.2f}%). Bounds: "
                    f"{detail.get('lower_bound')!r} to {detail.get('upper_bound')!r}."
                ),
                factors={
                    "outlier_count": count,
                    "outlier_percentage": percentage,
                    "lower_bound": detail.get("lower_bound"),
                    "upper_bound": detail.get("upper_bound"),
                    "iqr_multiplier": detail.get("iqr_multiplier"),
                },
                config=config,
            )
            continue

        if code == "suspicious_numeric_ranges":
            detail = context.get("numeric_range_issues", {}).get(column_name, {})
            percentage = float(detail.get("percentage", issue.get("metric", 0.0)) or 0.0)
            count = int(detail.get("count", 0) or 0)
            score = (
                _base_score(code, config)
                + min(0.10, percentage / 100.0 * 0.40)
                + _severity_bonus(severity, config)
            )
            results[column_name] = _column_result(
                score=score,
                method="detector_specific_heuristic",
                evidence=(
                    f"Conservative range rule '{detail.get('rule', 'unknown')}' found "
                    f"{count} value(s) outside the expected range for '{column_name}' "
                    f"({percentage:.2f}%)."
                ),
                factors={
                    "rule": detail.get("rule"),
                    "invalid_count": count,
                    "invalid_percentage": percentage,
                    "expected_minimum": detail.get("expected_minimum"),
                    "expected_maximum": detail.get("expected_maximum"),
                },
                config=config,
            )
            continue

        if code == "date_like_text":
            detail = context.get("date_like_text_columns", {}).get(column_name, {})
            parse_percentage = float(detail.get("parse_percentage", 0.0) or 0.0)
            non_missing = int(detail.get("non_missing_count", 0) or 0)
            parsed = int(detail.get("parsed_count", 0) or 0)
            score = (
                _base_score(code, config)
                + min(0.17, parse_percentage / 100.0 * 0.17)
                + _severity_bonus(severity, config)
            )
            results[column_name] = _column_result(
                score=score,
                method="detector_specific_heuristic",
                evidence=(
                    f"'{column_name}' parsed {parsed} of {non_missing} non-missing "
                    f"values as dates ({parse_percentage:.2f}%)."
                ),
                factors={
                    "parsed_count": parsed,
                    "non_missing_count": non_missing,
                    "parse_percentage": parse_percentage,
                    "suggested_dtype": detail.get("suggested_dtype"),
                },
                config=config,
            )
            continue

        # Identifier and high-cardinality findings currently expose column-level
        # detector membership, but not the original raw uniqueness ratio in the
        # inspection result. Keep their score transparent and conservative.
        score = _base_score(code, config) + _severity_bonus(severity, config)
        results[column_name] = _column_result(
            score=score,
            method="detector_specific_heuristic",
            evidence=(
                f"'{column_name}' was selected by AxiomBraid's '{code}' detector. "
                "The score reflects detector evidence strength, not probability."
            ),
            factors={"detector": code, "severity": severity},
            config=config,
        )

    return results



_ISSUE_NAMES: dict[str, dict[str, str]] = {
    "missing_values": {"en": "Missing Values", "roman_urdu": "Missing Values"},
    "duplicate_rows": {"en": "Duplicate Rows", "roman_urdu": "Duplicate Rows"},
    "constant_columns": {"en": "Constant Columns", "roman_urdu": "Constant Columns"},
    "text_inconsistencies": {"en": "Text Inconsistencies", "roman_urdu": "Text Inconsistencies"},
    "potential_outliers": {"en": "Potential Outliers", "roman_urdu": "Potential Outliers"},
    "suspicious_numeric_ranges": {"en": "Suspicious Numeric Ranges", "roman_urdu": "Mashkook Numeric Ranges"},
    "date_like_text": {"en": "Date-Like Text", "roman_urdu": "Date Jaisa Text"},
    "possible_identifiers": {"en": "Possible Identifiers", "roman_urdu": "Mumkin Identifier Columns"},
    "high_cardinality_descriptive": {"en": "High-Cardinality Descriptive Columns", "roman_urdu": "Zyada Unique Descriptive Columns"},
    "empty_dataset": {"en": "Empty Dataset", "roman_urdu": "Khali Dataset"},
    "no_numerical_columns": {"en": "No Numerical Columns", "roman_urdu": "Numerical Columns Nahi"},
}


def _language(value: str | None) -> str:
    normalized = str(value or "en").strip().lower().replace("-", "_")
    return "roman_urdu" if normalized in {"roman_urdu", "romanurdu", "ur"} else "en"


def humanize_issue_code(code: str, *, language: str = "en") -> str:
    """Return a user-friendly display name for an inspection issue code."""
    language_code = _language(language)
    labels = _ISSUE_NAMES.get(str(code), {})
    if language_code in labels:
        return labels[language_code]
    return str(code).replace("_", " ").strip().title() or "Unknown Issue"


def _first_column_details(confidence: dict[str, Any]) -> tuple[str | None, dict[str, Any]]:
    per_column = confidence.get("per_column", {})
    if isinstance(per_column, dict) and per_column:
        column = next(iter(per_column))
        details = per_column[column]
        return str(column), details if isinstance(details, dict) else {}
    return None, {}


def simple_issue_evidence(issue: dict[str, Any], *, language: str = "en") -> str:
    """Return concise evidence phrased for a normal user rather than a developer."""
    language_code = _language(language)
    code = str(issue.get("code", "unknown"))
    confidence = issue.get("confidence", {}) if isinstance(issue, dict) else {}
    if not isinstance(confidence, dict):
        confidence = {}
    column, details = _first_column_details(confidence)
    factors = details.get("factors", {}) if isinstance(details, dict) else {}
    if not isinstance(factors, dict):
        factors = {}

    if code == "potential_outliers" and column:
        count = factors.get("outlier_count", 0)
        percentage = factors.get("outlier_percentage", 0.0)
        lower = factors.get("lower_bound")
        upper = factors.get("upper_bound")
        if language_code == "roman_urdu":
            return (
                f"'{column}' mein {count} mumkin outlier mila ({percentage:.2f}%). "
                f"IQR range {lower} se {upper} tak hai."
            )
        return (
            f"{count} potential outlier(s) were detected in '{column}' "
            f"({percentage:.2f}%). The IQR range is {lower} to {upper}."
        )

    if code == "suspicious_numeric_ranges" and column:
        count = factors.get("invalid_count", 0)
        percentage = factors.get("invalid_percentage", 0.0)
        minimum = factors.get("expected_minimum")
        maximum = factors.get("expected_maximum")
        if language_code == "roman_urdu":
            return (
                f"'{column}' mein {count} value expected range {minimum} se {maximum} "
                f"ke bahar hai ({percentage:.2f}%)."
            )
        return (
            f"{count} value(s) in '{column}' fall outside the expected range "
            f"{minimum} to {maximum} ({percentage:.2f}%)."
        )

    if code == "constant_columns" and column:
        if language_code == "roman_urdu":
            return f"'{column}' ke tamam observed non-missing values aik jaisay hain."
        return f"All observed non-missing values in '{column}' are identical."

    if code == "text_inconsistencies" and column:
        groups = factors.get("normalized_group_count", 0)
        variants = factors.get("variant_count", 0)
        if language_code == "roman_urdu":
            return (
                f"'{column}' mein {groups} text group(s) case ya spacing ki wajah se "
                f"{variants} mukhtalif forms mein nazar aaye."
            )
        return (
            f"'{column}' contains {groups} text group(s) represented by {variants} "
            "case/spacing variants."
        )

    if code == "date_like_text" and column:
        parsed = factors.get("parsed_count", 0)
        total = factors.get("non_missing_count", 0)
        percentage = factors.get("parse_percentage", 0.0)
        if language_code == "roman_urdu":
            return (
                f"'{column}' ke {parsed}/{total} non-missing values date jaisay parse huay "
                f"({percentage:.2f}%)."
            )
        return (
            f"{parsed} of {total} non-missing values in '{column}' look like dates "
            f"({percentage:.2f}%)."
        )

    if code == "possible_identifiers" and column:
        if language_code == "roman_urdu":
            return f"'{column}' ko identifier detector ne mumkin ID column ke taur par flag kiya."
        return f"'{column}' was flagged as a possible identifier column."

    if code == "missing_values" and column:
        count = factors.get("missing_count", 0)
        percentage = factors.get("missing_percentage", 0.0)
        if language_code == "roman_urdu":
            return f"'{column}' mein {count} missing value(s) hain ({percentage:.2f}%)."
        return f"'{column}' contains {count} missing value(s) ({percentage:.2f}%)."

    columns = issue.get("columns", []) if isinstance(issue, dict) else []
    columns_text = ", ".join(map(str, columns)) if isinstance(columns, list) else ""
    name = humanize_issue_code(code, language=language_code)
    if language_code == "roman_urdu":
        return f"AxiomBraid ne {name} detect kiya" + (f" in: {columns_text}." if columns_text else ".")
    return f"AxiomBraid detected {name.lower()}" + (f" in: {columns_text}." if columns_text else ".")


def confidence_recommendation(issue: dict[str, Any], *, language: str = "en") -> str:
    """Return a confidence-aware, safety-first recommended action for an issue."""
    language_code = _language(language)
    code = str(issue.get("code", "unknown"))
    confidence = issue.get("confidence", {}) if isinstance(issue, dict) else {}
    level = str(confidence.get("level", "low")) if isinstance(confidence, dict) else "low"

    en = {
        "potential_outliers": "Review the flagged values before changing or removing them; valid rare values should be kept.",
        "suspicious_numeric_ranges": "Verify the flagged values against source data or business rules before correcting them.",
        "constant_columns": "Review whether the column is useful; do not drop it automatically without checking its purpose.",
        "text_inconsistencies": "Confirm that the variants mean the same thing, then normalize case and spacing.",
        "date_like_text": "Review values that did not parse, then convert the column to datetime when appropriate.",
        "possible_identifiers": "Confirm that the column is truly an identifier before excluding it from analysis or modeling.",
        "high_cardinality_descriptive": "Review whether the column is descriptive text, an identifier, or suitable for grouping before encoding it.",
        "missing_values": "Choose imputation, removal, or manual correction based on the column meaning and missingness level.",
        "duplicate_rows": "Review the duplicate records and remove them only when they are unintended duplicates.",
    }
    ur = {
        "potential_outliers": "Flagged values ko change ya remove karne se pehle review karein; valid rare values ko rehne dein.",
        "suspicious_numeric_ranges": "Correction se pehle values ko source data ya business rules ke sath verify karein.",
        "constant_columns": "Column ka purpose check karein; bina review ke automatically drop na karein.",
        "text_inconsistencies": "Pehle confirm karein ke variants ka meaning same hai, phir case aur spacing normalize karein.",
        "date_like_text": "Jo values parse nahi hui unko review karein, phir zarurat ho to datetime mein convert karein.",
        "possible_identifiers": "Modeling ya analysis se exclude karne se pehle confirm karein ke yeh waqai identifier hai.",
        "high_cardinality_descriptive": "Encoding se pehle check karein ke column descriptive text hai, identifier hai, ya grouping ke liye suitable hai.",
        "missing_values": "Column ke meaning aur missingness ko dekh kar imputation, removal, ya manual correction choose karein.",
        "duplicate_rows": "Duplicate records ko review karein aur sirf unintended duplicates ko remove karein.",
    }
    mapping = ur if language_code == "roman_urdu" else en
    recommendation = mapping.get(
        code,
        "Issue ko available evidence aur domain context ke sath review karein."
        if language_code == "roman_urdu"
        else "Review the issue using the available evidence and domain context.",
    )
    if level == "low":
        prefix = (
            "Low confidence: manual review zaroor karein. "
            if language_code == "roman_urdu"
            else "Low confidence: manual review is strongly recommended. "
        )
        return prefix + recommendation
    return recommendation


def format_confidence_console(
    inspection_result: dict[str, Any],
    *,
    language: str | None = None,
    details: str = "full",
) -> str:
    """Format confidence information as a clean, human-readable console section."""
    if not isinstance(inspection_result, dict):
        raise TypeError("inspection_result must be a dictionary.")
    normalized_details = str(details).strip().lower()
    if normalized_details not in {"summary", "full"}:
        raise ValueError("details must be 'summary' or 'full'.")

    language_code = _language(language or inspection_result.get("language", "en"))
    if "confidence_summary" not in inspection_result:
        inspection_result = add_confidence(inspection_result)
    summary = inspection_result["confidence_summary"]
    counts = summary["level_counts"]

    if language_code == "roman_urdu":
        lines = [
            "CONFIDENCE / AITMAAD OVERVIEW",
            f"- Assess kiye gaye issues: {summary['issue_count']}",
            f"- High confidence: {counts['high']}",
            f"- Medium confidence: {counts['medium']}",
            f"- Low confidence: {counts['low']}",
            f"- Average evidence strength: {int(round((summary['average_score'] or 0) * 100))}%",
        ]
    else:
        lines = [
            "CONFIDENCE OVERVIEW",
            f"- Issues assessed: {summary['issue_count']}",
            f"- High confidence: {counts['high']}",
            f"- Medium confidence: {counts['medium']}",
            f"- Low confidence: {counts['low']}",
            f"- Average evidence strength: {int(round((summary['average_score'] or 0) * 100))}%",
        ]

    if normalized_details == "full" and inspection_result.get("issues"):
        lines.append("")
        lines.append("CONFIDENCE DETAILS" if language_code == "en" else "CONFIDENCE DETAILS / TAFSEEL")
        for index, issue in enumerate(inspection_result["issues"], start=1):
            confidence = issue.get("confidence", {})
            score = int(round(float(confidence.get("score", 0.0)) * 100))
            level = str(confidence.get("level", "low")).upper()
            severity = str(issue.get("severity", "info")).upper()
            columns = issue.get("columns", [])
            columns_text = ", ".join(map(str, columns)) if columns else "-"
            lines.extend(
                [
                    "-" * 72,
                    f"{index}. {humanize_issue_code(str(issue.get('code', 'unknown')), language=language_code)}",
                    f"   Severity: {severity}",
                    f"   Confidence: {score}% ({level})",
                    f"   Column(s): {columns_text}",
                    f"   Evidence: {simple_issue_evidence(issue, language=language_code)}",
                    f"   Recommended action: {confidence_recommendation(issue, language=language_code)}",
                ]
            )

    lines.append("")
    lines.append(
        "Note: Confidence scores represent evidence strength, not statistical probability."
        if language_code == "en"
        else "Note: Confidence score evidence ki strength dikhata hai, statistical probability nahi."
    )
    return "\n".join(lines)

def issue_confidence(
    issue: dict[str, Any],
    *,
    context: dict[str, Any] | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return an explainable confidence assessment for one inspection issue.

    ``context`` may be a complete inspection result. When available, Phase 2 uses
    detector-specific details to build richer evidence and per-column confidence.
    The returned score is deterministic evidence strength in the range 0.0-1.0;
    it must not be interpreted as a calibrated probability.
    """
    if not isinstance(issue, dict):
        raise TypeError("issue must be a dictionary.")
    if context is not None and not isinstance(context, dict):
        raise TypeError("context must be a dictionary or None.")

    normalized_config = normalize_confidence_config(config)
    code = str(issue.get("code", "unknown"))
    severity = str(issue.get("severity", "info")).lower()
    metric_name = str(issue.get("metric_name", "metric"))
    metric = issue.get("metric")

    per_column = _per_column_confidence(issue, context, normalized_config)

    if code in _EXACT_CODES:
        score = 1.0
        method = "deterministic_rule"
        evidence = (
            f"'{code}' is produced by a direct deterministic dataset check; "
            f"{metric_name}={metric!r}."
        )
        factors = {
            "detector": code,
            "severity": severity,
            "direct_check": True,
            "metric_name": metric_name,
            "metric": metric,
        }
    elif per_column:
        scores = [details["score"] for details in per_column.values()]
        score = sum(scores) / len(scores)
        method = "detector_specific_heuristic"
        evidence = (
            f"'{code}' confidence is aggregated from {len(per_column)} "
            "column-level detector assessment(s)."
        )
        factors = {
            "detector": code,
            "severity": severity,
            "column_count": len(per_column),
            "aggregation": "mean",
            "metric_name": metric_name,
            "metric": metric,
        }
    else:
        score = _base_score(code, normalized_config) + _severity_bonus(
            severity, normalized_config
        )
        method = "explainable_heuristic"
        evidence = (
            f"'{code}' uses a transparent detector-level heuristic; "
            f"severity={severity}, {metric_name}={metric!r}."
        )
        factors = {
            "detector": code,
            "severity": severity,
            "base_score": _base_score(code, normalized_config),
            "severity_adjustment": _severity_bonus(severity, normalized_config),
            "metric_name": metric_name,
            "metric": metric,
        }

    normalized_score = _clamp(score)
    result = {
        "score": normalized_score,
        "level": _level(normalized_score, normalized_config),
        "method": method,
        "evidence": evidence,
        "factors": factors,
        "per_column": per_column,
        "is_probability": False,
    }
    presentation_issue = dict(issue)
    presentation_issue["confidence"] = result
    language = _language((context or {}).get("language", "en"))
    result["display_name"] = humanize_issue_code(code, language=language)
    result["simple_evidence"] = simple_issue_evidence(presentation_issue, language=language)
    result["recommended_action"] = confidence_recommendation(presentation_issue, language=language)
    return result


def add_confidence(
    inspection_result: dict[str, Any],
    *,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return a deep-copied inspection result with Phase 2 confidence metadata."""
    if not isinstance(inspection_result, dict):
        raise TypeError("inspection_result must be a dictionary.")

    normalized_config = normalize_confidence_config(config)
    result = deepcopy(inspection_result)
    issues = result.get("issues", [])
    if not isinstance(issues, list):
        raise TypeError("inspection_result['issues'] must be a list.")

    counts = {"high": 0, "medium": 0, "low": 0}
    detector_counts: dict[str, int] = {}
    scores: list[float] = []

    for issue in issues:
        if not isinstance(issue, dict):
            raise TypeError("Each inspection issue must be a dictionary.")
        confidence = issue_confidence(
            issue,
            context=result,
            config=normalized_config,
        )
        issue["confidence"] = confidence
        counts[confidence["level"]] += 1
        code = str(issue.get("code", "unknown"))
        detector_counts[code] = detector_counts.get(code, 0) + 1
        scores.append(float(confidence["score"]))

    average = round(sum(scores) / len(scores), 2) if scores else None
    result["confidence_summary"] = {
        "issue_count": len(issues),
        "level_counts": counts,
        "average_score": average,
        "lowest_score": round(min(scores), 2) if scores else None,
        "highest_score": round(max(scores), 2) if scores else None,
        "detector_counts": detector_counts,
        "level_thresholds": deepcopy(normalized_config["level_thresholds"]),
        "note": (
            "Confidence scores represent deterministic evidence strength, "
            "not calibrated statistical probabilities."
        ),
    }
    result["confidence_recommendations"] = [
        {
            "code": issue.get("code"),
            "display_name": issue.get("confidence", {}).get("display_name"),
            "columns": deepcopy(issue.get("columns", [])),
            "confidence_score": issue.get("confidence", {}).get("score"),
            "confidence_level": issue.get("confidence", {}).get("level"),
            "recommended_action": issue.get("confidence", {}).get("recommended_action"),
        }
        for issue in issues
    ]
    return result


def confidence_report(
    inspection_result: dict[str, Any],
    *,
    config: dict[str, Any] | None = None,
    display: bool = False,
    language: str | None = None,
    details: str = "full",
) -> dict[str, Any]:
    """Return a compact confidence-only view and optionally print a readable report.

    ``display=False`` preserves the Phase 2 machine-readable behavior.
    ``display=True`` prints a clean human-facing confidence report without exposing
    nested implementation dictionaries.
    """
    enhanced = add_confidence(inspection_result, config=config)
    rows = []
    for issue in enhanced.get("issues", []):
        confidence = issue["confidence"]
        rows.append(
            {
                "code": issue.get("code"),
                "severity": issue.get("severity"),
                "columns": deepcopy(issue.get("columns", [])),
                "score": confidence["score"],
                "level": confidence["level"],
                "method": confidence["method"],
                "evidence": confidence["evidence"],
                "per_column": deepcopy(confidence["per_column"]),
            }
        )
    compact = {
        "summary": deepcopy(enhanced["confidence_summary"]),
        "issues": rows,
    }
    if display:
        print(format_confidence_console(enhanced, language=language, details=details))
    return compact

