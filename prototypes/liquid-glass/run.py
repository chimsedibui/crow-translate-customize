"""Liquid-glass prototype. Standalone -- it imports nothing from the app.

    .venv\\Scripts\\python.exe prototypes\\liquid-glass\\run.py

Two questions it exists to answer:

  1. In-app, over our own content, can Qt draw glass that actually refracts?
     Drag the card over the paragraphs and watch the rim.
  2. Over the desktop, where Qt cannot read the pixels behind the window, how
     close does the Windows compositor get? The two popup buttons.
"""

from __future__ import annotations

import sys
from pathlib import Path

import os

from PySide6.QtCore import QObject, Qt, QTimer, QUrl, Slot
from PySide6.QtGui import QGuiApplication, QImage
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickImageProvider
from PySide6.QtQuickControls2 import QQuickStyle

sys.path.insert(0, str(Path(__file__).parent))
import backdrop  # noqa: E402


class ScreenProvider(QQuickImageProvider):
    """Holds the most recent desktop grab so QML can load it as a texture."""

    def __init__(self) -> None:
        super().__init__(QQuickImageProvider.Image)
        self.image = QImage()

    def requestImage(self, image_id: str, size, requested_size) -> QImage:
        return self.image


class ScreenGrab(QObject):
    """Captures the desktop region a glass window is about to cover.

    This is the piece that makes glass possible over other applications at all.
    Nothing in the process can read the pixels behind a window while it is up,
    but everything can read the screen before it goes up -- so the backdrop is
    a still, taken the instant before the popup appears.
    """

    def __init__(self, provider: ScreenProvider) -> None:
        super().__init__()
        self._provider = provider
        self._serial = 0

    @Slot(int, int, int, int, result=str)
    def capture(self, x: int, y: int, w: int, h: int) -> str:
        screen = QGuiApplication.primaryScreen()
        pixmap = screen.grabWindow(0, x, y, w, h)
        self._provider.image = pixmap.toImage()
        self._serial += 1
        # The serial is a cache-buster: QML would otherwise reuse the first grab.
        return f"image://screengrab/{self._serial}"


class Backdrop(QObject):
    """QML-side handle on the DWM calls."""

    @Slot(QObject, str, bool, result=str)
    def applyTo(self, window: QObject, kind: str, dark: bool) -> str:
        win_id = window.winId() if hasattr(window, "winId") else None
        if win_id is None:
            return "no HWND"
        results = backdrop.apply(int(win_id), kind, dark=dark)
        return "  ".join(f"{k}={v:#010x}" if isinstance(v, int) else f"{k}={v}"
                         for k, v in results.items())


def main() -> int:
    app = QGuiApplication(sys.argv)
    QQuickStyle.setStyle("FluentWinUI3")

    engine = QQmlApplicationEngine()
    # Held in a local for the lifetime of exec(): setContextProperty stores a
    # bare pointer, so letting Python collect this would dangle it.
    bridge = Backdrop()
    engine.rootContext().setContextProperty("backdrop", bridge)
    engine.rootContext().setContextProperty("autoPopup", os.environ.get("PROTO_POPUP", ""))

    provider = ScreenProvider()
    engine.addImageProvider("screengrab", provider)
    grabber = ScreenGrab(provider)
    engine.rootContext().setContextProperty("screenGrab", grabber)

    qml_dir = Path(__file__).parent / "qml"
    engine.addImportPath(str(qml_dir))
    engine.load(QUrl.fromLocalFile(str(qml_dir / "Lab.qml")))
    if not engine.rootObjects():
        return 1

    # PROTO_SHOT=<path> grabs the scene graph itself rather than the screen.
    # SetForegroundWindow is refused to a process that is not already in front,
    # so a screen grab photographs whatever happens to be on top instead; a
    # grabWindow re-renders our own scene and always gets the shader output.
    shot = os.environ.get("PROTO_SHOT")
    screen_shot = os.environ.get("PROTO_SHOT_SCREEN")
    window = engine.rootObjects()[0]

    if shot:
        def grab() -> None:
            window.grabWindow().save(shot)
            print(f"saved {shot}", flush=True)
            app.quit()

        QTimer.singleShot(2500, grab)

    if screen_shot:
        # A DWM backdrop is composited BENEATH our window, so it is not in our
        # scene graph and grabWindow cannot see it. Only a picture of the actual
        # desktop shows whether the compositor did anything.
        # raise() alone loses to whatever the user had in front, and the capture
        # then photographs that instead. Pin the window for the duration.
        window.setFlag(Qt.WindowStaysOnTopHint, True)
        window.raise_()
        window.requestActivate()

        def grab_screen() -> None:
            QGuiApplication.primaryScreen().grabWindow(0).save(screen_shot)
            print(f"saved {screen_shot}", flush=True)
            app.quit()

        QTimer.singleShot(3500, grab_screen)

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
