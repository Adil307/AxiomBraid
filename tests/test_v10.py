import json
import os
import subprocess
import sys
from pathlib import Path

import pandas as pd

import axiombraid as AB


EXPECTED_PUBLIC_API = {
    "Guide", "DataGuide", "BatchAnalyzer", "batch_analyze",
    "InspectionCache", "cached_inspect", "stream_csv",
    "DEFAULT_CONFIG", "load_config", "export_config", "available_themes",
    "read_csv", "read_excel", "guide", "inspect", "inspect_with_confidence", "report", "clean",
    "validate", "compare", "detect_drift", "export_html", "about",
    "self_check", "API_STATUS", "RELEASE_STAGE", "PUBLIC_API_VERSION", "BRAND_NAME",
    "VERSION_INFO", "__version__", "issue_confidence", "add_confidence",
    "DEFAULT_CONFIDENCE_CONFIG", "normalize_confidence_config",
    "confidence_report",
    "quality_profile", "DEFAULT_QUALITY_PROFILE_CONFIG",
    "normalize_quality_profile_config", "build_quality_profile",
    "format_quality_profile_console",
    "GROUND_TRUTH_VERSION", "inject_issues", "ground_truth_pairs",
    "EVALUATION_VERSION", "evaluate_detection", "evaluate_quality_response",
    "run_evaluation", "benchmark_inspection", "benchmark_scaling",
    "suggest_confidence_thresholds", "compatibility_check",
    "format_evaluation_console", "evaluation_report", "format_benchmark_console",
}


def test_stable_release_metadata():
    assert AB.__version__ == "2.0.1"
    assert AB.VERSION_INFO == (2, 0, 0)
    assert AB.API_STATUS == "stable"
    assert AB.PUBLIC_API_VERSION == "2"
    assert AB.BRAND_NAME == "AxiomBraid"


def test_public_api_is_frozen_and_importable():
    assert set(AB.__all__) == EXPECTED_PUBLIC_API
    for name in EXPECTED_PUBLIC_API:
        assert hasattr(AB, name)


def test_about_is_json_serializable():
    payload = AB.about()
    assert payload["brand"] == "AxiomBraid"
    assert payload["version"] == "2.0.1"
    assert payload["api_status"] == "stable"
    json.dumps(payload)


def test_self_check_passes():
    payload = AB.self_check()
    assert payload["ok"] is True
    assert all(item["passed"] for item in payload["checks"])


def test_python_module_cli_version():
    environment = os.environ.copy()
    source_root = str(Path(AB.__file__).parents[1])
    environment["PYTHONPATH"] = source_root
    completed = subprocess.run(
        [sys.executable, "-m", "axiombraid", "--version"],
        capture_output=True,
        text=True,
        check=False,
        env=environment,
    )
    assert completed.returncode == 0
    assert "AxiomBraid 2.0.1" in completed.stdout


def test_pep561_marker_is_packaged_in_source_tree():
    marker = Path(AB.__file__).with_name("py.typed")
    assert marker.exists()


def test_functional_api_safety_and_roundtrip(tmp_path):
    original = pd.DataFrame(
        {
            "ID": ["A1", "A2"],
            "Department": ["CS", " cs "],
            "Marks": [80, 90],
        }
    )
    cleaned = AB.clean(original)
    assert original.loc[1, "Department"] == " cs "
    assert cleaned.loc[1, "Department"] == "CS"
    report = AB.export_html(original, tmp_path / "report")
    assert report.exists()
    assert "AxiomBraid 2.0.1" in report.read_text(encoding="utf-8")


def test_legacy_namespace_not_shipped_in_source_tree():
    source_root = Path(AB.__file__).parents[1]
    assert not (source_root / "dataguidepy").exists()
