#define AppName "FitCV Local Technical Preview"
#define AppVersion "0.1.0"
#define AppExeName "fitcv-local.exe"

[Setup]
AppId={{A20D988D-88F4-41F5-B7F0-D180E4919B1F}
AppName={#AppName}
AppVersion={#AppVersion}
DefaultDirName={localappdata}\Programs\FitCV Local
DefaultGroupName=FitCV Local
PrivilegesRequired=lowest
OutputDir=..\..\dist\installer
OutputBaseFilename=FitCV-Local-{#AppVersion}-Technical-Preview-Setup
Compression=lzma2
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
WizardStyle=modern

[Files]
Source: "..\..\dist\fitcv-local\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Icons]
Name: "{group}\FitCV Local"; Filename: "{app}\{#AppExeName}"
Name: "{group}\Change Log"; Filename: "{app}\{#AppExeName}"; Parameters: "--change-log"
Name: "{autodesktop}\FitCV Local"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "Launch FitCV Local"; Flags: nowait postinstall skipifsilent
