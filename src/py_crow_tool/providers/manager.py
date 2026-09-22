from __future__ import annotations

import asyncio

from py_crow_tool.core.models import DetectedLanguage, TranslationError, TranslationException, TranslationRequest, TranslationResult
from py_crow_tool.core.provider import TranslationProvider


class ProviderManager:
    def __init__(self, providers: list[TranslationProvider], *, preferred: str = ""):
        self.providers = {provider.id: provider for provider in providers}
        self.preferred = preferred

    @property
    def active_provider(self) -> TranslationProvider:
        # The user's choice first, then the historical default, then whatever is left.
        # A preference that names an unconfigured provider falls through rather than
        # failing: the setting outlives the credential it was chosen with, and refusing
        # to translate because of a stale preference would be worse than quietly using
        # the provider that still works.
        for candidate in (self.preferred, "google-v2"):
            provider = self.providers.get(candidate) if candidate else None
            if provider and provider.configured:
                return provider
        for provider in self.providers.values():
            if provider.configured:
                return provider
        raise TranslationException(TranslationError.CONFIGURATION, "No translation provider is configured")

    def configured_providers(self) -> list[TranslationProvider]:
        return [provider for provider in self.providers.values() if provider.configured]

    def get(self, provider_id: str | None) -> TranslationProvider:
        if not provider_id:
            return self.active_provider
        try:
            provider = self.providers[provider_id]
        except KeyError as error:
            raise TranslationException(TranslationError.CONFIGURATION, f"Unknown provider: {provider_id}") from error
        if not provider.configured:
            raise TranslationException(TranslationError.CONFIGURATION, f"Provider is not configured: {provider_id}")
        return provider

    async def translate(self, request: TranslationRequest) -> TranslationResult:
        return await self.get(request.provider_id).translate(request)

    async def detect_language(self, text: str, provider_id: str | None = None) -> DetectedLanguage:
        return await self.get(provider_id).detect_language(text)

    def cancel(self, request_id: str) -> None:
        for provider in self.providers.values():
            provider.cancel(request_id)

    async def close(self) -> None:
        for provider in self.providers.values():
            close = getattr(provider, "close", None)
            if close:
                await close()

    def replace(self, providers: list[TranslationProvider], *, preferred: str | None = None) -> list[TranslationProvider]:
        old_providers = list(self.providers.values())
        self.providers = {provider.id: provider for provider in providers}
        if preferred is not None:
            self.preferred = preferred
        return old_providers

    @staticmethod
    async def close_providers(providers: list[TranslationProvider]) -> None:
        for provider in providers:
            pending = getattr(provider, "pending_tasks", None)
            if pending:
                tasks = pending()
                if tasks:
                    await asyncio.gather(*tasks, return_exceptions=True)
            close = getattr(provider, "close", None)
            if close:
                await close()
