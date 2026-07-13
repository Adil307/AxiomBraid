import json

import pandas as pd
import pytest

import axiombraid
from axiombraid import DataGuide


def test_version():
    assert axiombraid.__version__ == "1.0.1"


def test_shape_missing_and_duplicates():
    df = pd.DataFrame({"name": ["Ali", "Sara", "Sara"], "marks": [80, None, None]})
    result = DataGuide(df).inspect()
    assert result["shape"] == {"rows": 3, "columns": 2}
    assert result["missing_values"]["marks"]["count"] == 2
    assert result["duplicate_rows"] == 1


def test_normalized_cardinality_does_not_flag_department():
    df = pd.DataFrame({
        "Student_ID": ["ST001", "ST002", "ST003", "ST004", "ST005"],
        "Name": ["Ali", "Sara", "Hina", "Usman", "Ayesha"],
        "Department": ["CS", "cs", " CS ", "Zoology", "zoology"],
    })
    special = DataGuide(df).inspect()["special_columns"]
    assert "Student_ID" in special["possible_identifiers"]
    assert "Name" in special["high_cardinality_descriptive"]
    assert "Department" not in special["high_cardinality_descriptive"]


def test_text_inconsistencies_remain_detected():
    df = pd.DataFrame({"Department": ["CS", "cs", " CS ", "Zoology", "zoology"]})
    issues = DataGuide(df).inspect()["text_inconsistencies"]
    assert "Department" in issues
    assert len(issues["Department"]) == 2


def test_outlier_detection_iqr():
    df = pd.DataFrame({"Study_Hours": [2, 3, 3, 4, 4, 5, 5, 50]})
    outliers = DataGuide(df).inspect()["outliers"]
    assert "Study_Hours" in outliers
    assert outliers["Study_Hours"]["count"] == 1
    assert outliers["Study_Hours"]["example_values"] == [50]


def test_outlier_detection_respects_minimum_sample():
    df = pd.DataFrame({"Value": [1, 2, 100]})
    assert DataGuide(df).inspect()["outliers"] == {}


def test_outlier_detection_skips_numeric_identifier():
    df = pd.DataFrame({"Student_ID": [1, 2, 3, 100], "Marks": [70, 75, 80, 85]})
    result = DataGuide(df).inspect()
    assert "Student_ID" in result["special_columns"]["possible_identifiers"]
    assert "Student_ID" not in result["outliers"]


def test_numeric_range_detection():
    df = pd.DataFrame({
        "Age": [18, 20, -5, 22],
        "Attendance": [90, 85, 110, 70],
        "Probability": [0.2, 0.8, 1.4, 0.6],
    })
    issues = DataGuide(df).inspect()["numeric_range_issues"]
    assert issues["Age"]["example_values"] == [-5]
    assert issues["Attendance"]["example_values"] == [110]
    assert issues["Probability"]["example_values"] == [1.4]


def test_unknown_numeric_name_has_no_range_rule():
    df = pd.DataFrame({"Revenue": [-100, 50, 200]})
    assert DataGuide(df).inspect()["numeric_range_issues"] == {}


def test_date_like_text_detection():
    df = pd.DataFrame({
        "Enrollment_Date": ["2024-01-10", "2024/02/15", "15 March 2024", "2024-04-20"],
        "Department": ["CS", "Math", "CS", "Math"],
    })
    detected = DataGuide(df).inspect()["date_like_text_columns"]
    assert "Enrollment_Date" in detected
    assert detected["Enrollment_Date"]["parse_percentage"] == 100.0
    assert "Department" not in detected


def test_date_like_detection_does_not_flag_codes():
    df = pd.DataFrame({"Product_Code": ["AB-2024", "CD-2025", "EF-2026"]})
    assert DataGuide(df).inspect()["date_like_text_columns"] == {}


