import builtins

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
    _block_import(monkeypatch, "keyboard")
    desktop = DesktopServices()

    assert desktop.register_shortcut("ctrl+alt+q", "quick-translate") is False
    assert "unavailable" in capsys.readouterr().err


def test_simulate_copy_returns_false_when_keyboard_module_is_missing(monkeypatch, capsys):
    _block_import(monkeypatch, "keyboard")

    assert DesktopServices.simulate_copy() is False
    assert "Could not simulate" in capsys.readouterr().err


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
