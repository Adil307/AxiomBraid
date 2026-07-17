"""AxiomBraid 2.0 Phase 2 evidence-aware confidence example."""

import pandas as pd

import axiombraid as AB


df = pd.DataFrame(
    {
        "Employee_ID": ["E1", "E2", "E3", "E4", "E5"],
        "Department": ["HR", " hr ", "Hr", "IT", "it"],
        "Age": [25, 26, 27, 28, 200],
        "JoinDate": [
            "2025-01-01",
            "2025-02-02",
            "not-a-date",
            "2025-03-03",
            "2025-04-04",
        ],
        "Constant": ["X"] * 5,
    }
)

result = AB.inspect(
    df,
    include_confidence=True,
)

print("AxiomBraid version:", AB.__version__)
print("\nConfidence summary:")
print(result["confidence_summary"])

print("\nIssue evidence:")
for issue in result["issues"]:
    confidence = issue["confidence"]
    print("\n-", issue["code"])
    print("  score:", confidence["score"])
    print("  level:", confidence["level"])
    print("  method:", confidence["method"])
    print("  evidence:", confidence["evidence"])
    print("  per_column:", confidence["per_column"])

print("\nCompact confidence-only report:")
print(AB.confidence_report(AB.inspect(df)))
