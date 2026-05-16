import sys
import os
from setup import config
import sqlite3
from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import QApplication
from modules.button import MyPushButton
from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from modules.pomoc import pokaz_wsparcie
from modules.pokaz_info import pokaz_info_o_programie
from modules.smtp_store import load_smtp, save_smtp
from modules.password_protection import menedzer_hasel
from modules.utils import get_app_icon_path, get_app_logo_path, resource_path
from modules.raport import RaportDialog, RaportTopSprzetDialog, RaportTopNaprawyDialog
from modules.drukowanie import edytuj_szablon
from modules.sms import SMSConfigDialog

try:
    _("Test")
except NameError:
    def _(text):
        return text


CONFIG_FILE = getattr(config, "CONFIG_FILE", "config.ini")

def get_detailed_os_info():
    """Zwraca czytelny dla człowieka opis systemu operacyjnego wraz z wersją jądra."""
    try:
        sys_platform = sys.platform

        # --- 1. WINDOWS ---
        if sys_platform == "win32":
            win_release = platform.release() # np. "10" lub "11"
            win_version = platform.version() # np. "10.0.22631"
            return f"Windows {win_release} (Wersja: {win_version}, Jądro: NT)"

        # --- 2. MACOS (DARWIN) ---
        elif sys_platform == "darwin":
            mac_ver = platform.mac_ver()[0] # np. "14.4"
            kernel_ver = platform.release() # np. "23.4.0"
            return f"macOS {mac_ver} (Jądro: Darwin {kernel_ver})"

        # --- 3. LINUX (Arch, Ubuntu itp.) ---
        elif sys_platform.startswith("linux"):
            # Próbujemy odczytać dane z /etc/os-release (standard na nowoczesnych dystrybucjach)
            dist_name = "Linux"
            if os.path.exists("/etc/os-release"):
                with open("/etc/os-release", "r", encoding="utf-8") as f:
                    lines = f.readlines()
                    info = {}
                    for line in lines:
                        if "=" in line:
                            k, v = line.strip().split("=", 1)
                            info[k] = v.strip('"')
                    # Próbujemy wyciągnąć 'PRETTY_NAME' (np. "Arch Linux" lub "Ubuntu 22.04.4 LTS")
                    dist_name = info.get("PRETTY_NAME", info.get("NAME", "Linux"))

            kernel_ver = platform.release() # np. "6.12.1-arch1-1"
            return f"{dist_name} (Jądro: Linux {kernel_ver})"

    except Exception as e:
        # Fallback w razie jakichkolwiek problemów z uprawnieniami / odczytem
        return f"{platform.system()} {platform.release()} (Błąd detekcji: {str(e)})"

    return f"{platform.system()} {platform.release()}"

import urllib.parse
import platform
import subprocess

class BugReportDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(_("Zgłoś błąd lub sugestię"))
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)

        layout = QtWidgets.QVBoxLayout(self)

        # 1. Opis działania
        info_label = QtWidgets.QLabel(
            _("Opisz krótko napotkany problem lub swoją sugestię.<br>"
              "Po kliknięciu 'Zgłoś na GitHub' zostaniesz przekierowany do przeglądarki, "
              "gdzie zgłoszenie zostanie automatycznie przygotowane.")
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        layout.addSpacing(10)

        # 2. Tytuł zgłoszenia
        layout.addWidget(QtWidgets.QLabel(_("Krótki tytuł zgłoszenia:")))
        self.title_input = QtWidgets.QLineEdit(self)
        self.title_input.setPlaceholderText(_("np. Błąd przy generowaniu PDF, Sugestia dotycząca tabeli"))
        layout.addWidget(self.title_input)
        layout.addSpacing(10)

        # 3. Opis szczegółowy
        layout.addWidget(QtWidgets.QLabel(_("Szczegółowy opis (co robiłeś, co poszło nie tak):")))
        self.desc_input = QtWidgets.QTextEdit(self)
        self.desc_input.setPlaceholderText(_("Wpisz tutaj jak najwięcej szczegółów..."))
        layout.addWidget(self.desc_input)
        layout.addSpacing(15)

        # 4. Przyciski z Twoim Lux Style
        btn_layout = QtWidgets.QHBoxLayout()
        self.btn_cancel = QtWidgets.QPushButton(_("Anuluj"), self)
        self.btn_send = QtWidgets.QPushButton(_("Zgłoś na GitHub"), self)
        self.btn_send.setDefault(True)

        # Styl przycisku zgłoszenia (Twoje kolory: niebieski z ramką, wypełnienie na hover)
        self.btn_send.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #2980b9;
                border: 1px solid #3498db;
                border-radius: 4px;
                padding: 6px 15px;
                font-weight: bold;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #2980b9;
                color: #ffffff;
            }
            QPushButton:pressed {
                background-color: #1f618d;
                border-color: #1f618d;
                color: #ffffff;
            }
        """)

        # Styl przycisku anulowania
        self.btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #7f8c8d;
                border: 1px solid #bdc3c7;
                border-radius: 4px;
                padding: 6px 15px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #7f8c8d;
                color: #ffffff;
            }
            QPushButton:pressed {
                background-color: #616a6b;
                border-color: #616a6b;
                color: #ffffff;
            }
        """)

        self.btn_cancel.clicked.connect(self.reject)
        self.btn_send.clicked.connect(self.send_to_github)

        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_send)
        layout.addLayout(btn_layout)

    def send_to_github(self):
        title = self.title_input.text().strip()
        description = self.desc_input.toPlainText().strip()

        if not title:
            title = "Zgłoszenie błędu"

        # --- UŻYCIE NOWEJ, SZCZEGÓŁOWEJ DETEKCJI ---
        os_info = get_detailed_os_info()
        arch_info = platform.machine() # np. "AMD64" lub "x86_64"
        python_ver = platform.python_version()

        try:
            from setup.config import APP_VERSION
            app_version = APP_VERSION
        except ImportError:
            app_version = "1.0.0"

        # Szablon zgłoszenia błędu dla repozytorium SerwisApp
        github_body = (
            f"### Opis problemu\n"
            f"{description}\n\n"
            f"--- \n"
            f"### Środowisko uruchomieniowe\n"
            f"- **Wersja aplikacji:** {app_version}\n"
            f"- **System operacyjny:** {os_info}\n"
            f"- **Architektura:** {arch_info}\n"
            f"- **Wersja Pythona:** {python_ver}\n"
        )

        encoded_title = urllib.parse.quote(title)
        encoded_body = urllib.parse.quote(github_body)

        # Link kierujący do Twojego repozytorium SerwisApp
        github_url = (
            f"https://github.com/KlapkiSzatana/serwis-app/issues/new"
            f"?title={encoded_title}"
            f"&body={encoded_body}"
        )

        # Wywołanie systemowe otwarcia URL (zachowaj swój dotychczasowy kod otwierający przeglądarkę)
        if os.name == 'nt':
            try:
                os.startfile(github_url)
            except Exception:
                subprocess.Popen(['cmd', '/c', 'start', '', github_url], shell=True)
        else:
            env = dict(os.environ)
            env.pop('LD_LIBRARY_PATH', None)
            env.pop('QT_PLUGIN_PATH', None)
            env.pop('QT_QPA_PLATFORM_PLUGIN_PATH', None)

            opener = 'open' if sys.platform == 'darwin' else 'xdg-open'
            try:
                subprocess.Popen([opener, github_url], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception as e:
                print(f"Nie udało się otworzyć przeglądarki: {e}")

        self.accept()

class EmailConfigWindow(QtWidgets.QDialog):
    """Okno obsługujące wydzielony fragment funkcjonalności aplikacji."""
    def __init__(self, parent=None):
        """Inicjalizuje obiekt i przygotowuje jego stan początkowy."""
        super().__init__(parent)
        self.setWindowTitle(_("Konfiguracja Email"))
        self.setModal(True)
        self.resize(400, 250)
        self.setup_ui()
        self.load_config()

    def setup_ui(self):
        """Buduje i konfiguruje interfejs użytkownika."""
        layout = QtWidgets.QVBoxLayout(self)

        form_layout = QtWidgets.QFormLayout()
        self.edit_smtp = QtWidgets.QLineEdit()
        self.edit_smtp.setPlaceholderText(_("(np. smtp.gmail.com)"))
        self.edit_port = QtWidgets.QLineEdit()
        self.edit_port.setPlaceholderText(_("(np. 465 lub 587)"))
        self.edit_email = QtWidgets.QLineEdit()
        self.edit_email.setPlaceholderText(_("(Zwykle Twój adres e-mail)"))
        self.edit_password = QtWidgets.QLineEdit()
        self.edit_password.setPlaceholderText(_("(Zazwyczaj Twoje hasło email)"))
        self.edit_password.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)

        form_layout.addRow(_("SMTP Server:"), self.edit_smtp)
        form_layout.addRow(_("Port:"), self.edit_port)
        form_layout.addRow(_("Email nadawcy:"), self.edit_email)
        form_layout.addRow(_("Hasło / Token:"), self.edit_password)

        layout.addLayout(form_layout)

        btn_layout = QtWidgets.QHBoxLayout()
        self.btn_save = QtWidgets.QPushButton(_("Zapisz"))
        self.btn_cancel = QtWidgets.QPushButton(_("Anuluj"))
        btn_layout.addWidget(self.btn_save)
        btn_layout.addWidget(self.btn_cancel)
        layout.addLayout(btn_layout)

        self.btn_save.clicked.connect(self.save_config)
        self.btn_cancel.clicked.connect(self.close)

    def load_config(self):
        """Wczytuje dane lub ustawienia potrzebne do działania."""
        try:
            server, port, email, password = load_smtp()
            if server:
                self.edit_smtp.setText(server)
                self.edit_port.setText(str(port))
                self.edit_email.setText(email)
                self.edit_password.setText(password)
            else:
                self.edit_smtp.setText("")
                self.edit_port.setText("")
                self.edit_email.setText("")
                self.edit_password.setText("")
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, _("Błąd"), f"{_('Nie udało się wczytać konfiguracji SMTP:')}\n{e}")

    def save_config(self):
        """Zapisuje dane lub ustawienia."""
        try:
            save_smtp(
                server=self.edit_smtp.text().strip(),
                port=int(self.edit_port.text().strip()),
                email=self.edit_email.text().strip(),
                password=self.edit_password.text().strip()
            )
            QtWidgets.QMessageBox.information(self, _("Zapisano"), _("Dane email zostały zapisane w bazie."))
            self.close()
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, _("Błąd"), f"{_('Nie udało się zapisać konfiguracji SMTP:')}\n{e}")

