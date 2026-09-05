from __future__ import annotations

import asyncio
from dataclasses import asdict

from PySide6.QtCore import Property, QObject, Signal, Slot, Qt, QKeyCombination
from PySide6.QtGui import QKeySequence

from py_crow_tool.config import AppSettings, SettingsStore
from py_crow_tool.core.languages import LANGUAGES
from py_crow_tool.core.models import TranslationException, TranslationRequest
from py_crow_tool.providers.manager import ProviderManager
from py_crow_tool.providers.google_v2 import GoogleV2Provider
from py_crow_tool.services.async_runner import AsyncLoopRunner
from py_crow_tool.services.history import HistoryStore


class TranslationViewModel(QObject):
    sourceTextChanged = Signal()
    translatedTextChanged = Signal()
    sourceLanguageChanged = Signal()
    targetLanguageChanged = Signal()
    busyChanged = Signal()
    statusChanged = Signal()
    historyChanged = Signal()
    detectedSourceLanguageChanged = Signal()
    _resultReady = Signal(object, object)
    errorChanged = Signal()
    _errorReady = Signal(str, object)

    def __init__(
        self,
        manager: ProviderManager,
        settings: AppSettings,
        settings_store: SettingsStore,
        history: HistoryStore,
        loop_runner: AsyncLoopRunner,
        parent=None,
    ):
        super().__init__(parent)
        self._manager = manager
        self._settings = settings
        self._settings_store = settings_store
        self._history = history
        self._loop_runner = loop_runner
        self._source_text = ""
        self._translated_text = ""
        self._source_language = settings.source_language
        self._target_language = settings.target_language
        self._busy = False
        self._revision = 0
        self._pending = False
        self._error = ""
        self._detected_source_language = ""
        self._status = self._provider_status()
        self._resultReady.connect(self._apply_result)
        self._errorReady.connect(self._apply_error)

    def _provider_status(self) -> str:
        try:
            return self._manager.active_provider.display_name
        except TranslationException:
            return "Configure Google Cloud in Settings"

    @Property(str, notify=sourceTextChanged)
    def sourceText(self): return self._source_text

    @sourceText.setter
    def sourceText(self, value):
        if value != self._source_text:
            self._input_changed()
            self._source_text = value
            self.sourceTextChanged.emit()

    @Property(str, notify=translatedTextChanged)
    def translatedText(self): return self._translated_text

    @Property(str, notify=sourceLanguageChanged)
    def sourceLanguage(self): return self._source_language

    @sourceLanguage.setter
    def sourceLanguage(self, value):
        if value != self._source_language:
            self._input_changed()
            self._source_language = value
            self._settings.source_language = value
            self.sourceLanguageChanged.emit()

    @Property(str, notify=targetLanguageChanged)
    def targetLanguage(self): return self._target_language

    @targetLanguage.setter
    def targetLanguage(self, value):
        if value != self._target_language:
            self._input_changed()
            self._target_language = value
            self._settings.target_language = value
            self.targetLanguageChanged.emit()

    @Property(bool, notify=busyChanged)
    def busy(self): return self._busy

    @Property(str, notify=statusChanged)
    def status(self): return self._status

    @Property(str, notify=detectedSourceLanguageChanged)
    def detectedSourceLanguage(self): return self._detected_source_language

    @Property("QVariantList", constant=True)
    def languages(self):
        return [{"code": code, "name": name} for code, name in LANGUAGES]

    @Property("QVariantList", notify=historyChanged)
    def history(self):
        return [asdict(item) for item in self._history.load()]

    @Property(str, notify=errorChanged)
    def error(self): return self._error

    @Slot(str)
    def reportError(self, message):
        self._error = message
        self.errorChanged.emit()

    def _input_changed(self):
        self._revision += 1
        if self._translated_text:
            self._set_status("Text changed — translate to update")
        self.reportError("")
        if self._busy and self._settings.auto_translate:
            self._pending = True
        if self._detected_source_language:
            self._detected_source_language = ""
            self.detectedSourceLanguageChanged.emit()

    @Slot()
    def translate(self):
        text = self._source_text.strip()
        if not text:
            return
        if self._busy:
            self._pending = True
            return
        self._pending = False
        self.reportError("")
        self._set_busy(True)
        self._set_status("Translating…")
        request = TranslationRequest(text, self._target_language, self._source_language)
        revision = self._revision
        future = self._loop_runner.submit(self._manager.translate(request))
        future.add_done_callback(lambda done: self._translation_done(done, (request, revision)))

    def _translation_done(self, future, context):
        try:
            result = future.result()
        except Exception as error:
            self._errorReady.emit(str(error), context)
        else:
            self._resultReady.emit(result, context)

    def _finish_request(self, revision):
        self._set_busy(False)
        pending = self._pending and revision != self._revision
        self._pending = False
        if pending:
            self.translate()

    @Slot(object, object)
    def _apply_result(self, result, context):
        request, revision = context
        if revision == self._revision:
            self._translated_text = result.translated_text
            self.translatedTextChanged.emit()
            self._set_status(result.provider_id)
            self._detected_source_language = result.source_language if request.source_language == "auto" else ""
            self.detectedSourceLanguageChanged.emit()
            self._history.add(request.text, result.translated_text, result.source_language, result.target_language, result.provider_id)
            self.historyChanged.emit()
            self._loop_runner.submit(asyncio.to_thread(self._history.flush))
        else:
            self._set_status("Text changed — translate to update")
        self._finish_request(revision)

    @Slot()
    def clearSource(self):
        self.sourceText = ""

    @Slot()
    def clearAll(self):
        self.sourceText = ""
        self._pending = False
        self.reportError("")
        if self._translated_text:
            self._translated_text = ""
            self.translatedTextChanged.emit()

    @Slot()
    def copyTranslated(self):
        from PySide6.QtGui import QGuiApplication

        if self._translated_text:
            QGuiApplication.clipboard().setText(self._translated_text)

    @Slot()
    def copySource(self):
        from PySide6.QtGui import QGuiApplication

        if self._source_text:
            QGuiApplication.clipboard().setText(self._source_text)

    @Slot()
    def pasteSource(self):
        from PySide6.QtGui import QGuiApplication

        text = QGuiApplication.clipboard().text()
        if text:
            self.sourceText = text

    @Slot(str, object)
    def _apply_error(self, message, context):
        _, revision = context
        if revision == self._revision:
            self.reportError(message)
            self._set_status("Translation failed")
        self._finish_request(revision)

    @Slot(str, str, str, str)
    def restoreHistory(self, source, translation, source_language, target_language):
        self.sourceLanguage = source_language
        self.targetLanguage = target_language
        self.sourceText = source
        self._translated_text = translation
        self.translatedTextChanged.emit()
        self._pending = False
        self._set_status("Restored from history")

    @Slot()
    def swapLanguages(self):
        resolved_source = self._detected_source_language if self._source_language == "auto" else self._source_language
        if not resolved_source or resolved_source == self._target_language:
            return
        self.sourceLanguage, self.targetLanguage = self._target_language, resolved_source
        self._source_text, self._translated_text = self._translated_text, self._source_text
        self.sourceTextChanged.emit()
        self.translatedTextChanged.emit()
        if self._detected_source_language:
            self._detected_source_language = ""
            self.detectedSourceLanguageChanged.emit()

    @Slot()
    def clearHistory(self):
        self._history.clear()
        self.historyChanged.emit()

    @Slot()
    def savePreferences(self):
        self._loop_runner.submit(asyncio.to_thread(self._settings_store.save, self._settings))
        old_providers = self._manager.replace([GoogleV2Provider(self._settings.v2_api_key)])
        self._loop_runner.submit(ProviderManager.close_providers(old_providers))
        self._set_status(self._provider_status())

    def _set_busy(self, value):
        self._busy = value
        self.busyChanged.emit()

    def _set_status(self, value):
        self._status = value
        self.statusChanged.emit()


