import time

from py_crow_tool.config import AppSettings, SettingsStore
from py_crow_tool.core.models import TranslationResult
from py_crow_tool.providers.manager import ProviderManager
from py_crow_tool.services.async_runner import AsyncLoopRunner
from py_crow_tool.services.history import HistoryStore
from py_crow_tool.viewmodels import SettingsViewModel, TranslationViewModel


class FakeProvider:
    id = "fake"
    display_name = "Fake"
    configured = True

    def __init__(self):
        self.calls = 0

    async def translate(self, request):
        self.calls += 1
        return TranslationResult(f"{request.text}-translated", "en", request.target_language, self.id)

    async def detect_language(self, text):
        raise NotImplementedError

    def supported_languages(self):
        return []

    def cancel(self, request_id):
        pass

    async def close(self):
        pass


def _pump_until(qapp, predicate, timeout=2.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        qapp.processEvents()
        if predicate():
            return True
        time.sleep(0.01)
    return False


def _make_vm(qapp, tmp_path, loop_runner, provider=None):
    manager = ProviderManager([provider or FakeProvider()])
    settings = AppSettings()
    store = SettingsStore(tmp_path / "settings.toml")
    history = HistoryStore(tmp_path / "history.json", limit=10)
    return TranslationViewModel(manager, settings, store, history, loop_runner), history


def _wait_for_translate(qapp, vm, history) -> None:
    """Wait for an in-flight translate() to finish, including its background
    history flush — a successful translate() always schedules one on the loop
    runner, and stopping the runner before it lands would leak an unawaited
    coroutine (surfaced as a 'coroutine was never awaited' warning)."""
    assert _pump_until(qapp, lambda: not vm.busy)
    assert _pump_until(qapp, lambda: history.path.exists())


def test_translate_updates_translated_text_status_and_history(qapp, tmp_path):
    runner = AsyncLoopRunner()
    try:
        vm, history = _make_vm(qapp, tmp_path, runner)
        vm.sourceText = "hello"

        vm.translate()
        assert vm.busy is True
        _wait_for_translate(qapp, vm, history)

        assert vm.translatedText == "hello-translated"
        assert vm.status == "fake"
        assert len(vm.history) == 1
    finally:
        runner.stop()


def test_translate_is_a_noop_while_already_busy_or_for_blank_text(qapp, tmp_path):
    runner = AsyncLoopRunner()
    try:
        provider = FakeProvider()
        vm, history = _make_vm(qapp, tmp_path, runner, provider)

        vm.sourceText = "   "
        vm.translate()
        assert provider.calls == 0

        vm.sourceText = "hello"
        vm.translate()
        vm.translate()  # second call while busy must not submit another request
        _wait_for_translate(qapp, vm, history)
        assert provider.calls == 1
    finally:
        runner.stop()


def test_swap_languages_uses_detected_language_when_source_is_auto(qapp, tmp_path):
    runner = AsyncLoopRunner()
    try:
        vm, history = _make_vm(qapp, tmp_path, runner)
        vm.sourceLanguage = "auto"
        vm.targetLanguage = "vi"
        vm.sourceText = "hello"
        vm.translate()
        _wait_for_translate(qapp, vm, history)

        # translate() above ran with source_language "auto", so the result's
        # source_language ("en") becomes the detected language.
        assert vm.detectedSourceLanguage == "en"

        vm.swapLanguages()

        assert vm.sourceLanguage == "vi"
        assert vm.targetLanguage == "en"
        assert vm.sourceText == "hello-translated"
        assert vm.translatedText == "hello"
        assert vm.detectedSourceLanguage == ""
    finally:
        runner.stop()


def test_swap_languages_does_nothing_without_a_resolved_source(qapp, tmp_path):
    runner = AsyncLoopRunner()
    try:
        vm, _ = _make_vm(qapp, tmp_path, runner)
        vm.sourceLanguage = "auto"
        vm.targetLanguage = "en"
        vm.sourceText = "hello"

        vm.swapLanguages()  # nothing detected yet: must be a no-op

        assert vm.sourceLanguage == "auto"
        assert vm.sourceText == "hello"
    finally:
        runner.stop()


def test_clear_all_resets_both_fields(qapp, tmp_path):
    runner = AsyncLoopRunner()
    try:
        vm, history = _make_vm(qapp, tmp_path, runner)
        vm.sourceText = "hello"
        vm.translate()
        _wait_for_translate(qapp, vm, history)

        vm.clearAll()

        assert vm.sourceText == ""
        assert vm.translatedText == ""
    finally:
        runner.stop()


def test_save_preferences_replaces_provider_and_closes_the_old_one(qapp, tmp_path):
    runner = AsyncLoopRunner()
    try:
        closed = {"value": False}

        class ClosableFakeProvider(FakeProvider):
            async def close(self):
                closed["value"] = True

        vm, _ = _make_vm(qapp, tmp_path, runner, ClosableFakeProvider())
        settings_path = tmp_path / "settings.toml"

        vm.savePreferences()

        # savePreferences() dispatches both the settings write and the old
        # provider's close() to the loop runner; wait for both before
        # stopping it, or the settings coroutine can be torn down mid-flight.
        assert _pump_until(qapp, lambda: closed["value"] and settings_path.exists())
    finally:
        runner.stop()


def test_settings_view_model_save_dispatches_to_loop_runner(qapp, tmp_path):
    runner = AsyncLoopRunner()
    try:
        settings = AppSettings()
        store = SettingsStore(tmp_path / "settings.toml")
        vm = SettingsViewModel(settings, store, runner)

        saved_events = []
        vm.saved.connect(lambda: saved_events.append(True))
        vm.startWithSystem = True

        vm.save()

        assert saved_events == [True]
        assert _pump_until(qapp, lambda: store.path.exists())
        assert store.load().start_with_system is True
    finally:
        runner.stop()
