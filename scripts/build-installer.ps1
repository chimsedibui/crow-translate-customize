$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot

& (Join-Path $PSScriptRoot "build-windows.ps1")
if ($LASTEXITCODE -ne 0) { throw "App build failed." }

$Iscc = Get-Command "ISCC.exe" -ErrorAction SilentlyContinue
if (-not $Iscc) {
    $Candidates = @(
        "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe",
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
        "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
    )
    $Found = $Candidates | Where-Object { Test-Path $_ } | Select-Object -First 1
    if (-not $Found) { throw "ISCC.exe (Inno Setup) not found. Install it first: winget install JRSoftware.InnoSetup" }
    $Iscc = $Found
} else {
    $Iscc = $Iscc.Source
}

& $Iscc (Join-Path $ProjectRoot "installer\PyCrowTool.iss")
if ($LASTEXITCODE -ne 0) { throw "Installer build failed." }

Write-Host "Installer ready in installer\Output\"
