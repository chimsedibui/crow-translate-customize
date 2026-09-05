import time
import asyncio

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


def _stop_runner(runner):
    async def drain():
        pending = [task for task in asyncio.all_tasks() if task is not asyncio.current_task()]
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)
    runner.run_sync(drain(), timeout=2)
    runner.stop()


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
        _stop_runner(runner)


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
        _stop_runner(runner)


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
        _stop_runner(runner)


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
        _stop_runner(runner)


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
        _stop_runner(runner)


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
        _stop_runner(runner)


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
        _stop_runner(runner)


def test_latest_input_is_translated_after_inflight_request(qapp, tmp_path):
    import asyncio

    class SlowProvider(FakeProvider):
        async def translate(self, request):
            await asyncio.sleep(0.06)
            return await super().translate(request)

    runner = AsyncLoopRunner()
    try:
        provider = SlowProvider()
        vm, history = _make_vm(qapp, tmp_path, runner, provider)
        vm._settings.auto_translate = True
        seen = []
        vm.translatedTextChanged.connect(lambda: seen.append(vm.translatedText))
        vm.sourceText = "old"
        vm.translate()
        vm.sourceText = "latest"
        vm.translate()
        _wait_for_translate(qapp, vm, history)
        assert seen == ["latest-translated"]
        assert provider.calls == 2
        assert [item["source"] for item in vm.history] == ["latest"]
    finally:
        _stop_runner(runner)


def test_clear_during_request_does_not_restore_old_result(qapp, tmp_path):
    class SlowProvider(FakeProvider):
        async def translate(self, request):
            await asyncio.sleep(0.06)
            return await super().translate(request)

    runner = AsyncLoopRunner()
    try:
        vm, _ = _make_vm(qapp, tmp_path, runner, SlowProvider())
        vm.sourceText = "old"
        vm.translate()
        vm.clearAll()
        assert _pump_until(qapp, lambda: not vm.busy)
        assert vm.translatedText == ""
        assert vm.history == []
    finally:
        _stop_runner(runner)


def test_stale_failure_does_not_hide_latest_translation(qapp, tmp_path):
    class FailingFirstProvider(FakeProvider):
        async def translate(self, request):
            if request.text == "old":
                raise RuntimeError("Old request failed")
            return await super().translate(request)

    runner = AsyncLoopRunner()
    try:
        vm, history = _make_vm(qapp, tmp_path, runner, FailingFirstProvider())
        vm.sourceText = "old"
        vm.translate()
        vm.sourceText = "new"
        vm.translate()
        _wait_for_translate(qapp, vm, history)
        assert vm.translatedText == "new-translated"
        assert vm.error == ""
    finally:
        _stop_runner(runner)


def test_report_ocr_error_preserves_source(qapp, tmp_path):
    runner = AsyncLoopRunner()
    try:
        vm, _ = _make_vm(qapp, tmp_path, runner)
        vm.sourceText = "Keep this text"
        vm.reportError("No clipboard image")
        assert vm.sourceText == "Keep this text"
        assert vm.error == "No clipboard image"
    finally:
        _stop_runner(runner)
