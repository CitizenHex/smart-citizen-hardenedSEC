[Setup]
AppName=SC Localization Editor
AppVersion=0.1.0
AppPublisher=Osiris DevWorks
AppPublisherURL=https://github.com/Osiris-DevWorks/sc-localization-editor
DefaultDirName={pf}\Osiris DevWorks\SC Localization Editor
DefaultGroupName=SC Localization Editor
OutputDir=.
OutputBaseFilename=SCLocalizationEditor-0.1.0-Setup
Compression=lzma
SolidCompression=yes
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
WizardStyle=modern

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[CustomMessages]
SCDirectoryPrompt=Star Citizen Directory
SCDirectoryPromptDesc=Please specify your Star Citizen LIVE directory for automatic file detection.
SCDirectoryDefaultDesc=This is typically located at:
SCDirectoryDefaultPath=C:\Program Files\Roberts Space Industries\StarCitizen\LIVE

[Files]
Source: "dist\SCLocalizationEditor-v0.1.0.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\SC Localization Editor"; Filename: "{app}\SCLocalizationEditor.exe"
Name: "{group}\{cm:UninstallProgram,SC Localization Editor}"; Filename: "{uninstallexe}"
Name: "{commondesktop}\SC Localization Editor"; Filename: "{app}\SCLocalizationEditor.exe"

[Run]
Filename: "{app}\SCLocalizationEditor.exe"; Description: "{cm:LaunchProgram,SC Localization Editor}"; Flags: nowait postinstall skipifsilent

[Code]
var
  SCDirectoryPage: TInputDirWizardPage;
  SCDirectoryPath: String;

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

function InitializeSetup(): Boolean;
begin
  Result := True;
end;
