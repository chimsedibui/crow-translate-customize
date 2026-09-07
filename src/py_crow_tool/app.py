from __future__ import annotations

import sys
import os
from importlib.resources import files

from PySide6.QtCore import QMimeData, QObject, QTimer, QUrl, Qt, Slot
from PySide6.QtGui import QAction, QCursor, QGuiApplication, QIcon
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from py_crow_tool.bootstrap import build_services
from py_crow_tool.services import AsyncLoopRunner, DesktopServices, HistoryStore, OcrService, SingleInstance, TtsService
from py_crow_tool.services.capture import CaptureController, ScreenshotImageProvider
from py_crow_tool.viewmodels import SettingsViewModel, TranslationViewModel


class _ShortcutDispatcher(QObject):
    """Give keyboard callbacks an explicit receiver on the Qt GUI thread."""

    def __init__(self, callback, parent):
        super().__init__(parent)
        self._callback = callback

    @Slot(str)
    def dispatch(self, action: str) -> None:
        self._callback(action)


def main() -> int:
    QQuickStyle.setStyle("Basic")
    app = QApplication(sys.argv)
    app.setApplicationName("PyCrow Tool")
    app.setOrganizationName("CrowTranslate")
    app_icon = QIcon(str(files("py_crow_tool") / "qml" / "app-icon.png"))
    app.setWindowIcon(app_icon)
    app.setQuitOnLastWindowClosed(False)

    instance = SingleInstance(os.getenv("PY_CROW_INSTANCE_NAME", "io.crow_translate.PyCrowTool"))
    if not instance.is_primary:
        return 0

    store, settings, manager = build_services()
    history = HistoryStore(limit=settings.history_limit)
    loop_runner = AsyncLoopRunner()
    translation_vm = TranslationViewModel(manager, settings, store, history, loop_runner)
    settings_vm = SettingsViewModel(settings, store, loop_runner)
    tts = TtsService()
    ocr = OcrService(settings, loop_runner)
    desktop = DesktopServices()

    engine = QQmlApplicationEngine()
    context = engine.rootContext()
    context.setContextProperty("translationModel", translation_vm)
    context.setContextProperty("settingsModel", settings_vm)
    context.setContextProperty("ttsService", tts)
    context.setContextProperty("ocrService", ocr)
    qml_main = files("py_crow_tool") / "qml" / "Main.qml"
    engine.load(QUrl.fromLocalFile(str(qml_main)))
    if not engine.rootObjects():
        sys.stderr.write(f"Failed to load QML from {qml_main}\n")
        return 1
    window = engine.rootObjects()[0]

    ocr.recognized.connect(lambda text: setattr(translation_vm, "sourceText", text))
    instance.activated.connect(lambda: (window.show(), window.raise_(), window.requestActivate()))

    quick_vm = TranslationViewModel(manager, settings, store, history, loop_runner)
    quick_engine = QQmlApplicationEngine()
    quick_engine.rootContext().setContextProperty("quickTranslateModel", quick_vm)
    quick_qml = files("py_crow_tool") / "qml" / "QuickTranslatePopup.qml"
    quick_engine.load(QUrl.fromLocalFile(str(quick_qml)))
    quick_popup = quick_engine.rootObjects()[0] if quick_engine.rootObjects() else None

    screenshot_image_provider = ScreenshotImageProvider()
    capture_controller = CaptureController(screenshot_image_provider)
    capture_engine = QQmlApplicationEngine()
    capture_engine.addImageProvider("capture", screenshot_image_provider)
    capture_engine.rootContext().setContextProperty("captureController", capture_controller)
    capture_qml = files("py_crow_tool") / "qml" / "CaptureOverlay.qml"
    capture_engine.load(QUrl.fromLocalFile(str(capture_qml)))
    capture_overlay = capture_engine.rootObjects()[0] if capture_engine.rootObjects() else None

    def _on_region_captured(data: bytes) -> None:
        desktop.selection_capture_pending = False
        quick_vm.sourceText = ""
        quick_popup.popAt(*_popup_position(QCursor.pos(), quick_popup))
        ocr.recognizeImageBytes(data)

    def _on_region_cancelled() -> None:
        desktop.selection_capture_pending = False

    def _on_region_recognized(text: str) -> None:
        if not text.strip():
            quick_vm.reportError("No text found in the selected area")
            return
        quick_vm.sourceText = text
        quick_vm.translate()

    if quick_popup is not None and capture_overlay is not None:
        capture_controller.regionCaptured.connect(_on_region_captured)
        capture_controller.cancelled.connect(_on_region_cancelled)
        ocr.regionRecognized.connect(_on_region_recognized)
        ocr.regionFailed.connect(lambda message: quick_vm.reportError(message))

    desktop.set_startup_enabled(settings.start_with_system)

    tray = QSystemTrayIcon(app_icon, app)
    tray.setToolTip("PyCrow Tool")
    menu = QMenu()
    show_action = QAction("Show", menu)
    show_action.triggered.connect(lambda: (window.show(), window.raise_(), window.requestActivate()))
    translate_clipboard = QAction("Translate clipboard", menu)
    translate_clipboard.triggered.connect(lambda: _translate_clipboard(app, translation_vm, window))
    quit_action = QAction("Quit", menu)
    quit_action.triggered.connect(app.quit)
    menu.addAction(show_action)
    menu.addAction(translate_clipboard)
    menu.addSeparator()
    menu.addAction(quit_action)
    tray.setContextMenu(menu)
    tray.activated.connect(lambda reason: show_action.trigger() if reason == QSystemTrayIcon.ActivationReason.Trigger else None)
    tray.show()

    clipboard_hotkey_ok = desktop.register_shortcut(settings.clipboard_hotkey, "translate-clipboard")
    quick_hotkey_ok = desktop.register_shortcut(settings.quick_translate_hotkey, "quick-translate")
    screenshot_hotkey_ok = desktop.register_shortcut(settings.screenshot_hotkey, "capture-screenshot")
    if not (clipboard_hotkey_ok and quick_hotkey_ok and screenshot_hotkey_ok):
        tray.showMessage(
            "PyCrow Tool",
            "A global hotkey could not be registered. It may already be used by another app. "
            "Check the console error and change the hotkey in Settings. "
            "On Linux, also check the keyboard package and input-device permissions.",
            QSystemTrayIcon.MessageIcon.Warning,
            6000,
        )

    active_shortcuts = ((settings.clipboard_hotkey, "translate-clipboard"),
                        (settings.quick_translate_hotkey, "quick-translate"),
                        (settings.screenshot_hotkey, "capture-screenshot"))

    def _recording_changed() -> None:
        if settings_vm.recordingHotkey:
            desktop.unregister_shortcuts()
        else:
            for sequence, action in active_shortcuts:
                desktop.register_shortcut(sequence, action)

    settings_vm.recordingHotkeyChanged.connect(_recording_changed)

    def _on_shortcut(action: str) -> None:
        if settings_vm.recordingHotkey:
            return
        if action == "translate-clipboard":
            _translate_clipboard(app, translation_vm, window)
        elif action == "quick-translate":
            _quick_translate_selection(app, desktop, quick_vm, quick_popup, tray)
        elif action == "capture-screenshot":
            _capture_screenshot(desktop, capture_controller, capture_overlay, tray)

    shortcut_dispatcher = _ShortcutDispatcher(_on_shortcut, app)
    desktop.shortcutTriggered.connect(shortcut_dispatcher.dispatch, Qt.ConnectionType.QueuedConnection)
    settings_vm.saved.connect(lambda: desktop.set_startup_enabled(settings.start_with_system))

    def _shutdown() -> None:
        tts.stop()
        try:
            loop_runner.run_sync(manager.close(), timeout=3)
        except Exception:
            pass
        try:
            loop_runner.run_sync(ocr.close(), timeout=3)
        except Exception:
            pass
        loop_runner.stop()

    app.aboutToQuit.connect(_shutdown)
    return app.exec()


