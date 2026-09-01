from __future__ import annotations

import sys
import os
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QAction, QGuiApplication, QIcon
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
    engine.load(QUrl.fromLocalFile(str(Path(__file__).with_name("qml") / "Main.qml")))
    if not engine.rootObjects():
        return 1
    window = engine.rootObjects()[0]

    ocr.recognized.connect(lambda text: setattr(translation_vm, "sourceText", text))
    instance.activated.connect(lambda: (window.show(), window.raise_(), window.requestActivate()))

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

    desktop.register_shortcut("ctrl+alt+t", "translate-clipboard")
    desktop.shortcutTriggered.connect(lambda action: _translate_clipboard(app, translation_vm, window) if action == "translate-clipboard" else None)
    return app.exec()


def _translate_clipboard(app: QGuiApplication, model: TranslationViewModel, window) -> None:
    text = app.clipboard().text().strip()
    if text:
        model.sourceText = text
        window.show()
        window.raise_()
        model.translate()


if __name__ == "__main__":
    raise SystemExit(main())
