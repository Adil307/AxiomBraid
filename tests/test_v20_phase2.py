import pandas as pd
import pytest

import axiombraid as AB


def phase2_frame():
    return pd.DataFrame(
        {
            "Employee_ID": ["E1", "E2", "E3", "E4", "E5"],
            "Department": ["HR", " hr ", "Hr", "IT", "it"],
            "Age": [25, 26, 27, 28, 200],
            "JoinDate": [
                "2025-01-01",
                "2025-02-02",
                "not-a-date",
                "2025-03-03",
                "2025-04-04",
            ],
            "Constant": ["X", "X", "X", "X", "X"],
        }
    )


def _issue(result, code):
    return next(item for item in result["issues"] if item["code"] == code)


def test_phase2_alpha_metadata():
    assert AB.__version__ == "2.0.1"
    assert AB.VERSION_INFO == (2, 0, 0)
    assert AB.API_STATUS == "stable"
    assert AB.PUBLIC_API_VERSION == "2"


def test_detector_specific_evidence_and_per_column_confidence():
    result = AB.inspect(phase2_frame(), include_confidence=True)
    issue = _issue(result, "potential_outliers")
    confidence = issue["confidence"]

    assert confidence["method"] == "detector_specific_heuristic"
    assert "Age" in confidence["per_column"]
    age = confidence["per_column"]["Age"]
    assert age["factors"]["outlier_count"] == 1
    assert age["factors"]["upper_bound"] is not None
    assert "IQR screening" in age["evidence"]
    assert age["is_probability"] is False


def test_text_confidence_contains_variant_evidence():
    result = AB.inspect_with_confidence(phase2_frame())
    issue = _issue(result, "text_inconsistencies")
    department = issue["confidence"]["per_column"]["Department"]

    assert department["factors"]["normalized_group_count"] >= 1
    assert department["factors"]["variant_count"] >= 2
    assert "variant form" in department["evidence"]


def test_date_like_confidence_uses_parse_rate():
    result = AB.inspect_with_confidence(phase2_frame())
    issue = _issue(result, "date_like_text")
    join_date = issue["confidence"]["per_column"]["JoinDate"]

    assert join_date["factors"]["parse_percentage"] == 80.0
    assert join_date["factors"]["parsed_count"] == 4
    assert "80.00%" in join_date["evidence"]


def test_exact_column_check_remains_deterministic():
    result = AB.inspect_with_confidence(phase2_frame())
    issue = _issue(result, "constant_columns")
    constant = issue["confidence"]["per_column"]["Constant"]

    assert issue["confidence"]["score"] == 1.0
    assert constant["score"] == 1.0
    assert constant["method"] == "deterministic_rule"


def test_custom_confidence_thresholds_change_level_without_changing_score():
    original = AB.issue_confidence(
        {
            "code": "possible_identifiers",
            "severity": "info",
            "columns": ["Employee_ID"],
            "metric": 1,
            "metric_name": "identifier_column_count",
        }
    )
    custom = AB.issue_confidence(
        {
            "code": "possible_identifiers",
            "severity": "info",
            "columns": ["Employee_ID"],
            "metric": 1,
            "metric_name": "identifier_column_count",
        },
        config={"level_thresholds": {"high": 0.95, "medium": 0.85}},
    )

    assert original["score"] == custom["score"]
    assert original["level"] == "medium"
    assert custom["level"] == "low"


def test_custom_detector_base_score_is_supported():
    issue = {
        "code": "possible_identifiers",
        "severity": "info",
        "columns": [],
        "metric": 1,
        "metric_name": "identifier_column_count",
    }
    confidence = AB.issue_confidence(
        issue,
        config={"detectors": {"possible_identifiers": {"base_score": 0.92}}},
    )
    assert confidence["score"] == 0.92
    assert confidence["level"] == "high"


def test_confidence_report_returns_compact_view():
    inspection = AB.inspect(phase2_frame())
    report = AB.confidence_report(inspection)

    assert report["summary"]["issue_count"] == len(inspection["issues"])
    assert report["issues"]
    assert set(report["issues"][0]) == {
        "code",
        "severity",
        "columns",
        "score",
        "level",
        "method",
        "evidence",
        "per_column",
    }


def test_confidence_summary_contains_aggregate_statistics():
    result = AB.inspect_with_confidence(phase2_frame())
    summary = result["confidence_summary"]

    assert summary["average_score"] is not None
    assert summary["lowest_score"] <= summary["highest_score"]
    assert sum(summary["level_counts"].values()) == summary["issue_count"]
    assert summary["detector_counts"]
    assert summary["level_thresholds"] == {"high": 0.9, "medium": 0.75}


def test_inspect_accepts_confidence_config():
    result = AB.inspect(
        phase2_frame(),
        include_confidence=True,
        confidence_config={"level_thresholds": {"high": 0.99, "medium": 0.98}},
    )
    heuristic = _issue(result, "possible_identifiers")
    assert heuristic["confidence"]["level"] == "low"


def test_default_confidence_config_is_not_mutated_by_normalization():
    normalized = AB.normalize_confidence_config(
        {"level_thresholds": {"high": 0.95}}
    )
    normalized["level_thresholds"]["high"] = 0.50
    assert AB.DEFAULT_CONFIDENCE_CONFIG["level_thresholds"]["high"] == 0.90


def test_invalid_confidence_config_is_rejected():
    with pytest.raises(ValueError):
        AB.normalize_confidence_config({"unknown": {}})

    with pytest.raises(ValueError):
        AB.normalize_confidence_config(
            {"level_thresholds": {"high": 0.70, "medium": 0.80}}
        )

    with pytest.raises(ValueError):
        AB.normalize_confidence_config(
            {"detectors": {"potential_outliers": {"base_score": 1.5}}}
        )


def test_add_confidence_still_does_not_mutate_original():
    original = AB.inspect(phase2_frame())
    enhanced = AB.add_confidence(original)

    assert "confidence_summary" not in original
    assert all("confidence" not in item for item in original["issues"])
    assert "confidence_summary" in enhanced
