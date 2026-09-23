from __future__ import annotations

from PySide6.QtCore import QObject, QPoint, Signal, Slot
from PySide6.QtGui import QGuiApplication, QImage
from PySide6.QtQuick import QQuickImageProvider


class BackdropImageProvider(QQuickImageProvider):
    """Serves the desktop grab a glass window is about to sit on, as
    image://backdrop/<generation>."""

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


class BackdropController(QObject):
    """Captures what is behind a window the instant before it appears.

    Nothing in this process can read the pixels behind a window while it is up.
    Qt 6 exposes no compositor backdrop at all, and the two Windows APIs that
    look like they would do it -- DWMWA_SYSTEMBACKDROP_TYPE and the legacy accent
    policy -- do something worse than fail: both report success and turn a
    window that WAS see-through into an opaque slab. Measurements are in
    prototypes/liquid-glass/README.md.

    So the backdrop is a still, grabbed before the window shows. It is correct at
    that moment and does not track anything moving underneath, which is a fair
    trade for a popup that lives a few seconds over a document somebody is
    reading, and the wrong trade for a window that stays open.
    """

    captured = Signal()

    def __init__(self, image_provider: BackdropImageProvider, parent: QObject | None = None):
        super().__init__(parent)
        self._image_provider = image_provider
        self._generation = 0

    def screen_at(self, x: int, y: int):
        """The screen a global point falls on. Overridable so tests can hand in a
        stub: an offscreen QPA has no grabbable screen, and the interesting cases
        here are the second monitor and the failed grab."""
        return QGuiApplication.screenAt(QPoint(x, y)) or QGuiApplication.primaryScreen()

    @Slot(int, int, int, int, result=str)
    def capture(self, x: int, y: int, width: int, height: int) -> str:
        """Grab the desktop under a rect given in global coordinates.

        Returns the provider URL to hand to an Image, or "" when the grab failed
        -- GlassSurface treats that as "no glass" and falls back to an opaque
        surface rather than rendering an empty hole.
        """
        if width <= 0 or height <= 0:
            return ""
        screen = self.screen_at(x, y)
        if screen is None:
            return ""
        # grabWindow's offset is relative to the screen being grabbed, not to the
        # virtual desktop, so a popup on a second monitor would otherwise capture
        # a region from the wrong part of the first one.
        origin = screen.geometry().topLeft()
        pixmap = screen.grabWindow(0, x - origin.x(), y - origin.y(), width, height)
        if pixmap.isNull():
            return ""
        self._image_provider.set_image(pixmap.toImage())
        self._generation += 1
        self.captured.emit()
        # Same cache-buster as the capture overlay: QML's Image only refetches
        # from a provider when its "source" string actually changes, so without
        # the counter every popup after the first would show the first backdrop.
        return f"image://backdrop/{self._generation}"
