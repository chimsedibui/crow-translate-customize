import QtQuick
import QtQuick.Effects
import "."

// A pane, dialog or popup background made of glass: the backdrop behind it,
// refracted through a bevelled edge and held at a luminance that keeps the text
// on it legible.
//
// Like Surface, this goes BEHIND a caller's content, never around it -- a
// ShaderEffect renders its target to an offscreen texture, and pushing a live
// TextArea through one costs the subpixel antialiasing that makes 13px UI text
// readable. Content is an ordinary sibling drawn on top, and must sit at least
// `contentInset` in from the edge, because the bevel is lit and text on a lit
// edge is text on an unknown surface.
//
// The opaque Surface underneath is not a decoration. Qt Quick's software
// renderer -- what a machine without working GPU acceleration falls back to,
// over Remote Desktop or in a VM -- draws nothing at all for a ShaderEffect, so
// without it the popup would be an empty hole there. It also carries the drop
// shadow, and stands in whenever the backdrop grab failed.
Item {
    id: glass

    // Textures of what is behind this surface: one blurred for the body, one
    // sharp for the bevel. Two on purpose -- a real slab bends a legible,
    // compressed image of its surroundings into the edge while the middle stays
    // diffuse, and that split is what separates glass from frosted plastic.
    property var backdrop
    property var sharpTex
    // The item those textures cover, and so the space the shader works in. The
    // bevel samples outside this surface's own rect, which is why it needs to
    // know where it sits rather than just how big it is.
    property Item frame: parent
    property bool backdropReady: false

    // 0 at rest, 1 focused or hovered, 2 floating over another window.
    property int level: 2

    // The weakest text that will be placed on this surface, not the primary one:
    // the luminance bound is set by whichever role has the least contrast to
    // give. With this palette that is only ever Theme.ink -- see the note in
    // Theme.qml about why nothing else can go here.
    property color textColor: Theme.ink
    // Dark scheme means light text over a dark surface, so the surface gets a
    // ceiling; the light scheme gets a floor. Taken from the scheme rather than
    // from the text's own luminance, because roles like `muted` sit well under
    // half and are still the lighter of the two.
    property bool lightText: Theme.dark

    readonly property bool supported: GraphicsInfo.api !== GraphicsInfo.Software && backdropReady
    // The specular band falls off as (1-depth)^8, so it is gone well before the
    // bevel is -- measured at 13-14px for a 20px bevel across five backdrops.
    readonly property int contentInset: supported ? Math.ceil(Theme.glassThickness * 0.6) + 5 : 12

    Surface {
        id: fallback
        anchors.fill: parent
        radius: Theme.radiusGlass
        level: glass.level
    }

    ShaderEffect {
        id: material
        anchors.fill: parent
        visible: glass.supported

        property var backdrop: glass.backdrop
        property var sharpTex: glass.sharpTex

        // mapToItem is a function call, not a property read, so this would never
        // re-run on its own. Touching the geometry first is what makes it
        // reactive -- without that the refraction keeps sampling wherever the
        // surface used to be.
        property vector2d panelOrigin: {
            glass.x; glass.y; glass.width; glass.height
            if (glass.frame) { glass.frame.width; glass.frame.height }
            const p = glass.mapToItem(glass.frame, 0, 0)
            return Qt.vector2d(p.x, p.y)
        }
        property vector2d panelSize: Qt.vector2d(glass.width, glass.height)
        property vector2d winSize: Qt.vector2d(glass.frame ? glass.frame.width : 1,
                                               glass.frame ? glass.frame.height : 1)

        property real radius: Theme.radiusGlass
        property real thickness: Theme.glassThickness
        property real refraction: Theme.glassRefraction
        property real chroma: Theme.glassChroma
        property real specular: Theme.glassSpecular
        property real rimWidth: 1.0
        property real tintAmount: Theme.glassTintAmount
        property real saturation: Theme.glassSaturation
        property real lightAngle: -2.2          // radians; light from the upper left
        property color tintColor: Theme.glassTint
        property color rimColor: Theme.dark ? "#ffffff" : "#ffffff"

        property real lumCeiling: glass.lightText ? Theme.glassCeiling(glass.textColor) : 0.0
        property real lumFloor: glass.lightText ? 0.0 : Theme.glassFloor(glass.textColor)
        property real pad0: 0
        property real pad1: 0

        fragmentShader: "glass.frag.qsb"
    }
}
