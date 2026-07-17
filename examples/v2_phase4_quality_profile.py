"""AxiomBraid Version 2 Phase 4 example."""

import pandas as pd
import axiombraid as AB


df = pd.DataFrame(
    {
        "Employee_ID": [1, 2, 2, 4, 5],
        "Age": [25, 26, 26, 999, None],
        "Department": ["HR", " hr ", " hr ", "IT", "it"],
        "Constant": ["X", "X", "X", "X", "X"],
    }
)

print("\nReadable quality profile:\n")
AB.report(
    df,
    include_quality_profile=True,
    quality_details="full",
)

print("\nDirect structured profile:\n")
profile = AB.quality_profile(df)
print("Overall:", profile["score"], profile["rating"])
for name, details in profile["dimensions"].items():
    print(f"{name}: {details['score']}/100")
