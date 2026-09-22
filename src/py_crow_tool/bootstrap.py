from __future__ import annotations

from py_crow_tool.config import AppSettings, SettingsStore
from py_crow_tool.core.provider import TranslationProvider
from py_crow_tool.plugins import load_provider_plugins
from py_crow_tool.providers import AzureOpenAiProvider, GoogleV2Provider, ProviderManager


def build_providers(settings: AppSettings) -> list[TranslationProvider]:
    """Every provider the current settings describe, built from scratch.

    Shared with the settings save path rather than inlined at startup: rebuilding only
    the built-in providers there used to drop every plugin-supplied one the first time
    the user pressed Save.
    """
    providers: list[TranslationProvider] = [
        GoogleV2Provider(settings.v2_api_key),
        AzureOpenAiProvider(
            settings.azure_openai_api_key,
            endpoint=settings.azure_openai_endpoint,
            deployment=settings.azure_openai_deployment,
            api_version=settings.azure_openai_api_version,
        ),
    ]
    providers.extend(load_provider_plugins(set(settings.enabled_plugins)))
    return providers


def build_services(store: SettingsStore | None = None):
    settings_store = store or SettingsStore()
    settings = settings_store.load()
    manager = ProviderManager(build_providers(settings), preferred=settings.preferred_provider)
    return settings_store, settings, manager
