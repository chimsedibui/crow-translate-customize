from __future__ import annotations

import json
import re

import httpx

from py_crow_tool.core.models import TranslationError, TranslationException
from py_crow_tool.core.refine_models import DEFAULT_REFINE_TONE, RefineOption, RefineRequest, RefineResult

from .azure_openai import AzureOpenAiProvider
from .base import HttpProvider

_TONES = {
    "friendly": (
        "polite and friendly, the way you would message a client you work with regularly on "
        "Slack or Teams: clear, warm and natural, never stiff"
    ),
    "formal": "formal and professional, suitable for an email to a new client or an official report",
    "concise": "as short and direct as possible while keeping every point, suited to a quick status update",
    "keep": (
        "the writer's own tone and register; only fix grammar and word choice and put the ideas "
        "in a sensible order"
    ),
}

# The draft is the writer's thinking, not a text to be rendered faithfully: the point of
# this feature is that a word-for-word translation of muddled Vietnamese is muddled
# English. So the model is allowed to reorder and regroup, and the guard rails are all
# on content -- a rewrite that invents a promise to a client is worse than a clumsy one.
_SYSTEM = (
    "You help a Vietnamese software engineer write messages to English-speaking clients. "
    "The user's message is a draft. It may be in Vietnamese, in rough English, or a mix of "
    "both, and its ideas may be out of order. Rewrite it as a message in natural, fluent "
    "English that the writer can send as it is.\n"
    "- Keep every fact, number, name, date, link, code identifier and commitment exactly. "
    "Never add promises, details, apologies or questions the draft does not contain.\n"
    "- Reorder and group the ideas so they read logically. Use short paragraphs, or a list "
    "where the draft enumerates things.\n"
    "- Do not translate word for word.\n"
    "- Do not add a greeting or a sign-off unless the draft has one.\n"
    "- Tone: {tone}.\n"
    "Give two or three alternative versions that differ in a way that matters (for example "
    "one shorter and one more complete), each with a label of one to three English words. "
    "Then give up to four short notes, written in Vietnamese, on the main changes you made "
    "and why, so the writer can learn from them.\n"
    'Reply with JSON only, in the form {{"options": [{{"label": "...", "text": "..."}}], '
    '"notes": ["..."]}}.'
)


def build_system_prompt(tone: str) -> str:
    return _SYSTEM.format(tone=_TONES.get(tone, _TONES[DEFAULT_REFINE_TONE]))


def _clean(text: str) -> str:
    # Same markdown hard-break cleanup as the translator: trailing spaces per line would
    # otherwise ride along into whatever the user pastes the message into.
    return "\n".join(line.rstrip() for line in text.strip().splitlines())


def parse_refine_reply(reply: str, provider_id: str) -> RefineResult:
    """Read the model's JSON into a result, tolerating the usual wrapping.

    json_object mode makes a fence unlikely but not impossible across deployments, so the
    outermost object is extracted rather than the whole reply parsed.
    """
    match = re.search(r"\{.*\}", reply, re.DOTALL)
    try:
        parsed = json.loads(match.group(0) if match else reply)
    except (ValueError, TypeError) as error:
        raise TranslationException(TranslationError.PARSING, "The refine reply was not valid JSON") from error
    if not isinstance(parsed, dict):
        raise TranslationException(TranslationError.PARSING, "The refine reply was not a JSON object")
    options: list[RefineOption] = []
    for index, item in enumerate(parsed.get("options") or []):
        if isinstance(item, str):
            label, text = "", item
        elif isinstance(item, dict):
            label, text = str(item.get("label") or ""), str(item.get("text") or "")
        else:
            continue
        text = _clean(text)
        if text:
            options.append(RefineOption(label.strip() or f"Option {index + 1}", text))
    if not options:
        raise TranslationException(TranslationError.PARSING, "The refine reply contained no rewritten text")
    notes = tuple(str(note).strip() for note in (parsed.get("notes") or []) if str(note).strip())
    return RefineResult(options=tuple(options[:3]), notes=notes[:4], provider_id=provider_id)


