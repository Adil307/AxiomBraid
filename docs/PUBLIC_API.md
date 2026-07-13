# Stable Public API

AxiomBraid 1.x follows semantic versioning. The top-level names below are the
supported public API and will not be removed or incompatibly changed before 2.0.

```python
import axiombraid as AB
```

## Functional API

- `AB.read_csv`, `AB.read_excel`
- `AB.inspect`, `AB.report`
- `AB.clean`, `AB.validate`
- `AB.compare`, `AB.detect_drift`
- `AB.export_html`
- `AB.stream_csv`, `AB.cached_inspect`

## Object API

- `AB.Guide` / `AB.DataGuide`
- `AB.BatchAnalyzer`
- `AB.InspectionCache`

## Diagnostics

- `AB.about()`
- `AB.self_check()`

Internal module functions not exported from `axiombraid.__all__` may change in a
minor release.
