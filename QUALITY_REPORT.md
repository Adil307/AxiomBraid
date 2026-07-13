# AxiomBraid 1.0 Quality Report

Generated: 2026-07-13

## Verification summary

- Automated tests: **144 passed**
- Measured statement/branch coverage: **89%** on the local verification environment
- Critical Ruff checks: passed
- Wheel build: passed
- Source distribution build: passed
- Twine metadata/readme checks: passed
- Fresh virtual-environment installation: passed
- `AB.self_check()`: passed
- `axiombraid --version`: passed
- `python -m axiombraid --version`: passed
- PEP 561 `py.typed` marker: present in wheel

## Verification environment

- Python: 3.13.5
- pandas: 2.2.3
- Platform: Linux-4.4.0-x86_64-with-glibc2.41

## Local benchmark snapshot

| Rows | Full inspection | Cache miss | Cache hit |
|---:|---:|---:|---:|
| 1,000 | 0.1294s | 0.1245s | 0.0011s |
| 10,000 | 0.7582s | 0.7206s | 0.0043s |
| 50,000 | 3.6182s | 3.9311s | 0.0165s |

Streaming profile: 100,000 rows with a 10,000-row sample in 1.1578s.

> These timings are local regression baselines, not universal performance claims. Hardware, operating system, Python, pandas, storage, and dataset shape affect results.
