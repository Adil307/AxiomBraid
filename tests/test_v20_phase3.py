import json

import pandas as pd

import axiombraid as AB
from axiombraid.cli import main as cli_main


def phase3_frame():
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


def test_phase3_alpha_metadata():
    assert AB.__version__ == "2.0.0"
    assert AB.VERSION_INFO == (2, 0, 0)
    assert AB.API_STATUS == "stable"
    assert AB.PUBLIC_API_VERSION == "2"


def test_report_with_confidence_is_human_readable(capsys):
    result = AB.report(phase3_frame(), include_confidence=True)
    output = capsys.readouterr().out

    assert "CONFIDENCE OVERVIEW" in output
    assert "CONFIDENCE DETAILS" in output
    assert "Potential Outliers" in output
    assert "Confidence:" in output
    assert "Evidence:" in output
    assert "Recommended action:" in output
    assert "per_column" not in output
    assert "detector_specific_heuristic" not in output
    assert "confidence_summary" in result


def test_report_supports_summary_only_confidence(capsys):
    AB.report(
        phase3_frame(),
        include_confidence=True,
        confidence_details="summary",
    )
    output = capsys.readouterr().out
    assert "CONFIDENCE OVERVIEW" in output
    assert "CONFIDENCE DETAILS" not in output


def test_roman_urdu_confidence_console_is_readable(capsys):
    AB.report(
        phase3_frame(),
        language="roman_urdu",
        include_confidence=True,
        confidence_details="full",
    )
    output = capsys.readouterr().out
    assert "CONFIDENCE / AITMAAD OVERVIEW" in output
    assert "statistical probability nahi" in output


def test_confidence_report_display_preserves_compact_return_shape(capsys):
    inspection = AB.inspect(phase3_frame())
    compact = AB.confidence_report(inspection, display=True)
    output = capsys.readouterr().out

    assert "CONFIDENCE OVERVIEW" in output
    assert set(compact) == {"summary", "issues"}
    assert compact["issues"]
    assert set(compact["issues"][0]) == {
        "code",
        "severity",
        "columns",
        "score",
        "level",
        "method",
        "evidence",
        "per_column",
    }


def test_confidence_metadata_contains_user_facing_fields():
    result = AB.inspect_with_confidence(phase3_frame())
    issue = result["issues"][0]
    confidence = issue["confidence"]

    assert confidence["display_name"]
    assert confidence["simple_evidence"]
    assert confidence["recommended_action"]
    assert result["confidence_recommendations"]


def test_json_export_can_include_confidence(tmp_path):
    guide = AB.Guide(phase3_frame())
    path = guide.export_json(
        tmp_path / "report.json",
        include_confidence=True,
    )
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert "confidence_summary" in payload
    assert "confidence_recommendations" in payload
    assert payload["issues"][0]["confidence"]["simple_evidence"]


def test_default_json_export_remains_backward_compatible(tmp_path):
    guide = AB.Guide(phase3_frame())
    path = guide.export_json(tmp_path / "report.json")
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert "confidence_summary" not in payload
    assert all("confidence" not in issue for issue in payload["issues"])


def test_html_export_can_include_professional_confidence_section(tmp_path):
    path = AB.export_html(
        phase3_frame(),
        tmp_path / "report.html",
        include_confidence=True,
        theme="dark",
    )
    html = path.read_text(encoding="utf-8")

    assert "Confidence Overview" in html
    assert "Issue Evidence" in html
    assert "Recommended action" in html
    assert "Technical details" in html
    assert "badge-high" in html
    assert "AxiomBraid 2.0.0" in html


def test_default_html_export_does_not_add_confidence_section(tmp_path):
    path = AB.export_html(phase3_frame(), tmp_path / "report.html")
    html = path.read_text(encoding="utf-8")
    assert "Confidence Overview" not in html


def test_cli_confidence_flag_applies_to_console_json_and_html(tmp_path, capsys):
    csv_path = tmp_path / "employees.csv"
    phase3_frame().to_csv(csv_path, index=False)
    output = tmp_path / "reports" / "employee"

    code = cli_main(
        [
            "inspect",
            str(csv_path),
            "--confidence",
            "--confidence-details",
            "summary",
            "--format",
            "console",
            "--format",
            "json",
            "--format",
            "html",
            "--output",
            str(output),
        ]
    )
    console = capsys.readouterr().out

    assert code == 0
    assert "CONFIDENCE OVERVIEW" in console
    json_payload = json.loads(output.with_suffix(".json").read_text(encoding="utf-8"))
    assert "confidence_summary" in json_payload
    html = output.with_suffix(".html").read_text(encoding="utf-8")
    assert "Confidence Overview" in html


def test_user_facing_confidence_fields_are_present():
    inspection = AB.inspect_with_confidence(phase3_frame())
    issue = next(item for item in inspection["issues"] if item["code"] == "potential_outliers")
    confidence = issue["confidence"]
    assert confidence["display_name"] == "Potential Outliers"
    assert "outlier" in confidence["simple_evidence"].lower()
    assert "review" in confidence["recommended_action"].lower()
