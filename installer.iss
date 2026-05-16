[Setup]
AppName=SerwisApp
AppVersion=3.0.0
AppVerName=SerwisApp 3.0.0
AppPublisher=KlapkiSzatana
AppPublisherURL=https://github.com/KlapkiSzatana/serwis-app
AppSupportURL=https://github.com/KlapkiSzatana/serwis-app/issues
AppUpdatesURL=https://github.com/KlapkiSzatana/serwis-app/releases
AppCopyright=© 2026 KlapkiSzatana
DefaultDirName={userappdata}\KlapkiSzatana\SerwisApp
DefaultGroupName=SerwisApp
UninstallDisplayIcon={app}\serwis-app.exe
UninstallDisplayName=SerwisApp 3.0.0 - Proste Prowadzenie Serwisu
VersionInfoCompany=KlapkiSzatana
VersionInfoDescription=Proste Prowadzenie Serwisu
VersionInfoCopyright=Copyright © 2026 KlapkiSzatana
VersionInfoVersion=3.0.0.0
Compression=lzma
SolidCompression=yes
OutputDir=user_setup
OutputBaseFilename=SerwisApp_Setup
LicenseFile=LICENSE
PrivilegesRequired=lowest

[Files]
Source: "dist\serwis-app\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{userdesktop}\SerwisApp"; Filename: "{app}\serwis-app.exe"; Tasks: desktopicon
Name: "{userprograms}\SerwisApp"; Filename: "{app}\serwis-app.exe"

[Tasks]
Name: "desktopicon"; Description: "Stwórz skrót na pulpicie"; GroupDescription: "Dodatkowe:"; Flags: unchecked

[Run]
Filename: "{app}\serwis-app.exe"; Description: "Uruchom SerwisApp po zakończeniu"; Flags: nowait postinstall skipifsilent

