"""Can ANY Qt Quick window on Windows show a compositor blur of what is behind it?

The acrylic popup came back S_OK on every DWM call and still rendered as a flat
grey slab, so this isolates the question. It paints its own hard-edged colour
bars full-screen, drops four differently-configured windows on top of them, and
asks each one for a blur. Colour bars matter: over a white document every
failure mode looks like "a grey panel", and over a blur they look like smeared
stripes. The tint is fully transparent so nothing can hide a blur that worked.

    .venv\\Scripts\\python.exe prototypes\\liquid-glass\\test_backdrop.py out.png

WS_EX_LAYERED is the thing to watch: layered windows are composited by a path
that ignores DWM system backdrops. WS_EX_NOREDIRECTIONBITMAP is what a
DirectComposition swapchain sets, and is how WinUI 3 earns Mica and Acrylic.
"""

from __future__ import annotations

import ctypes
import sys
from ctypes import wintypes
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QGuiApplication
from PySide6.QtQuick import QQuickView

sys.path.insert(0, str(Path(__file__).parent))
import backdrop  # noqa: E402

WS_EX_LAYERED = 0x00080000
WS_EX_NOREDIRECTIONBITMAP = 0x00200000
WS_EX_TOOLWINDOW = 0x00000080
GWL_EXSTYLE = -20

BARS_QML = """
import QtQuick
Item {
    Row {
        anchors.fill: parent
        Repeater {
            model: ["#e0483c", "#f0b429", "#2bb3a1", "#7a5cf0", "#ffffff", "#101018"]
            Rectangle { width: parent.width / 6; height: parent.height; color: modelData }
        }
    }
}
"""

PANEL_QML = """
import QtQuick
Rectangle {
    color: "transparent"
    Rectangle {
        anchors.fill: parent
        color: "#00000000"
        border.color: "#a0ffffff"; border.width: 2; radius: 10
    }
    Text {
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom; anchors.bottomMargin: 10
        width: parent.width - 24
        horizontalAlignment: Text.AlignHCenter
        wrapMode: Text.Wrap
        color: "white"; font.pixelSize: 13; font.bold: true
        style: Text.Outline; styleColor: "#000000"
        text: variantLabel
    }
}
"""


def ex_style(hwnd: int) -> int:
    user32 = ctypes.windll.user32
    user32.GetWindowLongPtrW.restype = ctypes.c_longlong
    user32.GetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int]
    return user32.GetWindowLongPtrW(wintypes.HWND(hwnd), GWL_EXSTYLE)


def describe(style: int) -> str:
    bits = []
    if style & WS_EX_LAYERED:
        bits.append("LAYERED")
    if style & WS_EX_NOREDIRECTIONBITMAP:
        bits.append("NOREDIRECTIONBITMAP")
    if style & WS_EX_TOOLWINDOW:
        bits.append("TOOLWINDOW")
    return " | ".join(bits) or "(none of interest)"


_tmp: list[Path] = []


def view_for(qml: str, name: str, color: QColor, geom: tuple[int, int, int, int],
             label: str = "") -> QQuickView:
    view = QQuickView()
    view.setFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
    view.setColor(color)
    view.rootContext().setContextProperty("variantLabel", label)
    view.setResizeMode(QQuickView.SizeRootObjectToView)
    path = Path(__file__).parent / f"_t_{name}.qml"
    path.write_text(qml, encoding="utf-8")
    _tmp.append(path)
    view.setSource(path.as_uri())
    view.setGeometry(*geom)
    view.show()
    return view


def main() -> int:
    app = QGuiApplication(sys.argv)
    screen = app.primaryScreen().geometry()

    bars = view_for(BARS_QML, "bars", QColor(0, 0, 0),
                    (0, 0, screen.width(), 420))

    # tint alpha 0: a blur that works has nothing laid over it to hide behind.
    clear_tint = 0x00000000

    variants = [
        # The control. If the bars are visible through this one and not through
        # the others, the blur calls are not merely failing -- they are turning a
        # window that WAS see-through into an opaque one.
        ("E transparent, no call at all", None, "none"),
        ("A transparent + DWM acrylic", None, "dwm-acrylic"),
        ("B opaque black + DWM acrylic", QColor(0, 0, 0), "dwm-acrylic"),
        ("C transparent + legacy ACRYLIC", None, "accent-acrylic"),
        ("D transparent + legacy BLUR", None, "accent-blur"),
    ]

    width, gap = 250, 30
    total = len(variants) * width + (len(variants) - 1) * gap
    left = (screen.width() - total) // 2

    views = []
    for i, (label, color, _) in enumerate(variants):
        geom = (left + i * (width + gap), 90, width, 240)
        views.append(view_for(PANEL_QML, f"v{i}",
                              color if color else QColor(0, 0, 0, 0), geom, label))

    def report() -> None:
        print(f"bars window exstyle: 0x{ex_style(int(bars.winId())) & 0xFFFFFFFF:08x}\n")
        for view, (label, _, how) in zip(views, variants):
            hwnd = int(view.winId())
            if how == "none":
                res = {"called": "nothing"}
            elif how.startswith("dwm"):
                res = backdrop.apply(hwnd, how.split("-")[1], dark=True)
            else:
                res = backdrop.accent(hwnd, how.split("-")[1], tint=clear_tint)
            style = ex_style(hwnd)
            print(label)
            print(f"  exstyle : 0x{style & 0xFFFFFFFF:08x}  {describe(style)}")
            print("  result  : " + "  ".join(f"{k}={v}" for k, v in res.items()))
            print()

        shot = Path(sys.argv[1]) if len(sys.argv) > 1 else None

        def finish() -> None:
            if shot:
                QGuiApplication.primaryScreen().grabWindow(0).save(str(shot))
                print(f"saved {shot}", flush=True)
            app.quit()

        QTimer.singleShot(2000, finish)

    QTimer.singleShot(1500, report)
    code = app.exec()
    for path in _tmp:
        path.unlink(missing_ok=True)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
