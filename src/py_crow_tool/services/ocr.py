from __future__ import annotations

import asyncio
from io import BytesIO

from PIL import Image
import pytesseract
from PySide6.QtCore import QBuffer, QIODevice, QObject, Signal, Slot
from PySide6.QtGui import QGuiApplication

from py_crow_tool.services.async_runner import AsyncLoopRunner


class OcrService(QObject):
    recognized = Signal(str)
    failed = Signal(str)

    def __init__(self, tesseract_command: str = "", loop_runner: AsyncLoopRunner | None = None, parent: QObject | None = None):
        super().__init__(parent)
        self._loop_runner = loop_runner
        if tesseract_command:
            pytesseract.pytesseract.tesseract_cmd = tesseract_command

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

        def _recognize() -> None:
            try:
                text = pytesseract.image_to_string(Image.open(BytesIO(data))).strip()
                self.recognized.emit(text)
            except Exception as error:
                self.failed.emit(str(error))

        if self._loop_runner is not None:
            self._loop_runner.submit(asyncio.to_thread(_recognize))
        else:
            _recognize()

    def recognize_file(self, path: str, language: str | None = None) -> str:
        return pytesseract.image_to_string(Image.open(path), lang=language).strip()
