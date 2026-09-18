import QtQuick
import QtQuick.Controls
import "."

Button {
    id: control
    property bool primary: false
    property string symbol: ""
    implicitHeight: 36
    implicitWidth: Math.max(36, implicitContentWidth + 24)
    padding: 10
    font.pixelSize: Theme.sizeBody
    icon.source: symbol ? "icons/" + symbol + ".svg" : ""
    icon.width: 16
    icon.height: 16
    icon.color: !enabled ? Theme.inkDisabled : primary ? Theme.inkInverse : Theme.muted
    palette.buttonText: !enabled ? Theme.inkDisabled : primary ? Theme.inkInverse : Theme.ink
    background: Rectangle {
        radius: Theme.radiusSmall
        color: !control.enabled
            ? Theme.controlDisabled
            : control.primary
                ? (control.down ? Theme.accentPress : control.hovered ? Theme.accentHover : Theme.accent)
                : control.down ? Theme.controlPress : control.hovered ? Theme.controlHover : "transparent"
        border.color: control.activeFocus ? Theme.accent : "transparent"
        border.width: 2
    }
    Accessible.name: text.length ? text : ToolTip.text
    ToolTip.visible: hovered && ToolTip.text.length > 0
    ToolTip.delay: 500
}
