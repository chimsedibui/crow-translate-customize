# PyCrow Tool

PyCrow Tool is the Python 3.11, PySide 6, and QML rewrite of Crow Translate. It uses the official Google Cloud Translation APIs and keeps desktop integration behind Python services.

## Development

```bash
python3 -m venv .venv
.venv/bin/pip install -e '.[test]'
.venv/bin/pytest
.venv/bin/py-crow-gui
```

Configure Google Cloud from the Settings dialog or edit the user configuration file. Advanced v3 uses `GOOGLE_CLOUD_PROJECT` and Application Default Credentials, or a service-account JSON path. Basic v2 uses `PY_CROW_GOOGLE_API_KEY`. When both are configured, v3 is preferred.

Credentials entered in the GUI are stored in the user settings file. Keep that file private and never commit it.

## CLI

```bash
py-crow -s vi -t en "Xin chao"
py-crow --stdin -t fr --json
py-crow --detect "bonjour"
py-crow --ocr screenshot.png -t en
```

## Windows package

Run `scripts/build-windows.ps1` from PowerShell. The build output is placed in `dist/PyCrowTool.exe`. Install Tesseract separately and configure its executable path when it is not available on `PATH`.

Optional third-party providers are trusted Python packages registered in the `py_crow_tool.providers` entry-point group. Plugins must be explicitly listed in `enabled_plugins` in settings.
