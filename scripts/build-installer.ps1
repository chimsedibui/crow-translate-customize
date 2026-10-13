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

# Stamp the installer with the same version the app reports, so "installed version"
# in Windows and the version the updater compares are always one number.
$InitFile = Join-Path $ProjectRoot "src\py_crow_tool\__init__.py"
$VersionMatch = Select-String -Path $InitFile -Pattern '^__version__ = "([^"]+)"'
if (-not $VersionMatch) { throw "Could not read __version__ from $InitFile." }
$Version = $VersionMatch.Matches[0].Groups[1].Value

& $Iscc "/DMyAppVersion=$Version" (Join-Path $ProjectRoot "installer\PyCrowTool.iss")
if ($LASTEXITCODE -ne 0) { throw "Installer build failed." }

# Published next to the installer; the in-app updater refuses a download whose
# hash does not match it.
$Installer = Join-Path $ProjectRoot "installer\Output\PyCrowTool-Setup.exe"
$Hash = (Get-FileHash -Algorithm SHA256 $Installer).Hash.ToLowerInvariant()
Set-Content -Path "$Installer.sha256" -Value "$Hash  PyCrowTool-Setup.exe" -Encoding ascii -NoNewline

Write-Host "Installer $Version ready in installer\Output\"
