"""AxiomBraid Version 2 Phase 5 synthetic corruption tests."""

from __future__ import annotations

import pandas as pd
import pytest

import axiombraid as AB


def _clean_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Employee_ID": list(range(1, 21)),
            "Age": list(range(21, 41)),
            "Department": ["HR", "HR", "IT", "IT", "Sales"] * 4,
            "JoinDate": [f"2024-{month:02d}-01" for month in range(1, 11)] * 2,
            "Salary": list(range(50_000, 70_000, 1_000)),
        }
    )


def test_inject_issues_is_non_mutating_and_returns_ground_truth():
    original = _clean_frame()
    snapshot = original.copy(deep=True)
    corrupted, truth = AB.inject_issues(
        original,
        missing_rate=0.02,
        duplicate_rate=0.05,
        text_case_rate=0.05,
        invalid_range_rate=0.05,
        outlier_rate=0.05,
        constant_columns=1,
        identifier_columns=1,
        random_state=7,
    )
    pd.testing.assert_frame_equal(original, snapshot)
    assert corrupted is not original
    assert truth["ground_truth_version"] == AB.GROUND_TRUTH_VERSION
    assert truth["event_count"] > 0
    assert "missing_values" in truth["issue_summary"]
    assert "duplicate_rows" in truth["issue_summary"]
    assert "Injected_Constant_1" in corrupted.columns
    assert "Injected_ID_1" in corrupted.columns


def test_corruption_is_reproducible_with_random_state():
    first, first_truth = AB.inject_issues(
        _clean_frame(),
        missing_rate=0.05,
        duplicate_rate=0.05,
        invalid_range_rate=0.05,
        random_state=123,
    )
    second, second_truth = AB.inject_issues(
        _clean_frame(),
        missing_rate=0.05,
        duplicate_rate=0.05,
        invalid_range_rate=0.05,
        random_state=123,
    )
    pd.testing.assert_frame_equal(first, second)
    assert first_truth == second_truth


def test_duplicate_injection_produces_exact_duplicate_rows():
    corrupted, truth = AB.inject_issues(
        _clean_frame(),
        duplicate_rate=0.10,
        identifier_columns=1,
        random_state=3,
    )
    assert int(corrupted.duplicated().sum()) >= 1
    assert "duplicate_rows" in truth["issue_summary"]


def test_ground_truth_pairs_include_dataset_and_column_findings():
    _, truth = AB.inject_issues(
        _clean_frame(),
        missing_rate=0.02,
        duplicate_rate=0.05,
        constant_columns=1,
        random_state=10,
    )
    pairs = AB.ground_truth_pairs(truth)
    assert ("duplicate_rows", "__dataset__") in pairs
    assert ("constant_columns", "Injected_Constant_1") in pairs
    assert any(code == "missing_values" for code, _ in pairs)


def test_column_restrictions_are_respected():
    corrupted, truth = AB.inject_issues(
        _clean_frame(),
        missing_rate=0.10,
        columns={"missing_values": ["Salary"]},
        random_state=5,
    )
    assert corrupted["Salary"].isna().any()
    assert not corrupted["Age"].isna().any()
    assert truth["issue_summary"]["missing_values"]["columns"] == ["Salary"]


@pytest.mark.parametrize("name", ["missing_rate", "duplicate_rate", "outlier_rate"])
def test_invalid_rates_are_rejected(name):
    kwargs = {name: 1.5}
    with pytest.raises(ValueError):
        AB.inject_issues(_clean_frame(), **kwargs)
