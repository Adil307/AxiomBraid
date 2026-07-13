from pathlib import Path

from axiombraid import DataGuide

path = Path(__file__).with_name("students.csv")
guide = DataGuide(path)
result = guide.apply_cleaning()

print("Applied:", result["applied_actions"])
print("Before/after:", result["comparison"])
print("Original rows:", len(guide.dataframe))
print("Cleaned rows:", len(result["dataframe"]))
