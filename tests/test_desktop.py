import builtins
import sys

import pytest

from py_crow_tool.services.desktop import DesktopServices, SingleInstance


def _block_import(monkeypatch, blocked_name: str) -> None:
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == blocked_name:
            raise ImportError(f"No module named '{blocked_name}'")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)


def test_register_shortcut_returns_false_when_keyboard_module_is_missing(monkeypatch, capsys):
    monkeypatch.setattr(sys, "platform", "linux")
    _block_import(monkeypatch, "keyboard")
    desktop = DesktopServices()

    assert desktop.register_shortcut("ctrl+alt+q", "quick-translate") is False
    assert "unavailable" in capsys.readouterr().err


@pytest.mark.skipif(sys.platform != "win32", reason="Windows native hotkeys")
def test_native_hotkey_registration_conflict_and_cleanup(qapp, capsys):
    first, second = DesktopServices(), DesktopServices()
    received = []
    first.shortcutTriggered.connect(received.append)
    try:
        assert first.register_shortcut("ctrl+alt+f23", "quick-translate")
        assert not second.register_shortcut("ctrl+alt+f23", "other")
        assert "unavailable" in capsys.readouterr().err
        hotkey_id = next(iter(first._native_actions))
        assert first._on_native_hotkey(hotkey_id)
        assert received == ["quick-translate"]
        assert not first._on_native_hotkey(-1)
        first.unregister_shortcuts()
        assert second.register_shortcut("ctrl+alt+f23", "other")
    finally:
        first.unregister_shortcuts()
        second.unregister_shortcuts()


@pytest.mark.parametrize("sequence, expected", [("ctrl+alt+q", (0x4003, 81)), ("ctrl+alt+F8", (0x4003, 0x77)), ("Ctrl+Shift+Space", (0x4006, 32))])
def test_windows_hotkey_mapping(sequence, expected):
    from py_crow_tool.services.desktop import _windows_hotkey
    assert _windows_hotkey(sequence) == expected


def test_windows_hotkey_rejects_invalid_sequence():
    from py_crow_tool.services.desktop import _windows_hotkey
    with pytest.raises(ValueError):
        _windows_hotkey("not-a-key")


def test_simulate_copy_returns_false_when_keyboard_module_is_missing(monkeypatch, capsys):
    _block_import(monkeypatch, "keyboard")

    assert DesktopServices.simulate_copy() is False
    assert "Could not simulate" in capsys.readouterr().err


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX mode bits are not supported on Windows")
def test_credential_file_is_private_checks_permissions_on_posix(tmp_path):
    path = tmp_path / "creds.json"
    path.write_text("{}")
    path.chmod(0o600)
    assert DesktopServices.credential_file_is_private(path) is True

    path.chmod(0o644)
    assert DesktopServices.credential_file_is_private(path) is False


def test_single_instance_second_instance_is_not_primary(qapp):
    name = "py-crow-test-single-instance"
    first = SingleInstance(name)
    try:
        assert first.is_primary is True
        second = SingleInstance(name)
        assert second.is_primary is False
    finally:
        first.deleteLater()


def test_single_instance_falls_back_to_primary_with_a_warning_when_locking_fails(monkeypatch, qapp, capsys):
    class AlwaysFailsToListen:
        def __init__(self, parent=None):
            self.newConnection = _FakeSignal()

        def listen(self, name):
            return False

        @staticmethod
        def removeServer(name):
            return True

    class _FakeSignal:
        def connect(self, slot):
            pass

    monkeypatch.setattr("py_crow_tool.services.desktop.QLocalServer", AlwaysFailsToListen)

    class AlwaysFailsToConnect:
        def __init__(self, parent=None):
            pass

        def connectToServer(self, name):
            pass

        def waitForConnected(self, timeout):
            return False

    monkeypatch.setattr("py_crow_tool.services.desktop.QLocalSocket", AlwaysFailsToConnect)

    instance = SingleInstance("py-crow-test-fallback")

    assert instance.is_primary is True
    assert "multiple instances" in capsys.readouterr().err
