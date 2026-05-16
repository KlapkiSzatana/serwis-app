import configparser
import datetime
import os
import shutil
import sqlite3
import sys
import gettext
import locale

if getattr(sys, 'frozen', False):
    base_path = os.path.dirname(sys.executable)
else:
    base_path = os.path.dirname(os.path.abspath(__file__))

locales_dir = os.path.join(base_path, 'locales')

system_lang = 'en'
try:
    lang_code, encoding = locale.getlocale()
    if lang_code:
        system_lang = lang_code
    else:
        system_lang = os.environ.get('LANG', 'en')
except Exception:
    system_lang = 'en'

lang = 'pl' if system_lang and str(system_lang).lower().startswith('pl') else 'en'

_ = lambda s: s

try:
    t = gettext.translation('messages', localedir=locales_dir, languages=[lang])
    t.install()
    _ = t.gettext
except FileNotFoundError:
    pass
except Exception as e:
    print(f"Błąd ładowania tłumaczeń: {e}")

from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtGui import QIcon, QStandardItemModel
from PySide6.QtCore import QTranslator, QLocale, QLibraryInfo, QTimer, QDate
from PySide6.QtWidgets import QMainWindow

from setup import config
from modules.backup import Ui_MainWindow as BackupUi, wykonaj_backup_logika
from modules.cennik import CennikDialog, polacz_uslugi_z_naprawa
from modules.drukowanie import drukuj_zlecenie_html
from modules.odswiez_tabele import odswiez_tabele
from modules.password_protection import sprawdz_haslo_przy_starcie
from modules.zlecenia import (
    dodaj_zlecenie, pokaz_szczegoly, popraw_dane
)
from modules import startup_popup
from ui.ui_main import Ui_MainWindow
from modules.utils import formatuj_numer_zlecenia, get_app_icon_path, get_app_logo_path, resource_path
from modules.baza import init_baza, wybierz_baze_dialog, wczytaj_filtr, wczytaj_baze
from modules.labele import pokaz_szczegoly_w_labelach
from modules.firma import edytuj_dane_firmy
from modules.date_filter import DateFilterPopup
from modules.klienci import KlienciWindow
from modules.sms import SMSClient

