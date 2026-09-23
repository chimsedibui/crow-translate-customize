"""How much scrim does glass need before text on it is legible?

Glass breaks the promise Theme.qml makes. That palette is documented as clearing
WCAG AA "against the surfaces each colour is actually used on" -- which works
because those surfaces are ours and known. Put the same text on glass and the
surface becomes a photograph of somebody's desktop, so the guarantee has to be
re-established at runtime, against a backdrop nobody chose.

The lever is a scrim: a tinted layer between the backdrop and the text. Opaque
enough and contrast is certain; opaque enough and the glass is gone. So the
question is not "does a scrim work" but "what is the LEAST scrim that still
proves the guarantee", which is what this module solves.

Two regimes:

  blind()    -- nothing known about the backdrop. Must hold for every possible
                one, so it solves against pure black and pure white. This is the
                floor for a surface we cannot measure.

  measured() -- the backdrop is in hand (the popup captures it before it shows).
                Solves against the actual pixels, and comes out dramatically
                cheaper than blind() on any real backdrop.

Compositing is modelled in sRGB, per channel, because that is how the GPU blends
what this shader writes. Doing the algebra in linear light would give a prettier
derivation and the wrong number.
"""

from __future__ import annotations

from dataclasses import dataclass

RGB = tuple[float, float, float]

# WCAG 2.1 thresholds.
AA_BODY = 4.5      # text below 18.66px regular
AA_LARGE = 3.0     # large text, and non-text UI components


def _linear(channel: float) -> float:
    c = channel / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def luminance(rgb: RGB) -> float:
    """WCAG relative luminance."""
    r, g, b = (_linear(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a: RGB, b: RGB) -> float:
    la, lb = luminance(a), luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def hex_rgb(value: str) -> RGB:
    value = value.lstrip("#")
    if len(value) == 8:  # AARRGGBB, as QML writes it
        value = value[2:]
    return (int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16))


def composite(scrim: RGB, alpha: float, backdrop: RGB) -> RGB:
    """Source-over, per channel, in sRGB -- what the GPU actually does."""
    return tuple(alpha * s + (1.0 - alpha) * b for s, b in zip(scrim, backdrop))


@dataclass(frozen=True)
class Solution:
    alpha: float
    achieved: float          # worst contrast across the backdrops considered
    feasible: bool           # False when even alpha=1 misses the target
    scrim: RGB
    text: RGB

    @property
    def glass_left(self) -> float:
        """How much of the backdrop still shows. The number to minimise losing."""
        return 1.0 - self.alpha


def _worst_contrast(text: RGB, scrim: RGB, alpha: float, backdrops: list[RGB]) -> float:
    return min(contrast(text, composite(scrim, alpha, b)) for b in backdrops)


def solve(text: RGB, scrim: RGB, backdrops: list[RGB], target: float = AA_BODY,
          steps: int = 40) -> Solution:
    """Least alpha whose worst case over `backdrops` still clears `target`.

    Worst-case contrast rises monotonically with alpha -- at alpha=1 every
    backdrop composites to the scrim itself -- so a bisection is exact to within
    2**-steps and cannot land on a local optimum.
    """
    if _worst_contrast(text, scrim, 1.0, backdrops) < target:
        return Solution(1.0, _worst_contrast(text, scrim, 1.0, backdrops),
                        False, scrim, text)
    if _worst_contrast(text, scrim, 0.0, backdrops) >= target:
        return Solution(0.0, _worst_contrast(text, scrim, 0.0, backdrops),
                        True, scrim, text)

    lo, hi = 0.0, 1.0
    for _ in range(steps):
        mid = (lo + hi) / 2.0
        if _worst_contrast(text, scrim, mid, backdrops) >= target:
            hi = mid
        else:
            lo = mid
    return Solution(hi, _worst_contrast(text, scrim, hi, backdrops), True, scrim, text)


def blind(text: RGB, scrim: RGB, target: float = AA_BODY) -> Solution:
    """The floor for a backdrop that cannot be measured.

    Black and white bracket every possible backdrop: compositing is per-channel
    and monotonic, so no colour between them can produce a channel value outside
    the range those two produce.
    """
    return solve(text, scrim, [(0, 0, 0), (255, 255, 255)], target)


