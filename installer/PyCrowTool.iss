; Inno Setup script for PyCrow Tool.
; Build the app first (scripts\build-windows.ps1), then compile this script
; with ISCC.exe, or just run scripts\build-installer.ps1 which does both.

#define MyAppName "PyCrow Tool"
; The version comes from src/py_crow_tool/__init__.py, passed in by
; scripts\build-installer.ps1 as /DMyAppVersion=...; compiling this script on its
; own falls back to 0.0.0 rather than to a stale hard-coded number.
#ifndef MyAppVersion
  #define MyAppVersion "0.0.0"
#endif
#define MyAppPublisher "CrowTranslate"
#define MyAppExeName "PyCrowTool.exe"

[Setup]
AppId={{B28D3B49-F4DE-4FE8-BBFA-F2C272A3486B}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
; Per-user install under the current user's own Programs folder: no UAC
; prompt, and matches the "start with system" registry key the app writes
; to HKCU on its own (see src/py_crow_tool/services/desktop.py).
DefaultDirName={localappdata}\Programs\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=Output
OutputBaseFilename=PyCrowTool-Setup
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\{#MyAppExeName}
; Ask Windows to close the running app (it lives in the tray) before
; overwriting its exe, instead of failing with a file-in-use error.
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional icons:"

[Files]
Source: "..\dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent
; An in-app update runs this installer silently, which skips the entry above, and
; passes /RELAUNCH=1 so the app the user was just using comes back on its own.
Filename: "{app}\{#MyAppExeName}"; Flags: nowait; Check: ShouldRelaunch

[Code]
function ShouldRelaunch: Boolean;
begin
  Result := ExpandConstant('{param:RELAUNCH|0}') = '1';
end;

[UninstallRun]
; Belt-and-braces: make sure the tray process is gone before its files are
; removed, even if CloseApplications didn't catch it.
Filename: "{cmd}"; Parameters: "/C taskkill /IM {#MyAppExeName} /F"; Flags: runhidden; RunOnceId: "KillPyCrowTool"
