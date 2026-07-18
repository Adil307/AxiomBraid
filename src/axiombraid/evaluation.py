"""Detection evaluation, confidence diagnostics, performance, and compatibility.

Phase 6 evaluates AxiomBraid at the same issue/column granularity exposed by
its public inspection report. Scores are reproducible measurements, while any
suggested confidence thresholds remain empirical heuristics rather than
calibrated probabilities.
"""

from __future__ import annotations

from copy import deepcopy
import importlib
import math
from pathlib import Path
import statistics
import time
import tracemalloc
from typing import Any, Iterable

import pandas as pd

from .corruption import ground_truth_pairs, inject_issues


EVALUATION_VERSION = "1.1"
EVALUATABLE_CODES = {
    "missing_values",
    "duplicate_rows",
    "constant_columns",
    "text_inconsistencies",
    "potential_outliers",
    "suspicious_numeric_ranges",
    "date_like_text",
    "possible_identifiers",
    "high_cardinality_descriptive",
    "empty_dataset",
    "no_numerical_columns",
}


def _inspection_pairs(inspection: dict[str, Any]) -> set[tuple[str, str]]:
    if not isinstance(inspection, dict):
        raise TypeError("inspection_result must be a dictionary.")
    pairs: set[tuple[str, str]] = set()
    for issue in inspection.get("issues", []):
        if not isinstance(issue, dict):
            continue
        code = str(issue.get("code", "")).strip()
        if not code or code not in EVALUATABLE_CODES:
            continue
        columns = issue.get("columns", [])
        if isinstance(columns, list) and columns:
            pairs.update((code, str(column)) for column in columns)
        else:
            pairs.add((code, "__dataset__"))
    return pairs


def _metric(tp: int, fp: int, fn: int) -> dict[str, Any]:
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    false_positive_rate = fp / (tp + fp) if tp + fp else 0.0
    return {
        "true_positives": int(tp),
        "false_positives": int(fp),
        "false_negatives": int(fn),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "false_positive_share": round(false_positive_rate, 4),
    }

def _outlier_position_pairs(
    inspection: dict[str, Any] | None,
) -> tuple[set[tuple[str, int]], bool]:
    """Return ``(column, row_position)`` outlier evidence from an inspection.

    The boolean indicates whether every included column exposed complete
    row-level evidence. Version 2.0.0 reports do not contain this evidence and
    therefore return ``False`` without guessing.
    """
    if not isinstance(inspection, dict):
        return set(), False

    section = inspection.get("outliers", {})
    if not isinstance(section, dict):
        return set(), False

    pairs: set[tuple[str, int]] = set()
    complete = True

    for column, details in section.items():
        if not isinstance(details, dict):
            complete = False
            continue

        positions = details.get("outlier_row_positions")
        if not isinstance(positions, list):
            complete = False
            continue

        if details.get("outlier_evidence_complete") is not True:
            complete = False

        for position in positions:
            if isinstance(position, bool) or not isinstance(position, int):
                complete = False
                continue
            pairs.add((str(column), int(position)))

    return pairs, complete


def _ground_truth_outlier_pairs(
    ground_truth: dict[str, Any],
) -> set[tuple[str, int]]:
    """Return injected outlier ``(column, row_position)`` pairs."""
    pairs: set[tuple[str, int]] = set()

    for event in ground_truth.get("events", []):
        if not isinstance(event, dict):
            continue
        if str(event.get("issue_code", "")) != "potential_outliers":
            continue

        locations = event.get("cell_locations", [])
        if isinstance(locations, list):
            for location in locations:
                if not isinstance(location, dict):
                    continue
                column = location.get("column")
                row = location.get("row")
                if isinstance(column, str) and isinstance(row, int) and not isinstance(row, bool):
                    pairs.add((column, row))

    return pairs


