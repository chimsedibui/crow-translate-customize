"""What glass costs the real palette.

Reads the colours straight out of the app's Theme.qml rather than copying them,
so this report cannot quietly drift away from the thing it is describing, and
prints the scrim each text role needs -- blind, then measured against real
desktop backdrops cropped from an actual screenshot.

    .venv\\Scripts\\python.exe prototypes\\liquid-glass\\report_contrast.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from PySide6.QtGui import QGuiApplication, QImage

sys.path.insert(0, str(Path(__file__).parent))
import contrast as ct  # noqa: E402

THEME = Path(__file__).parents[2] / "src" / "py_crow_tool" / "qml" / "Theme.qml"
SHOTS = Path(__file__).parent / "shots"

COLOR_RE = re.compile(
    r'readonly property color (\w+):\s*dark \? "(#[0-9a-fA-F]{6,8})" : "(#[0-9a-fA-F]{6,8})"')


def theme_colors() -> dict[str, tuple[str, str]]:
    """{name: (dark_value, light_value)} from the shipping theme."""
    text = THEME.read_text(encoding="utf-8")
    return {m.group(1): (m.group(2), m.group(3)) for m in COLOR_RE.finditer(text)}


def backdrop_from(path: Path, box: tuple[int, int, int, int]) -> list[ct.RGB]:
    image = QImage(str(path))
    if image.isNull():
        return []
    return ct.sample_backdrop(image.copy(*box))


def row(label: str, solution: ct.Solution) -> str:
    if not solution.feasible:
        return f"  {label:<34} IMPOSSIBLE even opaque (best {solution.achieved:.2f}:1)"
    return (f"  {label:<34} scrim {solution.alpha * 100:5.1f}%"
            f"   glass left {solution.glass_left * 100:5.1f}%"
            f"   {solution.achieved:.2f}:1")


def main() -> int:
    QGuiApplication(sys.argv)  # QImage needs a GUI application for some formats

    colors = theme_colors()
    if not colors:
        print(f"could not parse {THEME}")
        return 1

    dark_ink = {k: ct.hex_rgb(v[0]) for k, v in colors.items()}
    light_ink = {k: ct.hex_rgb(v[1]) for k, v in colors.items()}

    print(f"Theme.qml: {len(colors)} colour roles parsed\n")
    print("Text roles, and what each needs from a scrim it cannot see through.")
    print("'glass left' is the share of the backdrop still visible -- the thing")
    print("a scrim spends. Target is WCAG AA 4.5:1 for body text.\n")

    # The scrim is the theme's own raised surface: the scrim is not a new colour
    # in the system, it is the surface the text already expects, made partial.
    roles = ["ink", "muted", "placeholder"]

    print("BLIND -- backdrop unknown, must hold against black AND white")
    print("(this is the floor for any surface we cannot measure)\n")
    for scheme, inks in (("dark", dark_ink), ("light", light_ink)):
        scrim = inks["raised"]
        print(f" {scheme} scheme, scrim = raised {colors['raised'][0 if scheme == 'dark' else 1]}")
        for role in roles:
            if role not in inks:
                continue
            print(row(role, ct.blind(inks[role], scrim)))
        print()

    # Real backdrops, cropped out of the desktop capture the prototype took.
    desktop = SHOTS / "02-desktop-glass-popup.png"
    full = SHOTS / "01-in-app-glass.png"
    cases: list[tuple[str, list[ct.RGB]]] = [
        ("pure white", [(255, 255, 255)]),
        ("pure black", [(0, 0, 0)]),
        ("mid grey 50%", [(128, 128, 128)]),
    ]
    if desktop.exists():
        cases.append(("real: glass popup capture", backdrop_from(desktop, (0, 0, 1040, 600))))
    if full.exists():
        cases.append(("real: colourful app content", backdrop_from(full, (0, 0, 880, 700))))

    print("MEASURED -- backdrop captured before the window shows\n")
    for scheme, inks in (("dark", dark_ink), ("light", light_ink)):
        print(f" {scheme} scheme")
        for name, backdrop in cases:
            if not backdrop:
                continue
            solution = ct.solve(inks["ink"], inks["raised"], backdrop)
            print(row(f"ink over {name}", solution))
        print()

    print("ADAPTIVE POLARITY -- text allowed to flip with the backdrop")
    print("(scheme names are the theme's: 'dark' = light text, 'light' = dark text)\n")
    inks = {"dark": dark_ink["ink"], "light": light_ink["ink"]}
    scrims = {"dark": dark_ink["raised"], "light": light_ink["raised"]}
    for name, backdrop in cases:
        if not backdrop:
            continue
        scheme, solution = ct.choose(inks, scrims, backdrop)
        print(row(f"{name} -> {scheme} scheme", solution))

    # ---------------------------------------------------------------- treatments
    print("\n" + "=" * 78)
    print("SCRIM vs LUMINANCE CAP")
    print("Both reach 4.5:1. The question is what each leaves of the backdrop.")
    print("'untouched' = pixels not altered at all; 'chroma' = colour surviving;")
    print("'texture' = luminance variation surviving.\n")

    ink = dark_ink["ink"]          # light text, the cheaper direction
    scrim_color = dark_ink["raised"]
    ceiling = ct.max_surface_luminance(ink)
    print(f" dark scheme, ink {colors['ink'][0]}  ->  surface must stay below "
          f"luminance {ceiling:.4f}\n")

    header = (f"  {'backdrop':<30} {'treatment':<16} "
              f"{'untouched':>10} {'chroma':>8} {'texture':>8}")
    print(header)
    print("  " + "-" * (len(header) - 2))

    for name, backdrop in cases:
        if not backdrop or len(backdrop) < 4:
            continue
        solution = ct.solve(ink, scrim_color, backdrop)
        scrimmed = [ct.composite(scrim_color, solution.alpha, b) for b in backdrop]
        capped = [ct.cap_luminance(b, ceiling) for b in backdrop]

        for label, treated in (("scrim", scrimmed), ("luminance cap", capped)):
            keep = ct.preservation(backdrop, treated)
            worst = min(ct.contrast(ink, t) for t in treated)
            flag = "" if worst >= ct.AA_BODY - 0.01 else f"  FAILS {worst:.2f}:1"
            print(f"  {name:<30} {label:<16} {keep.untouched * 100:9.1f}% "
                  f"{keep.chroma_kept * 100:7.1f}% {keep.texture_kept * 100:7.1f}%{flag}")
        print()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
