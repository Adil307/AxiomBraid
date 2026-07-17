import json
import subprocess
from pathlib import Path

import pandas as pd
import pytest

import axiombraid as AB
from axiombraid.cache import InspectionCache
from axiombraid.cli import main


def frame():
    return pd.DataFrame({
        "Student_ID": ["S1", "S2", "S3"],
        "Department": ["CS", " cs ", "Math"],
        "Marks": [80, 90, 70],
    })


def test_brand_and_alias_style():
    assert AB.BRAND_NAME == "AxiomBraid"
    assert AB.__version__ == "2.0.0"
    assert AB.Guide is AB.DataGuide
    assert AB.API_STATUS == "stable"


def test_functional_inspect_and_report(capsys):
    result = AB.inspect(frame())
    assert result["shape"] == {"rows": 3, "columns": 3}
    reported = AB.report(frame())
    assert reported["shape"]["rows"] == 3
    assert "AXIOMBRAID" in capsys.readouterr().out.upper()


def test_read_csv_and_excel(tmp_path):
    csv_path = tmp_path/"x.csv"; frame().to_csv(csv_path,index=False)
    assert AB.read_csv(csv_path).equals(frame())
    xlsx_path = tmp_path/"x.xlsx"; frame().to_excel(xlsx_path,index=False)
    assert AB.read_excel(xlsx_path).equals(frame())


def test_functional_clean_does_not_mutate():
    original = frame(); cleaned = AB.clean(original)
    assert original.loc[1,"Department"] == " cs "
    assert cleaned.loc[1,"Department"] == "CS"


def test_functional_clean_details():
    details = AB.clean(frame(), return_details=True)
    assert "normalize_text:Department" in details["applied_actions"]


def test_functional_validate_compare_and_drift():
    contract = {"columns": {"Marks": {"dtype": "numeric", "nullable": False}}}
    assert AB.validate(frame(), contract)["valid"] is True
    candidate = frame().copy(); candidate["Extra"] = 1
    assert AB.compare(frame(), candidate, mode="schema")["added_columns"] == ["Extra"]
    assert AB.compare(frame(), candidate)["column_change"] == 1
    assert "drift_detected" in AB.detect_drift(frame(), candidate, record=False)


def test_export_html_function(tmp_path):
    path = AB.export_html(frame(), tmp_path/"report", theme="minimal")
    assert path.exists() and "AxiomBraid 2.0.0" in path.read_text(encoding="utf-8")


def test_cache_miss_hit_and_refresh(tmp_path):
    cache_dir = tmp_path/"cache"
    first = AB.cached_inspect(frame(), cache_dir=cache_dir)
    second = AB.cached_inspect(frame(), cache_dir=cache_dir)
    refreshed = AB.cached_inspect(frame(), cache_dir=cache_dir, refresh=True)
    assert first["cache_hit"] is False
    assert second["cache_hit"] is True
    assert refreshed["cache_hit"] is False
    assert first["cache_key"] == second["cache_key"]


def test_cache_changes_with_content_and_config(tmp_path):
    a = AB.cached_inspect(frame(), cache_dir=tmp_path)
    modified = frame(); modified.loc[0,"Marks"] = 1
    b = AB.cached_inspect(modified, cache_dir=tmp_path)
    c = AB.cached_inspect(frame(), cache_dir=tmp_path, config={"analysis":{"high_cardinality_threshold":0.8}})
    assert len({a["cache_key"], b["cache_key"], c["cache_key"]}) == 3


def test_cache_clear_and_corrupt_entry(tmp_path):
    cache = InspectionCache(tmp_path)
    payload = AB.cached_inspect(frame(), cache_dir=tmp_path)
    cache.path_for(payload["cache_key"]).write_text("broken", encoding="utf-8")
    assert AB.cached_inspect(frame(), cache_dir=tmp_path)["cache_hit"] is False
    assert cache.clear() >= 1


def test_stream_csv_exact_counts_and_determinism(tmp_path):
    data = pd.DataFrame({"A": range(25), "B": [None if i%4==0 else i for i in range(25)]})
    path=tmp_path/"large.csv"; data.to_csv(path,index=False)
    first=AB.stream_csv(path,chunksize=6,sample_rows=7,random_state=3)
    second=AB.stream_csv(path,chunksize=5,sample_rows=7,random_state=3)
    assert first["streaming"]["exact_rows"] == 25
    assert first["exact_missing_values"]["B"]["count"] == 7
    assert first["streaming"]["sample_rows"] == 7
    assert first["sample_inspection"]["performance"]["effective_mode"] == "stream_sample"
    assert first["sample_inspection"]["shape"] == second["sample_inspection"]["shape"]


@pytest.mark.parametrize("kwargs,message", [
    ({"chunksize":0},"chunksize"), ({"sample_rows":0},"sample_rows"), ({"random_state":1.5},"integer")
])
def test_stream_invalid_options(tmp_path, kwargs, message):
    path=tmp_path/"x.csv"; frame().to_csv(path,index=False)
    with pytest.raises((ValueError,TypeError),match=message): AB.stream_csv(path,**kwargs)


def test_stream_rejects_excel(tmp_path):
    path=tmp_path/"x.xlsx"; frame().to_excel(path,index=False)
    with pytest.raises(ValueError,match="csv files only"): AB.stream_csv(path)


def test_parallel_batch_order_progress_and_workers(tmp_path):
    input_dir=tmp_path/"input"; input_dir.mkdir()
    for name in ["c","a","b"]: frame().to_csv(input_dir/f"{name}.csv",index=False)
    events=[]
    summary=AB.BatchAnalyzer(input_dir).analyze(tmp_path/"out",formats=["json"],workers=2,progress_callback=lambda done,total,entry: events.append((done,total,entry["status"])))
    assert summary["workers"] == 2 and summary["success_count"] == 3
    assert [Path(e["file"]).name for e in summary["entries"]] == ["a.csv","b.csv","c.csv"]
    assert len(events) == 3 and events[-1][:2] == (3,3)


def test_parallel_batch_charts_blocked(tmp_path):
    frame().to_csv(tmp_path/"a.csv",index=False)
    with pytest.raises(ValueError,match="thread safety"):
        AB.BatchAnalyzer(tmp_path).analyze(tmp_path/"out",formats=["charts"],workers=2)


def test_parallel_batch_invalid_workers(tmp_path):
    with pytest.raises(ValueError,match="positive integer"):
        AB.BatchAnalyzer(tmp_path).analyze(tmp_path/"out",workers=0)


def test_cli_version_and_new_commands(tmp_path, capsys):
    path=tmp_path/"x.csv"; frame().to_csv(path,index=False)
    assert main(["stream",str(path),"--chunksize","2","--sample-rows","2"]) == 0
    assert "exact_rows" in capsys.readouterr().out
    assert main(["cache-inspect",str(path),"--cache-dir",str(tmp_path/"cache")]) == 0
    assert "cache_hit" in capsys.readouterr().out
    assert main(["cache-clear","--cache-dir",str(tmp_path/"cache")]) == 0


def test_cli_batch_progress(tmp_path, capsys):
    input_dir=tmp_path/"input"; input_dir.mkdir(); frame().to_csv(input_dir/"a.csv",index=False)
    assert main(["batch",str(input_dir),"--output",str(tmp_path/"out"),"--workers","2","--format","json"]) == 0
    output=capsys.readouterr().out
    assert "[1/1] SUCCESS" in output and "Batch complete" in output
