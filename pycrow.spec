# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files

datas = collect_data_files("py_crow_tool")

a = Analysis(
    ["src/py_crow_tool/app.py"],
    pathex=["src"],
    binaries=[],
    datas=datas,
    hiddenimports=["PySide6.QtMultimedia"],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

# PySide6's QtQml hook (collect_qtqml_files) bundles every QML plugin it finds under Qt's
# QML import path, regardless of whether the app imports it. Our QML only uses QtQml,
# QtQml.Models, QtQuick, QtQuick.Controls (FluentWinUI3 style), QtQuick.Effects (MultiEffect,
# for the drop shadows), QtQuick.Layouts and QtQuick.Window, so this strips whole unrelated Qt
# feature areas (WebEngine/Chromium alone is ~83 MB) that would otherwise roughly triple
# the built executable for no functional benefit.
#
# Qt Multimedia itself stays: read-aloud plays Google's MP3 through QMediaPlayer, which
# needs Qt6Multimedia, the plugins/multimedia backends and the FFmpeg libraries they
# decode with. Only its QML module and the Quick/Widgets bindings are stripped.
_UNUSED_QT_QML_DIRS = (
    "PySide6\\qml\\QtWebEngine",
    "PySide6\\qml\\Qt3D",
    "PySide6\\qml\\QtQuick3D",
    "PySide6\\qml\\QtCharts",
    "PySide6\\qml\\QtDataVisualization",
    "PySide6\\qml\\QtGraphs",
    "PySide6\\qml\\QtLocation",
    "PySide6\\qml\\QtPositioning",
    "PySide6\\qml\\QtMultimedia",
    "PySide6\\qml\\QtQuick\\Pdf",
    "PySide6\\qml\\QtQuick\\VirtualKeyboard",
    "PySide6\\plugins\\platforminputcontexts",
)
_UNUSED_QT_BINARY_PREFIXES = (
    "PySide6\\Qt63D",
    "PySide6\\Qt6Quick3D",
    "PySide6\\Qt6Charts",
    "PySide6\\Qt6DataVisualization",
    "PySide6\\Qt6Graphs",
    "PySide6\\Qt6Location",
    "PySide6\\Qt6Positioning",
    "PySide6\\Qt6MultimediaQuick",
    "PySide6\\Qt6MultimediaWidgets",
    "PySide6\\Qt6Pdf",
    "PySide6\\Qt6VirtualKeyboard",
    "PySide6\\Qt6WebEngine",
    "PySide6\\Qt6ShaderTools",
    "PySide6\\QtMultimediaWidgets",
)


def _is_unused_qt_entry(dest_name: str) -> bool:
    normalized = dest_name.replace("/", "\\")
    return normalized.startswith(_UNUSED_QT_QML_DIRS) or normalized.startswith(_UNUSED_QT_BINARY_PREFIXES)


a.binaries = [entry for entry in a.binaries if not _is_unused_qt_entry(entry[0])]
a.datas = [entry for entry in a.datas if not _is_unused_qt_entry(entry[0])]

pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="PyCrowTool",
    icon="src/py_crow_tool/qml/app-icon.png",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
)

