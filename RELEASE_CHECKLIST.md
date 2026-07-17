# AxiomBraid 2.0.0 Release Checklist

## Verified in this package

- [x] Runtime and package versions synchronized
- [x] Stable API status and public API version 2
- [x] Version 1 compatibility preserved
- [x] Version 2 APIs present
- [x] Regression tests pass
- [x] Source compilation and Ruff critical checks pass
- [x] Wheel and source distribution build
- [x] Twine checks pass
- [x] Fresh wheel installation passes
- [x] CLI, self-check, and compatibility check pass
- [x] Migration, stability, and release documentation included
- [x] Project URLs included

## Actions before publication

- [ ] Review final Git diff
- [ ] Push exact files to Version 2 branch
- [ ] Confirm GitHub CI
- [ ] Merge into `main`
- [ ] Tag `v2.0.0`
- [ ] Publish GitHub Release
- [ ] Confirm Trusted Publishing
- [ ] Install `axiombraid==2.0.0` from PyPI in a fresh environment

## Doxygen documentation

- [ ] `PROJECT_NUMBER` in `Doxyfile` is `2.0.0`.
- [ ] `generate_doxygen.cmd` completes successfully on Windows.
- [ ] `docs/doxygen/html/index.html` is generated.
- [ ] `docs/doxygen/doxygen-warnings.log` has been reviewed.
- [ ] The GitHub `Doxygen Documentation` workflow passes.
- [ ] The generated HTML artifact opens correctly.

