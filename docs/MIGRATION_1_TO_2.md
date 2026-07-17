# Migration from AxiomBraid 1.x to 2.0

Most users only need to upgrade:

```powershell
py -m pip install --upgrade axiombraid
```

Existing code remains valid:

```python
import axiombraid as AB
frame = AB.read_csv("data.csv")
result = AB.inspect(frame)
AB.report(frame)
cleaned = AB.clean(frame, risk="low")
```

New confidence and quality output is opt-in:

```python
result = AB.inspect(frame, include_confidence=True, include_quality_profile=True)
```

Metadata changes:

```text
API_STATUS: stable
PUBLIC_API_VERSION: 2
VERSION_INFO: (2, 0, 0)
```

Confidence is evidence strength, not probability. Evaluation metrics use issue/column granularity. Validity covers supported rules rather than every possible business rule.
