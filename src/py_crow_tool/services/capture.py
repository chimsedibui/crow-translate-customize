from __future__ import annotations

from PySide6.QtCore import Property, QBuffer, QIODevice, QObject, QRect, Signal, Slot
from PySide6.QtGui import QGuiApplication, QImage
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

    def clear(self) -> None:
        self._images = {}

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
        # One full-resolution grab per monitor -- tens of MB on a 1440p + 1080p desk.
        # They are only needed while the overlay is up, so release() drops them as
        # soon as the user confirms or cancels; holding on to them between hotkey
        # presses is what made every screenshot cost RAM that never came back.
        self._images: dict[int, QImage] = {}
        # Seeded from the current layout so the overlay windows are built at startup,
        # not on the first hotkey press -- creating a Window per monitor is the slow
        # part of putting the overlay up.
        self._screens: list[dict] = [
            self._screen_entry(index, screen) for index, screen in enumerate(QGuiApplication.screens())
        ]
        self._generation = 0

    @staticmethod
    def _screen_entry(index: int, screen) -> dict:
        geometry = screen.geometry()
        return {
            "index": index,
            "x": geometry.x(),
            "y": geometry.y(),
            "width": geometry.width(),
            "height": geometry.height(),
        }

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
        images: dict[int, QImage] = {}
        screens: list[dict] = []
        for index, screen in enumerate(QGuiApplication.screens()):
            # Kept as a QImage only: the provider serves the same (implicitly shared)
            # image to QML and confirmRegion crops from it, so there is one copy of
            # each screen in memory instead of a QPixmap plus a converted QImage.
            image = screen.grabWindow(0).toImage()
            if image.isNull():
                continue
            images[index] = image
            screens.append(self._screen_entry(index, screen))
        if not images:
            return False
        self._images = images
        self._image_provider.set_images(images)
        self._generation += 1
        self.generationChanged.emit()
        # Every screensChanged makes CaptureOverlay.qml's Instantiator destroy and rebuild
        # every overlay window, which is what made each hotkey press stall. Only a real
        # layout change (monitor plugged in, resolution changed) is worth that.
        if screens != self._screens:
            self._screens = screens
            self.screensChanged.emit()
        self.captureRequested.emit()
        return True

    def release(self) -> None:
        """Drop the screen grabs once the overlay is gone; the next hotkey press grabs anew."""
        self._images = {}
        self._image_provider.clear()

    @Slot(int, int, int, int, int)
    def confirmRegion(self, screen_index: int, x: int, y: int, width: int, height: int) -> None:
        image = self._images.get(screen_index)
        if image is None or width <= 0 or height <= 0:
            self.cancel()
            return
        rect = QRect(x, y, width, height).intersected(image.rect())
        if rect.width() <= 0 or rect.height() <= 0:
            self.cancel()
            return
        cropped = image.copy(rect)
        buffer = QBuffer()
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        cropped.save(buffer, "PNG")
        del cropped
        self.release()
        self.regionCaptured.emit(bytes(buffer.data()))

    @Slot()
    def cancel(self) -> None:
        self.release()
        self.cancelled.emit()
