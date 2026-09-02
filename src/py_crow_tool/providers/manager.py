from __future__ import annotations

import asyncio

from py_crow_tool.core.models import DetectedLanguage, TranslationError, TranslationException, TranslationRequest, TranslationResult
from py_crow_tool.core.provider import TranslationProvider


class ProviderManager:
    def __init__(self, providers: list[TranslationProvider]):
        self.providers = {provider.id: provider for provider in providers}

    @property
    def active_provider(self) -> TranslationProvider:
        for provider_id in ("google-v3", "google-v2"):
            provider = self.providers.get(provider_id)
            if provider and provider.configured:
                return provider
        for provider in self.providers.values():
            if provider.configured:
                return provider
        raise TranslationException(TranslationError.CONFIGURATION, "No translation provider is configured")

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

    def replace(self, providers: list[TranslationProvider]) -> list[TranslationProvider]:
        old_providers = list(self.providers.values())
        self.providers = {provider.id: provider for provider in providers}
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
