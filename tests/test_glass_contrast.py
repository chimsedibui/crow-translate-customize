"""The contrast guarantee that lets text sit on glass.

Theme.qml's palette is documented as clearing WCAG AA against the surfaces each
colour is used on. A glass surface is not one of them -- its fill is a picture of
the user's desktop -- so the guarantee is re-established at runtime by holding
the surface's luminance inside a band derived from the text.

These tests run against the shipping Theme rather than a copy of the formula,
and they are written for whichever scheme is active: in the dark scheme every
text role is the lighter of the pair and the surface gets a ceiling, in the light
scheme it gets a floor. Asserting one polarity would pass on one machine and fail
on the next.
"""

from pathlib import Path

import pytest
from PySide6.QtCore import QUrl
from PySide6.QtGui import QColor
from PySide6.QtQml import QQmlApplicationEngine

QML_DIR = Path(__file__).parents[1] / "src/py_crow_tool/qml"

PROBE = """
import QtQuick
import "{qml_dir}"

QtObject {{
    function ceiling(c) {{ return Theme.glassCeiling(c) }}
    function floor(c) {{ return Theme.glassFloor(c) }}
    function luminance(c) {{ return Theme.relativeLuminance(c) }}
    property real target: Theme._glassTarget
    property bool dark: Theme.dark
    property color ink: Theme.ink
    property color muted: Theme.muted
    property color placeholder: Theme.placeholder
    property color glassMuted: Theme.glassMuted
}}
"""


def ratio(a: float, b: float) -> float:
    hi, lo = max(a, b), min(a, b)
    return (hi + 0.05) / (lo + 0.05)


@pytest.fixture
def probe(qapp, tmp_path):
    source = tmp_path / "Probe.qml"
    source.write_text(PROBE.format(qml_dir=QML_DIR.as_uri()), encoding="utf-8")
    engine = QQmlApplicationEngine()
    warnings: list[str] = []
    engine.warnings.connect(lambda errors: warnings.extend(e.toString() for e in errors))
    engine.load(QUrl.fromLocalFile(str(source)))
    assert engine.rootObjects(), warnings
    root = engine.rootObjects()[0]
    yield root
    engine.deleteLater()


def bound_for(probe, colour) -> float:
    """The luminance limit the active scheme puts on a surface carrying `colour`."""
    return probe.ceiling(colour) if probe.property("dark") else probe.floor(colour)


def room_for(probe, colour) -> float:
    """How much of the luminance range is left for the backdrop to live in.

    This is what a text role costs the material, and it is comparable across both
    schemes: a ceiling leaves everything below it, a floor everything above.
    """
    bound = bound_for(probe, colour)
    return bound if probe.property("dark") else 1.0 - bound


def test_the_bound_it_computes_actually_clears_AA(probe):
    """The point of the whole exercise: a surface sitting exactly on the bound
    must still be legible. Asserted against the WCAG ratio rather than a
    remembered constant, so a change to the target is caught by what it does to
    legibility instead of by what it does to a number."""
    ink = probe.property("ink")
    assert ratio(probe.luminance(ink), bound_for(probe, ink)) >= 4.5


def test_the_bound_is_aimed_above_the_target_to_survive_8_bit_output(probe):
    """A bound set at exactly 4.5:1 lands half its pixels a rounding step under
    it -- measured 4.47:1 to 4.52:1 on rendered output with no headroom. The band
    aims higher by at least one quantisation step near the bound."""
    ink = probe.property("ink")
    assert ratio(probe.luminance(ink), bound_for(probe, ink)) > 4.5
    assert probe.property("target") == pytest.approx(4.65)


def test_white_and_black_sit_at_the_extremes_of_the_band(probe):
    """White is the easiest text to keep legible and black the hardest, or the
    other way round; either way the two bracket everything between them."""
    white, black = QColor("#ffffff"), QColor("#000000")
    assert probe.luminance(white) == pytest.approx(1.0, abs=1e-6)
    assert probe.luminance(black) == pytest.approx(0.0, abs=1e-6)
    assert probe.ceiling(white) == pytest.approx(1.05 / 4.65 - 0.05, rel=1e-6)
    assert probe.floor(black) == pytest.approx(4.65 * 0.05 - 0.05, rel=1e-6)


def test_secondary_text_roles_cannot_survive_on_glass(probe):
    """Why the popup promotes every secondary role to ink.

    The band is set by the weakest text placed on the surface, not the primary
    one, and the weaker roles demand a surface so close to one end of the range
    that no backdrop is left to see. That measurement is what decided the popup's
    hierarchy comes from size rather than lightness -- so it is asserted here,
    not just written down.
    """
    ink_room = room_for(probe, probe.property("ink"))
    muted_room = room_for(probe, probe.property("muted"))
    placeholder_room = room_for(probe, probe.property("placeholder"))

    assert ink_room > 0.1, "ink has to leave the material something to show"
    assert muted_room < ink_room / 2
    assert placeholder_room < muted_room


def test_a_bound_outside_the_range_means_that_text_belongs_on_an_opaque_surface(probe):
    """Some roles have no answer at all: no surface of any luminance makes them
    clear AA. GlassSurface hands such a bound to the shader unchanged, and the
    shader clamps into an empty band -- so the caller has to keep them off glass,
    which is what QuickTranslatePopup does with its notice and error chips."""
    for role in ("muted", "placeholder"):
        bound = bound_for(probe, probe.property(role))
        # Either impossible outright, or possible only on a surface with almost
        # no room left. Both mean the same thing for the design.
        assert bound <= 0.0 or bound >= 1.0 or room_for(probe, probe.property(role)) < 0.35


def test_the_secondary_ink_for_glass_clears_the_3_to_1_UI_threshold(probe):
    """Icons and borders are held to 3:1, not 4.5:1 -- but `muted` misses even that.

    Against a surface sitting on the bound, muted manages about 2.1:1, so an icon
    drawn in it is not a quiet icon but an invisible one. Theme.glassMuted is the
    dimmer step that still clears the threshold, and this is what keeps it honest
    if either the palette or the target moves.
    """
    ink = probe.property("ink")
    bound = bound_for(probe, ink)
    glass_muted = probe.property("glassMuted")
    muted = probe.property("muted")

    assert ratio(probe.luminance(glass_muted), bound) >= 3.0
    assert ratio(probe.luminance(muted), bound) < 3.0, \
        "if muted ever clears 3:1 on glass, glassMuted has stopped earning its keep"
    # Still a step down from ink, or it would not be doing muted's job.
    assert ratio(probe.luminance(glass_muted), bound) < ratio(probe.luminance(ink), bound)
