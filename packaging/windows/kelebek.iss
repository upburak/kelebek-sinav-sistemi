; Inno Setup betiği: Windows kurulum paketi. Kullanıcı verisi %APPDATA% altında kalır, kaldırmada silinmez.
#ifndef AppVersion
  #define AppVersion "0.2.0"
#endif

[Setup]
AppId={{6F1B7C2E-4B7A-4D49-9C1E-5A3B2C1D0E01}
AppName=Kelebek Sınav Sistemi
AppVersion={#AppVersion}
AppPublisher=Kelebek Sınav Sistemi
DefaultDirName={localappdata}\Programs\KelebekSinavSistemi
DefaultGroupName=Kelebek Sınav Sistemi
PrivilegesRequired=lowest
OutputDir=..\..\dist
OutputBaseFilename=KelebekSinavSistemi-{#AppVersion}-windows-x64-kurulum
Compression=lzma2
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64compatible
WizardStyle=modern

[Languages]
Name: "turkish"; MessagesFile: "compiler:Languages\Turkish.isl"

[Tasks]
Name: "desktopicon"; Description: "Masaüstü kısayolu oluştur"; GroupDescription: "Kısayollar:"

[Files]
Source: "..\..\dist\KelebekSinavSistemi\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Kelebek Sınav Sistemi"; Filename: "{app}\KelebekSinavSistemi.exe"
Name: "{autodesktop}\Kelebek Sınav Sistemi"; Filename: "{app}\KelebekSinavSistemi.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\KelebekSinavSistemi.exe"; Description: "Kelebek Sınav Sistemi'ni başlat"; Flags: nowait postinstall skipifsilent
