from pathlib import Path

from axiombraid import DataGuide

path = Path(__file__).with_name("students.csv")
guide = DataGuide(path)
print(guide.dataset_fingerprint())
print(guide.compare_fingerprint(path))
