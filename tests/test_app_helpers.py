from PySide6.QtCore import QPoint

from py_crow_tool.app import _popup_position
from types import SimpleNamespace
from unittest.mock import Mock

from PySide6.QtCore import QMimeData, QThread, Qt

from py_crow_tool.app import _quick_translate_selection, _ShortcutDispatcher
from py_crow_tool.services.desktop import DesktopServices


class _FakePopup:
    def __init__(self, width, height):
        self._props = {"width": width, "height": height}

    def property(self, name):
        return self._props[name]


def test_popup_position_offsets_from_the_cursor(qapp):
    popup = _FakePopup(380, 260)
    cursor = QPoint(100, 100)

    x, y = _popup_position(cursor, popup)

    assert x >= cursor.x()
    assert y >= cursor.y()


def test_popup_position_stays_within_the_screen(qapp):
    popup = _FakePopup(380, 260)
    screen = qapp.primaryScreen()
    geometry = screen.availableGeometry()
    # place the cursor right at the bottom-right corner, where a naive
    # "cursor + 12px" offset would push the popup off-screen
    cursor = QPoint(geometry.right(), geometry.bottom())

    x, y = _popup_position(cursor, popup)

    assert geometry.left() <= x <= geometry.right() - popup.property("width")
    assert geometry.top() <= y <= geometry.bottom() - popup.property("height")


def _capture_setup(monkeypatch):
    data = QMimeData()
    data.setText("old clipboard")
    data.setHtml("<b>old clipboard</b>")
    clipboard = SimpleNamespace(data=data)
    clipboard.mimeData = lambda: clipboard.data
    clipboard.text = lambda: clipboard.data.text()
    clipboard.clear = lambda: setattr(clipboard, "data", QMimeData())
    clipboard.setMimeData = lambda value: setattr(clipboard, "data", value)
    pending = []
    monkeypatch.setattr("py_crow_tool.app.QTimer.singleShot", lambda delay, callback: pending.append(callback))
    monkeypatch.setattr("py_crow_tool.app._popup_position", lambda *args: (100, 100))
    desktop = SimpleNamespace(selection_capture_pending=False, copy_modifiers_released=Mock(return_value=True), simulate_copy=Mock(return_value=True))
    model, popup, tray = Mock(), Mock(), Mock()
    app = SimpleNamespace(clipboard=lambda: clipboard)
    return app, clipboard, desktop, model, popup, tray, pending


def test_selection_waits_for_release_and_delayed_copy_and_ignores_spam(monkeypatch, qapp):
    app, clipboard, desktop, model, popup, tray, pending = _capture_setup(monkeypatch)
    desktop.copy_modifiers_released.side_effect = [False, True]
    _quick_translate_selection(app, desktop, model, popup, tray)
    desktop.simulate_copy.assert_not_called()
    assert clipboard.text() == "old clipboard"
    _quick_translate_selection(app, desktop, model, popup, tray)
    assert len(pending) == 1
    pending.pop(0)()
    desktop.simulate_copy.assert_called_once()
    pending.pop(0)()  # Copy has not arrived yet.
    popup.popAt.assert_not_called()
    model.translate.assert_not_called()
    clipboard.data.setText("selected text")
    pending.pop(0)()
    assert model.sourceText == "selected text"
    model.translate.assert_called_once()
    popup.popAt.assert_called_once()
    assert clipboard.text() == "old clipboard"
    assert clipboard.data.html() == "<b>old clipboard</b>"
    assert not desktop.selection_capture_pending


def test_failed_copy_never_translates_old_clipboard(monkeypatch, qapp):
    app, clipboard, desktop, model, popup, tray, pending = _capture_setup(monkeypatch)
    _quick_translate_selection(app, desktop, model, popup, tray)
    while pending:
        pending.pop(0)()
    model.translate.assert_not_called()
    popup.popAt.assert_not_called()
    tray.showMessage.assert_called_once()
    assert clipboard.text() == "old clipboard"
    assert not desktop.selection_capture_pending


def test_busy_clipboard_does_not_translate_stale_text(monkeypatch, qapp):
    app, clipboard, desktop, model, popup, tray, pending = _capture_setup(monkeypatch)
    clipboard.clear = lambda: None
    _quick_translate_selection(app, desktop, model, popup, tray)
    desktop.simulate_copy.assert_not_called()
    model.translate.assert_not_called()
    assert not desktop.selection_capture_pending
    tray.showMessage.assert_called_once()


def test_selection_can_match_previous_clipboard(monkeypatch, qapp):
    app, clipboard, desktop, model, popup, tray, pending = _capture_setup(monkeypatch)
    desktop.simulate_copy.side_effect = lambda: (clipboard.data.setText("old clipboard"), True)[1]
    _quick_translate_selection(app, desktop, model, popup, tray)
    pending.pop(0)()
    assert model.sourceText == "old clipboard"
    model.translate.assert_called_once()


def test_copy_injection_failure_restores_clipboard(monkeypatch, qapp):
    app, clipboard, desktop, model, popup, tray, pending = _capture_setup(monkeypatch)
    desktop.simulate_copy.return_value = False
    _quick_translate_selection(app, desktop, model, popup, tray)
    assert clipboard.text() == "old clipboard"
    assert not desktop.selection_capture_pending
    assert not pending
    model.translate.assert_not_called()
    tray.showMessage.assert_called_once()


def test_held_modifiers_timeout_without_touching_clipboard(monkeypatch, qapp):
    app, clipboard, desktop, model, popup, tray, pending = _capture_setup(monkeypatch)
    desktop.copy_modifiers_released.return_value = False
    _quick_translate_selection(app, desktop, model, popup, tray)
    while pending:
        pending.pop(0)()
    desktop.simulate_copy.assert_not_called()
    assert clipboard.text() == "old clipboard"
    assert not desktop.selection_capture_pending
    model.translate.assert_not_called()
    tray.showMessage.assert_called_once()


def test_shortcut_from_worker_runs_on_gui_thread(qapp, qtbot):
    import threading

    calls = []
    desktop = DesktopServices()
    receiver = _ShortcutDispatcher(lambda action: calls.append((action, QThread.currentThread())), qapp)
    desktop.shortcutTriggered.connect(receiver.dispatch, Qt.ConnectionType.QueuedConnection)
    thread = threading.Thread(target=lambda: desktop.shortcutTriggered.emit("quick-translate"))
    thread.start()
    thread.join()
    qtbot.waitUntil(lambda: bool(calls))
    assert calls == [("quick-translate", qapp.thread())]
