import pandas as pd

import axiombraid as AB


def frame():
    return pd.DataFrame({
        "Employee_ID": ["E1", "E2", "E2", "E4"],
        "Department": ["HR", " hr ", " hr ", "IT"],
        "Age": [25, None, None, 200],
    })


def test_phase1_alpha_metadata():
    assert AB.__version__ == "2.0.0"
    assert AB.VERSION_INFO == (2, 0, 0)
    assert AB.API_STATUS == "stable"
    assert AB.PUBLIC_API_VERSION == "2"


def test_default_inspect_remains_backward_compatible():
    result = AB.inspect(frame())
    assert "confidence_summary" not in result
    assert all("confidence" not in issue for issue in result["issues"])


def test_optional_confidence_is_added():
    result = AB.inspect(frame(), include_confidence=True)
    assert "confidence_summary" in result
    assert result["confidence_summary"]["issue_count"] == len(result["issues"])
    assert all("confidence" in issue for issue in result["issues"])


def test_convenience_confidence_inspection():
    result = AB.inspect_with_confidence(frame())
    assert "confidence_summary" in result


def test_direct_issue_confidence_is_explainable_and_not_probability():
    confidence = AB.issue_confidence({
        "code": "potential_outliers",
        "severity": "medium",
        "metric": 12.5,
        "metric_name": "maximum_column_outlier_percentage",
    })
    assert 0.0 <= confidence["score"] <= 1.0
    assert confidence["method"] == "explainable_heuristic"
    assert confidence["is_probability"] is False
    assert "IQR" not in confidence["evidence"] or isinstance(confidence["evidence"], str)


def test_exact_detection_gets_deterministic_confidence():
    confidence = AB.issue_confidence({
        "code": "duplicate_rows",
        "severity": "low",
        "metric": 2.5,
        "metric_name": "duplicate_row_percentage",
    })
    assert confidence["score"] == 1.0
    assert confidence["method"] == "deterministic_rule"


def test_add_confidence_does_not_mutate_original_result():
    original = AB.inspect(frame())
    enhanced = AB.add_confidence(original)
    assert "confidence_summary" not in original
    assert "confidence_summary" in enhanced
    assert all("confidence" not in issue for issue in original["issues"])
