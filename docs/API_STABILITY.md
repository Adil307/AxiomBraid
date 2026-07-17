# API Stability Policy

AxiomBraid follows semantic versioning.

- Patch releases (`2.0.x`) provide compatible fixes.
- Minor releases (`2.x.0`) may add compatible functionality.
- Incompatible changes require a new major version.

Names exported through `axiombraid.__all__` form the stable Version 2 top-level API. A public API targeted for removal will normally receive a documented deprecation period. Internal and private names may change.

Version 2 preserves supported Version 1 workflows. Use `AB.compatibility_check()` for a runtime diagnostic.