class SerwisAppWindow(QMainWindow):
    """Okno obsługujące wydzielony fragment funkcjonalności aplikacji."""
    def __init__(self):
        """Inicjalizuje obiekt i przygotowuje jego stan początkowy."""
        super().__init__()
        self.ui = Ui_MainWindow()
        # W __init__ klasy MainWindow:
        sprawdz_haslo_przy_starcie(self) # To wywoła nowe okno logowania (combo box z użytkownikami)
        self.ui.setupUi(self)
        self.ui.tableView.installEventFilter(self)
        self.setup_footer()
        self.update_plus_status() # Pierwsze załadowanie danych stopki
        self.mail_okno = None
        self.sms_okno = None
        self.backup_window = None
        self.klienci_window = None

        # --- OBSŁUGA DATY ---
        # 1. Wywołujemy raz, żeby data pojawiła się natychmiast po uruchomieniu
        self.update_datetime()

        # 2. Uruchamiamy timer, który odświeża datę co 30 sekund (30000 ms)
        self.date_timer = QTimer(self)
        self.date_timer.timeout.connect(self.update_datetime)
        self.date_timer.start(30000)

        # 1. Ustawienia okna i kolumn na start
        self.load_window_settings()
        self.ui.tableView.updateGeometry()
        QtWidgets.QApplication.processEvents()

        # 2. Wczytujemy kolumny (bez skalowania na starcie!)
        wczytano = self.wczytaj_ustawienia_kolumn()

        if not wczytano:
            defaults = [90, 90, 210, 130, 160, 160, 240, 130, 60]
            for col, w in enumerate(defaults):
                if col < self.ui.tableView.model().columnCount():
                    self.ui.tableView.setColumnWidth(col, w)

        # 3. Zapamiętujemy oryginalne zdarzenie resize
        self._original_resize = self.ui.tableView.resizeEvent

        # 4. INTELIGENTNE SKALOWANIE (POPRAWIONE)
        def smart_resize(event):
            # Najpierw Qt ustawia nowy rozmiar widoku
            """Realizuje logikę operacji smart resize w klasie SerwisAppWindow."""
            self._original_resize(event)

            viewport_width = self.ui.tableView.viewport().width()

            # --- ZMIANA: Margines bezpieczeństwa 2px ---
            target_width = viewport_width - 2

            # Obliczamy ile aktualnie zajmują wszystkie kolumny
            total_col_width = sum([self.ui.tableView.columnWidth(c) for c in range(self.ui.tableView.model().columnCount())])

            # Zabezpieczenia
            if target_width <= 0 or total_col_width <= 0:
                return

            # Jeśli różnica jest mała, nie ruszamy
            if abs(target_width - total_col_width) < 3:
                return

            # Obliczamy współczynnik dopasowania do SZEROKOŚCI Z MARGINESEM
            factor = target_width / total_col_width

            # Skalujemy tylko przy realnych zmianach rozmiaru okna (0.5x - 2.0x)
            if 0.5 < factor < 2.0:
                for col in range(self.ui.tableView.model().columnCount()):
                    current_w = self.ui.tableView.columnWidth(col)
                    new_w = max(20, int(current_w * factor))
                    self.ui.tableView.setColumnWidth(col, new_w)

        self.ui.tableView.resizeEvent = smart_resize

    def eventFilter(self, source, event):
        """Przechwytuje wciśnięcie klawisza Enter na tabeli i otwiera szczegóły."""
        from PySide6.QtCore import Qt, QEvent

        if source is self.ui.tableView and event.type() == QEvent.KeyPress:
            # Sprawdzamy oba klawisze Enter (zwykły Return i ten z klawiatury numerycznej Enter)
            if event.key() in (Qt.Key_Return, Qt.Key_Enter):
                current_index = self.ui.tableView.currentIndex()
                if current_index.isValid():
                    # Wywołujemy dokładnie tę samą funkcję, co przy podwójnym kliknięciu
                    otworz_szczegoly(current_index)
                    return True # Informujemy system, że obsłużyliśmy ten klawisz i ma go ignorować

        return super().eventFilter(source, event)

    def update_datetime(self):
        """Aktualizuje etykietę daty w głównym oknie"""
        now = QDate.currentDate()
        formatted = QLocale.system().toString(now, "dddd, d MMMM yyyy")

        if formatted:
            # Zamienia pierwszą literę na wielką
            formatted = formatted[0].upper() + formatted[1:]

        # Bezpieczne ustawienie tekstu w UI
        if hasattr(self.ui, "datetime_label"):
            self.ui.datetime_label.setText(formatted)

    # --- NOWE FUNKCJE DO ZAPISU/ODCZYTU OKNA ---
    def load_window_settings(self):
        """Wczytuje dane lub ustawienia potrzebne do działania."""
        cfg = configparser.ConfigParser()
        if os.path.exists(config.CONFIG_FILE):
            cfg.read(config.CONFIG_FILE, encoding="utf-8")

            if 'Window' in cfg:
                try:
                    # 1. Odczytujemy wymiary
                    x = int(cfg['Window'].get('x', 100))
                    y = int(cfg['Window'].get('y', 100))
                    w = int(cfg['Window'].get('width', 1200))
                    h = int(cfg['Window'].get('height', 800))

                    self.resize(w, h)
                    self.move(x, y)

                    # 2. Jeśli było zmaksymalizowane -> maksymalizujemy
                    if cfg['Window'].getboolean('maximized', fallback=False):
                        self.showMaximized()

                except ValueError:
                    pass

    def save_window_settings(self):
        """Zapisuje dane lub ustawienia."""
        cfg = configparser.ConfigParser()
        # Czytamy plik, żeby nie usunąć innych ustawień (np. sekcji BACKUP czy DATABASE)
        if os.path.exists(config.CONFIG_FILE):
            cfg.read(config.CONFIG_FILE, encoding="utf-8")

        if 'Window' not in cfg:
            cfg['Window'] = {}

        # Sprawdzamy stan
        is_maximized = self.isMaximized()
        cfg['Window']['maximized'] = str(is_maximized)

        if not is_maximized:
            # Zapisujemy wymiary tylko gdy okno "pływa" (nie jest na pełny ekran)
            rect = self.geometry()
            cfg['Window']['x'] = str(rect.x())
            cfg['Window']['y'] = str(rect.y())
            cfg['Window']['width'] = str(rect.width())
            cfg['Window']['height'] = str(rect.height())

        # Zapis do pliku
        with open(config.CONFIG_FILE, 'w', encoding="utf-8") as configfile:
            cfg.write(configfile)

    def wczytaj_ustawienia_kolumn(self):
        """Wczytuje szerokości kolumn 1:1 z pliku config.ini"""
        header = self.ui.tableView.horizontalHeader()
        header.setSectionResizeMode(QtWidgets.QHeaderView.Interactive)
        header.setStretchLastSection(False)

        cfg = configparser.ConfigParser()
        if os.path.exists(config.CONFIG_FILE):
            cfg.read(config.CONFIG_FILE, encoding="utf-8")
            if "COLUMNS" in cfg:
                for col in range(self.ui.tableView.model().columnCount()):
                    if cfg.has_option("COLUMNS", f"col{col}"):
                        val = cfg.getint("COLUMNS", f"col{col}")
                        self.ui.tableView.setColumnWidth(col, val)
                return True
        return False

    def zapisz_ustawienia_kolumn(self):
        """Zapisuje aktualne szerokości kolumn do config.ini"""
        cfg = configparser.ConfigParser()
        if os.path.exists(config.CONFIG_FILE):
            cfg.read(config.CONFIG_FILE, encoding="utf-8")

        if "COLUMNS" not in cfg:
            cfg["COLUMNS"] = {}

        model = self.ui.tableView.model()
        for col in range(model.columnCount()):
            width = self.ui.tableView.columnWidth(col)
            cfg["COLUMNS"][f"col{col}"] = str(width)

        with open(config.CONFIG_FILE, 'w', encoding="utf-8") as f:
            cfg.write(f)

    def closeEvent(self, event):
        # --- CZĘŚĆ 1: TWOJA ORYGINALNA LOGIKA BACKUPU ---
        """Obsługuje zamknięcie okna i zapisuje wymagany stan."""
        cfg = configparser.ConfigParser()
        if os.path.exists(config.CONFIG_FILE):
            cfg.read(config.CONFIG_FILE, encoding="utf-8")

            if "BACKUP" in cfg and cfg.getboolean("BACKUP", "auto_backup", fallback=False):
                last_path_file = os.path.join(os.path.expanduser("~"), ".SerwisApp", "last_path.txt")
                backup_path = ""
                if os.path.exists(last_path_file):
                    try:
                        with open(last_path_file, "r", encoding="utf-8") as f:
                            backup_path = f.read().strip()
                    except:
                        pass

                if backup_path and os.path.isdir(os.path.dirname(backup_path)):
                    progress = QtWidgets.QProgressDialog(_("Wykonywanie automatycznej kopii zapasowej..."), None, 0, 100, self)
                    progress.setWindowTitle(_("Zamykanie SerwisApp"))
                    progress.setWindowModality(QtCore.Qt.WindowModal)
                    progress.setMinimumDuration(0)
                    progress.setAutoClose(True)
                    progress.setValue(0)

                    try:
                        wykonaj_backup_logika(backup_path, lambda val: progress.setValue(val))
                    except Exception as e:
                        QtWidgets.QMessageBox.warning(self, _("Błąd Backupu"), f"{_('Nie udało się wykonać automatycznej kopii:')}\n{e}")

                    progress.setValue(100)


        # --- CZĘŚĆ 2: ZAPIS USTAWIEŃ ---

        self.save_window_settings()
        self.zapisz_ustawienia_kolumn()
        zapisz_stan_i_motyw()

        event.accept()

    def setup_footer(self):
        """Buduje nowoczesną stopkę Lux Style i umieszcza ją bezpośrednio w systemowym pasku stanu."""
        from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel
        from PySide6.QtCore import Qt
        import datetime
        from setup import config

        # 1. Ukrywamy domyślny styl paska stanu (usuwamy brzydki uchwyt zmiany rozmiaru w rogu, jeśli jest)
        self.ui.statusbar.setSizeGripEnabled(False)

        # Usuwamy wewnętrzne marginesy paska stanu, żeby stopka idealnie do niego przylegała
        self.ui.statusbar.setStyleSheet("QStatusBar { background: transparent; } QStatusBar::item { border: none; }")

        # 2. Tworzymy główny kontener stopki
        self.footer_widget = QWidget(self)
        self.footer_widget.setFixedHeight(26) # Nieco niższa, żeby idealnie pasowała do statusbaru

        footer_layout = QHBoxLayout(self.footer_widget)
        # Zerujemy marginesy pionowe, aby stopka nie była ucięta w małej belce
        footer_layout.setContentsMargins(10, 0, 10, 5)

        # Wspólny minimalistyczny styl (Lux Style)
        self.footer_badge_style = (
            "QLabel { font-size: 11px; font-weight: bold; color: gray; "
            "padding: 0px 8px; border: 1px solid #bdc3c7; border-radius: 4px; "
            "background-color: transparent; }"
        )

        # 3. Wersja aplikacji
        self.lbl_version = QLabel(f"v{config.APP_VERSION}")
        self.lbl_version.setStyleSheet(self.footer_badge_style)

        # 4. Tytuł sekcji bazy
        lbl_base_title = QLabel(_("Status Bazy:"))
        lbl_base_title.setStyleSheet("font-size: 10px; font-weight: bold; color: gray;")

        # 5. Plakietka statusu bazy i nazwy firmy
        self.lbl_base_status = QLabel()
        self.lbl_base_status.setStyleSheet(self.footer_badge_style)

        # 6. Prawa autorskie z dynamicznym rokiem
        curr_year = datetime.date.today().year
        year_str = f"2025-{curr_year}" if curr_year > 2025 else "2025"

        lbl_copy = QLabel(f"© KlapkiSzatana {year_str}")
        lbl_copy.setStyleSheet(self.footer_badge_style)

        # Układamy elementy w layoutu stopki
        footer_layout.addWidget(self.lbl_version)
        footer_layout.addSpacing(10)
        footer_layout.addWidget(lbl_base_title)
        footer_layout.addWidget(self.lbl_base_status)
        footer_layout.addStretch(1) # Przesuwa prawa autorskie do prawej krawędzi
        footer_layout.addWidget(lbl_copy)

        # --- KLUCZOWA ZMIANA ---
        # Dodajemy cały nasz przygotowany widget jako permanentny element paska stanu.
        # Dzięki temu będzie on zawsze widoczny, idealnie wyrównany i osadzony na samej dolnej belce!
        self.ui.statusbar.addPermanentWidget(self.footer_widget, 1)

    def update_plus_status(self):
        """Dynamicznie odczytuje stan bazy oraz nazwę firmy i aplikuje style do stopki."""
        import os
        import sqlite3
        from setup import config

        # --- 1. Ustalanie typu bazy (Lokalna vs Sieciowa) ---
        try:
            current_db_path = os.path.abspath(config.DB_FILE)
            current_dir = os.path.normpath(os.path.dirname(current_db_path))
        except Exception:
            current_dir = ""

        local_dir_raw = os.path.join(os.path.expanduser("~"), ".SerwisApp")
        local_dir = os.path.normpath(os.path.abspath(local_dir_raw))

        if os.name == 'nt':
            is_local = (current_dir.lower() == local_dir.lower())
        else:
            is_local = (current_dir == local_dir)

        if is_local:
            baza_txt = _("Baza Lokalna")
            # Styl z szarą ramką i szarym tekstem dla bazy lokalnej
            baza_badge_style = (
                "QLabel { font-size: 11px; font-weight: bold; color: #7f8c8d; "
                "padding: 1px 8px; border: 1px solid #bdc3c7; border-radius: 5px; }"
            )
        else:
            baza_txt = _("Baza Sieciowa")
            # Styl z pięknym niebieskim akcentem dla bazy sieciowej (Lux Style)
            baza_badge_style = (
                "QLabel { font-size: 11px; font-weight: bold; color: #2980b9; "
                "padding: 1px 8px; border: 1px solid #3498db; border-radius: 5px; }"
            )

        # --- 2. Pobieranie nazwy firmy z bazy ---
        nazwa_firmy = _("Brak nazwy firmy")

        if os.path.exists(config.DB_FILE):
            try:
                conn = sqlite3.connect(config.DB_FILE, timeout=5)
                c_tmp = conn.cursor()
                c_tmp.execute("SELECT nazwa FROM firma LIMIT 1")
                row = c_tmp.fetchone()
                conn.close()

                if row and row[0]:
                    nazwa_firmy = row[0]
                else:
                    nazwa_firmy = _("Firma (Brak nazwy w DB)")

            except sqlite3.Error:
                nazwa_firmy = _("Błąd odczytu bazy")
            except Exception:
                nazwa_firmy = _("Błąd systemu")
        else:
            nazwa_firmy = _("Plik bazy nie istnieje!")

        # --- 3. Aktualizacja widoku w stopce ---
        self.lbl_base_status.setStyleSheet(baza_badge_style)
        self.lbl_base_status.setText(f"📂 {baza_txt} | {nazwa_firmy}")


CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".SerwisApp", "config")
os.makedirs(CONFIG_DIR, exist_ok=True)
CONFIG_BAZA_FILE = os.path.join(CONFIG_DIR, "bazadir.json")
LOCAL_DB = config.DB_FILE

# Definicja katalogów docelowych w ~/.SerwisApp
logo_dir = os.path.dirname(config.DST_LOGO_FILE)

# Upewniamy się, że katalogi docelowe istnieją
os.makedirs(logo_dir, exist_ok=True)

logo_src = get_app_logo_path()
if not os.path.exists(config.DST_LOGO_FILE):
    if os.path.exists(logo_src):
        try:
            shutil.copy(logo_src, config.DST_LOGO_FILE)
        except Exception as e:
            print(f"Błąd kopiowania logo: {e}")

przewodnik_src = resource_path("resources/szablony/przewodnik.pdf")
przewodnik_dst = os.path.join(os.path.expanduser("~"), ".SerwisApp", "przewodnik.pdf")

if not os.path.exists(przewodnik_dst):
    if os.path.exists(przewodnik_src):
        try:
            shutil.copy(przewodnik_src, przewodnik_dst)
        except Exception as e:
            print(f"Błąd kopiowania przewodnik.pdf: {e}")

zapamietana_sciezka = wczytaj_baze(CONFIG_BAZA_FILE, LOCAL_DB)
config.DB_FILE = zapamietana_sciezka
conn, c = init_baza(CONFIG_BAZA_FILE, LOCAL_DB)