def test_custom_date_threshold():
    df = pd.DataFrame({"Event_Date": ["2024-01-01", "bad", "2024-03-01", "2024-04-01"]})
    assert "Event_Date" not in DataGuide(df).inspect()["date_like_text_columns"]
    assert "Event_Date" in DataGuide(df, date_like_threshold=0.70).inspect()["date_like_text_columns"]


def test_column_quality_penalties():
    df = pd.DataFrame({"Age": [20, -5, None, 22], "Country": ["PK"] * 4})
    quality = DataGuide(df).inspect()["column_quality"]
    assert quality["Age"]["score"] < 100
    assert quality["Age"]["penalties"]["missing_values"] > 0
    assert quality["Age"]["penalties"]["numeric_range"] > 0
    assert quality["Country"]["penalties"]["constant_column"] == 20.0


def test_clean_quality_score_is_100():
    df = pd.DataFrame({"Department": ["CS", "Math", "CS", "Math"], "Value": [80, 90, 70, 60]})
    quality = DataGuide(df).inspect()["data_quality"]
    assert quality["score"] == 100.0
    assert quality["rating"] == "excellent"


def test_quality_score_reduces_for_new_issues():
    df = pd.DataFrame({
        "Attendance": [80, 85, 90, 150],
        "Event_Date": ["2024-01-01", "2024-02-01", "2024-03-01", "2024-04-01"],
    })
    quality = DataGuide(df).inspect()["data_quality"]
    assert quality["score"] < 100
    assert quality["penalties"]["numeric_ranges"] > 0
    assert quality["penalties"]["date_stored_as_text"] > 0


def test_empty_dataset_score_is_zero():
    quality = DataGuide(pd.DataFrame()).inspect()["data_quality"]
    assert quality["score"] == 0.0
    assert quality["rating"] == "poor"


def test_new_issue_codes_and_sorting():
    df = pd.DataFrame({
        "Attendance": [80, 85, 90, 150],
        "Event_Date": ["2024-01-01", "2024-02-01", "2024-03-01", "2024-04-01"],
    })
    issues = DataGuide(df).inspect()["issues"]
    codes = {item["code"] for item in issues}
    assert "potential_outliers" in codes
    assert "suspicious_numeric_ranges" in codes
    assert "date_like_text" in codes
    order = {"high": 0, "medium": 1, "low": 2, "info": 3}
    severities = [item["severity"] for item in issues]
    assert severities == sorted(severities, key=order.get)


def test_json_export_contains_v06_fields(tmp_path):
    output = DataGuide(pd.DataFrame({"Age": [20, -5, 22, 23]})).export_json(tmp_path / "report")
    data = json.loads(output.read_text(encoding="utf-8"))
    assert "outliers" in data
    assert "numeric_range_issues" in data
    assert "date_like_text_columns" in data
    assert "column_quality" in data


def test_html_export_contains_v06_sections(tmp_path):
    output = DataGuide(pd.DataFrame({"Age": [20, -5, 22, 23]})).export_html(tmp_path / "report")
    html = output.read_text(encoding="utf-8")
    assert "Potential outliers" in html
    assert "Suspicious numeric ranges" in html
    assert "Column quality scores" in html
    assert "Generated by AxiomBraid 1.0.1" in html
    assert "Cleaning plan preview" in html


def test_html_escapes_column_names(tmp_path):
    df = pd.DataFrame({"<script>": [1, 2, 3, 4]})
    output = DataGuide(df).export_html(tmp_path / "safe.html")
    assert "<script>" not in output.read_text(encoding="utf-8")


def test_chart_export(tmp_path):
    pytest.importorskip("matplotlib")
    df = pd.DataFrame({"Marks": [60, 70, 80, 90], "Department": ["CS", "Math", "CS", "Math"]})
    paths = DataGuide(df).export_charts(tmp_path / "charts")
    assert len(paths) == 2
    assert all(path.exists() and path.suffix == ".png" for path in paths)


def test_chart_export_max_charts(tmp_path):
    pytest.importorskip("matplotlib")
    df = pd.DataFrame({"One": [1, 2, 3, 4], "Two": [4, 3, 2, 1]})
    paths = DataGuide(df).export_charts(tmp_path / "charts", max_charts=1)
    assert len(paths) == 1