def _evaluate_outlier_events(
    inspection: dict[str, Any],
    ground_truth: dict[str, Any],
    baseline_inspection: dict[str, Any] | None,
) -> dict[str, Any]:
    """Evaluate injected outliers at row level when complete evidence exists."""
    expected = _ground_truth_outlier_pairs(ground_truth)
    detected, detected_complete = _outlier_position_pairs(inspection)
    baseline, baseline_complete = _outlier_position_pairs(baseline_inspection)

    evidence_complete = detected_complete and (
        baseline_inspection is None or baseline_complete
    )

    if not expected:
        return {
            "status": "not_applicable",
            "granularity": "outlier_cell",
            "expected_event_count": 0,
            "evidence_complete": evidence_complete,
            **_metric(0, 0, 0),
        }

    if not evidence_complete:
        return {
            "status": "not_evaluated_incomplete_evidence",
            "granularity": "outlier_cell",
            "expected_event_count": len(expected),
            "evidence_complete": False,
            "note": (
                "Row-level outlier evidence is unavailable or truncated. "
                "No event-level accuracy claim was made."
            ),
        }

    newly_detected = detected - baseline
    true_positive_pairs = expected & detected
    false_negative_pairs = expected - detected
    false_positive_pairs = newly_detected - expected
    metrics = _metric(
        len(true_positive_pairs),
        len(false_positive_pairs),
        len(false_negative_pairs),
    )

    return {
        "status": "evaluated",
        "granularity": "outlier_cell",
        "expected_event_count": len(expected),
        "evidence_complete": True,
        **metrics,
        "true_positive_pairs": [list(item) for item in sorted(true_positive_pairs)],
        "false_positive_pairs": [list(item) for item in sorted(false_positive_pairs)],
        "false_negative_pairs": [list(item) for item in sorted(false_negative_pairs)],
        "note": (
            "This event-level diagnostic avoids inferring detection from a net "
            "change in per-column outlier counts."
        ),
    }


def _confidence_lookup(inspection: dict[str, Any]) -> dict[tuple[str, str], float]:
    lookup: dict[tuple[str, str], float] = {}
    for issue in inspection.get("issues", []):
        if not isinstance(issue, dict):
            continue
        code = str(issue.get("code", "")).strip()
        confidence = issue.get("confidence", {})
        if not isinstance(confidence, dict):
            continue
        per_column = confidence.get("per_column", {})
        if isinstance(per_column, dict) and per_column:
            for column, detail in per_column.items():
                if isinstance(detail, dict) and isinstance(detail.get("score"), (int, float)):
                    lookup[(code, str(column))] = float(detail["score"])
        elif isinstance(confidence.get("score"), (int, float)):
            lookup[(code, "__dataset__")] = float(confidence["score"])
    return lookup


