; =====================================================================
; MediGen AI Pro - Windows installer (Inno Setup 6)
;
; Step 1: run build_exe.bat (creates dist\MediGenAIPro\MediGenAIPro.exe)
; Step 2: open this file in "Inno Setup Compiler" and press Compile
;         (free from jrsoftware.org), or run:  iscc installer\MediGen.iss
; Output: dist\MediGen_Setup_<version>.exe  (one file to copy to any PC)
;
; The installer does NOT need Python on the target PC (the program is built
; as MediGenAIPro.exe). It still needs MySQL 8.0 on that PC - see BUILD_APPS.md.
; .env, backups and profile pictures are never overwritten by an update.
; NOT code-signed: Windows SmartScreen may warn the first time.
; =====================================================================
#define AppName "MediGen AI Pro"
#define AppVersion "101.03"
#define AppExe "MediGenAIPro.exe"

[Setup]
AppId={{B7C2E4A1-3F5D-4E8A-9C21-5A7D0E61F001}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=MediGen
DefaultDirName={localappdata}\MediGen AI Pro
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
OutputDir=..\dist
OutputBaseFilename=MediGen_Setup_{#AppVersion}
SetupIconFile=..\assets\medigen.ico
UninstallDisplayIcon={app}\{#AppExe}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
UninstallDisplayName={#AppName}

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"; Flags: checkedonce

[Files]
; The built program folder (exe, templates, static, and the bundled mysql folder if it was there).
; Installed per user (no admin needed) so the app can write backups and its database files.
Source: "..\dist\MediGenAIPro\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion; Excludes: ".env,backups\*,static\profiles\*,mysql-data\*,mysql-server.log,mysql\mysql-test\*,mysql\docs\*,mysql\include\*,mysql\lib\debug\*,mysql\lib\plugin\debug\*,*.pdb,*.lib"
; First install only: a default .env. An existing .env is never replaced.
Source: "..\dist\MediGenAIPro\.env"; DestDir: "{app}"; Flags: onlyifdoesntexist uninsneveruninstall

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExe}"; WorkingDir: "{app}"; IconFilename: "{app}\{#AppExe}"
Name: "{group}\Uninstall {#AppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; WorkingDir: "{app}"; IconFilename: "{app}\{#AppExe}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExe}"; Description: "Open {#AppName} now"; WorkingDir: "{app}"; Flags: nowait postinstall skipifsilent