@pytest.mark.parametrize("kwargs", [
    {"high_cardinality_threshold": 0},
    {"high_cardinality_threshold": 1.1},
    {"min_unique_for_high_cardinality": 1},
    {"structured_identifier_threshold": 0},
    {"low_missing_threshold": 40, "high_missing_threshold": 20},
    {"outlier_iqr_multiplier": 0},
    {"min_outlier_sample_size": 3},
    {"date_like_threshold": 0},
    {"min_date_like_non_missing": 1},
])
def test_invalid_configuration(kwargs):
    with pytest.raises(ValueError):
        DataGuide(pd.DataFrame({"Marks": [80]}), **kwargs)


@pytest.mark.parametrize("kwargs", [
    {"max_categories": 1},
    {"max_charts": 0},
])
def test_invalid_chart_configuration(tmp_path, kwargs):
    with pytest.raises(ValueError):
        DataGuide(pd.DataFrame({"Marks": [80, 90, 70, 60]})).export_charts(tmp_path, **kwargs)


def test_roman_urdu_recommendations_include_new_features():
    df = pd.DataFrame({"Age": [20, -5, 22, 23]})
    recommendations = DataGuide(df).inspect(language="roman_urdu")["recommendations"]
    assert any("range" in text.lower() for text in recommendations)


def test_dataframe_is_copied():
    df = pd.DataFrame({"marks": [70, 80]})
    guide = DataGuide(df)
    guide.dataframe.loc[0, "marks"] = 0
    assert df.loc[0, "marks"] == 70


def test_unsupported_file(tmp_path):
    path = tmp_path / "data.txt"
    path.write_text("sample", encoding="utf-8")
    with pytest.raises(ValueError, match="Unsupported file type"):
        DataGuide(path)


def test_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        DataGuide(tmp_path / "missing.csv")


def test_invalid_input():
    with pytest.raises(TypeError):
        DataGuide(123)



def test_cleaning_plan_is_preview_only():
    df = pd.DataFrame({"Department": ["CS", "cs", " CS "], "Marks": [80, None, 90]})
    guide = DataGuide(df)
    before = guide.dataframe.copy(deep=True)
    plan = guide.cleaning_plan()
    assert plan["preview_only"] is True
    assert guide.dataframe.equals(before)
    assert "normalize_text:Department" in [a["action_id"] for a in plan["actions"]]
    assert "fill_missing_numeric:Marks" in [a["action_id"] for a in plan["actions"]]


def test_low_risk_cleaning_normalizes_and_removes_duplicates():
    df = pd.DataFrame({"Department": ["CS", "cs", "cs"], "Marks": [80, 90, 90]})
    guide = DataGuide(df)
    result = guide.apply_cleaning()
    cleaned = result["dataframe"]
    assert len(cleaned) == 2
    assert cleaned["Department"].tolist() == ["cs", "cs"]
    assert cleaned["Department"].nunique() == 1
    assert guide.dataframe.equals(df)


def test_medium_risk_filling_requires_explicit_maximum():
    df = pd.DataFrame({"Marks": [10, None, 30]})
    guide = DataGuide(df)
    low = guide.apply_cleaning()
    assert pd.isna(low["dataframe"].loc[1, "Marks"])
    medium = guide.apply_cleaning(max_risk="medium")
    assert medium["dataframe"].loc[1, "Marks"] == 20


def test_selected_medium_action_can_be_applied():
    df = pd.DataFrame({"Department": ["CS", None, "CS"]})
    guide = DataGuide(df)
    result = guide.apply_cleaning(
        max_risk="medium",
        selected_actions=["fill_missing_categorical:Department"],
    )
    assert result["dataframe"]["Department"].isna().sum() == 0


