from pathlib import Path

from axiombraid import DataGuide, available_themes


guide = DataGuide(Path(__file__).with_name("students.csv"))
output = Path(__file__).parent / "reports" / "themes"

for theme in available_themes():
    path = guide.export_html(output / f"report_{theme}.html", theme=theme)
    print(path)
