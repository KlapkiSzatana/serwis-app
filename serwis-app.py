import configparser
import datetime
import os
import shutil
import sqlite3
import sys
import gettext
import locale

app_id = "serwis-app"

basedir = os.path.dirname(__file__)
icon_path = os.path.join(basedir, "serwisapp.png")

# --- 1. USTALANIE ŚCIEŻKI BAZOWEJ (Wersja pod ONEDIR) ---
if getattr(sys, 'frozen', False):
    # W trybie --onedir ścieżka bazowa to katalog, w którym leży plik .exe
    base_path = os.path.dirname(sys.executable)
else:
    # W trybie deweloperskim (uruchamianie z pliku .py)
    base_path = os.path.dirname(os.path.abspath(__file__))

locales_dir = os.path.join(base_path, 'locales')

# --- 2. JĘZYK SYSTEMU ---
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

# --- 3. INICJALIZACJA TŁUMACZEŃ ---
_ = lambda s: s

try:
    t = gettext.translation('messages', localedir=locales_dir, languages=[lang])
    t.install()
    _ = t.gettext
except FileNotFoundError:
    # Opcjonalnie: odkomentuj print poniżej, aby widzieć w konsoli czy folder został znaleziony
    # print(f"Nie znaleziono tłumaczeń w: {locales_dir}")
    pass
except Exception as e:
    print(f"Błąd ładowania tłumaczeń: {e}")

from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtGui import QShortcut, QKeySequence, QIcon, QStandardItemModel
from PySide6.QtCore import QTranslator, QLocale, QLibraryInfo, QTimer, QDate
from PySide6.QtWidgets import QMainWindow

from setup import config
from modules.backup import Ui_MainWindow as BackupUi, wykonaj_backup_logika
from modules.button import MyPushButton
from modules.drukowanie import drukuj_zlecenie_html
from modules.odswiez_tabele import odswiez_tabele
# Importujemy nowe funkcje: menedżera i sprawdzanie przy starcie
from modules.password_protection import sprawdz_haslo_przy_starcie
from modules.zlecenia import (
    dodaj_zlecenie, pokaz_szczegoly, popraw_dane
)
from modules import startup_popup
from ui.ui_main import Ui_MainWindow
from modules.utils import resource_path, formatuj_numer_zlecenia
from modules.baza import init_baza, wybierz_baze_dialog, zapisz_filtr, wczytaj_filtr, wczytaj_baze
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


CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".SerwisApp", "config")
os.makedirs(CONFIG_DIR, exist_ok=True)
CONFIG_BAZA_FILE = os.path.join(CONFIG_DIR, "bazadir.json")
LOCAL_DB = config.DB_FILE

# Definicja katalogów docelowych w ~/.SerwisApp
logo_dir = os.path.dirname(config.DST_LOGO_FILE)

# Upewniamy się, że katalogi docelowe istnieją
os.makedirs(logo_dir, exist_ok=True)

# 3. Kopiowanie logo
logo_src = resource_path("resources/logo/serwisapp.png")
if not os.path.exists(config.DST_LOGO_FILE):
    if os.path.exists(logo_src):
        try:
            shutil.copy(logo_src, config.DST_LOGO_FILE)
        except Exception as e:
            print(f"Błąd kopiowania logo: {e}")

# 4. Kopiowanie przewodnik.pdf
przewodnik_src = resource_path("resources/szablony/przewodnik.pdf")
# Budujemy ścieżkę docelową do głównego katalogu .SerwisApp
przewodnik_dst = os.path.join(os.path.expanduser("~"), ".SerwisApp", "przewodnik.pdf")

if not os.path.exists(przewodnik_dst):
    if os.path.exists(przewodnik_src):
        try:
            shutil.copy(przewodnik_src, przewodnik_dst)
        except Exception as e:
            print(f"Błąd kopiowania przewodnik.pdf: {e}")

# --- INICJALIZACJA BAZY DANYCH ---

# 1. Najpierw wczytujemy zapamiętaną ścieżkę z pliku JSON
zapamietana_sciezka = wczytaj_baze(CONFIG_BAZA_FILE, LOCAL_DB)

# 2. Aktualizujemy globalną konfigurację, żeby status bar wiedział, co pokazać
config.DB_FILE = zapamietana_sciezka  # <--- WAŻNE: Aktualizacja zmiennej globalnej

# 3. Inicjalizujemy połączenie
conn, c = init_baza(CONFIG_BAZA_FILE, LOCAL_DB)

# --- START APLIKACJI ---
# 1. Ustawienia skalowania (zawsze przed QApplication)
os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "0"
os.environ["QT_SCREEN_SCALE_FACTORS"] = "1"
os.environ["QT_SCALE_FACTOR"] = "1"
QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_DisableHighDpiScaling)

# 2. Wymuszenie nazw dla systemów Linux (przed stworzeniem app)
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

