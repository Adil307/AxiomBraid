"""Built-in HTML report themes."""

from __future__ import annotations

from copy import deepcopy

HTML_THEMES = {
    "light": {
        "background": "#f5f7fa",
        "surface": "#ffffff",
        "surface_alt": "#f8fafc",
        "text": "#172033",
        "muted": "#526174",
        "border": "#dce3ed",
        "accent": "#2457d6",
    },
    "dark": {
        "background": "#0f172a",
        "surface": "#172033",
        "surface_alt": "#1e293b",
        "text": "#e5edf7",
        "muted": "#a8b6ca",
        "border": "#334155",
        "accent": "#7aa2ff",
    },
    "minimal": {
        "background": "#ffffff",
        "surface": "#ffffff",
        "surface_alt": "#ffffff",
        "text": "#111111",
        "muted": "#555555",
        "border": "#d4d4d4",
        "accent": "#111111",
    },
    "high_contrast": {
        "background": "#000000",
        "surface": "#000000",
        "surface_alt": "#111111",
        "text": "#ffffff",
        "muted": "#f0f0f0",
        "border": "#ffffff",
        "accent": "#ffff00",
    },
}


def available_themes() -> list[str]:
    return sorted(HTML_THEMES)


def get_theme(name: str) -> dict[str, str]:
    normalized = str(name).strip().lower().replace("-", "_")
    if normalized not in HTML_THEMES:
        raise ValueError(
            "Unsupported HTML theme. Use one of: " + ", ".join(available_themes())
        )
    return deepcopy(HTML_THEMES[normalized])
