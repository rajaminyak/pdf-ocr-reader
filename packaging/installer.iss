; Inno Setup script for PDF OCR Reader.
;
; Build (after the PyInstaller build has populated dist\PdfOcrReader\):
;   "C:\Users\Ridho\AppData\Local\Programs\Inno Setup 6\ISCC.exe" packaging\installer.iss
;
; Output: packaging\output\PdfOcrReader-Setup.exe

#define MyAppName "PDF OCR Reader"
#define MyAppVersion "0.1.0"
#define MyAppPublisher "RU VI Balongan - Process Engineering"
#define MyAppExeName "PdfOcrReader.exe"

[Setup]
AppId={{9F3C1D74-6B2E-4A55-9C10-PDFOCRREADER01}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
; Per-user install under the user's own AppData -- no admin rights needed.
DefaultDirName={localappdata}\Programs\{#MyAppName}
PrivilegesRequired=lowest
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=output
OutputBaseFilename=PdfOcrReader-Setup
SetupIconFile=app.ico
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional shortcuts:"

[Files]
Source: "..\dist\PdfOcrReader\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "README-first-run.id.txt"; DestDir: "{app}"; Flags: ignoreversion isreadme
Source: "README-first-run.txt"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName} now"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Leave the user's config and OCR cache (%LOCALAPPDATA%\PdfOcrReader) alone --
; only the installed program files are removed on uninstall.
