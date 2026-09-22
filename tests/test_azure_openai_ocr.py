import json
from io import BytesIO

import httpx
import pytest
from PIL import Image

from py_crow_tool.config import AppSettings
from py_crow_tool.core.ocr_models import OcrError, OcrException, OcrRequest
from py_crow_tool.providers.azure_openai_ocr import AzureOpenAiOcrProvider
from py_crow_tool.services.ocr import OcrService


def _png(size=(40, 20)) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", size, "white").save(buffer, format="PNG")
    return buffer.getvalue()


def _provider(handler, **kwargs):
    defaults = dict(endpoint="https://res.openai.azure.com", deployment="gpt-4o")
    defaults.update(kwargs)
    return AzureOpenAiOcrProvider("key", client=httpx.AsyncClient(transport=httpx.MockTransport(handler)), **defaults)


def _reply(text):
    return httpx.Response(200, json={"choices": [{"message": {"content": text}}], "usage": {"total_tokens": 7}})


@pytest.mark.asyncio
async def test_reads_text_and_addresses_the_deployment_the_azure_way():
    seen = {}

    async def handler(request: httpx.Request):
        seen["path"] = request.url.path
        seen["api_version"] = request.url.params.get("api-version")
        seen["api_key"] = request.headers.get("api-key")
        seen["authorization"] = request.headers.get("Authorization")
        seen["body"] = json.loads(request.read())
        return _reply("Hoa don ban le")

    provider = _provider(handler)
    result = await provider.recognize(OcrRequest(image=_png()))
    assert result.text == "Hoa don ban le"
    assert result.provider_id == "azure-openai-vision"
    assert result.model == "gpt-4o"
    assert seen["path"] == "/openai/deployments/gpt-4o/chat/completions"
    assert seen["api_version"] == "2025-01-01-preview"
    assert seen["api_key"] == "key"
    # Azure's own header, not OpenAI's bearer scheme.
    assert seen["authorization"] is None
    # The deployment is in the path; repeating it in the body can be rejected.
    assert "model" not in seen["body"]
    # The image still travels as an inline data URI, as it does for OpenAI.
    assert seen["body"]["messages"][0]["content"][1]["image_url"]["url"].startswith("data:image/png;base64,")
    await provider.close()


@pytest.mark.asyncio
async def test_markdown_hard_breaks_are_stripped_from_each_line():
    """Asked to preserve line breaks, the model emits trailing double-spaces."""

    async def handler(request: httpx.Request):
        return _reply("Line one  \nLine two   \nLine three")

    provider = _provider(handler)
    result = await provider.recognize(OcrRequest(image=_png()))
    assert result.text == "Line one\nLine two\nLine three"
    await provider.close()


@pytest.mark.asyncio
async def test_a_language_hint_reaches_the_prompt():
    seen = {}

    async def handler(request: httpx.Request):
        seen["prompt"] = json.loads(request.read())["messages"][0]["content"][0]["text"]
        return _reply("xin chao")

    provider = _provider(handler)
    await provider.recognize(OcrRequest(image=_png(), language_hint="vi"))
    assert "Vietnamese" in seen["prompt"]
    await provider.close()


@pytest.mark.asyncio
async def test_a_large_image_is_downscaled_before_upload():
    seen = {}

    async def handler(request: httpx.Request):
        seen["body"] = json.loads(request.read())
        return _reply("text")

    provider = _provider(handler, max_dimension=64)
    original = _png((512, 256))
    result = await provider.recognize(OcrRequest(image=original))
    assert result.metadata["image_bytes_original"] == len(original)
    assert result.metadata["image_bytes_sent"] < len(original)
    await provider.close()


@pytest.mark.parametrize(
    ("key", "endpoint", "deployment", "missing"),
    [
        ("", "https://r.openai.azure.com", "gpt-4o", "API key"),
        ("key", "", "gpt-4o", "endpoint"),
        ("key", "https://r.openai.azure.com", "", "deployment"),
    ],
)
@pytest.mark.asyncio
async def test_each_missing_piece_is_named(key, endpoint, deployment, missing):
    provider = AzureOpenAiOcrProvider(key, endpoint=endpoint, deployment=deployment)
    assert provider.configured is False
    with pytest.raises(OcrException) as error:
        await provider.recognize(OcrRequest(image=_png()))
    assert error.value.kind == OcrError.CONFIGURATION
    assert missing in str(error.value)


@pytest.mark.asyncio
async def test_a_text_only_deployment_surfaces_the_service_error():
    async def handler(request: httpx.Request):
        return httpx.Response(400, json={"error": {"message": "The model does not support image input."}})

    provider = _provider(handler)
    with pytest.raises(OcrException) as error:
        await provider.recognize(OcrRequest(image=_png()))
    assert error.value.kind == OcrError.INVALID_REQUEST
    assert "image input" in str(error.value)
    await provider.close()


def test_endpoint_is_reduced_the_same_way_as_the_translation_provider():
    provider = AzureOpenAiOcrProvider("key", endpoint="res.openai.azure.com/openai/v1", deployment="gpt-4o")
    assert provider.endpoint == "https://res.openai.azure.com"


# --- engine selection in the service -----------------------------------------------


def _settings(engine, *, openai_key="", azure_key=""):
    settings = AppSettings()
    settings.ocr_engine = engine
    settings.openai.api_key = openai_key
    settings.azure_openai.api_key = azure_key
    settings.azure_openai.endpoint = "https://res.openai.azure.com"
    settings.azure_openai.deployment = "gpt-4o"
    return settings


def test_service_uses_the_selected_engine():
    service = OcrService(_settings("azure-openai", openai_key="openai", azure_key="azure"))
    assert service._provider.id == "azure-openai-vision"
    service._settings.ocr_engine = "openai"
    assert service._provider.id == "openai-vision"


def test_selecting_an_unconfigured_engine_falls_back_to_the_one_that_works():
    """A stale engine choice must not be able to disable OCR entirely."""
    service = OcrService(_settings("azure-openai", openai_key="openai", azure_key=""))
    assert service._provider.id == "openai-vision"


def test_with_nothing_configured_the_error_names_the_engine_the_user_picked():
    service = OcrService(_settings("azure-openai"))
    assert service._provider.id == "azure-openai-vision"


def test_apply_settings_moves_new_azure_credentials_onto_the_provider():
    settings = _settings("azure-openai")
    service = OcrService(settings)
    assert service._azure.configured is False
    settings.azure_openai.api_key = "fresh"
    settings.azure_openai.endpoint = "https://other.openai.azure.com/openai/v1"
    settings.azure_openai.deployment = "gpt-4o-mini"
    service.apply_settings()
    assert service._azure.configured is True
    assert service._azure.endpoint == "https://other.openai.azure.com"
    assert service._azure.deployment == "gpt-4o-mini"
    assert service._provider.id == "azure-openai-vision"


def test_resize_settings_apply_to_both_engines():
    settings = _settings("openai", openai_key="openai")
    service = OcrService(settings)
    settings.openai.ocr_resize_resolution = 640
    service.apply_settings()
    assert service._openai.max_dimension == 640
    assert service._azure.max_dimension == 640


def test_the_fallback_works_in_both_directions():
    """Symmetry matters: either engine can be the one that still has a key."""
    azure_only = OcrService(_settings("openai", azure_key="azure"))
    assert azure_only._provider.id == "azure-openai-vision"
    openai_only = OcrService(_settings("azure-openai", openai_key="openai"))
    assert openai_only._provider.id == "openai-vision"
