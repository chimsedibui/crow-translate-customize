pragma Singleton
import QtQuick

// Single source of truth for colour, type and shape. Every value here is a role
// ("muted text", "pressed control") rather than a raw literal, so a surface can
// never drift out of step with the rest of the app the way 29 scattered hex
// literals did. Text colours are picked to clear WCAG AA (4.5:1) against the
// surfaces they are actually used on; fills only need 3:1.
QtObject {
    // Surfaces
    readonly property color surface: "#f3f6f8"
    readonly property color raised: "#ffffff"
    readonly property color raisedAlt: "#f8fafb"
    readonly property color hairline: "#dce4eb"

    // Text
    readonly property color ink: "#182b3a"
    readonly property color muted: "#5c6b7a"
    readonly property color placeholder: "#6b7885"
    readonly property color inkDisabled: "#7f8c98"
    readonly property color inkInverse: "#ffffff"

    // Accent. One teal serves both fills and text: the old #0d897e read at only
    // 4.29:1, which failed as body text and as a white label on the primary button.
    readonly property color accent: "#0b7469"
    readonly property color accentHover: "#0a6660"
    readonly property color accentPress: "#08564f"
    readonly property color accentSoft: "#e5f3f0"
    readonly property color accentSoftInk: "#15605a"

    // Controls
    readonly property color controlHover: "#edf2f6"
    readonly property color controlPress: "#e2e8ee"
    readonly property color controlDisabled: "#edf1f4"

    // Feedback
    readonly property color danger: "#a82f1c"
    readonly property color dangerSoft: "#fff0ec"

    // Capture overlay
    readonly property color scrim: "#000000a6"
    readonly property color overlayChip: "#182b3acc"
    readonly property color selectionFill: "#0b746933"

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
}
