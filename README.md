# Crow Tool: Python Version

The Python version is a native desktop translation application built with Python 3.11, PySide 6, and QML. It uses the official Google Cloud Translation API and separates translation providers, desktop services, settings, and UI view models so the application can be extended in Python.

This implementation is newer than the C++ version. It provides the core GUI and CLI translation workflows, history, clipboard OCR, TTS integration, background/tray operation, global hotkeys, and provider plugins. The C++ version remains the reference when full legacy desktop behavior is required.

## Features

- Google Cloud Translation Basic v2 with API-key authentication.
- QML desktop interface with language selection, history, settings, OCR input, and speech controls.
- Runs like a normal background app: system tray icon, single-instance enforcement, and an optional "start with system" setting.
- Global hotkeys: translate the current clipboard, or select text anywhere and pop up a translation near the cursor.
- CLI translation, language detection, file/stdin input, OCR, and JSON output.
- Versioned TOML settings in the current user's application-data directory.
- Python translation-provider plugins through package entry points.

## Requirements

- Python 3.11 or newer.
- Tesseract OCR for image recognition.
- A Google Cloud Translation API key.
- Windows optional dependencies (the `windows` extra) for global hotkeys.

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

Set an API key:

```powershell
$env:PY_CROW_GOOGLE_API_KEY = "your-api-key"
py-crow-gui
```

Alternatively, enter the key in Settings.

Settings can contain a plaintext API key. Keep the settings file private and never commit credentials.

## Background operation and global hotkeys

The GUI keeps running in the system tray after its window is closed (`Show`, `Translate clipboard`, and `Quit` are available from the tray menu). Enable **Start with system** in Settings to launch it automatically at login.

Two global hotkeys are configurable in Settings:

- **Clipboard hotkey** (default `ctrl+alt+t`): translates whatever is currently on the clipboard and shows the main window.
- **Quick-translate hotkey** (default `ctrl+alt+q`): copies the current text selection (by simulating Ctrl+C) and shows a small popup with the translation near the cursor, without switching focus to the main window.

Hotkey changes take effect after restarting the app.

Global hotkeys depend on the optional `keyboard` package (installed via the `windows` extra) and have real platform constraints:

- **WSL2 cannot run this feature at all**, even with `keyboard` installed: WSL2 has no access to the physical keyboard's raw input devices, so hotkeys silently never fire. Test hotkeys on native Windows (or native Linux with the permissions below), not inside WSL.
- On native Linux, `keyboard` needs permission to read `/dev/input` (typically root, or a user in the `input` group).
- On native Windows, if a hotkey still doesn't fire after confirming `keyboard` is installed: try running the app as Administrator (some elevated foreground windows block hooks from non-elevated processes), and check Windows Security's protection history — an unsigned PyInstaller build can be flagged for installing a low-level keyboard hook.
- If registration fails, the app logs the reason to stderr (visible when `pycrow.spec` is built with `console=True`, the default) and shows a tray notification.

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
| `-p, --provider` | Force `google-v2`, or a plugin's provider id. |
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
| `src/py_crow_tool/providers/` | Google v2 provider and provider manager. |
| `src/py_crow_tool/services/` | History, OCR, TTS, desktop (hotkeys/tray/startup), and the shared async loop runner. |
| `src/py_crow_tool/qml/` | QML application interface (main window and the quick-translate popup). |
| `src/py_crow_tool/viewmodels.py` | QML-facing application state. |
| `src/py_crow_tool/cli.py` | Command-line entry point. |
| `tests/` | Unit, mocked-provider, and threading/async tests. |

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

## Windows packaging and deployment

This section packages `py_crow_tool` as `PyCrowTool.exe` with Python 3.11, PySide 6, QML, and PyInstaller.

### 1. Requirements

Install on 64-bit Windows 10 or Windows 11:

- Python 3.11 from python.org, including the `py` launcher;
- Git for Windows;
- Tesseract OCR when OCR is required;
- Microsoft Visual C++ Redistributable;
- Windows SDK `signtool` when signing releases.

Verify the tools in PowerShell:

```powershell
py -3.11 --version
git --version
tesseract --version
```

### 2. Prepare the source

```powershell
Set-Location C:\src\crow-tool\py_crow_tool
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[windows,test,build]"
```

