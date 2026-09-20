import QtQuick
import QtQuick.Controls
import QtQuick.Effects
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
    // settles in rather than snapping. Kept under 200ms: this is a hotkey tool and
    // the translation has to feel immediate.
    onVisibleChanged: if (visible) entrance.restart()
    ParallelAnimation {
        id: entrance
        NumberAnimation { target: card; property: "opacity"; from: 0; to: 1; duration: Theme.durationBase; easing.type: Theme.easingCurve }
        NumberAnimation { target: cardLift; property: "y"; from: 8; to: 0; duration: Theme.durationBase; easing.type: Theme.easingCurve }
    }

    // MultiEffect draws its source as a texture, so the card itself cannot be the
    // source: everything inside it would stop receiving clicks. This is a stand-in
    // shape that exists only to be blurred. It carries the card's own colour and is
    // inset by a pixel so nothing can peek out from behind the card's antialiased
    // corners, and it is declared before the card so it paints underneath.
    Rectangle {
        id: shadowShape
        anchors.fill: card
        anchors.margins: 1
        radius: card.radius
        color: Theme.raised
        visible: false
    }
    MultiEffect {
        source: shadowShape
        anchors.fill: shadowShape
        shadowEnabled: true
        shadowColor: Theme.shadow
        shadowOpacity: Theme.shadowOpacity
        shadowVerticalOffset: Theme.shadowOffset
        shadowBlur: 1.0
        blurMax: Theme.shadowBlurMax
        // anchors track the card's layout box but not its transform, so the entrance
        // lift and fade have to be mirrored here for the shadow to travel with it.
        opacity: card.opacity
        transform: Translate { y: cardLift.y }
    }

    Rectangle {
        id: card
        anchors.fill: parent
        anchors.margins: popup.shadowMargin
        radius: Theme.radiusLarge
        color: Theme.raised
        border.color: Theme.hairline
        border.width: 1
        transform: Translate { id: cardLift }

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
                    color: Theme.muted
                    font.pixelSize: Theme.sizeCaption
                    Layout.fillWidth: true
                    elide: Text.ElideRight
                }
                ActionButton { symbol: "pin"; primary: popup.pinned; ToolTip.text: popup.pinned ? "Unpin popup" : "Keep popup open"; onClicked: popup.pinned = !popup.pinned }
                ActionButton { symbol: "copy"; enabled: quickTranslateModel.translatedText.length > 0; ToolTip.text: "Copy translation"; onClicked: { quickTranslateModel.copyTranslated(); popup.notice = "Copied to clipboard"; copyTimer.restart() } }
                ActionButton { symbol: "close"; ToolTip.text: "Close popup"; onClicked: popup.close() }
            }

            Label { visible: quickTranslateModel.busy || popup.notice.length > 0; text: popup.notice || "Translating…"; color: Theme.accent }
            Label { Layout.fillWidth: true; visible: quickTranslateModel.error.length > 0; text: quickTranslateModel.error; color: Theme.danger; wrapMode: Text.Wrap; maximumLineCount: 3; elide: Text.ElideRight }
            ActionButton { visible: quickTranslateModel.error.length > 0; text: "Retry"; enabled: !quickTranslateModel.busy; onClicked: quickTranslateModel.translate() }
            ScrollView {
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                TextArea {
                    readOnly: true
                    wrapMode: TextEdit.Wrap
                    verticalAlignment: TextEdit.AlignTop
                    font.pixelSize: Theme.sizeControl
                    color: Theme.ink
                    placeholderTextColor: Theme.placeholder
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
                color: Theme.muted
                font.pixelSize: Theme.sizeCaption
            }
        }
    }
}
