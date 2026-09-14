from __future__ import annotations

from PySide6.QtCore import Property, QBuffer, QIODevice, QObject, QRect, Signal, Slot
from PySide6.QtGui import QGuiApplication, QImage, QPixmap
from PySide6.QtQuick import QQuickImageProvider


class ScreenshotImageProvider(QQuickImageProvider):
    """Serves the most recent per-screen grabs to QML as image://capture/<screenIndex>/<generation>,
    so CaptureOverlayWindow.qml can show each monitor's own capture as its selection background
    without a round trip through a temp file."""

    def __init__(self):
        super().__init__(QQuickImageProvider.ImageType.Image)
        self._images: dict[int, QImage] = {}

    def set_images(self, images: dict[int, QImage]) -> None:
        self._images = images

    def requestImage(self, id, size, requestedSize):  # noqa: A002 - Qt's parameter name
        try:
            screen_index = int(id.split("/")[0])
        except (ValueError, IndexError):
            screen_index = -1
        image = self._images.get(screen_index, QImage())
        if size is not None:
            size.setWidth(image.width())
            size.setHeight(image.height())
        return image


class CaptureController(QObject):
    """Grabs every connected screen for the screenshot hotkey and turns a user-selected
    region into cropped PNG bytes. One CaptureOverlayWindow is instantiated per screen (see
    CaptureOverlay.qml) so the user can drag-select on whichever monitor the region actually
    is on, all within a single hotkey press."""

    regionCaptured = Signal(bytes)
    cancelled = Signal()
    generationChanged = Signal()
    captureRequested = Signal()
    screensChanged = Signal()

    def __init__(self, image_provider: ScreenshotImageProvider, parent: QObject | None = None):
        super().__init__(parent)
        self._image_provider = image_provider
        self._pixmaps: dict[int, QPixmap] = {}
        self._screens: list[dict] = []
        self._generation = 0

    @Property(int, notify=generationChanged)
    def generation(self) -> int:
        # QML's Image only refetches from a provider when its "source" string actually
        # changes; "image://capture/<index>" alone would serve the *first* capture forever.
        # CaptureOverlayWindow.qml appends this counter to the URL so every capture forces a reload.
        return self._generation

    @Property("QVariantList", notify=screensChanged)
    def screens(self) -> list[dict]:
        # Fed to an Instantiator in CaptureOverlay.qml (one CaptureOverlayWindow per entry)
        # instead of Qt.application.screens, which QML reports as undefined in this app's
        # setup -- exposing plain geometry dicts from Python sidesteps that entirely.
        return self._screens

    def capture_all_screens(self) -> bool:
        pixmaps: dict[int, QPixmap] = {}
        screens: list[dict] = []
        for index, screen in enumerate(QGuiApplication.screens()):
            pixmap = screen.grabWindow(0)
            if pixmap.isNull():
                continue
            pixmaps[index] = pixmap
            geometry = screen.geometry()
            screens.append({
                "index": index,
                "x": geometry.x(),
                "y": geometry.y(),
                "width": geometry.width(),
                "height": geometry.height(),
            })
        if not pixmaps:
            return False
        self._pixmaps = pixmaps
        self._screens = screens
        self._image_provider.set_images({index: pixmap.toImage() for index, pixmap in pixmaps.items()})
        self._generation += 1
        self.generationChanged.emit()
        self.screensChanged.emit()
        self.captureRequested.emit()
        return True

    @Slot(int, int, int, int, int)
    def confirmRegion(self, screen_index: int, x: int, y: int, width: int, height: int) -> None:
        pixmap = self._pixmaps.get(screen_index)
        if pixmap is None or width <= 0 or height <= 0:
            self.cancelled.emit()
            return
        rect = QRect(x, y, width, height).intersected(pixmap.rect())
        if rect.width() <= 0 or rect.height() <= 0:
            self.cancelled.emit()
            return
        cropped = pixmap.copy(rect)
        buffer = QBuffer()
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        cropped.save(buffer, "PNG")
        self.regionCaptured.emit(bytes(buffer.data()))

    @Slot()
    def cancel(self) -> None:
        self.cancelled.emit()
