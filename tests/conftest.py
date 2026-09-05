import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


import pytest


@pytest.fixture(scope="session", autouse=True)
def release_clipboard_before_qt_shutdown(qapp):
    """The offscreen clipboard must release its MIME object before Qt teardown."""
    yield
    qapp.clipboard().clear()
    qapp.processEvents()
