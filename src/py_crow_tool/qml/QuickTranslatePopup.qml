import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window

Window {
    id: popup
    width: 380
    height: 260
    minimumWidth: 260
    minimumHeight: 160
    flags: Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
    color: "transparent"
    visible: false

    property bool closeArmed: false

    function popAt(x, y) {
        popup.x = x
        popup.y = y
        closeArmed = false
        popup.show()
        popup.raise()
        popup.requestActivate()
        closeArmDelay.restart()
    }

    // Activating a window we just showed can briefly report active=false before
    // settling to true; closing on that first flicker would hide the popup the
    // instant it appears, so only start reacting to deactivation once it has
    // had a moment to actually gain focus.
    Timer { id: closeArmDelay; interval: 250; onTriggered: popup.closeArmed = true }
    onActiveChanged: if (!active && closeArmed) popup.close()

    Rectangle {
        anchors.fill: parent
        radius: 10
        color: "#ffffff"
        border.color: "#d5d9de"
        border.width: 1

        Keys.onEscapePressed: popup.close()
        focus: true

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 12
            spacing: 8

            RowLayout {
                Layout.fillWidth: true
                Label {
                    text: quickTranslateModel.detectedSourceLanguage
                        ? "Auto (" + quickTranslateModel.detectedSourceLanguage + ") → " + quickTranslateModel.targetLanguage
                        : quickTranslateModel.sourceLanguage + " → " + quickTranslateModel.targetLanguage
                    color: "#6b7480"
                    font.pixelSize: 11
                    Layout.fillWidth: true
                    elide: Text.ElideRight
                }
                ToolButton { text: "⎘"; ToolTip.text: "Copy translation"; ToolTip.visible: hovered; onClicked: { quickTranslateModel.copyTranslated() } }
                ToolButton { text: "✕"; onClicked: popup.close() }
            }

            ScrollView {
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                TextArea {
                    readOnly: true
                    wrapMode: TextEdit.Wrap
                    font.pixelSize: 14
                    text: quickTranslateModel.busy ? "Translating..." : quickTranslateModel.translatedText
                    selectByMouse: true
                }
            }

            Label {
                Layout.fillWidth: true
                text: quickTranslateModel.sourceText
                wrapMode: Text.Wrap
                elide: Text.ElideRight
                maximumLineCount: 2
                color: "#8a9099"
                font.pixelSize: 11
            }
        }
    }
}
