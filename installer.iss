[Setup]
AppName=SerwisApp
AppVersion=2.3.0
; Instalacja w AppData użytkownika w folderze Heisenberg\SerwisApp
DefaultDirName={userappdata}\KlapkiSzatana\SerwisApp
DefaultGroupName=SerwisApp
UninstallDisplayIcon={app}\serwis-app.exe
Compression=lzma
SolidCompression=yes
OutputDir=user_setup
OutputBaseFilename=SerwisApp_Setup
LicenseFile=LICENSE
PrivilegesRequired=lowest

[Files]
; Kopiuje całą zawartość folderu wyjściowego PyInstallera
Source: "dist\serwis-app\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{userdesktop}\SerwisApp"; Filename: "{app}\serwis-app.exe"; Tasks: desktopicon
Name: "{userprograms}\SerwisApp"; Filename: "{app}\serwis-app.exe"

[Tasks]
Name: "desktopicon"; Description: "Stwórz skrót na pulpicie"; GroupDescription: "Dodatkowe:"; Flags: unchecked

[Run]
Filename: "{app}\serwis-app.exe"; Description: "Uruchom SerwisApp po zakończeniu"; Flags: nowait postinstall skipifsilent