os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "0"
os.environ["QT_SCREEN_SCALE_FACTORS"] = "1"
os.environ["QT_SCALE_FACTOR"] = "1"
# W Qt6 nie ustawiamy już AA_DisableHighDpiScaling, bo atrybut jest zdeprecjonowany.
# Skalowanie trzymamy przez zmienne środowiskowe ustawione powyżej.

QtCore.QCoreApplication.setOrganizationName("SerwisApp")
QtCore.QCoreApplication.setApplicationName("serwis-app")

app = QtWidgets.QApplication(sys.argv)

app.setDesktopFileName("serwis-app")

translator = QTranslator()
locale_sys = QLocale.system().name()
qt_translations_path = QLibraryInfo.path(QLibraryInfo.TranslationsPath)
translator.load(f"qt_{locale_sys}", qt_translations_path)
app.installTranslator(translator)

startup_popup.show_startup_if_needed()

main_window = SerwisAppWindow()
ui = main_window.ui


#ui.pushButtonNew_ref.clicked.connect(lambda: odswiez_tabele_z_filtrami())

ui.actionDaneFirmy.triggered.connect(lambda: edytuj_dane_firmy(main_window, conn))

teraz = datetime.date.today()
obecny_rok = str(teraz.year)

current_date_filter = {
    "type": "year",
    "from": f"{obecny_rok}-01-01",
    "to": None
}

ui.pushButtonNew_filter.setText(obecny_rok)

app_icon = QIcon(get_app_icon_path())
main_window.setWindowTitle(f"SerwisApp")
main_window.setWindowIcon(app_icon)

app.setStyle("Fusion")

cfg = configparser.ConfigParser()
if os.path.exists(config.CONFIG_FILE):
    cfg.read(config.CONFIG_FILE, encoding="utf-8")

model = QStandardItemModel()
model.setHorizontalHeaderLabels([_("Numer"), _("Data"), _("Klient"), _("Telefon"), _("Sprzęt"), _("Nr seryjny"), _("Uwagi"), _("Status")])
ui.tableView.setModel(model)
ui.tableView.setSortingEnabled(True)

font = QtGui.QFont()
font.setPointSize(10)
ui.tableView.setFont(font)

header_font = QtGui.QFont()
header_font.setPointSize(10)
header_font.setBold(True)
ui.tableView.horizontalHeader().setFont(header_font)

header = ui.tableView.horizontalHeader()

for col in range(model.columnCount()):
    header.setSectionsClickable(col in [0, 1, 7])

header.setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.Interactive)
header.setMinimumSectionSize(90)

ui.tableView.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
ui.tableView.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
ui.tableView.verticalHeader().setVisible(False)

def get_real_id(index):
    """Zwraca wymagane dane lub ustawienia."""
    if not index.isValid():
        return None
    idx_col0 = index.sibling(index.row(), 0)
    item = ui.tableView.model().itemFromIndex(idx_col0)
    if item:
        real_id = item.data(QtCore.Qt.UserRole)
        if real_id:
            return int(real_id)
    try:
        txt = idx_col0.data()
        return int(str(txt).split('/')[0])
    except:
        return None

def pobierz_kontekst_zaznaczonego_zlecenia():
    """Zwraca ID i sformatowany numer aktualnie zaznaczonego zlecenia."""
    indexes = ui.tableView.selectionModel().selectedRows()
    if not indexes:
        return None, ""

    id_num = get_real_id(indexes[0])
    if not id_num:
        return None, ""

    cols = [col[1] for col in c.execute("PRAGMA table_info(zlecenia)").fetchall()]
    has_nr_roczny = "nr_roczny" in cols
    query = "SELECT data_zlecenia"
    if has_nr_roczny:
        query += ", nr_roczny"
    query += " FROM zlecenia WHERE id=?"
    row = c.execute(query, (id_num,)).fetchone()

    if not row:
        return id_num, str(id_num)

    data_zlecenia = row[0]
    nr_roczny = row[1] if has_nr_roczny and len(row) > 1 else None
    return id_num, formatuj_numer_zlecenia(id_num, data_zlecenia, nr_roczny)

def dodaj_uslugi_do_zaznaczonego_zlecenia(wybrane_uslugi):
    """Dopisuje usługi z cennika do zaznaczonego zlecenia."""
    id_num, _numer_zlecenia = pobierz_kontekst_zaznaczonego_zlecenia()
    if not id_num:
        QtWidgets.QMessageBox.warning(main_window, _("Uwaga"), _("Zaznacz zlecenie, do którego chcesz dodać usługę."))
        return False

    z = c.execute("SELECT * FROM zlecenia WHERE id=?", (id_num,)).fetchone()
    if not z:
        QtWidgets.QMessageBox.warning(main_window, _("Błąd"), _("Nie znaleziono zlecenia w bazie."))
        return False

    colnames = [desc[0] for desc in c.description]
    naprawa_val = z[colnames.index("naprawa_opis")] if "naprawa_opis" in colnames else ""
    koszt_us_val = z[colnames.index("koszt_uslugi")] if "koszt_uslugi" in colnames else 0.0
    nowa_naprawa, nowy_koszt = polacz_uslugi_z_naprawa(naprawa_val, koszt_us_val, wybrane_uslugi)

    c.execute(
        "UPDATE zlecenia SET naprawa_opis=?, koszt_uslugi=? WHERE id=?",
        (nowa_naprawa, nowy_koszt, id_num)
    )
    conn.commit()
    odswiez_tabele_z_filtrami()
    return True

def otworz_cennik():
    """Otwiera wspólne okno cennika."""
    id_num, numer_zlecenia = pobierz_kontekst_zaznaczonego_zlecenia()
    dialog = CennikDialog(
        parent=main_window,
        order_label=numer_zlecenia if id_num else "",
        service_apply_callback=dodaj_uslugi_do_zaznaczonego_zlecenia if id_num else None
    )
    dialog.exec()

