from __future__ import annotations

from PySide6.QtCore import Property, QBuffer, QIODevice, QObject, QRect, Signal, Slot
from PySide6.QtGui import QCursor, QGuiApplication, QImage, QPixmap
from PySide6.QtQuick import QQuickImageProvider


class ScreenshotImageProvider(QQuickImageProvider):
    """Serves the most recent screen grab to QML as image://capture/current, so
    CaptureOverlay.qml can show it as the selection background without a round trip
    through a temp file."""

    def __init__(self):
        super().__init__(QQuickImageProvider.ImageType.Image)
        self._image = QImage()

    def set_image(self, image: QImage) -> None:
        self._image = image

    def requestImage(self, id, size, requestedSize):  # noqa: A002 - Qt's parameter name
        if size is not None:
            size.setWidth(self._image.width())
            size.setHeight(self._image.height())
        return self._image


class CaptureController(QObject):
    """Grabs the screen under the cursor for the screenshot hotkey and turns a
    user-selected region into cropped PNG bytes. Mirrors the research doc's proposed
    Idle -> Selecting -> Capturing state flow (P1 Screenshot MVP), scoped to a single
    monitor for now -- cross-monitor selection is a follow-up (see doc section 4)."""

    regionCaptured = Signal(bytes)
    cancelled = Signal()
    generationChanged = Signal()

    def __init__(self, image_provider: ScreenshotImageProvider, parent: QObject | None = None):
        super().__init__(parent)
        self._image_provider = image_provider
        self._pixmap: QPixmap | None = None
        self._generation = 0

    @Property(int, notify=generationChanged)
    def generation(self) -> int:
        # QML's Image only refetches from a provider when its "source" string actually
        # changes; "image://capture/current" alone would serve the *first* capture forever.
        # CaptureOverlay.qml appends this counter to the URL so every capture forces a reload.
        return self._generation

    def capture_screen_at_cursor(self) -> QRect | None:
        screen = QGuiApplication.screenAt(QCursor.pos()) or QGuiApplication.primaryScreen()
        if screen is None:
            return None
        pixmap = screen.grabWindow(0)
        if pixmap.isNull():
            return None
        self._pixmap = pixmap
        self._image_provider.set_image(pixmap.toImage())
        self._generation += 1
        self.generationChanged.emit()
        return screen.geometry()

    @Slot(int, int, int, int)
    def confirmRegion(self, x: int, y: int, width: int, height: int) -> None:
        if self._pixmap is None or width <= 0 or height <= 0:
            self.cancelled.emit()
            return
        rect = QRect(x, y, width, height).intersected(self._pixmap.rect())
        if rect.width() <= 0 or rect.height() <= 0:
            self.cancelled.emit()
            return
        cropped = self._pixmap.copy(rect)
        buffer = QBuffer()
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        cropped.save(buffer, "PNG")
        self.regionCaptured.emit(bytes(buffer.data()))

    @Slot()
    def cancel(self) -> None:
        self.cancelled.emit()