def test_manual_outlier_action_is_never_automatically_applied():
    df = pd.DataFrame({"Study_Hours": [1, 2, 2, 50]})
    guide = DataGuide(df)
    plan = guide.cleaning_plan()
    action_id = next(a["action_id"] for a in plan["actions"] if a["operation"] == "manual_review_outliers")
    result = guide.apply_cleaning(
        plan,
        max_risk="medium",
        selected_actions=[action_id],
    )
    assert result["dataframe"]["Study_Hours"].tolist() == [1, 2, 2, 50]
    assert result["skipped_actions"][0]["reason"] == "manual_review_required"


def test_inplace_requires_confirmation():
    guide = DataGuide(pd.DataFrame({"Department": ["CS", "cs"]}))
    with pytest.raises(ValueError, match="confirm=True"):
        guide.apply_cleaning(inplace=True)


def test_inplace_cleaning_and_undo():
    df = pd.DataFrame({"Department": ["CS", "cs"], "Marks": [1, 2]})
    guide = DataGuide(df)
    result = guide.apply_cleaning(inplace=True, confirm=True)
    assert result["can_undo"] is True
    assert guide.dataframe["Department"].nunique() == 1
    undo = guide.undo_last_cleaning()
    assert guide.dataframe.equals(df)
    assert undo["remaining_undo_steps"] == 0


def test_undo_without_history_raises():
    guide = DataGuide(pd.DataFrame({"Marks": [1, 2]}))
    with pytest.raises(RuntimeError, match="No in-place cleaning"):
        guide.undo_last_cleaning()


def test_before_after_comparison():
    before = pd.DataFrame({"A": [1, None, 1], "B": ["x", "y", "y"]})
    after = pd.DataFrame({"A": [1, 2], "B": ["x", "y"]})
    result = DataGuide(before).compare_before_after(after)
    assert result["row_change"] == -1
    assert result["missing_cell_change"] == -1
    assert result["duplicate_rows_before"] == 0


def test_schema_comparison_detects_added_removed_and_dtype_changes():
    baseline = pd.DataFrame({"A": [1, 2], "B": ["x", "y"]})
    candidate = pd.DataFrame({"A": ["1", "2"], "C": [10, 20]})
    result = DataGuide(baseline).compare_schema(candidate)
    assert result["added_columns"] == ["C"]
    assert result["removed_columns"] == ["B"]
    assert "A" in result["dtype_changes"]
    assert result["same_schema"] is False


def test_drift_detects_numeric_shift():
    baseline = pd.DataFrame({"Score": [10, 11, 9, 10, 10]})
    candidate = pd.DataFrame({"Score": [50, 51, 49, 50, 50]})
    result = DataGuide(baseline).detect_drift(candidate)
    assert result["drift_detected"] is True
    assert "Score" in result["numeric_distribution_drift"]


def test_drift_detects_categorical_shift():
    baseline = pd.DataFrame({"Department": ["CS"] * 8 + ["Math"] * 2})
    candidate = pd.DataFrame({"Department": ["Math"] * 8 + ["CS"] * 2})
    result = DataGuide(baseline).detect_drift(candidate)
    assert "Department" in result["categorical_distribution_drift"]


def test_drift_detects_missingness_change():
    baseline = pd.DataFrame({"Marks": [1, 2, 3, 4]})
    candidate = pd.DataFrame({"Marks": [1, None, None, None]})
    result = DataGuide(baseline).detect_drift(candidate)
    assert "Marks" in result["missingness_drift"]


def test_no_drift_for_identical_copy():
    df = pd.DataFrame({"Marks": [1, 2, 3], "Department": ["CS", "Math", "CS"]})
    result = DataGuide(df).detect_drift(df.copy())
    assert result["drift_detected"] is False
    assert result["overall_severity"] == "none"


def test_inspection_contains_cleaning_plan():
    result = DataGuide(pd.DataFrame({"Department": ["CS", "cs"]})).inspect()
    assert "cleaning_plan" in result
    assert result["cleaning_plan"]["preview_only"] is True


