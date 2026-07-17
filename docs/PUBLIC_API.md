# Stable Public API — Version 2

```python
import axiombraid as AB
```

## Version 1-compatible core

- `AB.read_csv`, `AB.read_excel`, `AB.guide`
- `AB.inspect`, `AB.report`, `AB.clean`, `AB.validate`
- `AB.compare`, `AB.detect_drift`, `AB.export_html`
- `AB.stream_csv`, `AB.cached_inspect`, `AB.batch_analyze`
- `AB.Guide`, `AB.DataGuide`, `AB.BatchAnalyzer`, `AB.InspectionCache`

## Version 2

- `AB.inspect_with_confidence`, `AB.issue_confidence`, `AB.add_confidence`, `AB.confidence_report`
- `AB.quality_profile`, `AB.build_quality_profile`, `AB.format_quality_profile_console`
- `AB.inject_issues`, `AB.ground_truth_pairs`
- `AB.evaluate_detection`, `AB.evaluate_quality_response`, `AB.run_evaluation`, `AB.evaluation_report`
- `AB.benchmark_inspection`, `AB.benchmark_scaling`, `AB.suggest_confidence_thresholds`
- `AB.format_evaluation_console`, `AB.format_benchmark_console`, `AB.compatibility_check`

## Diagnostics and metadata

- `AB.about`, `AB.self_check`
- `AB.__version__`, `AB.VERSION_INFO`, `AB.API_STATUS`, `AB.PUBLIC_API_VERSION`, `AB.RELEASE_STAGE`, `AB.BRAND_NAME`

Names exported through `axiombraid.__all__` are supported. Confidence is evidence strength, not probability. Evaluation metrics use issue/column granularity.
