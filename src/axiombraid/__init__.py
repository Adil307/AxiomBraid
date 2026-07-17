"""AxiomBraid 2 stable public API.

Recommended usage::

    import axiombraid as AB
"""

from ._version import (
    API_STATUS,
    BRAND_NAME,
    PUBLIC_API_VERSION,
    RELEASE_STAGE,
    VERSION_INFO,
    __version__,
)

from .inspector import DataGuide
from .batch import BatchAnalyzer, batch_analyze
from .cache import InspectionCache, cached_inspect
from .config import DEFAULT_CONFIG, export_config, load_config
from .streaming import stream_csv
from .corruption import GROUND_TRUTH_VERSION, inject_issues, ground_truth_pairs
from .evaluation import (
    EVALUATION_VERSION,
    evaluate_detection,
    evaluate_quality_response,
    run_evaluation,
    benchmark_inspection,
    benchmark_scaling,
    suggest_confidence_thresholds,
    compatibility_check,
    format_evaluation_console,
    evaluation_report,
    format_benchmark_console,
)
from .themes import available_themes
from .diagnostics import about, self_check
from .scoring_v2 import (
    DEFAULT_QUALITY_PROFILE_CONFIG,
    normalize_quality_profile_config,
    build_quality_profile,
    format_quality_profile_console,
)
from .confidence import (
    DEFAULT_CONFIDENCE_CONFIG,
    normalize_confidence_config,
    issue_confidence,
    add_confidence,
    confidence_report,
)
from .api import (
    read_csv,
    read_excel,
    guide,
    inspect,
    inspect_with_confidence,
    quality_profile,
    report,
    clean,
    validate,
    compare,
    detect_drift,
    export_html,
)

Guide = DataGuide

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
    "inspect_with_confidence",
    "quality_profile",
    "report",
    "clean",
    "validate",
    "compare",
    "detect_drift",
    "export_html",
    "about",
    "self_check",
    "DEFAULT_CONFIDENCE_CONFIG",
    "normalize_confidence_config",
    "issue_confidence",
    "add_confidence",
    "confidence_report",
    "DEFAULT_QUALITY_PROFILE_CONFIG",
    "normalize_quality_profile_config",
    "build_quality_profile",
    "format_quality_profile_console",
    "GROUND_TRUTH_VERSION",
    "inject_issues",
    "ground_truth_pairs",
    "EVALUATION_VERSION",
    "evaluate_detection",
    "evaluate_quality_response",
    "run_evaluation",
    "benchmark_inspection",
    "benchmark_scaling",
    "suggest_confidence_thresholds",
    "compatibility_check",
    "format_evaluation_console",
    "evaluation_report",
    "format_benchmark_console",
    "API_STATUS",
    "RELEASE_STAGE",
    "PUBLIC_API_VERSION",
    "BRAND_NAME",
    "VERSION_INFO",
    "__version__",
]