class ChatRefiner(HttpProvider):
    """One chat-completions endpoint asked to rewrite a draft.

    The Azure and OpenAI variants differ only in where the request goes, how it is
    authenticated and how the model is named, which are the overridden seams below.
    """

    id = "refiner"
    display_name = "Refiner"

    def __init__(self, *, client: httpx.AsyncClient | None = None):
        # Three versions plus notes is a longer reply than a translation, and a reasoning
        # deployment thinks before it writes; the default 20s cut it off in testing.
        super().__init__(client=client, timeout=60.0)

    @property
    def configured(self) -> bool:
        raise NotImplementedError

    def _url(self) -> str:
        raise NotImplementedError

    def _params(self) -> dict[str, str] | None:
        return None

    def _headers(self) -> dict[str, str]:
        raise NotImplementedError

    def _model_fields(self) -> dict[str, object]:
        return {}

    async def refine(self, request: RefineRequest) -> RefineResult:
        if not self.configured:
            raise TranslationException(TranslationError.CONFIGURATION, f"{self.display_name} is not configured")

        async def operation() -> RefineResult:
            # No temperature: the reasoning models (gpt-5, o-series) reject anything but
            # their default, the deployment behind an Azure name could be either kind, and
            # for producing distinct alternatives the default is the right setting anyway.
            payload: dict[str, object] = {
                **self._model_fields(),
                "messages": [
                    {"role": "system", "content": build_system_prompt(request.tone)},
                    {"role": "user", "content": request.text},
                ],
                "response_format": {"type": "json_object"},
            }
            response = await self._request(
                "POST", self._url(), params=self._params(), headers=self._headers(), json=payload
            )
            self._raise_for_response(response)
            try:
                content = response.json()["choices"][0]["message"]["content"]
            except (KeyError, IndexError, TypeError, ValueError) as error:
                raise TranslationException(TranslationError.PARSING, f"Unexpected {self.display_name} response") from error
            if not content:
                raise TranslationException(TranslationError.PARSING, f"{self.display_name} returned an empty response")
            return parse_refine_reply(content, self.id)

        return await self._run(request.request_id, operation())


class AzureOpenAiRefiner(ChatRefiner):
    id = "azure-openai"
    display_name = "Azure OpenAI"

    def __init__(
        self,
        api_key: str,
        *,
        endpoint: str = "",
        deployment: str = "",
        api_version: str = "2025-01-01-preview",
        client: httpx.AsyncClient | None = None,
    ):
        super().__init__(client=client)
        self.configure(api_key, endpoint=endpoint, deployment=deployment, api_version=api_version)

    def configure(self, api_key: str, *, endpoint: str, deployment: str, api_version: str) -> None:
        self.api_key = api_key.strip()
        self.endpoint = AzureOpenAiProvider._normalize_endpoint(endpoint)
        self.deployment = deployment.strip()
        self.api_version = api_version.strip() or "2025-01-01-preview"

    @property
    def configured(self) -> bool:
        return bool(self.api_key and self.endpoint and self.deployment)

    def _url(self) -> str:
        return f"{self.endpoint}/openai/deployments/{self.deployment}/chat/completions"

    def _params(self) -> dict[str, str]:
        return {"api-version": self.api_version}

    def _headers(self) -> dict[str, str]:
        return {"api-key": self.api_key}


class OpenAiRefiner(ChatRefiner):
    id = "openai"
    display_name = "OpenAI"
    endpoint = "https://api.openai.com/v1/chat/completions"

    def __init__(self, api_key: str, *, model: str = "gpt-5-mini", client: httpx.AsyncClient | None = None):
        super().__init__(client=client)
        self.api_key = api_key.strip()
        self.model = model

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    def _url(self) -> str:
        return self.endpoint

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}"}

    def _model_fields(self) -> dict[str, object]:
        fields: dict[str, object] = {"model": self.model}
        # A rewrite is not a puzzle: at the default effort gpt-5 spends many seconds of
        # hidden reasoning for no better English. "low" keeps it to a moment.
        if self.model.startswith("gpt-5"):
            fields["reasoning_effort"] = "low"
        return fields
