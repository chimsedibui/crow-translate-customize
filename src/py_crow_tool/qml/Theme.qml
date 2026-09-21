pragma Singleton
import QtQuick

// Single source of truth for colour, type, shape and motion. Every value is a role
// ("muted text", "pressed control") rather than a raw literal, so a surface can
// never drift out of step with the rest of the app the way 29 scattered hex
// literals did. Both schemes are picked to clear WCAG AA (4.5:1) for text against
// the surfaces each colour is actually used on; fills only need 3:1.
QtObject {
    // Follows the OS setting live: Qt re-evaluates this binding when the user
    // switches Windows between light and dark, so no restart and no setting of
    // our own is needed.
    readonly property bool dark: Application.styleHints.colorScheme === Qt.ColorScheme.Dark

    // Surfaces
    readonly property color surface: dark ? "#121a21" : "#f3f6f8"
    readonly property color raised: dark ? "#1a232b" : "#ffffff"
    readonly property color raisedAlt: dark ? "#161f26" : "#f8fafb"
    // The translation pane only. raisedAlt beside raised is #f8fafb against #ffffff --
    // a difference the eye cannot resolve, so the two panes read as one wide box with a
    // gap down the middle. This is the same step, tilted towards the accent: enough to
    // tell input from output at a glance, not enough to look like a coloured panel.
    readonly property color raisedTranslated: dark ? "#16211f" : "#f1f8f6"
    readonly property color hairline: dark ? "#2b3844" : "#dce4eb"
    // For a divider that has to be found rather than merely seen -- the split handle at
    // rest. Decorative: nothing may depend on it alone being noticed.
    readonly property color hairlineStrong: dark ? "#3a4a58" : "#c4d0da"

    // Text
    readonly property color ink: dark ? "#e8eef3" : "#182b3a"
    readonly property color muted: dark ? "#93a3b0" : "#5c6b7a"
    readonly property color placeholder: dark ? "#8593a1" : "#6b7885"
    readonly property color inkDisabled: dark ? "#657380" : "#7f8c98"

    // Accent. One teal serves both fills and text. Light mode takes a white label;
    // the dark teal has to be bright enough to read on a dark surface, which then
    // only carries a near-black label -- hence accentInk rather than a fixed white.
    readonly property color accent: dark ? "#2bb3a1" : "#0b7469"
    readonly property color accentHover: dark ? "#31bdaa" : "#0a6660"
    readonly property color accentPress: dark ? "#239789" : "#08564f"
    readonly property color accentInk: dark ? "#04211d" : "#ffffff"
    readonly property color accentSoft: dark ? "#0e2a27" : "#e5f3f0"
    readonly property color accentSoftInk: dark ? "#7fd8c9" : "#15605a"

    // Controls
    readonly property color controlHover: dark ? "#222d37" : "#edf2f6"
    readonly property color controlPress: dark ? "#2a3742" : "#e2e8ee"
    readonly property color controlDisabled: dark ? "#1c252d" : "#edf1f4"

    // Feedback
    readonly property color danger: dark ? "#f08a75" : "#a82f1c"
    readonly property color dangerSoft: dark ? "#2d1713" : "#fff0ec"

    // The bars that stand in for a translation while it is in flight, and the highlight
    // that crosses them. Decorative only -- the status line says the same thing in words.
    readonly property color skeleton: dark ? "#1f2932" : "#e6ecf1"
    readonly property color skeletonSheen: dark ? "#2b3743" : "#f7fafc"

    // Elevation. Qt Quick has no box-shadow, so a shadow is a MultiEffect over a surface
    // and these are its parameters. The strength is a separate number rather than an
    // alpha on the colour: MultiEffect multiplies shadowColor by shadowOpacity and a
    // colour that carries its own alpha renders no shadow at all, silently. On a dark
    // ground only a near-opaque black reads, on a light one a faint tinted ink keeps
    // the shadow from looking like soot.
    readonly property color shadowColor: dark ? "#000000" : "#182b3a"
    readonly property real shadowOpacity: dark ? 0.8 : 0.18
    readonly property int shadowBlurMax: 64
    // Multiplied by shadowBlurMax: roughly 6px, 16px and 40px of blur.
    readonly property real shadowRest: 0.09
    readonly property real shadowRaised: 0.25
    readonly property real shadowFloating: 0.62
    readonly property int shadowOffsetRest: 1
    readonly property int shadowOffsetRaised: 4
    readonly property int shadowOffsetFloating: 12

    // The transparent gutter a frameless window has to reserve around its card for the
    // blur to render into: a shadow cannot spill outside its own window. Measured, not
    // guessed -- a floating shadow is still darkening the background 40px out, so a
    // smaller gutter ends it on a visible straight edge.
    readonly property int shadowMargin: 48

    // The keyboard focus ring. Solid accent rather than a soft glow: it is the only
    // affordance a keyboard-only user gets, and it clears 3:1 on every surface it lands on.
    readonly property color focusRing: accent

    // Capture overlay. Always dark in both schemes: it sits on a dimmed screenshot,
    // not on one of our surfaces.
    readonly property color scrim: "#000000a6"
    readonly property color overlayChip: "#182b3acc"
    readonly property color overlayInk: "#ffffff"
    readonly property color selectionFill: dark ? "#2bb3a133" : "#0b746933"

    // Type. The UI face and its per-script fallbacks are set application-wide from
    // Python (QFont.setFamilies), because QML's font value type has no "families"
    // property. These two cover the roles that deviate from that default.
    readonly property string displayFamily: "Segoe UI Variable Display"
    readonly property string monoFamily: "Cascadia Mono"

    // Type scale, by role rather than by number.
    readonly property int sizeCaption: 11
    readonly property int sizeBody: 13
    readonly property int sizeControl: 15
    readonly property int sizeReading: 19
    readonly property int sizeTitle: 23

    readonly property int weightRegular: Font.Normal
    readonly property int weightMedium: Font.DemiBold
    readonly property int weightBold: Font.Bold

    // Shape
    readonly property int radiusChip: 4
    readonly property int radiusSmall: 8
    readonly property int radiusLarge: 12

    // Fixed dimensions the layouts used to set by hand. Here so a new control comes out
    // the same height as the ones beside it: an input is four pixels taller than an
    // action, which is what keeps a field from reading as a button.
    readonly property int controlHeight: 36
    readonly property int fieldHeight: 40
    readonly property int iconSize: 16
    readonly property int paneMinWidth: 240

    // Motion. Kept short: this is a utility that pops over other windows, so a
    // transition should soften an appearance, never delay it. The budget is by kind,
    // not by taste -- press, then hover and focus, then something appearing in place,
    // then something that travels a real distance. Nothing is slower than 260ms.
    readonly property int durationInstant: 90
    readonly property int durationFast: 110
    readonly property int durationBase: 180
    readonly property int durationSlow: 260
    // Delay between consecutive history rows entering, for the first eight only.
    readonly property int durationStagger: 40

    readonly property int easingCurve: Easing.OutCubic
    // Easing.OutBack with the overshoot dialled down from its default 1.7, which bounces.
    // Two places only: the quick-translate popup arriving and the swap button turning --
    // the two moments that should feel physical. Anywhere else it reads as a toy.
    readonly property int easingSpring: Easing.OutBack
    readonly property real springOvershoot: 0.9

    // When Windows has "Show animations" switched off, keep the fades -- they carry the
    // "this is new" signal -- and drop every move, turn and scale to nothing. app.py
    // reads the OS setting and hands it in; the guard keeps this file loadable on its
    // own, which is how the tests and the QML tooling load it.
    readonly property bool reduceMotion: typeof systemReduceMotion !== "undefined" && systemReduceMotion
    function motion(ms) { return reduceMotion ? 0 : ms }
}
