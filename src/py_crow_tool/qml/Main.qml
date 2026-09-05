import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ApplicationWindow {
    id: root
    width: 1040; height: 700
    minimumWidth: 720; minimumHeight: 540
    visible: true
    title: "PyCrow Tool"
    color: "#f3f6f8"
    font.family: "Sans Serif"
    font.pixelSize: 13
    palette.window: "#f3f6f8"
    palette.text: "#182b3a"
    palette.windowText: "#182b3a"
    palette.buttonText: "#182b3a"
    palette.button: "#edf2f6"
    palette.base: "white"
    palette.placeholderText: "#637587"
    palette.highlight: "#0d897e"
    property bool restoring: false
    property string notice: ""
    function languageName(code) {
        for (let item of translationModel.languages) if (item.code === code) return item.name
        return code
    }
    function copied() { notice = "Copied to clipboard"; noticeTimer.restart() }
    function schedule() { if (settingsModel.autoTranslate && !restoring) autoTimer.restart() }
    Timer { id: noticeTimer; interval: 2200; onTriggered: root.notice = "" }
    Timer { id: autoTimer; interval: 600; onTriggered: translationModel.translate() }
    Shortcut { sequence: "Ctrl+Return"; onActivated: translationModel.translate() }
    Shortcut { sequence: "Ctrl+L"; onActivated: sourceEditor.forceActiveFocus() }
    Connections {
        target: translationModel
        function onSourceTextChanged() { root.schedule() }
        function onSourceLanguageChanged() { root.schedule() }
        function onTargetLanguageChanged() { root.schedule() }
    }
    Connections { target: ocrService; function onFailed(message) { translationModel.reportError(message) } }

    component LanguagePicker: ComboBox {
        Layout.fillWidth: true
        implicitHeight: 40
        textRole: "name"; valueRole: "code"
        font.pixelSize: 14
        background: Rectangle { color: "white"; radius: 8; border.color: parent.activeFocus ? "#0d897e" : "#dce4eb" }
    }
    component SettingsField: TextField {
        implicitHeight: 40
        background: Rectangle { radius: 8; color: "white"; border.color: parent.activeFocus ? "#0d897e" : "#dce4eb" }
    }
    component Caption: Label { color: "#637587"; font.pixelSize: 11; font.weight: Font.DemiBold }

    ColumnLayout {
        anchors.fill: parent; anchors.margins: 24; spacing: 18
        RowLayout {
            Layout.fillWidth: true
            Image {
                source: "app-icon.png"
                Layout.preferredWidth: 36; Layout.preferredHeight: 36
                sourceSize.width: 72; sourceSize.height: 72
                fillMode: Image.PreserveAspectFit
                mipmap: true
                Accessible.name: "PyCrow application icon"
            }
            ColumnLayout {
                spacing: 1
                Label { text: "PyCrow"; font.pixelSize: 21; font.bold: true; color: "#182b3a" }
                Label { text: "A little clarity, in any language."; color: "#637587"; font.pixelSize: 12 }
            }
            Item { Layout.fillWidth: true }
            ActionButton { text: "History"; symbol: "history"; onClicked: historyDrawer.open() }
            ActionButton { text: "Settings"; symbol: "settings"; onClicked: settingsDialog.open() }
        }
        Rectangle {
            visible: settingsModel.apiKey.length === 0 && translationModel.status.indexOf("Configure") === 0
            Layout.fillWidth: true; implicitHeight: setupRow.implicitHeight + 24
            color: "#e5f3f0"; radius: 10
            RowLayout {
                id: setupRow; anchors.fill: parent; anchors.margins: 12
                Label { Layout.fillWidth: true; wrapMode: Text.Wrap; text: "Welcome! Connect Google Cloud to start translating."; color: "#18675f" }
                ActionButton { text: "Set up translation"; primary: true; onClicked: settingsDialog.open() }
            }
        }
        RowLayout {
            Layout.fillWidth: true; spacing: 16
            LanguagePicker {
                id: sourceLanguage; objectName: "sourceLanguage"; model: translationModel.languages
                currentIndex: translationModel.languages.findIndex(item => item.code === translationModel.sourceLanguage)
                onActivated: translationModel.sourceLanguage = currentValue
                Accessible.name: "Source language"
            }
            ActionButton {
                symbol: "swap"; ToolTip.text: "Swap languages"
                enabled: translationModel.sourceLanguage !== "auto" || translationModel.detectedSourceLanguage.length > 0
                onClicked: translationModel.swapLanguages()
            }
            LanguagePicker {
                id: targetLanguage; objectName: "targetLanguage"; model: translationModel.languages.slice(1)
                currentIndex: translationModel.languages.slice(1).findIndex(item => item.code === translationModel.targetLanguage)
                onActivated: translationModel.targetLanguage = currentValue
                Accessible.name: "Target language"
            }

        }
        RowLayout {
            Layout.fillWidth: true; Layout.fillHeight: true; spacing: 16
            Rectangle {
                Layout.fillWidth: true; Layout.fillHeight: true; Layout.preferredWidth: 1
                color: "white"; radius: 12; border.color: sourceEditor.activeFocus ? "#6bb8ae" : "#dce4eb"
                ColumnLayout {
                    anchors.fill: parent; anchors.margins: 16; spacing: 10
                    RowLayout {
                        Layout.fillWidth: true
                        Caption { text: "SOURCE TEXT" }
                        Label { text: translationModel.detectedSourceLanguage ? "Detected: " + root.languageName(translationModel.detectedSourceLanguage) : ""; color: "#0d897e"; font.pixelSize: 11; Layout.fillWidth: true; elide: Text.ElideRight }
                        ActionButton { symbol: "close"; ToolTip.text: "Clear text and translation"; enabled: translationModel.sourceText.length > 0 || translationModel.translatedText.length > 0; onClicked: translationModel.clearAll() }
                    }
                    ScrollView {
                        Layout.fillWidth: true; Layout.fillHeight: true; clip: true
                        TextArea {
                            id: sourceEditor; objectName: "sourceEditor"
                            text: translationModel.sourceText
                            onTextChanged: if (activeFocus) translationModel.sourceText = text
                            placeholderText: "Type or paste text here…"
                            placeholderTextColor: "#8b99a7"
                            wrapMode: TextEdit.Wrap; selectByMouse: true
                            font.pixelSize: 19; color: "#182b3a"
                            background: Item {}
                            Accessible.name: "Source text"
                        }
                    }
                    RowLayout {
                        Layout.fillWidth: true; spacing: 2
                        ActionButton { text: "Paste"; symbol: "paste"; onClicked: translationModel.pasteSource() }
                        ActionButton { symbol: "scan"; ToolTip.text: "Read text from clipboard image"; onClicked: ocrService.recognizeClipboardImage() }
                        ActionButton { symbol: "speaker"; ToolTip.text: ttsService.speaking ? "Stop speaking" : "Read source aloud"; enabled: translationModel.sourceText.length > 0; onClicked: ttsService.speaking ? ttsService.stop() : ttsService.speak(translationModel.sourceText, translationModel.detectedSourceLanguage || translationModel.sourceLanguage) }
                        ActionButton { symbol: "copy"; ToolTip.text: "Copy source"; enabled: translationModel.sourceText.length > 0; onClicked: { translationModel.copySource(); root.copied() } }
                        Item { Layout.fillWidth: true }
                        Caption { text: translationModel.sourceText.length + " chars" }
                    }
                }
            }
            Rectangle {
                Layout.fillWidth: true; Layout.fillHeight: true; Layout.preferredWidth: 1
                color: "#fafdfe"; radius: 12; border.color: "#dce4eb"
                ColumnLayout {
                    anchors.fill: parent; anchors.margins: 16; spacing: 10
                    RowLayout {
                        Layout.fillWidth: true; Layout.minimumHeight: 36
                        Caption { text: "TRANSLATION" }
                        Item { Layout.fillWidth: true }
                        BusyIndicator { visible: translationModel.busy; running: visible; implicitWidth: 24; implicitHeight: 24 }
                        Label { visible: translationModel.busy; text: "Updating…"; color: "#0d897e"; font.pixelSize: 12 }
                    }
                    ScrollView {
                        Layout.fillWidth: true; Layout.fillHeight: true; clip: true
                        TextArea {
                            text: translationModel.translatedText
                            readOnly: true; selectByMouse: true; wrapMode: TextEdit.Wrap
                            placeholderText: "Your translation will appear here."
                            placeholderTextColor: "#8b99a7"
                            font.pixelSize: 19; color: "#182b3a"; background: Item {}
                            Accessible.name: "Translation"
                        }
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        ActionButton { symbol: "speaker"; ToolTip.text: ttsService.speaking ? "Stop speaking" : "Read translation aloud"; enabled: translationModel.translatedText.length > 0; onClicked: ttsService.speaking ? ttsService.stop() : ttsService.speak(translationModel.translatedText, translationModel.targetLanguage) }
                        Item { Layout.fillWidth: true }
                        ActionButton { text: "Copy translation"; symbol: "copy"; enabled: translationModel.translatedText.length > 0; onClicked: { translationModel.copyTranslated(); root.copied() } }
                    }
                }
            }
        }
        Rectangle {
            Layout.fillWidth: true; implicitHeight: errorRow.implicitHeight + 20
            visible: translationModel.error.length > 0; color: "#fff0ec"; radius: 8
            RowLayout {
                id: errorRow; anchors.fill: parent; anchors.margins: 10
                Label { Layout.fillWidth: true; text: translationModel.error; wrapMode: Text.Wrap; color: "#a03927"; maximumLineCount: 3; elide: Text.ElideRight; ToolTip.text: text; ToolTip.visible: errorHover.hovered; HoverHandler { id: errorHover } }
                ActionButton { text: "Retry"; enabled: !translationModel.busy; onClicked: translationModel.translate() }
                ActionButton { text: "Settings"; onClicked: settingsDialog.open() }
                ActionButton { symbol: "close"; ToolTip.text: "Dismiss error"; onClicked: translationModel.reportError("") }
            }
        }
        RowLayout {
            Layout.fillWidth: true
            Label { Layout.fillWidth: true; text: root.notice || translationModel.status; color: root.notice ? "#0d897e" : "#637587"; elide: Text.ElideRight }
            Switch {
                text: "Auto-translate"; checked: settingsModel.autoTranslate
                onToggled: { settingsModel.autoTranslate = checked; settingsModel.save(); if (checked) root.schedule(); else autoTimer.stop() }
            }
            Caption { text: "Ctrl + Enter" }
            ActionButton { text: "Translate"; symbol: "arrow"; primary: true; enabled: !translationModel.busy && translationModel.sourceText.trim().length > 0; onClicked: { autoTimer.stop(); translationModel.translate() } }
        }
    }
    Drawer {
        id: historyDrawer; objectName: "historyDrawer"; edge: Qt.RightEdge; width: Math.min(root.width - 48, 420); height: root.height
        ColumnLayout {
            anchors.fill: parent; anchors.margins: 20; spacing: 16
            RowLayout {
                Label { text: "History"; font.pixelSize: 22; font.bold: true }
                Item { Layout.fillWidth: true }
                ActionButton { text: "Clear all"; enabled: translationModel.history.length > 0; onClicked: clearHistoryDialog.open() }
                ActionButton { symbol: "close"; ToolTip.text: "Close history"; onClicked: historyDrawer.close() }
            }
            TextField { id: historySearch; objectName: "historySearch"; Layout.fillWidth: true; placeholderText: "Search translations…"; Accessible.name: "Search history" }
            Label { visible: historyList.count === 0; text: historySearch.text ? "No matching translations." : "Your translations will be saved here."; color: "#637587"; Layout.fillWidth: true; wrapMode: Text.Wrap }
            ListView {
                id: historyList; objectName: "historyList"; Layout.fillWidth: true; Layout.fillHeight: true; clip: true; spacing: 8
                model: translationModel.history.filter(item => (item.source + " " + item.translation).toLowerCase().indexOf(historySearch.text.toLowerCase()) >= 0)
                delegate: ItemDelegate {
                    required property var modelData
                    width: ListView.view.width
                    implicitHeight: historyContent.implicitHeight + 24
                    onClicked: {
                        root.restoring = true; autoTimer.stop()
                        translationModel.restoreHistory(modelData.source, modelData.translation, modelData.source_language, modelData.target_language)
                        root.restoring = false; historyDrawer.close()
                    }
                    contentItem: ColumnLayout {
                        id: historyContent; spacing: 6
                        Caption { text: root.languageName(modelData.source_language) + " → " + root.languageName(modelData.target_language) }
                        Label { Layout.fillWidth: true; text: modelData.source; elide: Text.ElideRight; font.bold: true }
                        Label { Layout.fillWidth: true; text: modelData.translation; wrapMode: Text.Wrap; maximumLineCount: 3; elide: Text.ElideRight; color: "#637587" }
                        Caption { text: "Click to restore · " + modelData.created_at.slice(0, 10) }
                    }
                }
            }
        }
    }
    Dialog {
        id: clearHistoryDialog; title: "Clear translation history?"; modal: true; anchors.centerIn: parent
        standardButtons: Dialog.Ok | Dialog.Cancel
        Label { text: "This removes all saved translations." }
        onAccepted: translationModel.clearHistory()
    }
    Dialog {
        id: settingsDialog; objectName: "settingsDialog"; title: "Settings"; modal: true; anchors.centerIn: parent
        width: Math.min(root.width - 48, 520); height: Math.min(root.height - 48, 530)
        padding: 20
        background: Rectangle { color: "#f8fafb"; radius: 12; border.color: "#dce4eb" }
        footer: DialogButtonBox {
            padding: 16; spacing: 8
            background: Item {}
            ActionButton { text: "Cancel"; DialogButtonBox.buttonRole: DialogButtonBox.RejectRole }
            ActionButton { text: "Save changes"; primary: true; enabled: !hotkey.recording; DialogButtonBox.buttonRole: DialogButtonBox.AcceptRole }
        }
        onOpened: { showKey.checked = false; apiKey.text = settingsModel.apiKey; startup.checked = settingsModel.startWithSystem; hotkey.sequence = settingsModel.quickTranslateHotkey; hotkey.error = "" }
        onClosed: hotkey.recording = false
        onAccepted: {
            settingsModel.apiKey = apiKey.text.trim()
            settingsModel.startWithSystem = startup.checked
            settingsModel.quickTranslateHotkey = hotkey.sequence
            settingsModel.save(); translationModel.savePreferences()
        }
        ScrollView {
            anchors.fill: parent; clip: true; contentWidth: availableWidth
            ColumnLayout {
                width: parent.width; spacing: 12
                Label { text: "Translation service"; font.bold: true; font.pixelSize: 16 }
                Label { Layout.fillWidth: true; text: "Connect a Google Cloud Translation API key to translate text."; wrapMode: Text.Wrap; color: "#637587" }
                Label { text: "API key" }
                SettingsField { id: apiKey; objectName: "apiKey"; Layout.fillWidth: true; placeholderText: "Enter your API key"; echoMode: showKey.checked ? TextInput.Normal : TextInput.Password; Accessible.name: "Google Cloud API key" }
                CheckBox { id: showKey; text: "Show key"; checked: false }
                Label { text: "Desktop"; font.bold: true; font.pixelSize: 16; Layout.topMargin: 8 }
                CheckBox { id: startup; objectName: "startup"; text: "Start with system" }
                Label { text: "Quick-translate shortcut" }
                ActionButton {
                    id: hotkey; objectName: "hotkey"; Layout.fillWidth: true
                    property string sequence: ""
                    property bool recording: false
                    property string error: ""
                    text: recording ? "Press a shortcut… (Esc to cancel)" : sequence + "  ·  Click to change"
                    Accessible.name: "Quick translate shortcut. " + text
                    onClicked: { error = ""; recording = true; forceActiveFocus() }
                    onRecordingChanged: settingsModel.recordingHotkey = recording
                    onActiveFocusChanged: { if (!activeFocus) recording = false }
                    Keys.priority: Keys.BeforeItem
                    Keys.onShortcutOverride: function(event) { if (recording) event.accepted = true }
                    Keys.onPressed: function(event) {
                        if (!recording) return
                        event.accepted = true
                        if (event.isAutoRepeat) return
                        if (event.key === Qt.Key_Escape) { recording = false; error = ""; return }
                        if ([Qt.Key_Control, Qt.Key_Alt, Qt.Key_Shift, Qt.Key_Meta].indexOf(event.key) !== -1) return
                        let captured = settingsModel.captureHotkey(event.key, event.modifiers)
                        if (!captured) {
                            error = "Use Ctrl, Alt, Shift or Win with a letter, number or navigation key, or use F1–F24."
                            return
                        }
                        if (settingsModel.hotkeyConflicts(captured)) {
                            error = "This shortcut is already used for clipboard translation. Choose another."
                            return
                        }
                        sequence = captured
                        error = ""
                        recording = false
                    }
                    Keys.onReleased: function(event) { event.accepted = true }
                }
                Label { Layout.fillWidth: true; visible: hotkey.error.length > 0; text: hotkey.error; wrapMode: Text.Wrap; color: "#b42318" }
                Label { Layout.fillWidth: true; wrapMode: Text.Wrap; color: "#637587"; text: "Select text in another app and press this shortcut. Shortcut changes apply after restarting PyCrow." }
                Label { Layout.fillWidth: true; wrapMode: Text.Wrap; color: "#637587"; font.pixelSize: 11; text: "Your API key is stored locally in your user settings file." }
            }
        }
    }
}
