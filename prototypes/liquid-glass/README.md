# Liquid glass — prototype

Standalone. Imports nothing from `py_crow_tool` and changes nothing in it; delete
the folder and the app is untouched.

```bash
.venv/Scripts/python.exe prototypes/liquid-glass/run.py
```

Drag the card over the paragraphs, and use the sliders to find values worth
keeping. The bottom-left corner names the renderer — on the software renderer
the shader draws nothing at all, which is the fallback question, not a bug.

## What it answers

**Inside the app, over our own content: yes, fully.** `ShaderEffectSource` hands
the shader a texture of whatever is behind a panel, so the whole material is
available — bevel refraction, chromatic dispersion, specular rim, adaptive tint.
`shots/01-in-app-glass.png`.

**Over the desktop: yes, but not the way it looked like it would.** See below.

## The compositor is a dead end

The plan was Windows 11's own backdrop: `DWMWA_SYSTEMBACKDROP_TYPE` with
`DWMSBT_TRANSIENTWINDOW`. It does not work, and it fails in a way worth writing
down, because every call reports success.

`test_backdrop.py` puts five windows over hard-edged colour bars and asks each
for a blur:

| | surface | call | result |
|---|---|---|---|
| E | transparent | *none* | **see-through** — bars fully visible |
| A | transparent | DWM acrylic | opaque grey |
| B | opaque black | DWM acrylic | opaque black |
| C | transparent | legacy `ACCENT_ENABLE_ACRYLICBLURBEHIND` | opaque black |
| D | transparent | legacy `ACCENT_ENABLE_BLURBEHIND` | opaque black |

Every DWM call returned `S_OK`; both legacy calls returned `ok=True`. Windows
transparency effects are on (`EnableTransparency=1`), composition is on.

Read row E against the rest: **the calls do not fail to add blur, they destroy
transparency that was already working.** A Qt window that was see-through
becomes an opaque slab the moment either API touches it. So the rule for this
codebase is not "acrylic is unreliable" — it is *do not call these at all*.

The reason is in the extended styles the test prints. Qt's translucent window is
`WS_EX_LAYERED`, which DWM system backdrops ignore by design, and no Qt window
has `WS_EX_NOREDIRECTIONBITMAP` — the DirectComposition swapchain that WinUI 3
uses to earn Mica and Acrylic. Qt 6.11 exposes no API for either; `QWindow` has
no backdrop, material or blur property.

`shots/03-backdrop-test.png`.

## What works instead

Grab the desktop ourselves, one frame, the instant before the window appears,
and feed that to the same shader the in-app panels use. `GlassPopup.qml`.

This is better than the compositor route would have been, not worse: Acrylic
would have given us its blur and nothing else, with no way to layer refraction
on top, because the blurred pixels are never handed back. A captured backdrop is
just a texture, so the full material applies over other applications —
refraction, dispersion, specular rim and all. `shots/02-desktop-glass-popup.png`.

The cost is that the backdrop is a **still**. It is correct at pop time and does
not track anything moving underneath. For a popup that lives a few seconds over
a document somebody is reading, that is a fair trade. For a window that stays
open it is not, and that window should stay opaque.

## Files

| | |
|---|---|
| `run.py` | launcher; `PROTO_SHOT`, `PROTO_SHOT_SCREEN`, `PROTO_POPUP` drive captures |
| `qml/glass.frag` | the material; `.qsb` is built with `pyside6-qsb` |
| `qml/GlassPanel.qml` | one slab, for use over our own content |
| `qml/GlassPopup.qml` | the popup, on a captured desktop backdrop |
| `qml/AcrylicPopup.qml` | the compositor attempt, kept as the record of a negative result |
| `qml/Lab.qml` | the bench: background, sliders, comparison toggle |
| `backdrop.py` | both Windows backdrop APIs, via ctypes |
| `test_backdrop.py` | the five-variant backdrop experiment |
| `contrast.py` | luminance, WCAG contrast, scrim solver, luminance cap |
| `report_contrast.py` | what glass costs the real palette |
| `verify_contrast.py` | measures rendered pixels; exit 0 only if every backdrop passes |

Rebuild the shader after editing it:

```bash
.venv/Scripts/pyside6-qsb.exe --glsl 100es,120,150 --hlsl 50 --msl 12 -o prototypes/liquid-glass/qml/glass.frag.qsb prototypes/liquid-glass/qml/glass.frag
```

## Contrast — solved, and measured

`contrast.py` has the maths, `report_contrast.py` runs it against the real
Theme.qml, `verify_contrast.py` measures the rendered pixels.

**A scrim is the wrong instrument.** Against an unmeasurable backdrop the
theme's own ink needs a **66.5%** scrim to clear 4.5:1, leaving a third of the
glass. It costs that much because it drags all three channels toward one colour,
spending the backdrop's hue to buy luminance safety.

**Contrast depends on luminance alone, so cap the luminance and keep the
colour.** Scaling every linear channel by one factor moves luminance exactly
where it must go and leaves chromaticity untouched: a bright red stops being
bright and stays red. On real backdrops, against the same 4.5:1:

| treatment | pixels untouched | colour kept | texture kept |
|---|---|---|---|
| scrim | 0% | 43% | 16% |
| luminance cap | 68% | 86% | 40% |

The bound comes from the text colour, not the backdrop, so it needs **nothing
measured** and holds over any desktop. That is the part that matters: the
expensive blind floor and the cheap adaptive answer turn out to be the same
answer.

Measured on rendered pixels, text hidden so every sample is surface, five
backdrops including pure white and fully saturated fills: **all pass, with a
safe inset of 13-14px.** `shots/04-contrast-off-vs-on.png`.

Three things the measuring turned up that the maths alone would not have:

1. **Quantisation.** A ceiling set exactly at 4.5:1 lands half its pixels a
   rounding step below it — measured 4.47:1 to 4.52:1. `contrastHeadroom` aims
   at 4.65:1 to absorb one 8-bit step.
2. **A NaN that silently disabled the guarantee.** `saturation` above 1 drives
   the weak channel of a vivid colour negative; `pow()` of a negative base is
   undefined, `mix()` propagates the NaN because `NaN * 0` is `NaN`, and every
   comparison against a NaN luminance is false — so the clamp decided the pixel
   was fine and passed it through. One vivid region, no error, guarantee gone.
   The fix is a clamp before the transfer function; `vivid saturated fills`
   stays in the suite as the regression.
3. **Secondary text cannot go on glass.** The ceiling is set by the weakest text
   role, not the primary one. Against Theme.qml: `ink` demands 0.143, `muted`
   0.037, `placeholder` 0.022, and `inkDisabled` a **negative** ceiling — no
   surface of any luminance makes it legible. Glass carries `ink` only;
   hierarchy on glass has to come from size and weight, not lightness.

The bevel is lit on purpose, which puts it off limits to text.
`GlassPanel.contentInset` covers it.

## Still open before any of this reaches the app

1. **Software renderer.** `Surface.qml` already guards `layer.enabled` because
   `MultiEffect` draws nothing over RDP or in a VM. Glass needs a full opaque
   fallback, not just a disabled shadow.
2. **Text antialiasing.** Content on top of `GlassPanel` is a normal sibling, so
   it keeps subpixel AA. That holds only as long as nothing layers the card as a
   whole — the warning already in `Surface.qml`.
3. **Reduce motion.** Untouched here. Anything that morphs has to respect
   `Theme.reduceMotion`.
