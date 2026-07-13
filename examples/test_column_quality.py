from pathlib import Path

from axiombraid import DataGuide


dataset_path = Path(__file__).with_name("students.csv")
result = DataGuide(dataset_path).inspect()

for column, details in result["column_quality"].items():
    print(column, details["score"], details["rating"], details["penalties"])
