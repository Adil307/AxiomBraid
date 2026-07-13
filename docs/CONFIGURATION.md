# Configuration

AxiomBraid accepts JSON, YAML, and TOML configuration files.

```yaml
analysis:
  high_cardinality_threshold: 0.90
  low_missing_threshold: 5
  high_missing_threshold: 30
performance:
  mode: auto
  sample_rows: 50000
  strategy: random
  random_state: 42
report:
  language: en
  html_theme: light
```

```python
import axiombraid as AB
guide = AB.Guide.from_config("data.csv", "axiombraid.yaml")
```
