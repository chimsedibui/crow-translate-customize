import QtQuick

// One slab of liquid glass. It is a ShaderEffect the size of the panel, but it
// samples textures that cover the WHOLE window, so it has to be told where it
// sits: refraction pulls in pixels from outside the panel's own rect, which a
// panel-sized texture simply would not contain.
//
// Content goes on top as ordinary QML children -- never inside the effect, or
// the text would be refracted along with the backdrop.
ShaderEffect {
    id: glass

    // The two textures of what is behind this panel, blurred and sharp.
    property var backdrop
    property var sharpTex

    // The item those textures cover, and therefore the coordinate space the
    // shader works in.
    property Item frame: parent

    // mapToItem is a function call, not a property read, so this binding would
    // never re-run on its own. Touching x/y/size first is what makes it
    // reactive -- without that the refraction keeps sampling the spot the panel
    // used to be in as soon as you drag it.
    property vector2d panelOrigin: {
        glass.x; glass.y; glass.width; glass.height
        if (frame) { frame.width; frame.height }
        const p = glass.mapToItem(frame, 0, 0)
        return Qt.vector2d(p.x, p.y)
    }
    property vector2d panelSize: Qt.vector2d(width, height)
    property vector2d winSize: Qt.vector2d(frame ? frame.width : 1, frame ? frame.height : 1)

    property real radius: 22
    property real thickness: 26        // bevel depth, px
    property real refraction: 34       // how far the bevel drags the backdrop, px
    property real chroma: 0.55         // dispersion across the bevel
    property real specular: 0.55
    property real rimWidth: 1.0
    property real tintAmount: 0.10
    property real saturation: 1.25
    property real lightAngle: -2.2     // radians; light from the upper left
    property color tintColor: "#ffffff"
    property color rimColor: "#ffffff"

    // ---- the contrast guarantee -------------------------------------------
    // The band the surface is held inside so `textColor` stays legible on it.
    // Derived from the text alone, never from the backdrop, which is what makes
    // it hold over a desktop nobody measured. Set enforceContrast false only to
    // see what the rule is buying.
    // The WEAKEST text that will sit on this surface, not the primary one. The
    // ceiling is driven by whichever role has the least contrast to give, so
    // naming the wrong one here silently under-protects the rest.
    //
    // Measured against Theme.qml: ink demands a ceiling of 0.143, muted 0.037,
    // placeholder 0.022, and inkDisabled a NEGATIVE ceiling -- that is, no
    // surface of any luminance makes it legible. Secondary text roles do not
    // belong on glass; they belong on an opaque surface.
    property color textColor: "#e8eef3"
    property real contrastTarget: 4.5
    property bool enforceContrast: true

    // Aim above the target, because the shader's float result is quantised to 8
    // bits on the way to the screen and a ceiling set exactly at 4.5:1 lands
    // half its pixels a rounding step below it. Measured: the surface came out
    // between 4.47:1 and 4.52:1 with no headroom at all. This is the width of
    // one quantisation step near the ceiling, not a fudge factor.
    property real contrastHeadroom: 0.15
    readonly property real _target: contrastTarget + contrastHeadroom

    function _lin(c) {
        return c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4)
    }
    function _lum(c) {
        return 0.2126 * _lin(c.r) + 0.7152 * _lin(c.g) + 0.0722 * _lin(c.b)
    }
    readonly property real textLuminance: _lum(textColor)
    readonly property bool textIsLight: textLuminance >= 0.5

    // Light text wants a ceiling on the surface; dark text wants a floor. Only
    // one of the two is ever active -- a band with both ends closed would leave
    // no room for the backdrop to show through at all.
    readonly property real lumCeiling: (enforceContrast && textIsLight)
        ? (textLuminance + 0.05) / _target - 0.05 : 0.0
    readonly property real lumFloor: (enforceContrast && !textIsLight)
        ? _target * (textLuminance + 0.05) - 0.05 : 0.0
    // The bevel is lit on purpose, which makes it off limits to text. The
    // specular band falls off as (1-depth)^8, so it is gone well before the
    // bevel is: measured at 13-14px for a 22px bevel across four backdrops.
    // This covers that with room for the hairline.
    readonly property int contentInset: Math.ceil(thickness * 0.6) + 5

    property real pad0: 0
    property real pad1: 0

    fragmentShader: "glass.frag.qsb"
}
