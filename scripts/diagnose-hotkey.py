"""Interactive, offline test of the real selection/hotkey/popup pipeline.

Run with .venv/Scripts/python.exe -u scripts/diagnose-hotkey.py.
Select the sample text and press Ctrl+Alt+F8. No translation API is called.
"""
import sys
from pathlib import Path
from time import monotonic

from PySide6.QtCore import QTimer, QUrl, Qt
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtWidgets import QApplication, QPlainTextEdit

from py_crow_tool.app import _ShortcutDispatcher, _quick_translate_selection
from py_crow_tool.config import AppSettings, SettingsStore
from py_crow_tool.providers.manager import ProviderManager
from py_crow_tool.services import AsyncLoopRunner, DesktopServices, HistoryStore
from py_crow_tool.viewmodels import TranslationViewModel

app = QApplication(sys.argv)
app.setQuitOnLastWindowClosed(False)
start = monotonic()


def log(message):
    print(f'{monotonic() - start:.3f}s {message}', flush=True)


class ProbeDesktop(DesktopServices):
    def simulate_copy(self):
        log('COPY_SEND')
        return super().simulate_copy()


class ProbeModel(TranslationViewModel):
    def translate(self):
        log(f'TRANSLATE_CALLED sample_match={self.sourceText == sample} popup_visible={popup.isVisible()}')
        self._translated_text = 'PASS: selection captured. No API request sent.'
        self.translatedTextChanged.emit()


class ProbeTray:
    def showMessage(self, title, message, *args):
        log(f'FAIL {message}')


sample = 'PyCrow selection test 12345'
editor = QPlainTextEdit()
editor.setWindowTitle('PyCrow hotkey diagnostic - Ctrl+Alt+F8')
editor.setPlainText(sample)
editor.resize(650, 250)
runner = AsyncLoopRunner()
model = ProbeModel(ProviderManager([]), AppSettings(), SettingsStore(), HistoryStore(), runner)
engine = QQmlApplicationEngine()
engine.rootContext().setContextProperty('quickTranslateModel', model)
engine.load(QUrl.fromLocalFile(str(Path(__file__).resolve().parents[1] / 'src/py_crow_tool/qml/QuickTranslatePopup.qml')))
popup = engine.rootObjects()[0]
desktop = ProbeDesktop()
tray = ProbeTray()


def handle(action):
    log(f'QT_DISPATCH {action}')
    _quick_translate_selection(app, desktop, model, popup, tray)


receiver = _ShortcutDispatcher(handle, app)
desktop.shortcutTriggered.connect(lambda action: log('HOTKEY_SIGNAL'), Qt.ConnectionType.DirectConnection)
desktop.shortcutTriggered.connect(receiver.dispatch, Qt.ConnectionType.QueuedConnection)
log(f'REGISTERED {desktop.register_shortcut("ctrl+alt+f8", "quick-translate")}')
app.clipboard().dataChanged.connect(lambda: log('CLIPBOARD_CHANGED'))
editor.show()
editor.selectAll()
QTimer.singleShot(500, editor.showNormal)
app.aboutToQuit.connect(runner.stop)
QTimer.singleShot(0, lambda: log('EVENT_LOOP_READY'))
sys.exit(app.exec())
