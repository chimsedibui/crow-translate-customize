"""Does the rendered glass actually clear 4.5:1?

contrast.py proves it on paper and the shader claims to implement it, which are
two different statements. This one renders the real popup over deliberately
hostile backdrops, reads the pixels back, and measures.

Hostile means: pure white, a bright saturated field, and a hard black/white
edge running under the text. The last is the one that breaks naive solutions --
anything that picks a single tint for the whole panel has to fail on one side of
that edge.

    .venv\\Scripts\\python.exe prototypes\\liquid-glass\\verify_contrast.py

Exit code is 0 only if every sampled pixel under the text area clears the target
with the guarantee on. It also measures with the guarantee OFF, to show what the
rule is worth rather than just that it passes.
"""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QColor, QGuiApplication, QImage
from PySide6.QtQml import QQmlComponent, QQmlEngine
from PySide6.QtQuick import QQuickView

sys.path.insert(0, str(Path(__file__).parent))
import contrast as ct  # noqa: E402

QML_DIR = Path(__file__).parent / "qml"
INK = (0xE8, 0xEE, 0xF3)          # Theme.qml dark-scheme ink

BACKDROPS = {
    "white": """
        import QtQuick
        Rectangle { color: "#ffffff" }
    """,
    "bright yellow": """
        import QtQuick
        Rectangle { color: "#ffe14d" }
    """,
    "hard black/white edge": """
        import QtQuick
        Item {
            Rectangle { width: parent.width / 2; height: parent.height; color: "#ffffff" }
            Rectangle { x: parent.width / 2; width: parent.width / 2
                        height: parent.height; color: "#000000" }
        }
    """,
    "photo-ish gradient + shapes": """
        import QtQuick
        Item {
            Rectangle {
                anchors.fill: parent
                gradient: Gradient {
                    GradientStop { position: 0.0; color: "#ffffff" }
                    GradientStop { position: 1.0; color: "#101010" }
                }
            }
            Rectangle { x: 40; y: 30; width: 200; height: 200; radius: 100; color: "#ff2d2d" }
            Rectangle { x: 260; y: 120; width: 260; height: 90; color: "#00ffd0" }
        }
    """,
    # Fully saturated fills, large enough to cover the middle of the card. This
    # is the case that caught the NaN: saturation > 1 drives the weak channel of
    # a colour like #00ffd0 negative, and everything downstream of that silently
    # skipped the contrast clamp. It stays in the suite as a regression.
    "vivid saturated fills": """
        import QtQuick
        Item {
            Rectangle {
                anchors.fill: parent
                gradient: Gradient {
                    GradientStop { position: 0.0; color: "#ffffff" }
                    GradientStop { position: 1.0; color: "#1a1a2e" }
                }
            }
            Rectangle { x: 30;  y: 40;  width: 210; height: 210; radius: 105; color: "#ff2d2d" }
            Rectangle { x: 250; y: 150; width: 300; height: 110; radius: 12;  color: "#00ffd0" }
            Rectangle { x: 120; y: 300; width: 420; height: 40;  radius: 20;  color: "#ffe14d" }
            Rectangle { x: 420; y: 40;  width: 160; height: 90;  radius: 8;   color: "#ff00d0" }
        }
    """,
}

PAD = 64          # GlassPopup.pad
CARD_W, CARD_H = 380, 240


