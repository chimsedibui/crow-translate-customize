from __future__ import annotations

import os
import sys
from pathlib import Path

from PySide6.QtCore import QObject, Signal
from PySide6.QtNetwork import QLocalServer, QLocalSocket


class SingleInstance(QObject):
    activated = Signal()

    def __init__(self, name: str, parent: QObject | None = None):
        super().__init__(parent)
        self._server = QLocalServer(self)
        self._server.newConnection.connect(self.activated)
        self.is_primary = self._server.listen(name)
        if not self.is_primary:
            socket = QLocalSocket(self)
            socket.connectToServer(name)
            if socket.waitForConnected(300):
                socket.disconnectFromServer()
            else:
                QLocalServer.removeServer(name)
                self.is_primary = self._server.listen(name)
                if not self.is_primary:
                    # Sandboxed environments may block local sockets entirely.
                    # Continue without single-instance enforcement in that case,
                    # but make it loud: two instances would fight over the same
                    # global hotkeys and each spin up their own tray icon.
                    sys.stderr.write(
                        f"Warning: could not enforce single-instance lock for '{name}'; "
                        "multiple instances of PyCrow Tool may run and conflict (e.g. duplicate hotkeys/tray icons).\n"
                    )
                    self.is_primary = True


class DesktopServices(QObject):
    shortcutTriggered = Signal(str)

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._shortcuts: list[object] = []

    def set_startup_enabled(self, enabled: bool) -> None:
        if sys.platform != "win32":
            return
        import winreg

        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
            if enabled:
                command = f'"{sys.executable}" -m py_crow_tool.app'
                winreg.SetValueEx(key, "PyCrowTool", 0, winreg.REG_SZ, command)
            else:
                try:
                    winreg.DeleteValue(key, "PyCrowTool")
                except FileNotFoundError:
                    pass

    def register_shortcut(self, sequence: str, action: str) -> bool:
        try:
            import keyboard

            handle = keyboard.add_hotkey(sequence, lambda: self.shortcutTriggered.emit(action))
            self._shortcuts.append(handle)
            return True
        except (ImportError, OSError, RuntimeError) as error:
            sys.stderr.write(f"Global hotkey '{sequence}' unavailable: {type(error).__name__}: {error}\n")
            return False

    @staticmethod
    def simulate_copy() -> bool:
        """Send Ctrl+C so the caller's current text selection lands on the clipboard."""
        try:
            import keyboard

            keyboard.send("ctrl+c")
            return True
        except (ImportError, OSError, RuntimeError) as error:
            sys.stderr.write(f"Could not simulate Ctrl+C: {type(error).__name__}: {error}\n")
            return False

    @staticmethod
    def credential_file_is_private(path: Path) -> bool:
        if os.name == "nt":
            return True
        return path.stat().st_mode & 0o077 == 0
