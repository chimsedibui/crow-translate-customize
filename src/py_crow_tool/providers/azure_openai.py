from __future__ import annotations

import json
import re

import httpx

from py_crow_tool.core.languages import language_display_name, normalize_language
from py_crow_tool.core.models import DetectedLanguage, TranslationError, TranslationException, TranslationRequest, TranslationResult

from .base import HttpProvider

# The model is told to answer with the translation and nothing else, because the result
# goes straight into the translation pane -- a "Sure, here is the translation:" preamble
# would be copied along with it. Asking for JSON instead would cost a second round of
# escaping for no gain: the payload is one string.
_TRANSLATE_SYSTEM = (
    "You are a translation engine. Translate the user's message into {target}. "
    "Reply with the translation only: no preamble, no quotes around it, no notes, no "
    "explanation, and no commentary on the request. Preserve the original line breaks, "
    "capitalisation style and any markup or placeholders such as {{name}} or %s exactly "
    "as they appear. If the message is already in {target}, repeat it unchanged."
)
_TRANSLATE_SYSTEM_FROM = " The message is written in {source}."

# Detection returns JSON because two values have to come back, and a confidence read off
# prose ("I am fairly sure this is French") is not a number.
_DETECT_SYSTEM = (
    'Identify the language of the user\'s message. Reply with JSON only, in the form '
    '{"language": "<ISO 639-1 code>", "confidence": <number between 0 and 1>}. '
    "Use the bare two-letter code where one exists. Add nothing else."
)


class AzureOpenAiProvider(HttpProvider):
    """Translate through a chat model deployed on Azure OpenAI.

    Azure puts the model behind a per-deployment URL on the customer's own resource
    rather than a shared endpoint, so the deployment name and the API version are part
    of the address and all three pieces have to be configured together.
    """

    id = "azure-openai"
    display_name = "Azure OpenAI"

    def __init__(
        self,
        api_key: str,
        *,
        endpoint: str = "",
        deployment: str = "",
        api_version: str = "2025-01-01-preview",
        temperature: float | None = 0.0,
        client: httpx.AsyncClient | None = None,
    ):
        super().__init__(client=client)
        self.api_key = api_key.strip()
        self.endpoint = self._normalize_endpoint(endpoint)
        self.deployment = deployment.strip()
        self.api_version = api_version.strip() or "2025-01-01-preview"
        self.temperature = temperature

    @staticmethod
    def _normalize_endpoint(endpoint: str) -> str:
        """Reduce whatever the Azure portal handed the user to the resource root.

        The portal shows several addresses for one resource -- the bare host, the same
        host with `/openai`, and the OpenAI-compatible `/openai/v1` -- and people paste
        whichever one they were looking at. They all describe the same resource, so the
        suffix is trimmed here rather than turned into a configuration error.
        """
        value = endpoint.strip().rstrip("/")
        if not value:
            return ""
        if not value.startswith(("http://", "https://")):
            value = "https://" + value
        return re.sub(r"/openai(/v1)?$", "", value)

    @property
    def configured(self) -> bool:
        return bool(self.api_key and self.endpoint and self.deployment)

    def _chat_url(self) -> str:
        return f"{self.endpoint}/openai/deployments/{self.deployment}/chat/completions"

    def _require_configuration(self) -> None:
        if self.configured:
            return
        missing = [
            name
            for name, value in (("endpoint", self.endpoint), ("deployment", self.deployment), ("API key", self.api_key))
            if not value
        ]
        raise TranslationException(
            TranslationError.CONFIGURATION,
            "Azure OpenAI is missing its " + ", ".join(missing),
        )

    async def _chat(self, system: str, user: str, *, max_tokens: int | None = None) -> str:
        payload: dict[str, object] = {
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        }
        # Reasoning deployments (o-series, gpt-5) reject any temperature but their default,
        # and bill hidden thinking tokens for what is a single-shot rewrite either way.
        if self.temperature is not None:
            payload["temperature"] = self.temperature
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        response = await self._request(
            "POST",
            self._chat_url(),
            params={"api-version": self.api_version},
            headers={"api-key": self.api_key},
            json=payload,
        )
        self._raise_for_response(response)
        try:
            content = response.json()["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError, ValueError) as error:
            raise TranslationException(TranslationError.PARSING, "Unexpected Azure OpenAI response") from error
        if content is None:
            raise TranslationException(TranslationError.PARSING, "Azure OpenAI returned an empty response")
        # Trailing spaces per line, not just at the ends: asked to preserve line breaks,
        # the model reaches for the markdown hard-break ("two spaces, newline"), which
        # would otherwise travel into the translation pane and out through Copy.
        return "\n".join(line.rstrip() for line in content.strip().splitlines())

    async def translate(self, request: TranslationRequest) -> TranslationResult:
        self._require_configuration()

        async def operation() -> TranslationResult:
            target = normalize_language(request.target_language)
            system = _TRANSLATE_SYSTEM.format(target=language_display_name(target))
            source = normalize_language(request.source_language) if request.source_language != "auto" else "auto"
            if source != "auto":
                system += _TRANSLATE_SYSTEM_FROM.format(source=language_display_name(source))
            translated = await self._chat(system, request.text)
            return TranslationResult(
                translated_text=translated,
                # The chat endpoint does not report what it detected. Claiming "auto" back
                # would leave the UI showing "Auto-detect -> Vietnamese" after a successful
                # translation, so an auto request runs detection as a separate call.
                source_language=source if source != "auto" else (await self.detect_language(request.text)).language,
                target_language=request.target_language,
                provider_id=self.id,
                metadata={"deployment": self.deployment},
            )

        return await self._run(request.request_id, operation())

    async def detect_language(self, text: str) -> DetectedLanguage:
        self._require_configuration()
        reply = await self._chat(_DETECT_SYSTEM, text, max_tokens=40)
        # Models wrap JSON in a ```json fence often enough that stripping it is cheaper
        # than a retry, and a bare code ("fr") is a good enough answer to accept as well.
        fenced = re.search(r"\{.*\}", reply, re.DOTALL)
        if fenced:
            try:
                parsed = json.loads(fenced.group(0))
                language = normalize_language(str(parsed.get("language", "")).strip())
                confidence = parsed.get("confidence")
                return DetectedLanguage(language, float(confidence) if isinstance(confidence, (int, float)) else None)
            except (ValueError, TypeError):
                pass
        candidate = re.fullmatch(r"[A-Za-z]{2,3}(-[A-Za-z0-9]{2,8})?", reply)
        if candidate:
            return DetectedLanguage(normalize_language(reply), None)
        raise TranslationException(TranslationError.PARSING, "Azure OpenAI returned an unreadable detection result")

    def supported_languages(self) -> list[str]:
        # A chat model will attempt any language it was trained on, so there is no list to
        # report; the UI falls back to its own, as it does for Google.
        return []
