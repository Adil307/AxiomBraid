"""Configuration-file support for AxiomBraid."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.9/3.10 fallback
    tomllib = None


DEFAULT_CONFIG: dict[str, Any] = {
    "analysis": {
        "high_cardinality_threshold": 0.90,
        "min_unique_for_high_cardinality": 3,
        "structured_identifier_threshold": 0.80,
        "low_missing_threshold": 5.0,
        "high_missing_threshold": 30.0,
        "outlier_iqr_multiplier": 1.5,
        "min_outlier_sample_size": 4,
        "date_like_threshold": 0.80,
        "min_date_like_non_missing": 3,
    },
    "performance": {
        "mode": "auto",
        "sample_rows": 50000,
        "strategy": "random",
        "random_state": 42,
    },
    "report": {
        "language": "en",
        "html_theme": "light",
        "formats": ["json", "html"],
    },
    "batch": {
        "recursive": False,
        "continue_on_error": True,
        "workers": 1,
    },
    "cache": {
        "enabled": False,
        "directory": ".axiombraid_cache",
    },
}


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = deepcopy(value)
    return result


def normalize_config(config: dict[str, Any] | None) -> dict[str, Any]:
    """Merge user settings with safe defaults and validate top-level sections."""
    if config is None:
        return deepcopy(DEFAULT_CONFIG)
    if not isinstance(config, dict):
        raise TypeError("Configuration must be a dictionary.")
    allowed = {"analysis", "performance", "report", "batch", "cache"}
    unexpected = sorted(set(config) - allowed)
    if unexpected:
        raise ValueError(
            "Unsupported configuration section(s): " + ", ".join(unexpected)
        )
    for section, value in config.items():
        if not isinstance(value, dict):
            raise TypeError(f"Configuration section '{section}' must be a dictionary.")
    return _deep_merge(DEFAULT_CONFIG, config)


def load_config(config: str | Path | dict[str, Any] | None) -> dict[str, Any]:
    """Load JSON, YAML, or TOML configuration and merge safe defaults."""
    if config is None or isinstance(config, dict):
        return normalize_config(config)

    path = Path(config)
    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {path}")
    if not path.is_file():
        raise ValueError(f"Configuration path is not a file: {path}")

    suffix = path.suffix.lower()
    if suffix == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
    elif suffix in {".yaml", ".yml"}:
        try:
            import yaml
        except ImportError as exc:  # pragma: no cover
            raise ImportError(
                "YAML configuration requires PyYAML. Install AxiomBraid normally "
                "or run: py -m pip install PyYAML"
            ) from exc
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    elif suffix == ".toml":
        if tomllib is None:  # pragma: no cover
            try:
                import tomli as tomllib_fallback
            except ImportError as exc:
                raise ImportError(
                    "TOML configuration on Python below 3.11 requires tomli."
                ) from exc
            with path.open("rb") as file:
                payload = tomllib_fallback.load(file)
        else:
            with path.open("rb") as file:
                payload = tomllib.load(file)
    else:
        raise ValueError("Unsupported config type. Use .json, .yaml/.yml, or .toml.")

    if payload is None:
        payload = {}
    if not isinstance(payload, dict):
        raise ValueError("Configuration file must contain a mapping/object at its root.")
    return normalize_config(payload)


def _toml_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return json.dumps(value)
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        return "[" + ", ".join(_toml_value(item) for item in value) + "]"
    raise TypeError(f"Unsupported TOML value: {type(value).__name__}")


def _to_toml(config: dict[str, Any]) -> str:
    lines: list[str] = []
    for section, values in config.items():
        lines.append(f"[{section}]")
        for key, value in values.items():
            lines.append(f"{key} = {_toml_value(value)}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def export_config(
    path: str | Path,
    config: dict[str, Any] | None = None,
) -> Path:
    """Export a normalized configuration as JSON, YAML, or TOML."""
    output = Path(path)
    normalized = normalize_config(config)
    suffix = output.suffix.lower()
    if not suffix:
        output = output.with_suffix(".json")
        suffix = ".json"
    output.parent.mkdir(parents=True, exist_ok=True)

    if suffix == ".json":
        output.write_text(
            json.dumps(normalized, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    elif suffix in {".yaml", ".yml"}:
        try:
            import yaml
        except ImportError as exc:  # pragma: no cover
            raise ImportError("YAML export requires PyYAML.") from exc
        output.write_text(
            yaml.safe_dump(normalized, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )
    elif suffix == ".toml":
        output.write_text(_to_toml(normalized), encoding="utf-8")
    else:
        raise ValueError("Unsupported config type. Use .json, .yaml/.yml, or .toml.")
    return output.resolve()


class ConfigMixin:
    """Construct DataGuide objects from reusable configuration files."""

    @classmethod
    def from_config(
        cls,
        data: Any,
        config: str | Path | dict[str, Any] | None = None,
    ):
        normalized = load_config(config)
        analysis = normalized["analysis"]
        guide = cls(data, **analysis)
        guide._runtime_config = normalized
        return guide

    def runtime_config(self) -> dict[str, Any]:
        current = getattr(self, "_runtime_config", None)
        if current is None:
            current = normalize_config({"analysis": self._configuration()})
        return deepcopy(current)

    def export_runtime_config(self, path: str | Path) -> Path:
        return export_config(path, self.runtime_config())
