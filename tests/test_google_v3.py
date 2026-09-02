import httpx
import pytest

from py_crow_tool.core.models import TranslationError, TranslationException, TranslationRequest
from py_crow_tool.providers.google_v3 import GoogleV3Provider


class FakeCredentials:
    def __init__(self):
        self.valid = True
        self.token = "fake-token"
        self.refresh_calls = 0

    def refresh(self, request):
        self.refresh_calls += 1


@pytest.mark.asyncio
async def test_v3_translation_and_detection():
    async def handler(request: httpx.Request):
        if request.url.path.endswith(":detectLanguage"):
            return httpx.Response(200, json={"languages": [{"languageCode": "vi", "confidence": 0.9}]})
        return httpx.Response(200, json={"translations": [{"translatedText": "Hello", "detectedLanguageCode": "vi", "model": "nmt"}]})

    provider = GoogleV3Provider("proj", "global", "", client=httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    provider._credentials = FakeCredentials()

    result = await provider.translate(TranslationRequest("Xin chao", "en"))
    detected = await provider.detect_language("Xin chao")

    assert result.translated_text == "Hello"
    assert result.source_language == "vi"
    assert detected.language == "vi"
    await provider.close()


@pytest.mark.asyncio
async def test_v3_raises_authentication_error_when_credentials_cannot_be_obtained(monkeypatch):
    provider = GoogleV3Provider("proj", "global", "", client=httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(200))))

    def failing_default_credentials(*args, **kwargs):
        # Runs inside asyncio.to_thread — must stay a plain sync callable.
        raise RuntimeError("no ADC available in this environment")

    import py_crow_tool.providers.google_v3 as google_v3_module

    monkeypatch.setattr(google_v3_module, "default_credentials", failing_default_credentials)

    with pytest.raises(TranslationException) as error:
        await provider.translate(TranslationRequest("x", "en"))
    assert error.value.kind == TranslationError.AUTHENTICATION
    await provider.close()


def test_configured_is_false_without_a_project_id():
    provider = GoogleV3Provider("", "global", "")
    assert provider.configured is False


def test_configured_caches_the_credentials_file_stat(tmp_path):
    creds_path = tmp_path / "creds.json"
    provider = GoogleV3Provider("proj", "global", str(creds_path))

    assert provider.configured is False

    creds_path.write_text("{}")
    # still cached from the check above; a fresh instance would see the file
    assert provider.configured is False
    assert GoogleV3Provider("proj", "global", str(creds_path)).configured is True


@pytest.mark.asyncio
async def test_concurrent_authorization_calls_initialize_credentials_once():
    import asyncio

    provider = GoogleV3Provider("proj", "global", "", client=httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(200))))
    init_calls = {"count": 0}

    def fake_default_credentials(*args, **kwargs):
        # Runs inside asyncio.to_thread — must stay a plain sync callable,
        # like the real google.auth.default().
        init_calls["count"] += 1
        return FakeCredentials(), "proj"

    import py_crow_tool.providers.google_v3 as google_v3_module

    original = google_v3_module.default_credentials
    google_v3_module.default_credentials = fake_default_credentials
    try:
        tokens = await asyncio.gather(*(provider._authorization() for _ in range(5)))
    finally:
        google_v3_module.default_credentials = original

    assert init_calls["count"] == 1
    assert all(token == "Bearer fake-token" for token in tokens)
    await provider.close()
