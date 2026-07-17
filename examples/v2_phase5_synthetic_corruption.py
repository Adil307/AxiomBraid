"""AxiomBraid Version 2 Phase 5 example."""

import json
from pathlib import Path

import pandas as pd

import axiombraid as AB


clean = pd.DataFrame(
    {
        "Employee_ID": list(range(1, 21)),
        "Age": list(range(21, 41)),
        "Department": ["HR", "HR", "IT", "IT", "Sales"] * 4,
        "JoinDate": [f"2024-{month:02d}-01" for month in range(1, 11)] * 2,
        "Salary": list(range(50_000, 70_000, 1_000)),
    }
)

corrupted, truth = AB.inject_issues(
    clean,
    missing_rate=0.03,
    duplicate_rate=0.05,
    text_case_rate=0.05,
    whitespace_rate=0.05,
    invalid_range_rate=0.05,
    outlier_rate=0.03,
    date_format_rate=0.10,
    constant_columns=1,
    identifier_columns=1,
    random_state=42,
)

output = Path("phase5_outputs")
output.mkdir(exist_ok=True)
corrupted.to_csv(output / "corrupted_employees.csv", index=False)
(output / "ground_truth.json").write_text(
    json.dumps(truth, indent=2, ensure_ascii=False, default=str),
    encoding="utf-8",
)

print("Original shape:", clean.shape)
print("Corrupted shape:", corrupted.shape)
print("Injected issue types:", sorted(truth["issue_summary"]))
print("Saved:", output.resolve())
