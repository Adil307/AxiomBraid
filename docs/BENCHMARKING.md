# Benchmarking

Run the local benchmark:

```powershell
py benchmarks\benchmark_release.py
```

Results depend on hardware, Python, pandas, operating system, and dataset shape.
Baselines are evidence for regression detection, not universal performance claims.

The benchmark records:

- full inspection duration
- cached inspection miss/hit duration
- streaming CSV duration
- row and column counts
- environment metadata
