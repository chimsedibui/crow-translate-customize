import QtQuick
import QtQuick.Controls
import QtQuick.Window

// One instance of this is created per connected screen by CaptureOverlay.qml, so a single
// hotkey press lets the user drag-select on whichever monitor the region is actually on.
Window {
    id: overlay
    // Not "required": Instantiator's Window delegates complete before the model's index/modelData
    // context properties are injected (a known QML limitation for Window-type delegates), so
    // CaptureOverlay.qml's Instantiator.onObjectAdded sets these imperatively after creation instead.
    property int screenIndex: 0
    property int screenX: 0
    property int screenY: 0
    property int screenWidth: 0
    property int screenHeight: 0

    // Geometry comes from captureController.screens (Python-side QScreen.geometry()), so the
    // overlay exactly covers that monitor regardless of its position in the virtual desktop.
    x: screenX
    y: screenY
    width: screenWidth
    height: screenHeight

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
        source: "image://capture/" + overlay.screenIndex + "/" + captureController.generation
        cache: false
        asynchronous: false
        fillMode: Image.Stretch
    }

    Rectangle {
        anchors.fill: parent
        color: "#000000a6"
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
                captureController.confirmRegion(overlay.screenIndex, x, y, w, h)
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
        function onCaptureRequested() { overlay.show(); overlay.requestActivate() }
        function onCancelled() { overlay.close() }
        function onRegionCaptured() { overlay.close() }
    }
}
