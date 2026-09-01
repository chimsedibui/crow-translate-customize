from __future__ import annotations

import asyncio
from pathlib import Path

import httpx
from google.auth import default as default_credentials
from google.auth.credentials import Credentials
from google.auth.transport.requests import Request as AuthRequest
from google.oauth2 import service_account

from py_crow_tool.core.languages import normalize_language
from py_crow_tool.core.models import DetectedLanguage, TranslationError, TranslationException, TranslationRequest, TranslationResult

from .base import HttpProvider

SCOPES = ["https://www.googleapis.com/auth/cloud-translation"]


class GoogleV3Provider(HttpProvider):
    id = "google-v3"
    display_name = "Google Cloud Advanced v3"

    def __init__(self, project_id: str, location: str = "global", credentials_file: str = "", *, client: httpx.AsyncClient | None = None):
        super().__init__(client=client)
        self.project_id = project_id.strip()
        self.location = location.strip() or "global"
        self.credentials_file = credentials_file.strip()
        self._credentials: Credentials | None = None

    @property
    def configured(self) -> bool:
        if not self.project_id:
            return False
        return not self.credentials_file or Path(self.credentials_file).is_file()

    @property
    def parent(self) -> str:
        return f"projects/{self.project_id}/locations/{self.location}"

    async def _authorization(self) -> str:
        try:
            if self._credentials is None:
                if self.credentials_file:
                    self._credentials = service_account.Credentials.from_service_account_file(self.credentials_file, scopes=SCOPES)
                else:
                    self._credentials, discovered_project = await asyncio.to_thread(default_credentials, scopes=SCOPES)
                    if not self.project_id and discovered_project:
                        self.project_id = discovered_project
            if not self._credentials.valid:
                await asyncio.to_thread(self._credentials.refresh, AuthRequest())
            return f"Bearer {self._credentials.token}"
        except Exception as error:
            raise TranslationException(TranslationError.AUTHENTICATION, f"Unable to initialize Google v3 credentials: {error}") from error

    async def translate(self, request: TranslationRequest) -> TranslationResult:
        if not self.configured:
            raise TranslationException(TranslationError.CONFIGURATION, "Google Cloud v3 project or credentials are not configured")

        async def operation() -> TranslationResult:
            payload = {
                "contents": [request.text],
                "targetLanguageCode": normalize_language(request.target_language),
                "mimeType": "text/plain",
            }
            if request.source_language != "auto":
                payload["sourceLanguageCode"] = normalize_language(request.source_language)
            response = await self._request(
                "POST",
                f"https://translation.googleapis.com/v3/{self.parent}:translateText",
                headers={"Authorization": await self._authorization()},
                json=payload,
            )
            self._raise_for_response(response)
            try:
                item = response.json()["translations"][0]
                return TranslationResult(
                    translated_text=item["translatedText"],
                    source_language=item.get("detectedLanguageCode", request.source_language),
                    target_language=request.target_language,
                    provider_id=self.id,
                    metadata={"model": item.get("model", "")},
                )
            except (KeyError, IndexError, TypeError, ValueError) as error:
                raise TranslationException(TranslationError.PARSING, "Unexpected Google Cloud v3 response") from error

        return await self._run(request.request_id, operation())

    async def detect_language(self, text: str) -> DetectedLanguage:
        if not self.configured:
            raise TranslationException(TranslationError.CONFIGURATION, "Google Cloud v3 project or credentials are not configured")
        response = await self._request(
            "POST",
            f"https://translation.googleapis.com/v3/{self.parent}:detectLanguage",
            headers={"Authorization": await self._authorization()},
            json={"content": text, "mimeType": "text/plain"},
        )
        self._raise_for_response(response)
        try:
            item = response.json()["languages"][0]
            return DetectedLanguage(item["languageCode"], item.get("confidence"))
        except (KeyError, IndexError, TypeError, ValueError) as error:
            raise TranslationException(TranslationError.PARSING, "Unexpected Google Cloud v3 detection response") from error

    def supported_languages(self) -> list[str]:
        return []

