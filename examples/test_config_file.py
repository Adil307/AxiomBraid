from pathlib import Path

from axiombraid import DataGuide, export_config


folder = Path(__file__).parent
config_path = export_config(folder / "reports" / "dataguide.yaml")
guide = DataGuide.from_config(folder / "students.csv", config_path)
guide.report()
print(f"Config: {config_path}")