@pytest.mark.parametrize("kwargs", [
    {"max_risk": "high"},
    {"max_risk": "manual"},
])
def test_invalid_cleaning_risk(kwargs):
    guide = DataGuide(pd.DataFrame({"Marks": [1, None, 3]}))
    with pytest.raises(ValueError, match="max_risk"):
        guide.apply_cleaning(**kwargs)


@pytest.mark.parametrize("kwargs", [
    {"numeric_mean_threshold": 0},
    {"categorical_tv_threshold": 0},
    {"categorical_tv_threshold": 1.1},
    {"missing_change_threshold": -1},
])
def test_invalid_drift_thresholds(kwargs):
    guide = DataGuide(pd.DataFrame({"Marks": [1, 2, 3]}))
    with pytest.raises(ValueError):
        guide.detect_drift(pd.DataFrame({"Marks": [1, 2, 3]}), **kwargs)



def test_fingerprint_is_stable_for_identical_data():
    df = pd.DataFrame({"A": [1, 2], "B": ["x", "y"]})
    guide = DataGuide(df)
    first = guide.dataset_fingerprint()
    second = guide.dataset_fingerprint(df.copy())
    assert first["combined_hash"] == second["combined_hash"]
    assert len(first["combined_hash"]) == 64


def test_fingerprint_detects_row_order_but_can_ignore_it():
    df = pd.DataFrame({"A": [1, 2, 3]})
    reordered = df.iloc[::-1].reset_index(drop=True)
    result = DataGuide(df).compare_fingerprint(reordered, include_index=False)
    assert result["same_ordered_content"] is False
    assert result["same_content_ignoring_row_order"] is True


def test_inspection_contains_fingerprint():
    result = DataGuide(pd.DataFrame({"A": [1, 2]})).inspect()
    assert "dataset_fingerprint" in result
    assert result["dataset_fingerprint"]["algorithm"] == "sha256"


def test_create_and_validate_contract_successfully():
    df = pd.DataFrame({"Student_ID": ["S1", "S2"], "Age": [20, 21], "Status": ["Pass", "Fail"]})
    guide = DataGuide(df)
    contract = guide.create_validation_contract({
        "Age": {"nullable": False, "minimum": 0, "maximum": 120},
        "Status": {"allowed_values": ["Pass", "Fail"]},
    })
    result = guide.validate_contract(contract)
    assert result["valid"] is True
    assert contract["columns"]["Student_ID"]["unique"] is True


def test_contract_detects_missing_column_dtype_null_range_and_extra():
    baseline = pd.DataFrame({"Age": [20, 21], "Status": ["Pass", "Fail"], "Required": [1, 2]})
    guide = DataGuide(baseline)
    contract = guide.create_validation_contract({
        "Age": {"dtype": "number", "nullable": False, "minimum": 0, "maximum": 120},
    })
    candidate = pd.DataFrame({"Age": ["bad", None], "Status": ["Pass", "Other"], "Extra": [1, 2]})
    result = guide.validate_contract(contract, data=candidate)
    codes = {item["code"] for item in result["violations"]}
    assert "missing_required_column" in codes
    assert "dtype_mismatch" in codes
    assert "null_not_allowed" in codes
    assert "unexpected_column" in codes


def test_contract_allowed_pattern_length_and_unique_rules():
    df = pd.DataFrame({"Code": ["AA1", "bad", "AA1"], "Status": ["Pass", "Other", "Pass"]})
    guide = DataGuide(df)
    contract = guide.create_validation_contract({
        "Code": {"unique": True, "pattern": r"[A-Z]{2}\d", "min_length": 3, "max_length": 3},
        "Status": {"allowed_values": ["Pass", "Fail"]},
    }, strict_columns=False)
    result = guide.validate_contract(contract)
    codes = {item["code"] for item in result["violations"]}
    assert "duplicate_values" in codes
    assert "pattern_mismatch" in codes
    assert "disallowed_value" in codes


