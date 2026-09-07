from __future__ import annotations

import os
import sys
import ctypes
from ctypes import wintypes
from itertools import count
from pathlib import Path

from PySide6.QtCore import QAbstractNativeEventFilter, QCoreApplication, QObject, Signal, Qt
from PySide6.QtGui import QKeySequence
from PySide6.QtNetwork import QLocalServer, QLocalSocket


class SingleInstance(QObject):
    activated = Signal()

    def __init__(self, name: str, parent: QObject | None = None):
        super().__init__(parent)
        self._server = QLocalServer(self)
        self._server.newConnection.connect(self.activated)
        # Windows allows multiple listeners for one named pipe. Probe the
        # existing instance before listening so a second launch activates it.
        probe = QLocalSocket(self)
        probe.connectToServer(name)
        if probe.waitForConnected(300):
            probe.disconnectFromServer()
            self.is_primary = False
            return
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


class _WindowsHotkeyFilter(QAbstractNativeEventFilter):
    def __init__(self, callback):
        super().__init__()
        self.callback = callback

    def nativeEventFilter(self, event_type, message):
        msg = wintypes.MSG.from_address(int(message))
        if msg.message == 0x0312:  # WM_HOTKEY
            return self.callback(int(msg.wParam)), 0
        return False, 0


_hotkey_ids = count(1)


def _windows_hotkey(sequence: str) -> tuple[int, int]:
    parsed = QKeySequence.fromString(sequence, QKeySequence.SequenceFormat.PortableText)
    if parsed.count() != 1:
        raise ValueError("Use one key combination")
    combination = parsed[0]
    key = combination.key().value
    qt_mods = combination.keyboardModifiers()
    mods = 0x4000  # MOD_NOREPEAT
    for qt_mod, native_mod in ((Qt.ControlModifier, 2), (Qt.AltModifier, 1), (Qt.ShiftModifier, 4), (Qt.MetaModifier, 8)):
        if qt_mods & qt_mod:
            mods |= native_mod
    named = {Qt.Key_Space: 0x20, Qt.Key_Tab: 9, Qt.Key_Return: 13, Qt.Key_Escape: 27,
             Qt.Key_Backspace: 8, Qt.Key_Insert: 0x2D, Qt.Key_Delete: 0x2E,
             Qt.Key_Home: 0x24, Qt.Key_End: 0x23, Qt.Key_Left: 0x25, Qt.Key_Up: 0x26,
             Qt.Key_Right: 0x27, Qt.Key_Down: 0x28, Qt.Key_PageUp: 0x21, Qt.Key_PageDown: 0x22}
    if ord('A') <= key <= ord('Z') or ord('0') <= key <= ord('9'):
        return mods, key
    if Qt.Key_F1 <= key <= Qt.Key_F24:
        return mods, 0x70 + key - Qt.Key_F1.value
    if key in named:
        return mods, named[key]
    raise ValueError("Unsupported hotkey key")


class DesktopServices(QObject):
    shortcutTriggered = Signal(str)

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._shortcuts: list[object] = []
        self.selection_capture_pending = False
        self._native_actions: dict[int, str] = {}
        self._native_filter = None

    def set_startup_enabled(self, enabled: bool) -> None:
        if sys.platform != "win32":
            return
        import winreg

        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
            if enabled:
                if getattr(sys, "frozen", False):
                    command = f'"{sys.executable}"'
                else:
                    command = f'"{sys.executable}" -m py_crow_tool.app'
                winreg.SetValueEx(key, "PyCrowTool", 0, winreg.REG_SZ, command)
            else:
                try:
                    winreg.DeleteValue(key, "PyCrowTool")
                except FileNotFoundError:
                    pass

    def register_shortcut(self, sequence: str, action: str) -> bool:
        try:
            if sys.platform == "win32":
                app = QCoreApplication.instance()
                if app is None:
                    raise RuntimeError("Hotkeys require a running Qt application")
                modifiers, key = _windows_hotkey(sequence)
                if self._native_filter is None:
                    self._native_filter = _WindowsHotkeyFilter(self._on_native_hotkey)
                    app.installNativeEventFilter(self._native_filter)
                    app.aboutToQuit.connect(self.unregister_shortcuts)
                hotkey_id = next(_hotkey_ids)
                user32 = ctypes.WinDLL("user32", use_last_error=True)
                if not user32.RegisterHotKey(None, hotkey_id, modifiers, key):
                    raise ctypes.WinError(ctypes.get_last_error())
                self._native_actions[hotkey_id] = action
                return True
            import keyboard

            handle = keyboard.add_hotkey(sequence, lambda: self.shortcutTriggered.emit(action), trigger_on_release=True)
            self._shortcuts.append(handle)
            return True
        except (ImportError, OSError, RuntimeError, ValueError) as error:
            sys.stderr.write(f"Global hotkey '{sequence}' unavailable: {type(error).__name__}: {error}\n")
            return False

    def _on_native_hotkey(self, hotkey_id: int) -> bool:
        action = self._native_actions.get(hotkey_id)
        if action is None:
            return False
        self.shortcutTriggered.emit(action)
        return True

    def unregister_shortcuts(self) -> None:
        if self._native_filter is not None:
            for hotkey_id in self._native_actions:
                ctypes.windll.user32.UnregisterHotKey(None, hotkey_id)
            self._native_actions.clear()
            QCoreApplication.instance().removeNativeEventFilter(self._native_filter)
            self._native_filter = None
        if self._shortcuts:
            import keyboard
            for handle in self._shortcuts:
                keyboard.remove_hotkey(handle)
            self._shortcuts.clear()

    @staticmethod
    def copy_modifiers_released() -> bool:
        if sys.platform == "win32":
            import ctypes

            # Read physical state instead of the keyboard hook's cached state:
            # injected events and hook processing can leave that cache behind.
            return not any(
                ctypes.windll.user32.GetAsyncKeyState(key) & 0x8000
                for key in (0x10, 0x11, 0x12, 0x5B, 0x5C)
            )
        try:
            import keyboard

            return not any(keyboard.is_pressed(key) for key in ("ctrl", "alt", "shift", "windows"))
        except (ImportError, OSError, RuntimeError):
            return True  # simulate_copy reports missing keyboard support.

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
