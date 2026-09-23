from PySide6.QtCore import QRect, QSize
from PySide6.QtGui import QImage, QPixmap

from py_crow_tool.services.backdrop import BackdropController, BackdropImageProvider


class FakeScreen:
    """Stands in for a QScreen. Records the offset it was asked to grab at, which
    is the part that goes wrong on a second monitor."""

    def __init__(self, geometry: QRect, pixmap: QPixmap | None = None):
        self._geometry = geometry
        self._pixmap = pixmap if pixmap is not None else QPixmap(10, 10)
        self.grabs: list[tuple[int, int, int, int]] = []

    def geometry(self) -> QRect:
        return self._geometry

    def grabWindow(self, window, x, y, width, height):  # noqa: N802 - Qt's spelling
        self.grabs.append((x, y, width, height))
        return self._pixmap


def controller_on(screen) -> tuple[BackdropController, BackdropImageProvider]:
    provider = BackdropImageProvider()
    controller = BackdropController(provider)
    controller.screen_at = lambda x, y: screen
    return controller, provider


def test_capture_returns_a_url_that_changes_every_time(qapp):
    pixmap = QPixmap(40, 30)
    pixmap.fill()
    controller, _ = controller_on(FakeScreen(QRect(0, 0, 1920, 1080), pixmap))

    first = controller.capture(10, 20, 40, 30)
    second = controller.capture(10, 20, 40, 30)

    assert first.startswith("image://backdrop/")
    # QML's Image only refetches when the source string changes, so two identical
    # URLs would leave every popup after the first showing the first backdrop.
    assert first != second


def test_capture_offsets_the_grab_by_the_screens_own_origin(qapp):
    pixmap = QPixmap(40, 30)
    pixmap.fill()
    screen = FakeScreen(QRect(1920, 0, 1920, 1080), pixmap)
    controller, _ = controller_on(screen)

    controller.capture(2000, 150, 40, 30)

    # grabWindow's offset is relative to the screen, not the virtual desktop. A
    # popup 80px into the second monitor must grab 80px into that monitor, not
    # 2000px into the first one.
    assert screen.grabs == [(80, 150, 40, 30)]


def test_a_failed_grab_reports_no_backdrop_rather_than_an_empty_image(qapp):
    controller, provider = controller_on(FakeScreen(QRect(0, 0, 1920, 1080), QPixmap()))

    assert controller.capture(10, 20, 40, 30) == ""
    # The caller reads "" as "no glass" and falls back to an opaque surface. Had
    # this handed back a URL, the popup would have rendered an empty hole.
    assert provider.requestImage("1", None, None).isNull()


def test_a_zero_sized_rect_never_touches_the_screen(qapp):
    screen = FakeScreen(QRect(0, 0, 1920, 1080))
    controller, _ = controller_on(screen)

    assert controller.capture(10, 20, 0, 30) == ""
    assert controller.capture(10, 20, 40, -1) == ""
    assert screen.grabs == []


def test_the_provider_serves_the_latest_grab_and_reports_its_size(qapp):
    first = QPixmap(40, 30)
    first.fill()
    screen = FakeScreen(QRect(0, 0, 1920, 1080), first)
    controller, provider = controller_on(screen)
    controller.capture(0, 0, 40, 30)

    size = QSize()
    image = provider.requestImage("1", size, None)

    assert isinstance(image, QImage)
    assert (image.width(), image.height()) == (40, 30)
    assert (size.width(), size.height()) == (40, 30)
