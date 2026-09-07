from __future__ import annotations

import asyncio
from io import BytesIO
from typing import Any

from PIL import Image
import pytesseract

from py_crow_tool.core.ocr_models import OcrError, OcrException, OcrRequest, OcrResult

_TESSERACT_LANG_MAP = {"vi": "vie", "en": "eng"}
_DEFAULT_MULTI_LANG = "eng+vie"


def _resolve_tesseract_lang(hint: str | None) -> str:
    if not hint or hint == "auto":
        return _DEFAULT_MULTI_LANG
    return _TESSERACT_LANG_MAP.get(hint, hint)


class TesseractOcrProvider:
    id = "tesseract"
    display_name = "Tesseract (local, CPU)"

    def __init__(self, tesseract_command: str = ""):
        if tesseract_command:
            pytesseract.pytesseract.tesseract_cmd = tesseract_command
        self._tasks: dict[str, list[asyncio.Task[Any]]] = {}

    @property
    def configured(self) -> bool:
        return True

    def cancel(self, request_id: str) -> None:
        for task in self._tasks.get(request_id, []):
            task.cancel()

    def pending_tasks(self) -> list[asyncio.Task[Any]]:
        return [task for tasks in self._tasks.values() for task in tasks]

    async def close(self) -> None:
        return None

    async def recognize(self, request: OcrRequest) -> OcrResult:
        lang = _resolve_tesseract_lang(request.language_hint)

        def _run() -> str:
            try:
                image = Image.open(BytesIO(request.image))
            except Exception as error:  # noqa: BLE001 - corrupt/unsupported image data
                raise OcrException(OcrError.INVALID_REQUEST, f"Could not decode image: {error}") from error
            try:
                return pytesseract.image_to_string(image, lang=lang).strip()
            except Exception as error:  # noqa: BLE001 - tesseract binary/runtime errors
                raise OcrException(OcrError.SERVICE, str(error)) from error

        task = asyncio.create_task(asyncio.to_thread(_run))
        self._tasks.setdefault(request.request_id, []).append(task)
        try:
            text = await task
        except asyncio.CancelledError as error:
            raise OcrException(OcrError.CANCELLED, "OCR cancelled") from error
        finally:
            tasks = self._tasks.get(request.request_id)
            if tasks is not None:
                tasks.remove(task)
                if not tasks:
                    self._tasks.pop(request.request_id, None)
        return OcrResult(text=text, provider_id=self.id, model=f"tesseract:{lang}")
