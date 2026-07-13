import json
from pathlib import Path

import pandas as pd
import pytest

from axiombraid import (
    BatchAnalyzer,
    DataGuide,
    available_themes,
    batch_analyze,
    export_config,
    load_config,
)
from axiombraid.cli import main


def sample_frame(rows=10):
    return pd.DataFrame(
        {
            "Student_ID": [f"S{i:03d}" for i in range(rows)],
            "Department": ["CS" if i % 2 == 0 else "Math" for i in range(rows)],
            "Marks": list(range(rows)),
        }
    )


def test_available_themes():
    assert available_themes() == ["dark", "high_contrast", "light", "minimal"]


@pytest.mark.parametrize("suffix", [".json", ".yaml", ".toml"])
def test_config_round_trip(tmp_path, suffix):
    path = export_config(tmp_path / f"config{suffix}")
    loaded = load_config(path)
    assert loaded["analysis"]["high_cardinality_threshold"] == 0.90
    assert loaded["performance"]["mode"] == "auto"
    assert loaded["report"]["html_theme"] == "light"


def test_config_merges_defaults():
    loaded = load_config({"performance": {"sample_rows": 25}})
    assert loaded["performance"]["sample_rows"] == 25
    assert loaded["performance"]["strategy"] == "random"
    assert loaded["analysis"]["outlier_iqr_multiplier"] == 1.5


def test_invalid_config_section():
    with pytest.raises(ValueError, match="Unsupported configuration section"):
        load_config({"unsafe": {}})


def test_config_section_must_be_mapping():
    with pytest.raises(TypeError, match="must be a dictionary"):
        load_config({"analysis": 5})


def test_from_config_applies_analysis_settings():
    guide = DataGuide.from_config(
        sample_frame(),
        {"analysis": {"high_cardinality_threshold": 0.75}},
    )
    assert guide.high_cardinality_threshold == 0.75
    assert guide.runtime_config()["performance"]["sample_rows"] == 50000


def test_runtime_config_normal_object_and_export(tmp_path):
    guide = DataGuide(sample_frame())
    config = guide.runtime_config()
    assert config["analysis"]["date_like_threshold"] == 0.80
    path = guide.export_runtime_config(tmp_path / "runtime.json")
    assert json.loads(path.read_text())["analysis"]["date_like_threshold"] == 0.80


def test_html_dark_theme(tmp_path):
    path = DataGuide(sample_frame()).export_html(tmp_path / "dark", theme="dark")
    html = path.read_text(encoding="utf-8")
    assert "Theme: dark" in html
    assert "#0f172a" in html
    assert "AxiomBraid 1.0.0" in html


def test_html_custom_title(tmp_path):
    path = DataGuide(sample_frame()).export_html(
        tmp_path / "custom.html",
        report_title="My Quality Report",
    )
    assert "My Quality Report" in path.read_text(encoding="utf-8")


def test_invalid_html_theme(tmp_path):
    with pytest.raises(ValueError, match="Unsupported HTML theme"):
        DataGuide(sample_frame()).export_html(tmp_path / "x", theme="pink")


def test_plugin_result_is_in_inspection():
    guide = DataGuide(sample_frame())

    def row_check(frame, context):
        return {"row_count": len(frame), "score": context["data_quality"]["score"]}

    guide.register_plugin("row_check", row_check)
    result = guide.inspect()
    assert result["plugin_results"]["row_check"]["status"] == "success"
    assert result["plugin_results"]["row_check"]["result"]["row_count"] == 10


def test_plugin_receives_copy_not_original():
    guide = DataGuide(sample_frame())

    def destructive(frame):
        frame.loc[0, "Marks"] = 999
        return int(frame.loc[0, "Marks"])

    guide.register_plugin("destructive", destructive)
    guide.run_plugins()
    assert guide.dataframe.loc[0, "Marks"] == 0


def test_plugin_duplicate_replace_and_unregister():
    guide = DataGuide(sample_frame())
    guide.register_plugin("p", lambda: 1)
    with pytest.raises(ValueError, match="already registered"):
        guide.register_plugin("p", lambda: 2)
    guide.register_plugin("p", lambda: 2, replace=True)
    assert guide.run_plugins()["p"]["result"] == 2
    assert guide.unregister_plugin("p") is True
    assert guide.unregister_plugin("p") is False
    assert guide.list_plugins() == []


