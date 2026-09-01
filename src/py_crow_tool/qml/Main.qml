import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ApplicationWindow {
    id: root
    width: 980
    height: 620
    minimumWidth: 720
    minimumHeight: 480
    visible: true
    title: "PyCrow Tool"
    color: "#f4f5f7"

    header: ToolBar {
        height: 52
        background: Rectangle { color: "#20242a" }
        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 18
            anchors.rightMargin: 12
            Label { text: "PyCrow Tool"; color: "white"; font.pixelSize: 18; font.bold: true }
            Item { Layout.fillWidth: true }
            Label { text: translationModel.status; color: "#c8d0d9"; elide: Text.ElideRight; Layout.maximumWidth: 320 }
            ToolButton { text: "History"; onClicked: historyDrawer.open(); palette.buttonText: "white" }
            ToolButton { text: "Settings"; onClicked: settingsDialog.open(); palette.buttonText: "white" }
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 18
        spacing: 12

        RowLayout {
            Layout.fillWidth: true
            ComboBox {
                id: sourceLanguage
                Layout.preferredWidth: 220
                model: translationModel.languages
                textRole: "name"
                valueRole: "code"
                Component.onCompleted: currentIndex = indexOfValue(translationModel.sourceLanguage)
                onActivated: translationModel.sourceLanguage = currentValue
            }
            ToolButton { text: "Swap"; enabled: translationModel.sourceLanguage !== "auto"; onClicked: translationModel.swapLanguages() }
            ComboBox {
                id: targetLanguage
                Layout.preferredWidth: 220
                model: translationModel.languages.slice(1)
                textRole: "name"
                valueRole: "code"
                Component.onCompleted: currentIndex = indexOfValue(translationModel.targetLanguage)
                onActivated: translationModel.targetLanguage = currentValue
            }
            Item { Layout.fillWidth: true }
            Button { text: "OCR clipboard"; onClicked: ocrService.recognizeClipboardImage() }
        }

        SplitView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            orientation: Qt.Horizontal

            Pane {
                SplitView.fillWidth: true
                SplitView.minimumWidth: 280
                padding: 0
                TextArea {
                    anchors.fill: parent
                    anchors.margins: 14
                    placeholderText: "Enter text"
                    wrapMode: TextEdit.Wrap
                    font.pixelSize: 18
                    text: translationModel.sourceText
                    onTextChanged: if (activeFocus) translationModel.sourceText = text
                }
            }
            Pane {
                SplitView.fillWidth: true
                SplitView.minimumWidth: 280
                padding: 0
                TextArea {
                    anchors.fill: parent
                    anchors.margins: 14
                    readOnly: true
                    selectByMouse: true
                    wrapMode: TextEdit.Wrap
                    font.pixelSize: 18
                    text: translationModel.translatedText
                    placeholderText: "Translation"
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            BusyIndicator { running: translationModel.busy; visible: running; Layout.preferredWidth: 36; Layout.preferredHeight: 36 }
            Item { Layout.fillWidth: true }
            ToolButton { text: "Speak source"; onClicked: ttsService.speak(translationModel.sourceText, translationModel.sourceLanguage) }
            ToolButton { text: "Speak result"; onClicked: ttsService.speak(translationModel.translatedText, translationModel.targetLanguage) }
            Button { text: translationModel.busy ? "Translating" : "Translate"; enabled: !translationModel.busy && translationModel.sourceText.trim().length > 0; onClicked: translationModel.translate() }
        }
    }

    Drawer {
        id: historyDrawer
        edge: Qt.RightEdge
        width: Math.min(root.width * 0.42, 420)
        height: root.height
        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 14
            RowLayout {
                Layout.fillWidth: true
                Label { text: "History"; font.pixelSize: 20; font.bold: true }
                Item { Layout.fillWidth: true }
                Button { text: "Clear"; onClicked: translationModel.clearHistory() }
            }
            ListView {
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                spacing: 8
                model: translationModel.history
                delegate: ItemDelegate {
                    width: ListView.view.width
                    height: content.implicitHeight + 20
                    contentItem: Column {
                        id: content
                        spacing: 4
                        Label { width: parent.width; text: modelData.source; elide: Text.ElideRight; font.bold: true }
                        Label { width: parent.width; text: modelData.translation; wrapMode: Text.Wrap; color: "#49515a" }
                        Label { text: modelData.provider_id; font.pixelSize: 11; color: "#747d87" }
                    }
                }
            }
        }
    }

    Dialog {
        id: settingsDialog
        title: "Google Cloud settings"
        modal: true
        anchors.centerIn: parent
        width: Math.min(root.width - 40, 560)
        standardButtons: Dialog.Save | Dialog.Cancel
        onAccepted: { settingsModel.save(); translationModel.savePreferences() }
        ColumnLayout {
            width: parent.width
            spacing: 10
            Label { text: "Advanced v3"; font.bold: true }
            TextField { Layout.fillWidth: true; placeholderText: "Google Cloud project ID"; text: settingsModel.projectId; onTextChanged: settingsModel.projectId = text }
            TextField { Layout.fillWidth: true; placeholderText: "Location (global)"; text: settingsModel.location; onTextChanged: settingsModel.location = text }
            TextField { Layout.fillWidth: true; placeholderText: "Service account JSON path (blank for ADC)"; text: settingsModel.credentialsFile; onTextChanged: settingsModel.credentialsFile = text }
            Label { text: "Basic v2 fallback"; font.bold: true; Layout.topMargin: 8 }
            TextField { Layout.fillWidth: true; placeholderText: "API key"; echoMode: TextInput.Password; text: settingsModel.apiKey; onTextChanged: settingsModel.apiKey = text }
            Label { Layout.fillWidth: true; wrapMode: Text.Wrap; color: "#a2462e"; text: "Credentials are stored in a user-readable settings file. Restrict access to your Windows account." }
        }
    }

    Connections {
        target: ocrService
        function onFailed(message) { translationModel.sourceText = message }
    }
}
