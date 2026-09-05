$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Venv = Join-Path $ProjectRoot ".venv"

if (-not (Test-Path $Venv)) {
    py -3.11 -m venv $Venv
    if ($LASTEXITCODE -ne 0) { throw "Virtual environment creation failed." }
}

& "$Venv\Scripts\python.exe" -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw "pip upgrade failed." }
& "$Venv\Scripts\python.exe" -m pip install -e "$ProjectRoot[windows,build]"
if ($LASTEXITCODE -ne 0) { throw "Dependency installation failed." }
$PythonBase = & "$Venv\Scripts\python.exe" -c "import sys; print(sys.base_prefix)"
if ($LASTEXITCODE -ne 0) { throw "Could not locate the Python runtime." }
$BuildOriginalPath = $env:PATH
Push-Location $ProjectRoot
try {
    # DLL discovery must not pick up unrelated ICU/Qt libraries from tools such
    # as Poppler on the caller's PATH. Qt uses the Windows ICU system library.
    $env:PATH = "$Venv\Scripts;$PythonBase;$env:SystemRoot\System32;$env:SystemRoot"
    & "$Venv\Scripts\pyinstaller.exe" --clean --noconfirm pycrow.spec
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller build failed." }
} finally {
    $env:PATH = $BuildOriginalPath
    Pop-Location
}
