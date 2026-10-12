import base64
import json

import httpx
import pytest

from py_crow_tool.core.models import TranslationError, TranslationException
from py_crow_tool.providers.google_tts import GoogleTtsProvider, choose_voice, speech_locale


def _voice(name):
    return {"name": name, "languageCodes": ["-".join(name.split("-")[:2])]}


VI_VOICES = [_voice(name) for name in (
    "vi-VN-Standard-A", "vi-VN-Wavenet-A", "vi-VN-Neural2-A", "vi-VN-Chirp3-HD-Achernar", "vi-VN-Chirp3-HD-Aoede",
)] + [{"name": "Aoede", "languageCodes": ["vi-VN"]}]


def test_speech_locale_maps_translation_codes():
    assert speech_locale("vi") == "vi"
    assert speech_locale("en") == "en-US"
    assert speech_locale("en-GB") == "en-GB"
    assert speech_locale("zh-CN") == "cmn-CN"
    assert speech_locale("zh-TW") == "cmn-TW"


def test_choose_voice_prefers_the_requested_quality():
    assert choose_voice(VI_VOICES, "vi", "chirp-hd") == ("vi-VN", "vi-VN-Chirp3-HD-Aoede")
    assert choose_voice(VI_VOICES, "vi", "neural2") == ("vi-VN", "vi-VN-Neural2-A")
    assert choose_voice(VI_VOICES, "vi", "standard") == ("vi-VN", "vi-VN-Standard-A")


def test_choose_voice_falls_back_to_the_best_available_quality():
    only_basic = [_voice("xx-YY-Standard-B"), _voice("xx-YY-Wavenet-A")]
    assert choose_voice(only_basic, "xx", "chirp-hd") == ("xx-YY", "xx-YY-Wavenet-A")


def test_choose_voice_keeps_the_default_region():
    voices = [_voice("en-AU-Neural2-A"), _voice("en-US-Neural2-C")]
    assert choose_voice(voices, "en-US", "neural2") == ("en-US", "en-US-Neural2-C")


def test_choose_voice_without_voices_lets_google_choose():
    assert choose_voice([], "vi-VN", "chirp-hd") == ("vi-VN", None)


def _provider(handler, key="key"):
    return GoogleTtsProvider(key, client=httpx.AsyncClient(transport=httpx.MockTransport(handler)))


async def test_synthesize_picks_a_voice_and_decodes_audio():
    calls = []

    async def handler(request: httpx.Request):
        calls.append(request)
        if request.url.path.endswith("/voices"):
            return httpx.Response(200, json={"voices": VI_VOICES})
        return httpx.Response(200, json={"audioContent": base64.b64encode(b"mp3 bytes").decode()})

    provider = _provider(handler)
    assert await provider.synthesize("Xin chào", "vi", "chirp-hd") == b"mp3 bytes"
    assert await provider.synthesize("Tạm biệt", "vi", "chirp-hd") == b"mp3 bytes"
    # The voice list is fetched once per locale, not in front of every sentence.
    assert [request.url.path for request in calls] == ["/v1/voices", "/v1/text:synthesize", "/v1/text:synthesize"]
    body = json.loads(calls[1].content)
    assert body["voice"] == {"languageCode": "vi-VN", "name": "vi-VN-Chirp3-HD-Aoede"}
    assert body["input"] == {"text": "Xin chào"}
    assert calls[1].url.params["key"] == "key"
    await provider.close()


async def test_synthesize_reports_a_disabled_api():
    async def handler(request: httpx.Request):
        return httpx.Response(403, json={"error": {"message": "Cloud Text-to-Speech API has not been used in project 1"}})

    provider = _provider(handler)
    with pytest.raises(TranslationException) as error:
        await provider.synthesize("Xin chào", "vi")
    assert error.value.kind == TranslationError.AUTHENTICATION
    assert "Text-to-Speech API" in str(error.value)
    await provider.close()


@pytest.mark.parametrize("key, text, language, kind", [
    ("", "Xin chào", "vi", TranslationError.CONFIGURATION),
    ("key", "Xin chào", "auto", TranslationError.INVALID_REQUEST),
    ("key", "Xin chào", "", TranslationError.INVALID_REQUEST),
    ("key", "â" * 3000, "vi", TranslationError.INVALID_REQUEST),
])
async def test_synthesize_refuses_what_it_cannot_send(key, text, language, kind):
    async def handler(request: httpx.Request):
        raise AssertionError("no request should be sent")

    provider = _provider(handler, key)
    with pytest.raises(TranslationException) as error:
        await provider.synthesize(text, language)
    assert error.value.kind == kind
    await provider.close()
