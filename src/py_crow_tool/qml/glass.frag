#version 440

// Liquid-glass material: a thick slab with a refracting bevel, drawn over a
// texture of whatever is behind it. Two textures on purpose -- the rim samples
// the SHARP backdrop and the body samples the BLURRED one. That split is what
// separates glass from frosted plastic: a real slab bends a legible, compressed
// image of its surroundings into the bevel while the middle stays diffuse.

layout(location = 0) in vec2 qt_TexCoord0;
layout(location = 0) out vec4 fragColor;

// std140. Order matters: vec2 aligns to 8 and vec4 to 16, so the scalars are
// grouped to fill the gaps rather than pad them.
layout(std140, binding = 0) uniform buf {
    mat4  qt_Matrix;      //   0
    float qt_Opacity;     //  64
    float radius;         //  68
    float refraction;     //  72
    float specular;       //  76
    vec2  panelOrigin;    //  80  panel top-left, in window pixels
    vec2  panelSize;      //  88
    vec2  winSize;        //  96
    float thickness;      // 104  depth of the bevel, in pixels
    float chroma;         // 108
    float tintAmount;     // 112
    float saturation;     // 116
    float lightAngle;     // 120
    float rimWidth;       // 124
    float lumCeiling;     // 160  surface may not be brighter than this
    float lumFloor;       // 164  ...nor darker than this
    float pad0;           // 168
    float pad1;           // 172
    vec4  tintColor;      // 128
    vec4  rimColor;       // 144
};

layout(binding = 1) uniform sampler2D backdrop;  // blurred
layout(binding = 2) uniform sampler2D sharpTex;  // unblurred

// sRGB transfer function. The texture holds sRGB-encoded values and Qt Quick
// does not render in linear light, so the contrast work has to convert rather
// than assume.
vec3 toLinear(vec3 c) {
    // The clamp is load-bearing, not hygiene. A saturation above 1 drives the
    // weak channel of a vivid colour NEGATIVE -- cyan #00ffd0 comes in here with
    // red at -0.19 -- and pow() of a negative base is undefined. It returns NaN,
    // mix() propagates it because NaN * 0 is still NaN, and every comparison
    // against the NaN luminance that follows evaluates false. The contrast test
    // then quietly decides the pixel is already fine and passes it through
    // untouched. That is how a guarantee ships broken: not with an error, but
    // with one vivid region that never gets clamped.
    c = clamp(c, 0.0, 1.0);
    return mix(c / 12.92, pow((c + 0.055) / 1.055, vec3(2.4)), step(vec3(0.04045), c));
}

vec3 toSrgb(vec3 c) {
    c = clamp(c, 0.0, 1.0);
    return mix(c * 12.92, 1.055 * pow(c, vec3(1.0 / 2.4)) - 0.055, step(vec3(0.0031308), c));
}

// The contrast guarantee, per pixel.
//
// Text legibility depends on luminance alone, so there is no reason to spend the
// backdrop's colour buying it. Scaling every linear channel by one factor moves
// luminance exactly where it needs to go and leaves chromaticity untouched: a
// bright red stops being bright and stays red. A scrim, which is what this
// replaces, would have made it grey.
//
// Because the bound comes from the text colour and not from the backdrop, this
// holds against ANY backdrop with nothing measured -- the same guarantee a 66%
// scrim buys, at a fraction of the cost. Pixels already inside the band are not
// touched at all.
vec3 enforceContrast(vec3 col) {
    if (lumCeiling <= 0.0 && lumFloor <= 0.0) return col;

    // Enforce on the value that will actually reach the screen. The framebuffer
    // clamps to [0,1] regardless, so measuring anything else would guarantee a
    // colour nobody ever sees.
    col = clamp(col, 0.0, 1.0);

    vec3 lin = toLinear(col);
    float lum = dot(lin, vec3(0.2126, 0.7152, 0.0722));

    if (lumCeiling > 0.0 && lum > lumCeiling) {
        return toSrgb(lin * (lumCeiling / max(lum, 1e-5)));
    }
    // Lifting cannot be a scale -- zero times anything is zero -- so dark pixels
    // blend toward white. Luminance is linear in the channels, so the blend
    // factor is closed form rather than a search.
    if (lumFloor > 0.0 && lum < lumFloor) {
        float t = (lumFloor - lum) / max(1.0 - lum, 1e-5);
        return toSrgb(lin + (vec3(1.0) - lin) * t);
    }
    return col;
}

float sdRoundedBox(vec2 p, vec2 b, float r) {
    r = min(r, min(b.x, b.y));
    vec2 q = abs(p) - b + r;
    return min(max(q.x, q.y), 0.0) + length(max(q, vec2(0.0))) - r;
}

void main() {
    vec2 uv = qt_TexCoord0;
    vec2 halfSize = panelSize * 0.5;
    vec2 p = (uv - 0.5) * panelSize;

    float d = sdRoundedBox(p, halfSize, radius);

    // Surface normal = gradient of the distance field, pointing out of the slab.
    vec2 n = vec2(
        sdRoundedBox(p + vec2(1.0, 0.0), halfSize, radius) - sdRoundedBox(p - vec2(1.0, 0.0), halfSize, radius),
        sdRoundedBox(p + vec2(0.0, 1.0), halfSize, radius) - sdRoundedBox(p - vec2(0.0, 1.0), halfSize, radius)
    );
    float nl = length(n);
    n = nl > 1e-5 ? n / nl : vec2(0.0);

    // 0 at the rim, 1 once we are `thickness` pixels inside the slab.
    float depth = clamp(-d / max(thickness, 1.0), 0.0, 1.0);

    // The bevel profile. Refraction is concentrated in the last few pixels of
    // the edge, which is where a real lens does most of its bending.
    float bend = pow(1.0 - depth, 2.5);

    vec2 winUV = (panelOrigin + uv * panelSize) / winSize;
    vec2 offs = n * bend * refraction / winSize;

    // Chromatic split, rim only. Glass disperses; the eye reads that as "thick".
    vec3 rim;
    rim.r = texture(sharpTex, winUV + offs * (1.0 + chroma)).r;
    rim.g = texture(sharpTex, winUV + offs).g;
    rim.b = texture(sharpTex, winUV + offs * (1.0 - chroma)).b;

    vec3 body = texture(backdrop, winUV + offs * 0.35).rgb;

    vec3 col = mix(rim, body, smoothstep(0.0, 0.85, depth));

    float grey = dot(col, vec3(0.2126, 0.7152, 0.0722));
    col = mix(vec3(grey), col, saturation);
    col = mix(col, tintColor.rgb, tintAmount * tintColor.a);

    // Last thing before the specular: the rim highlight is decoration drawn ON
    // the surface, not part of the surface the text sits on, so clamping after
    // it would dim the highlight for no legibility gain.
    col = enforceContrast(col);

    // Specular: a lit edge on the side facing the light, plus a thin bright
    // hairline all the way round so the shape still has an edge on any wallpaper.
    vec2 L = vec2(cos(lightAngle), sin(lightAngle));
    float ndl = max(dot(n, L), 0.0);
    float band = pow(1.0 - depth, 8.0);
    col += rimColor.rgb * pow(ndl, 2.0) * band * specular;

    float aa = max(fwidth(d), 0.75);
    float hairline = 1.0 - smoothstep(0.0, aa * 2.0, abs(d + rimWidth));
    col += rimColor.rgb * hairline * 0.30;

    // Premultiplied, which is what the scene graph expects.
    float mask = 1.0 - smoothstep(-aa, aa, d);
    fragColor = vec4(col, 1.0) * mask * qt_Opacity;
}
