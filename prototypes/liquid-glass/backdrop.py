"""Windows 11 compositor backdrops, reached through ctypes.

Qt 6.11 exposes no API for this -- QWindow has no backdrop, material or blur
property -- so the only way to a window that blurs the *desktop* behind it is to
ask DWM directly. Everything here is a no-op on anything but Windows 11 22621+,
and every call reports its HRESULT rather than failing silently, because the
whole point of the prototype is to find out what actually takes effect.
"""

from __future__ import annotations

import ctypes
import sys
from ctypes import wintypes

DWMWA_USE_IMMERSIVE_DARK_MODE = 20
DWMWA_WINDOW_CORNER_PREFERENCE = 33
DWMWA_SYSTEMBACKDROP_TYPE = 38

# DWM_SYSTEMBACKDROP_TYPE
BACKDROPS = {
    "auto": 0,
    "none": 1,
    "mica": 2,        # for a long-lived main window
    "acrylic": 3,     # for a transient window: blurs the desktop behind it
    "mica-alt": 4,
}

# DWM_WINDOW_CORNER_PREFERENCE
CORNERS = {"default": 0, "square": 1, "round": 2, "round-small": 3}


class MARGINS(ctypes.Structure):
    _fields_ = [
        ("cxLeftWidth", ctypes.c_int),
        ("cxRightWidth", ctypes.c_int),
        ("cyTopHeight", ctypes.c_int),
        ("cyBottomHeight", ctypes.c_int),
    ]


def available() -> bool:
    return sys.platform == "win32"


def _set_attr(hwnd: int, attr: int, value: int) -> int:
    v = ctypes.c_int(value)
    return ctypes.windll.dwmapi.DwmSetWindowAttribute(
        wintypes.HWND(hwnd), ctypes.c_uint(attr), ctypes.byref(v), ctypes.sizeof(v)
    )


def apply(hwnd: int, kind: str = "acrylic", *, dark: bool = True,
          corner: str = "round") -> dict:
    """Put a DWM backdrop behind `hwnd`. Returns the HRESULT of each step."""
    if not available():
        return {"skipped": "not windows"}

    dwm = ctypes.windll.dwmapi
    out: dict[str, int] = {}

    # The backdrop is painted into the window frame, so a frameless window has
    # to extend that frame over its whole client area or there is nowhere for
    # DWM to put it. -1 on every side means "the entire client area".
    margins = MARGINS(-1, -1, -1, -1)
    out["extend_frame"] = dwm.DwmExtendFrameIntoClientArea(
        wintypes.HWND(hwnd), ctypes.byref(margins)
    )
    out["dark_mode"] = _set_attr(hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE, int(dark))
    out["corner"] = _set_attr(hwnd, DWMWA_WINDOW_CORNER_PREFERENCE, CORNERS[corner])
    out["backdrop"] = _set_attr(hwnd, DWMWA_SYSTEMBACKDROP_TYPE, BACKDROPS[kind])
    return out


# --------------------------------------------------------------------------
# The older road. SetWindowCompositionAttribute is undocumented and Microsoft
# has been steering people off it for years, but unlike DWMWA_SYSTEMBACKDROP_TYPE
# it works on a LAYERED window -- which is exactly what Qt gives us for a
# translucent one. If anything can blur the desktop behind a Qt Quick window,
# it is this.

WCA_ACCENT_POLICY = 19

ACCENT_DISABLED = 0
ACCENT_ENABLE_BLURBEHIND = 3
ACCENT_ENABLE_ACRYLICBLURBEHIND = 4
ACCENT_ENABLE_HOSTBACKDROP = 5

ACCENTS = {
    "off": ACCENT_DISABLED,
    "blur": ACCENT_ENABLE_BLURBEHIND,
    "acrylic": ACCENT_ENABLE_ACRYLICBLURBEHIND,
    "hostbackdrop": ACCENT_ENABLE_HOSTBACKDROP,
}


class ACCENT_POLICY(ctypes.Structure):
    _fields_ = [
        ("AccentState", ctypes.c_uint),
        ("AccentFlags", ctypes.c_uint),
        ("GradientColor", ctypes.c_uint),   # ABGR
        ("AnimationId", ctypes.c_uint),
    ]


class WINDOWCOMPOSITIONATTRIBDATA(ctypes.Structure):
    _fields_ = [
        ("Attrib", ctypes.c_uint),
        ("pvData", ctypes.c_void_p),
        ("cbData", ctypes.c_size_t),
    ]


def accent(hwnd: int, kind: str = "acrylic", tint: int = 0x99201A14) -> dict:
    """Legacy blur-behind. `tint` is ABGR, and its alpha is the tint strength."""
    if not available():
        return {"skipped": "not windows"}

    user32 = ctypes.windll.user32
    if not hasattr(user32, "SetWindowCompositionAttribute"):
        return {"error": "SetWindowCompositionAttribute not exported"}

    policy = ACCENT_POLICY(ACCENTS[kind], 2, tint, 0)
    data = WINDOWCOMPOSITIONATTRIBDATA(
        WCA_ACCENT_POLICY, ctypes.cast(ctypes.byref(policy), ctypes.c_void_p),
        ctypes.sizeof(policy)
    )
    ok = user32.SetWindowCompositionAttribute(wintypes.HWND(hwnd), ctypes.byref(data))
    return {"accent": kind, "ok": bool(ok), "lasterror": ctypes.get_last_error() if not ok else 0}
