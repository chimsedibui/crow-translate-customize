from __future__ import annotations

from py_crow_tool.config import SettingsStore
from py_crow_tool.plugins import load_provider_plugins
from py_crow_tool.providers import GoogleV2Provider, GoogleV3Provider, ProviderManager


def build_services(store: SettingsStore | None = None):
    settings_store = store or SettingsStore()
    settings = settings_store.load()
    providers = [
        GoogleV3Provider(settings.v3_project_id, settings.google_v3.location, settings.v3_credentials_file),
        GoogleV2Provider(settings.v2_api_key),
    ]
    providers.extend(load_provider_plugins(set(settings.enabled_plugins)))
    return settings_store, settings, ProviderManager(providers)

