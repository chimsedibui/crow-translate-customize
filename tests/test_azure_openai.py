import httpx
import pytest

from py_crow_tool.core.models import TranslationError, TranslationException, TranslationRequest
from py_crow_tool.providers.azure_openai import AzureOpenAiProvider


def _provider(handler, **kwargs):
    defaults = dict(endpoint="https://res.openai.azure.com", deployment="gpt-4o")
    defaults.update(kwargs)
    return AzureOpenAiProvider("key", client=httpx.AsyncClient(transport=httpx.MockTransport(handler)), **defaults)


def _reply(text):
    return httpx.Response(200, json={"choices": [{"message": {"content": text}}]})


@pytest.mark.asyncio
async def test_translation_targets_the_deployment_url_and_returns_the_reply():
    seen = {}

    async def handler(request: httpx.Request):
        seen["path"] = request.url.path
        seen["api_version"] = request.url.params.get("api-version")
        seen["auth"] = request.headers.get("api-key")
        return _reply("  Hello world  ")

    provider = _provider(handler, api_version="2025-01-01-preview")
    result = await provider.translate(TranslationRequest("Xin chao", "en", "vi"))
    assert result.translated_text == "Hello world"
    assert result.source_language == "vi"
    assert result.provider_id == "azure-openai"
    assert seen["path"] == "/openai/deployments/gpt-4o/chat/completions"
    assert seen["api_version"] == "2025-01-01-preview"
    # The key goes in Azure's own header, never in the query string.
    assert seen["auth"] == "key"
    await provider.close()


@pytest.mark.asyncio
async def test_auto_source_runs_detection_so_the_result_names_a_language():
    async def handler(request: httpx.Request):
        body = request.read().decode()
        if "Identify the language" in body:
            return _reply('{"language": "vi", "confidence": 0.98}')
        return _reply("Hello")

    provider = _provider(handler)
    result = await provider.translate(TranslationRequest("Xin chao", "en", "auto"))
    assert result.translated_text == "Hello"
    assert result.source_language == "vi"
    await provider.close()


@pytest.mark.asyncio
async def test_detection_accepts_a_fenced_object_or_a_bare_code():
    async def fenced(request: httpx.Request):
        return _reply('```json\n{"language": "fr", "confidence": 0.8}\n```')

    async def bare(request: httpx.Request):
        return _reply("fr")

    for handler, confidence in ((fenced, 0.8), (bare, None)):
        provider = _provider(handler)
        detected = await provider.detect_language("bonjour")
        assert detected.language == "fr"
        assert detected.confidence == confidence
        await provider.close()


@pytest.mark.asyncio
async def test_unreadable_detection_is_a_parsing_error():
    async def handler(request: httpx.Request):
        return _reply("I think this might be French, but it is hard to say.")

    provider = _provider(handler)
    with pytest.raises(TranslationException) as error:
        await provider.detect_language("bonjour")
    assert error.value.kind == TranslationError.PARSING
    await provider.close()


@pytest.mark.asyncio
async def test_authentication_error_is_classified():
    async def handler(request: httpx.Request):
        return httpx.Response(401, json={"error": {"message": "Access denied"}})

    provider = _provider(handler)
    with pytest.raises(TranslationException) as error:
        await provider.translate(TranslationRequest("text", "en", "vi"))
    assert error.value.kind == TranslationError.AUTHENTICATION
    assert "Access denied" in str(error.value)
    await provider.close()


@pytest.mark.asyncio
async def test_an_http_error_with_no_body_names_this_provider_not_google():
    async def handler(request: httpx.Request):
        return httpx.Response(418, text="")

    provider = _provider(handler)
    with pytest.raises(TranslationException) as error:
        await provider.translate(TranslationRequest("text", "en", "vi"))
    assert "Azure OpenAI" in str(error.value)
    await provider.close()


@pytest.mark.parametrize(
    "given",
    [
        "https://res.openai.azure.com",
        "https://res.openai.azure.com/",
        "https://res.openai.azure.com/openai",
        "https://res.openai.azure.com/openai/v1",
        "  res.openai.azure.com  ",
    ],
)
def test_endpoint_is_reduced_to_the_resource_root(given):
    provider = AzureOpenAiProvider("key", endpoint=given, deployment="gpt-4o")
    assert provider.endpoint == "https://res.openai.azure.com"
    assert provider._chat_url() == "https://res.openai.azure.com/openai/deployments/gpt-4o/chat/completions"


@pytest.mark.parametrize(
    ("key", "endpoint", "deployment", "missing"),
    [
        ("", "https://r.openai.azure.com", "gpt-4o", "API key"),
        ("key", "", "gpt-4o", "endpoint"),
        ("key", "https://r.openai.azure.com", "", "deployment"),
    ],
)
@pytest.mark.asyncio
async def test_each_missing_piece_is_named_in_the_error(key, endpoint, deployment, missing):
    provider = AzureOpenAiProvider(key, endpoint=endpoint, deployment=deployment)
    assert provider.configured is False
    with pytest.raises(TranslationException) as error:
        await provider.translate(TranslationRequest("text", "en", "vi"))
    assert error.value.kind == TranslationError.CONFIGURATION
    assert missing in str(error.value)


@pytest.mark.asyncio
async def test_a_reasoning_deployment_can_drop_the_temperature():
    seen = {}

    async def handler(request: httpx.Request):
        seen["body"] = request.read().decode()
        return _reply("Hello")

    provider = _provider(handler, temperature=None)
    await provider.translate(TranslationRequest("Xin chao", "en", "vi"))
    assert "temperature" not in seen["body"]
    await provider.close()
