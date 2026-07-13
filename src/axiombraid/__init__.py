"""AxiomBraid stable public API.

Recommended usage::

    import axiombraid as AB
"""

from .inspector import DataGuide
from .batch import BatchAnalyzer, batch_analyze
from .cache import InspectionCache, cached_inspect
from .config import DEFAULT_CONFIG, export_config, load_config
from .streaming import stream_csv
from .themes import available_themes
from .diagnostics import about, self_check
from .api import (
    read_csv,
    read_excel,
    guide,
    inspect,
    report,
    clean,
    validate,
    compare,
    detect_drift,
    export_html,
)

Guide = DataGuide
API_STATUS = "stable"
PUBLIC_API_VERSION = "1"
BRAND_NAME = "AxiomBraid"
VERSION_INFO = (1, 0, 0)
__version__ = "1.0.0"

__all__ = [
    "Guide",
    "DataGuide",
    "BatchAnalyzer",
    "batch_analyze",
    "InspectionCache",
    "cached_inspect",
    "stream_csv",
    "DEFAULT_CONFIG",
    "load_config",
    "export_config",
    "available_themes",
    "read_csv",
    "read_excel",
    "guide",
    "inspect",
    "report",
    "clean",
    "validate",
    "compare",
    "detect_drift",
    "export_html",
    "about",
    "self_check",
    "API_STATUS",
    "PUBLIC_API_VERSION",
    "BRAND_NAME",
    "VERSION_INFO",
    "__version__",
]
