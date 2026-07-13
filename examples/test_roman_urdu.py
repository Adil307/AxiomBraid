from pathlib import Path

from axiombraid import DataGuide


dataset_path = Path(__file__).with_name("students.csv")

guide = DataGuide(dataset_path)
guide.report(language="roman_urdu")