shortcut_refresh = QShortcut(QKeySequence("F5"), main_window)
shortcut_insert = QShortcut(QKeySequence("Insert"), main_window)
shortcut_insert.activated.connect(ui.pushButtonNew_new.click)
shortcut_delete = QShortcut(QKeySequence("Delete"), main_window)
shortcut_delete.activated.connect(ui.pushButtonNew_del.click)
shortcut_ctrl_p = QShortcut(QKeySequence("Ctrl+P"), main_window)
shortcut_ctrl_p.activated.connect(ui.pushButtonNew_print.click)
shortcut_refresh.activated.connect(lambda: odswiez_tabele_z_filtrami())
shortcut_enter = QShortcut(QKeySequence("Return"), main_window)
shortcut_enter.activated.connect(lambda: pokaz_szczegoly(conn, c, ui.tableView.selectionModel().currentIndex(), ui.tableView.model()))
ui.pushButtonNew_ref.clicked.connect(lambda: odswiez_tabele_z_filtrami())
main_window.show()

ui.actionDaneFirmy.triggered.connect(lambda: edytuj_dane_firmy(main_window, conn))

# 1. Pobieramy aktualny rok
teraz = datetime.date.today()
obecny_rok = str(teraz.year)

# 2. Ustawiamy domyślny filtr w strukturze danych
current_date_filter = {
    "type": "year",
    "from": f"{obecny_rok}-01-01",
    "to": None
}

ui.pushButtonNew_filter.setText(obecny_rok)

main_window.setWindowTitle(f"SerwisApp - {config.APP_VERSION} {config.APP_NAME}")
main_window.setWindowIcon(QIcon(resource_path("resources/logo/icon.png")))

def replace_buttons_with_mypushbutton(ui):
    """Realizuje logikę operacji replace buttons with mypushbutton."""
    from modules.button import MyPushButton
    button_names = [
        "pushButtonNew_new", "pushButtonNew_popdane", "pushButtonNew_del",
        "pushButtonNew_print", "pushButtonNew_end", "pushButtonNew_tryb",
        "pushButtonNew_popfir", "pushButtonNew_backup", "pushButtonNew_baza",
        "pushButtonNew_ref", "pushButtonNew_filter", "pushButtonNew_clients",
    ]
    for name in button_names:
        old_btn = getattr(ui, name, None)
        if old_btn is None: continue
        parent = old_btn.parent()
        text = old_btn.text()
        geom = old_btn.geometry()
        new_btn = MyPushButton(text=text, parent=parent)
        new_btn.setGeometry(geom)
        try: old_btn.clicked.connect(new_btn.clicked)
        except Exception: pass
        setattr(ui, name, new_btn)

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

def ustaw_filtr(filtr):
    """Realizuje logikę operacji ustaw filtr."""
    zapisz_filtr(filtr)
    if filtr == "Przyjęte": odswiez_tabele(c, model, status_filter="Przyjęte")
    elif filtr == "Ukończone": odswiez_tabele(c, model, status_filter="Ukończone")
    else: odswiez_tabele(c, model, status_filter=None)

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
    global backup_window
    backup_window = QtWidgets.QMainWindow()
    ui_backup = BackupUi()
    ui_backup.setupUi(backup_window)
    backup_window.show()

def otworz_klienci():
    """Otwiera wskazane okno lub akcję."""
    global klienci_window
    klienci_window = KlienciWindow(main_window, conn, model, ui)
    klienci_window.exec()

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
        main_window.sms_okno.show()

ui.tableView.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
ui.tableView.customContextMenuRequested.connect(pokaz_menu_kontekstowe)

ui.tableView.selectionModel().selectionChanged.connect(lambda selected, deselected: pokaz_szczegoly_w_labelach(ui, c, selected, deselected))

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
    global conn, c, db_file_path

    # 1. Wywołanie dialogu wyboru
    db_file_path = wybierz_baze_dialog(main_window, CONFIG_BAZA_FILE, LOCAL_DB)

    if db_file_path is None:
        return

    # 2. Zamknięcie starego połączenia
    try:
        conn.close()
    except Exception:
        pass

    # 3. Aktualizacja konfiguracji globalnej (KLUCZOWE DLA ODŚWIEŻANIA STATUSU)
    config.DB_FILE = db_file_path

    # 4. Nowe połączenie
    conn = sqlite3.connect(db_file_path)
    c = conn.cursor()

    # 5. Odświeżenie widoku tabeli
    odswiez_tabele(c, model, status_filter=None)

    ui.update_plus_status()

# Obliczamy rok
curr_year = datetime.date.today().year
year_str = f"2025-{curr_year}" if curr_year > 2025 else "2025"

copyright_label = QtWidgets.QLabel(f"© KlapkiSzatana {year_str}")
font = QtGui.QFont()
font.setPointSize(8)
font.setBold(False)
copyright_label.setFont(font)
copyright_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
ui.statusbar.addPermanentWidget(copyright_label)

ui.pushButtonNew_baza.clicked.connect(on_baza_clicked)

app.setWindowIcon(QIcon(icon_path))
main_window.show()
sys.exit(app.exec())
