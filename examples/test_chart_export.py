from pathlib import Path

from axiombraid import DataGuide


dataset_path = Path(__file__).with_name("students.csv")
output_directory = Path(__file__).parent / "reports" / "charts"

paths = DataGuide(dataset_path).export_charts(output_directory, max_charts=5)
for path in paths:
    print(path)
