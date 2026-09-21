import QtQuick
import QtQuick.Controls
import QtQuick.Effects
import "."

Button {
    id: control
    property bool primary: false
    property string symbol: ""

    // A copy leaves no trace of its own, so the button that did it holds an accentSoft
    // tint for a moment. That, plus the line the status bar writes, is the whole
    // confirmation -- no icon swap, no toast.
    property bool flashing: false
    function flash() { flashing = true; flashTimer.restart() }
    Timer { id: flashTimer; interval: 600; onTriggered: control.flashing = false }

    implicitHeight: Theme.controlHeight
    implicitWidth: Math.max(Theme.controlHeight, implicitContentWidth + 24)
    padding: 10
    font.pixelSize: Theme.sizeBody
    icon.source: symbol ? "icons/" + symbol + ".svg" : ""
    icon.width: Theme.iconSize
    icon.height: Theme.iconSize
    icon.color: !enabled ? Theme.inkDisabled : primary ? Theme.accentInk : Theme.muted
    palette.buttonText: !enabled ? Theme.inkDisabled : primary ? Theme.accentInk : Theme.ink

    // Hover borrows a pixel and the press gives it straight back, so a click always
    // lands the button where it started and never leaves the row looking nudged. It is
    // a transform rather than a layout change on purpose: moving a laid-out item
    // relayouts its whole row, on every hover.
    transform: Translate {
        y: control.enabled && control.hovered && !control.down ? -1 : 0
        Behavior on y {
            NumberAnimation {
                duration: Theme.motion(control.down ? Theme.durationInstant : Theme.durationFast)
                easing.type: Theme.easingCurve
            }
        }
    }

    background: Rectangle {
        id: fill
        radius: Theme.radiusSmall
        // A disabled ghost button stays transparent. Filling it would make an
        // unavailable action the most solid thing in its row -- louder disabled than
        // enabled, which is backwards. Only the primary button, whose resting state is
        // already a fill, swaps that fill for the flat disabled one.
        color: !control.enabled
            ? (control.primary ? Theme.controlDisabled : "transparent")
            : control.primary
                ? (control.down ? Theme.accentPress : control.hovered ? Theme.accentHover : Theme.accent)
                : control.flashing
                    ? Theme.accentSoft
                    : control.down ? Theme.controlPress : control.hovered ? Theme.controlHover : "transparent"
        border.color: control.activeFocus ? Theme.focusRing : "transparent"
        border.width: 2
        Behavior on color { ColorAnimation { duration: Theme.motion(Theme.durationFast); easing.type: Theme.easingCurve } }
        Behavior on border.color { ColorAnimation { duration: Theme.motion(Theme.durationFast); easing.type: Theme.easingCurve } }

        // Only the primary button is raised, and only while it is enabled: the shadow is
        // what separates it from the ghost buttons beside it, so spending one on those
        // would give the difference away. Pressing it flattens the shadow rather than
        // inverting it -- Qt has no inset shadow, and going flat reads as pressed-in
        // just as well. The software renderer draws nothing for a layered item, so there
        // the button keeps its fill and loses only the shadow -- see Surface.qml.
        layer.enabled: control.primary && control.enabled && GraphicsInfo.api !== GraphicsInfo.Software
        layer.effect: MultiEffect {
            shadowEnabled: true
            blurMax: Theme.shadowBlurMax
            shadowColor: Theme.shadowColor
            shadowOpacity: Theme.shadowOpacity
            shadowBlur: control.down ? 0 : control.hovered ? Theme.shadowRaised : Theme.shadowRest
            shadowVerticalOffset: control.down ? 0 : control.hovered ? Theme.shadowOffsetRaised : Theme.shadowOffsetRest
            Behavior on shadowBlur {
                NumberAnimation {
                    duration: Theme.motion(control.down ? Theme.durationInstant : Theme.durationFast)
                    easing.type: Theme.easingCurve
                }
            }
            Behavior on shadowVerticalOffset {
                NumberAnimation {
                    duration: Theme.motion(control.down ? Theme.durationInstant : Theme.durationFast)
                    easing.type: Theme.easingCurve
                }
            }
        }
    }

    Accessible.name: text.length ? text : ToolTip.text
    ToolTip.visible: hovered && ToolTip.text.length > 0
    ToolTip.delay: 500
}
