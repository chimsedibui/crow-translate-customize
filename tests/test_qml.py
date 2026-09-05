from pathlib import Path

import pytest
import shiboken6
from PySide6.QtCore import QObject, Property, Signal, QUrl, QMetaObject
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest

from py_crow_tool.config import AppSettings, SettingsStore
from py_crow_tool.providers.manager import ProviderManager
from py_crow_tool.services.async_runner import AsyncLoopRunner
from py_crow_tool.services.history import HistoryStore
from py_crow_tool.viewmodels import TranslationViewModel, SettingsViewModel


class DesktopStub(QObject):
    failed = Signal(str)

    @Property(bool, constant=True)
    def speaking(self):
        return False


@pytest.fixture
def ui(qapp, tmp_path):
    QQuickStyle.setStyle("Basic")
    runner = AsyncLoopRunner()
    settings = AppSettings()
    store = SettingsStore(tmp_path / "settings.toml")
    model = TranslationViewModel(ProviderManager([]), settings, store, HistoryStore(tmp_path / "history.json"), runner)
    settings_model = SettingsViewModel(settings, store)
    service = DesktopStub()
    engine = QQmlApplicationEngine()
    warnings = []
    engine.warnings.connect(lambda errors: warnings.extend(error.toString() for error in errors))
    for name, obj in [("translationModel", model), ("quickTranslateModel", model), ("settingsModel", settings_model), ("ttsService", service), ("ocrService", service)]:
        engine.rootContext().setContextProperty(name, obj)
    qml_dir = Path(__file__).parents[1] / "src/py_crow_tool/qml"
    engine.load(QUrl.fromLocalFile(str(qml_dir / "Main.qml")))
    assert engine.rootObjects(), warnings
    window = engine.rootObjects()[0]
    qapp.processEvents()
    yield window, model, settings_model, service, engine, warnings, qml_dir
    shiboken6.delete(engine)
    runner.stop()


def test_language_selectors_track_model_and_swap(ui, qapp):
    window, model, *rest = ui
    source = window.findChild(QObject, "sourceLanguage")
    target = window.findChild(QObject, "targetLanguage")
    assert source.property("currentValue") == "auto"
    model.sourceLanguage = "en"
    model.targetLanguage = "vi"
    model.swapLanguages()
    qapp.processEvents()
    assert source.property("currentValue") == "vi"
    assert target.property("currentValue") == "en"
    assert not ui[5]


def test_settings_cancel_discards_draft(ui, qapp):
    window, model, settings, *_ = ui
    dialog = window.findChild(QObject, "settingsDialog")
    QMetaObject.invokeMethod(dialog, "open")
    qapp.processEvents()
    window.findChild(QObject, "apiKey").setProperty("text", "draft-secret")
    window.findChild(QObject, "startup").setProperty("checked", True)
    QMetaObject.invokeMethod(dialog, "reject")
    assert settings.apiKey == ""
    assert settings.startWithSystem is False
    QMetaObject.invokeMethod(dialog, "open")
    qapp.processEvents()
    assert window.findChild(QObject, "apiKey").property("text") == ""
    assert not ui[5]


def test_hotkey_records_keys_and_cancel_discards_draft(ui, qapp):
    window, model, settings, *_ = ui
    dialog = window.findChild(QObject, "settingsDialog")
    QMetaObject.invokeMethod(dialog, "open")
    qapp.processEvents()
    hotkey = window.findChild(QObject, "hotkey")
    QMetaObject.invokeMethod(hotkey, "forceActiveFocus")
    hotkey.setProperty("recording", True)
    QTest.keyClick(window, Qt.Key_K, Qt.ControlModifier | Qt.ShiftModifier)
    assert hotkey.property("sequence") == "Ctrl+Shift+K"
    assert not settings.recordingHotkey
    assert settings.quickTranslateHotkey == "ctrl+alt+q"
    hotkey.setProperty("recording", True)
    QTest.keyClick(window, Qt.Key_Escape)
    assert dialog.property("visible")
    assert not hotkey.property("recording")
    assert hotkey.property("sequence") == "Ctrl+Shift+K"
    QMetaObject.invokeMethod(dialog, "reject")
    QMetaObject.invokeMethod(dialog, "open")
    qapp.processEvents()
    assert hotkey.property("sequence") == "ctrl+alt+q"
    assert not ui[5]


def test_hotkey_rejects_typing_and_conflicts_then_saves(ui, qapp):
    window, model, settings, *_ = ui
    dialog = window.findChild(QObject, "settingsDialog")
    QMetaObject.invokeMethod(dialog, "open")
    qapp.processEvents()
    hotkey = window.findChild(QObject, "hotkey")
    QMetaObject.invokeMethod(hotkey, "forceActiveFocus")
    hotkey.setProperty("recording", True)
    QTest.keyClick(window, Qt.Key_A)
    assert hotkey.property("recording")
    assert hotkey.property("error")
    QTest.keyClick(window, Qt.Key_T, Qt.ControlModifier | Qt.AltModifier)
    assert "clipboard" in hotkey.property("error")
    assert hotkey.property("sequence") == "ctrl+alt+q"
    QTest.keyClick(window, Qt.Key_F8)
    assert hotkey.property("sequence") == "F8"
    assert not hotkey.property("error")
    QMetaObject.invokeMethod(dialog, "accept")
    assert settings.quickTranslateHotkey == "F8"
    assert settings.store.load().quick_translate_hotkey == "F8"
    assert not ui[5]


def test_ocr_error_and_popup_load(ui, qapp):
    window, model, settings, service, engine, warnings, qml_dir = ui
    model.sourceText = "Preserve me"
    service.failed.emit("No clipboard image")
    assert model.sourceText == "Preserve me"
    assert model.error == "No clipboard image"
    window.setProperty("width", 720)
    window.setProperty("height", 540)
    engine.load(QUrl.fromLocalFile(str(qml_dir / "QuickTranslatePopup.qml")))
    qapp.processEvents()
    assert len(engine.rootObjects()) == 2
    assert not warnings


def test_history_filter_and_restore(ui, qapp):
    window, model, *_ = ui
    model._history.add("hello", "xin chào", "en", "vi", "fake")
    model.historyChanged.emit()
    drawer = window.findChild(QObject, "historyDrawer")
    QMetaObject.invokeMethod(drawer, "open")
    qapp.processEvents()
    listing = window.findChild(QObject, "historyList")
    assert listing.property("count") == 1
    search = window.findChild(QObject, "historySearch")
    search.setProperty("text", "missing")
    qapp.processEvents()
    assert listing.property("count") == 0
    search.setProperty("text", "xin")
    qapp.processEvents()
    assert listing.property("count") == 1
    model.restoreHistory("hello", "xin chào", "en", "vi")
    assert model.sourceText == "hello"
    assert model.translatedText == "xin chào"
    assert model.targetLanguage == "vi"
    assert not ui[5]
