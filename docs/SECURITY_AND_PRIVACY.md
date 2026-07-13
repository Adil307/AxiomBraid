# Security and Privacy Review

- Dataset fingerprints are SHA-256 digests and do not intentionally include raw values.
- Cache entries contain inspection results and may include example values from detected issues;
  store caches in an access-controlled location when data is sensitive.
- Plugins receive deep copies, but plugin code is trusted local Python code and can access the host environment.
- HTML reports escape dataset-derived text before rendering.
- Cleaning never changes caller data through the functional API and sampled cleaning is blocked.
- AxiomBraid does not upload datasets or make network requests.
