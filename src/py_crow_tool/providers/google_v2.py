from __future__ import annotations

import html

import httpx

from py_crow_tool.core.languages import normalize_language
from py_crow_tool.core.models import DetectedLanguage, TranslationError, TranslationException, TranslationRequest, TranslationResult

from .base import HttpProvider


class GoogleV2Provider(HttpProvider):
    id = "google-v2"
    display_name = "Google Cloud Basic v2"
    endpoint = "https://translation.googleapis.com/language/translate/v2"

    def __init__(self, api_key: str, *, client: httpx.AsyncClient | None = None):
        super().__init__(client=client)
        self.api_key = api_key.strip()

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    async def translate(self, request: TranslationRequest) -> TranslationResult:
        if not self.configured:
            raise TranslationException(TranslationError.CONFIGURATION, "Google Cloud v2 API key is not configured")

        async def operation() -> TranslationResult:
            payload = {"q": request.text, "target": normalize_language(request.target_language), "format": "text"}
            if request.source_language != "auto":
                payload["source"] = normalize_language(request.source_language)
            response = await self._request("POST", self.endpoint, params={"key": self.api_key}, json=payload)
            self._raise_for_response(response)
            try:
                item = response.json()["data"]["translations"][0]
                return TranslationResult(
                    translated_text=html.unescape(item["translatedText"]),
                    source_language=item.get("detectedSourceLanguage", request.source_language),
                    target_language=request.target_language,
                    provider_id=self.id,
                )
            except (KeyError, IndexError, TypeError, ValueError) as error:
                raise TranslationException(TranslationError.PARSING, "Unexpected Google Cloud v2 response") from error

        return await self._run(request.request_id, operation())

    async def detect_language(self, text: str) -> DetectedLanguage:
        if not self.configured:
            raise TranslationException(TranslationError.CONFIGURATION, "Google Cloud v2 API key is not configured")
        response = await self._request("POST", f"{self.endpoint}/detect", params={"key": self.api_key}, json={"q": text})
        self._raise_for_response(response)
        try:
            item = response.json()["data"]["detections"][0][0]
            return DetectedLanguage(item["language"], item.get("confidence"))
        except (KeyError, IndexError, TypeError, ValueError) as error:
            raise TranslationException(TranslationError.PARSING, "Unexpected Google Cloud v2 detection response") from error

    def supported_languages(self) -> list[str]:
        return []

