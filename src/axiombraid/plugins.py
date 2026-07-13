"""Safe, instance-level plugin hooks for AxiomBraid."""

from __future__ import annotations

import inspect as python_inspect
import json
from copy import deepcopy
from typing import Any, Callable

import pandas as pd

PluginCallable = Callable[..., Any]


class PluginMixin:
    """Register custom read-only checks without changing the core package."""

    def register_plugin(
        self,
        name: str,
        plugin: PluginCallable,
        *,
        replace: bool = False,
    ) -> None:
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Plugin name must be a non-empty string.")
        if not callable(plugin):
            raise TypeError("Plugin must be callable.")
        normalized = name.strip()
        if normalized in self._plugins and not replace:
            raise ValueError(
                f"Plugin '{normalized}' is already registered. Use replace=True."
            )
        self._plugins[normalized] = plugin

    def unregister_plugin(self, name: str) -> bool:
        return self._plugins.pop(name, None) is not None

    def list_plugins(self) -> list[str]:
        return sorted(self._plugins)

    @staticmethod
    def _invoke_plugin(
        plugin: PluginCallable,
        dataframe: pd.DataFrame,
        context: dict[str, Any],
    ) -> Any:
        signature = python_inspect.signature(plugin)
        positional = [
            parameter
            for parameter in signature.parameters.values()
            if parameter.kind
            in {
                parameter.POSITIONAL_ONLY,
                parameter.POSITIONAL_OR_KEYWORD,
            }
        ]
        has_varargs = any(
            parameter.kind == parameter.VAR_POSITIONAL
            for parameter in signature.parameters.values()
        )
        if has_varargs or len(positional) >= 2:
            return plugin(dataframe, context)
        if len(positional) == 1:
            return plugin(dataframe)
        return plugin()

    def run_plugins(
        self,
        *,
        context: dict[str, Any] | None = None,
        strict: bool = False,
    ) -> dict[str, dict[str, Any]]:
        """Run plugins on a deep copy; plugin failures are isolated by default."""
        results: dict[str, dict[str, Any]] = {}
        safe_context = deepcopy(context or {})
        for name in self.list_plugins():
            plugin = self._plugins[name]
            try:
                value = self._invoke_plugin(
                    plugin,
                    self.dataframe.copy(deep=True),
                    deepcopy(safe_context),
                )
                json.dumps(value, default=str)
                results[name] = {"status": "success", "result": value}
            except Exception as exc:
                if strict:
                    raise RuntimeError(f"Plugin '{name}' failed: {exc}") from exc
                results[name] = {
                    "status": "error",
                    "error_type": type(exc).__name__,
                    "message": str(exc),
                }
        return results