def otworz_filtr_daty():
    """Otwiera wskazane okno lub akcję."""
    global current_date_filter
    dialog = DateFilterPopup(main_window, current_date_filter)
    pos = ui.pushButtonNew_filter.mapToGlobal(QtCore.QPoint(0, ui.pushButtonNew_filter.height()))
    dialog.move(pos)

    if dialog.exec():
        current_date_filter = dialog.get_filter_data()
        ui.pushButtonNew_filter.setText(dialog.get_label_text())
        odswiez_tabele_z_filtrami()

def odswiez_tabele_z_filtrami():
    """Odświeża dane lub widok interfejsu."""
    if ui.radioButton_all.isChecked(): status_filter = None
    elif ui.radioButton_end.isChecked(): status_filter = "Ukończone"
    elif ui.radioButton_new.isChecked(): status_filter = "Przyjęte"
    else: status_filter = None

    d_from = current_date_filter["from"]
    d_to = current_date_filter["to"]

    search_term = ui.lineEdit_szukajka.text().strip() or None

    odswiez_tabele(
        c, model, table_view=ui.tableView,
        status_filter=status_filter,
        search_term=search_term,
        date_from=d_from,
        date_to=d_to
    )

def otworz_szczegoly(index):
    """Otwiera wskazane okno lub akcję."""
    if not index.isValid():
        return
    pokaz_szczegoly(
        conn,
        c,
        index,
        model,
        parent=main_window,
        ui=ui,
        odswiez_funkcja=odswiez_tabele_z_filtrami
    )

def otworz_backup():
    """Otwiera wskazane okno lub akcję."""
    if main_window.backup_window:
        main_window.backup_window.raise_()
        main_window.backup_window.activateWindow()
        return

    backup_window = QtWidgets.QMainWindow(main_window)
    backup_window.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose, True)
    backup_window.setWindowIcon(QIcon(get_app_icon_path()))
    ui_backup = BackupUi()
    ui_backup.setupUi(backup_window)
    backup_window.destroyed.connect(lambda: setattr(main_window, "backup_window", None))
    main_window.backup_window = backup_window
    backup_window.show()

def otworz_klienci():
    """Otwiera wskazane okno lub akcję."""
    main_window.klienci_window = KlienciWindow(main_window, conn, model, ui)
    main_window.klienci_window.exec()
    main_window.klienci_window = None

def drukuj_wybrane_zlecenie():
    """Przygotowuje i wykonuje wydruk."""
    sel = ui.tableView.selectionModel().selectedIndexes()
    if not sel:
        QtWidgets.QMessageBox.warning(main_window, _("Uwaga"), _("Wybierz zlecenie do drukowania"))
        return
    id_num = get_real_id(sel[0])
    if not id_num:
        return
    z = c.execute("SELECT * FROM zlecenia WHERE id=?", (id_num,)).fetchone()
    if z:
        drukuj_zlecenie_html(z, main_window, c=c)

def usun_zlecenie():
    """Realizuje logikę operacji usun zlecenie."""
    indexes = ui.tableView.selectionModel().selectedRows()
    if not indexes:
        QtWidgets.QMessageBox.warning(main_window, _("Uwaga"), _("Zaznacz zlecenie do usunięcia"))
        return
    index = indexes[0]
    id_num = get_real_id(index)
    if not id_num:
        return

    # Pobieramy dane zlecenia
    z = c.execute("SELECT * FROM zlecenia WHERE id=?", (id_num,)).fetchone()
    if not z:
        return

    # --- NOWA BLOKADA: OCHRONA ZLECEŃ UKOŃCZONYCH ---
    from modules import password_protection  # Importujemy moduł uprawnień

    # 1. Pobieramy nazwy kolumn, żeby znaleźć indeks kolumny 'status'
    colnames = [d[0] for d in c.description]

    if "status" in colnames:
        status_val = z[colnames.index("status")] # Pobieramy wartość statusu

        # 2. Sprawdzamy: Czy status to "Ukończone" I czy użytkownik NIE jest adminem
        if status_val == "Ukończone" and not password_protection.CURRENT_USER_IS_SUPER:
            QtWidgets.QMessageBox.warning(
                main_window,
                _("Brak uprawnień"),
                _("Zlecenia o statusie 'Ukończone' mogą być usuwane tylko przez Administratora.")
            )
            return
    # ------------------------------------------------

    display_text = index.sibling(index.row(), 0).data()
    msg_box = QtWidgets.QMessageBox(main_window)
    msg_box.setWindowTitle(_("Potwierdzenie"))
    msg_box.setText(_("Czy na pewno usunąć zlecenie {}? Operacja jest nieodwracalna!").format(display_text))
    tak_button = msg_box.addButton(_("Tak"), QtWidgets.QMessageBox.ButtonRole.YesRole)
    anuluj_button = msg_box.addButton(_("Anuluj"), QtWidgets.QMessageBox.ButtonRole.RejectRole)
    msg_box.exec()

    if msg_box.clickedButton() == tak_button:
        c.execute("DELETE FROM zlecenia WHERE id=?", (id_num,))
        conn.commit()
        odswiez_tabele_z_filtrami()

