"""AxiomBraid Version 2 Phase 6 example."""

import pandas as pd

import axiombraid as AB


clean = pd.DataFrame(
    {
        "Employee_ID": list(range(1, 31)),
        "Age": [21 + (index % 30) for index in range(30)],
        "Department": ["HR", "HR", "IT", "IT", "Sales"] * 6,
        "JoinDate": [f"2024-{(index % 12) + 1:02d}-01" for index in range(30)],
        "Salary": [50_000 + index * 1_000 for index in range(30)],
    }
)

result = AB.evaluation_report(
    clean,
    corruption_config={
        "missing_rate": 0.02,
        "duplicate_rate": 0.05,
        "text_case_rate": 0.05,
        "whitespace_rate": 0.05,
        "invalid_range_rate": 0.05,
        "outlier_rate": 0.03,
        "constant_columns": 1,
        "identifier_columns": 1,
        "random_state": 42,
    },
)

suggestion = AB.suggest_confidence_thresholds(
    result["detection_evaluation"],
    minimum_true_positives=1,
)
print("\nThreshold suggestion:")
print(suggestion)

benchmark = AB.benchmark_inspection(clean, repeats=2)
print()
print(AB.format_benchmark_console(benchmark))

print("\nCompatibility:")
print(AB.compatibility_check())
