# Migration from DataGuidePy

Old code continues to work in 0.9 with a `DeprecationWarning`:

```python
import dataguidepy
```

Recommended replacement:

```python
import axiombraid as AB
```

The old namespace and `dataguide` command are scheduled for removal in 1.0.
