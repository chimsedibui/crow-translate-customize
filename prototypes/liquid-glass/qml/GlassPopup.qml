import QtQuick
import QtQuick.Controls
import QtQuick.Effects
import QtQuick.Layouts

// The quick-translate popup with REAL liquid glass over the desktop.
//
// The compositor route is a dead end: DwmSetWindowAttribute and the legacy
// accent policy both report success and both turn a see-through Qt window into
// an opaque slab (see test_backdrop.py). What does work is doing the job
// ourselves -- grab the desktop under where the popup is about to appear, hand
// that to the same shader the in-app panels use, and the full material comes
// with it: refraction, dispersion, specular rim.
//
// The trade is that the backdrop is a still. It is captured at pop time and
// does not follow anything moving underneath. For a popup that lives for a few
// seconds over a document the user is reading, that is a fair price -- and it
// buys a material the compositor would never have given us anyway.
Window {
    id: popup

    // Captured margin around the card. The bevel samples OUTSIDE the panel, so
    // a texture cropped to the card exactly would leave the rim with nothing to
    // bend and it would clamp to a smear at the edges.
    readonly property int pad: 64

    property bool guarantee: true

    // Off for measurement: with the text gone, every pixel of the card is
    // surface, and the verifier can read it without guessing which pixels are
    // glyphs and which are a surface that failed.
    property bool showContent: true

    property int cardWidth: 380
    property int cardHeight: 240

    width: cardWidth + pad * 2
    height: cardHeight + pad * 2
    flags: Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
    color: "transparent"
    visible: false

    function popAt(x, y) {
        // Grab BEFORE showing, or the capture contains the popup itself.
        popup.x = x - pad
        popup.y = y - pad
        shot.source = screenGrab.capture(popup.x, popup.y, popup.width, popup.height)
        popup.show()
        popup.raise()
        popup.requestActivate()
    }

    // The captured desktop. Never drawn -- it exists to be a texture.
    Image {
        id: shot
        anchors.fill: parent
        cache: false
        visible: false
    }
    ShaderEffectSource {
        id: sharpSrc
        anchors.fill: parent
        sourceItem: shot
        live: true
        visible: false
    }
    MultiEffect {
        id: blurItem
        anchors.fill: parent
        source: sharpSrc
        blurEnabled: true
        blur: 1.0
        blurMax: 32
        blurMultiplier: 0.85
        visible: false
    }
    ShaderEffectSource {
        id: blurSrc
        anchors.fill: parent
        sourceItem: blurItem
        live: true
        visible: false
    }

    GlassPanel {
        id: card
        x: popup.pad; y: popup.pad
        width: popup.cardWidth; height: popup.cardHeight
        frame: popup.contentItem
        backdrop: blurSrc
        sharpTex: sharpSrc

        radius: 24
        thickness: 22
        refraction: 38
        chroma: 0.25
        specular: 0.8
        tintAmount: 0.08
        saturation: 1.2
        tintColor: "#8fd8ff"
        textColor: "#e8eef3"
        enforceContrast: popup.guarantee

        ColumnLayout {
            visible: popup.showContent
            anchors.fill: parent
            anchors.margins: card.contentInset
            spacing: 8

            RowLayout {
                Layout.fillWidth: true
                Label { text: "English → Tiếng Việt"; color: "#e8eef3"; font.pixelSize: 11; Layout.fillWidth: true }
                Label { text: "glass"; color: "#e8eef3"; font.pixelSize: 11; font.bold: true }
            }
            Label {
                Layout.fillWidth: true
                text: "Kính thật: nền là ảnh chụp desktop, đưa thẳng vào shader."
                wrapMode: Text.Wrap
                font.pixelSize: 17
                color: "#ffffff"
            }
            Item { Layout.fillHeight: true; Layout.fillWidth: true }
            Label {
                Layout.fillWidth: true
                text: "Esc để đóng"
                // Not a muted grey: muted does not clear AA on any glass this
                // side of opaque. Hierarchy comes from size here, not lightness.
                color: "#e8eef3"; font.pixelSize: 11
            }
        }

        // drag.target needs a QQuickItem and a Window is not one, so moving the
        // popup goes through the window manager instead.
        MouseArea {
            anchors.fill: parent
            cursorShape: Qt.SizeAllCursor
            onPressed: popup.startSystemMove()
        }
    }

    Shortcut { sequence: "Escape"; onActivated: popup.close() }
}