def zmien_status(conn, c, model, ui, parent=None):
    """Realizuje logikę operacji zmien status."""
    indexes = ui.tableView.selectionModel().selectedRows()
    if not indexes:
        QtWidgets.QMessageBox.warning(parent, _("Uwaga"), _("Zaznacz zlecenie do zmiany statusu!"))
        return
    index = indexes[0]
    id_num = get_real_id(index)
    if not id_num:
        return
    z = c.execute("SELECT * FROM zlecenia WHERE id=?", (id_num,)).fetchone()
    if not z:
        QtWidgets.QMessageBox.warning(parent, _("Uwaga"), _("Nie znaleziono zlecenia w bazie"))
        return
    current_status = z[7] if len(z) > 7 else "Przyjęte"
    if current_status in ("Zakończone", "Ukończone"):
        QtWidgets.QMessageBox.information(parent, _("Blokada"), _("Nie można zmienić statusu zakończonego zlecenia."))
        return
    msg = QtWidgets.QMessageBox(parent)
    msg.setWindowTitle(_("Zakończ zlecenie"))
    msg.setText(_("Czy na pewno chcesz zakończyć zlecenie?"))
    msg.setIcon(QtWidgets.QMessageBox.Icon.Question)
    ok_btn = msg.addButton(_("Zakończone"), QtWidgets.QMessageBox.ButtonRole.AcceptRole)
    cancel_btn = msg.addButton(_("Anuluj"), QtWidgets.QMessageBox.ButtonRole.RejectRole)
    msg.exec()
    if msg.clickedButton() != ok_btn:
        return
    def show_repair_details_dialog(existing_naprawa="", existing_cz=None, existing_us=None):
        """Wyświetla odpowiednie dane lub okno."""
        dialog = QtWidgets.QDialog(parent)
        dialog.setWindowTitle(_("Szczegóły naprawy"))
        layout = QtWidgets.QFormLayout(dialog)
        naprawa_edit = QtWidgets.QTextEdit(existing_naprawa or "")
        naprawa_edit.setFixedHeight(120)
        naprawa_edit.setTabChangesFocus(True)
        koszt_czesci_edit = QtWidgets.QLineEdit(str(existing_cz) if existing_cz is not None else "")
        koszt_uslugi_edit = QtWidgets.QLineEdit(str(existing_us) if existing_us is not None else "")
        layout.addRow(_("Opis naprawy:"), naprawa_edit)
        layout.addRow(_("Koszt części:"), koszt_czesci_edit)
        layout.addRow(_("Koszt usługi:"), koszt_uslugi_edit)
        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.StandardButton.Ok | QtWidgets.QDialogButtonBox.StandardButton.Cancel)
        layout.addWidget(buttons)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        result = dialog.exec()
        if result == QtWidgets.QDialog.DialogCode.Accepted:
            naprawa_text = naprawa_edit.toPlainText().strip()
            try: koszt_cz_val = float(koszt_czesci_edit.text()) if koszt_czesci_edit.text() else None
            except ValueError: koszt_cz_val = None
            try: koszt_us_val = float(koszt_uslugi_edit.text()) if koszt_uslugi_edit.text() else None
            except ValueError: koszt_us_val = None
            return True, naprawa_text, koszt_cz_val, koszt_us_val
        return False, None, None, None
    naprawa_existing = z[10] if len(z) > 10 else ""
    koszt_cz_existing = z[11] if len(z) > 11 else None
    koszt_us_existing = z[12] if len(z) > 12 else None
    if not naprawa_existing:
        msg2 = QtWidgets.QMessageBox(parent)
        msg2.setWindowTitle(_("Brak danych naprawy"))
        msg2.setText(_("Nie ma opisu naprawy. Chcesz dodać szczegóły naprawy teraz?"))
        msg2.setIcon(QtWidgets.QMessageBox.Icon.Question)
        yes_btn = msg2.addButton(_("Tak"), QtWidgets.QMessageBox.ButtonRole.YesRole)
        no_btn = msg2.addButton(_("Nie"), QtWidgets.QMessageBox.ButtonRole.NoRole)
        msg2.exec()
        if msg2.clickedButton() == yes_btn:
            ok2, naprawa_text, koszt_cz_val, koszt_us_val = show_repair_details_dialog(existing_naprawa="", existing_cz=koszt_cz_existing, existing_us=koszt_us_existing)
            if not ok2: return
            c.execute("UPDATE zlecenia SET status=?, naprawa_opis=?, koszt_czesci=?, koszt_uslugi=? WHERE id=?", ("Ukończone", naprawa_text, koszt_cz_val, koszt_us_val, id_num))
            conn.commit()
        else:
            c.execute("UPDATE zlecenia SET status=? WHERE id=?", ("Ukończone", id_num))
            conn.commit()
    else:
        c.execute("UPDATE zlecenia SET status=? WHERE id=?", ("Ukończone", id_num))
        conn.commit()
    msg_print = QtWidgets.QMessageBox(parent)
    msg_print.setWindowTitle(_("Drukuj raport"))
    msg_print.setText(_("Status ustawiony na 'Ukończone'. Czy chcesz wydrukować raport dla klienta teraz?"))
    msg_print.setIcon(QtWidgets.QMessageBox.Icon.Question)
    yes_btn = msg_print.addButton(_("Tak"), QtWidgets.QMessageBox.ButtonRole.YesRole)
    no_btn = msg_print.addButton(_("Nie"), QtWidgets.QMessageBox.ButtonRole.NoRole)
    msg_print.exec()
    if msg_print.clickedButton() == yes_btn:
        z_new = c.execute("SELECT * FROM zlecenia WHERE id=?", (id_num,)).fetchone()
        if z_new: drukuj_zlecenie_html(z_new, parent, c=c)
        QtWidgets.QMessageBox.information(parent, _("Sukces"), _("Status ustawiony na 'Zakończone' i zapisano szczegóły naprawy."))
    odswiez_tabele_z_filtrami()

def zapisz_stan_i_motyw():
    """Zapisuje dane lub ustawienia."""
    cfg = configparser.ConfigParser()
    if os.path.exists(config.CONFIG_FILE): cfg.read(config.CONFIG_FILE, encoding="utf-8")
    if "WINDOW" not in cfg: cfg["WINDOW"] = {}
    if main_window.isMaximized(): cfg["WINDOW"]["maximized"] = "True"
    else:
        cfg["WINDOW"]["maximized"] = "False"
        geom = main_window.geometry()
        cfg["WINDOW"]["x"] = str(geom.x())
        cfg["WINDOW"]["y"] = str(geom.y())
        cfg["WINDOW"]["width"] = str(geom.width())
        cfg["WINDOW"]["height"] = str(geom.height())
    if "COLUMNS" not in cfg: cfg["COLUMNS"] = {}
    for col in range(ui.tableView.model().columnCount()): cfg["COLUMNS"][f"col{col}"] = str(ui.tableView.columnWidth(col))
    if "FILTER" not in cfg: cfg["FILTER"] = {}
    if ui.radioButton_new.isChecked(): cfg["FILTER"]["ostatni"] = "Przyjęte"
    elif ui.radioButton_end.isChecked(): cfg["FILTER"]["ostatni"] = "Ukończone"
    else: cfg["FILTER"]["ostatni"] = "Wszystkie"
    with open(config.CONFIG_FILE, "w", encoding="utf-8") as f: cfg.write(f)