def evaluate_detection(
    inspection_result: dict[str, Any],
    ground_truth: dict[str, Any],
    *,
    baseline_inspection: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Evaluate detection at issue/column level.

    ``baseline_inspection`` is strongly recommended for real datasets. Findings
    already present in the clean baseline are subtracted before the corrupted
    dataset is scored, preventing pre-existing issues from being mislabeled as
    synthetic false positives.
    """

    expected_all = ground_truth_pairs(ground_truth)
    detected_all = _inspection_pairs(inspection_result)
    baseline = _inspection_pairs(baseline_inspection) if baseline_inspection is not None else set()
    detected = detected_all - baseline
    preexisting_expected = expected_all & baseline
    expected = expected_all - baseline

    tp_pairs = detected & expected
    fp_pairs = detected - expected
    fn_pairs = expected - detected
    overall = _metric(len(tp_pairs), len(fp_pairs), len(fn_pairs))

    codes = sorted({code for code, _ in expected | detected})
    per_detector: dict[str, dict[str, Any]] = {}
    for code in codes:
        expected_code = {(c, column) for c, column in expected if c == code}
        detected_code = {(c, column) for c, column in detected if c == code}
        metrics = _metric(
            len(expected_code & detected_code),
            len(detected_code - expected_code),
            len(expected_code - detected_code),
        )
        metrics["expected_pairs"] = len(expected_code)
        metrics["detected_pairs"] = len(detected_code)
        per_detector[code] = metrics

    confidence_lookup = _confidence_lookup(inspection_result)
    confidence_records = []
    for pair in sorted(detected):
        score = confidence_lookup.get(pair)
        if score is None:
            # Dataset-level findings can have a score even when pair extraction
            # used the synthetic dataset marker.
            score = confidence_lookup.get((pair[0], "__dataset__"))
        confidence_records.append(
            {
                "issue_code": pair[0],
                "column": pair[1],
                "score": score,
                "outcome": "true_positive" if pair in expected else "false_positive",
            }
        )

    true_scores = [record["score"] for record in confidence_records if record["outcome"] == "true_positive" and record["score"] is not None]
    false_scores = [record["score"] for record in confidence_records if record["outcome"] == "false_positive" and record["score"] is not None]
    confidence_diagnostics = {
        "scored_detection_count": len(true_scores) + len(false_scores),
        "true_positive_average": round(statistics.mean(true_scores), 4) if true_scores else None,
        "false_positive_average": round(statistics.mean(false_scores), 4) if false_scores else None,
        "true_positive_scores": true_scores,
        "false_positive_scores": false_scores,
        "note": (
            "Confidence diagnostics compare evidence-strength scores with observed "
            "evaluation outcomes; they do not calibrate statistical probabilities."
        ),
    }

    return {
        "evaluation_version": EVALUATION_VERSION,
        "granularity": "issue_column_pair",
        "baseline_subtracted": baseline_inspection is not None,
        "overall": overall,
        "per_detector": per_detector,
        "expected_pairs": [list(pair) for pair in sorted(expected)],
        "all_injected_pairs": [list(pair) for pair in sorted(expected_all)],
        "preexisting_expected_pairs": [list(pair) for pair in sorted(preexisting_expected)],
        "detected_pairs": [list(pair) for pair in sorted(detected)],
        "true_positive_pairs": [list(pair) for pair in sorted(tp_pairs)],
        "false_positive_pairs": [list(pair) for pair in sorted(fp_pairs)],
        "false_negative_pairs": [list(pair) for pair in sorted(fn_pairs)],
        "confidence_records": confidence_records,
        "confidence_diagnostics": confidence_diagnostics,
        "outlier_event_evaluation": _evaluate_outlier_events(
            inspection_result,
            ground_truth,
            baseline_inspection,
        ),
        "note": (
            "Metrics operate at issue/column granularity because that is the "
            "public detection granularity exposed by AxiomBraid inspection reports. "
            "Injected pairs already present in the baseline are reported as pre-existing "
            "and excluded from scoring."
        ),
    }


def evaluate_quality_response(
    clean_data: Any,
    corrupted_data: Any,
    *,
    quality_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Measure how the explainable quality profile responds to corruption."""
    from .api import quality_profile

    clean = quality_profile(clean_data, quality_config=quality_config)
    corrupted = quality_profile(corrupted_data, quality_config=quality_config)
    dimension_deltas = {
        name: round(
            float(corrupted["dimensions"][name]["score"])
            - float(clean["dimensions"][name]["score"]),
            4,
        )
        for name in clean["dimensions"]
    }
    overall_delta = round(float(corrupted["score"]) - float(clean["score"]), 4)
    return {
        "clean_score": clean["score"],
        "corrupted_score": corrupted["score"],
        "overall_delta": overall_delta,
        "score_decreased": overall_delta < 0,
        "dimension_deltas": dimension_deltas,
        "clean_profile": clean,
        "corrupted_profile": corrupted,
    }


def run_evaluation(
    clean_data: Any,
    *,
    corruption_config: dict[str, Any],
    inspection_options: dict[str, Any] | None = None,
    include_quality_response: bool = True,
) -> dict[str, Any]:
    """Run corruption, baseline inspection, corrupted inspection, and evaluation."""
    if not isinstance(corruption_config, dict):
        raise TypeError("corruption_config must be a dictionary.")
    if inspection_options is not None and not isinstance(inspection_options, dict):
        raise TypeError("inspection_options must be a dictionary or None.")

    from .api import inspect

    corrupted, truth = inject_issues(clean_data, **corruption_config)
    options = dict(inspection_options or {})
    options.setdefault("include_confidence", True)
    options.setdefault("include_quality_profile", True)
    baseline = inspect(clean_data, **options)
    corrupted_inspection = inspect(corrupted, **options)
    detection = evaluate_detection(
        corrupted_inspection,
        truth,
        baseline_inspection=baseline,
    )
    result = {
        "corrupted_dataframe": corrupted,
        "ground_truth": truth,
        "baseline_inspection": baseline,
        "corrupted_inspection": corrupted_inspection,
        "detection_evaluation": detection,
    }
    if include_quality_response:
        result["quality_response"] = evaluate_quality_response(clean_data, corrupted)
    return result


def _load_frame(data: Any) -> pd.DataFrame:
    if isinstance(data, pd.DataFrame):
        return data.copy(deep=True)
    path = Path(data)
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path)
    if path.suffix.lower() in {".xlsx", ".xls"}:
        return pd.read_excel(path)
    raise ValueError("Benchmark input must be a DataFrame, CSV, or Excel file.")


