import QtQuick
import QtQuick.Controls
import QtQuick.Window

Window {
    id: overlay
    // Qt.Tool is required, not just cosmetic: without it, Windows/DWM does not composite
    // this window's alpha correctly even though Qt requests an alpha-capable swapchain --
    // the whole overlay silently fails to render (desktop shows through untouched, no
    // error). Confirmed by isolating flags/backend/Image on real Windows hardware.
    flags: Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
    visible: false
    color: "transparent"

    property real originX: 0
    property real originY: 0

    Image {
        id: background
        objectName: "captureBackground"
        anchors.fill: parent
        source: "image://capture/current/" + captureController.generation
        cache: false
        asynchronous: false
        fillMode: Image.Stretch
    }

    Rectangle {
        anchors.fill: parent
        color: "#00000066"
        focus: true
        Keys.onEscapePressed: captureController.cancel()

        MouseArea {
            id: mouseArea
            objectName: "captureMouseArea"
            anchors.fill: parent
            hoverEnabled: true
            onPressed: { overlay.originX = mouseX; overlay.originY = mouseY }
            onReleased: {
                const x = Math.min(overlay.originX, mouseX)
                const y = Math.min(overlay.originY, mouseY)
                const w = Math.abs(mouseX - overlay.originX)
                const h = Math.abs(mouseY - overlay.originY)
                captureController.confirmRegion(x, y, w, h)
            }
        }

        Rectangle {
            id: selectionRect
            objectName: "selectionRect"
            visible: mouseArea.pressed
            color: "#0d897e33"
            border.color: "#0d897e"
            border.width: 2
            x: Math.min(mouseArea.mouseX, overlay.originX)
            y: Math.min(mouseArea.mouseY, overlay.originY)
            width: Math.abs(mouseArea.mouseX - overlay.originX)
            height: Math.abs(mouseArea.mouseY - overlay.originY)
        }

        Rectangle {
            anchors.top: parent.top
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.topMargin: 24
            radius: 8
            color: "#182b3acc"
            width: hint.implicitWidth + 24
            height: hint.implicitHeight + 12
            Label { id: hint; anchors.centerIn: parent; text: "Drag to select an area  ·  Esc to cancel"; color: "white" }
        }
    }

    Connections {
        target: captureController
        function onCancelled() { overlay.close() }
        function onRegionCaptured() { overlay.close() }
    }
}
