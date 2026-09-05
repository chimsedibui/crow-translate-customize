import QtQuick
import QtQuick.Controls

Button {
    id: control
    property bool primary: false
    property string symbol: ""
    implicitHeight: 36
    implicitWidth: Math.max(36, implicitContentWidth + 24)
    padding: 10
    font.pixelSize: 13
    icon.source: symbol ? "icons/" + symbol + ".svg" : ""
    icon.width: 16
    icon.height: 16
    icon.color: !enabled ? "#9ba9b4" : primary ? "white" : "#475569"
    palette.buttonText: !enabled ? "#9ba9b4" : primary ? "white" : "#334155"
    background: Rectangle {
        radius: 8
        color: !control.enabled ? "#edf1f4" : control.primary ? (control.down ? "#0f655f" : control.hovered ? "#117b72" : "#0d897e") : control.down ? "#e2e8ee" : control.hovered ? "#edf2f6" : "transparent"
        border.color: control.activeFocus ? "#0d897e" : "transparent"
        border.width: 2
    }
    Accessible.name: text.length ? text : ToolTip.text
    ToolTip.visible: hovered && ToolTip.text.length > 0
    ToolTip.delay: 500
}
