from __future__ import annotations

from PySide6.QtCore import QObject, Slot


class TtsService(QObject):
    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._engine = None
        try:
            from PySide6.QtTextToSpeech import QTextToSpeech

            self._engine = QTextToSpeech(self)
        except ImportError:
            pass

    @Slot(str, str)
    def speak(self, text: str, language: str = "") -> None:
        if self._engine is None:
            return
        if language:
            for locale in self._engine.availableLocales():
                if locale.name().lower().startswith(language.lower().replace("-", "_")):
                    self._engine.setLocale(locale)
                    break
        self._engine.say(text)

    @Slot()
    def stop(self) -> None:
        if self._engine is not None:
            self._engine.stop()
