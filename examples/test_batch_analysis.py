from pathlib import Path

from axiombraid import BatchAnalyzer


examples = Path(__file__).parent
summary = BatchAnalyzer(examples).analyze(
    examples / "reports" / "batch",
    formats=["json", "html"],
    html_theme="minimal",
)

print("Files:", summary["file_count"])
print("Succeeded:", summary["success_count"])
print("Errors:", summary["error_count"])
print("Summary:", summary["summary_json"])
