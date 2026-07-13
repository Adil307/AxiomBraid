from pathlib import Path

from axiombraid import DataGuide

path = Path(__file__).with_name("students.csv")
guide = DataGuide(path)

guide.apply_cleaning(inplace=True, confirm=True)
print("After cleaning rows:", len(guide.dataframe))

guide.undo_last_cleaning()
print("After undo rows:", len(guide.dataframe))
