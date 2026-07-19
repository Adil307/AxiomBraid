"""Tests for AxiomBraid Version 2 Phase 4 explainable quality profile."""

from __future__ import annotations

import json

import pandas as pd
import pytest

import axiombraid as AB


def _messy_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Employee_ID": [1, 2, 2, 4, 5],
            "Age": [25, 26, 26, 999, None],
            "Department": ["HR", " hr ", " hr ", "IT", "it"],
            "Constant": ["X", "X", "X", "X", "X"],
            "JoinDate": [
                "2024-01-01",
                "2024-02-01",
                "2024-02-01",
                "bad",
                "2024-04-01",
            ],
        }
    )


def test_default_inspection_stays_backward_compatible():
    result = AB.inspect(_messy_frame())
    assert "data_quality" in result
    assert "quality_profile" not in result


def test_inspection_can_include_quality_profile():
    result = AB.inspect(_messy_frame(), include_quality_profile=True)
    profile = result["quality_profile"]
    assert set(profile["dimensions"]) == {
        "completeness",
        "uniqueness",
        "validity",
        "consistency",
        "integrity",
    }
    assert 0 <= profile["score"] <= 100
    assert profile["profile_version"] == "2.0"


def test_direct_quality_profile_api():
    profile = AB.quality_profile(_messy_frame())
    assert profile["dimensions"]["completeness"]["score"] < 100
    assert profile["dimensions"]["validity"]["score"] < 100
    assert profile["dimensions"]["consistency"]["score"] < 100
    assert profile["dimensions"]["integrity"]["score"] < 100


def test_duplicate_rows_reduce_uniqueness():
    frame = pd.DataFrame({"A": [1, 1], "B": ["x", "x"]})
    profile = AB.quality_profile(frame)
    assert profile["dimensions"]["uniqueness"]["score"] == 50.0


def test_weights_are_normalized_and_configurable():
    profile = AB.quality_profile(
        _messy_frame(),
        quality_config={
            "weights": {
                "completeness": 4,
                "uniqueness": 1,
                "validity": 1,
                "consistency": 1,
                "integrity": 1,
            }
        },
    )
    assert sum(profile["weights"].values()) == pytest.approx(1.0, abs=1e-5)
    assert profile["weights"]["completeness"] == pytest.approx(0.5, abs=1e-5)


def test_invalid_weight_name_is_rejected():
    with pytest.raises(ValueError):
        AB.quality_profile(
            _messy_frame(),
            quality_config={"weights": {"mystery": 1}},
        )


def test_console_report_is_human_readable(capsys):
    AB.report(
        _messy_frame(),
        include_quality_profile=True,
        quality_details="summary",
    )
    output = capsys.readouterr().out
    assert "EXPLAINABLE DATA QUALITY PROFILE" in output
    assert "Completeness" in output
    assert "Lowest dimension" in output


def test_json_export_can_include_quality_profile(tmp_path):
    guide = AB.Guide(_messy_frame())
    path = guide.export_json(
        tmp_path / "quality.json",
        include_quality_profile=True,
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert "quality_profile" in payload
    assert "dimensions" in payload["quality_profile"]


def test_html_export_can_include_quality_profile(tmp_path):
    path = AB.export_html(
        _messy_frame(),
        tmp_path / "quality.html",
        include_quality_profile=True,
    )
    html = path.read_text(encoding="utf-8")
    assert "Explainable Data Quality Profile" in html
    assert "Dimension breakdown" in html
    assert "Improvement priorities" in html
    assert "AxiomBraid 2.0.1" in html


def test_profile_keeps_legacy_score_for_comparison():
    result = AB.inspect(_messy_frame(), include_quality_profile=True)
    profile = result["quality_profile"]
    assert profile["legacy_compatibility_score"] == result["data_quality"]["score"]
    assert isinstance(profile["score_difference_from_legacy"], float)
