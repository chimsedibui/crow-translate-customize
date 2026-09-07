# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files

datas = collect_data_files("py_crow_tool")

a = Analysis(
    ["src/py_crow_tool/app.py"],
    pathex=["src"],
    binaries=[],
    datas=datas,
    hiddenimports=["PySide6.QtTextToSpeech"],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
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

