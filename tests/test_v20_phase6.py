"""AxiomBraid Version 2 Phase 6 evaluation and performance tests."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import pandas as pd

import axiombraid as AB


def _clean_frame(rows: int = 30) -> pd.DataFrame:
    departments = ["HR", "HR", "IT", "IT", "Sales"]
    return pd.DataFrame(
        {
            "Employee_ID": list(range(1, rows + 1)),
            "Age": [21 + (index % 30) for index in range(rows)],
            "Department": [departments[index % len(departments)] for index in range(rows)],
            "JoinDate": [f"2024-{(index % 12) + 1:02d}-01" for index in range(rows)],
            "Salary": [50_000 + index * 1_000 for index in range(rows)],
        }
    )


def _evaluation_result():
    return AB.run_evaluation(
        _clean_frame(),
        corruption_config={
            "missing_rate": 0.02,
            "duplicate_rate": 0.05,
            "text_case_rate": 0.05,
            "whitespace_rate": 0.05,
            "invalid_range_rate": 0.05,
            "outlier_rate": 0.03,
            "constant_columns": 1,
            "identifier_columns": 1,
            "random_state": 42,
        },
    )


def test_run_evaluation_returns_reproducible_metrics():
    result = _evaluation_result()
    metrics = result["detection_evaluation"]["overall"]
    assert metrics["precision"] >= 0.80
    assert metrics["recall"] >= 0.80
    assert metrics["f1"] >= 0.80
    assert result["detection_evaluation"]["baseline_subtracted"] is True
    assert isinstance(result["corrupted_dataframe"], pd.DataFrame)


def test_detection_evaluation_is_json_serializable():
    result = _evaluation_result()["detection_evaluation"]
    json.dumps(result)
    assert "per_detector" in result
    assert "confidence_diagnostics" in result


def test_quality_response_reports_dimension_deltas():
    result = _evaluation_result()["quality_response"]
    assert "dimension_deltas" in result
    assert set(result["dimension_deltas"]) == {
        "completeness",
        "uniqueness",
        "validity",
        "consistency",
        "integrity",
    }
    assert isinstance(result["overall_delta"], float)


def test_benchmark_inspection_has_runtime_and_memory():
    result = AB.benchmark_inspection(_clean_frame(10), repeats=1)
    assert result["rows"] == 10
    assert result["runtime_seconds"]["mean"] >= 0
    assert result["peak_memory_bytes"]["maximum"] >= 0
    assert result["repeats"] == 1


def test_scaling_benchmark_uses_requested_sizes():
    result = AB.benchmark_scaling(_clean_frame(10), sizes=[5, 20], repeats=1)
    assert result["sizes"] == [5, 20]
    assert [entry["rows"] for entry in result["results"]] == [5, 20]


def test_confidence_threshold_suggestion_is_explicitly_empirical():
    evaluation = _evaluation_result()["detection_evaluation"]
    suggestion = AB.suggest_confidence_thresholds(
        evaluation,
        minimum_true_positives=1,
    )
    assert suggestion["status"] == "suggestion_available"
    assert suggestion["is_probability_calibration"] is False
    assert suggestion["suggested_thresholds"]["medium"] <= suggestion["suggested_thresholds"]["high"]


def test_compatibility_check_protects_v1_and_v2_api():
    result = AB.compatibility_check()
    assert result["ok"] is True
    assert result["missing"] == []
    assert result["version"] == "2.0.1"


def test_cli_benchmark_and_evaluate(tmp_path):
    data_path = tmp_path / "employees.csv"
    _clean_frame(20).to_csv(data_path, index=False)
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(Path(AB.__file__).parents[1])

    benchmark_path = tmp_path / "benchmark.json"
    benchmark = subprocess.run(
        [
            sys.executable,
            "-m",
            "axiombraid",
            "benchmark",
            str(data_path),
            "--repeats",
            "1",
            "--output",
            str(benchmark_path),
        ],
        capture_output=True,
        text=True,
        check=False,
        env=environment,
    )
    assert benchmark.returncode == 0
    assert benchmark_path.exists()

    evaluation_prefix = tmp_path / "evaluation"
    evaluation = subprocess.run(
        [
            sys.executable,
            "-m",
            "axiombraid",
            "evaluate",
            str(data_path),
            "--output",
            str(evaluation_prefix),
            "--missing-rate",
            "0.02",
            "--duplicate-rate",
            "0.05",
            "--constant-columns",
            "1",
        ],
        capture_output=True,
        text=True,
        check=False,
        env=environment,
    )
    assert evaluation.returncode == 0
    assert evaluation_prefix.with_suffix(".json").exists()
    assert evaluation_prefix.with_name("evaluation_corrupted.csv").exists()


def test_human_friendly_evaluation_and_benchmark_formatters(capsys):
    evaluation = _evaluation_result()
    text = AB.format_evaluation_console(evaluation)
    assert "AXIOMBRAID DETECTION EVALUATION" in text
    assert "Precision" in text
    assert "PER-DETECTOR RESULTS" in text

    returned = AB.evaluation_report(
        _clean_frame(),
        corruption_config={"missing_rate": 0.02, "duplicate_rate": 0.05, "random_state": 7},
    )
    output = capsys.readouterr().out
    assert "F1 score" in output
    assert "detection_evaluation" in returned

    benchmark = AB.benchmark_inspection(_clean_frame(10), repeats=1)
    benchmark_text = AB.format_benchmark_console(benchmark)
    assert "AXIOMBRAID INSPECTION BENCHMARK" in benchmark_text

def test_outlier_event_evaluation_handles_preexisting_column_findings():
    from axiombraid.evaluation import evaluate_detection

    baseline = {
        "issues": [
            {"code": "potential_outliers", "columns": ["Value"]},
        ],
        "outliers": {
            "Value": {
                "outlier_row_positions": [1],
                "outlier_evidence_complete": True,
            }
        },
    }
    corrupted = {
        "issues": [
            {"code": "potential_outliers", "columns": ["Value"]},
        ],
        "outliers": {
            "Value": {
                "outlier_row_positions": [1, 8],
                "outlier_evidence_complete": True,
            }
        },
    }
    truth = {
        "events": [
            {
                "issue_code": "potential_outliers",
                "columns": ["Value"],
                "row_indices": [8],
                "cell_locations": [
                    {
                        "row": 8,
                        "column": "Value",
                        "original": 0.43,
                        "injected": 5780.0,
                    }
                ],
            }
        ]
    }

    result = evaluate_detection(
        corrupted,
        truth,
        baseline_inspection=baseline,
    )
    event_result = result["outlier_event_evaluation"]

    assert event_result["status"] == "evaluated"
    assert event_result["true_positives"] == 1
    assert event_result["false_positives"] == 0
    assert event_result["false_negatives"] == 0
    assert event_result["recall"] == 1.0
