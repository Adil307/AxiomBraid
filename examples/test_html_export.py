from pathlib import Path
from axiombraid import DataGuide

path = Path(__file__).with_name("students.csv")
output = Path(__file__).parent / "reports" / "student_report.html"
print(DataGuide(path).export_html(output))
