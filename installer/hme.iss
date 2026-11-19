#define AppName "HME"
#define AppVersion "1.0.0"

[Setup]
AppId={{A77D2938-FC32-44A5-A01E-91B37C764A80}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=HME
DefaultDirName={localappdata}\Programs\HME
DefaultGroupName=HME
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\dist
OutputBaseFilename=HME-Setup
SetupIconFile=..\assets\hme.ico
UninstallDisplayIcon={app}\hme.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
Uninstallable=yes

[Tasks]
Name: "autostart"; Description: "Start HME when I sign in to Windows"; GroupDescription: "Windows startup:"; Flags: checkedonce
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Files]
Source: "..\dist\hme.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\HME"; Filename: "{app}\hme.exe"
Name: "{autoprograms}\Edit HME cookies"; Filename: "{app}\hme.exe"; Parameters: "--setup"
Name: "{userstartup}\HME"; Filename: "{app}\hme.exe"; Tasks: autostart
Name: "{autodesktop}\HME"; Filename: "{app}\hme.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\hme.exe"; Description: "Launch HME"; Flags: postinstall nowait skipifsilent

[Code]
procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
    if not WizardIsTaskSelected('autostart') then
      DeleteFile(ExpandConstant('{userstartup}\HME.lnk'));
end;