def _quick_translate_selection(
    app: QApplication, desktop: DesktopServices, model: TranslationViewModel, popup, tray: QSystemTrayIcon | None = None
) -> None:
    if popup is None or desktop.selection_capture_pending:
        return
    desktop.selection_capture_pending = True
    clipboard = app.clipboard()
    previous_data = None

    def _finish(message: str | None = None) -> None:
        if previous_data is not None:
            clipboard.setMimeData(previous_data)
        desktop.selection_capture_pending = False
        if message and tray is not None:
            tray.showMessage("PyCrow Tool", message, QSystemTrayIcon.MessageIcon.Warning, 5000)

    def _poll(attempts: int = 25) -> None:
        selected = clipboard.text().strip()
        if selected:
            _finish()
            model.sourceText = selected
            popup.popAt(*_popup_position(QCursor.pos(), popup))
            model.translate()
        elif attempts <= 1:
            _finish("No text was copied. Select text in the foreground application and try again.")
        else:
            QTimer.singleShot(40, lambda: _poll(attempts - 1))

    def _copy_when_released(attempts: int = 100) -> None:
        nonlocal previous_data
        if not desktop.copy_modifiers_released():
            if attempts <= 1:
                _finish("Release the hotkey keys, then try again.")
            else:
                QTimer.singleShot(30, lambda: _copy_when_released(attempts - 1))
            return
        # Snapshot all clipboard formats before copying. Serialize captures so
        # another hotkey cannot read a previous capture's restored clipboard.
        previous_data = QMimeData()
        current = clipboard.mimeData()
        if current is not None:
            for format_name in current.formats():
                previous_data.setData(format_name, current.data(format_name))
        clipboard.clear()
        # Windows can temporarily refuse clipboard access. Never interpret the
        # old clipboard as a successfully copied selection if clearing failed.
        if clipboard.text():
            _finish("Clipboard is busy. Please try again.")
            return
        if not desktop.simulate_copy():
            _finish("Could not copy the selection. Check that the keyboard package is installed.")
            return
        QTimer.singleShot(40, _poll)

    _copy_when_released()


