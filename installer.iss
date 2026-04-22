; Single source of truth: VERSION.TXT at the project root. Update that file
; and re-run the build — every version-stamped field below is derived from it.
#define VersionFile FileOpen(AddBackslash(SourcePath) + "VERSION.TXT")
#define AppVer Trim(FileRead(VersionFile))
#expr FileClose(VersionFile)
#undef VersionFile

[Setup]
AppId={{9A8B7C6D-4E3F-5B2A-0D1E-8F7G6H5I4J3K}
AppName=Smart Citizen
AppVersion={#AppVer}
AppPublisher=Osiris DevWorks
AppPublisherURL=https://github.com/Osiris-DevWorks/smart-citizen
DefaultDirName={localappdata}\Osiris DevWorks\Smart Citizen
DefaultGroupName=Smart Citizen
OutputDir=dist
OutputBaseFilename=SmartCitizen-{#AppVer}-Setup
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
Source: "dist\SmartCitizen-v{#AppVer}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Smart Citizen"; Filename: "{app}\SmartCitizen-v{#AppVer}.exe"
Name: "{group}\{cm:UninstallProgram,Smart Citizen}"; Filename: "{uninstallexe}"
Name: "{commondesktop}\Smart Citizen"; Filename: "{app}\SmartCitizen-v{#AppVer}.exe"

[Run]
Filename: "{app}\SmartCitizen-v{#AppVer}.exe"; Description: "{cm:LaunchProgram,Smart Citizen}"; Flags: nowait postinstall skipifsilent

[Code]
var
  SCDirectoryPage: TInputDirWizardPage;
  DataDirPage: TInputDirWizardPage;
  DataDirPromptShown: Boolean;

function IsDocsOnOneDrive(): Boolean;
var
  DocsPath: String;
begin
  { Read the invoking user's Documents shell-folder path. When Windows has
    folder-redirected Documents into OneDrive (the default on most OneDrive
    installs now), this string contains "\OneDrive\". Cache extraction +
    50,000-file rmtree under an actively-synced OneDrive tree is 3-5x
    slower and routinely fails with WinError 5 — worth warning the user
    and offering a local-only alternative. }
  Result := False;
  if RegQueryStringValue(HKCU,
    'SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders',
    'Personal', DocsPath) then
  begin
    Result := (Pos('\OneDrive\', DocsPath) > 0) or
              (Pos('\OneDrive/', DocsPath) > 0);
  end;
end;

function HasDataDirOverride(): Boolean;
var
  Dummy: String;
begin
  { Respect existing user choice — if the override is already set in either
    the new "Smart Citizen" node or the legacy "SC Localization Editor"
    node, skip the prompt entirely. }
  Result := RegQueryStringValue(HKCU,
              'Software\Osiris DevWorks\Smart Citizen',
              'user_data_dir', Dummy) or
            RegQueryStringValue(HKCU,
              'Software\Osiris DevWorks\SC Localization Editor',
              'user_data_dir', Dummy);
end;

function SuggestLocalDataDir(): String;
begin
  { Build a sensible default pointing at the local (non-OneDrive) profile.
    %USERPROFILE% is the real NTFS path; \Documents here is the junction
    that Windows keeps even when the shell's Personal has been redirected. }
  Result := ExpandConstant('{%USERPROFILE}\Documents\Smart Citizen');
end;

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

function GetDocumentsBase(): String;
begin
  if not RegQueryStringValue(HKCU,
    'SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders',
    'Personal', Result) then
  begin
    Result := ExpandConstant('{userdocs}');
  end;
end;

function GetDocumentsDir(): String;
begin
  Result := GetDocumentsBase() + '\Smart Citizen';
end;

procedure MigrateUserDocsFolder();
var
  DocsBase, OldDir, NewDir: String;
begin
  { Rebrand: rename Documents\SC Localization Editor\ → Documents\Smart Citizen\
    if the old folder exists and the new one does not. User data (user.ini,
    backups, cache) moves with the rename — no copy required. }
  DocsBase := GetDocumentsBase();
  OldDir := DocsBase + '\SC Localization Editor';
  NewDir := DocsBase + '\Smart Citizen';
  if DirExists(OldDir) and not DirExists(NewDir) then
  begin
    MsgBox('Your user data folder will be renamed as part of this update:' + #13#10 + #13#10 +
           '  ' + OldDir + #13#10 +
           '  →  ' + NewDir + #13#10 + #13#10 +
           'Your custom edits, backups, and cached files will move with it — nothing is lost.',
           mbInformation, MB_OK);
    Log('Renaming user data folder: ' + OldDir + ' -> ' + NewDir);
    if not RenameFile(OldDir, NewDir) then
      Log('WARNING: rename failed; data remains at old location');
  end;
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

    { Rebrand migration: rename Documents\SC Localization Editor\ to
      Documents\Smart Citizen\ before we touch any cached data. }
    MigrateUserDocsFolder();

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
    ButtonPressed := MsgBox('A previous version of this application is already installed.' + #13#10 + #13#10 +
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

  { Rebrand: if the prior install is still under the old "SC Localization
    Editor" folder name, override the prefilled app dir (and start-menu
    group) to the new brand. Any other prior location — including one the
    user customized — is preserved. }
  if Pos('SC Localization Editor', WizardForm.DirEdit.Text) > 0 then
    WizardForm.DirEdit.Text := ExpandConstant('{localappdata}\Osiris DevWorks\Smart Citizen');
  if Pos('SC Localization Editor', WizardForm.GroupEdit.Text) > 0 then
    WizardForm.GroupEdit.Text := 'Smart Citizen';

  { OneDrive guard rail: when Documents is redirected to OneDrive, offer
    to store Smart Citizen's cache + user.ini on a local path instead.
    The page is *always* created (so ShouldSkipPage has something to
    reference) but hidden when it doesn't apply. DataDirPromptShown
    records whether it was actually exposed, so CurFinished only persists
    a value the user was given the chance to see. }
  DataDirPage := CreateInputDirPage(
    SCDirectoryPage.ID,
    'Smart Citizen Data Location',
    'Your Documents folder is synced to OneDrive — pick where to store data.',
    'Smart Citizen caches 2+ GB of extracted game data and stores your custom edits ' +
    'under your Documents folder. OneDrive-synced Documents is known to cause problems:'
    + #13#10 + #13#10 +
    '  - DataForge extraction is 3-5x slower because OneDrive, Windows Defender,'
    + #13#10 +
    '    and the Search Indexer each intercept every one of the 50,000+ files'
    + #13#10 +
    '  - Cache rebuilds can fail with "Access is denied" errors when OneDrive holds'
    + #13#10 +
    '    a transient file lock'
    + #13#10 +
    '  - The 2+ GB cache uploads to your OneDrive cloud quota on every rebuild'
    + #13#10 + #13#10 +
    'We recommend a local (non-OneDrive) folder. Accept the suggestion below, browse ' +
    'to a different location, or clear the field to keep the OneDrive default.',
    False,
    'Smart Citizen Data'
  );
  DataDirPage.Add('');
  DataDirPage.Values[0] := SuggestLocalDataDir();
  DataDirPromptShown := False;
end;

function ShouldSkipPage(PageID: Integer): Boolean;
begin
  Result := False;
  if (DataDirPage <> nil) and (PageID = DataDirPage.ID) then
  begin
    { Skip unless Documents is OneDrive-synced AND the user hasn't already
      set an override from a prior launch. }
    if IsDocsOnOneDrive() and not HasDataDirOverride() then
      DataDirPromptShown := True
    else
      Result := True;
  end;
end;

procedure CurFinished(LastStep: TSetupStep);
var
  RegPath: String;
  FinalPath: String;
  DataDir: String;
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

    { Persist the OneDrive-escape choice. Writes to the NEW (Smart Citizen)
      node — 0.9.2+ reads user_data_dir from there. If a legacy install's
      migration runs afterwards and the old node happens to carry its own
      user_data_dir, that user's prior explicit choice wins (migration
      overwrites). Otherwise this installer-written value survives. }
    if DataDirPromptShown then
    begin
      DataDir := DataDirPage.Values[0];
      if DataDir <> '' then
      begin
        RegWriteStringValue(HKCU,
          'Software\Osiris DevWorks\Smart Citizen',
          'user_data_dir', DataDir);
        ForceDirectories(DataDir);
        Log('Saved user_data_dir to registry: ' + DataDir);
      end
      else
      begin
        Log('User cleared data-dir override; keeping OneDrive default.');
      end;
    end;
  end;
end;
