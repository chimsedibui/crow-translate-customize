from PySide6.QtCore import QPoint

from py_crow_tool.app import _popup_position


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
