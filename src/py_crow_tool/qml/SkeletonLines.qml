import QtQuick
import "."

// Stands in for a translation that is on its way. This is the only looping animation in
// the app, and it runs only while a request is actually in flight -- a shimmer that
// outlives its request reads as a hang, so whatever shows this is responsible for hiding
// it the moment the answer, or the error, arrives.
//
// It replaces a spinner on purpose: a BusyIndicator says something is happening
// somewhere, three bars in the translation pane say the translation is being written
// here.
Column {
    id: root

    // Relative widths, longest first. Two lines for the popup, three for a pane.
    property var widths: [1.0, 0.92, 0.64]

    spacing: 10

    Repeater {
        model: root.widths.length

        Rectangle {
            id: bar
            required property int index

            width: root.width * root.widths[bar.index]
            height: 12
            radius: height / 2
            color: Theme.skeleton

            // The sheen travels inside the bar rather than across it, so it needs no
            // clipping and its own rounded ends never square off the bar's.
            Rectangle {
                id: sheen
                width: bar.width * 0.45
                height: bar.height
                radius: bar.radius
                gradient: Gradient {
                    orientation: Gradient.Horizontal
                    GradientStop { position: 0.0; color: "transparent" }
                    GradientStop { position: 0.5; color: Theme.skeletonSheen }
                    GradientStop { position: 1.0; color: "transparent" }
                }

                XAnimator on x {
                    from: 0
                    to: bar.width - sheen.width
                    duration: 1200
                    loops: Animation.Infinite
                    running: root.visible && !Theme.reduceMotion
                }
            }
        }
    }
}
