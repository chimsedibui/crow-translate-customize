import json

import httpx
import pytest

from py_crow_tool.config import AppSettings
from py_crow_tool.core.models import TranslationError, TranslationException
from py_crow_tool.core.refine_models import RefineRequest
from py_crow_tool.providers.refiner import AzureOpenAiRefiner, OpenAiRefiner, build_system_prompt, parse_refine_reply
from py_crow_tool.services.refine import RefineService

_GOOD = json.dumps(
    {
        "options": [
            {"label": "Concise", "text": "We fixed the login bug.  \nDeploying tomorrow."},
            {"label": "Detailed", "text": "We have fixed the login bug and plan to deploy it tomorrow."},
        ],
        "notes": ["Tách thành hai câu", "  "],
    }
)


def _reply(content, status=200):
    return httpx.Response(status, json={"choices": [{"message": {"content": content}}]})


def _client(handler):
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def _azure(handler, **kwargs):
    defaults = dict(endpoint="https://res.openai.azure.com/openai/v1", deployment="gpt-4o")
    defaults.update(kwargs)
    return AzureOpenAiRefiner("azure-key", client=_client(handler), **defaults)


def test_parse_reads_options_and_notes_and_strips_hard_breaks():
    result = parse_refine_reply(_GOOD, "azure-openai")
    assert [option.label for option in result.options] == ["Concise", "Detailed"]
    # The markdown hard break would otherwise travel into the client's chat window.
    assert result.options[0].text == "We fixed the login bug.\nDeploying tomorrow."
    assert result.notes == ("Tách thành hai câu",)


def test_parse_accepts_a_fenced_reply_and_bare_string_options():
    result = parse_refine_reply('```json\n{"options": ["Hi there."], "notes": []}\n```', "openai")
    assert result.options[0].label == "Option 1"
    assert result.options[0].text == "Hi there."


@pytest.mark.parametrize("reply", ["not json", '{"options": []}', '{"options": [{"label": "x", "text": "  "}]}', "[1, 2]"])
def test_parse_rejects_replies_with_nothing_to_show(reply):
    with pytest.raises(TranslationException) as caught:
        parse_refine_reply(reply, "openai")
    assert caught.value.kind == TranslationError.PARSING


def test_prompt_carries_the_tone_and_falls_back_to_friendly_for_unknown_ones():
    assert "formal and professional" in build_system_prompt("formal")
    assert build_system_prompt("nonsense") == build_system_prompt("friendly")
    # The guard rail that matters most for client messages.
    assert "Never add promises" in build_system_prompt("friendly")


@pytest.mark.asyncio
async def test_azure_refiner_targets_the_deployment_and_asks_for_json():
    seen = {}

    async def handler(request: httpx.Request):
        seen["path"] = request.url.path
        seen["version"] = request.url.params.get("api-version")
        seen["key"] = request.headers.get("api-key")
        seen["body"] = json.loads(request.read())
        return _reply(_GOOD)

    refiner = _azure(handler)
    result = await refiner.refine(RefineRequest("anh oi bug login fix xong roi", "concise"))
    assert seen["path"] == "/openai/deployments/gpt-4o/chat/completions"
    assert seen["version"] == "2025-01-01-preview"
    assert seen["key"] == "azure-key"
    assert seen["body"]["response_format"] == {"type": "json_object"}
    # No temperature: a reasoning deployment behind the name would reject it.
    assert "temperature" not in seen["body"]
    assert "short and direct" in seen["body"]["messages"][0]["content"]
    assert seen["body"]["messages"][1]["content"] == "anh oi bug login fix xong roi"
    assert result.provider_id == "azure-openai"
    await refiner.close()


@pytest.mark.asyncio
async def test_openai_refiner_names_its_model_and_keeps_gpt5_reasoning_low():
    seen = {}

    async def handler(request: httpx.Request):
        seen["auth"] = request.headers.get("authorization")
        seen["body"] = json.loads(request.read())
        return _reply(_GOOD)

    refiner = OpenAiRefiner("sk-test", model="gpt-5-mini", client=_client(handler))
    await refiner.refine(RefineRequest("xin chao"))
    assert seen["auth"] == "Bearer sk-test"
    assert seen["body"]["model"] == "gpt-5-mini"
    assert seen["body"]["reasoning_effort"] == "low"
    await refiner.close()


@pytest.mark.asyncio
async def test_service_falls_back_to_openai_and_says_azure_failed():
    async def azure_down(request):
        return httpx.Response(401, json={"error": {"message": "bad key"}})

    async def openai_ok(request):
        return _reply(_GOOD)

    service = RefineService(AppSettings(), refiners=[_azure(azure_down), OpenAiRefiner("sk", client=_client(openai_ok))])
    result = await service.refine(RefineRequest("xin chao"))
    assert result.provider_id == "openai"
    assert result.fallback_from == ("Azure OpenAI",)
    await service.close()


@pytest.mark.asyncio
async def test_service_skips_an_unconfigured_azure_without_calling_it():
    calls = []

    async def handler(request):
        calls.append(request.url.host)
        return _reply(_GOOD)

    azure = AzureOpenAiRefiner("", endpoint="", deployment="", client=_client(handler))
    service = RefineService(AppSettings(), refiners=[azure, OpenAiRefiner("sk", client=_client(handler))])
    result = await service.refine(RefineRequest("xin chao"))
    assert calls == ["api.openai.com"]
    # Not configured is not a failure worth reporting.
    assert result.fallback_from == ()
    await service.close()


@pytest.mark.asyncio
async def test_service_names_every_failure_when_nothing_answers():
    async def azure_down(request):
        return httpx.Response(401, json={"error": {"message": "bad azure key"}})

    async def openai_garbled(request):
        return _reply("sorry, I cannot")

    service = RefineService(AppSettings(), refiners=[_azure(azure_down), OpenAiRefiner("sk", client=_client(openai_garbled))])
    with pytest.raises(TranslationException) as caught:
        await service.refine(RefineRequest("xin chao"))
    assert "Azure OpenAI: bad azure key" in str(caught.value)
    assert "OpenAI: " in str(caught.value)
    await service.close()


@pytest.mark.asyncio
async def test_service_without_any_key_explains_what_to_configure():
    service = RefineService(AppSettings())
    assert not service.configured
    with pytest.raises(TranslationException) as caught:
        await service.refine(RefineRequest("xin chao"))
    assert caught.value.kind == TranslationError.CONFIGURATION
    await service.close()


@pytest.mark.asyncio
async def test_apply_settings_picks_up_keys_saved_after_startup():
    settings = AppSettings()
    service = RefineService(settings)
    settings.azure_openai.api_key = "k"
    settings.azure_openai.endpoint = "res.openai.azure.com"
    settings.azure_openai.deployment = "gpt-4o"
    settings.openai.refine_model = "gpt-4o-mini"
    service.apply_settings()
    assert service.configured
    assert service._azure.endpoint == "https://res.openai.azure.com"
    assert service._openai.model == "gpt-4o-mini"
    await service.close()