class Ui_MainWindow(object):
    """Klasa budująca i przechowująca elementy interfejsu użytkownika."""
    def setupUi(self, MainWindow):
        """Buduje i konfiguruje interfejs użytkownika."""
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(1120, 750)
        MainWindow.setMinimumSize(QtCore.QSize(980, 650))
        MainWindow.setWindowIcon(QtGui.QIcon(get_app_icon_path()))
        self.centralwidget = QtWidgets.QWidget(parent=MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.mainLayout = QtWidgets.QVBoxLayout(self.centralwidget)
        self.mainLayout.setObjectName("mainLayout")

        # Top Layout
        self.topLayout = QtWidgets.QHBoxLayout()
        self.topLayout.setObjectName("topLayout")

        # Szukajka
        self.lineEdit_szukajka = QtWidgets.QLineEdit(parent=self.centralwidget)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.lineEdit_szukajka.sizePolicy().hasHeightForWidth())
        self.lineEdit_szukajka.setSizePolicy(sizePolicy)
        self.lineEdit_szukajka.setMinimumSize(QtCore.QSize(300, 0))
        self.lineEdit_szukajka.setObjectName("lineEdit_szukajka")
        self.topLayout.addWidget(self.lineEdit_szukajka)

        # Odśwież
        #self.pushButtonNew_ref = MyPushButton(parent=self.centralwidget)
        #self.pushButtonNew_ref.setFixedSize(30, 26)
        #self.pushButtonNew_ref.setObjectName("pushButtonNew_ref")
        #self.topLayout.addWidget(self.pushButtonNew_ref)
        #self.pushButtonNew_ref.setToolTip(_("Odśwież Tabelę"))

        # Label top
        self.label_top = QtWidgets.QLabel(parent=self.centralwidget)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHeightForWidth(self.label_top.sizePolicy().hasHeightForWidth())
        self.label_top.setSizePolicy(sizePolicy)
        font = QtGui.QFont()
        font.setPointSize(15)
        font.setBold(True)
        self.label_top.setFont(font)
        self.label_top.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.label_top.setObjectName("label_top")
        self.topLayout.addWidget(self.label_top)

        # FILTR DATY - Wersja poprawiona (kompaktowa, przezroczysta)
        # Używamy QWidget zamiast QFrame, żeby nie było szarego tła
        self.container_filters = QtWidgets.QWidget(self.centralwidget)

        # Pionowy layout dla etykiety i przycisku
        self.layout_filters_v = QtWidgets.QVBoxLayout(self.container_filters)
        # Kluczowe: zerujemy marginesy i dajemy minimalny odstęp, żeby nie rozpychało paska
        self.layout_filters_v.setContentsMargins(0, 0, 0, 0)
        self.layout_filters_v.setSpacing(0)

        # 1. Nowa etykieta (Napis NAD przyciskiem)
        self.label_zakres = QtWidgets.QLabel(self.container_filters)
        self.label_zakres.setObjectName("label_zakres")
        self.label_zakres.setText(_("Zakres Filtra"))
        self.label_zakres.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        # Styl: przezroczyste tło, mała czcionka, szary kolor, brak marginesów dolnych
        self.label_zakres.setStyleSheet(
            "background: transparent; font-size: 7pt; color: #666; margin-bottom: 0px; padding: 0px;"
        )
        self.layout_filters_v.addWidget(self.label_zakres)

        # 2. Przycisk (Rok)
        self.pushButtonNew_filter = QtWidgets.QPushButton(self.container_filters)
        self.pushButtonNew_filter.setObjectName("pushButtonNew_filter")
        self.pushButtonNew_filter.setMinimumSize(QtCore.QSize(90, 20))

        icon_cal = QtGui.QIcon(resource_path("actions/calendar.png"))
        if not icon_cal.isNull():
             self.pushButtonNew_filter.setIcon(icon_cal)

        self.layout_filters_v.addWidget(self.pushButtonNew_filter)

        # Dodajemy kontener (z napisem i przyciskiem) do głównego paska
        # Ustawiamy wyrównanie do dołu, żeby przycisk był w jednej linii z innymi
        self.topLayout.addWidget(self.container_filters, 0, QtCore.Qt.AlignmentFlag.AlignBottom)

        # Radio Buttons
        self.radioButton_new = QtWidgets.QRadioButton(parent=self.centralwidget)
        self.radioButton_new.setObjectName("radioButton_new")
        self.topLayout.addWidget(self.radioButton_new)

        self.radioButton_all = QtWidgets.QRadioButton(parent=self.centralwidget)
        self.radioButton_all.setObjectName("radioButton_all")
        self.topLayout.addWidget(self.radioButton_all)

        self.radioButton_end = QtWidgets.QRadioButton(parent=self.centralwidget)
        self.radioButton_end.setObjectName("radioButton_end")
        self.topLayout.addWidget(self.radioButton_end)

        self.mainLayout.addLayout(self.topLayout)

        # Splitter i TableView
        self.splitter_tables = QtWidgets.QSplitter(parent=self.centralwidget)
        self.splitter_tables.setOrientation(QtCore.Qt.Orientation.Vertical)
        self.splitter_tables.setObjectName("splitter_tables")

        self.tableView = QtWidgets.QTableView(parent=self.splitter_tables)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.tableView.sizePolicy().hasHeightForWidth())
        self.tableView.setSizePolicy(sizePolicy)
        font = QtGui.QFont()
        font.setPointSize(11)
        font.setBold(True)
        self.tableView.setFont(font)
        self.tableView.setObjectName("tableView")

        self.model = QtGui.QStandardItemModel()
        self.model.setHorizontalHeaderLabels([_("Numer"), _("Data"), _("Klient"), _("Telefon"), _("Sprzęt"), _("Nr seryjny"), _("Uwagi"), _("Status")])
        self.tableView.setModel(self.model)


        # Header Widget
        self.headerWidget = QtWidgets.QFrame(parent=self.splitter_tables)
        self.headerWidget.setMinimumSize(QtCore.QSize(0, 220))
        self.headerWidget.setMaximumSize(QtCore.QSize(16777215, 220))
        self.headerWidget.setObjectName("headerWidget")
        self.headerLayout = QtWidgets.QHBoxLayout(self.headerWidget)
        self.headerLayout.setContentsMargins(0, 0, 0, 0)
        self.headerLayout.setSpacing(6)

        self.label_lewy = QtWidgets.QLabel(parent=self.headerWidget)
        self.label_lewy.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.label_lewy.setMaximumHeight(270)
        self.label_lewy.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignTop)
        self.label_lewy.setWordWrap(True)
        self.label_lewy.setObjectName("label_lewy")
        self.headerLayout.addWidget(self.label_lewy)

        self.label_srodek = QtWidgets.QLabel(parent=self.headerWidget)
        self.label_srodek.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.label_srodek.setMaximumHeight(270)
        self.label_srodek.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignTop)
        self.label_srodek.setWordWrap(True)
        self.label_srodek.setObjectName("label_srodek")
        self.headerLayout.addWidget(self.label_srodek)

        self.label_prawy = QtWidgets.QLabel(parent=self.headerWidget)
        self.label_prawy.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.label_prawy.setMaximumHeight(270)
        self.label_prawy.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignTop)
        self.label_prawy.setWordWrap(True)
        self.label_prawy.setObjectName("label_prawy")
        self.headerLayout.addWidget(self.label_prawy)

        self.label_dodatki = QtWidgets.QLabel(parent=self.headerWidget)
        self.label_dodatki.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.label_dodatki.setMaximumHeight(270)
        self.label_dodatki.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignTop)
        self.label_dodatki.setWordWrap(True)
        self.label_dodatki.setObjectName("label_dodatki")
        self.headerLayout.addWidget(self.label_dodatki)

        self.mainLayout.addWidget(self.splitter_tables)

        # Bottom Layout i przyciski
        self.bottomLayout = QtWidgets.QHBoxLayout()
        self.bottomLayout.setObjectName("bottomLayout")

        self.pushButtonNew_new = MyPushButton(parent=self.centralwidget)
        self.pushButtonNew_new.setObjectName("pushButtonNew_new")
        self.bottomLayout.addWidget(self.pushButtonNew_new)

        self.pushButtonNew_popdane = MyPushButton(parent=self.centralwidget)
        self.pushButtonNew_popdane.setObjectName("pushButtonNew_popdane")
        self.bottomLayout.addWidget(self.pushButtonNew_popdane)

        self.pushButtonNew_del = MyPushButton(parent=self.centralwidget)
        self.pushButtonNew_del.setObjectName("pushButtonNew_del")
        self.bottomLayout.addWidget(self.pushButtonNew_del)

        self.pushButtonNew_print = MyPushButton(parent=self.centralwidget)
        self.pushButtonNew_print.setObjectName("pushButtonNew_print")
        self.bottomLayout.addWidget(self.pushButtonNew_print)

        self.pushButtonNew_end = MyPushButton(parent=self.centralwidget)
        self.pushButtonNew_end.setObjectName("pushButtonNew_end")
        self.bottomLayout.addWidget(self.pushButtonNew_end)

        self.pushButtonNew_backup = MyPushButton(parent=self.centralwidget)
        self.pushButtonNew_backup.setObjectName("pushButtonNew_backup")
        self.bottomLayout.addWidget(self.pushButtonNew_backup)

        # Przycisk KLIENCI
        self.pushButtonNew_clients = MyPushButton(parent=self.centralwidget)
        self.pushButtonNew_clients.setObjectName("pushButtonNew_clients")
        self.bottomLayout.addWidget(self.pushButtonNew_clients)

        self.pushButtonNew_baza = MyPushButton(parent=self.centralwidget)
        self.pushButtonNew_baza.setVisible(False)

        spacerItem = QtWidgets.QSpacerItem(0, 0, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.bottomLayout.addItem(spacerItem)

        self.label_help_icon = QtWidgets.QLabel(self.centralwidget)
        self.label_help_icon.setObjectName("label_help_icon")
        icon_path = get_app_logo_path()
        pixmap = QtGui.QPixmap(icon_path)
        pixmap = pixmap.scaled(
            40, 40,
            QtCore.Qt.AspectRatioMode.KeepAspectRatio,
            QtCore.Qt.TransformationMode.SmoothTransformation
        )

        self.label_help_icon.setPixmap(pixmap)
        self.label_help_icon.setFixedSize(30, 30)
        self.label_help_icon.setScaledContents(True)

        self.label_help_icon.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self.click_count = 0

        def logo_klikniete(event):
            # Reagujemy tylko na lewy przycisk myszy
            """Realizuje logikę operacji logo klikniete w klasie Ui_MainWindow."""
            if event.button() == QtCore.Qt.MouseButton.LeftButton:
                self.click_count += 1
                if self.click_count == 10:
                    self.click_count = 0 # Reset licznika po odpaleniu
                    from modules.easteregg import EasterEggDialog
                    EasterEggDialog(self.centralwidget).exec()

        self.label_help_icon.mousePressEvent = logo_klikniete

        # Label Serwis
        self.label_serwis = QtWidgets.QLabel(self.centralwidget)
        font_file = resource_path("fonts/Comfortaa-Bold.ttf")
        font_id = QtGui.QFontDatabase.addApplicationFont(font_file)
        font_family = (
            QtGui.QFontDatabase.applicationFontFamilies(font_id)[0]
            if font_id != -1 else "Arial"
        )
        self.label_serwis.setText(_(
            '<span style="font-family:\'{font_family}\'; font-size:13pt;">SerwisApp</span><br>'
            '<span style="font-family:\'{font_family}\'; font-size:7pt;">Proste Prowadzenie Serwisu</span>'
        ).format(font_family=font_family))

        self.label_serwis.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.label_serwis.adjustSize()

        def update_bottom_right_widgets():
            """Aktualizuje stan danych lub interfejsu."""
            margin_right = 15
            margin_bottom = 5
            spacing = 10
            icon_x = self.centralwidget.width() - self.label_help_icon.width() - margin_right
            icon_y = self.centralwidget.height() - self.label_help_icon.height() - margin_bottom
            self.label_help_icon.move(icon_x, icon_y)
            label_x = icon_x - self.label_serwis.width() - spacing
            label_y = icon_y + (self.label_help_icon.height() - self.label_serwis.height()) // 2
            self.label_serwis.move(label_x, label_y)

        update_bottom_right_widgets()
        old_resize_event = self.centralwidget.resizeEvent

        def new_resize_event(event):
            """Realizuje logikę operacji new resize event w klasie Ui_MainWindow."""
            update_bottom_right_widgets()
            if old_resize_event:
                old_resize_event(event)

        self.centralwidget.resizeEvent = new_resize_event

        self.mainLayout.addLayout(self.bottomLayout)

        # Ikony przycisków
        icon_size = QtCore.QSize(18, 18)
        self.pushButtonNew_new.setIcon(QtGui.QIcon(resource_path("actions/dodaj.png")))
        self.pushButtonNew_new.setIconSize(icon_size)
        self.pushButtonNew_new.setText(_("Dodaj"))
        self.pushButtonNew_new.setToolTip(_("Dodaj nowe zlecenie"))

        self.pushButtonNew_popdane.setIcon(QtGui.QIcon(resource_path("actions/edit.png")))
        self.pushButtonNew_popdane.setIconSize(icon_size)
        self.pushButtonNew_popdane.setText(_("Edytuj"))
        self.pushButtonNew_popdane.setToolTip(_("Edytuj dane zlecenia / Dodaj naprawę"))

        self.pushButtonNew_del.setIcon(QtGui.QIcon(resource_path("actions/usun.png")))
        self.pushButtonNew_del.setIconSize(icon_size)
        self.pushButtonNew_del.setText(_("Usuń"))
        self.pushButtonNew_del.setToolTip(_("Usuń zlecenie"))

        self.pushButtonNew_print.setIcon(QtGui.QIcon(resource_path("actions/drukuj.png")))
        self.pushButtonNew_print.setIconSize(icon_size)
        self.pushButtonNew_print.setText(_("Drukuj"))
        self.pushButtonNew_print.setToolTip(_("Wydrukuj zlecenie/raport"))

        self.pushButtonNew_end.setIcon(QtGui.QIcon(resource_path("actions/zakoncz.png")))
        self.pushButtonNew_end.setIconSize(icon_size)
        self.pushButtonNew_end.setText(_("Zakończ"))
        self.pushButtonNew_end.setToolTip(_("Zmień status zlecenia"))

        self.pushButtonNew_backup.setIcon(QtGui.QIcon(resource_path("actions/backup.png")))
        self.pushButtonNew_backup.setIconSize(icon_size)
        self.pushButtonNew_backup.setText(_("Backup"))
        self.pushButtonNew_backup.setToolTip(_("Wykonaj kopię lub przywróć"))

        self.pushButtonNew_clients.setIcon(QtGui.QIcon(resource_path("actions/client.png")))
        self.pushButtonNew_clients.setIconSize(icon_size)
        self.pushButtonNew_clients.setText(_("Klienci"))
        self.pushButtonNew_clients.setToolTip(_("Baza kontrahentów"))

        #self.pushButtonNew_ref.setIcon(QtGui.QIcon(resource_path("actions/refresh.png")))

        # Central widget i menubar
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(parent=MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 980, 30))
        self.menubar.setObjectName("menubar")

        # Etykieta daty i czasu
        self.datetime_label = QtWidgets.QLabel(self.menubar)
        self.datetime_label.setMinimumWidth(250)
        self.datetime_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.datetime_label.setStyleSheet("padding-right: 10px; font-weight: bold;")
        self.menubar.setCornerWidget(self.datetime_label, QtCore.Qt.TopRightCorner)

        # --- 1. Menu Zlecenia ---
        self.menuPlik = QtWidgets.QMenu(_("Zlecenia"), self.menubar)
        self.actionDodaj = QAction(QtGui.QIcon(resource_path("actions/dodaj.png")), _("Dodaj Zlecenie"), MainWindow)
        self.actionDodaj.setShortcut(QKeySequence("Ctrl+N")) # Standardowy skrót dla nowej pozycji

        self.actionPopraw = QAction(QtGui.QIcon(resource_path("actions/edit.png")), _("Edytuj Zlecenie"), MainWindow)
        self.actionPopraw.setShortcut(QKeySequence("Ctrl+E"))

        self.actionUsun = QAction(QtGui.QIcon(resource_path("actions/usun.png")), _("Usuń Zlecenie"), MainWindow)
        self.actionUsun.setShortcut(QKeySequence("Delete"))

        self.actionSzczegoly = QAction(QtGui.QIcon(resource_path("actions/details.png")), _("Pokaż Szczegóły"), MainWindow)
        self.actionSzczegoly.setShortcut(QKeySequence("Return")) # Klawisz Enter/Return

        self.actionStatus = QAction(QtGui.QIcon(resource_path("actions/zakoncz.png")), _("Zakończ Zlecenie"), MainWindow)
        self.actionStatus.setShortcut(QKeySequence("Ctrl+L"))

        self.actionDrukuj = QAction(QtGui.QIcon(resource_path("actions/drukuj.png")), _("Drukuj"), MainWindow)
        self.actionDrukuj.setShortcut(QKeySequence("Ctrl+P"))

        self.actionZakoncz = QAction(QtGui.QIcon(resource_path("actions/exit.png")), _("Zakończ Aplikację"), MainWindow)
        self.actionZakoncz.setShortcut(QKeySequence("Ctrl+Q"))

        self.menuPlik.addAction(self.actionDodaj)
        self.menuPlik.addAction(self.actionPopraw)
        self.menuPlik.addAction(self.actionUsun)
        self.menuPlik.addAction(self.actionStatus)
        self.menuPlik.addSeparator()
        self.menuPlik.addAction(self.actionDrukuj)
        self.menuPlik.addSeparator()
        self.menuPlik.addAction(self.actionZakoncz)

        # --- 2. Menu Filtruj ---
        self.menuFiltruj = QtWidgets.QMenu(_("Filtruj"), self.menubar)
        self.actionNowe = QAction(QtGui.QIcon(resource_path("actions/new.png")), _("Przyjęte"), MainWindow)
        self.actionNowe.setShortcut(QKeySequence("Ctrl+1"))

        self.actionAll = QAction(QtGui.QIcon(resource_path("actions/all.png")), _("Wszystkie"), MainWindow)
        self.actionAll.setShortcut(QKeySequence("Ctrl+2"))

        self.actionend = QAction(QtGui.QIcon(resource_path("actions/zakoncz.png")), _("Zakończone"), MainWindow)
        self.actionend.setShortcut(QKeySequence("Ctrl+3"))

        self.menuFiltruj.addAction(self.actionNowe)
        self.menuFiltruj.addAction(self.actionAll)
        self.menuFiltruj.addAction(self.actionend)

        # --- 3. Menu Narzędzia ---
        self.menuNarzedzia = QtWidgets.QMenu(_("Narzędzia"), self.menubar)
        self.actionBackup = QAction(QtGui.QIcon(resource_path("actions/backup.png")), _("Kopia Zapasowa i Przywracanie"), MainWindow)
        self.actionBackup.setShortcut(QKeySequence("Ctrl+B"))

        self.actionBaza = QAction(QtGui.QIcon(resource_path("actions/baza.png")), _("Wybierz Bazę Danych (Zdalna/Lokalna)"), MainWindow)
        self.actionBaza.setShortcut(QKeySequence("Ctrl+D"))

        self.action_users_manager = QAction(QtGui.QIcon(resource_path("actions/hasloon.png")), _("Użytkownicy i Hasła"), MainWindow)
        self.action_users_manager.setShortcut(QKeySequence("Ctrl+U"))

        self.menuNarzedzia.addAction(self.actionBackup)
        self.menuNarzedzia.addAction(self.actionBaza)
        self.menuNarzedzia.addSeparator()
        self.menuNarzedzia.addAction(self.action_users_manager)

        # --- 4. Menu Ustawienia ---
        self.menuUstawienia = QtWidgets.QMenu(_("Ustawienia"), self.menubar)
        self.actionDaneFirmy = QAction(QtGui.QIcon(resource_path("actions/firma.png")), _("Edytuj Dane Firmy"), MainWindow)
        self.actionDaneFirmy.setShortcut(QKeySequence("Ctrl+Shift+F"))

        self.actionEmailConfig = QAction(QtGui.QIcon(resource_path("actions/email.png")), _("Konfiguracja Email"), MainWindow)
        self.actionEmailConfig.setShortcut(QKeySequence("Ctrl+Shift+M"))

        self.actionKonfiguracjaSMS = QAction(QtGui.QIcon(resource_path("actions/smsconf.png")), _("Konfiguracja SMS (SMSAPI)"), MainWindow)
        self.actionKonfiguracjaSMS.setShortcut(QKeySequence("Ctrl+Shift+S"))

        self.actionEdytujSzablon = QAction(QtGui.QIcon(resource_path("actions/template.png")), _("Ustawienia Wydruku"), MainWindow)
        self.actionEdytujSzablon.setShortcut(QKeySequence("Ctrl+Shift+T"))

        self.menuUstawienia.addAction(self.actionDaneFirmy)
        self.menuUstawienia.addAction(self.actionEmailConfig)
        self.menuUstawienia.addAction(self.actionKonfiguracjaSMS)
        self.menuUstawienia.addAction(self.actionEdytujSzablon)

        self.menuRaporty = QtWidgets.QMenu(_("Raporty"), self.menubar)

        self.actionRaportFinansowy = QAction(QtGui.QIcon(resource_path("actions/raport.png")), _("Raport Finansowy"), MainWindow)
        self.actionRaportFinansowy.setShortcut(QKeySequence("Ctrl+R"))
        self.actionRaportSprzet = QAction(QtGui.QIcon(resource_path("actions/raport.png")), _("Najczęściej naprawiany sprzęt"), MainWindow)
        self.actionRaportNajdrozsze = QAction(QtGui.QIcon(resource_path("actions/raport.png")), _("Najdroższe naprawy"), MainWindow)
        self.menuRaporty.addAction(self.actionRaportFinansowy)
        self.menuRaporty.addAction(self.actionRaportSprzet)
        self.menuRaporty.addAction(self.actionRaportNajdrozsze)

        # Tworzymy nowe menu dla Cennika w głównym pasku (MenuBar)
        self.menuCennik = QtWidgets.QMenu(_("Cennik"), self.menubar)

        self.actionPokazCennik = QAction(QtGui.QIcon(resource_path("actions/readme.png")), _("Cennik"), MainWindow)
        self.actionPokazCennik.setShortcut(QKeySequence("Ctrl+K"))

        self.menuCennik.addAction(self.actionPokazCennik)

        # --- 6. Menu Pomoc ---
        self.menuPomoc = QtWidgets.QMenu(_("Pomoc"), self.menubar)
        self.actionPrzewodnik = QAction(QtGui.QIcon(resource_path("actions/readme.png")), _("Przewodnik"), MainWindow)
        self.actionPrzewodnik.setShortcut(QKeySequence("F1"))

        self.actionWsparcie = QAction(QtGui.QIcon(resource_path("actions/wsparcie.png")), _("Postaw Kawkę"), MainWindow)

        # --- ZGŁOŚ BŁĄD (Ctrl+Shift+B dla Win/Linux, Cmd+Shift+B dla macOS) ---
        self.actionZglosBlad = QAction(QtGui.QIcon(resource_path("actions/robal.png")), _("Zgłoś błąd / sugestię"), MainWindow)

        # Przypisujemy ujednolicony, bezpieczny skrót
        self.actionZglosBlad.setShortcut(QKeySequence("Ctrl+Shift+B") if sys.platform != "darwin" else QKeySequence("Cmd+Shift+B"))

        # Pamiętamy o wymuszeniu kontekstu na całe okno, żeby działało przy zaznaczonej tabeli
        self.actionZglosBlad.setShortcutContext(QtCore.Qt.ShortcutContext.WindowShortcut)


        self.actionOProgramie = QAction(QtGui.QIcon(resource_path("actions/about.png")), _("O Programie"), MainWindow)

        self.menuPomoc.addAction(self.actionPrzewodnik)
        self.menuPomoc.addSeparator()
        self.menuPomoc.addAction(self.actionWsparcie)
        self.menuPomoc.addAction(self.actionZglosBlad)
        self.menuPomoc.addAction(self.actionOProgramie)

        # --- Dodawanie do paska menu ---
        self.menubar.addMenu(self.menuPlik)
        self.menubar.addMenu(self.menuFiltruj)
        self.menubar.addMenu(self.menuNarzedzia)
        self.menubar.addMenu(self.menuUstawienia)
        self.menubar.addMenu(self.menuCennik)
        self.menubar.addMenu(self.menuRaporty)
        self.menubar.addMenu(self.menuPomoc)

        # --- Podłączenie akcji ---
        self.actionDodaj.triggered.connect(lambda: self.pushButtonNew_new.click())
        self.actionPopraw.triggered.connect(lambda: self.pushButtonNew_popdane.click())
        self.actionUsun.triggered.connect(lambda: self.pushButtonNew_del.click())
        self.actionSzczegoly.triggered.connect(lambda: self.tableView.doubleClicked.emit(self.tableView.currentIndex()))
        self.actionStatus.triggered.connect(lambda: self.pushButtonNew_end.click())
        self.actionDrukuj.triggered.connect(lambda: self.pushButtonNew_print.click())
        self.actionZakoncz.triggered.connect(QApplication.instance().quit)

        self.actionNowe.triggered.connect(lambda: self.radioButton_new.setChecked(True))
        self.actionAll.triggered.connect(lambda: self.radioButton_all.setChecked(True))
        self.actionend.triggered.connect(lambda: self.radioButton_end.setChecked(True))

        self.actionBackup.triggered.connect(lambda: self.pushButtonNew_backup.click())
        self.actionBaza.triggered.connect(lambda: self.pushButtonNew_baza.click())
        self.action_users_manager.triggered.connect(lambda: menedzer_hasel(MainWindow))

        self.actionRaportFinansowy.triggered.connect(lambda: RaportDialog(parent=MainWindow).exec())
        self.actionRaportSprzet.triggered.connect(lambda: RaportTopSprzetDialog(parent=MainWindow).exec())
        self.actionRaportNajdrozsze.triggered.connect(lambda: RaportTopNaprawyDialog(parent=MainWindow).exec())

        self.actionEmailConfig.triggered.connect(lambda: EmailConfigWindow(None).exec())
        self.actionKonfiguracjaSMS.triggered.connect(lambda: SMSConfigDialog(None).exec())
        self.actionEdytujSzablon.triggered.connect(lambda: edytuj_szablon(MainWindow))

        self.actionPrzewodnik.triggered.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.join(os.path.expanduser("~"), ".SerwisApp", "przewodnik.pdf"))))

        # Podepnij pod sekcją pomocy w pliku głównym:
        self.actionWsparcie.triggered.connect(lambda: pokaz_wsparcie(None))
        self.actionZglosBlad.triggered.connect(lambda: BugReportDialog(MainWindow).exec()) # Uruchomienie okna zgłaszania błędu
        self.actionOProgramie.triggered.connect(lambda: pokaz_info_o_programie(None))

        MainWindow.setMenuBar(self.menubar)

        # Statusbar
        self.statusbar = QtWidgets.QStatusBar(parent=MainWindow)
        #self.statusbar.addWidget(self.label_plus_status)
        #self.update_plus_status()
        MainWindow.setStatusBar(self.statusbar)

        # Inicjalizacja UI
        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        """Ustawia teksty interfejsu zgodnie z aktywnym tłumaczeniem."""
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "MainWindow"))
        font_family = "Arial"
        font_file = resource_path("fonts/Comfortaa-Bold.ttf")
        if os.path.exists(font_file):
            font_id = QtGui.QFontDatabase.addApplicationFont(font_file)
            if font_id != -1:
                font_family = QtGui.QFontDatabase.applicationFontFamilies(font_id)[0]
        custom_font = QtGui.QFont(font_family)
        custom_font.setPointSize(18)
        self.label_top.setFont(custom_font)
        self.lineEdit_szukajka.setPlaceholderText(_translate("MainWindow", _("Szukaj...")))
        self.label_top.setText(_translate("MainWindow", _("Zlecenia Serwisowe")))

        # --- KOD EASTER EGGA: WYBÓR GRY ---
        self.label_top.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self.credits_click_count = 0

        def tytul_klikniety(event):
            """Realizuje logikę operacji tytul klikniety w klasie Ui_MainWindow."""
            if event.button() == QtCore.Qt.MouseButton.LeftButton:
                self.credits_click_count += 1
                if self.credits_click_count == 7: # Odpala okno wyboru po 7 kliknięciach
                    self.credits_click_count = 0

                    from modules.game import GameSelectionDialog
                    selection_dialog = GameSelectionDialog(self.centralwidget)
                    if selection_dialog.exec() == QtWidgets.QDialog.Accepted:
                        if selection_dialog.wybor == 1:
                            from modules.game import SerwisMarioDialog
                            SerwisMarioDialog(self.centralwidget).exec()
                        elif selection_dialog.wybor == 2:
                            from modules.game import SerwisSnakeDialog
                            SerwisSnakeDialog(self.centralwidget).exec()

        # Zastępujemy domyślne zachowanie etykiety
        self.label_top.mousePressEvent = tytul_klikniety
        # ----------------------------------------
        self.radioButton_new.setText(_translate("MainWindow", _("Przyjęte")))
        self.radioButton_all.setText(_translate("MainWindow", _("Wszystkie")))
        self.radioButton_end.setText(_translate("MainWindow", _("Ukończone")))
        self.label_lewy.setText(_translate("MainWindow", _("Dane Klienta/Zlecenie")))
        self.label_srodek.setText(_translate("MainWindow", _("Opis, Uwagi, Naprawa")))
        self.label_prawy.setText(_translate("MainWindow", _("Dane Urządzenia, Koszty")))
        self.label_dodatki.setText(_translate("MainWindow", _("Opcje")))
        self.pushButtonNew_new.setText(_translate("MainWindow", _("Dodaj")))
        self.pushButtonNew_popdane.setText(_translate("MainWindow", _("Edytuj")))
        self.pushButtonNew_del.setText(_translate("MainWindow", _("Usuń")))
        self.pushButtonNew_print.setText(_translate("MainWindow", _("Drukuj")))
        self.pushButtonNew_end.setText(_translate("MainWindow", _("Zakończ")))
        self.pushButtonNew_backup.setText(_translate("MainWindow", _("Backup")))
        self.pushButtonNew_filter.setText(_translate("MainWindow", _("Rok")))



if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    MainWindow = QtWidgets.QMainWindow()
    ui = Ui_MainWindow()
    ui.setupUi(MainWindow)
    MainWindow.show()
    sys.exit(app.exec())
