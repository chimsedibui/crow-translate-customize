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
    property bool pinned: false
    property string notice: ""
    function languageName(code) {
        for (let item of quickTranslateModel.languages) if (item.code === code) return item.name
        return code
    }
    Timer { id: copyTimer; interval: 2000; onTriggered: popup.notice = "" }

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
    onActiveChanged: if (!active && closeArmed && !pinned) popup.close()

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
                    text: popup.languageName(quickTranslateModel.detectedSourceLanguage || quickTranslateModel.sourceLanguage) + " → " + popup.languageName(quickTranslateModel.targetLanguage)
                    color: "#6b7480"
                    font.pixelSize: 11
                    Layout.fillWidth: true
                    elide: Text.ElideRight
                }
                ActionButton { symbol: "pin"; primary: popup.pinned; ToolTip.text: popup.pinned ? "Unpin popup" : "Keep popup open"; onClicked: popup.pinned = !popup.pinned }
                ActionButton { symbol: "copy"; enabled: quickTranslateModel.translatedText.length > 0; ToolTip.text: "Copy translation"; onClicked: { quickTranslateModel.copyTranslated(); popup.notice = "Copied to clipboard"; copyTimer.restart() } }
                ActionButton { symbol: "close"; ToolTip.text: "Close popup"; onClicked: popup.close() }
            }

            Label { visible: quickTranslateModel.busy || popup.notice.length > 0; text: popup.notice || "Translating…"; color: "#0d897e" }
            Label { Layout.fillWidth: true; visible: quickTranslateModel.error.length > 0; text: quickTranslateModel.error; color: "#a03927"; wrapMode: Text.Wrap; maximumLineCount: 3; elide: Text.ElideRight }
            ActionButton { visible: quickTranslateModel.error.length > 0; text: "Retry"; enabled: !quickTranslateModel.busy; onClicked: quickTranslateModel.translate() }
            ScrollView {
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                TextArea {
                    readOnly: true
                    wrapMode: TextEdit.Wrap
                    font.pixelSize: 14
                    color: "#182b3a"
                    placeholderTextColor: "#637587"
                    background: Item {}
                    text: quickTranslateModel.translatedText
                    placeholderText: quickTranslateModel.busy ? "Translating…" : "Translation"
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
