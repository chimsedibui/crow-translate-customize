import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window
import "."

Window {
    id: popup
    // The window is the card plus a transparent gutter on every side for the drop
    // shadow to blur into; a shadow cannot spill outside its own window. Every size
    // here is therefore "card size + both gutters", and popAt subtracts the gutter
    // again so the card still lands exactly where the caller asked for.
    readonly property int shadowMargin: Theme.shadowMargin
    width: 380 + shadowMargin * 2
    height: 260 + shadowMargin * 2
    minimumWidth: 260 + shadowMargin * 2
    minimumHeight: 160 + shadowMargin * 2
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
        popup.x = x - popup.shadowMargin
        popup.y = y - popup.shadowMargin
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

    // The popup is thrown onto the screen over whatever the user was doing, so it
    // settles in rather than snapping. This is one of the two places the spring is
    // allowed: a small overshoot makes the window read as arriving rather than as
    // blinking into existence. Still inside 260ms -- this is a hotkey tool and the
    // translation has to feel immediate.
    onVisibleChanged: if (visible && !Theme.reduceMotion) entrance.restart()
    ParallelAnimation {
        id: entrance
        NumberAnimation { target: card; property: "opacity"; from: 0; to: 1; duration: Theme.durationSlow; easing.type: Theme.easingCurve }
        NumberAnimation {
            target: cardLift; property: "y"; from: 8; to: 0
            duration: Theme.durationSlow
            easing.type: Theme.easingSpring
            easing.overshoot: Theme.springOvershoot
        }
    }

    Item {
        id: card
        anchors.fill: parent
        anchors.margins: popup.shadowMargin
        transform: Translate { id: cardLift }

        Keys.onEscapePressed: popup.close()
        focus: true

        // Behind the content, not around it: a MultiEffect over the whole card would put
        // the translation itself through an offscreen texture. See Surface.qml.
        Surface { anchors.fill: parent; level: 2 }

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 12
            spacing: 8

            RowLayout {
                Layout.fillWidth: true
                Label {
                    text: popup.languageName(quickTranslateModel.detectedSourceLanguage || quickTranslateModel.sourceLanguage) + " → " + popup.languageName(quickTranslateModel.targetLanguage)
                    color: Theme.muted
                    font.pixelSize: Theme.sizeCaption
                    Layout.fillWidth: true
                    elide: Text.ElideRight
                }
                ActionButton { symbol: "pin"; primary: popup.pinned; ToolTip.text: popup.pinned ? "Unpin popup" : "Keep popup open"; onClicked: popup.pinned = !popup.pinned }
                ActionButton { symbol: "copy"; enabled: quickTranslateModel.translatedText.length > 0; ToolTip.text: "Copy translation"; onClicked: { quickTranslateModel.copyTranslated(); flash(); popup.notice = "Copied to clipboard"; copyTimer.restart() } }
                ActionButton { symbol: "close"; ToolTip.text: "Close popup"; onClicked: popup.close() }
            }

            // Only the notice: while a request is in flight the skeleton below says so,
            // and two indicators for one wait is one too many.
            Label { visible: popup.notice.length > 0; text: popup.notice; color: Theme.accent }
            Label { Layout.fillWidth: true; visible: quickTranslateModel.error.length > 0; text: quickTranslateModel.error; color: Theme.danger; wrapMode: Text.Wrap; maximumLineCount: 3; elide: Text.ElideRight }
            ActionButton { visible: quickTranslateModel.error.length > 0; text: "Retry"; enabled: !quickTranslateModel.busy; onClicked: quickTranslateModel.translate() }
            Item {
                Layout.fillWidth: true
                Layout.fillHeight: true

                // Two bars, not three: the popup shows a sentence, not a paragraph.
                SkeletonLines {
                    id: popupSkeleton
                    width: parent.width
                    y: 4
                    widths: [1.0, 0.72]
                    visible: quickTranslateModel.busy
                }

                ScrollView {
                    anchors.fill: parent
                    clip: true
                    visible: !popupSkeleton.visible
                    TextArea {
                        id: popupTranslation
                        readOnly: true
                        wrapMode: TextEdit.Wrap
                        verticalAlignment: TextEdit.AlignTop
                        font.pixelSize: Theme.sizeControl
                        color: Theme.ink
                        placeholderTextColor: Theme.placeholder
                        background: Item {}
                        text: quickTranslateModel.translatedText
                        placeholderText: "Translation"
                        selectByMouse: true
                        transform: Translate { id: popupShift }
                    }
                }
            }
            Connections {
                target: quickTranslateModel
                function onTranslatedTextChanged() {
                    if (quickTranslateModel.translatedText.length > 0 && !Theme.reduceMotion) popupReveal.restart()
                }
            }
            ParallelAnimation {
                id: popupReveal
                NumberAnimation { target: popupTranslation; property: "opacity"; from: 0; to: 1; duration: Theme.durationBase; easing.type: Theme.easingCurve }
                NumberAnimation { target: popupShift; property: "y"; from: 6; to: 0; duration: Theme.durationBase; easing.type: Theme.easingCurve }
            }

            Label {
                Layout.fillWidth: true
                text: quickTranslateModel.sourceText
                wrapMode: Text.Wrap
                elide: Text.ElideRight
                maximumLineCount: 2
                color: Theme.muted
                font.pixelSize: Theme.sizeCaption
            }
        }
    }
}
