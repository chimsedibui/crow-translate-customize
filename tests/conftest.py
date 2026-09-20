import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


import pytest
from PySide6.QtQuickControls2 import QQuickStyle

# Qt only honours the style chosen before the first Qt Quick Controls import, so it
# is picked here rather than per-fixture. It has to match what app.main() sets:
# FluentWinUI3 animates dialogs and centres TextArea content where Basic does
# neither, so testing under Basic would not exercise what actually ships.
QQuickStyle.setStyle("FluentWinUI3")


@pytest.fixture(scope="session", autouse=True)
def release_clipboard_before_qt_shutdown(qapp):
    """The offscreen clipboard must release its MIME object before Qt teardown."""
    yield
    qapp.clipboard().clear()
    qapp.processEvents()
