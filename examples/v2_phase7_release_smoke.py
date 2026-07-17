"""Small AxiomBraid 2.0.0 stable-release smoke example."""

import pandas as pd
import axiombraid as AB

frame = pd.DataFrame({
    "Employee_ID": [1, 2, 3, 4, 5],
    "Age": [25, 26, 27, 28, 150],
    "Department": ["HR", " hr ", "IT", "IT", "Sales"],
    "Salary": [50000, 52000, 54000, 56000, 58000],
})

print("Release:", AB.__version__, AB.API_STATUS)
AB.report(frame, include_confidence=True, include_quality_profile=True, confidence_details="summary", quality_details="summary")

corrupted, truth = AB.inject_issues(frame, missing_rate=0.1, duplicate_rate=0.2, random_state=42)
print("Injected events:", len(truth["events"]))
print("Source unchanged:", len(frame) == 5)
print("Self-check:", AB.self_check()["ok"])
print("Compatibility:", AB.compatibility_check()["ok"])
