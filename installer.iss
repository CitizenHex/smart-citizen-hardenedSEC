[Setup]
AppName=SC Localization Editor
AppVersion=0.1.0
AppPublisher=Osiris DevWorks
AppPublisherURL=https://github.com/OsirisDevworks/sc-localization-editor
DefaultDirName={pf}\Osiris DevWorks\SC Localization Editor
DefaultGroupName=SC Localization Editor
OutputDir=output
OutputBaseFilename=SCLocalizationEditor-0.1.0-installer
Compression=lzma
SolidCompression=yes
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
Source: "dist\SCLocalizationEditor\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\SC Localization Editor"; Filename: "{app}\SCLocalizationEditor.exe"
Name: "{group}\{cm:UninstallProgram,SC Localization Editor}"; Filename: "{uninstallexe}"
Name: "{commondesktop}\SC Localization Editor"; Filename: "{app}\SCLocalizationEditor.exe"

[Code]
procedure CreateOrUpdateUserCfg;
var
  UserCfgPath: string;
  FileContent: string;
  HasLanguageLine: Boolean;
begin
  UserCfgPath := ExpandConstant('{app}\..\..\..\LIVE\user.cfg');

  if FileExists(UserCfgPath) then
  begin
    { File exists: read it, check for g_language = english }
    LoadStringFromFile(UserCfgPath, FileContent);
    HasLanguageLine := Pos('g_language = english', FileContent) > 0;

    if not HasLanguageLine then
    begin
      { Append the line if not present }
      FileContent := FileContent + #13#10 + 'g_language = english';
      SaveStringToFile(UserCfgPath, FileContent, False);
    end;
  end
  else
  begin
    { File doesn't exist: create it with g_language = english }
    SaveStringToFile(UserCfgPath, 'g_language = english', False);
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    CreateOrUpdateUserCfg();
  end;
end;

function InitializeSetup(): Boolean;
begin
  Result := True;
end;
