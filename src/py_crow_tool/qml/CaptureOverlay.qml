import QtQml
import QtQml.Models

// Root object for the capture engine: spawns one CaptureOverlayWindow per connected screen,
// so a single hotkey press lets the user drag-select on any monitor, not just the one under
// the cursor. Instantiator keeps the list in sync as captureController.screens changes.
QtObject {
    id: root

    property Instantiator instantiator: Instantiator {
        model: captureController.screens
        delegate: CaptureOverlayWindow {}
        // Window delegates finish construction before Instantiator can inject "index"/"modelData"
        // context properties, so bindings like "screenWidth: modelData.width" inside the delegate
        // itself silently fail. Assigning the values here, once the object exists, works around it.
        onObjectAdded: (index, object) => {
            const entry = captureController.screens[index]
            object.screenIndex = entry.index
            object.screenX = entry.x
            object.screenY = entry.y
            object.screenWidth = entry.width
            object.screenHeight = entry.height
        }
    }
}
