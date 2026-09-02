import asyncio

import httpx
import pytest

from py_crow_tool.core.models import TranslationException
from py_crow_tool.providers.base import HttpProvider


@pytest.mark.asyncio
async def test_retry_honors_retry_after_header(monkeypatch):
    calls = {"count": 0}
    sleeps: list[float] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        if calls["count"] == 1:
            return httpx.Response(429, headers={"Retry-After": "5"})
        return httpx.Response(200, text="ok")

    provider = HttpProvider(client=httpx.AsyncClient(transport=httpx.MockTransport(handler)))

    import py_crow_tool.providers.base as base_module

    async def fake_sleep(seconds: float) -> None:
        sleeps.append(seconds)

    monkeypatch.setattr(base_module.asyncio, "sleep", fake_sleep)

    response = await provider._request("GET", "https://example.test/x")

    assert response.status_code == 200
    assert calls["count"] == 2
    assert sleeps and sleeps[0] == 5.0
    await provider.close()


@pytest.mark.asyncio
async def test_retry_after_is_capped_at_thirty_seconds(monkeypatch):
    sleeps: list[float] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, headers={"Retry-After": "9999"})

    provider = HttpProvider(client=httpx.AsyncClient(transport=httpx.MockTransport(handler)))

    import py_crow_tool.providers.base as base_module

    async def fake_sleep(seconds: float) -> None:
        sleeps.append(seconds)

    monkeypatch.setattr(base_module.asyncio, "sleep", fake_sleep)

    await provider._request("GET", "https://example.test/x")

    assert all(delay <= 30.0 for delay in sleeps)
    await provider.close()


@pytest.mark.asyncio
async def test_cancel_stops_every_task_sharing_a_request_id():
    provider = HttpProvider(client=httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(200))))

    async def never_ending():
        await asyncio.sleep(10)
        return "done"

    task1 = asyncio.create_task(provider._run("shared-id", never_ending()))
    task2 = asyncio.create_task(provider._run("shared-id", never_ending()))
    await asyncio.sleep(0.05)  # let both register under the same request id

    provider.cancel("shared-id")

    with pytest.raises(TranslationException):
        await task1
    with pytest.raises(TranslationException):
        await task2
    assert provider.pending_tasks() == []
    await provider.close()
