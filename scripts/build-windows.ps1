$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Venv = Join-Path $ProjectRoot ".venv"

if (-not (Test-Path $Venv)) {
    py -3.11 -m venv $Venv
}

& "$Venv\Scripts\python.exe" -m pip install --upgrade pip
& "$Venv\Scripts\python.exe" -m pip install -e "$ProjectRoot[windows,build]"
Push-Location $ProjectRoot
try {
    & "$Venv\Scripts\pyinstaller.exe" --clean --noconfirm pycrow.spec
} finally {
    Pop-Location
}