def sample_backdrop(image, grid: int = 24) -> list[RGB]:
    """Downsample a QImage to a grid of representative pixels.

    A grid rather than a mean: an average hides the one bright window behind the
    popup that is about to swallow a line of text, and that pixel is exactly the
    one the guarantee has to survive.
    """
    width, height = image.width(), image.height()
    if width == 0 or height == 0:
        return [(128, 128, 128)]
    out: list[RGB] = []
    for row in range(grid):
        for col in range(grid):
            x = min(width - 1, (col * width) // grid + width // (2 * grid))
            y = min(height - 1, (row * height) // grid + height // (2 * grid))
            pixel = image.pixelColor(x, y)
            out.append((pixel.red(), pixel.green(), pixel.blue()))
    return out


def measured(text: RGB, scrim: RGB, backdrops: list[RGB],
             target: float = AA_BODY) -> Solution:
    return solve(text, scrim, backdrops, target)


def choose(inks: dict[str, RGB], scrims: dict[str, RGB], backdrops: list[RGB],
           target: float = AA_BODY) -> tuple[str, Solution]:
    """Pick the polarity that costs the least glass.

    Light text on a dark scrim and dark text on a light scrim are both valid
    answers, and which one is cheaper depends entirely on the backdrop -- a dark
    scrim over a dark desktop barely has to do anything. Flipping the text with
    the backdrop is the single biggest win available here, worth more than any
    amount of tuning at fixed polarity.
    """
    best: tuple[str, Solution] | None = None
    for name, ink in inks.items():
        solution = solve(ink, scrims[name], backdrops, target)
        if not solution.feasible:
            continue
        if best is None or solution.alpha < best[1].alpha:
            best = (name, solution)
    if best is None:
        name = next(iter(inks))
        return name, Solution(1.0, 0.0, False, scrims[name], inks[name])
    return best


# ---------------------------------------------------------------------------
# A scrim is a blunt instrument. It pulls all three channels toward one colour,
# so it spends the backdrop's hue to buy luminance safety it could have bought
# on its own. Contrast depends on luminance alone -- so cap the luminance and
# leave the colour.


def max_surface_luminance(text: RGB, target: float = AA_BODY) -> float:
    """Brightest a surface may be under `text`, when the text is the lighter one."""
    return (luminance(text) + 0.05) / target - 0.05


def min_surface_luminance(text: RGB, target: float = AA_BODY) -> float:
    """Darkest a surface may be under `text`, when the text is the darker one."""
    return target * (luminance(text) + 0.05) - 0.05


def _to_linear(rgb: RGB) -> RGB:
    return tuple(_linear(c) for c in rgb)


def _from_linear(linear: RGB) -> RGB:
    out = []
    for c in linear:
        c = max(0.0, min(1.0, c))
        s = 12.92 * c if c <= 0.0031308 else 1.055 * (c ** (1 / 2.4)) - 0.055
        out.append(s * 255.0)
    return tuple(out)


def cap_luminance(rgb: RGB, ceiling: float) -> RGB:
    """Darken until luminance <= ceiling, scaling in linear light.

    Scaling every linear channel by one factor leaves chromaticity untouched, so
    a bright red stays red -- it just stops being bright. That is the whole point:
    a scrim would have turned it grey, and grey is what makes glass look like
    frosted plastic.
    """
    current = luminance(rgb)
    if current <= ceiling or current <= 0.0:
        return rgb
    return _from_linear(tuple(c * (ceiling / current) for c in _to_linear(rgb)))


def lift_luminance(rgb: RGB, floor: float) -> RGB:
    """Brighten until luminance >= floor, by blending toward white.

    Not symmetric with cap_luminance, and the asymmetry matters: scaling cannot
    lift a black pixel, because zero times anything is zero. Dark pixels have to
    be blended toward white, which does wash out their hue. Light text on dark
    glass is therefore the cheaper direction, and that is a design conclusion,
    not an implementation detail.
    """
    current = luminance(rgb)
    if current >= floor:
        return rgb
    lo, hi = 0.0, 1.0
    for _ in range(30):
        mid = (lo + hi) / 2.0
        blended = tuple(c + (255.0 - c) * mid for c in rgb)
        if luminance(blended) >= floor:
            hi = mid
        else:
            lo = mid
    return tuple(c + (255.0 - c) * hi for c in rgb)


def chroma(rgb: RGB) -> float:
    """Rough colourfulness: how far the pixel is from grey. 0..1."""
    return (max(rgb) - min(rgb)) / 255.0


@dataclass(frozen=True)
class Preservation:
    """What a treatment left of the backdrop."""
    untouched: float     # share of pixels it did not have to alter at all
    chroma_kept: float   # share of the original colourfulness surviving
    texture_kept: float  # share of the original luminance spread surviving


def _spread(values: list[float]) -> float:
    if not values:
        return 0.0
    mean = sum(values) / len(values)
    return (sum((v - mean) ** 2 for v in values) / len(values)) ** 0.5


def preservation(original: list[RGB], treated: list[RGB]) -> Preservation:
    untouched = sum(
        1 for a, b in zip(original, treated)
        if all(abs(x - y) < 1.0 for x, y in zip(a, b))
    ) / max(1, len(original))

    chroma_before = sum(chroma(p) for p in original)
    chroma_after = sum(chroma(p) for p in treated)
    kept = chroma_after / chroma_before if chroma_before > 1e-9 else 1.0

    spread_before = _spread([luminance(p) for p in original])
    spread_after = _spread([luminance(p) for p in treated])
    texture = spread_after / spread_before if spread_before > 1e-9 else 1.0

    return Preservation(untouched, min(1.0, kept), min(1.0, texture))
