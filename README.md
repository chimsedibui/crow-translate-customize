# Crow Tool: Python Version

The Python version is a native desktop translation application built with Python 3.11, PySide 6, and QML. It uses official Google Cloud Translation APIs and separates translation providers, desktop services, settings, and UI view models so the application can be extended in Python.

This implementation is newer than the C++ version. It provides the core GUI and CLI translation workflows, history, clipboard OCR, TTS integration, tray actions, global-shortcut adapters, and provider plugins. The C++ version remains the reference when full legacy desktop behavior is required.

## Features

- Google Cloud Translation Advanced v3 with OAuth/ADC or service-account credentials.
- Google Cloud Translation Basic v2 with API-key authentication.
- Automatic provider selection: configured v3 first, then v2.
- QML desktop interface with language selection, history, settings, OCR input, and speech controls.
- CLI translation, language detection, file/stdin input, OCR, and JSON output.
- Versioned TOML settings in the current user's application-data directory.
- Python translation-provider plugins through package entry points.
- Windows adapters for startup, global shortcuts, tray behavior, and single-instance handling.

## Requirements

- Python 3.11 or newer.
- Tesseract OCR for image recognition.
- Google Cloud credentials for translation.
- Windows optional dependencies for full shortcut and native integration support.

## Development setup

### Linux or macOS

```bash
cd py_crow_tool
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[test]'
pytest
py-crow-gui
```

### Windows PowerShell

```powershell
Set-Location py_crow_tool
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[windows,test]"
pytest
py-crow-gui
```

If PowerShell blocks activation, run the virtual-environment executables directly, for example `.\.venv\Scripts\py-crow-gui.exe`.

## Configure Google Cloud

### Advanced v3

Set a project and use Application Default Credentials:

```powershell
$env:GOOGLE_CLOUD_PROJECT = "your-project-id"
$env:GOOGLE_APPLICATION_CREDENTIALS = "C:\secure\service-account.json"
py-crow-gui
```

You can also enter the project, location, and credential-file path in Settings. The default location is `global`.

### Basic v2

Set an API key:

```powershell
$env:PY_CROW_GOOGLE_API_KEY = "your-api-key"
py-crow-gui
```

Alternatively, enter the key in Settings. When v3 and v2 are both configured, v3 is selected. The application does not retry a failed billable v3 request through v2; v2 is used only when v3 is unavailable or explicitly selected.

Settings can contain plaintext API keys and credential paths. Keep the settings file private and never commit credentials.

## CLI

```bash
py-crow -s vi -t en "Xin chao"
py-crow --stdin -t fr --json
py-crow --file input.txt -t de
py-crow --detect "bonjour"
py-crow --ocr screenshot.png -t en
py-crow --provider google-v2 -t en "Hola"
```

| Option | Description |
|---|---|
| `-s, --source` | Source language code; defaults to `auto`. |
| `-t, --target` | Target language code; defaults to `en`. |
| `-p, --provider` | Force `google-v3` or `google-v2`. |
| `--file` | Read UTF-8 source text from a file. |
| `--stdin` | Read source text from standard input. |
| `--ocr` | Recognize source text from an image. |
| `--detect` | Detect the language without translating. |
| `--json` | Print structured JSON. |

Run `py-crow --help` for the current interface.

## Project layout

| Path | Purpose |
|---|---|
| `src/py_crow_tool/core/` | Typed requests, results, language data, and provider protocol. |
| `src/py_crow_tool/providers/` | Google v2/v3 providers and provider manager. |
| `src/py_crow_tool/services/` | History, OCR, TTS, and desktop adapters. |
| `src/py_crow_tool/qml/` | QML application interface. |
| `src/py_crow_tool/viewmodels.py` | QML-facing application state. |
| `src/py_crow_tool/cli.py` | Command-line entry point. |
| `tests/` | Unit and mocked provider tests. |

## Provider plugins

Plugins are trusted Python packages registered in the `py_crow_tool.providers` entry-point group. A plugin exposes `ProviderPlugin` metadata and a factory implementing the `TranslationProvider` protocol. Users must explicitly list plugin IDs in `enabled_plugins` before they are loaded.

Plugins execute with the same permissions as the application. Install only trusted plugins.

## Testing

```bash
python -m pip install -e '.[test]'
pytest
python -m compileall -q src tests
```

Google tests use mocked HTTP transports. Live credential tests should be opt-in and use a dedicated test project with strict quotas.

## Windows packaging

The included PowerShell script creates a PyInstaller executable:

```powershell
.\scripts\build-windows.ps1
```

See [WINDOWS_DEPLOY.md](WINDOWS_DEPLOY.md) for prerequisites, packaging, clean-machine testing, and signing.

## Known limitations

- Tesseract must be installed separately unless a future package bundles it.
- Windows integration must be validated on Windows; Linux smoke tests cannot verify shortcuts, startup registration, or the system tray implementation.
- Pixel-selected screen capture and all legacy C++ workflows are not yet at full parity.
- Credentials entered in Settings are not stored in Windows Credential Manager.

## License

The project is licensed under GPL-3.0-or-later.