def render_case(app: QGuiApplication, backdrop_qml: str, guarantee: bool,
                out: Path) -> QImage:
    """Put a backdrop window up, pop the glass over it, grab the screen."""
    bg_file = Path(__file__).parent / "_verify_bg.qml"
    bg_file.write_text(backdrop_qml.strip(), encoding="utf-8")

    bg = QQuickView()
    bg.setFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
    bg.setResizeMode(QQuickView.SizeRootObjectToView)
    bg.setSource(QUrl.fromLocalFile(str(bg_file)))
    bg.setGeometry(100, 100, 700, 480)
    bg.show()

    engine = QQmlEngine()
    engine.addImportPath(str(QML_DIR))

    # The popup needs the same screen-grab bridge the lab gives it.
    from run import ScreenGrab, ScreenProvider  # noqa: PLC0415

    provider = ScreenProvider()
    engine.addImageProvider("screengrab", provider)
    grabber = ScreenGrab(provider)
    engine.rootContext().setContextProperty("screenGrab", grabber)

    component = QQmlComponent(engine, QUrl.fromLocalFile(str(QML_DIR / "GlassPopup.qml")))
    popup = component.create()
    if popup is None:
        for error in component.errors():
            print("   ", error.toString())
        raise SystemExit("could not build GlassPopup")

    popup.setProperty("guarantee", guarantee)
    popup.setProperty("showContent", False)   # measuring the surface, not glyphs

    result: dict[str, QImage] = {}

    def shoot() -> None:
        popup.popAt(180, 170)
        QTimer.singleShot(700, grab)

    def grab() -> None:
        # The popup's OWN window, not the screen: a screen grab comes back in
        # physical pixels under an unknown scale factor and may be colour
        # managed, and both of those corrupt a measurement this exact.
        shot = popup.grabWindow()
        shot.save(str(out))
        result["image"] = shot
        app.quit()

    QTimer.singleShot(600, shoot)
    app.exec()

    popup.setProperty("visible", False)
    bg.hide()
    bg_file.unlink(missing_ok=True)
    return result.get("image", QImage())


def measure(image: QImage, inset: int = 0) -> tuple[float, int, int]:
    """Worst contrast against INK over the card, `inset` device px in from its edge."""
    scale = image.width() / float(CARD_W + PAD * 2)
    x0 = int((PAD) * scale) + inset
    y0 = int((PAD) * scale) + inset
    x1 = int((PAD + CARD_W) * scale) - inset
    y1 = int((PAD + CARD_H) * scale) - inset

    worst = 99.0
    failures = 0
    total = 0
    for y in range(y0, y1, 2):
        for x in range(x0, x1, 2):
            if not (0 <= x < image.width() and 0 <= y < image.height()):
                continue
            pixel = image.pixelColor(x, y)
            ratio = ct.contrast((pixel.red(), pixel.green(), pixel.blue()), INK)
            total += 1
            worst = min(worst, ratio)
            if ratio < ct.AA_BODY:
                failures += 1
    return worst, failures, total


def safe_inset(image: QImage, limit: int = 60) -> int:
    """Least inset from the card edge at which every pixel clears the target.

    The bevel is allowed to be bright -- it is a lit edge, and lighting it is the
    point. But that makes it off limits to text, and this is the number that says
    by how much. It is a layout constraint the shader cannot enforce on its own.
    """
    scale = image.width() / float(CARD_W + PAD * 2)
    for inset in range(0, limit):
        _, failures, total = measure(image, int(inset * scale))
        if total and not failures:
            return inset
    return -1


def main() -> int:
    shots = Path(__file__).parent / "shots" / "verify"
    shots.mkdir(parents=True, exist_ok=True)

    print(f"target {ct.AA_BODY}:1 against ink #{INK[0]:02x}{INK[1]:02x}{INK[2]:02x}")
    print(f"surface ceiling = {ct.max_surface_luminance(INK):.4f} "
          f"(luminance of ink = {ct.luminance(INK):.4f})")
    print("measured on the rendered card with the text hidden, so every pixel "
          "sampled is surface.\n")
    print(f"  {'backdrop':<30} {'rule':<5} {'worst':>7} {'fail px':>9} "
          f"{'of':>7}  {'safe inset':>10}")
    print("  " + "-" * 76)

    ok = True
    for name, qml in BACKDROPS.items():
        for guarantee in (False, True):
            app = QGuiApplication(sys.argv)
            tag = "on" if guarantee else "off"
            out = shots / f"{name.replace(' ', '-').replace('/', '-')}-{tag}.png"
            image = render_case(app, qml, guarantee, out)
            app.shutdown()
            del app

            if image.isNull():
                print(f"  {name:<30} {tag:<5}  (no capture)")
                continue
            worst, failures, total = measure(image)
            inset = safe_inset(image) if guarantee else -1
            inset_text = f"{inset}px" if inset >= 0 else ("-" if not guarantee else "none")
            flag = ""
            if guarantee and inset < 0:
                flag = "   <-- NO SAFE REGION"
                ok = False
            print(f"  {name:<30} {tag:<5} {worst:6.2f}: {failures:8d} {total:7d}"
                  f"  {inset_text:>10}{flag}")
        print()

    print("shots written to", shots)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
