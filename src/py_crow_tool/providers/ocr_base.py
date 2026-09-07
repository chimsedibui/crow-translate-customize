from __future__ import annotations

import asyncio
from typing import Any

import httpx

from py_crow_tool.core.ocr_models import OcrError, OcrException


class HttpOcrProvider:
    """Same retry/cancellation/error-mapping shape as HttpProvider (providers/base.py), kept
    separate because OCR and translation calls raise different exception types."""

    def __init__(self, *, client: httpx.AsyncClient | None = None, timeout: float = 30.0):
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(timeout=timeout)
        self._tasks: dict[str, list[asyncio.Task[Any]]] = {}

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    def cancel(self, request_id: str) -> None:
        for task in self._tasks.get(request_id, []):
            task.cancel()

    def pending_tasks(self) -> list[asyncio.Task[Any]]:
        return [task for tasks in self._tasks.values() for task in tasks]

    async def _run(self, request_id: str, operation):
        task = asyncio.create_task(operation)
        self._tasks.setdefault(request_id, []).append(task)
        try:
            return await task
        except asyncio.CancelledError as error:
            raise OcrException(OcrError.CANCELLED, "OCR cancelled") from error
        finally:
            tasks = self._tasks.get(request_id)
            if tasks is not None:
                tasks.remove(task)
                if not tasks:
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
                raise OcrException(OcrError.NETWORK, str(error), retryable=True) from error
            if response.status_code in {429, 500, 502, 503, 504} and attempt < 2:
                delay = 0.25 * (2**attempt)
                if response.status_code == 429:
                    delay = max(delay, self._retry_after_seconds(response) or 0.0)
                await asyncio.sleep(min(delay, 30.0))
                continue
            return response
        raise OcrException(OcrError.NETWORK, str(last_error), retryable=True)

    @staticmethod
    def _retry_after_seconds(response: httpx.Response) -> float | None:
        header = response.headers.get("Retry-After")
        if not header:
            return None
        try:
            return float(header)
        except ValueError:
            return None

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
            kind = OcrError.AUTHENTICATION
        elif response.status_code == 429:
            kind = OcrError.QUOTA
        elif response.status_code in {400, 404}:
            kind = OcrError.INVALID_REQUEST
        else:
            kind = OcrError.SERVICE
        raise OcrException(kind, message or f"OCR API returned HTTP {response.status_code}")
