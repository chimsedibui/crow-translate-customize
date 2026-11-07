from PySide6.QtCore import QRect, QSize
from PySide6.QtGui import QColor, QImage, QPixmap

from py_crow_tool.services import capture as capture_module
from py_crow_tool.services.capture import CaptureController, ScreenshotImageProvider


class FakeScreen:
    def __init__(self, geometry: QRect):
        self._geometry = geometry

    def geometry(self) -> QRect:
        return self._geometry

    def grabWindow(self, window):  # noqa: N802 - Qt's spelling
        pixmap = QPixmap(self._geometry.size())
        pixmap.fill(QColor("white"))
        return pixmap


class FakeApplication:
    screen_list: list[FakeScreen] = []

    @classmethod
    def screens(cls):
        return cls.screen_list


def make_controller(monkeypatch) -> tuple[CaptureController, ScreenshotImageProvider]:
    FakeApplication.screen_list = [FakeScreen(QRect(0, 0, 200, 100)), FakeScreen(QRect(-150, 0, 150, 80))]
    monkeypatch.setattr(capture_module, "QGuiApplication", FakeApplication)
    provider = ScreenshotImageProvider()
    return CaptureController(provider), provider


def served(provider: ScreenshotImageProvider, screen_index: int) -> QImage:
    return provider.requestImage(f"{screen_index}/1", QSize(), QSize())


def test_capture_serves_every_screen_to_the_overlay(qapp, monkeypatch):
    controller, provider = make_controller(monkeypatch)

    assert controller.capture_all_screens()

    assert served(provider, 0).size() == QSize(200, 100)
    assert served(provider, 1).size() == QSize(150, 80)


def test_cancel_releases_the_screen_grabs(qapp, monkeypatch):
    """A full-screen grab per monitor is tens of MB; holding it until the next hotkey
    press is memory the tray app never gave back."""
    controller, provider = make_controller(monkeypatch)
    controller.capture_all_screens()

    controller.cancel()

    assert served(provider, 0).isNull()
    assert served(provider, 1).isNull()


def test_confirm_crops_then_releases_the_screen_grabs(qapp, monkeypatch):
    controller, provider = make_controller(monkeypatch)
    captured: list[bytes] = []
    controller.regionCaptured.connect(captured.append)
    controller.capture_all_screens()

    controller.confirmRegion(0, 10, 10, 50, 40)

    assert len(captured) == 1
    assert QImage.fromData(captured[0]).size() == QSize(50, 40)
    assert served(provider, 0).isNull()


def test_a_confirm_after_release_is_treated_as_cancelled(qapp, monkeypatch):
    controller, _ = make_controller(monkeypatch)
    cancelled: list[bool] = []
    controller.cancelled.connect(lambda: cancelled.append(True))
    controller.capture_all_screens()
    controller.cancel()

    controller.confirmRegion(0, 10, 10, 50, 40)

    assert cancelled == [True, True]
