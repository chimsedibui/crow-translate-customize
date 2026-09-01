from __future__ import annotations

from typing import Protocol, runtime_checkable

from .models import DetectedLanguage, TranslationRequest, TranslationResult


@runtime_checkable
class TranslationProvider(Protocol):
    id: str
    display_name: str

    @property
    def configured(self) -> bool: ...

    async def translate(self, request: TranslationRequest) -> TranslationResult: ...

    async def detect_language(self, text: str) -> DetectedLanguage: ...

    def supported_languages(self) -> list[str]: ...

    def cancel(self, request_id: str) -> None: ...

