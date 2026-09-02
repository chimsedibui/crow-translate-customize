from __future__ import annotations

import sys
import os
from importlib.resources import files

from PySide6.QtCore import QTimer, QUrl
from PySide6.QtGui import QAction, QCursor, QGuiApplication, QIcon
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtWidgets import QApplication, QMenu, QStyle, QSystemTrayIcon

from py_crow_tool.bootstrap import build_services
from py_crow_tool.services import DesktopServices, HistoryStore, OcrService, SingleInstance, TtsService
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
    translation_vm = TranslationViewModel(manager, settings, store, history)
    settings_vm = SettingsViewModel(settings, store)
    tts = TtsService()
    ocr = OcrService(settings.tesseract_command)
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

    quick_vm = TranslationViewModel(manager, settings, store, history)
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

    desktop.register_shortcut(settings.clipboard_hotkey, "translate-clipboard")
    desktop.register_shortcut(settings.quick_translate_hotkey, "quick-translate")

    def _on_shortcut(action: str) -> None:
        if action == "translate-clipboard":
            _translate_clipboard(app, translation_vm, window)
        elif action == "quick-translate":
            _quick_translate_selection(app, desktop, quick_vm, quick_popup)

    desktop.shortcutTriggered.connect(_on_shortcut)
    settings_vm.saved.connect(lambda: desktop.set_startup_enabled(settings.start_with_system))
    return app.exec()


def _quick_translate_selection(app: QApplication, desktop: DesktopServices, model: TranslationViewModel, popup) -> None:
    if popup is None:
        return
    clipboard = app.clipboard()
    previous_text = clipboard.text()
    clipboard.clear()
    desktop.simulate_copy()

    def _finish() -> None:
        selected = clipboard.text().strip()
        if previous_text:
            clipboard.setText(previous_text)
        if not selected:
            return
        cursor = QCursor.pos()
        popup.popAt(cursor.x() + 12, cursor.y() + 12)
        model.sourceText = selected
        model.translate()

    QTimer.singleShot(150, _finish)


def _translate_clipboard(app: QGuiApplication, model: TranslationViewModel, window) -> None:
    text = app.clipboard().text().strip()
    if text:
        model.sourceText = text
        window.show()
        window.raise_()
        model.translate()


if __name__ == "__main__":
    raise SystemExit(main())
