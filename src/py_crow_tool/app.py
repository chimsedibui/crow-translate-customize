from __future__ import annotations

import sys
import os
from importlib.resources import files

from PySide6.QtCore import QTimer, QUrl
from PySide6.QtGui import QAction, QCursor, QGuiApplication, QIcon
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtWidgets import QApplication, QMenu, QStyle, QSystemTrayIcon

from py_crow_tool.bootstrap import build_services
from py_crow_tool.services import AsyncLoopRunner, DesktopServices, HistoryStore, OcrService, SingleInstance, TtsService
from py_crow_tool.viewmodels import SettingsViewModel, TranslationViewModel


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("PyCrow Tool")
    app.setOrganizationName("CrowTranslate")
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
    ocr = OcrService(settings.tesseract_command, loop_runner)
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

    desktop.set_startup_enabled(settings.start_with_system)

    tray_icon = QIcon.fromTheme("accessories-dictionary")
    if tray_icon.isNull():
        tray_icon = app.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogInfoView)
    tray = QSystemTrayIcon(tray_icon, app)
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
    if not (clipboard_hotkey_ok and quick_hotkey_ok):
        tray.showMessage(
            "PyCrow Tool",
            "Global hotkeys are unavailable. Install the optional 'keyboard' package "
            '(pip install -e ".[windows]") and, on Linux, run with permission to read input devices.',
            QSystemTrayIcon.MessageIcon.Warning,
            6000,
        )

    def _on_shortcut(action: str) -> None:
        if action == "translate-clipboard":
            _translate_clipboard(app, translation_vm, window)
        elif action == "quick-translate":
            _quick_translate_selection(app, desktop, quick_vm, quick_popup, tray)

    desktop.shortcutTriggered.connect(_on_shortcut)
    settings_vm.saved.connect(lambda: desktop.set_startup_enabled(settings.start_with_system))

    def _shutdown() -> None:
        tts.stop()
        try:
            loop_runner.run_sync(manager.close(), timeout=3)
        except Exception:
            pass
        loop_runner.stop()

    app.aboutToQuit.connect(_shutdown)
    return app.exec()


def _quick_translate_selection(
    app: QApplication, desktop: DesktopServices, model: TranslationViewModel, popup, tray: QSystemTrayIcon | None = None
) -> None:
    if popup is None:
        return
    clipboard = app.clipboard()
    previous_text = clipboard.text()
    clipboard.clear()
    if not desktop.simulate_copy():
        if previous_text:
            clipboard.setText(previous_text)
        if tray:
            tray.showMessage(
                "PyCrow Tool",
                "Could not copy the selection. Install the optional 'keyboard' package to use this hotkey.",
                QSystemTrayIcon.MessageIcon.Warning,
                5000,
            )
        return

    # Ctrl+C is delivered to whatever app owned the selection, and the target
    # app updates the clipboard on its own schedule (slower under remote
    # desktop, X11 clipboard managers, etc.), so poll for a change instead of
    # trusting a single fixed delay to be long enough.
    remaining_attempts = [20]  # ~20 * 40ms = 800ms ceiling

    def _poll() -> None:
        selected = clipboard.text().strip()
        if selected:
            if previous_text:
                clipboard.setText(previous_text)
            popup.popAt(*_popup_position(QCursor.pos(), popup))
            model.sourceText = selected
            model.translate()
            return
        remaining_attempts[0] -= 1
        if remaining_attempts[0] <= 0:
            if previous_text:
                clipboard.setText(previous_text)
            return
        QTimer.singleShot(40, _poll)

    QTimer.singleShot(40, _poll)


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