def pokaz_menu_kontekstowe(pos):
    """Wyświetla wskazane dane lub okno."""
    index = ui.tableView.indexAt(pos)
    if not index.isValid(): return

    selected_rows = ui.tableView.selectionModel().selectedRows()
    if not selected_rows:
        QtWidgets.QMessageBox.warning(main_window, _("Uwaga"), _("Zaznacz zlecenie do zmiany statusu!"))
        return

    row_index = selected_rows[0]
    id_num = get_real_id(row_index)
    if not id_num: return

    menu = QtWidgets.QMenu()

    kopiuj = menu.addAction(_("Kopiuj komórkę"))
    kopiuj.setIcon(QtGui.QIcon(resource_path("actions/kopiuj.png")))
    drukuj_zlecenie = menu.addAction(_("Drukuj zlecenie"))
    drukuj_zlecenie.setIcon(QtGui.QIcon(resource_path("actions/drukuj.png")))
    popraw_zlecenie = menu.addAction(_("Edytuj zlecenie/naprawę"))
    popraw_zlecenie.setIcon(QtGui.QIcon(resource_path("actions/edit.png")))
    zmien_status_action = menu.addAction(_("Zakończ zlecenie"))
    zmien_status_action.setIcon(QtGui.QIcon(resource_path("actions/zakoncz.png")))
    usun_zlecenie_action = menu.addAction(_("Usuń zlecenie"))
    usun_zlecenie_action.setIcon(QtGui.QIcon(resource_path("actions/usun.png")))
    duplikuj_zlecenie_action = menu.addAction(_("Duplikuj zlecenie"))
    duplikuj_zlecenie_action.setIcon(QtGui.QIcon(resource_path("actions/duplikuj.png")))
    wyslij_email_action = menu.addAction(_("Wyślij Email Do Klienta"))
    wyslij_email_action.setIcon(QtGui.QIcon(resource_path("actions/mail.png")))
    wyslij_sms_action = menu.addAction(_("Wyślij SMS Do Klienta"))
    wyslij_sms_action.setIcon(QtGui.QIcon(resource_path("actions/sms.png")))

    action = menu.exec(ui.tableView.viewport().mapToGlobal(pos))

    if action == kopiuj:
        QtWidgets.QApplication.clipboard().setText(str(index.data()))
    elif action == drukuj_zlecenie:
        z = c.execute("SELECT * FROM zlecenia WHERE id=?", (id_num,)).fetchone()
        if z:
            if z[7] == "Ukończone":
                msg = QtWidgets.QMessageBox(main_window)
                msg.setWindowTitle(_("Wybierz typ wydruku"))
                msg.setText(_("Zlecenie jest ukończone.\nCo chcesz wydrukować?"))
                wzorzec_btn = msg.addButton(_("Zlecenie"), QtWidgets.QMessageBox.ButtonRole.AcceptRole)
                raport_btn = msg.addButton(_("Raport"), QtWidgets.QMessageBox.ButtonRole.AcceptRole)
                anuluj_btn = msg.addButton(_("Anuluj"), QtWidgets.QMessageBox.ButtonRole.RejectRole)
                msg.setIcon(QtWidgets.QMessageBox.Icon.Question)
                msg.exec()
                if msg.clickedButton() == wzorzec_btn:
                    drukuj_zlecenie_html(z, main_window, tryb="wzorzec", c=c)
                elif msg.clickedButton() == raport_btn:
                    drukuj_zlecenie_html(z, main_window, tryb="raport", c=c)
            else:
                drukuj_zlecenie_html(z, main_window, c=c)
    elif action == popraw_zlecenie:
        popraw_dane(conn, c, model, ui, parent=main_window)
    elif action == zmien_status_action:
        zmien_status(conn, c, model, ui, parent=main_window)
    elif action == usun_zlecenie_action:
        usun_zlecenie()
    elif action == wyslij_email_action:
        try:
            cols = [col[1] for col in c.execute("PRAGMA table_info(zlecenia)").fetchall()]
            has_nr_roczny = "nr_roczny" in cols
            query = "SELECT sprzet, data_zlecenia, email"
            if has_nr_roczny: query += ", nr_roczny"
            query += " FROM zlecenia WHERE id=?"
            z = c.execute(query, (id_num,)).fetchone()
            if not z or not z[2]:
                QtWidgets.QMessageBox.warning(main_window, _("Uwaga"), _("Brak e-maila dla tego klienta!"))
                return
            sprzet = z[0]
            data_zlecenia = z[1]
            email_klienta = z[2]
            nr_roczny = z[3] if has_nr_roczny else None
            nr_zlecenia_str = formatuj_numer_zlecenia(id_num, data_zlecenia, nr_roczny)
            firma = c.execute("SELECT nazwa, adres, telefon, email, nip, godziny_otwarcia FROM firma WHERE id=1").fetchone()
            if firma:
                template = _("Pozdrawiamy,\n{nazwa}\n{adres}\nTel: {telefon}\nEmail: {email}\nNIP: {nip}\nGodziny otwarcia: {godziny}")
                dane_firmy = template.format(nazwa=firma[0], adres=firma[1], telefon=firma[2], email=firma[3], nip=firma[4], godziny=firma[5])
            else:
                dane_firmy = _("Pozdrawiamy,\nSerwisApp")
            odswiez_tabele_z_filtrami()
            from modules.mail import MailClient
            main_window.mail_okno = MailClient(email_klienta, nr_zlecenia_str, sprzet, dane_firmy)
            main_window.mail_okno.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose, True)
            main_window.mail_okno.destroyed.connect(lambda: setattr(main_window, "mail_okno", None))
            main_window.mail_okno.show()
        except Exception as e:
            QtWidgets.QMessageBox.critical(main_window, _("Błąd"), f"Błąd przygotowania maila: {e}")
    elif action == duplikuj_zlecenie_action:
        z = c.execute("SELECT imie_nazwisko, telefon, email, sprzet, nr_seryjny FROM zlecenia WHERE id=?", (id_num,)).fetchone()
        if not z:
            QtWidgets.QMessageBox.warning(main_window, _("Błąd"), _("Nie znaleziono zlecenia w bazie"))
            return
        prefill = {_("Imię i nazwisko"): z[0], _("Telefon"): z[1], _("E-mail"): z[2], _("Sprzęt"): z[3], _("Nr seryjny"): z[4]}
        dodaj_zlecenie(conn, c, model, ui, parent=main_window, prefill=prefill)

    elif action == wyslij_sms_action:
        # Pobieramy dane potrzebne do SMS
        # Pobieramy też nr_roczny i data_zlecenia do ładnego numeru
        cols = [col[1] for col in c.execute("PRAGMA table_info(zlecenia)").fetchall()]
        has_nr_roczny = "nr_roczny" in cols

        query = "SELECT sprzet, telefon, data_zlecenia, id"
        if has_nr_roczny: query += ", nr_roczny"
        query += " FROM zlecenia WHERE id=?"

        z = c.execute(query, (id_num,)).fetchone()

        if not z: return

        sprzet = z[0]
        telefon = z[1]
        data_zlecenia = z[2]
        real_id = z[3]
        nr_roczny = z[4] if has_nr_roczny else None

        if not telefon:
            QtWidgets.QMessageBox.warning(main_window, _("Uwaga"), _("Brak numeru telefonu w zleceniu!"))
            return

        # Formatowanie numeru zlecenia (używając twojej funkcji utils)
        nr_zlecenia_str = formatuj_numer_zlecenia(real_id, data_zlecenia, nr_roczny)

        # Otwarcie okna SMS
        main_window.sms_okno = SMSClient(telefon, nr_zlecenia_str, sprzet)
        main_window.sms_okno.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose, True)
        main_window.sms_okno.destroyed.connect(lambda: setattr(main_window, "sms_okno", None))
        main_window.sms_okno.show()

