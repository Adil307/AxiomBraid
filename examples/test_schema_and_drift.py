import pandas as pd

from axiombraid import DataGuide

baseline = pd.DataFrame({
    "Department": ["CS", "CS", "Math", "CS"],
    "Marks": [70, 75, 80, 72],
})

candidate = pd.DataFrame({
    "Department": ["Math", "Math", "Math", "CS"],
    "Marks": [90, 92, 88, 91],
    "Batch": [2026, 2026, 2026, 2026],
})

guide = DataGuide(baseline)
print("Schema comparison:")
print(guide.compare_schema(candidate))

print("\nDrift screen:")
print(guide.detect_drift(candidate))
