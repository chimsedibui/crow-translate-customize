from __future__ import annotations

import asyncio
from dataclasses import asdict

from PySide6.QtCore import Property, QObject, Signal, Slot

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
    _errorReady = Signal(str)

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
            self._source_text = value
            self.sourceTextChanged.emit()

    @Property(str, notify=translatedTextChanged)
    def translatedText(self): return self._translated_text

    @Property(str, notify=sourceLanguageChanged)
    def sourceLanguage(self): return self._source_language

    @sourceLanguage.setter
    def sourceLanguage(self, value):
        if value != self._source_language:
            self._source_language = value
            self._settings.source_language = value
            self.sourceLanguageChanged.emit()

    @Property(str, notify=targetLanguageChanged)
    def targetLanguage(self): return self._target_language

    @targetLanguage.setter
    def targetLanguage(self, value):
        if value != self._target_language:
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

    @Slot()
    def translate(self):
        text = self._source_text.strip()
        if not text or self._busy:
            return
        self._set_busy(True)
        self._set_status("Translating...")
        request = TranslationRequest(text, self._target_language, self._source_language)
        future = self._loop_runner.submit(self._manager.translate(request))
        future.add_done_callback(lambda done: self._translation_done(done, request))

    def _translation_done(self, future, request):
        try:
            result = future.result()
        except Exception as error:
            self._errorReady.emit(str(error))
        else:
            self._resultReady.emit(result, request)

    @Slot(object, object)
    def _apply_result(self, result, request):
        self._translated_text = result.translated_text
        self.translatedTextChanged.emit()
        self._set_status(result.provider_id)
        detected = result.source_language if request.source_language == "auto" else ""
        if detected != self._detected_source_language:
            self._detected_source_language = detected
            self.detectedSourceLanguageChanged.emit()
        self._history.add(request.text, result.translated_text, result.source_language, result.target_language, result.provider_id)
        self.historyChanged.emit()
        self._loop_runner.submit(asyncio.to_thread(self._history.flush))
        self._set_busy(False)

    @Slot()
    def clearSource(self):
        self.sourceText = ""

    @Slot()
    def clearAll(self):
        self.sourceText = ""
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

    @Slot(str)
    def _apply_error(self, message):
        self._set_status(message)
        self._set_busy(False)

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

    def __init__(self, settings: AppSettings, store: SettingsStore, loop_runner: AsyncLoopRunner | None = None, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.store = store
        self._loop_runner = loop_runner

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