def _capture_screenshot(
    desktop: DesktopServices, capture: CaptureController, overlay, tray: QSystemTrayIcon | None = None
) -> None:
    if overlay is None or desktop.selection_capture_pending:
        return
    desktop.selection_capture_pending = True
    geometry = capture.capture_screen_at_cursor()
    if geometry is None:
        desktop.selection_capture_pending = False
        if tray is not None:
            tray.showMessage("PyCrow Tool", "Could not capture the screen.", QSystemTrayIcon.MessageIcon.Warning, 5000)
        return
    overlay.setProperty("x", geometry.x())
    overlay.setProperty("y", geometry.y())
    overlay.setProperty("width", geometry.width())
    overlay.setProperty("height", geometry.height())
    overlay.show()
    overlay.requestActivate()


def _popup_position(cursor, popup) -> tuple[int, int]:
    x, y = cursor.x() + 12, cursor.y() + 12
    width, height = popup.property("width"), popup.property("height")
    screen = QGuiApplication.screenAt(cursor) or QGuiApplication.primaryScreen()
    if screen is not None:
        geometry = screen.availableGeometry()
        if x + width > geometry.right():
            x = cursor.x() - width - 12
        if y + height > geometry.bottom():
            y = cursor.y() - height - 12
        x = max(geometry.left(), min(x, geometry.right() - width))
        y = max(geometry.top(), min(y, geometry.bottom() - height))
    return x, y


def _translate_clipboard(app: QGuiApplication, model: TranslationViewModel, window) -> None:
    text = app.clipboard().text().strip()
    if text:
        model.sourceText = text
        window.show()
        window.raise_()
        model.translate()


if __name__ == "__main__":
    raise SystemExit(main())
