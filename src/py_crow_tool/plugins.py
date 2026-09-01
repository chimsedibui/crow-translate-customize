from __future__ import annotations

from dataclasses import dataclass
from importlib.metadata import entry_points
from typing import Any, Callable

from py_crow_tool.core.provider import TranslationProvider


@dataclass(frozen=True, slots=True)
class ProviderPlugin:
    id: str
    version: str
    capabilities: tuple[str, ...]
    settings_schema: dict[str, Any]
    factory: Callable[[dict[str, Any]], TranslationProvider]


def load_provider_plugins(enabled: set[str], settings: dict[str, dict[str, Any]] | None = None) -> list[TranslationProvider]:
    loaded: list[TranslationProvider] = []
    plugin_settings = settings or {}
    for entry_point in entry_points(group="py_crow_tool.providers"):
        if entry_point.name not in enabled:
            continue
        plugin = entry_point.load()
        if not isinstance(plugin, ProviderPlugin):
            raise TypeError(f"Provider entry point {entry_point.name!r} does not expose ProviderPlugin")
        loaded.append(plugin.factory(plugin_settings.get(plugin.id, {})))
    return loaded
