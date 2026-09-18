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
    readonly property color hairline: dark ? "#2b3844" : "#dce4eb"

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
    readonly property int radiusSmall: 8
    readonly property int radiusLarge: 12

    // Motion. Kept short and limited to colour and opacity: this is a utility that
    // pops over other windows, so transitions should soften the appearance, never
    // delay it.
    readonly property int durationFast: 110
    readonly property int durationBase: 180
    readonly property int easingCurve: Easing.OutCubic
}
