; Instalador Windows do MT5Bot (Inno Setup 6) — spec 002 FR-2/FR-3/FR-7.
; Gerado por packaging\windows\build.ps1, que passa AppVersion, StageDir e RepoRoot.

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

[Setup]
AppId={{6F3C2B8E-4A1D-4E7B-9C55-2D8F1A0B7E61}
AppName=MT5Bot
AppVersion={#AppVersion}
AppVerName=MT5Bot {#AppVersion}
AppPublisher=Fabio Dornele
AppPublisherURL=https://github.com/fabiodrneles/mt5_bot
AppSupportURL=https://github.com/fabiodrneles/mt5_bot/issues
; Instalacao por usuario, sem administrador (FR-3).
PrivilegesRequired=lowest
DefaultDirName={localappdata}\Programs\MT5Bot
DisableProgramGroupPage=yes
LicenseFile={#RepoRoot}\LICENSE
OutputBaseFilename=MT5Bot-Setup-{#AppVersion}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayName=MT5Bot {#AppVersion}

[Languages]
Name: "pt"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"
Name: "en"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "{#StageDir}\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{autoprograms}\MT5Bot\MT5Bot Quant"; Filename: "{cmd}"; Parameters: "/k ""{app}\bot.bat"" quant"; WorkingDir: "{app}"; Comment: "Rotas quant validadas (painel ao vivo)"
Name: "{autoprograms}\MT5Bot\MT5Bot Maestro"; Filename: "{app}\mt5bot.bat"; WorkingDir: "{app}\maestro"; Comment: "Painel interativo com varios robos"
Name: "{autoprograms}\MT5Bot\MT5Bot Dashboard"; Filename: "{cmd}"; Parameters: "/k ""{app}\bot.bat"" dashboard"; WorkingDir: "{app}"; Comment: "Painel web ao vivo no navegador"
Name: "{autoprograms}\MT5Bot\Diagnostico"; Filename: "{cmd}"; Parameters: "/k ""{app}\bot.bat"" diagnose"; WorkingDir: "{app}"
Name: "{autoprograms}\MT5Bot\Desinstalar MT5Bot"; Filename: "{uninstallexe}"
Name: "{autodesktop}\MT5Bot Quant"; Filename: "{cmd}"; Parameters: "/k ""{app}\bot.bat"" quant"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{cmd}"; Parameters: "/k ""{app}\bot.bat"" diagnose"; WorkingDir: "{app}"; Description: "Testar a conexao com o MetaTrader 5 agora"; Flags: postinstall nowait skipifsilent unchecked

[UninstallDelete]
; Arquivos gerados em tempo de execucao dentro da pasta do programa (cache, indice RAG).
Type: filesandordirs; Name: "{app}"

[Code]
// FR-7: os dados do usuario (%APPDATA%\mt5bot: trades, logs, config.toml)
// so sao apagados se ele pedir. Na desinstalacao silenciosa, sempre ficam.
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  DataDir: String;
begin
  if CurUninstallStep = usPostUninstall then
  begin
    DataDir := ExpandConstant('{userappdata}\mt5bot');
    if DirExists(DataDir) and (not UninstallSilent) then
      if MsgBox('Apagar tambem seus dados do MT5Bot (historico de trades, logs e config.toml)?' + #13#10 + DataDir,
                mbConfirmation, MB_YESNO or MB_DEFBUTTON2) = IDYES then
        DelTree(DataDir, True, True, True);
  end;
end;
