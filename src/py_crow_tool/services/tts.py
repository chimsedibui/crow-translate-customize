from __future__ import annotations

import asyncio
import uuid
from collections import OrderedDict

from PySide6.QtCore import Property, QBuffer, QByteArray, QIODevice, QObject, Qt, QUrl, Signal, Slot
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer

from py_crow_tool.config import AppSettings
from py_crow_tool.core.models import TranslationError, TranslationException
from py_crow_tool.providers.google_tts import GoogleTtsProvider
from py_crow_tool.services.async_runner import AsyncLoopRunner


class TtsService(QObject):
    """Reads text aloud with Google Cloud Text-to-Speech.

    There is deliberately no fallback to the Windows voices: they were what made
    read-aloud sound bad in the first place, and with no Vietnamese voice installed
    Windows reads Vietnamese in an English voice. A failure is reported instead.
    """

    speakingChanged = Signal()
    # origin is whatever the caller passed to speak(), so each window only reports
    # the failures of the requests it made.
    failed = Signal(str, str)
    # Results arrive on the async loop's thread; these hop them to the GUI thread,
    # which is the only place the media player may be touched.
    _audioReady = Signal(str, object, object)
    _requestFailed = Signal(str, str)

    # Enough for "play that again" and flipping between the two panes, without
    # holding on to audio for every sentence of a long session.
    CACHE_SIZE = 16

    def __init__(
        self,
        settings: AppSettings,
        loop_runner: AsyncLoopRunner | None = None,
        provider: GoogleTtsProvider | None = None,
        parent: QObject | None = None,
    ):
        super().__init__(parent)
        self._settings = settings
        self._loop_runner = loop_runner
        self._provider = provider or GoogleTtsProvider()
        self._cache: OrderedDict[tuple[str, str, str], bytes] = OrderedDict()
        self._pending: str | None = None
        self._pending_origin = ""
        self._loading = False
        self._playing = False
        self._player: QMediaPlayer | None = None
        self._buffer: QBuffer | None = None
        self._audioReady.connect(self._on_audio_ready, Qt.ConnectionType.QueuedConnection)
        self._requestFailed.connect(self._on_request_failed, Qt.ConnectionType.QueuedConnection)

    @Property(bool, notify=speakingChanged)
    def speaking(self):
        # Fetching counts: the button has to offer "stop" from the moment it is
        # pressed, not only once the audio starts a second later.
        return self._loading or self._playing

    def _set_state(self, *, loading: bool | None = None, playing: bool | None = None) -> None:
        before = self.speaking
        if loading is not None:
            self._loading = loading
        if playing is not None:
            self._playing = playing
        if self.speaking != before:
            self.speakingChanged.emit()

    @Slot(str, str)
    @Slot(str, str, str)
    def speak(self, text: str, language: str = "", origin: str = "") -> None:
        text = text.strip()
        if not text:
            return
        self.stop()
        self._pending_origin = origin
        key = (text, language, self._settings.tts_voice)
        if key in self._cache:
            self._cache.move_to_end(key)
            self._play(self._cache[key])
            return
        request_id = uuid.uuid4().hex
        self._pending = request_id
        self._set_state(loading=True)
        # Read at call time, so a key or voice changed in Settings applies to the
        # very next sentence.
        self._provider.api_key = self._settings.v2_api_key.strip()

        async def _operation() -> None:
            try:
                audio = await self._provider.synthesize(text, language, self._settings.tts_voice, request_id=request_id)
            except TranslationException as error:
                if error.kind != TranslationError.CANCELLED:
                    self._requestFailed.emit(request_id, str(error))
                return
            self._audioReady.emit(request_id, key, audio)

        if self._loop_runner is not None:
            self._loop_runner.submit(_operation())
        else:
            asyncio.run(_operation())

    def _on_audio_ready(self, request_id: str, key, audio: bytes) -> None:
        self._cache[key] = audio
        while len(self._cache) > self.CACHE_SIZE:
            self._cache.popitem(last=False)
        # A stop() or a newer speak() since this was requested: keep the audio for
        # next time, but do not start talking over whatever the user did since.
        if request_id != self._pending:
            return
        self._pending = None
        self._play(audio)
        self._set_state(loading=False)

    def _on_request_failed(self, request_id: str, message: str) -> None:
        if request_id != self._pending:
            return
        self._pending = None
        self._set_state(loading=False)
        self.failed.emit(message, self._pending_origin)

    def _ensure_player(self) -> QMediaPlayer:
        if self._player is None:
            self._player = QMediaPlayer(self)
            self._player.setAudioOutput(QAudioOutput(self._player))
            self._player.playbackStateChanged.connect(
                lambda state: self._set_state(playing=state == QMediaPlayer.PlaybackState.PlayingState)
            )
            self._player.errorOccurred.connect(self._on_player_error)
        return self._player

    def _on_player_error(self, _error, message: str) -> None:
        self._set_state(playing=False)
        self.failed.emit(message or "Could not play the audio", self._pending_origin)

    def _play(self, audio: bytes) -> None:
        player = self._ensure_player()
        player.stop()
        # The player reads from the buffer for as long as it plays, so the buffer has
        # to outlive this call. The URL only tells the decoder to expect MP3.
        buffer = QBuffer(self)
        buffer.setData(QByteArray(audio))
        buffer.open(QIODevice.OpenModeFlag.ReadOnly)
        player.setSourceDevice(buffer, QUrl("speech.mp3"))
        if self._buffer is not None:
            self._buffer.deleteLater()
        self._buffer = buffer
        player.play()
        # The player reports PlayingState a moment later; until then the button would
        # flick back to "read" between the fetch ending and the sound starting.
        self._set_state(playing=True)

    @Slot()
    def stop(self) -> None:
        if self._pending is not None:
            request_id, self._pending = self._pending, None
            # The request's task lives on the async loop, and asyncio tasks may only be
            # cancelled from their own loop's thread.
            if self._loop_runner is not None:
                async def _cancel() -> None:
                    self._provider.cancel(request_id)

                self._loop_runner.submit(_cancel())
        self._set_state(loading=False)
        if self._player is not None:
            self._player.stop()

    async def close(self) -> None:
        await self._provider.close()