def test_plugin_error_isolated_and_strict():
    guide = DataGuide(sample_frame())

    def broken(frame):
        raise RuntimeError("boom")

    guide.register_plugin("broken", broken)
    result = guide.run_plugins()
    assert result["broken"]["status"] == "error"
    assert result["broken"]["error_type"] == "RuntimeError"
    with pytest.raises(RuntimeError, match="Plugin 'broken' failed"):
        guide.run_plugins(strict=True)


def test_empty_plugin_name_and_non_callable():
    guide = DataGuide(sample_frame())
    with pytest.raises(ValueError):
        guide.register_plugin("", lambda: None)
    with pytest.raises(TypeError):
        guide.register_plugin("x", 5)


def test_performance_profile():
    profile = DataGuide(sample_frame(100)).performance_profile()
    assert profile["rows"] == 100
    assert profile["columns"] == 3
    assert profile["memory_bytes"] > 0


def test_prepare_full_mode_returns_same_object():
    guide = DataGuide(sample_frame(20))
    prepared = guide.prepare_analysis(mode="full", sample_rows=5)
    assert prepared is guide
    assert prepared.inspect()["performance"]["sampled"] is False


def test_prepare_sample_mode_is_deterministic_and_non_mutating():
    guide = DataGuide(sample_frame(100))
    first = guide.prepare_analysis(mode="sample", sample_rows=10, random_state=7)
    second = guide.prepare_analysis(mode="sample", sample_rows=10, random_state=7)
    assert first.dataframe.equals(second.dataframe)
    assert len(first.dataframe) == 10
    assert len(guide.dataframe) == 100
    metadata = first.inspect()["performance"]
    assert metadata["sampled"] is True
    assert metadata["full_rows"] == 100
    assert metadata["analyzed_rows"] == 10


def test_prepare_sample_copies_plugins():
    guide = DataGuide(sample_frame(20))
    guide.register_plugin("rows", lambda frame: len(frame))
    sampled = guide.prepare_analysis(mode="sample", sample_rows=5)
    assert sampled.inspect()["plugin_results"]["rows"]["result"] == 5


def test_auto_mode_samples_only_when_needed():
    small = DataGuide(sample_frame(5)).prepare_analysis(mode="auto", sample_rows=10)
    large = DataGuide(sample_frame(20)).prepare_analysis(mode="auto", sample_rows=10)
    assert small is not None and small.inspect()["performance"]["sampled"] is False
    assert large.inspect()["performance"]["sampled"] is True


@pytest.mark.parametrize(
    "kwargs, message",
    [
        ({"mode": "fast"}, "mode must"),
        ({"strategy": "middle"}, "strategy must"),
        ({"sample_rows": 0}, "positive integer"),
        ({"random_state": 2.5}, "must be an integer"),
    ],
)
def test_invalid_performance_options(kwargs, message):
    with pytest.raises((ValueError, TypeError), match=message):
        DataGuide(sample_frame()).prepare_analysis(**kwargs)


def test_sampled_cleaning_is_blocked():
    sampled = DataGuide(sample_frame(20)).prepare_analysis(
        mode="sample", sample_rows=5
    )
    with pytest.raises(ValueError, match="Cleaning is disabled"):
        sampled.apply_cleaning()


def test_inspect_performance_contains_metadata():
    result = DataGuide(sample_frame(30)).inspect_performance(
        mode="sample", sample_rows=6
    )
    assert result["shape"]["rows"] == 6
    assert result["performance"]["full_rows"] == 30


def write_csv(path, start=0, rows=3):
    pd.DataFrame(
        {"ID": [f"S{i}" for i in range(start, start + rows)], "Marks": range(rows)}
    ).to_csv(path, index=False)


def test_batch_discovery_non_recursive_and_recursive(tmp_path):
    write_csv(tmp_path / "a.csv")
    (tmp_path / "notes.txt").write_text("ignore")
    nested = tmp_path / "nested"
    nested.mkdir()
    write_csv(nested / "b.csv")
    assert len(BatchAnalyzer(tmp_path).discover_files()) == 1
    assert len(BatchAnalyzer(tmp_path, recursive=True).discover_files()) == 2


def test_batch_analysis_creates_reports_and_summaries(tmp_path):
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    write_csv(input_dir / "a.csv")
    write_csv(input_dir / "b.csv", start=10)
    output = tmp_path / "output"
    summary = BatchAnalyzer(input_dir).analyze(
        output,
        formats=["json", "html"],
        html_theme="minimal",
    )
    assert summary["success_count"] == 2
    assert summary["error_count"] == 0
    assert Path(summary["summary_json"]).exists()
    assert Path(summary["summary_csv"]).exists()
    assert len(list(output.glob("*.json"))) == 3  # 2 reports + summary
    assert len(list(output.glob("*.html"))) == 2


