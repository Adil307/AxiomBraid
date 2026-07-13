"""Privacy-conscious, fingerprint-based inspection cache."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd

CACHE_FORMAT_VERSION = 2


def _stable_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _data_digest(data: Any) -> str:
    if isinstance(data, (str, Path)):
        path = Path(data)
        if not path.exists() or not path.is_file():
            raise FileNotFoundError(f"Dataset not found: {path}")
        digest = hashlib.sha256()
        with path.open("rb") as file:
            for block in iter(lambda: file.read(1024 * 1024), b""):
                digest.update(block)
        return digest.hexdigest()
    if isinstance(data, pd.DataFrame):
        digest = hashlib.sha256()
        digest.update(_stable_json([str(c) for c in data.columns]).encode())
        digest.update(_stable_json([str(d) for d in data.dtypes]).encode())
        hashed = pd.util.hash_pandas_object(data, index=True).values.tobytes()
        digest.update(hashed)
        return digest.hexdigest()
    raise TypeError("Cache supports a dataset path or pandas DataFrame.")


class InspectionCache:
    """Store structured inspection results by content and configuration hash."""

    def __init__(self, directory: str | Path = ".axiombraid_cache") -> None:
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)

    def key(self, data: Any, *, language: str, config: Any) -> str:
        payload = {
            "format": CACHE_FORMAT_VERSION,
            "library": "axiombraid",
            "version": "1.0.0",
            "data_digest": _data_digest(data),
            "language": language,
            "config": config,
        }
        return hashlib.sha256(_stable_json(payload).encode()).hexdigest()

    def path_for(self, key: str) -> Path:
        return self.directory / f"{key}.json"

    def get(self, key: str) -> dict[str, Any] | None:
        path = self.path_for(key)
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        if payload.get("cache_format") != CACHE_FORMAT_VERSION:
            return None
        return payload.get("result")

    def set(self, key: str, result: dict[str, Any]) -> Path:
        output = self.path_for(key)
        temporary = output.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(
                {"cache_format": CACHE_FORMAT_VERSION, "result": result},
                indent=2,
                ensure_ascii=False,
                default=str,
            ),
            encoding="utf-8",
        )
        temporary.replace(output)
        return output.resolve()

    def clear(self) -> int:
        removed = 0
        for path in self.directory.glob("*.json"):
            path.unlink(missing_ok=True)
            removed += 1
        return removed


def cached_inspect(
    data: Any,
    *,
    cache_dir: str | Path = ".axiombraid_cache",
    language: str = "en",
    config: Any = None,
    refresh: bool = False,
) -> dict[str, Any]:
    """Return an inspection result plus cache-hit metadata."""
    from .config import load_config
    from .inspector import DataGuide

    normalized = load_config(config)
    cache = InspectionCache(cache_dir)
    key = cache.key(data, language=language, config=normalized)
    if not refresh:
        existing = cache.get(key)
        if existing is not None:
            return {"cache_hit": True, "cache_key": key, "result": existing}
    result = DataGuide.from_config(data, normalized).inspect(language)
    path = cache.set(key, result)
    return {
        "cache_hit": False,
        "cache_key": key,
        "cache_path": str(path),
        "result": result,
    }
