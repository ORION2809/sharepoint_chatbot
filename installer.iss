; SharePoint Chatbot — Inno Setup Installer Script
; Generates a professional Windows installer (.exe)
;
; Prerequisites:
;   1. Install Inno Setup 6+ from https://jrsoftware.org/isinfo.php
;   2. Run build_installer.py --folder first to create the staging folder
;      OR point SourceDir below to the project root
;   3. Compile this script with Inno Setup Compiler
;
; The resulting installer will:
;   - Install files to C:\SharePointChatbot (configurable)
;   - Create Start Menu and Desktop shortcuts
;   - Check for Python and offer to install it
;   - Run the setup wizard on first launch
;   - Register an uninstaller

#define MyAppName "SharePoint Chatbot"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Your Company"
#define MyAppURL "https://yourcompany.sharepoint.com"
#define MyAppExeName "start.bat"
#define MyAppSetupExe "install.bat"

[Setup]
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
DefaultDirName={autopf}\SharePointChatbot
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
; Output settings — change OutputDir to your release folder
OutputDir=dist
OutputBaseFilename=SharePointChatbot_Setup_{#MyAppVersion}
; Compression
Compression=lzma2/ultra64
SolidCompression=yes
; UI
WizardStyle=modern
SetupIconFile=
; Privileges — per-user install (no admin needed)
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
; Misc
Uninstallable=yes
UninstallDisplayName={#MyAppName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: checked
Name: "startmenu"; Description: "Create Start Menu shortcut"; GroupDescription: "{cm:AdditionalIcons}"; Flags: checked

[Files]
; Core application files
Source: "main.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "sharepoint_client.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "vector_store.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "llm_client.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "vision_client.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "chunker.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "config.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "login.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "setup_wizard.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "requirements.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "install.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "start.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "uninstall.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: ".env.example"; DestDir: "{app}"; Flags: ignoreversion
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion

; Pre-filled .env (if IT admin built with --prefill)
Source: ".env"; DestDir: "{app}"; Flags: ignoreversion onlyifdoesntexist

; Templates
Source: "templates\*"; DestDir: "{app}\templates"; Flags: ignoreversion recursesubdirs

[Icons]
; Start Menu
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: startmenu
Name: "{group}\Setup Wizard"; Filename: "python"; Parameters: """{app}\setup_wizard.py"""; WorkingDir: "{app}"; Tasks: startmenu
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"; Tasks: startmenu

; Desktop
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
; Post-install: run the setup wizard (installs deps, configures, signs in)
Filename: "python"; Parameters: """{app}\setup_wizard.py"""; WorkingDir: "{app}"; \
  Description: "Run Setup Wizard (install dependencies & sign in)"; Flags: postinstall nowait skipifsilent

[UninstallDelete]
; Clean up generated files on uninstall
Type: filesandordirs; Name: "{app}\venv"
Type: filesandordirs; Name: "{app}\.chroma_db"
Type: filesandordirs; Name: "{app}\__pycache__"
Type: files; Name: "{app}\.token_cache.json"
Type: files; Name: "{app}\.index_meta.json"
Type: files; Name: "{app}\.env"

[Code]
// Pascal Script to check for Python at install time
function IsPythonInstalled(): Boolean;
var
  ResultCode: Integer;
begin
  Result := Exec('python', '--version', '', SW_HIDE, ewWaitUntilTerminated, ResultCode)
           and (ResultCode = 0);
end;

function InitializeSetup(): Boolean;
begin
  Result := True;
  if not IsPythonInstalled() then
  begin
    if MsgBox(
      'Python is not installed or not in PATH.'#13#10#13#10 +
      'The SharePoint Chatbot requires Python 3.10 or later.'#13#10 +
      'Download it from https://www.python.org/downloads/'#13#10#13#10 +
      'Make sure to check "Add Python to PATH" during installation.'#13#10#13#10 +
      'Click OK to open the download page, then re-run this installer.',
      mbInformation,
      MB_OKCANCEL
    ) = IDOK then
    begin
      // Open Python download page
      ShellExec('open', 'https://www.python.org/downloads/', '', '', SW_SHOWNORMAL, ewNoWait, ResultCode);
    end;
    Result := False;  // Cancel installation
  end;
end;

var
  ResultCode: Integer;