def test_contract_export_and_load(tmp_path):
    guide = DataGuide(pd.DataFrame({"Age": [20, 21]}))
    path = guide.export_validation_contract(tmp_path / "contract")
    loaded = guide.load_validation_contract(path)
    assert path.suffix == ".json"
    assert "Age" in loaded["columns"]


def test_leakage_detects_exact_target_copy():
    df = pd.DataFrame({"Feature": [1, 2, 3, 4], "Target": [0, 0, 1, 1], "Target_Copy": [0, 0, 1, 1]})
    result = DataGuide(df).check_target_leakage("Target")
    assert any(issue["code"] == "exact_target_copy" and issue["column"] == "Target_Copy" for issue in result["issues"])


def test_leakage_detects_near_perfect_numeric_correlation():
    df = pd.DataFrame({"Target": [10, 20, 30, 40], "Leaked_Score": [100, 200, 300, 400], "Safe": [2, 8, 1, 7]})
    result = DataGuide(df).check_target_leakage("Target")
    assert any(issue["code"] == "near_perfect_target_correlation" and issue["column"] == "Leaked_Score" for issue in result["issues"])


def test_leakage_invalid_target_and_threshold():
    guide = DataGuide(pd.DataFrame({"Target": [0, 1]}))
    with pytest.raises(ValueError, match="Target column"):
        guide.check_target_leakage("Missing")
    with pytest.raises(ValueError, match="correlation_threshold"):
        guide.check_target_leakage("Target", correlation_threshold=0)


def test_cleaning_audit_records_copy_and_inplace_operations(tmp_path):
    guide = DataGuide(pd.DataFrame({"Department": ["CS", "cs"]}))
    guide.apply_cleaning()
    guide.apply_cleaning(inplace=True, confirm=True)
    guide.undo_last_cleaning()
    log = guide.cleaning_audit_log()
    assert [entry["event"] for entry in log] == ["apply_cleaning", "apply_cleaning", "undo_cleaning"]
    assert "combined_hash" in log[0]["before_fingerprint"]
    exported = guide.export_cleaning_audit_log(tmp_path / "audit")
    payload = json.loads(exported.read_text(encoding="utf-8"))
    assert payload["event_count"] == 3
    assert guide.clear_cleaning_audit_log() == 3


def test_drift_history_records_labels_and_exports(tmp_path):
    guide = DataGuide(pd.DataFrame({"Score": [1, 2, 3, 4]}))
    guide.detect_drift(pd.DataFrame({"Score": [10, 20, 30, 40]}), label="batch-2")
    history = guide.drift_history()
    assert len(history) == 1
    assert history[0]["label"] == "batch-2"
    assert history[0]["run_id"] == 1
    output = guide.export_drift_history(tmp_path / "history")
    assert json.loads(output.read_text(encoding="utf-8"))["run_count"] == 1
    assert guide.clear_drift_history() == 1


def test_drift_can_skip_history_recording():
    guide = DataGuide(pd.DataFrame({"Score": [1, 2, 3]}))
    guide.detect_drift(pd.DataFrame({"Score": [4, 5, 6]}), record=False)
    assert guide.drift_history() == []


def test_fingerprint_and_leakage_exports(tmp_path):
    df = pd.DataFrame({"Target": [0, 1, 1], "Target_Copy": [0, 1, 1]})
    guide = DataGuide(df)
    fingerprint_path = guide.export_fingerprint(tmp_path / "fingerprint")
    leakage_path = guide.export_leakage_report("Target", tmp_path / "leakage")
    assert json.loads(fingerprint_path.read_text(encoding="utf-8"))["algorithm"] == "sha256"
    assert json.loads(leakage_path.read_text(encoding="utf-8"))["leakage_risk_detected"] is True


def test_identifier_target_leakage_warning_with_small_dataset():
    df = pd.DataFrame({"Student_ID": ["S1", "S2"], "Feature": [10, 20]})
    result = DataGuide(df).check_target_leakage("Student_ID")
    assert any(issue["code"] == "identifier_as_target" for issue in result["issues"])