def test_batch_continues_after_corrupt_file(tmp_path):
    write_csv(tmp_path / "good.csv")
    (tmp_path / "bad.xlsx").write_text("not an excel file")
    summary = BatchAnalyzer(tmp_path).analyze(
        tmp_path / "out", formats=["json"], continue_on_error=True
    )
    assert summary["success_count"] == 1
    assert summary["error_count"] == 1
    assert any(entry["status"] == "error" for entry in summary["entries"])


def test_batch_can_stop_on_error(tmp_path):
    (tmp_path / "bad.xlsx").write_text("not excel")
    with pytest.raises(ValueError):
        BatchAnalyzer(tmp_path).analyze(
            tmp_path / "out", formats=["json"], continue_on_error=False
        )


def test_batch_helper(tmp_path):
    write_csv(tmp_path / "a.csv")
    summary = batch_analyze(tmp_path, tmp_path / "out", formats=["json"])
    assert summary["file_count"] == 1


def test_invalid_batch_format(tmp_path):
    write_csv(tmp_path / "a.csv")
    with pytest.raises(ValueError, match="Unsupported batch format"):
        BatchAnalyzer(tmp_path).analyze(tmp_path / "out", formats=["pdf"])


def test_cli_themes(capsys):
    assert main(["themes"]) == 0
    assert "high_contrast" in capsys.readouterr().out


def test_cli_init_config(tmp_path, capsys):
    target = tmp_path / "config.yaml"
    assert main(["init-config", str(target)]) == 0
    assert target.exists()
    assert "Configuration created" in capsys.readouterr().out


def test_cli_inspect_json_and_html(tmp_path, capsys):
    data = tmp_path / "data.csv"
    write_csv(data)
    output = tmp_path / "report"
    code = main(
        [
            "inspect", str(data),
            "--output", str(output),
            "--format", "json",
            "--format", "html",
            "--theme", "dark",
        ]
    )
    assert code == 0
    assert output.with_suffix(".json").exists()
    assert output.with_suffix(".html").exists()
    assert "JSON report" in capsys.readouterr().out


def test_cli_inspect_sample_mode(tmp_path):
    data = tmp_path / "data.csv"
    write_csv(data, rows=20)
    output = tmp_path / "sample"
    assert main([
        "inspect", str(data), "--output", str(output), "--format", "json",
        "--mode", "sample", "--sample-rows", "5",
    ]) == 0
    result = json.loads(output.with_suffix(".json").read_text())
    assert result["performance"]["sampled"] is True
    assert result["shape"]["rows"] == 5


def test_cli_batch(tmp_path):
    input_dir = tmp_path / "in"
    input_dir.mkdir()
    write_csv(input_dir / "a.csv")
    code = main([
        "batch", str(input_dir), "--output", str(tmp_path / "out"),
        "--format", "json",
    ])
    assert code == 0
    assert (tmp_path / "out" / "batch_summary.json").exists()


def test_cli_fingerprint(tmp_path, capsys):
    data = tmp_path / "data.csv"
    write_csv(data)
    output = tmp_path / "fingerprint.json"
    assert main([
        "fingerprint", str(data), "--output", str(output)
    ]) == 0
    assert output.exists()
    assert "Fingerprint report" in capsys.readouterr().out


def test_cli_validate_valid_and_invalid(tmp_path):
    data = tmp_path / "data.csv"
    write_csv(data)
    guide = DataGuide(data)
    contract = guide.create_validation_contract(
        {"Marks": {"minimum": 0, "maximum": 5}}, strict_columns=True
    )
    contract_path = guide.export_validation_contract(tmp_path / "contract.json", contract=contract)
    assert main(["validate", str(data), str(contract_path)]) == 0

    invalid_contract = guide.create_validation_contract(
        {"Marks": {"maximum": -1}}, strict_columns=True
    )
    invalid_path = guide.export_validation_contract(
        tmp_path / "invalid_contract.json", contract=invalid_contract
    )
    assert main(["validate", str(data), str(invalid_path)]) == 3


def test_export_json_includes_performance_and_plugins(tmp_path):
    guide = DataGuide(sample_frame())
    guide.register_plugin("one", lambda: {"ok": True})
    path = guide.export_json(tmp_path / "report")
    payload = json.loads(path.read_text())
    assert payload["performance"]["effective_mode"] == "full"
    assert payload["plugin_results"]["one"]["status"] == "success"