ui.tableView.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
ui.tableView.customContextMenuRequested.connect(pokaz_menu_kontekstowe)

ui.tableView.selectionModel().selectionChanged.connect(lambda selected, deselected: pokaz_szczegoly_w_labelach(ui, c, selected, deselected))

ui.actionPokazCennik.triggered.connect(otworz_cennik)
ui.radioButton_all.toggled.connect(lambda: odswiez_tabele_z_filtrami())
ui.radioButton_end.toggled.connect(lambda: odswiez_tabele_z_filtrami())
ui.radioButton_new.toggled.connect(lambda: odswiez_tabele_z_filtrami())
ui.pushButtonNew_filter.clicked.connect(otworz_filtr_daty)
ui.lineEdit_szukajka.textChanged.connect(lambda: odswiez_tabele_z_filtrami())
QtCore.QTimer.singleShot(0, lambda: odswiez_tabele_z_filtrami())

ostatni_filtr = wczytaj_filtr(config.CONFIG_FILE)
if ostatni_filtr == "Przyjęte": ui.radioButton_new.setChecked(True)
elif ostatni_filtr == "Ukończone": ui.radioButton_end.setChecked(True)
else: ui.radioButton_all.setChecked(True)

ui.pushButtonNew_new.clicked.connect(lambda: dodaj_zlecenie(conn, c, model, ui=ui, parent=main_window))
ui.pushButtonNew_end.clicked.connect(lambda: zmien_status(conn, c, model, ui, parent=main_window))
ui.pushButtonNew_popdane.clicked.connect(lambda: popraw_dane(conn, c, model, ui=ui, parent=main_window, odswiez_funkcja=odswiez_tabele_z_filtrami))
ui.tableView.doubleClicked.connect(otworz_szczegoly)
ui.pushButtonNew_backup.clicked.connect(otworz_backup)
ui.pushButtonNew_print.clicked.connect(drukuj_wybrane_zlecenie)
ui.pushButtonNew_del.clicked.connect(usun_zlecenie)
ui.pushButtonNew_clients.clicked.connect(otworz_klienci)
def on_baza_clicked():
    """Obsługuje zmianę stanu lub zdarzenie interfejsu."""
    global conn, c

    # 1. Wywołanie dialogu wyboru bazy
    # Upewniamy się, że przekazujemy 'main_window' jako parent
    db_file_path = wybierz_baze_dialog(main_window, CONFIG_BAZA_FILE, LOCAL_DB)

    if db_file_path is None:
        return # Użytkownik anulował wybór

    # 2. Zamknięcie starego połączenia
    try:
        conn.close()
    except Exception as e:
        print(f"Błąd zamykania starego połączenia: {e}")

    # 3. Aktualizacja konfiguracji globalnej
    from setup import config
    config.DB_FILE = db_file_path

    # 4. Nowe połączenie z wybraną bazą
    try:
        conn = sqlite3.connect(db_file_path)
        c = conn.cursor()
    except Exception as e:
        QtWidgets.QMessageBox.critical(main_window, _("Błąd"), f"Nie udało się połączyć z bazą:\n{e}")
        return

    # 5. Odświeżenie widoku tabeli
    odswiez_tabele_z_filtrami()

    # 6. NOWE: Odświeżenie naszej nowej stopki w oknie głównym!
    main_window.update_plus_status()

ui.pushButtonNew_baza.clicked.connect(on_baza_clicked)

app.setWindowIcon(app_icon)
main_window.show()

_cleanup_done = False

def cleanup_before_exit():
    """Domyka zasoby przed zakończeniem procesu."""
    global _cleanup_done, conn, c
    if _cleanup_done:
        return
    _cleanup_done = True

    try:
        if hasattr(main_window, "date_timer") and main_window.date_timer.isActive():
            main_window.date_timer.stop()
    except Exception:
        pass

    for attr_name in ("mail_okno", "sms_okno", "backup_window", "klienci_window"):
        widget = getattr(main_window, attr_name, None)
        if not widget:
            continue
        try:
            widget.close()
        except Exception:
            pass
        try:
            widget.deleteLater()
        except Exception:
            pass
        setattr(main_window, attr_name, None)

    try:
        ui.tableView.setModel(None)
    except Exception:
        pass

    try:
        conn.commit()
    except Exception:
        pass

    try:
        conn.close()
    except Exception:
        pass

    conn = None
    c = None

app.aboutToQuit.connect(cleanup_before_exit)

exit_code = app.exec()
cleanup_before_exit()

try:
    sys.stdout.flush()
    sys.stderr.flush()
except Exception:
    pass

# Workaround na sporadyczny crash PySide/Qt przy teardown interpretera.
os._exit(int(exit_code))
