from __future__ import annotations

import asyncio
from typing import Any

import httpx

from py_crow_tool.core.models import TranslationError, TranslationException


class HttpProvider:
    def __init__(self, *, client: httpx.AsyncClient | None = None, timeout: float = 20.0):
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(timeout=timeout)
        self._tasks: dict[str, asyncio.Task[Any]] = {}

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    def cancel(self, request_id: str) -> None:
        task = self._tasks.get(request_id)
        if task:
            task.cancel()

    async def _run(self, request_id: str, operation):
        task = asyncio.create_task(operation)
        self._tasks[request_id] = task
        try:
            return await task
        except asyncio.CancelledError as error:
            raise TranslationException(TranslationError.CANCELLED, "Translation cancelled") from error
        finally:
            self._tasks.pop(request_id, None)

    async def _request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                response = await self._client.request(method, url, **kwargs)
            except (httpx.TimeoutException, httpx.NetworkError) as error:
                last_error = error
                if attempt < 2:
                    await asyncio.sleep(0.25 * (2**attempt))
                    continue
                raise TranslationException(TranslationError.NETWORK, str(error), retryable=True) from error
            if response.status_code in {429, 500, 502, 503, 504} and attempt < 2:
                await asyncio.sleep(0.25 * (2**attempt))
                continue
            return response
        raise TranslationException(TranslationError.NETWORK, str(last_error), retryable=True)

    @staticmethod
    def _raise_for_response(response: httpx.Response) -> None:
        if response.is_success:
            return
        try:
            detail = response.json().get("error", {})
            message = detail.get("message") or response.text
        except (ValueError, AttributeError):
            message = response.text
        if response.status_code in {401, 403}:
            kind = TranslationError.AUTHENTICATION
        elif response.status_code == 429:
            kind = TranslationError.QUOTA
        elif response.status_code in {400, 404}:
            kind = TranslationError.INVALID_REQUEST
        else:
            kind = TranslationError.SERVICE
        raise TranslationException(kind, message or f"Google API returned HTTP {response.status_code}")

