from __future__ import annotations

from PySide6.QtCore import Property, QObject, Signal, Slot


class TtsService(QObject):
    speakingChanged = Signal()

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._engine = None
        self._speaking = False
        self._locales_by_name: dict[str, object] | None = None
        try:
            from PySide6.QtTextToSpeech import QTextToSpeech

            self._engine = QTextToSpeech(self)
            self._engine.stateChanged.connect(self._on_state_changed)
        except ImportError:
            pass

    def _on_state_changed(self, state) -> None:
        from PySide6.QtTextToSpeech import QTextToSpeech

        speaking = state == QTextToSpeech.State.Speaking
        if speaking != self._speaking:
            self._speaking = speaking
            self.speakingChanged.emit()

    @Property(bool, notify=speakingChanged)
    def speaking(self):
        return self._speaking

    def _locale_for(self, language: str):
        if self._locales_by_name is None:
            self._locales_by_name = {locale.name().lower(): locale for locale in self._engine.availableLocales()}
        key = language.lower().replace("-", "_")
        for name, locale in self._locales_by_name.items():
            if name.startswith(key):
                return locale
        return None

    @Slot(str, str)
    def speak(self, text: str, language: str = "") -> None:
        if self._engine is None or not text:
            return
        self._engine.stop()
        if language:
            locale = self._locale_for(language)
            if locale is not None:
                self._engine.setLocale(locale)
        self._engine.say(text)

    @Slot()
    def stop(self) -> None:
        if self._engine is not None:
            self._engine.stop()
