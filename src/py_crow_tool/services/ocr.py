from __future__ import annotations

from io import BytesIO

from PIL import Image
import pytesseract
from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtGui import QGuiApplication


class OcrService(QObject):
    recognized = Signal(str)
    failed = Signal(str)

    def __init__(self, tesseract_command: str = "", parent: QObject | None = None):
        super().__init__(parent)
        if tesseract_command:
            pytesseract.pytesseract.tesseract_cmd = tesseract_command

    @Slot()
    def recognizeClipboardImage(self) -> None:
        image = QGuiApplication.clipboard().image()
        if image.isNull():
            self.failed.emit("Clipboard does not contain an image")
            return
        buffer = BytesIO()
        from PySide6.QtCore import QBuffer, QIODevice

        qt_buffer = QBuffer()
        qt_buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        image.save(qt_buffer, "PNG")
        buffer.write(bytes(qt_buffer.data()))
        try:
            text = pytesseract.image_to_string(Image.open(buffer)).strip()
            self.recognized.emit(text)
        except Exception as error:
            self.failed.emit(str(error))

    def recognize_file(self, path: str, language: str | None = None) -> str:
        return pytesseract.image_to_string(Image.open(path), lang=language).strip()

