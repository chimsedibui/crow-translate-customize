import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "."

ApplicationWindow {
    id: root
    width: 1040; height: 700
    minimumWidth: 720; minimumHeight: 540
    visible: true
    title: "PyCrow Tool"
    color: Theme.surface
    palette.window: Theme.surface
    palette.text: Theme.ink
    palette.windowText: Theme.ink
    palette.buttonText: Theme.ink
    palette.button: Theme.controlHover
    palette.base: Theme.raised
    palette.placeholderText: Theme.placeholder
    palette.highlight: Theme.accent
    palette.highlightedText: Theme.accentInk
    property bool restoring: false
    property string notice: ""
    function languageName(code) {
        for (let item of translationModel.languages) if (item.code === code) return item.name
        return code
    }
    function copied() { notice = "Copied to clipboard"; noticeTimer.restart() }
    // A pane is headed by the language it actually holds. For the source that is the
    // detected language once one is known, since "Detect language" stops being true
    // the moment detection resolves.
    function sourceLabel() {
        if (translationModel.detectedSourceLanguage) return root.languageName(translationModel.detectedSourceLanguage)
        if (translationModel.sourceLanguage === "auto") return "Auto-detect"
        return root.languageName(translationModel.sourceLanguage)
    }
    function sourceCode() {
        const code = translationModel.detectedSourceLanguage || translationModel.sourceLanguage
        return code === "auto" ? "AUTO" : code.toUpperCase()
    }
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
        implicitHeight: Theme.fieldHeight
        textRole: "name"; valueRole: "code"
        font.pixelSize: Theme.sizeControl
        background: Surface {
            radius: Theme.radiusSmall
            border.color: parent.activeFocus ? Theme.focusRing : Theme.hairline
            level: parent.activeFocus ? 1 : 0
        }
    }
    component SettingsField: TextField {
        implicitHeight: Theme.fieldHeight
        background: Surface {
            radius: Theme.radiusSmall
            border.color: parent.activeFocus ? Theme.focusRing : Theme.hairline
            level: parent.activeFocus ? 1 : 0
        }
    }
    component Caption: Label { color: Theme.muted; font.pixelSize: Theme.sizeCaption; font.weight: Theme.weightMedium }
    // The language code is data, so it is set in the mono face. It carries the accent
    // only when the language was inferred rather than chosen -- and because that is the
    // app working something out on the user's behalf, the change is worth a moment:
    // the chip takes the accent over durationBase and swells six percent on the way.
    component LanguageCode: Rectangle {
        id: chip
        property string code: ""
        property bool detected: false
        implicitWidth: codeLabel.implicitWidth + 12
        implicitHeight: codeLabel.implicitHeight + 6
        radius: Theme.radiusChip
        color: detected ? Theme.accentSoft : Theme.controlHover
        Behavior on color { ColorAnimation { duration: Theme.motion(Theme.durationBase); easing.type: Theme.easingCurve } }
        onDetectedChanged: if (detected && !Theme.reduceMotion) chipPop.restart()
        SequentialAnimation {
            id: chipPop
            NumberAnimation { target: chip; property: "scale"; to: 1.06; duration: Theme.durationBase * 0.45; easing.type: Theme.easingCurve }
            NumberAnimation { target: chip; property: "scale"; to: 1.0; duration: Theme.durationBase * 0.55; easing.type: Theme.easingCurve }
        }
        Label {
            id: codeLabel; anchors.centerIn: parent; text: chip.code
            font.family: Theme.monoFamily; font.pixelSize: Theme.sizeCaption
            color: chip.detected ? Theme.accentSoftInk : Theme.muted
            Behavior on color { ColorAnimation { duration: Theme.motion(Theme.durationBase); easing.type: Theme.easingCurve } }
        }
    }

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
                Label { text: "PyCrow"; font.family: Theme.displayFamily; font.pixelSize: Theme.sizeTitle; font.weight: Theme.weightBold; color: Theme.ink }
                Label { text: "A little clarity, in any language."; color: Theme.muted; font.pixelSize: Theme.sizeCaption }
            }
            Item { Layout.fillWidth: true }
            ActionButton { text: "History"; symbol: "history"; onClicked: historyDrawer.open() }
            ActionButton { text: "Settings"; symbol: "settings"; onClicked: settingsDialog.open() }
        }
        Rectangle {
            visible: settingsModel.apiKey.length === 0 && translationModel.status.indexOf("Configure") === 0
            Layout.fillWidth: true; implicitHeight: setupRow.implicitHeight + 24
            color: Theme.accentSoft; radius: Theme.radiusSmall
            RowLayout {
                id: setupRow; anchors.fill: parent; anchors.margins: 12
                Label { Layout.fillWidth: true; wrapMode: Text.Wrap; text: "Welcome! Connect Google Cloud to start translating."; color: Theme.accentSoftInk }
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
            // The one control in the app whose entire meaning is "reverse direction", so
            // it is one of the two places the spring is allowed. The turn accumulates
            // rather than toggling between 0 and 180: consecutive swaps then keep going
            // the same way instead of rocking back and forth.
            ActionButton {
                id: swapButton
                symbol: "swap"; ToolTip.text: "Swap languages"
                enabled: translationModel.sourceLanguage !== "auto" || translationModel.detectedSourceLanguage.length > 0
                onClicked: { rotation += 180; translationModel.swapLanguages() }
                Behavior on rotation {
                    NumberAnimation {
                        duration: Theme.motion(Theme.durationBase)
                        easing.type: Theme.easingSpring
                        easing.overshoot: Theme.springOvershoot
                    }
                }
            }
            LanguagePicker {
                id: targetLanguage; objectName: "targetLanguage"; model: translationModel.languages.slice(1)
                currentIndex: translationModel.languages.slice(1).findIndex(item => item.code === translationModel.targetLanguage)
                onActivated: translationModel.targetLanguage = currentValue
                Accessible.name: "Target language"
            }

        }
        SplitView {
            id: panes
            Layout.fillWidth: true; Layout.fillHeight: true
            orientation: Qt.Horizontal
            handle: Rectangle {
                implicitWidth: 16
                color: "transparent"
                Rectangle {
                    anchors.centerIn: parent
                    width: SplitHandle.hovered || SplitHandle.pressed ? 5 : 3
                    height: 40; radius: width / 2
                    color: SplitHandle.pressed ? Theme.accent : SplitHandle.hovered ? Theme.muted : Theme.hairlineStrong
                    Behavior on color { ColorAnimation { duration: Theme.motion(Theme.durationFast); easing.type: Theme.easingCurve } }
                    Behavior on width { NumberAnimation { duration: Theme.motion(Theme.durationFast); easing.type: Theme.easingCurve } }
                }
            }
            // The surface sits behind the content rather than around it: a shadow is a
            // MultiEffect, and layering a pane that holds a live editor would push every
            // keystroke through an offscreen texture. See Surface.qml.
            Item {
                SplitView.fillWidth: true
                SplitView.minimumWidth: Theme.paneMinWidth
                Surface {
                    anchors.fill: parent
                    border.color: sourceEditor.activeFocus ? Theme.focusRing : Theme.hairline
                    level: sourceEditor.activeFocus ? 1 : 0
                }
                ColumnLayout {
                    anchors.fill: parent; anchors.margins: 16; spacing: 10
                    RowLayout {
                        Layout.fillWidth: true; spacing: 8
                        Label {
                            text: root.sourceLabel(); color: Theme.ink
                            font.family: Theme.displayFamily; font.pixelSize: Theme.sizeControl; font.weight: Theme.weightMedium
                            elide: Text.ElideRight
                        }
                        LanguageCode {
                            code: root.sourceCode()
                            detected: translationModel.detectedSourceLanguage.length > 0
                            ToolTip.text: "Detected automatically"
                            ToolTip.visible: detected && codeHover.hovered
                            HoverHandler { id: codeHover }
                        }
                        Item { Layout.fillWidth: true }
                        ActionButton { symbol: "close"; ToolTip.text: "Clear text and translation"; enabled: translationModel.sourceText.length > 0 || translationModel.translatedText.length > 0; onClicked: translationModel.clearAll() }
                    }
                    ScrollView {
                        Layout.fillWidth: true; Layout.fillHeight: true; clip: true
                        TextArea {
                            id: sourceEditor; objectName: "sourceEditor"
                            text: translationModel.sourceText
                            onTextChanged: if (activeFocus) translationModel.sourceText = text
                            placeholderText: "Type or paste text here…"
                            placeholderTextColor: Theme.placeholder
                            wrapMode: TextEdit.Wrap; selectByMouse: true; verticalAlignment: TextEdit.AlignTop
                            font.pixelSize: Theme.sizeReading; color: Theme.ink
                            background: Item {}
                            Accessible.name: "Source text"
                        }
                    }
                    RowLayout {
                        Layout.fillWidth: true; spacing: 2
                        ActionButton { text: "Paste"; symbol: "paste"; onClicked: translationModel.pasteSource() }
                        ActionButton { symbol: "scan"; ToolTip.text: "Read text from clipboard image"; onClicked: ocrService.recognizeClipboardImage() }
                        ActionButton { symbol: "speaker"; ToolTip.text: ttsService.speaking ? "Stop speaking" : "Read source aloud"; enabled: translationModel.sourceText.length > 0; onClicked: ttsService.speaking ? ttsService.stop() : ttsService.speak(translationModel.sourceText, translationModel.detectedSourceLanguage || translationModel.sourceLanguage) }
                        ActionButton { symbol: "copy"; ToolTip.text: "Copy source"; enabled: translationModel.sourceText.length > 0; onClicked: { translationModel.copySource(); flash(); root.copied() } }
                        Item { Layout.fillWidth: true }
                        Caption { text: translationModel.sourceText.length + " chars"; font.family: Theme.monoFamily }
                    }
                }
            }
            // Only the source pane fills: when two items both do, SplitView hands the
            // leftover to the first and the second falls back to its minimum, which is
            // why the translation pane opened squashed to 240px. A preferred width keeps
            // the window symmetrical at any size, and the first drag overwrites this
            // binding, so the user's own split still sticks.
            Item {
                SplitView.preferredWidth: (panes.width - 16) / 2
                SplitView.minimumWidth: Theme.paneMinWidth
                Surface { anchors.fill: parent; color: Theme.raisedTranslated }
                ColumnLayout {
                    anchors.fill: parent; anchors.margins: 16; spacing: 10
                    RowLayout {
                        Layout.fillWidth: true; Layout.minimumHeight: Theme.controlHeight; spacing: 8
                        Label {
                            text: root.languageName(translationModel.targetLanguage); color: Theme.ink
                            font.family: Theme.displayFamily; font.pixelSize: Theme.sizeControl; font.weight: Theme.weightMedium
                            elide: Text.ElideRight
                        }
                        LanguageCode { code: translationModel.targetLanguage.toUpperCase() }
                        Item { Layout.fillWidth: true }
                    }
                    Item {
                        Layout.fillWidth: true; Layout.fillHeight: true

                        // While a request is in flight the pane shows where the answer is
                        // going to be written, rather than a spinner in the corner saying
                        // that something is happening somewhere.
                        SkeletonLines {
                            id: translationSkeleton
                            width: parent.width
                            y: 6
                            visible: translationModel.busy
                        }

                        ScrollView {
                            anchors.fill: parent; clip: true
                            visible: !translationSkeleton.visible
                            TextArea {
                                id: translatedText
                                text: translationModel.translatedText
                                readOnly: true; selectByMouse: true; wrapMode: TextEdit.Wrap; verticalAlignment: TextEdit.AlignTop
                                placeholderText: "Your translation will appear here."
                                placeholderTextColor: Theme.placeholder
                                font.pixelSize: Theme.sizeReading; color: Theme.ink; background: Item {}
                                Accessible.name: "Translation"
                                transform: Translate { id: translatedShift }
                            }
                        }
                    }
                    // Only the text moves. The heading, the chip and the buttons did not
                    // change, and animating them would turn a six-pixel move into a
                    // flicker. Bound to the text changing rather than to busy going
                    // false, so a result restored from history arrives the same way.
                    Connections {
                        target: translationModel
                        function onTranslatedTextChanged() {
                            if (translationModel.translatedText.length > 0 && !Theme.reduceMotion) reveal.restart()
                        }
                    }
                    ParallelAnimation {
                        id: reveal
                        NumberAnimation { target: translatedText; property: "opacity"; from: 0; to: 1; duration: Theme.durationBase; easing.type: Theme.easingCurve }
                        NumberAnimation { target: translatedShift; property: "y"; from: 6; to: 0; duration: Theme.durationBase; easing.type: Theme.easingCurve }
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        ActionButton { symbol: "speaker"; ToolTip.text: ttsService.speaking ? "Stop speaking" : "Read translation aloud"; enabled: translationModel.translatedText.length > 0; onClicked: ttsService.speaking ? ttsService.stop() : ttsService.speak(translationModel.translatedText, translationModel.targetLanguage) }
                        Item { Layout.fillWidth: true }
                        ActionButton { text: "Copy translation"; symbol: "copy"; enabled: translationModel.translatedText.length > 0; onClicked: { translationModel.copyTranslated(); flash(); root.copied() } }
                    }
                }
            }
        }
        // Fades and travels four pixels: the drop is what makes it read as arriving
        // rather than as having been there all along.
        Rectangle {
            id: errorBanner
            Layout.fillWidth: true; implicitHeight: errorRow.implicitHeight + 20
            opacity: translationModel.error.length > 0 ? 1 : 0
            visible: opacity > 0
            Behavior on opacity { NumberAnimation { duration: Theme.motion(Theme.durationBase); easing.type: Theme.easingCurve } }
            transform: Translate {
                y: translationModel.error.length > 0 ? 0 : -4
                Behavior on y { NumberAnimation { duration: Theme.motion(Theme.durationBase); easing.type: Theme.easingCurve } }
            }
            color: Theme.dangerSoft; radius: Theme.radiusSmall
            RowLayout {
                id: errorRow; anchors.fill: parent; anchors.margins: 10
                Label { Layout.fillWidth: true; text: translationModel.error; wrapMode: Text.Wrap; color: Theme.danger; maximumLineCount: 3; elide: Text.ElideRight; ToolTip.text: text; ToolTip.visible: errorHover.hovered; HoverHandler { id: errorHover } }
                ActionButton { text: "Retry"; enabled: !translationModel.busy; onClicked: translationModel.translate() }
                ActionButton { text: "Settings"; onClicked: settingsDialog.open() }
                ActionButton { symbol: "close"; ToolTip.text: "Dismiss error"; onClicked: translationModel.reportError("") }
            }
        }
        RowLayout {
            Layout.fillWidth: true
            // A notice replaces the status for a moment and then hands it back. Both
            // arrivals slide up six pixels, which is what separates "this just happened"
            // from text that was always sitting there.
            Label {
                id: statusLabel
                Layout.fillWidth: true
                text: root.notice || translationModel.status
                color: root.notice ? Theme.accent : Theme.muted
                elide: Text.ElideRight
                transform: Translate { id: statusShift }
                onTextChanged: if (text.length > 0 && !Theme.reduceMotion) statusIn.restart()
                ParallelAnimation {
                    id: statusIn
                    NumberAnimation { target: statusLabel; property: "opacity"; from: 0; to: 1; duration: Theme.durationBase; easing.type: Theme.easingCurve }
                    NumberAnimation { target: statusShift; property: "y"; from: 6; to: 0; duration: Theme.durationBase; easing.type: Theme.easingCurve }
                }
            }
            Switch {
                text: "Auto-translate"; checked: settingsModel.autoTranslate
                onToggled: { settingsModel.autoTranslate = checked; settingsModel.save(); if (checked) root.schedule(); else autoTimer.stop() }
            }
            Caption { text: "Ctrl + Enter"; font.family: Theme.monoFamily }
            ActionButton { text: "Translate"; symbol: "arrow"; primary: true; enabled: !translationModel.busy && translationModel.sourceText.trim().length > 0; onClicked: { autoTimer.stop(); translationModel.translate() } }
        }
    }
    Drawer {
        id: historyDrawer; objectName: "historyDrawer"; edge: Qt.RightEdge; width: Math.min(root.width - 48, 420); height: root.height
        // It floats over the app rather than sitting in it, so it takes the popup
        // elevation instead of a pane's.
        background: Surface { radius: 0; level: 2 }

        // True from just before the drawer shows until its rows have finished arriving.
        // The delegates read it to tell an opening from a re-filter.
        property bool entering: false
        onAboutToShow: { entering = true; enteringTimer.restart() }
        Timer { id: enteringTimer; interval: 600; onTriggered: historyDrawer.entering = false }
        ColumnLayout {
            anchors.fill: parent; anchors.margins: 20; spacing: 16
            RowLayout {
                Label { text: "History"; font.family: Theme.displayFamily; font.pixelSize: Theme.sizeTitle; font.weight: Theme.weightBold }
                Item { Layout.fillWidth: true }
                ActionButton { text: "Clear all"; enabled: translationModel.history.length > 0; onClicked: clearHistoryDialog.open() }
                ActionButton { symbol: "close"; ToolTip.text: "Close history"; onClicked: historyDrawer.close() }
            }
            TextField { id: historySearch; objectName: "historySearch"; Layout.fillWidth: true; placeholderText: "Search translations…"; Accessible.name: "Search history" }
            Label { visible: historyList.count === 0; text: historySearch.text ? "No matching translations." : "Your translations will be saved here."; color: Theme.muted; Layout.fillWidth: true; wrapMode: Text.Wrap }
            ListView {
                id: historyList; objectName: "historyList"; Layout.fillWidth: true; Layout.fillHeight: true; clip: true; spacing: 8
                model: translationModel.history.filter(item => (item.source + " " + item.translation).toLowerCase().indexOf(historySearch.text.toLowerCase()) >= 0)
                delegate: ItemDelegate {
                    id: historyRow
                    required property var modelData
                    required property int index
                    width: ListView.view.width
                    implicitHeight: historyContent.implicitHeight + 24

                    // Rows arrive in sequence, forty milliseconds apart, for the first
                    // eight only: past that the delay would outlast the glance it is
                    // meant to guide. Only while the drawer is opening -- the filter
                    // rebuilds these delegates on every keystroke, and a staggered
                    // re-entry each time someone types is noise, not feedback.
                    opacity: 0
                    transform: Translate { id: rowShift; y: 8 }
                    Component.onCompleted: {
                        if (historyDrawer.entering && !Theme.reduceMotion) rowIn.start()
                        else { historyRow.opacity = 1; rowShift.y = 0 }
                    }
                    SequentialAnimation {
                        id: rowIn
                        PauseAnimation { duration: Theme.motion(Math.min(historyRow.index, 7) * Theme.durationStagger) }
                        ParallelAnimation {
                            NumberAnimation { target: historyRow; property: "opacity"; to: 1; duration: Theme.motion(Theme.durationBase); easing.type: Theme.easingCurve }
                            NumberAnimation { target: rowShift; property: "y"; to: 0; duration: Theme.motion(Theme.durationBase); easing.type: Theme.easingCurve }
                        }
                    }

                    onClicked: {
                        root.restoring = true; autoTimer.stop()
                        translationModel.restoreHistory(modelData.source, modelData.translation, modelData.source_language, modelData.target_language)
                        root.restoring = false; historyDrawer.close()
                    }
                    contentItem: ColumnLayout {
                        id: historyContent; spacing: 6
                        Caption { text: root.languageName(modelData.source_language) + " → " + root.languageName(modelData.target_language) }
                        Label { Layout.fillWidth: true; text: modelData.source; elide: Text.ElideRight; font.weight: Theme.weightMedium }
                        Label { Layout.fillWidth: true; text: modelData.translation; wrapMode: Text.Wrap; maximumLineCount: 3; elide: Text.ElideRight; color: Theme.muted }
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
        background: Surface { color: Theme.raisedAlt; level: 2 }
        footer: DialogButtonBox {
            padding: 16; spacing: 8
            background: Item {}
            ActionButton { text: "Cancel"; DialogButtonBox.buttonRole: DialogButtonBox.RejectRole }
            ActionButton { text: "Save changes"; primary: true; enabled: !hotkey.recording && !screenshotHotkey.recording; DialogButtonBox.buttonRole: DialogButtonBox.AcceptRole }
        }
        // The draft is seeded before the enter transition rather than after it: the
        // FluentWinUI3 style animates the dialog in, and "opened" only fires once that
        // animation finishes, which would show a frame of stale fields first.
        onAboutToShow: {
            showKey.checked = false; apiKey.text = settingsModel.apiKey; startup.checked = settingsModel.startWithSystem
            hotkey.sequence = settingsModel.quickTranslateHotkey; hotkey.error = ""
            showOpenaiKey.checked = false; openaiKey.text = settingsModel.openaiApiKey
            ocrLanguage.currentIndex = translationModel.languages.findIndex(item => item.code === settingsModel.ocrLanguage)
            resizeResolution.value = settingsModel.ocrResizeResolution
            screenshotHotkey.sequence = settingsModel.screenshotHotkey; screenshotHotkey.error = ""
        }
        onAboutToHide: { hotkey.recording = false; screenshotHotkey.recording = false }
        onAccepted: {
            settingsModel.apiKey = apiKey.text.trim()
            settingsModel.startWithSystem = startup.checked
            settingsModel.quickTranslateHotkey = hotkey.sequence
            settingsModel.openaiApiKey = openaiKey.text.trim()
            settingsModel.ocrLanguage = ocrLanguage.currentValue
            settingsModel.ocrResizeResolution = resizeResolution.value
            settingsModel.screenshotHotkey = screenshotHotkey.sequence
            settingsModel.save(); translationModel.savePreferences()
        }
        ScrollView {
            anchors.fill: parent; clip: true; contentWidth: availableWidth
            ColumnLayout {
                width: parent.width; spacing: 12
                Label { text: "Translation service"; font.pixelSize: Theme.sizeControl; font.weight: Theme.weightBold }
                Label { Layout.fillWidth: true; text: "Connect a Google Cloud Translation API key to translate text."; wrapMode: Text.Wrap; color: Theme.muted }
                Label { text: "API key" }
                SettingsField { id: apiKey; objectName: "apiKey"; Layout.fillWidth: true; placeholderText: "Enter your API key"; echoMode: showKey.checked ? TextInput.Normal : TextInput.Password; Accessible.name: "Google Cloud API key" }
                CheckBox { id: showKey; text: "Show key"; checked: false }
                Label { text: "Desktop"; font.pixelSize: Theme.sizeControl; font.weight: Theme.weightBold; Layout.topMargin: 8 }
                CheckBox { id: startup; objectName: "startup"; text: "Start with system" }
                Label { text: "OCR"; font.pixelSize: Theme.sizeControl; font.weight: Theme.weightBold; Layout.topMargin: 8 }
                Label { Layout.fillWidth: true; wrapMode: Text.Wrap; color: Theme.muted
                    text: "OCR reads text from a screenshot by sending the image to OpenAI's Vision API. Enter an API key below to enable it." }
                Label { text: "OpenAI API key" }
                SettingsField { id: openaiKey; objectName: "openaiKey"; Layout.fillWidth: true; placeholderText: "Enter your OpenAI API key"; echoMode: showOpenaiKey.checked ? TextInput.Normal : TextInput.Password; Accessible.name: "OpenAI API key" }
                CheckBox { id: showOpenaiKey; text: "Show key"; checked: false }
                Label { text: "OCR language" }
                LanguagePicker { id: ocrLanguage; objectName: "ocrLanguage"; model: translationModel.languages; Accessible.name: "OCR language" }
                Label { text: "Resize resolution (longest side, px)" }
                SpinBox {
                    id: resizeResolution; objectName: "resizeResolution"; Layout.fillWidth: true
                    from: 256; to: 4096; stepSize: 64; editable: true
                    Accessible.name: "OCR image resize resolution in pixels"
                }
                Label { Layout.fillWidth: true; wrapMode: Text.Wrap; color: Theme.muted; font.pixelSize: Theme.sizeCaption
                    text: "Images larger than this are downscaled before upload to reduce cost and latency; too low can blur small text." }
                Label { text: "Screenshot shortcut" }
                ActionButton {
                    id: screenshotHotkey; objectName: "screenshotHotkey"; Layout.fillWidth: true
                    property string sequence: ""
                    property bool recording: false
                    property string error: ""
                    text: recording ? "Press a shortcut… (Esc to cancel)" : sequence + "  ·  Click to change"
                    Accessible.name: "Screenshot shortcut. " + text
                    onClicked: { error = ""; recording = true; forceActiveFocus() }
                    onRecordingChanged: settingsModel.recordingHotkey = recording || hotkey.recording
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
                        if (settingsModel.hotkeyConflicts(captured, "screenshot")) {
                            error = "This shortcut is already in use. Choose another."
                            return
                        }
                        sequence = captured
                        error = ""
                        recording = false
                    }
                    Keys.onReleased: function(event) { event.accepted = true }
                }
                Label { Layout.fillWidth: true; visible: screenshotHotkey.error.length > 0; text: screenshotHotkey.error; wrapMode: Text.Wrap; color: Theme.danger }
                Label { Layout.fillWidth: true; wrapMode: Text.Wrap; color: Theme.muted; font.pixelSize: Theme.sizeCaption
                    text: "Drag-select a screen area, read its text with OCR, and translate it in the quick-translate popup. Changes apply after restarting PyCrow." }
                Label { text: "Quick-translate shortcut" }
                ActionButton {
                    id: hotkey; objectName: "hotkey"; Layout.fillWidth: true
                    property string sequence: ""
                    property bool recording: false
                    property string error: ""
                    text: recording ? "Press a shortcut… (Esc to cancel)" : sequence + "  ·  Click to change"
                    Accessible.name: "Quick translate shortcut. " + text
                    onClicked: { error = ""; recording = true; forceActiveFocus() }
                    onRecordingChanged: settingsModel.recordingHotkey = recording || screenshotHotkey.recording
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
                        if (settingsModel.hotkeyConflicts(captured, "quick-translate")) {
                            error = "This shortcut is already in use. Choose another."
                            return
                        }
                        sequence = captured
                        error = ""
                        recording = false
                    }
                    Keys.onReleased: function(event) { event.accepted = true }
                }
                Label { Layout.fillWidth: true; visible: hotkey.error.length > 0; text: hotkey.error; wrapMode: Text.Wrap; color: Theme.danger }
                Label { Layout.fillWidth: true; wrapMode: Text.Wrap; color: Theme.muted; text: "Select text in another app and press this shortcut. Shortcut changes apply after restarting PyCrow." }
                Label { Layout.fillWidth: true; wrapMode: Text.Wrap; color: Theme.muted; font.pixelSize: Theme.sizeCaption; text: "Your API key is stored locally in your user settings file." }
            }
        }
    }
}
