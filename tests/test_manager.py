import pytest

from py_crow_tool.core.models import DetectedLanguage, TranslationError, TranslationException, TranslationRequest, TranslationResult
from py_crow_tool.providers.manager import ProviderManager


class FakeProvider:
    def __init__(self, provider_id, configured=True, failure=None):
        self.id = provider_id
        self.display_name = provider_id
        self.configured = configured
        self.failure = failure
        self.calls = 0

    async def translate(self, request):
        self.calls += 1
        if self.failure:
            raise self.failure
        return TranslationResult("ok", "vi", "en", self.id)

    async def detect_language(self, text): return DetectedLanguage("vi", 1.0)
    def supported_languages(self): return []
    def cancel(self, request_id): pass


@pytest.mark.asyncio
async def test_manager_prefers_v3():
    v3, v2 = FakeProvider("google-v3"), FakeProvider("google-v2")
    result = await ProviderManager([v2, v3]).translate(TranslationRequest("x", "en"))
    assert result.provider_id == "google-v3"


@pytest.mark.asyncio
async def test_manager_uses_v2_when_v3_not_configured():
    v3, v2 = FakeProvider("google-v3", False), FakeProvider("google-v2")
    result = await ProviderManager([v3, v2]).translate(TranslationRequest("x", "en"))
    assert result.provider_id == "google-v2"


@pytest.mark.asyncio
async def test_manager_does_not_fallback_after_request_failure():
    failure = TranslationException(TranslationError.AUTHENTICATION, "denied")
    v3, v2 = FakeProvider("google-v3", failure=failure), FakeProvider("google-v2")
    with pytest.raises(TranslationException):
        await ProviderManager([v3, v2]).translate(TranslationRequest("x", "en"))
    assert v3.calls == 1
    assert v2.calls == 0