Do not package from a virtual environment containing unrelated application dependencies. This step is also what determines whether global hotkeys work in the built executable — skipping the `windows` extra here means `keyboard` never gets bundled, and hotkeys will silently do nothing.

### 3. Test before packaging

```powershell
.\.venv\Scripts\pytest.exe
.\.venv\Scripts\python.exe -m compileall -q src tests
.\.venv\Scripts\py-crow.exe --help
.\.venv\Scripts\py-crow-gui.exe
```

Configure test credentials only through environment variables or a local user settings file. Do not place them in the source tree.

### 4. Build the executable

Use the repository script:

```powershell
.\scripts\build-windows.ps1
```

The script creates `.venv` when necessary, installs the `windows` and `build` extras, and invokes PyInstaller with `pycrow.spec`.

The expected artifact is:

```text
dist/PyCrowTool.exe
```

To rebuild from a clean PyInstaller output directory:

```powershell
Remove-Item -Recurse -Force .\build, .\dist -ErrorAction SilentlyContinue
.\scripts\build-windows.ps1
```

### 5. Tesseract deployment

The current PyInstaller specification does not bundle Tesseract. Choose one deployment policy:

1. Require users to install Tesseract and add it to `PATH`.
2. Install Tesseract beside the application and configure its executable path in PyCrow settings.

Document the selected policy in release notes. Verify the OCR language data needed by your users is installed.

### 6. Configure Google Cloud

Do not embed API keys in `PyCrowTool.exe`.

For managed deployments, configure the API key per user or machine:

```powershell
[Environment]::SetEnvironmentVariable("PY_CROW_GOOGLE_API_KEY", "your-api-key", "User")
```

Environment variables avoid packaging secrets but are not a general-purpose secret vault. Restrict the Google API key to the minimum required permissions and quotas.

### 7. Verify on a clean machine

Test `dist/PyCrowTool.exe` on a clean Windows VM that does not have the development virtual environment.

Release checklist:

- [ ] The GUI opens without a Python, Qt, or missing-DLL error.
- [ ] QML controls and dialogs render correctly at common display scales.
- [ ] Google v2 works with an API key.
- [ ] Translation errors do not expose credentials.
- [ ] CLI behavior is tested separately from the GUI artifact when a CLI package is distributed.
- [ ] Clipboard OCR works with the documented Tesseract installation.
- [ ] TTS, tray actions, global hotkeys, and single-instance behavior work.
- [ ] The application starts without network access and shows a useful configuration state.

### 8. Sign the release

Sign the executable with an organization-owned certificate:

```powershell
signtool sign /a /fd SHA256 /td SHA256 `
  /tr http://timestamp.digicert.com `
  .\dist\PyCrowTool.exe
```

Verify it:

```powershell
Get-AuthenticodeSignature .\dist\PyCrowTool.exe
```

Keep certificates and passwords outside the repository and CI logs.

### 9. Publish

Generate a checksum:

```powershell
Get-FileHash .\dist\PyCrowTool.exe -Algorithm SHA256
```

Publish the signed executable with:

- the SHA-256 checksum;
- supported Windows versions;
- Tesseract installation instructions;
- Google credential instructions;
- known limitations and upgrade notes.

### Windows packaging troubleshooting

**PowerShell blocks virtual-environment activation** — Activation is optional. Invoke `.venv\Scripts\python.exe`, `pytest.exe`, and `pyinstaller.exe` directly as shown above.

**PyInstaller cannot find QML files** — Build through `pycrow.spec`. It uses `collect_data_files("py_crow_tool")` and the wheel configuration includes `src/py_crow_tool/qml`.

**OCR reports that Tesseract is missing** — Install Tesseract, add it to `PATH`, or configure the full executable path in application settings.

**Windows blocks the executable** — Sign the release and distribute it from a trusted HTTPS location. New certificates may still build reputation gradually with Microsoft SmartScreen.

**Global hotkeys don't fire** — See "Background operation and global hotkeys" above: confirm the `windows` extra was installed before packaging, rule out WSL2, and try running as Administrator.

## Known limitations

- Tesseract must be installed separately unless a future package bundles it.
- Windows integration must be validated on Windows; Linux smoke tests cannot verify global hotkeys, startup registration, or the system tray implementation.
- Pixel-selected screen capture and all legacy C++ workflows are not yet at full parity.
- Credentials entered in Settings are not stored in Windows Credential Manager.

## License

The project is licensed under GPL-3.0-or-later.
