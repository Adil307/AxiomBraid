from pathlib import Path

from axiombraid import DataGuide


dataset_path = Path(__file__).with_name("students.csv")
output_path = Path(__file__).parent / "reports" / "student_report.json"

guide = DataGuide(dataset_path)
saved_path = guide.export_json(output_path)

print(f"JSON report saved at: {saved_path}")
