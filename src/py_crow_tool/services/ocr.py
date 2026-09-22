from __future__ import annotations

import asyncio
from typing import Callable

from PySide6.QtCore import QBuffer, QIODevice, QObject, Signal, Slot
from PySide6.QtGui import QGuiApplication

from py_crow_tool.config import AppSettings
from py_crow_tool.core.ocr_models import OcrException, OcrRequest
from py_crow_tool.providers.azure_openai_ocr import AzureOpenAiOcrProvider
from py_crow_tool.providers.openai_ocr import OpenAiOcrProvider
from py_crow_tool.services.async_runner import AsyncLoopRunner


class OcrService(QObject):
    # Clipboard-button flow: feeds the main window's source text.
    recognized = Signal(str)
    failed = Signal(str)
    # Screenshot-region flow: feeds the quick-translate popup instead. Kept on separate
    # signals (and a separate stale-request tracker) so a clipboard OCR in flight and a
    # screenshot-region OCR in flight can't invalidate each other's result.
    regionRecognized = Signal(str)
    regionFailed = Signal(str)

    def __init__(self, settings: AppSettings, loop_runner: AsyncLoopRunner | None = None, parent: QObject | None = None):
        super().__init__(parent)
        self._settings = settings
        self._loop_runner = loop_runner
        # Both readers are built up front and kept: switching engines in Settings should
        # not have to tear down and rebuild an httpx client, and each holds its own
        # in-flight tasks that cancel_current() still has to be able to reach.
        self._openai = OpenAiOcrProvider(
            settings.openai_api_key,
            model=settings.openai.ocr_model,
            max_dimension=settings.openai.ocr_resize_resolution,
            image_format=settings.openai.ocr_image_format,
            jpeg_quality=settings.openai.ocr_jpeg_quality,
        )
        self._azure = AzureOpenAiOcrProvider(
            settings.azure_openai_api_key,
            endpoint=settings.azure_openai_endpoint,
            deployment=settings.azure_openai_deployment,
            api_version=settings.azure_openai_api_version,
            max_dimension=settings.openai.ocr_resize_resolution,
            image_format=settings.openai.ocr_image_format,
            jpeg_quality=settings.openai.ocr_jpeg_quality,
        )
        # Only the result matching a channel's id may reach that channel's signals: an
        # in-flight recognize() call that finishes after a newer one started on the same
        # channel must not overwrite the newer result.
        self._latest_clipboard_request_id: str | None = None
        self._latest_region_request_id: str | None = None

    @property
    def _provider(self):
        """The reader the current settings select.

        An engine chosen but left unconfigured falls back rather than failing: the
        setting outlives the credential it was chosen with, and an OCR that reports
        "not configured" is less useful than one that quietly uses the key that works.
        """
        selected = self._azure if self._settings.ocr_engine == "azure-openai" else self._openai
        other = self._openai if selected is self._azure else self._azure
        if selected.configured:
            return selected
        if other.configured:
            return other
        # Neither is configured; hand back the selected one so its own error names the
        # engine the user actually picked.
        return selected

    def apply_settings(self) -> None:
        """Re-read OCR settings the providers were constructed with, so a key or option
        entered in Settings takes effect immediately instead of only after a restart."""
        self._openai.api_key = self._settings.openai_api_key.strip()
        self._openai.model = self._settings.openai.ocr_model
        self._azure.api_key = self._settings.azure_openai_api_key.strip()
        self._azure.endpoint = AzureOpenAiOcrProvider._normalize_endpoint(self._settings.azure_openai_endpoint)
        self._azure.deployment = self._settings.azure_openai_deployment.strip()
        self._azure.api_version = self._settings.azure_openai_api_version.strip() or "2025-01-01-preview"
        for provider in (self._openai, self._azure):
            provider.max_dimension = self._settings.openai.ocr_resize_resolution
            provider.image_format = self._settings.openai.ocr_image_format
            provider.jpeg_quality = self._settings.openai.ocr_jpeg_quality

    def _language_hint(self, language: str | None = None) -> str | None:
        return language or self._settings.ocr_language

    def _submit(self, request: OcrRequest, provider, on_success: Callable[[str, str], None], on_failure: Callable[[str, str], None]) -> None:
        async def _operation() -> None:
            try:
                result = await provider.recognize(request)
            except OcrException as error:
                on_failure(request.request_id, str(error))
                return
            on_success(request.request_id, result.text)

        if self._loop_runner is not None:
            self._loop_runner.submit(_operation())
        else:
            asyncio.run(_operation())

    @Slot()
    def recognizeClipboardImage(self) -> None:
        image = QGuiApplication.clipboard().image()
        if image.isNull():
            self.failed.emit("Clipboard does not contain an image")
            return
        buffer = QBuffer()
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        image.save(buffer, "PNG")
        data = bytes(buffer.data())

        request = OcrRequest(image=data, language_hint=self._language_hint())
        self._latest_clipboard_request_id = request.request_id

        def _ok(request_id: str, text: str) -> None:
            if request_id == self._latest_clipboard_request_id:
                self.recognized.emit(text)

        def _err(request_id: str, message: str) -> None:
            if request_id == self._latest_clipboard_request_id:
                self.failed.emit(message)

        self._submit(request, self._provider, _ok, _err)

    def recognizeImageBytes(self, data: bytes, language: str | None = None) -> None:
        """Screenshot-region counterpart to recognizeClipboardImage(): same async/stale-result
        handling, but for an in-memory crop (e.g. from CaptureController) instead of the
        clipboard, and reporting through regionRecognized/regionFailed instead."""
        request = OcrRequest(image=data, language_hint=self._language_hint(language))
        self._latest_region_request_id = request.request_id

        def _ok(request_id: str, text: str) -> None:
            if request_id == self._latest_region_request_id:
                self.regionRecognized.emit(text)

        def _err(request_id: str, message: str) -> None:
            if request_id == self._latest_region_request_id:
                self.regionFailed.emit(message)

        self._submit(request, self._provider, _ok, _err)

    def cancel_current(self) -> None:
        for request_id in (self._latest_clipboard_request_id, self._latest_region_request_id):
            if request_id is None:
                continue
            # Both, not just the selected one: a request may still be in flight on the
            # engine that was selected when it started.
            self._openai.cancel(request_id)
            self._azure.cancel(request_id)

    async def recognize_file(self, path: str, language: str | None = None) -> str:
        with open(path, "rb") as stream:
            data = stream.read()
        request = OcrRequest(image=data, language_hint=self._language_hint(language))
        result = await self._provider.recognize(request)
        return result.text

    async def close(self) -> None:
        await self._openai.close()
        await self._azure.close()
