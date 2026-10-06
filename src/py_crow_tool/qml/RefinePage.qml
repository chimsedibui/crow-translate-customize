import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "."

// The Refine tab: the writer's idea in Vietnamese (or rough English) on the left, two
// or three English messages ready to send on the right, and a few notes on what was
// changed underneath them. Laid out like the Translate tab on purpose, so switching
// tabs swaps what the panes do and not where things are.
ColumnLayout {
    id: page
    spacing: 18

    signal copied()
    function focusEditor() { draftEditor.forceActiveFocus() }
    function openHistory() { refineHistoryDrawer.open() }
    function toneName(code) {
        for (let item of refineModel.tones) if (item.code === code) return item.name
        return code
    }

    component Caption: Label { color: Theme.muted; font.pixelSize: Theme.sizeCaption; font.weight: Theme.weightMedium }

    // A segmented control rather than a combo box: there are only four tones, and seeing
    // all of them is what makes trying another one a single click.
    component ToneChip: Button {
        id: chip
        property bool selected: false
        implicitHeight: Theme.controlHeight
        padding: 12
        font.pixelSize: Theme.sizeBody
        font.weight: selected ? Theme.weightMedium : Font.Normal
        palette.buttonText: selected ? Theme.accentSoftInk : Theme.ink
        background: Rectangle {
            radius: Theme.radiusSmall
            color: chip.selected ? Theme.accentSoft : chip.down ? Theme.controlPress : chip.hovered ? Theme.controlHover : "transparent"
            border.color: chip.activeFocus ? Theme.focusRing : chip.selected ? Theme.accent : Theme.hairline
            border.width: chip.activeFocus ? 2 : 1
            Behavior on color { ColorAnimation { duration: Theme.motion(Theme.durationFast); easing.type: Theme.easingCurve } }
        }
        Accessible.role: Accessible.RadioButton
        Accessible.checked: selected
    }

    RowLayout {
        Layout.fillWidth: true; spacing: 8
        Label { text: "Tone"; color: Theme.muted; font.pixelSize: Theme.sizeBody; Layout.rightMargin: 4 }
        Repeater {
            model: refineModel.tones
            ToneChip {
                required property var modelData
                objectName: "tone_" + modelData.code
                text: modelData.name
                selected: refineModel.tone === modelData.code
                onClicked: refineModel.tone = modelData.code
            }
        }
        Item { Layout.fillWidth: true }
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
            }
        }
        Item {
            SplitView.fillWidth: true
            SplitView.minimumWidth: Theme.paneMinWidth
            Surface {
                anchors.fill: parent
                border.color: draftEditor.activeFocus ? Theme.focusRing : Theme.hairline
                level: draftEditor.activeFocus ? 1 : 0
            }
            ColumnLayout {
                anchors.fill: parent; anchors.margins: 16; spacing: 10
                RowLayout {
                    Layout.fillWidth: true; Layout.minimumHeight: Theme.controlHeight; spacing: 8
                    Label {
                        text: "Your idea"; color: Theme.ink
                        font.family: Theme.displayFamily; font.pixelSize: Theme.sizeControl; font.weight: Theme.weightMedium
                    }
                    Item { Layout.fillWidth: true }
                    ActionButton { symbol: "close"; ToolTip.text: "Clear draft and results"; enabled: refineModel.sourceText.length > 0 || refineModel.options.length > 0; onClicked: refineModel.clearAll() }
                }
                ScrollView {
                    Layout.fillWidth: true; Layout.fillHeight: true; clip: true
                    TextArea {
                        id: draftEditor; objectName: "draftEditor"
                        text: refineModel.sourceText
                        onTextChanged: if (activeFocus) refineModel.sourceText = text
                        placeholderText: "Write what you want to say — in Vietnamese, rough English, or a mix. The order of ideas does not matter."
                        placeholderTextColor: Theme.placeholder
                        wrapMode: TextEdit.Wrap; selectByMouse: true; verticalAlignment: TextEdit.AlignTop
                        font.pixelSize: Theme.sizeReading; color: Theme.ink
                        background: Item {}
                        Accessible.name: "Draft to refine"
                    }
                }
                RowLayout {
                    Layout.fillWidth: true; spacing: 2
                    ActionButton { text: "Paste"; symbol: "paste"; onClicked: refineModel.pasteSource() }
                    Item { Layout.fillWidth: true }
                    Caption { text: refineModel.sourceText.length + " chars"; font.family: Theme.monoFamily }
                }
            }
        }
        Item {
            SplitView.preferredWidth: (panes.width - 16) / 2
            SplitView.minimumWidth: Theme.paneMinWidth
            Surface { anchors.fill: parent; color: Theme.raisedTranslated }
            ColumnLayout {
                anchors.fill: parent; anchors.margins: 16; spacing: 10
                RowLayout {
                    Layout.fillWidth: true; Layout.minimumHeight: Theme.controlHeight; spacing: 8
                    Label {
                        text: "English"; color: Theme.ink
                        font.family: Theme.displayFamily; font.pixelSize: Theme.sizeControl; font.weight: Theme.weightMedium
                    }
                    Item { Layout.fillWidth: true }
                    Caption { visible: refineModel.options.length > 0; text: refineModel.options.length + " versions" }
                }
                Item {
                    Layout.fillWidth: true; Layout.fillHeight: true
                    SkeletonLines { id: skeleton; width: parent.width; y: 6; visible: refineModel.busy; widths: [1.0, 0.92, 0.64, 1.0, 0.78] }
                    Label {
                        visible: !refineModel.busy && refineModel.options.length === 0
                        width: parent.width; wrapMode: Text.Wrap
                        text: "Refined versions will appear here, each with its own Copy button."
                        color: Theme.placeholder; font.pixelSize: Theme.sizeReading
                    }
                    ScrollView {
                        id: resultScroll
                        anchors.fill: parent; clip: true
                        visible: !refineModel.busy && refineModel.options.length > 0
                        contentWidth: availableWidth
                        ColumnLayout {
                            id: results
                            width: resultScroll.availableWidth; spacing: 12
                            Repeater {
                                objectName: "refineOptions"
                                model: refineModel.options
                                // Each version is its own card, because the thing the user
                                // does next is pick one and copy it -- the card is the unit
                                // of that choice, and the Copy button sits on it.
                                Rectangle {
                                    id: card
                                    required property var modelData
                                    required property int index
                                    Layout.fillWidth: true
                                    implicitHeight: cardContent.implicitHeight + 24
                                    radius: Theme.radiusSmall
                                    color: Theme.raised
                                    border.color: cardHover.hovered ? Theme.hairlineStrong : Theme.hairline
                                    HoverHandler { id: cardHover }
                                    ColumnLayout {
                                        id: cardContent
                                        anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top
                                        anchors.margins: 12; spacing: 6
                                        RowLayout {
                                            Layout.fillWidth: true
                                            Caption { text: card.modelData.label; color: Theme.accentSoftInk }
                                            Item { Layout.fillWidth: true }
                                            ActionButton {
                                                text: "Copy"; symbol: "copy"
                                                Accessible.name: "Copy " + card.modelData.label
                                                onClicked: { refineModel.copyOption(card.index); flash(); page.copied() }
                                            }
                                        }
                                        TextEdit {
                                            Layout.fillWidth: true
                                            text: card.modelData.text
                                            readOnly: true; selectByMouse: true; wrapMode: TextEdit.Wrap
                                            font.pixelSize: Theme.sizeBody + 2; color: Theme.ink
                                            selectionColor: Theme.accent; selectedTextColor: Theme.accentInk
                                            Accessible.name: card.modelData.label
                                        }
                                    }
                                }
                            }
                            ColumnLayout {
                                Layout.fillWidth: true; Layout.topMargin: 4; spacing: 4
                                visible: refineModel.notes.length > 0
                                Caption { text: "What changed" }
                                Repeater {
                                    model: refineModel.notes
                                    Label {
                                        required property var modelData
                                        Layout.fillWidth: true; wrapMode: Text.Wrap
                                        text: "•  " + modelData
                                        color: Theme.muted; font.pixelSize: Theme.sizeBody
                                    }
                                }
                            }
                        }
                    }
                    Connections {
                        target: refineModel
                        function onResultChanged() {
                            if (refineModel.options.length > 0 && !Theme.reduceMotion) reveal.restart()
                        }
                    }
                    NumberAnimation { id: reveal; target: results; property: "opacity"; from: 0; to: 1; duration: Theme.durationBase; easing.type: Theme.easingCurve }
                }
            }
        }
    }

    Rectangle {
        Layout.fillWidth: true; implicitHeight: refineErrorRow.implicitHeight + 20
        visible: refineModel.error.length > 0
        color: Theme.dangerSoft; radius: Theme.radiusSmall
        RowLayout {
            id: refineErrorRow; anchors.fill: parent; anchors.margins: 10
            Label { Layout.fillWidth: true; text: refineModel.error; wrapMode: Text.Wrap; color: Theme.danger; maximumLineCount: 3; elide: Text.ElideRight }
            ActionButton { text: "Retry"; enabled: !refineModel.busy; onClicked: refineModel.refine() }
            ActionButton { symbol: "close"; ToolTip.text: "Dismiss error"; onClicked: refineModel.reportError("") }
        }
    }

    RowLayout {
        Layout.fillWidth: true
        Label {
            Layout.fillWidth: true
            text: page.notice || refineModel.status
            color: page.notice ? Theme.accent : Theme.muted
            elide: Text.ElideRight
        }
        Caption { text: "Ctrl + Enter"; font.family: Theme.monoFamily }
        ActionButton {
            objectName: "refineButton"
            text: "Refine"; symbol: "arrow"; primary: true
            enabled: !refineModel.busy && refineModel.sourceText.trim().length > 0
            onClicked: refineModel.refine()
        }
    }

    // The translation history's twin, kept separate because an entry here is a draft
    // and the versions it produced rather than one text and its translation.
    Drawer {
        id: refineHistoryDrawer; objectName: "refineHistoryDrawer"
        edge: Qt.RightEdge
        width: Math.min(ApplicationWindow.window ? ApplicationWindow.window.width - 48 : 420, 420)
        height: ApplicationWindow.window ? ApplicationWindow.window.height : 600
        background: Surface { radius: 0; level: 2 }
        ColumnLayout {
            anchors.fill: parent; anchors.margins: 20; spacing: 16
            RowLayout {
                Label { text: "Refine history"; font.family: Theme.displayFamily; font.pixelSize: Theme.sizeTitle; font.weight: Theme.weightBold }
                Item { Layout.fillWidth: true }
                ActionButton { text: "Clear all"; enabled: refineModel.history.length > 0; onClicked: clearRefineHistoryDialog.open() }
                ActionButton { symbol: "close"; ToolTip.text: "Close history"; onClicked: refineHistoryDrawer.close() }
            }
            TextField { id: refineHistorySearch; objectName: "refineHistorySearch"; Layout.fillWidth: true; placeholderText: "Search drafts and versions…"; Accessible.name: "Search refine history" }
            Label {
                visible: refineHistoryList.count === 0; Layout.fillWidth: true; wrapMode: Text.Wrap; color: Theme.muted
                text: refineHistorySearch.text ? "No matching drafts." : "Your refined drafts will be saved here."
            }
            ListView {
                id: refineHistoryList; objectName: "refineHistoryList"
                Layout.fillWidth: true; Layout.fillHeight: true; clip: true; spacing: 8
                // Searches the versions as well as the draft: what is remembered later is
                // usually a phrase from the English that was sent, not the Vietnamese.
                model: refineModel.history.filter(item => {
                    const haystack = (item.source + " " + item.options.map(option => option.text).join(" ")).toLowerCase()
                    return haystack.indexOf(refineHistorySearch.text.toLowerCase()) >= 0
                })
                delegate: ItemDelegate {
                    required property var modelData
                    width: ListView.view.width
                    implicitHeight: refineRowContent.implicitHeight + 24
                    onClicked: { refineModel.restoreHistory(modelData.id); refineHistoryDrawer.close() }
                    contentItem: ColumnLayout {
                        id: refineRowContent; spacing: 6
                        Caption { text: page.toneName(modelData.tone) + " · " + modelData.options.length + " versions" }
                        Label { Layout.fillWidth: true; text: modelData.source; elide: Text.ElideRight; font.weight: Theme.weightMedium }
                        Label { Layout.fillWidth: true; text: modelData.options.length ? modelData.options[0].text : ""; wrapMode: Text.Wrap; maximumLineCount: 3; elide: Text.ElideRight; color: Theme.muted }
                        Caption { text: "Click to restore · " + modelData.created_at.slice(0, 10) }
                    }
                }
            }
        }
    }
    Dialog {
        id: clearRefineHistoryDialog; title: "Clear refine history?"; modal: true
        anchors.centerIn: Overlay.overlay
        standardButtons: Dialog.Ok | Dialog.Cancel
        Label { text: "This removes all saved refined drafts." }
        onAccepted: refineModel.clearHistory()
    }

    property string notice: ""
    onCopied: { notice = "Copied to clipboard"; noticeTimer.restart() }
    Timer { id: noticeTimer; interval: 2200; onTriggered: page.notice = "" }
}
