; Inno Setup script for Bally AI
; Produces: BallyAI-Setup.exe
; Requires: Inno Setup 6+ from https://jrsoftware.org/isinfo.php
;
; Build steps:
;   1. pyinstaller build.spec          → dist/BallyAI/
;   2. iscc installer.iss              → Output/BallyAI-Setup.exe

#define AppName "Bally AI"
#define AppVersion "1.1.0"
#define AppPublisher "Bally AI"
#define AppURL "https://github.com/jishanahmed-shaikh/bally-ai"
#define AppExeName "BallyAI.exe"
#define DistDir "dist\BallyAI"

[Setup]
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
AllowNoIcons=yes
OutputDir=Output
OutputBaseFilename=BallyAI-Setup
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
UninstallDisplayIcon={app}\{#AppExeName}
MinVersion=10.0
ArchitecturesInstallIn64BitMode=x64

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional icons:"; Flags: checked
Name: "startupicon"; Description: "Launch Bally AI when Windows starts"; GroupDescription: "Additional icons:"; Flags: unchecked

[Files]
; Main application bundle from PyInstaller
Source: "{#DistDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; Start Menu
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}"
Name: "{group}\Uninstall {#AppName}"; Filename: "{uninstallexe}"
; Desktop shortcut
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon
; Startup
Name: "{userstartup}\{#AppName}"; Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}"; Tasks: startupicon

[Run]
; Launch app after install
Filename: "{app}\{#AppExeName}"; Description: "Launch {#AppName}"; Flags: nowait postinstall skipifsilent

[UninstallRun]
; Kill running processes on uninstall
Filename: "taskkill"; Parameters: "/F /IM {#AppExeName}"; Flags: runhidden

[Code]
// Show a custom "Welcome" page explaining the API key requirement
procedure InitializeWizard();
var
  WelcomePage: TWizardPage;
  InfoLabel: TLabel;
begin
  WelcomePage := CreateCustomPage(
    wpWelcome,
    'Before you begin',
    'What you need to use Bally AI'
  );

  InfoLabel := TLabel.Create(WelcomePage);
  InfoLabel.Parent := WelcomePage.Surface;
  InfoLabel.Left := 0;
  InfoLabel.Top := 0;
  InfoLabel.Width := WelcomePage.SurfaceWidth;
  InfoLabel.Height := 200;
  InfoLabel.WordWrap := True;
  InfoLabel.Caption :=
    'Bally AI converts Indian bank statement PDFs into Tally XML files.' + #13#10 + #13#10 +
    'To use the AI features, you need a FREE Groq API key:' + #13#10 + #13#10 +
    '  1. Go to https://console.groq.com' + #13#10 +
    '  2. Sign up for a free account' + #13#10 +
    '  3. Create an API key' + #13#10 + #13#10 +
    'You will be asked to enter this key the first time you launch the app.' + #13#10 +
    'The key is stored securely on your computer and never shared.';
end;
