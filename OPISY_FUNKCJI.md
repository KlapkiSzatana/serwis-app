# Opisy funkcji

## Główny plik

### `serwis-app.py`

- `SerwisAppWindow` - główne okno aplikacji. Odpowiada za start interfejsu, zapis rozmiaru okna, szerokości kolumn, automatyczny backup przy zamykaniu i odświeżanie daty w pasku menu.
- `odswiez_tabele_z_filtrami()` - odświeża listę zleceń z uwzględnieniem aktywnego filtra statusu, zakresu dat i tekstu wyszukiwania.
- `ustaw_filtr(filtr)` - zapisuje nowy filtr dat i aktualizuje tekst przycisku filtra.
- `otworz_filtr_daty()` - otwiera okno wyboru zakresu dat.
- `otworz_szczegoly(index)` - otwiera szczegóły zaznaczonego zlecenia.
- `otworz_backup()` - otwiera okno wykonywania i przywracania kopii zapasowej.
- `otworz_klienci()` - otwiera bazę klientów.
- `drukuj_wybrane_zlecenie()` - pobiera zaznaczone zlecenie i przekazuje je do modułu wydruku.
- `usun_zlecenie()` - usuwa wybrane zlecenie po potwierdzeniu użytkownika.
- `zmien_status(...)` - zmienia status zlecenia i zapisuje dane naprawy.
- `pokaz_menu_kontekstowe(pos)` - buduje menu pod prawym przyciskiem myszy dla tabeli zleceń.
- `on_baza_clicked()` - uruchamia wybór lokalnej albo zdalnej bazy danych.

## Zlecenia i baza

### `modules/zlecenia.py`

- `ensure_pilne_column(cursor)` - zapewnia istnienie kolumny `pilne` w bazie.
- `pobierz_nastepny_numer_roczny(cursor)` - wylicza kolejny numer roczny zlecenia.
- `dodaj_zlecenie(...)` - otwiera formularz dodania zlecenia i zapisuje rekord w bazie.
- `zakoncz_zlecenie(...)` - finalizuje zlecenie i ustawia status zakończenia.
- `popraw_dane(...)` - otwiera edycję istniejącego zlecenia.
- `pokaz_szczegoly(...)` - pokazuje szczegóły zlecenia w trybie tylko do odczytu.
- `CopyableLineEdit`, `CopyableTextEdit` - pola tekstowe z własnym menu kopiowania.

### `modules/baza.py`

- `zapisz_baze(...)` - zapisuje wybraną ścieżkę bazy do pliku konfiguracyjnego.
- `wczytaj_baze(...)` - odczytuje zapamiętaną ścieżkę bazy.
- `wybierz_baze_dialog(...)` - pokazuje dialog wyboru bazy lokalnej lub sieciowej.
- `init_baza(...)` - inicjalizuje połączenie SQLite i tworzy brakujące tabele.
- `zapisz_filtr(...)` - zapisuje aktywny filtr dat do konfiguracji.
- `wczytaj_filtr(...)` - odczytuje ostatni filtr dat.

## Backup i wydruki

### `modules/backup.py`

- `force_remove_file(path, ...)` - usuwa plik z ponawianiem prób, gdy system blokuje zapis.
- `clean_directory(path)` - czyści katalog bez usuwania katalogu głównego.
- `wykonaj_backup_logika(dst_path, progress_callback=None)` - pakuje katalog danych użytkownika `.SerwisApp` do pliku `.bak`.
- `Ui_MainWindow` - interfejs okna backupu; obsługuje wybór ścieżki, zapis ostatniej lokalizacji, automatyczny backup i przywracanie danych.

### `modules/drukowanie.py`

- `get_print_mode()`, `set_print_mode(mode)` - odczyt i zapis trybu wydruku.
- `get_preview_mode()`, `set_preview_mode(enabled)` - odczyt i zapis podglądu przed drukiem.
- `get_report_engine()`, `set_report_engine(engine)` - konfiguracja silnika raportów.
- `get_order_engine()`, `set_order_engine(engine)` - konfiguracja silnika wydruku zleceń.
- `VisualEditor` - wizualny edytor układu dokumentów.
- `edytuj_szablon(parent)` - otwiera edytor szablonu.
- `drukuj_zlecenie_html(...)` - główne wejście do drukowania zleceń.
- `generuj_kod_zlecenia_base64_maly(...)` - generuje mały kod kreskowy w base64.

