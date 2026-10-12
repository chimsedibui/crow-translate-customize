from __future__ import annotations

import base64
import binascii

import httpx

from py_crow_tool.core.models import TranslationError, TranslationException

from .base import HttpProvider

# The voice qualities offered in Settings, best first. A setting names one of these;
# the name families are how Google labels them inside a voice name such as
# "vi-VN-Chirp3-HD-Aoede" or "en-US-Neural2-C".
VOICE_TYPES = ("chirp-hd", "neural2", "wavenet", "standard")
_FAMILIES = {
    "chirp-hd": ("Chirp3", "Chirp"),
    "neural2": ("Neural2",),
    "wavenet": ("Wavenet",),
    "standard": ("Standard",),
}
# Chirp voices are named after stars rather than lettered, so "the first one" is an
# accident of the alphabet. This one is the voice that was auditioned and kept.
_PREFERRED_CHIRP_VOICE = "Aoede"

# Translation codes name a language; speech needs a locale. Where a language is spoken
# in several, pick the one most readers would expect rather than the alphabetically first.
_DEFAULT_LOCALES = {"en": "en-US", "es": "es-ES", "fr": "fr-FR", "pt": "pt-BR", "de": "de-DE", "ar": "ar-XA"}
# Google's speech service files Mandarin under cmn, not the zh the translator uses.
_SPEECH_LANGUAGES = {"zh": "cmn-CN", "zh-cn": "cmn-CN", "zh-tw": "cmn-TW"}

# Google refuses a synthesis request whose text is over 5000 bytes.
MAX_TEXT_BYTES = 5000


def speech_locale(language: str) -> str:
    """The locale to ask the voice list for: a regional code is kept as given, a bare
    language gets its usual region, and Chinese is renamed to what the API calls it."""
    code = language.strip()
    return _SPEECH_LANGUAGES.get(code.lower()) or _DEFAULT_LOCALES.get(code.lower(), code)


def _family(name: str) -> str | None:
    # "vi-VN-Chirp3-HD-Aoede" -> "Chirp3". Names without the locale prefix are voices
    # that need a separate model parameter, which this client does not send.
    parts = name.split("-")
    return parts[2] if len(parts) >= 4 else None


def choose_voice(voices: list[dict], locale: str, voice_type: str) -> tuple[str, str | None]:
    """Pick (language code, voice name) for a locale at the requested quality.

    A language without that quality gets the best one it does have rather than an
    error: a Settings choice of "Chirp HD" should not make a language that only has
    Standard voices go silent. With no usable voice at all the name is None, which
    lets Google choose its own default for the language code.
    """
    order = list(VOICE_TYPES)
    if voice_type in order:
        order.remove(voice_type)
        order.insert(0, voice_type)
    locales = [code for voice in voices for code in voice.get("languageCodes", [])]
    target = locale if locale in locales else (sorted(locales)[0] if locales else locale)
    candidates = [voice["name"] for voice in voices if target in voice.get("languageCodes", []) and _family(voice["name"])]
    for kind in order:
        names = sorted(name for name in candidates if _family(name) in _FAMILIES[kind])
        if names:
            preferred = [name for name in names if name.endswith("-" + _PREFERRED_CHIRP_VOICE)]
            return target, (preferred or names)[0]
    return target, None


class GoogleTtsProvider(HttpProvider):
    display_name = "Google Cloud Text-to-Speech"
    endpoint = "https://texttospeech.googleapis.com/v1"

    def __init__(self, api_key: str = "", *, client: httpx.AsyncClient | None = None):
        super().__init__(client=client)
        self.api_key = api_key.strip()
        # The voice list for a locale does not change while the app runs, and fetching
        # it again would put a second round trip in front of every sentence.
        self._voices: dict[str, list[dict]] = {}

    async def _voices_for(self, locale: str) -> list[dict]:
        if locale not in self._voices:
            response = await self._request("GET", f"{self.endpoint}/voices", params={"key": self.api_key, "languageCode": locale})
            self._raise_for_response(response)
            try:
                self._voices[locale] = list(response.json().get("voices", []))
            except (ValueError, AttributeError) as error:
                raise TranslationException(TranslationError.PARSING, "Unexpected Google Text-to-Speech voice list") from error
        return self._voices[locale]

    async def synthesize(self, text: str, language: str, voice_type: str = "chirp-hd", *, request_id: str = "") -> bytes:
        """MP3 audio of text read in language."""
        if not self.api_key:
            raise TranslationException(TranslationError.CONFIGURATION, "Add a Google Cloud API key in Settings to read text aloud")
        if not language or language == "auto":
            raise TranslationException(TranslationError.INVALID_REQUEST, "The language is not known yet. Translate the text first, then read it aloud")
        if len(text.encode("utf-8")) > MAX_TEXT_BYTES:
            raise TranslationException(TranslationError.INVALID_REQUEST, "This text is too long to read aloud in one go")

        async def operation() -> bytes:
            locale = speech_locale(language)
            language_code, name = choose_voice(await self._voices_for(locale), locale, voice_type)
            voice = {"languageCode": language_code}
            if name:
                voice["name"] = name
            payload = {"input": {"text": text}, "voice": voice, "audioConfig": {"audioEncoding": "MP3"}}
            response = await self._request("POST", f"{self.endpoint}/text:synthesize", params={"key": self.api_key}, json=payload)
            self._raise_for_response(response)
            try:
                return base64.b64decode(response.json()["audioContent"])
            except (KeyError, TypeError, ValueError, binascii.Error) as error:
                raise TranslationException(TranslationError.PARSING, "Unexpected Google Text-to-Speech response") from error

        return await self._run(request_id, operation())
