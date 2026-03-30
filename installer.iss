[Setup]
AppId={{9A8B7C6D-4E3F-5B2A-0D1E-8F7G6H5I4J3K}
AppName=SC Localization Editor
AppVersion=0.3.0
AppPublisher=Osiris DevWorks
AppPublisherURL=https://github.com/Osiris-DevWorks/sc-localization-editor
DefaultDirName={localappdata}\Osiris DevWorks\SC Localization Editor
DefaultGroupName=SC Localization Editor
OutputDir=dist
OutputBaseFilename=SCLocalizationEditor-0.3.0-Setup
Compression=lzma
SolidCompression=yes
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
WizardStyle=modern
DisableDirPage=no
AllowUNCPath=no
PrivilegesRequired=lowest
SetupIconFile=assets\logo.ico

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[CustomMessages]
SCDirectoryPrompt=Star Citizen Directory
SCDirectoryPromptDesc=Please specify your Star Citizen LIVE directory for automatic file detection.
SCDirectoryDefaultDesc=This is typically located at:
SCDirectoryDefaultPath=C:\Program Files\Roberts Space Industries\StarCitizen\LIVE

[Files]
Source: "dist\SCLocalizationEditor-v0.3.0.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\SC Localization Editor"; Filename: "{app}\SCLocalizationEditor-v0.3.0.exe"
Name: "{group}\{cm:UninstallProgram,SC Localization Editor}"; Filename: "{uninstallexe}"
Name: "{commondesktop}\SC Localization Editor"; Filename: "{app}\SCLocalizationEditor-v0.3.0.exe"

[Run]
Filename: "{app}\SCLocalizationEditor-v0.3.0.exe"; Description: "{cm:LaunchProgram,SC Localization Editor}"; Flags: nowait postinstall skipifsilent

[Code]
var
  SCDirectoryPage: TInputDirWizardPage;
  SCDirectoryPath: String;

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

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if (CurStep=ssInstall) then
  begin
    if (IsUpgrade()) then
    begin
      UnInstallOldVersion();
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
begin
  { Create custom page for Star Citizen directory selection }
  DefaultPath := 'C:\Program Files\Roberts Space Industries\StarCitizen\LIVE';

  { Check if default SC directory exists }
  if DirExists('C:\Program Files\Roberts Space Industries\StarCitizen\LIVE') then
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

procedure CurPageChanged(CurPageID: Integer);
begin
  { Store the selected directory path }
  if CurPageID = SCDirectoryPage.ID then
  begin
    SCDirectoryPath := SCDirectoryPage.Values[0];
  end;
end;

procedure CurFinished(LastStep: TSetupStep);
var
  RegPath: String;
begin
  if LastStep = ssPostInstall then
  begin
    { Save the SC directory to registry for the application to use }
    if SCDirectoryPath <> '' then
    begin
      RegPath := 'Software\Osiris DevWorks\SC Localization Editor';
      RegWriteStringValue(HKCU, RegPath, 'sc_directory', SCDirectoryPath);
    end;
  end;
end;
