; Single source of truth: VERSION.TXT at the project root. Update that file
; and re-run the build — every version-stamped field below is derived from it.
#define VersionFile FileOpen(AddBackslash(SourcePath) + "VERSION.TXT")
#define AppVer Trim(FileRead(VersionFile))
#expr FileClose(VersionFile)
#undef VersionFile

[Setup]
AppId={{9A8B7C6D-4E3F-5B2A-0D1E-8F7G6H5I4J3K}
AppName=SC Localization Editor
AppVersion={#AppVer}
AppPublisher=Osiris DevWorks
AppPublisherURL=https://github.com/Osiris-DevWorks/sc-localization-editor
DefaultDirName={localappdata}\Osiris DevWorks\SC Localization Editor
DefaultGroupName=SC Localization Editor
OutputDir=dist
OutputBaseFilename=SCLocalizationEditor-{#AppVer}-Setup
Compression=lzma
SolidCompression=yes
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
WizardStyle=modern
DisableDirPage=no
AllowUNCPath=no
PrivilegesRequired=admin
SetupIconFile=assets\logo.ico

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[CustomMessages]
SCDirectoryPrompt=Star Citizen Directory
SCDirectoryPromptDesc=Please specify your Star Citizen LIVE directory for automatic file detection.
SCDirectoryDefaultDesc=This is typically located at:
SCDirectoryDefaultPath=C:\Program Files\Roberts Space Industries\StarCitizen\LIVE

[InstallDelete]
; Clear previous install directory completely before installing new files
Type: filesandordirs; Name: "{app}\*"

[Files]
Source: "dist\SCLocalizationEditor-v{#AppVer}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\SC Localization Editor"; Filename: "{app}\SCLocalizationEditor-v{#AppVer}.exe"
Name: "{group}\{cm:UninstallProgram,SC Localization Editor}"; Filename: "{uninstallexe}"
Name: "{commondesktop}\SC Localization Editor"; Filename: "{app}\SCLocalizationEditor-v{#AppVer}.exe"

[Run]
Filename: "{app}\SCLocalizationEditor-v{#AppVer}.exe"; Description: "{cm:LaunchProgram,SC Localization Editor}"; Flags: nowait postinstall skipifsilent

[Code]
var
  SCDirectoryPage: TInputDirWizardPage;

function GetUninstallString(): String;
var
  sUnInstPath: String;
  sUnInstallString: String;
begin
  sUnInstPath := ExpandConstant('Software\Microsoft\Windows\CurrentVersion\Uninstall\{#emit SetupSetting("AppId")}_is1');
  sUnInstallString := '';
  if not RegQueryStringValue(HKLM, sUnInstPath, 'UninstallString', sUnInstallString) then
    RegQueryStringValue(HKCU, sUnInstPath, 'UninstallString', sUnInstallString);
  Result := sUnInstallString;
end;

function IsUpgrade(): Boolean;
begin
  Result := (GetUninstallString() <> '');
end;

function UnInstallOldVersion(): Integer;
var
  sUnInstallString: String;
  iResultCode: Integer;
begin
  { Return Values:
    1 - uninstall string is empty
    2 - error executing the UnInstallString
    3 - successfully executed the UnInstallString }

  Result := 0;

  { get the uninstall string of the old app }
  sUnInstallString := GetUninstallString();
  if sUnInstallString <> '' then begin
    sUnInstallString := RemoveQuotes(sUnInstallString);
    if Exec(sUnInstallString, '/SILENT /NORESTART /SUPPRESSMSGBOXES','', SW_HIDE, ewWaitUntilTerminated, iResultCode) then
      Result := 3
    else
      Result := 2;
  end else
    Result := 1;
end;

function GetDocumentsDir(): String;
var
  DocsPath: String;
begin
  if not RegQueryStringValue(HKCU,
    'SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders',
    'Personal', DocsPath) then
  begin
    DocsPath := ExpandConstant('{userdocs}');
  end;
  Result := DocsPath + '\SC Localization Editor';
end;

procedure CleanCachedData();
var
  UserDataDir: String;
begin
  UserDataDir := GetDocumentsDir();
  if DirExists(UserDataDir) then
  begin
    Log('Cleaning cached data from: ' + UserDataDir);
    { Only \cache is deleted. \backups (user's global.ini safety net) and
      user.ini (their customizations) must survive install AND uninstall. }
    DelTree(UserDataDir + '\cache', True, True, True);
  end;
end;

procedure CleanRegistrySettings();
var
  RegPath: String;
  SavedSCDir: String;
  HadSCDir: Boolean;
begin
  RegPath := 'Software\Osiris DevWorks\SC Localization Editor';

  { Preserve sc_directory so the installer page can pre-fill it }
  HadSCDir := RegQueryStringValue(HKCU, RegPath, 'sc_directory', SavedSCDir);

  { Delete the entire app registry key }
  RegDeleteKeyIncludingSubkeys(HKCU, RegPath);

  { Restore sc_directory if it existed }
  if HadSCDir and (SavedSCDir <> '') then
  begin
    RegWriteStringValue(HKCU, RegPath, 'sc_directory', SavedSCDir);
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if (CurStep=ssInstall) then
  begin
    if (IsUpgrade()) then
    begin
      UnInstallOldVersion();
    end;

    { Clear cached data but preserve registry settings (source paths, preferences, etc.) }
    CleanCachedData();
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  UserDataDir: String;
begin
  if CurUninstallStep = usUninstall then
  begin
    UserDataDir := GetDocumentsDir();
    if DirExists(UserDataDir) then
    begin
      Log('Cleaning cached data during uninstall: ' + UserDataDir);
      { Only \cache is deleted. \backups (user's global.ini safety net) and
        user.ini (their customizations) must survive uninstall — a user
        reinstalling later should find their backups intact. }
      DelTree(UserDataDir + '\cache', True, True, True);
    end;
  end;
end;

function InitializeSetup(): Boolean;
var
  ResultCode: Integer;
  UninstallString: String;
  ButtonPressed: Integer;
begin
  Result := True;

  { Check if the application is already installed }
  UninstallString := GetUninstallString();
  if UninstallString <> '' then
  begin
    { Show custom dialog with three options }
    ButtonPressed := MsgBox('SC Localization Editor is already installed.' + #13#10 + #13#10 +
                            'Choose an option:' + #13#10 +
                            '  - Click YES to uninstall the old version and install this new version' + #13#10 +
                            '  - Click NO to uninstall the old version only (without installing)' + #13#10 +
                            '  - Click CANCEL to exit without making any changes',
                            mbConfirmation, MB_YESNOCANCEL);

    case ButtonPressed of
      IDYES: begin
        { Continue with upgrade (uninstall old, then install new) }
        Result := True;
      end;
      IDNO: begin
        { Uninstall only, without installing new version }
        UninstallString := RemoveQuotes(UninstallString);
        Exec(UninstallString, '/SILENT /NORESTART /SUPPRESSMSGBOXES','', SW_HIDE, ewWaitUntilTerminated, ResultCode);
        Result := False;
      end;
      IDCANCEL: begin
        { Cancel installation }
        Result := False;
      end;
    end;
  end;
end;

procedure InitializeWizard();
var
  DefaultPath: String;
  RegPath: String;
  SavedPath: String;
begin
  RegPath := 'Software\Osiris DevWorks\SC Localization Editor';
  DefaultPath := '';

  { Prefer previously saved SC directory (installer key, then Config tab QSettings key) }
  if RegQueryStringValue(HKCU, RegPath, 'sc_directory', SavedPath) and (SavedPath <> '') then
    DefaultPath := SavedPath
  else if RegQueryStringValue(HKCU, RegPath, 'game_install_path', SavedPath) and (SavedPath <> '') then
    DefaultPath := SavedPath
  else if DirExists('C:\Program Files\Roberts Space Industries\StarCitizen\LIVE') then
    DefaultPath := 'C:\Program Files\Roberts Space Industries\StarCitizen\LIVE'
  else if DirExists('C:\Program Files (x86)\Roberts Space Industries\StarCitizen\LIVE') then
    DefaultPath := 'C:\Program Files (x86)\Roberts Space Industries\StarCitizen\LIVE'
  else
    DefaultPath := 'C:\Program Files\Roberts Space Industries\StarCitizen';

  SCDirectoryPage := CreateInputDirPage(
    wpSelectTasks,
    ExpandConstant('{cm:SCDirectoryPrompt}'),
    ExpandConstant('{cm:SCDirectoryPromptDesc}'),
    ExpandConstant('{cm:SCDirectoryDefaultDesc}' + #13#10 + '{cm:SCDirectoryDefaultPath}'),
    False,
    'Star Citizen LIVE Directory'
  );

  SCDirectoryPage.Add('');
  SCDirectoryPage.Values[0] := DefaultPath;
end;

procedure CurFinished(LastStep: TSetupStep);
var
  RegPath: String;
  FinalPath: String;
begin
  if LastStep = ssPostInstall then
  begin
    { Read the SC directory value at finish time (not page-change time)
      to ensure we capture any edits the user made on the page }
    FinalPath := SCDirectoryPage.Values[0];
    if FinalPath <> '' then
    begin
      RegPath := 'Software\Osiris DevWorks\SC Localization Editor';
      RegWriteStringValue(HKCU, RegPath, 'sc_directory', FinalPath);
      Log('Saved sc_directory to registry: ' + FinalPath);
    end;
  end;
end;
