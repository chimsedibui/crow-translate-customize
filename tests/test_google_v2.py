import httpx
import pytest

from py_crow_tool.core.models import TranslationError, TranslationException, TranslationRequest
from py_crow_tool.providers.google_v2 import GoogleV2Provider


@pytest.mark.asyncio
async def test_v2_translation_and_detection():
    async def handler(request: httpx.Request):
        if request.url.path.endswith("/detect"):
            return httpx.Response(200, json={"data": {"detections": [[{"language": "vi", "confidence": 0.9}]]}})
        return httpx.Response(200, json={"data": {"translations": [{"translatedText": "Hello &amp; welcome", "detectedSourceLanguage": "vi"}]}})

    provider = GoogleV2Provider("key", client=httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    result = await provider.translate(TranslationRequest("Xin chao", "en"))
    detected = await provider.detect_language("Xin chao")
    assert result.translated_text == "Hello & welcome"
    assert result.source_language == "vi"
    assert detected.language == "vi"
    await provider.close()


@pytest.mark.asyncio
async def test_v2_authentication_error():
    async def handler(request: httpx.Request):
        return httpx.Response(403, json={"error": {"message": "bad key"}})

    provider = GoogleV2Provider("key", client=httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    with pytest.raises(TranslationException) as error:
        await provider.translate(TranslationRequest("text", "en"))
    assert error.value.kind == TranslationError.AUTHENTICATION
    await provider.close()

