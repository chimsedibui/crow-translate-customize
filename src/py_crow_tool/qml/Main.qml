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

    readonly property var flags: ({
        "auto": "🌐", "ar": "🇸🇦", "zh-CN": "🇨🇳", "zh-TW": "🇹🇼", "nl": "🇳🇱", "en": "🇬🇧",
        "fr": "🇫🇷", "de": "🇩🇪", "hi": "🇮🇳", "id": "🇮🇩", "it": "🇮🇹", "ja": "🇯🇵",
        "ko": "🇰🇷", "pl": "🇵🇱", "pt": "🇵🇹", "ru": "🇷🇺", "es": "🇪🇸", "th": "🇹🇭",
        "tr": "🇹🇷", "vi": "🇻🇳"
    })

    function flagFor(code) { return flags[code] || "🌐" }

    function languageName(code) {
        for (let i = 0; i < translationModel.languages.length; i++) {
            if (translationModel.languages[i].code === code) return translationModel.languages[i].name
        }
        return code
    }

    component LanguageChip: ComboBox {
        id: chip
        Layout.preferredWidth: 210
        Layout.preferredHeight: 36
        textRole: "name"
        valueRole: "code"
        property string overrideText: ""
        background: Rectangle {
            radius: 18
            color: chip.pressed ? "#dde1e6" : (chip.hovered ? "#e6e9ed" : "#eef0f3")
            border.color: "#d5d9de"
        }
        contentItem: RowLayout {
            spacing: 6
            anchors.fill: parent
            anchors.leftMargin: 14
            anchors.rightMargin: 6
            Label { text: flagFor(chip.currentValue); font.pixelSize: 15 }
            Label {
                Layout.fillWidth: true
                text: chip.overrideText.length > 0 ? chip.overrideText : chip.currentText
                elide: Text.ElideRight
                font.pixelSize: 13
                color: "#20242a"
            }
        }
    }

    header: ToolBar {
        height: 44
        background: Rectangle { color: "#20242a" }
        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 18
            anchors.rightMargin: 12
            Label { text: "PyCrow Tool"; color: "white"; font.pixelSize: 16; font.bold: true }
            Item { Layout.fillWidth: true }
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 18
        spacing: 12

        RowLayout {
            Layout.fillWidth: true
            spacing: 6

            ToolButton {
                text: "✎"
                ToolTip.text: "Choose source language"
                ToolTip.visible: hovered
                onClicked: sourceLanguage.popup.open()
            }
            LanguageChip {
                id: sourceLanguage
                model: translationModel.languages
                overrideText: currentValue === "auto" && translationModel.detectedSourceLanguage.length > 0
                    ? "Auto (" + languageName(translationModel.detectedSourceLanguage) + ")"
                    : ""
                Component.onCompleted: currentIndex = indexOfValue(translationModel.sourceLanguage)
                onActivated: translationModel.sourceLanguage = currentValue
            }

            Item { Layout.fillWidth: true }
            CheckBox {
                text: "Auto-translation"
                checked: settingsModel.autoTranslate
                onToggled: { settingsModel.autoTranslate = checked; settingsModel.save() }
            }
            Item { Layout.fillWidth: true }

            LanguageChip {
                id: targetLanguage
                model: translationModel.languages.slice(1)
                Component.onCompleted: currentIndex = indexOfValue(translationModel.targetLanguage)
                onActivated: translationModel.targetLanguage = currentValue
            }
            ToolButton {
                text: "✎"
                ToolTip.text: "Choose target language"
                ToolTip.visible: hovered
                onClicked: targetLanguage.popup.open()
            }
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
                    id: sourceArea
                    anchors.fill: parent
                    anchors.margins: 14
                    placeholderText: "Enter text"
                    wrapMode: TextEdit.Wrap
                    font.pixelSize: 18
                    text: translationModel.sourceText
                    onTextChanged: {
                        if (activeFocus) {
                            translationModel.sourceText = text
                            if (settingsModel.autoTranslate) autoTranslateTimer.restart()
                        }
                    }
                }
                Timer { id: autoTranslateTimer; interval: 600; onTriggered: translationModel.translate() }
            }

            Pane {
                SplitView.preferredWidth: 52
                SplitView.minimumWidth: 52
                SplitView.maximumWidth: 52
                padding: 0
                ColumnLayout {
                    anchors.centerIn: parent
                    spacing: 10
                    ToolButton {
                        text: "⇄"
                        font.pixelSize: 18
                        Layout.alignment: Qt.AlignHCenter
                        enabled: translationModel.sourceLanguage !== "auto"
                        ToolTip.text: "Swap languages"
                        ToolTip.visible: hovered
                        onClicked: translationModel.swapLanguages()
                    }
                    ToolButton {
                        text: "⊗"
                        font.pixelSize: 18
                        Layout.alignment: Qt.AlignHCenter
                        ToolTip.text: "Clear source"
                        ToolTip.visible: hovered
                        onClicked: translationModel.clearSource()
                    }
                    ToolButton {
                        text: "→"
                        font.pixelSize: 18
                        Layout.alignment: Qt.AlignHCenter
                        enabled: !translationModel.busy && translationModel.sourceText.trim().length > 0
                        ToolTip.text: "Translate"
                        ToolTip.visible: hovered
                        onClicked: translationModel.translate()
                    }
                    ToolButton {
                        text: "✕"
                        font.pixelSize: 18
                        Layout.alignment: Qt.AlignHCenter
                        ToolTip.text: "Clear both"
                        ToolTip.visible: hovered
                        onClicked: translationModel.clearAll()
                    }
                }
            }

            Pane {
                SplitView.fillWidth: true
                SplitView.minimumWidth: 280
                padding: 0
                TextArea {
                    id: translatedArea
                    anchors.fill: parent
                    anchors.margins: 14
                    readOnly: true
                    selectByMouse: true
                    wrapMode: TextEdit.Wrap
                    font.pixelSize: 18
                    text: translationModel.busy ? "Translating..." : translationModel.translatedText
                    placeholderText: "Translation"
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 4
            ToolButton { text: "▶"; ToolTip.text: "Speak source"; ToolTip.visible: hovered; onClicked: ttsService.speak(translationModel.sourceText, translationModel.sourceLanguage) }
            ToolButton { text: "■"; ToolTip.text: "Stop speaking"; ToolTip.visible: hovered; onClicked: ttsService.stop() }
            ToolButton { text: "⎘"; ToolTip.text: "Copy source"; ToolTip.visible: hovered; onClicked: translationModel.copySource() }
            ToolButton { text: "📋"; ToolTip.text: "Paste"; ToolTip.visible: hovered; onClicked: translationModel.pasteSource() }
            BusyIndicator { running: translationModel.busy; visible: running; Layout.preferredWidth: 24; Layout.preferredHeight: 24 }

            Item { Layout.fillWidth: true }
            Label { text: translationModel.status; color: "#747d87"; elide: Text.ElideRight; Layout.maximumWidth: 220 }
            Item { Layout.fillWidth: true }

            ComboBox { Layout.preferredWidth: 120; model: ["Google"] }
            ToolButton { text: "▶"; ToolTip.text: "Speak result"; ToolTip.visible: hovered; onClicked: ttsService.speak(translationModel.translatedText, translationModel.targetLanguage) }
            ToolButton { text: "■"; ToolTip.text: "Stop speaking"; ToolTip.visible: hovered; onClicked: ttsService.stop() }
            ToolButton { text: "⎘"; ToolTip.text: "Copy translation"; ToolTip.visible: hovered; onClicked: translationModel.copyTranslated() }
            ToolButton { text: "🖼"; ToolTip.text: "OCR clipboard image"; ToolTip.visible: hovered; onClicked: ocrService.recognizeClipboardImage() }
            ToolButton { text: "🕘"; ToolTip.text: "History"; ToolTip.visible: hovered; onClicked: historyDrawer.open() }
            ToolButton { text: "⚙"; ToolTip.text: "Settings"; ToolTip.visible: hovered; onClicked: settingsDialog.open() }
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
            Label { text: "Desktop behavior"; font.bold: true; Layout.topMargin: 8 }
            CheckBox { text: "Start with system"; checked: settingsModel.startWithSystem; onToggled: settingsModel.startWithSystem = checked }
            TextField { Layout.fillWidth: true; placeholderText: "Quick-translate hotkey (e.g. ctrl+alt+q)"; text: settingsModel.quickTranslateHotkey; onTextChanged: settingsModel.quickTranslateHotkey = text }
            Label { Layout.fillWidth: true; wrapMode: Text.Wrap; color: "#747d87"; font.pixelSize: 11; text: "Select text anywhere, press the hotkey, and a translation popup appears near the cursor. Hotkey changes take effect after restart." }
            Label { Layout.fillWidth: true; wrapMode: Text.Wrap; color: "#a2462e"; text: "Credentials are stored in a user-readable settings file. Restrict access to your Windows account." }
        }
    }

    Connections {
        target: ocrService
        function onFailed(message) { translationModel.sourceText = message }
    }
}
