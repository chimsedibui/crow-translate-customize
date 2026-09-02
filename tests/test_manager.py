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
async def test_manager_prefers_google_v2_by_default():
    v2, plugin = FakeProvider("google-v2"), FakeProvider("some-plugin")
    result = await ProviderManager([plugin, v2]).translate(TranslationRequest("x", "en"))
    assert result.provider_id == "google-v2"


@pytest.mark.asyncio
async def test_manager_falls_back_to_another_provider_when_google_v2_not_configured():
    v2, plugin = FakeProvider("google-v2", False), FakeProvider("some-plugin")
    result = await ProviderManager([v2, plugin]).translate(TranslationRequest("x", "en"))
    assert result.provider_id == "some-plugin"


@pytest.mark.asyncio
async def test_manager_does_not_fallback_after_request_failure():
    failure = TranslationException(TranslationError.AUTHENTICATION, "denied")
    primary, secondary = FakeProvider("google-v2", failure=failure), FakeProvider("some-plugin")
    with pytest.raises(TranslationException):
        await ProviderManager([primary, secondary]).translate(TranslationRequest("x", "en"))
    assert primary.calls == 1
    assert secondary.calls == 0
