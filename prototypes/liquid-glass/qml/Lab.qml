import QtQuick
import QtQuick.Controls
import QtQuick.Effects
import QtQuick.Layouts

ApplicationWindow {
    id: root
    width: 1180; height: 760
    visible: true
    title: "Liquid glass — prototype"
    color: "#0e1319"

    property bool dark: true
    property bool glassOn: true
    property bool guarantee: true

    RowLayout {
        anchors.fill: parent
        spacing: 0

        // ---------------------------------------------------------------- stage
        Item {
            id: stage
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true

            // Everything the glass is allowed to see. The glass itself is NOT in
            // here -- if it were, its own output would feed back into the texture
            // it samples and the panel would smear into itself.
            Item {
                id: bgContent
                anchors.fill: parent

                Rectangle {
                    anchors.fill: parent
                    gradient: Gradient {
                        GradientStop { position: 0.0; color: root.dark ? "#101b2a" : "#e9f1f7" }
                        GradientStop { position: 1.0; color: root.dark ? "#1d1026" : "#fdf3ea" }
                    }
                }
                // Hard-edged colour, so the bevel has something worth bending.
                Rectangle { x: 60;  y: 70;  width: 190; height: 190; radius: 95; color: "#e0483c"; opacity: 0.85 }
                Rectangle { x: 330; y: 430; width: 230; height: 130; radius: 16; color: "#2bb3a1"; opacity: 0.9 }
                Rectangle { x: 520; y: 90;  width: 120; height: 320; radius: 60; color: "#f0b429"; opacity: 0.8 }
                Rectangle { x: 120; y: 520; width: 300; height: 28;  radius: 14; color: "#7a5cf0"; opacity: 0.9 }

                // Dense text: the honest test. If the rim cannot bend legible
                // type into a compressed band, it is frosting, not glass.
                Column {
                    x: 40; y: 300; width: parent.width - 80; spacing: 6
                    Repeater {
                        model: 7
                        Label {
                            width: 700
                            text: "Kính lỏng bẻ cong thứ nằm sau nó — mép dày dồn ảnh lại thành một dải hẹp, còn phần giữa thì tán ra."
                            wrapMode: Text.Wrap
                            font.pixelSize: 15
                            color: root.dark ? "#c8d6e2" : "#2a3b4a"
                            opacity: 0.85
                        }
                    }
                }
            }

            // The backdrop textures. Both cover the whole stage, because the
            // bevel samples pixels from outside the panel's own rectangle.
            ShaderEffectSource {
                id: sharpSrc
                anchors.fill: parent
                sourceItem: bgContent
                live: true
                hideSource: false
                visible: false
            }
            MultiEffect {
                id: blurItem
                anchors.fill: parent
                source: sharpSrc
                blurEnabled: true
                blur: 1.0
                blurMax: 32
                blurMultiplier: blurAmount.value
                visible: false
            }
            ShaderEffectSource {
                id: blurSrc
                anchors.fill: parent
                sourceItem: blurItem
                live: true
                visible: false
            }

            // ------------------------------------------------------------ glass
            GlassPanel {
                id: card
                x: 150; y: 250
                width: 440; height: 260
                frame: stage
                backdrop: blurSrc
                sharpTex: sharpSrc
                visible: root.glassOn

                radius: radiusS.value
                thickness: thicknessS.value
                refraction: refractionS.value
                chroma: chromaS.value
                specular: specularS.value
                tintAmount: tintS.value
                saturation: satS.value
                lightAngle: lightS.value
                tintColor: root.dark ? "#8fd8ff" : "#ffffff"
                rimColor: "#ffffff"
                textColor: root.dark ? "#e8eef3" : "#182b3a"
                enforceContrast: root.guarantee

                Column {
                    anchors.left: parent.left; anchors.top: parent.top
                    anchors.margins: 26
                    spacing: 10
                    Label { text: "English → Tiếng Việt"; color: "#b9cbd8"; font.pixelSize: 11 }
                    Label {
                        width: card.width - 52
                        text: "Kéo tấm kính này qua chữ phía dưới."
                        wrapMode: Text.Wrap
                        font.pixelSize: 19
                        color: "#ffffff"
                    }
                }
                MouseArea {
                    anchors.fill: parent
                    drag.target: card
                    drag.minimumX: -60; drag.minimumY: -60
                    drag.maximumX: stage.width - card.width + 60
                    drag.maximumY: stage.height - card.height + 60
                    cursorShape: Qt.SizeAllCursor
                }
            }

            // The card as it is drawn today, for comparison: opaque fill,
            // hairline, drop shadow. Same size, same place, one toggle apart.
            Rectangle {
                x: 150; y: 250; width: 440; height: 260
                visible: !root.glassOn
                radius: 12
                color: root.dark ? "#1a232b" : "#ffffff"
                border.width: 1
                border.color: root.dark ? "#2b3844" : "#dce4eb"
                Column {
                    anchors.left: parent.left; anchors.top: parent.top
                    anchors.margins: 26
                    spacing: 10
                    Label { text: "English → Tiếng Việt"; color: root.dark ? "#93a3b0" : "#5c6b7a"; font.pixelSize: 11 }
                    Label {
                        width: 388
                        text: "Đây là Surface hiện tại, để so sánh."
                        wrapMode: Text.Wrap
                        font.pixelSize: 19
                        color: root.dark ? "#e8eef3" : "#182b3a"
                    }
                }
            }

            Label {
                anchors.left: parent.left; anchors.bottom: parent.bottom; anchors.margins: 10
                font.pixelSize: 11
                font.family: "Cascadia Mono"
                color: "#7d8f9d"
                text: "renderer: " + (GraphicsInfo.api === GraphicsInfo.Software
                        ? "SOFTWARE — shader sẽ không vẽ gì"
                        : GraphicsInfo.api === GraphicsInfo.Direct3D11 ? "Direct3D 11"
                        : GraphicsInfo.api === GraphicsInfo.OpenGL ? "OpenGL"
                        : "GPU (" + GraphicsInfo.api + ")")
            }
        }

        // -------------------------------------------------------------- controls
        Rectangle {
            Layout.preferredWidth: 300
            Layout.fillHeight: true
            color: "#151c24"

            // `value` is applied in Component.onCompleted rather than as a plain
            // assignment: a Slider recomputes value from its handle position when
            // `to` changes, so setting value before the range lands leaves it
            // rescaled to something nobody asked for.
            component Knob: ColumnLayout {
                id: knob
                property real from: 0
                property real to: 1
                property real initial: 0
                property alias value: s.value
                property string label
                spacing: 0
                RowLayout {
                    Layout.fillWidth: true
                    Label { text: knob.label; color: "#a9bac7"; font.pixelSize: 12; Layout.fillWidth: true }
                    Label { text: s.value.toFixed(2); color: "#2bb3a1"; font.pixelSize: 12; font.family: "Cascadia Mono" }
                }
                Slider {
                    id: s
                    Layout.fillWidth: true
                    from: knob.from
                    to: knob.to
                    Component.onCompleted: value = knob.initial
                }
            }

            ScrollView {
                anchors.fill: parent
                contentWidth: availableWidth

                ColumnLayout {
                    width: parent.width
                    spacing: 6

                    Label {
                        text: "Liquid glass"
                        color: "#e8eef3"; font.pixelSize: 17; font.bold: true
                        Layout.leftMargin: 14; Layout.topMargin: 14
                    }

                    Knob { id: refractionS; Layout.fillWidth: true; Layout.leftMargin: 14; Layout.rightMargin: 14
                           label: "Refraction (bẻ cong ở mép)"; from: 0; to: 140; initial: 34 }
                    Knob { id: thicknessS;  Layout.fillWidth: true; Layout.leftMargin: 14; Layout.rightMargin: 14
                           label: "Thickness (độ dày bevel)"; from: 4; to: 90; initial: 20 }
                    Knob { id: chromaS;     Layout.fillWidth: true; Layout.leftMargin: 14; Layout.rightMargin: 14
                           label: "Chromatic dispersion"; from: 0; to: 2; initial: 0.22 }
                    Knob { id: specularS;   Layout.fillWidth: true; Layout.leftMargin: 14; Layout.rightMargin: 14
                           label: "Specular rim"; from: 0; to: 2; initial: 0.75 }
                    Knob { id: blurAmount;  Layout.fillWidth: true; Layout.leftMargin: 14; Layout.rightMargin: 14
                           label: "Body blur"; from: 0; to: 2; initial: 0.85 }
                    Knob { id: tintS;       Layout.fillWidth: true; Layout.leftMargin: 14; Layout.rightMargin: 14
                           label: "Tint"; from: 0; to: 0.6; initial: 0.06 }
                    Knob { id: satS;        Layout.fillWidth: true; Layout.leftMargin: 14; Layout.rightMargin: 14
                           label: "Saturation"; from: 0.4; to: 2; initial: 1.15 }
                    Knob { id: radiusS;     Layout.fillWidth: true; Layout.leftMargin: 14; Layout.rightMargin: 14
                           label: "Corner radius"; from: 0; to: 120; initial: 28 }
                    Knob { id: lightS;      Layout.fillWidth: true; Layout.leftMargin: 14; Layout.rightMargin: 14
                           label: "Light angle"; from: -3.14; to: 3.14; initial: -2.2 }

                    Item { Layout.preferredHeight: 10 }

                    Switch {
                        Layout.leftMargin: 8
                        text: "Glass"; checked: root.glassOn
                        onToggled: root.glassOn = checked
                    }
                    Switch {
                        Layout.leftMargin: 8
                        text: "Dark"; checked: root.dark
                        onToggled: root.dark = checked
                    }
                    Switch {
                        Layout.leftMargin: 8
                        text: "Contrast guarantee (4.5:1)"
                        checked: root.guarantee
                        onToggled: root.guarantee = checked
                    }
                    Label {
                        Layout.fillWidth: true
                        Layout.leftMargin: 14; Layout.rightMargin: 14
                        wrapMode: Text.Wrap; font.pixelSize: 10
                        font.family: "Cascadia Mono"; color: "#7d8f9d"
                        text: card.lumCeiling > 0
                              ? "surface luminance capped at " + card.lumCeiling.toFixed(4)
                              : card.lumFloor > 0
                                ? "surface luminance lifted to " + card.lumFloor.toFixed(4)
                                : "unclamped — text may land on anything"
                    }

                    Label {
                        Layout.fillWidth: true
                        Layout.leftMargin: 14; Layout.rightMargin: 14; Layout.topMargin: 10
                        text: "Cửa sổ nổi trên desktop — chỉ compositor mới blur được, nên đây là DWM chứ không phải shader:"
                        wrapMode: Text.Wrap; color: "#a9bac7"; font.pixelSize: 12
                    }
                    RowLayout {
                        Layout.leftMargin: 14; Layout.rightMargin: 14; Layout.fillWidth: true
                        Button { text: "Acrylic popup"; Layout.fillWidth: true
                                 onClicked: pop.popAt(root.x + 140, root.y + 180, "acrylic") }
                        Button { text: "Mica popup"; Layout.fillWidth: true
                                 onClicked: pop.popAt(root.x + 140, root.y + 180, "mica") }
                    }
                    Button {
                        Layout.leftMargin: 14; Layout.rightMargin: 14; Layout.fillWidth: true
                        highlighted: true
                        text: "Glass popup (chụp màn hình + shader)"
                        onClicked: glassPop.popAt(root.x + 200, root.y + 200)
                    }
                    Button {
                        Layout.leftMargin: 14; Layout.rightMargin: 14; Layout.fillWidth: true
                        text: "Mica lên cửa sổ này"
                        onClicked: mainHr.text = backdrop.applyTo(root, "mica", root.dark)
                    }
                    Label {
                        id: mainHr
                        Layout.fillWidth: true
                        Layout.leftMargin: 14; Layout.rightMargin: 14; Layout.bottomMargin: 14
                        wrapMode: Text.Wrap; color: "#7d8f9d"; font.pixelSize: 10; font.family: "Cascadia Mono"
                    }
                    Item { Layout.fillHeight: true }
                }
            }
        }
    }

    AcrylicPopup { id: pop; darkMode: root.dark }
    GlassPopup { id: glassPop }

    // So a capture run can bring the popup up without a human clicking.
    Component.onCompleted: {
        if (typeof autoPopup !== "undefined" && autoPopup.length > 0)
            popTimer.start()
    }
    Timer {
        id: popTimer
        interval: 900
        onTriggered: {
            if (autoPopup === "glass") glassPop.popAt(root.x + 200, root.y + 260)
            else pop.popAt(root.x + 150, root.y + 260, autoPopup)
        }
    }
}