class SettingsViewModel(QObject):
    saved = Signal()
    settingsChanged = Signal()
    recordingHotkeyChanged = Signal()

    def __init__(self, settings: AppSettings, store: SettingsStore, loop_runner: AsyncLoopRunner | None = None, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.store = store
        self._loop_runner = loop_runner
        self._recording_hotkey = False

    @Property(bool, notify=recordingHotkeyChanged)
    def recordingHotkey(self): return self._recording_hotkey

    @recordingHotkey.setter
    def recordingHotkey(self, value):
        if value != self._recording_hotkey:
            self._recording_hotkey = value
            self.recordingHotkeyChanged.emit()

    @Slot(int, int, result=str)
    def captureHotkey(self, key, modifiers):
        from py_crow_tool.services.desktop import _windows_hotkey

        allowed = Qt.ControlModifier | Qt.AltModifier | Qt.ShiftModifier | Qt.MetaModifier
        mods = Qt.KeyboardModifier(modifiers) & allowed
        # Plain typing keys must remain available to other applications.
        if not mods and not Qt.Key_F1 <= key <= Qt.Key_F24:
            return ""
        sequence = QKeySequence(QKeyCombination(mods, Qt.Key(key)))
        text = sequence.toString(QKeySequence.PortableText)
        try:
            _windows_hotkey(text)
        except ValueError:
            return ""
        return text

    @Slot(str, result=bool)
    def hotkeyConflicts(self, sequence):
        return QKeySequence(sequence) == QKeySequence(self.settings.clipboard_hotkey)

    @Property(str, notify=settingsChanged)
    def apiKey(self): return self.settings.google_v2.api_key

    @apiKey.setter
    def apiKey(self, value):
        if value != self.settings.google_v2.api_key:
            self.settings.google_v2.api_key = value
            self.settingsChanged.emit()

    @Property(bool, notify=settingsChanged)
    def autoTranslate(self): return self.settings.auto_translate

    @autoTranslate.setter
    def autoTranslate(self, value):
        if value != self.settings.auto_translate:
            self.settings.auto_translate = value
            self.settingsChanged.emit()

    @Property(bool, notify=settingsChanged)
    def startWithSystem(self): return self.settings.start_with_system

    @startWithSystem.setter
    def startWithSystem(self, value):
        if value != self.settings.start_with_system:
            self.settings.start_with_system = value
            self.settingsChanged.emit()

    @Property(str, notify=settingsChanged)
    def quickTranslateHotkey(self): return self.settings.quick_translate_hotkey

    @quickTranslateHotkey.setter
    def quickTranslateHotkey(self, value):
        if value != self.settings.quick_translate_hotkey:
            self.settings.quick_translate_hotkey = value
            self.settingsChanged.emit()

    @Slot()
    def save(self):
        if self._loop_runner is not None:
            self._loop_runner.submit(asyncio.to_thread(self.store.save, self.settings))
        else:
            self.store.save(self.settings)
        self.saved.emit()
