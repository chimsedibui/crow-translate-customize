# Build and Deploy the Python Version on Windows

This guide packages `py_crow_tool` as `PyCrowTool.exe` with Python 3.11, PySide 6, QML, and PyInstaller.

## 1. Requirements

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

## 2. Prepare the source

```powershell
Set-Location C:\src\crow-tool\py_crow_tool
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[windows,test,build]"
```

Do not package from a virtual environment containing unrelated application dependencies.

## 3. Test before packaging

```powershell
.\.venv\Scripts\pytest.exe
.\.venv\Scripts\python.exe -m compileall -q src tests
.\.venv\Scripts\py-crow.exe --help
.\.venv\Scripts\py-crow-gui.exe
```

Configure test credentials only through environment variables or a local user settings file. Do not place them in the source tree.

## 4. Build the executable

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

## 5. Tesseract deployment

The current PyInstaller specification does not bundle Tesseract. Choose one deployment policy:

1. Require users to install Tesseract and add it to `PATH`.
2. Install Tesseract beside the application and configure its executable path in PyCrow settings.

Document the selected policy in release notes. Verify the OCR language data needed by your users is installed.

## 6. Configure Google Cloud

Do not embed API keys or service-account files in `PyCrowTool.exe`.

For managed v3 deployments, configure these values per user or machine:

```powershell
[Environment]::SetEnvironmentVariable("GOOGLE_CLOUD_PROJECT", "your-project-id", "User")
[Environment]::SetEnvironmentVariable("GOOGLE_APPLICATION_CREDENTIALS", "C:\secure\service-account.json", "User")
```

For Basic v2:

```powershell
[Environment]::SetEnvironmentVariable("PY_CROW_GOOGLE_API_KEY", "your-api-key", "User")
```

Environment variables avoid packaging secrets but are not a general-purpose secret vault. Restrict service-account files and Google API keys to the minimum required permissions and quotas.

## 7. Verify on a clean machine

Test `dist/PyCrowTool.exe` on a clean Windows VM that does not have the development virtual environment.

Release checklist:

- [ ] The GUI opens without a Python, Qt, or missing-DLL error.
- [ ] QML controls and dialogs render correctly at common display scales.
- [ ] Google v3 works with ADC or a service-account file.
- [ ] Google v2 works with an API key.
- [ ] v3 is preferred when both providers are configured.
- [ ] Translation errors do not expose credentials.
- [ ] CLI behavior is tested separately from the GUI artifact when a CLI package is distributed.
- [ ] Clipboard OCR works with the documented Tesseract installation.
- [ ] TTS, tray actions, shortcuts, and single-instance behavior work.
- [ ] The application starts without network access and shows a useful configuration state.

## 8. Sign the release

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

## 9. Publish

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

## Troubleshooting

### PowerShell blocks virtual-environment activation

Activation is optional. Invoke `.venv\Scripts\python.exe`, `pytest.exe`, and `pyinstaller.exe` directly as shown above.

### PyInstaller cannot find QML files

Build through `pycrow.spec`. It uses `collect_data_files("py_crow_tool")` and the wheel configuration includes `src/py_crow_tool/qml`.

### OCR reports that Tesseract is missing

Install Tesseract, add it to `PATH`, or configure the full executable path in application settings.

### Windows blocks the executable

Sign the release and distribute it from a trusted HTTPS location. New certificates may still build reputation gradually with Microsoft SmartScreen.