## Bezpieczeństwo i komunikacja

### `modules/password_protection.py`

- `ensure_dirs()` - tworzy wymagane katalogi i pliki bezpieczeństwa.
- `get_fernet()` - ładuje lub generuje klucz szyfrujący.
- `init_users_table()` - przygotowuje tabelę użytkowników.
- `db_add_user(...)`, `db_update_pass(...)`, `db_delete_user(...)` - operacje administracyjne na użytkownikach.
- `db_verify_user(...)` - sprawdza login i hasło użytkownika.
- `sprawdz_haslo_przy_starcie(parent=None)` - wymusza logowanie przy starcie programu.
- `menedzer_hasel(parent=None, force_admin=False)` - otwiera panel zarządzania użytkownikami i hasłami.
- `PasswordManagerDialog`, `LoginDialog`, `ChangeOwnPasswordDialog` - okna logowania i administracji użytkownikami.

### `modules/mail.py`

- `MailClient` - buduje wiadomość e-mail, dołącza logo firmy i wysyła wiadomość przez SMTP.

### `modules/sms.py`

- `SMSConfigDialog` - okno konfiguracji dostawcy SMS.
- `SMSClient` - przygotowuje i wysyła wiadomości SMS do klienta.

## Interfejs i moduły pomocnicze

### `ui/ui_main.py`

- `EmailConfigWindow` - okno konfiguracji SMTP.
- `Ui_MainWindow` - buduje główne menu, tabelę, paski narzędzi i dolne przyciski aplikacji.
- `update_plus_status()` - pokazuje typ aktualnej bazy i nazwę firmy w pasku statusu.

### `modules/odswiez_tabele.py`

- `strip_html_tags(text)` - usuwa HTML z treści przed pokazaniem w tabeli.
- `odswiez_tabele(...)` - pobiera dane z bazy i zasila model tabeli zleceń.

### `modules/labele.py`

- `obsluga_menu_kontekstowego(pos, label)` - dodaje kopiowanie dla etykiet z danymi.
- `pokaz_szczegoly_w_labelach(...)` - aktualizuje panel szczegółów po zmianie zaznaczenia.

### `modules/firma.py`

- `edytuj_dane_firmy(parent, conn)` - edycja danych firmy dostępna dla administratora.
- `okno_konfiguracji_firmy(parent, conn)` - pierwsza konfiguracja danych firmy i własnego logo.

### `modules/utils.py`

- `resource_path(relative_path)` - rozwiązuje ścieżkę do zasobu w trybie developerskim, pakowanym i instalowanym.
- `get_app_icon_name(platform=None)` - wybiera właściwy plik ikony dla Linux, Windows lub macOS.
- `get_app_icon_path(platform=None)` - zwraca pełną ścieżkę do ikony programu.
- `get_app_logo_path()` - zwraca pełną ścieżkę do głównego logo PNG.
- `formatuj_numer_zlecenia(...)` - formatuje numer zlecenia na podstawie daty i numeru rocznego.

## Moduły dodatkowe

- `modules/raport.py` - raporty finansowe, najczęściej naprawiany sprzęt i najdroższe naprawy.
- `modules/cennik.py` - podgląd i edycja cennika usług.
- `modules/klienci.py` - baza klientów, szybkie dodawanie i podgląd historii.
- `modules/date_filter.py` - okno wyboru zakresu dat.
- `modules/startup_popup.py` - okno powitalne po starcie programu.
- `modules/pokaz_info.py` - okno "O programie" i skrót licencji.
- `modules/pomoc.py` - odnośnik wsparcia projektu.
- `modules/game.py`, `modules/easteregg.py` - ukryte moduły dodatkowe uruchamiane z poziomu interfejsu.
