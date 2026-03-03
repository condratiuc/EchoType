; Inno Setup script for EchoType
; Download Inno Setup from https://jrsoftware.org/isinfo.php

[Setup]
AppName=EchoType
AppVersion=1.0.0
AppPublisher=Personal
DefaultDirName={autopf}\EchoType
DefaultGroupName=EchoType
UninstallDisplayIcon={app}\EchoType.exe
OutputDir=installer_output
OutputBaseFilename=EchoType_Setup
Compression=lzma2
SolidCompression=yes
SetupIconFile=icon.ico
PrivilegesRequired=lowest

[Files]
Source: "dist\EchoType.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "icon.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\EchoType"; Filename: "{app}\EchoType.exe"
Name: "{group}\Uninstall EchoType"; Filename: "{uninstallexe}"
Name: "{autodesktop}\EchoType"; Filename: "{app}\EchoType.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional icons:"
Name: "startup"; Description: "Start EchoType with Windows"; GroupDescription: "Startup:"

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "EchoType"; ValueData: """{app}\EchoType.exe"""; Flags: uninsdeletevalue; Tasks: startup

[Run]
Filename: "{app}\EchoType.exe"; Description: "Launch EchoType"; Flags: nowait postinstall skipifsilent
