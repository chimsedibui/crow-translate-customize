import QtQuick
import QtQuick.Effects
import "."

// The background of a pane, dialog, drawer or popup: the rounded fill, its hairline, and
// the drop shadow that lifts it off whatever is behind it.
//
// The shadow lives on this rectangle alone and never on the pane's whole subtree. A
// MultiEffect renders its target into an offscreen texture, so layering a pane that
// contains a live TextArea would push every keystroke through that texture and cost the
// subpixel antialiasing that makes 13px UI text readable. Callers therefore put a
// Surface behind their content rather than around it:
//
//     Item {
//         Surface { anchors.fill: parent; level: editor.activeFocus ? 1 : 0 }
//         ColumnLayout { anchors.fill: parent; ... }
//     }
Rectangle {
    id: surface

    // 0 at rest, 1 while focused or hovered, 2 for a surface floating over another window.
    property int level: 0

    radius: Theme.radiusLarge
    color: Theme.raised
    border.color: Theme.hairline
    border.width: 1

    // The border stays at every level. A shadow alone does not define an edge: this app
    // lands on unpredictable desktop wallpaper, and the hairline is what keeps a popup
    // from bleeding into a pale document behind it.
    Behavior on border.color {
        ColorAnimation { duration: Theme.motion(Theme.durationFast); easing.type: Theme.easingCurve }
    }

    // A MultiEffect is a shader, and Qt Quick's software renderer -- what a machine
    // without working GPU acceleration falls back to, over Remote Desktop or in a VM --
    // draws nothing at all for a layered item. Guarding this is not about the shadow:
    // unguarded, every pane, dialog and popup background in the app disappears there.
    layer.enabled: GraphicsInfo.api !== GraphicsInfo.Software
    layer.effect: MultiEffect {
        shadowEnabled: true
        blurMax: Theme.shadowBlurMax
        shadowColor: Theme.shadowColor
        shadowOpacity: Theme.shadowOpacity
        shadowBlur: surface.level === 2 ? Theme.shadowFloating
                  : surface.level === 1 ? Theme.shadowRaised
                  : Theme.shadowRest
        shadowVerticalOffset: surface.level === 2 ? Theme.shadowOffsetFloating
                            : surface.level === 1 ? Theme.shadowOffsetRaised
                            : Theme.shadowOffsetRest

        Behavior on shadowBlur {
            NumberAnimation { duration: Theme.motion(Theme.durationFast); easing.type: Theme.easingCurve }
        }
        Behavior on shadowVerticalOffset {
            NumberAnimation { duration: Theme.motion(Theme.durationFast); easing.type: Theme.easingCurve }
        }
    }
}
