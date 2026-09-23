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
    //
    // The gutter earns a second job with glass: the bevel refracts pixels from
    // OUTSIDE the card, so the backdrop texture has to extend past it. The grab
    // covers the whole window, gutter included, which is exactly the margin the
    // bevel wants -- no extra padding needed.
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

    // A line of coloured text with an opaque surface under it. The Label takes an
    // explicit width rather than anchoring to both edges: wrapping decides the
    // height, so a height that fed back into the width would be a binding loop.
    component SemanticChip: Rectangle {
        property alias text: chipText.text
        property color fill: Theme.accentSoft
        property color ink: Theme.accentSoftInk
        property int maxLines: 1
        color: fill
        radius: Theme.radiusChip
        implicitHeight: chipText.implicitHeight + 10
        Label {
            id: chipText
            x: 8
            width: parent.width - 16
            anchors.verticalCenter: parent.verticalCenter
            color: parent.ink
            font.pixelSize: Theme.sizeBody
            wrapMode: Text.Wrap
            maximumLineCount: parent.maxLines
            elide: Text.ElideRight
        }
    }

    // "" when there is no controller (the QML tests load this file on its own) or
    // when the grab failed. GlassSurface reads that as "no glass" and falls back
    // to the opaque surface rather than rendering an empty hole.
    function captureBackdrop() {
        if (typeof backdropController === "undefined") return ""
        return backdropController.capture(popup.x, popup.y, popup.width, popup.height)
    }

    function popAt(x, y) {
        // Only move and re-grab while hidden. The grab has to happen before the
        // window shows or it captures the popup itself, and hiding an already
        // visible one to re-grab races the compositor -- it would photograph the
        // window it just hid. A popup that is still up is a pinned one, so
        // leaving it where the user put it is also what pinning should mean.
        if (!popup.visible) {
            popup.x = x - popup.shadowMargin
            popup.y = y - popup.shadowMargin
            backdropShot.source = popup.captureBackdrop()
        }
        closeArmed = false
        popup.show()
        popup.raise()
        popup.requestActivate()
        closeArmDelay.restart()
    }

    // The captured desktop, and the two textures the material samples: blurred
    // for the body, sharp for the bevel. None of them is ever drawn -- they exist
    // to be sampled, and the glass is what gets shown.
    Image {
        id: backdropShot
        anchors.fill: parent
        cache: false
        visible: false
    }
    ShaderEffectSource {
        id: sharpSource
        anchors.fill: parent
        sourceItem: backdropShot
        live: true
        visible: false
    }
    MultiEffect {
        id: blurPass
        anchors.fill: parent
        source: sharpSource
        blurEnabled: true
        blur: 1.0
        blurMax: 32
        blurMultiplier: 0.85
        visible: false
    }
    ShaderEffectSource {
        id: blurredSource
        anchors.fill: parent
        sourceItem: blurPass
        live: true
        visible: false
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
        GlassSurface {
            id: glass
            anchors.fill: parent
            frame: popup.contentItem
            backdrop: blurredSource
            sharpTex: sharpSource
            backdropReady: backdropShot.source != "" && backdropShot.status === Image.Ready
            level: 2
        }

        ColumnLayout {
            anchors.fill: parent
            // The bevel is lit, and text on a lit edge is text on a surface
            // nothing guaranteed. GlassSurface reports how far in that reaches.
            anchors.margins: glass.contentInset
            spacing: 8

            RowLayout {
                Layout.fillWidth: true
                Label {
                    text: popup.languageName(quickTranslateModel.detectedSourceLanguage || quickTranslateModel.sourceLanguage) + " → " + popup.languageName(quickTranslateModel.targetLanguage)
                    // Ink, not muted. On glass, muted needs a surface at roughly
                    // 0.037 luminance to clear AA -- black, with no backdrop left
                    // to see. Hierarchy here comes from size, not lightness.
                    color: glass.supported ? Theme.ink : Theme.muted
                    font.pixelSize: Theme.sizeCaption
                    Layout.fillWidth: true
                    elide: Text.ElideRight
                }
                ActionButton { onGlass: glass.supported; symbol: "pin"; primary: popup.pinned; ToolTip.text: popup.pinned ? "Unpin popup" : "Keep popup open"; onClicked: popup.pinned = !popup.pinned }
                ActionButton { onGlass: glass.supported; symbol: "copy"; enabled: quickTranslateModel.translatedText.length > 0; ToolTip.text: "Copy translation"; onClicked: { quickTranslateModel.copyTranslated(); flash(); popup.notice = "Copied to clipboard"; copyTimer.restart() } }
                ActionButton { onGlass: glass.supported; symbol: "close"; ToolTip.text: "Close popup"; onClicked: popup.close() }
            }

            // Only the notice: while a request is in flight the skeleton below says so,
            // and two indicators for one wait is one too many.
            //
            // Both of these keep their colour and stand on an opaque chip. Accent
            // and danger say something that flattening to ink would lose, and
            // neither clears AA on glass at any surface the material survives --
            // so the fix is not to recolour the text but to give it a surface.
            // The soft pairs are already proven against each other.
            SemanticChip {
                Layout.fillWidth: true
                visible: popup.notice.length > 0
                text: popup.notice
                fill: glass.supported ? Theme.accentSoft : "transparent"
                ink: glass.supported ? Theme.accentSoftInk : Theme.accent
            }
            SemanticChip {
                Layout.fillWidth: true
                visible: quickTranslateModel.error.length > 0
                text: quickTranslateModel.error
                maxLines: 3
                fill: glass.supported ? Theme.dangerSoft : "transparent"
                ink: Theme.danger
            }
            ActionButton { onGlass: glass.supported; visible: quickTranslateModel.error.length > 0; text: "Retry"; enabled: !quickTranslateModel.busy; onClicked: quickTranslateModel.translate() }
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
                        // The placeholder is the one role with no answer on glass:
                        // it needs a surface brighter than white in the light scheme.
                        // It only shows when there is no translation yet, so it gets
                        // promoted to ink rather than given a chip of its own.
                        placeholderTextColor: glass.supported ? Theme.ink : Theme.placeholder
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
                // The source echo. Ink on glass, muted on the opaque fallback --
                // see the language label above for why.
                color: glass.supported ? Theme.ink : Theme.muted
                font.pixelSize: Theme.sizeCaption
            }
        }
    }
}
