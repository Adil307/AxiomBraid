from pathlib import Path

from axiombraid import DataGuide


def pass_rate_plugin(dataframe, context):
    status = dataframe["Status"].astype(str).str.strip().str.casefold()
    return {
        "pass_rate": round(float(status.eq("pass").mean() * 100), 2),
        "core_quality_score": context["data_quality"]["score"],
    }


guide = DataGuide(Path(__file__).with_name("students.csv"))
guide.register_plugin("pass_rate", pass_rate_plugin)
print(guide.inspect()["plugin_results"])
