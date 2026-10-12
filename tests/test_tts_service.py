from py_crow_tool.config import AppSettings
from py_crow_tool.core.models import TranslationError, TranslationException
from py_crow_tool.services.tts import TtsService


class _FakeProvider:
    def __init__(self, audio=b"mp3", error=None):
        self.api_key = ""
        self.audio = audio
        self.error = error
        self.calls = []

    async def synthesize(self, text, language, voice_type="chirp-hd", *, request_id=""):
        self.calls.append((text, language, voice_type, self.api_key))
        if self.error is not None:
            raise self.error
        return self.audio

    def cancel(self, request_id):
        pass

    async def close(self):
        pass


def _service(monkeypatch, provider, settings=None):
    service = TtsService(settings or AppSettings(), provider=provider)
    played = []
    monkeypatch.setattr(service, "_play", played.append)
    return service, played


def test_speak_fetches_with_current_settings_and_plays(monkeypatch, qapp, qtbot):
    settings = AppSettings(tts_voice="neural2")
    settings.google_v2.api_key = "abc"
    provider = _FakeProvider()
    service, played = _service(monkeypatch, provider, settings)
    service.speak("Xin chào", "vi", "popup")
    assert service.speaking
    qtbot.waitUntil(lambda: played == [b"mp3"])
    assert provider.calls == [("Xin chào", "vi", "neural2", "abc")]
    assert not service.speaking  # fetching is over; the faked player never started


def test_repeat_is_played_from_cache(monkeypatch, qapp, qtbot):
    provider = _FakeProvider()
    service, played = _service(monkeypatch, provider)
    service.speak("Xin chào", "vi")
    qtbot.waitUntil(lambda: len(played) == 1)
    service.speak("Xin chào", "vi")
    assert len(played) == 2
    assert len(provider.calls) == 1


def test_stop_before_audio_arrives_keeps_quiet(monkeypatch, qapp, qtbot):
    provider = _FakeProvider()
    service, played = _service(monkeypatch, provider)
    service.speak("Xin chào", "vi")
    service.stop()
    assert not service.speaking
    qtbot.wait(50)
    assert played == []
    # The audio still landed in the cache, so asking again costs no request.
    service.speak("Xin chào", "vi")
    assert played == [b"mp3"]
    assert len(provider.calls) == 1


def test_failure_is_reported_to_the_window_that_asked(monkeypatch, qapp, qtbot):
    provider = _FakeProvider(error=TranslationException(TranslationError.AUTHENTICATION, "API disabled"))
    service, played = _service(monkeypatch, provider)
    failures = []
    service.failed.connect(lambda message, origin: failures.append((message, origin)))
    service.speak("Xin chào", "vi", "popup")
    qtbot.waitUntil(lambda: bool(failures))
    assert failures == [("API disabled", "popup")]
    assert played == []
    assert not service.speaking


def test_rapid_clicks_share_one_request(monkeypatch, qapp, qtbot):
    import asyncio

    from py_crow_tool.services.async_runner import AsyncLoopRunner

    class _SlowProvider(_FakeProvider):
        async def synthesize(self, *args, **kwargs):
            await asyncio.sleep(0.3)
            return await super().synthesize(*args, **kwargs)

    runner = AsyncLoopRunner()
    provider = _SlowProvider()
    service = TtsService(AppSettings(), runner, provider=provider)
    played = []
    monkeypatch.setattr(service, "_play", played.append)
    try:
        # Read, stop, read, stop, read -- all before Google has answered once.
        for _ in range(3):
            service.speak("Xin chào", "vi")
            service.stop()
        service.speak("Xin chào", "vi")
        qtbot.waitUntil(lambda: played == [b"mp3"])
        assert len(provider.calls) == 1
        # And the audio it fetched is now cached for the next click.
        service.speak("Xin chào", "vi")
        assert played == [b"mp3", b"mp3"]
        assert len(provider.calls) == 1
    finally:
        runner.stop()


def test_blank_text_does_nothing(monkeypatch, qapp):
    provider = _FakeProvider()
    service, played = _service(monkeypatch, provider)
    service.speak("   ", "vi")
    assert provider.calls == [] and played == [] and not service.speaking
