import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

// The quick-translate popup, rebuilt on a DWM backdrop instead of a drawn card.
//
// This is the half of the design Qt cannot do alone. Nothing in the process can
// read the pixels of the apps underneath, so the blur has to come from the
// compositor, and what the compositor gives us is Acrylic -- its blur, its
// recipe. We layer our own rim and tint on top; we cannot layer refraction,
// because the blurred pixels are never handed back to us.
//
// Note what had to go: the shipping popup reserves a 48px transparent gutter
// for a drawn shadow (Theme.shadowMargin). A DWM backdrop fills the whole
// window rect, so that gutter would render as a visible blurred slab. The
// window here is therefore exactly the card, and Windows draws the shadow.
Window {
    id: popup

    property string kindLabel: "acrylic"
    property bool darkMode: true
    property string hresults: ""

    width: 380
    height: 240
    flags: Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
    color: "transparent"

    function popAt(x, y, kind) {
        popup.kindLabel = kind
        popup.x = x
        popup.y = y
        popup.show()
        popup.raise()
        popup.requestActivate()
        // The HWND only exists once the window is up.
        popup.hresults = backdrop.applyTo(popup, kind, popup.darkMode)
    }

    // A tint floor over the backdrop. Acrylic alone is not a contrast guarantee:
    // it blurs whatever is behind it, which on a pale document is still pale.
    // Text has to sit on something known, and this is the cheapest version of
    // that -- the same job Apple's adaptive tint does, minus the adaptation.
    Rectangle {
        anchors.fill: parent
        radius: 8
        color: popup.darkMode ? "#20262d" : "#ffffff"
        opacity: popup.darkMode ? 0.42 : 0.55
    }

    // The specular rim. This part we can still draw ourselves, and it is most of
    // what makes a flat blurred panel read as a physical edge.
    Rectangle {
        anchors.fill: parent
        radius: 8
        color: "transparent"
        border.width: 1
        border.color: popup.darkMode ? "#4affffff" : "#66ffffff"
    }
    Rectangle {
        anchors.fill: parent
        anchors.margins: 1
        radius: 7
        color: "transparent"
        border.width: 1
        border.color: popup.darkMode ? "#14ffffff" : "#40ffffff"
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 14
        spacing: 8

        RowLayout {
            Layout.fillWidth: true
            Label {
                text: "English → Tiếng Việt"
                color: popup.darkMode ? "#9fb0bd" : "#5c6b7a"
                font.pixelSize: 11
                Layout.fillWidth: true
            }
            Label {
                text: popup.kindLabel
                color: popup.darkMode ? "#2bb3a1" : "#0b7469"
                font.pixelSize: 11
                font.bold: true
            }
        }

        Label {
            Layout.fillWidth: true
            text: "Kính không phải là một lớp phủ — nó là thứ nằm giữa chữ và nền."
            wrapMode: Text.Wrap
            font.pixelSize: 15
            color: popup.darkMode ? "#e8eef3" : "#182b3a"
        }

        Item { Layout.fillHeight: true; Layout.fillWidth: true }

        Label {
            Layout.fillWidth: true
            text: popup.hresults
            wrapMode: Text.Wrap
            font.pixelSize: 10
            font.family: "Cascadia Mono"
            color: popup.darkMode ? "#93a3b0" : "#5c6b7a"
        }

        RowLayout {
            Button { text: "Close"; onClicked: popup.close() }
            Item { Layout.fillWidth: true }
        }
    }

    Shortcut { sequence: "Escape"; onActivated: popup.close() }
}
