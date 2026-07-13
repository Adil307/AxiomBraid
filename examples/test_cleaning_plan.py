from pathlib import Path

from axiombraid import DataGuide

path = Path(__file__).with_name("students.csv")
guide = DataGuide(path)
plan = guide.cleaning_plan()

print("Total actions:", plan["action_count"])
print("Risk counts:", plan["risk_counts"])
for action in plan["actions"]:
    print(action["action_id"], "->", action["risk"], "->", action["reason"])