def benchmark_inspection(
    data: Any,
    *,
    repeats: int = 3,
    include_confidence: bool = True,
    include_quality_profile: bool = True,
    inspection_options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Benchmark inspection runtime and Python-tracked peak memory."""
    if isinstance(repeats, bool) or not isinstance(repeats, int):
        raise TypeError("repeats must be an integer.")
    if repeats < 1:
        raise ValueError("repeats must be at least 1.")
    if inspection_options is not None and not isinstance(inspection_options, dict):
        raise TypeError("inspection_options must be a dictionary or None.")

    from .api import inspect

    frame = _load_frame(data)
    options = dict(inspection_options or {})
    options["include_confidence"] = include_confidence
    options["include_quality_profile"] = include_quality_profile

    # Warm-up reduces one-time import and code-path initialization noise.
    inspect(frame, **options)
    durations: list[float] = []
    peaks: list[int] = []
    for _ in range(repeats):
        tracemalloc.start()
        started = time.perf_counter()
        inspect(frame, **options)
        duration = time.perf_counter() - started
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        durations.append(duration)
        peaks.append(int(peak))

    return {
        "rows": int(frame.shape[0]),
        "columns": int(frame.shape[1]),
        "repeats": repeats,
        "include_confidence": include_confidence,
        "include_quality_profile": include_quality_profile,
        "runtime_seconds": {
            "minimum": round(min(durations), 6),
            "median": round(statistics.median(durations), 6),
            "mean": round(statistics.mean(durations), 6),
            "maximum": round(max(durations), 6),
            "runs": [round(value, 6) for value in durations],
        },
        "peak_memory_bytes": {
            "minimum": min(peaks),
            "median": int(statistics.median(peaks)),
            "mean": int(statistics.mean(peaks)),
            "maximum": max(peaks),
            "runs": peaks,
        },
        "measurement_note": (
            "Peak memory is measured with Python tracemalloc and may not include "
            "all native-library allocations. Runtime includes inspection only."
        ),
    }


def benchmark_scaling(
    data: Any,
    *,
    sizes: Iterable[int] = (100, 1000, 5000),
    repeats: int = 2,
    random_state: int = 42,
    include_confidence: bool = True,
    include_quality_profile: bool = True,
) -> dict[str, Any]:
    """Benchmark AxiomBraid across deterministic resampled dataset sizes."""
    frame = _load_frame(data)
    if frame.empty:
        raise ValueError("Cannot run scaling benchmark on an empty dataset.")
    normalized_sizes = []
    for size in sizes:
        if isinstance(size, bool) or not isinstance(size, int) or size < 1:
            raise ValueError("Each benchmark size must be a positive integer.")
        normalized_sizes.append(size)
    results = []
    for size in normalized_sizes:
        sampled = frame.sample(n=size, replace=size > len(frame), random_state=random_state).reset_index(drop=True)
        results.append(
            benchmark_inspection(
                sampled,
                repeats=repeats,
                include_confidence=include_confidence,
                include_quality_profile=include_quality_profile,
            )
        )
    return {
        "sizes": normalized_sizes,
        "results": results,
        "random_state": random_state,
    }


def _quantile(values: list[float], fraction: float) -> float:
    if not values:
        raise ValueError("Cannot calculate a quantile from no values.")
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def suggest_confidence_thresholds(
    evaluation_runs: dict[str, Any] | Iterable[dict[str, Any]],
    *,
    minimum_true_positives: int = 3,
) -> dict[str, Any]:
    """Suggest empirical confidence labels from observed true-positive scores.

    This helper does not calibrate probabilities. It is a transparent tuning aid
    that uses the 25th and 75th percentiles of true-positive evidence scores.
    """
    runs = [evaluation_runs] if isinstance(evaluation_runs, dict) else list(evaluation_runs)
    true_scores: list[float] = []
    false_scores: list[float] = []
    for run in runs:
        diagnostics = run.get("confidence_diagnostics", run.get("detection_evaluation", {}).get("confidence_diagnostics", {}))
        true_scores.extend(float(value) for value in diagnostics.get("true_positive_scores", []))
        false_scores.extend(float(value) for value in diagnostics.get("false_positive_scores", []))
    if len(true_scores) < minimum_true_positives:
        return {
            "status": "insufficient_evidence",
            "true_positive_score_count": len(true_scores),
            "minimum_required": minimum_true_positives,
            "suggested_thresholds": None,
            "note": "Collect more labeled evaluation runs before tuning confidence labels.",
        }
    medium = max(0.5, min(0.95, _quantile(true_scores, 0.25)))
    high = max(medium, min(0.99, _quantile(true_scores, 0.75)))
    return {
        "status": "suggestion_available",
        "true_positive_score_count": len(true_scores),
        "false_positive_score_count": len(false_scores),
        "suggested_thresholds": {"high": round(high, 2), "medium": round(medium, 2)},
        "true_positive_median": round(statistics.median(true_scores), 4),
        "false_positive_median": round(statistics.median(false_scores), 4) if false_scores else None,
        "method": "true_positive_score_quartiles",
        "is_probability_calibration": False,
        "note": "Validate suggestions on independent datasets before adopting them.",
    }


def compatibility_check() -> dict[str, Any]:
    """Verify the Version 1 compatibility surface and stable Version 2 APIs."""
    package = importlib.import_module("axiombraid")
    required_v1 = [
        "read_csv", "read_excel", "inspect", "report", "clean", "validate",
        "compare", "detect_drift", "export_html", "stream_csv", "cached_inspect",
        "batch_analyze", "Guide", "DataGuide", "BatchAnalyzer", "InspectionCache",
    ]
    required_v2 = [
        "inspect_with_confidence", "quality_profile", "issue_confidence",
        "add_confidence", "confidence_report", "build_quality_profile",
        "format_quality_profile_console", "inject_issues", "ground_truth_pairs",
        "evaluate_detection", "evaluate_quality_response", "run_evaluation",
        "evaluation_report", "benchmark_inspection", "benchmark_scaling",
        "suggest_confidence_thresholds", "format_evaluation_console",
        "format_benchmark_console", "compatibility_check",
    ]
    checks = {
        name: bool(hasattr(package, name) and (callable(getattr(package, name)) or name in {"Guide", "DataGuide", "BatchAnalyzer", "InspectionCache"}))
        for name in required_v1 + required_v2
    }
    missing = sorted(name for name, ok in checks.items() if not ok)
    return {
        "ok": not missing,
        "version": getattr(package, "__version__", None),
        "api_status": getattr(package, "API_STATUS", None),
        "checks": checks,
        "missing": missing,
        "v1_api_count": len(required_v1),
        "v2_api_count": len(required_v2),
    }


def format_evaluation_console(
    evaluation: dict[str, Any],
    *,
    language: str = "en",
) -> str:
    """Format a concise human-readable evaluation report."""
    if not isinstance(evaluation, dict):
        raise TypeError("evaluation must be a dictionary.")
    detection = evaluation.get("detection_evaluation", evaluation)
    overall = detection.get("overall", {})
    language_code = str(language).strip().lower().replace("-", "_")
    roman_urdu = language_code in {"roman_urdu", "romanurdu", "ur"}
    title = (
        "AXIOMBRAID DETECTION EVALUATION"
        if not roman_urdu
        else "AXIOMBRAID DETECTION EVALUATION / JAIZA"
    )
    lines = ["=" * 68, title, "=" * 68]
    lines.extend(
        [
            f"Precision: {float(overall.get('precision', 0.0)) * 100:.2f}%",
            f"Recall:    {float(overall.get('recall', 0.0)) * 100:.2f}%",
            f"F1 score:  {float(overall.get('f1', 0.0)) * 100:.2f}%",
            f"True positives:  {overall.get('true_positives', 0)}",
            f"False positives: {overall.get('false_positives', 0)}",
            f"False negatives: {overall.get('false_negatives', 0)}",
        ]
    )
    preexisting = detection.get("preexisting_expected_pairs", [])
    if preexisting:
        lines.append(
            f"Pre-existing injected-type findings excluded from scoring: {len(preexisting)}"
        )
    per_detector = detection.get("per_detector", {})
    if per_detector:
        lines.extend(["", "PER-DETECTOR RESULTS", "-" * 68])
        for code, metrics in sorted(per_detector.items()):
            label = code.replace("_", " ").title()
            lines.append(
                f"{label}: F1 {float(metrics.get('f1', 0.0)) * 100:.2f}% "
                f"| P {float(metrics.get('precision', 0.0)) * 100:.2f}% "
                f"| R {float(metrics.get('recall', 0.0)) * 100:.2f}%"
            )
    quality = evaluation.get("quality_response")
    if isinstance(quality, dict):
        lines.extend(["", "QUALITY-SCORE RESPONSE", "-" * 68])
        lines.append(f"Clean score:     {quality.get('clean_score')}")
        lines.append(f"Corrupted score: {quality.get('corrupted_score')}")
        lines.append(f"Score change:    {quality.get('overall_delta')}")
    lines.extend(
        [
            "",
            "Note: Metrics are calculated at issue/column granularity.",
            "Confidence values remain evidence-strength scores, not probabilities.",
        ]
    )
    return "\n".join(lines)


def evaluation_report(
    clean_data: Any,
    *,
    corruption_config: dict[str, Any],
    inspection_options: dict[str, Any] | None = None,
    include_quality_response: bool = True,
    language: str = "en",
) -> dict[str, Any]:
    """Run an evaluation, print a readable report, and return full results."""
    result = run_evaluation(
        clean_data,
        corruption_config=corruption_config,
        inspection_options=inspection_options,
        include_quality_response=include_quality_response,
    )
    print(format_evaluation_console(result, language=language))
    return result


def format_benchmark_console(benchmark: dict[str, Any]) -> str:
    """Format a concise benchmark report for terminal users."""
    if not isinstance(benchmark, dict):
        raise TypeError("benchmark must be a dictionary.")
    if "results" in benchmark:
        lines = ["=" * 68, "AXIOMBRAID SCALING BENCHMARK", "=" * 68]
        for entry in benchmark.get("results", []):
            lines.append(
                f"Rows {entry['rows']}: median {entry['runtime_seconds']['median']:.6f}s "
                f"| peak {entry['peak_memory_bytes']['maximum']} bytes"
            )
        return "\n".join(lines)
    return "\n".join(
        [
            "=" * 68,
            "AXIOMBRAID INSPECTION BENCHMARK",
            "=" * 68,
            f"Shape: {benchmark.get('rows')} rows x {benchmark.get('columns')} columns",
            f"Repeats: {benchmark.get('repeats')}",
            f"Median runtime: {benchmark.get('runtime_seconds', {}).get('median')} seconds",
            f"Mean runtime:   {benchmark.get('runtime_seconds', {}).get('mean')} seconds",
            f"Peak memory:    {benchmark.get('peak_memory_bytes', {}).get('maximum')} bytes",
            "Note: tracemalloc may not include every native-library allocation.",
        ]
    )