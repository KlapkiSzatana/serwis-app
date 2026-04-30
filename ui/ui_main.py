import sys
import os
from setup import config
import sqlite3
from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QApplication
from modules.button import MyPushButton
from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from modules.pomoc import pokaz_wsparcie
from modules.pokaz_info import pokaz_info_o_programie
from modules.smtp_store import load_smtp, save_smtp
from modules.password_protection import menedzer_hasel
from modules.utils import resource_path
from modules.raport import RaportDialog, RaportTopSprzetDialog, RaportTopNaprawyDialog
from modules.cennik import CennikDialog, EdytujCennikDialog
from modules.drukowanie import edytuj_szablon
from modules.sms import SMSConfigDialog

# Zabezpieczenie tłumaczeń (dodaj to na górze pliku ui_main.py)
try:
    _("Test")
except NameError:
    def _(text):
        """Zwraca tekst bez tłumaczenia, gdy mechanizm i18n nie jest aktywny."""
        return text


CONFIG_FILE = getattr(config, "CONFIG_FILE", "config.ini")

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
        self.lineEdit_szukajka.setMinimumSize(QtCore.QSize(200, 0))
        self.lineEdit_szukajka.setObjectName("lineEdit_szukajka")
        self.topLayout.addWidget(self.lineEdit_szukajka)

        # Odśwież
        self.pushButtonNew_ref = MyPushButton(parent=self.centralwidget)
        self.pushButtonNew_ref.setFixedSize(30, 26)
        self.pushButtonNew_ref.setObjectName("pushButtonNew_ref")
        self.topLayout.addWidget(self.pushButtonNew_ref)
        self.pushButtonNew_ref.setToolTip(_("Odśwież Tabelę"))

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

        # Ikona serwisu
        self.label_help_icon = QtWidgets.QLabel(self.centralwidget)
        self.label_help_icon.setObjectName("label_help_icon")
        icon_path = resource_path("actions/serwisapp.png")
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

        # "Hakujemy" ikonkę, zastępując jej domyślną reakcję naszą funkcją
        self.label_help_icon.mousePressEvent = logo_klikniete
        # -----------------------

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

        self.pushButtonNew_ref.setIcon(QtGui.QIcon(resource_path("actions/refresh.png")))

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
        self.actionPopraw = QAction(QtGui.QIcon(resource_path("actions/edit.png")), _("Edytuj Zlecenie"), MainWindow)
        self.actionUsun = QAction(QtGui.QIcon(resource_path("actions/usun.png")), _("Usuń Zlecenie"), MainWindow)
        self.actionSzczegoly = QAction(QtGui.QIcon(resource_path("actions/details.png")), _("Pokaż Szczegóły"), MainWindow)
        self.actionStatus = QAction(QtGui.QIcon(resource_path("actions/zakoncz.png")), _("Zakończ Zlecenie"), MainWindow)
        self.actionDrukuj = QAction(QtGui.QIcon(resource_path("actions/drukuj.png")), _("Drukuj"), MainWindow)
        self.actionZakoncz = QAction(QtGui.QIcon(resource_path("actions/exit.png")), _("Zakończ Aplikację"), MainWindow)

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
        self.actionend = QAction(QtGui.QIcon(resource_path("actions/zakoncz.png")), _("Zakończone"), MainWindow)
        self.actionAll = QAction(QtGui.QIcon(resource_path("actions/all.png")), _("Wszystkie"), MainWindow)
        self.menuFiltruj.addAction(self.actionNowe)
        self.menuFiltruj.addAction(self.actionAll)
        self.menuFiltruj.addAction(self.actionend)

        # --- 3. Menu Narzędzia ---
        self.menuNarzedzia = QtWidgets.QMenu(_("Narzędzia"), self.menubar)
        self.actionBackup = QAction(QtGui.QIcon(resource_path("actions/backup2.png")), _("Kopia Zapasowa i Przywracanie"), MainWindow)
        self.actionBaza = QAction(QtGui.QIcon(resource_path("actions/baza.png")), _("Wybierz Bazę Danych (Zdalna/Lokalna)"), MainWindow)
        self.action_users_manager = QAction(QtGui.QIcon(resource_path("actions/hasloon.png")), _("Użytkownicy i Hasła"), MainWindow)

        self.menuNarzedzia.addAction(self.actionBackup)
        self.menuNarzedzia.addAction(self.actionBaza)
        self.menuNarzedzia.addSeparator()
        self.menuNarzedzia.addAction(self.action_users_manager)

        # --- 4. Menu Ustawienia ---
        self.menuUstawienia = QtWidgets.QMenu(_("Ustawienia"), self.menubar)
        self.actionDaneFirmy = QAction(QtGui.QIcon(resource_path("actions/firma.png")), _("Edytuj Dane Firmy"), MainWindow)
        self.actionEmailConfig = QAction(QtGui.QIcon(resource_path("actions/email.png")), _("Konfiguracja Email"), MainWindow)
        self.actionKonfiguracjaSMS = QAction(QtGui.QIcon(resource_path("actions/smsconf.png")), _("Konfiguracja SMS (SMSAPI)"), MainWindow)
        self.actionEdytujSzablon = QAction(QtGui.QIcon(resource_path("actions/template.png")), _("Ustawienia Wydruku"), MainWindow)

        self.menuUstawienia.addAction(self.actionDaneFirmy)
        self.menuUstawienia.addAction(self.actionEmailConfig)
        self.menuUstawienia.addAction(self.actionKonfiguracjaSMS)
        self.menuUstawienia.addAction(self.actionEdytujSzablon)

        # --- 5. Raport ---
        # Tworzymy główne menu rozwijane
        self.menuRaporty = QtWidgets.QMenu(_("Raporty"), self.menubar)
        self.menuRaporty.setIcon(QtGui.QIcon(resource_path(""))) # Dodaj tu ikonkę jeśli masz

        # Tworzymy 3 oddzielne akcje do menu
        self.actionRaportFinansowy = QAction(QtGui.QIcon(resource_path("actions/raport.png")), _("Raport Finansowy"), MainWindow)
        self.actionRaportSprzet = QAction(QtGui.QIcon(resource_path("actions/raport.png")), _("Najczęściej naprawiany sprzęt"), MainWindow)
        self.actionRaportNajdrozsze = QAction(QtGui.QIcon(resource_path("actions/raport.png")), _("Najdroższe naprawy"), MainWindow)
        # Dodajemy akcje do rozwijanego menu
        self.menuRaporty.addAction(self.actionRaportFinansowy)
        self.menuRaporty.addAction(self.actionRaportSprzet)
        self.menuRaporty.addAction(self.actionRaportNajdrozsze)

        # Tworzymy nowe menu dla Cennika w głównym pasku (MenuBar)
        self.menuCennik = QtWidgets.QMenu(_("Cennik"), self.menubar)

        self.actionPokazCennik = QAction(QtGui.QIcon(resource_path("actions/readme.png")), _("Pokaż cennik"), MainWindow)
        self.actionEdytujCennik = QAction(QtGui.QIcon(resource_path("actions/edit.png")), _("Edytuj cennik"), MainWindow)

        self.menuCennik.addAction(self.actionPokazCennik)
        self.menuCennik.addAction(self.actionEdytujCennik)

        # Podpinamy akcje pod nasze nowe klasy
        self.actionPokazCennik.triggered.connect(lambda: CennikDialog(parent=MainWindow).exec())
        self.actionEdytujCennik.triggered.connect(lambda: EdytujCennikDialog(parent=MainWindow).exec())

        # --- 6. Menu Pomoc ---
        self.menuPomoc = QtWidgets.QMenu(_("Pomoc"), self.menubar)
        self.actionPrzewodnik = QAction(QtGui.QIcon(resource_path("actions/readme.png")), _("Przewodnik"), MainWindow)

        self.actionWsparcie = QAction(QtGui.QIcon(resource_path("actions/wsparcie.png")), _("Postaw Kawkę"), MainWindow)
        self.actionOProgramie = QAction(QtGui.QIcon(resource_path("actions/about.png")), _("O Programie"), MainWindow)

        self.menuPomoc.addAction(self.actionPrzewodnik)
        self.menuPomoc.addSeparator()
        self.menuPomoc.addAction(self.actionWsparcie)
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

        self.actionWsparcie.triggered.connect(lambda: pokaz_wsparcie(None))
        self.actionOProgramie.triggered.connect(lambda: pokaz_info_o_programie(None))

        MainWindow.setMenuBar(self.menubar)

        # Statusbar
        self.statusbar = QtWidgets.QStatusBar(parent=MainWindow)
        self.label_plus_status = QtWidgets.QLabel(parent=self.statusbar)
        self.statusbar.addWidget(self.label_plus_status)
        self.update_plus_status()
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

    def update_plus_status(self):
        """
        Zaktualizowana wersja: Odporna na różnice w ścieżkach (Windows/Linux)
        i poprawnie odświeżająca dane firmy.
        """
        import os
        import sqlite3
        from setup import config

        # --- 2. Ustalanie typu bazy ---
        # Pobieramy pełną ścieżkę aktualnej bazy
        try:
            current_db_path = os.path.abspath(config.DB_FILE)
            current_dir = os.path.normpath(os.path.dirname(current_db_path))
        except Exception:
            current_dir = ""

        # Pobieramy ścieżkę katalogu domyślnego (.SerwisApp)
        local_dir_raw = os.path.join(os.path.expanduser("~"), ".SerwisApp")
        local_dir = os.path.normpath(os.path.abspath(local_dir_raw))

        # Porównanie - na Windowsie wielkość liter nie ma znaczenia, więc dajemy .lower()
        if os.name == 'nt':
            is_local = (current_dir.lower() == local_dir.lower())
        else:
            is_local = (current_dir == local_dir)

        if is_local:
            baza_txt = "[Baza Lokalna]"
            baza_color = "gray"
        else:
            baza_txt = "[Baza Sieciowa]"
            baza_color = "#0055ff" # Niebieski

        # --- 3. Pobieranie nazwy firmy ---
        nazwa_firmy = _("Brak nazwy firmy")

        # Sprawdzamy czy plik fizycznie istnieje przed połączeniem
        if os.path.exists(config.DB_FILE):
            try:
                # Timeout 5 sekund, żeby nie wieszało przy sieciowej
                conn = sqlite3.connect(config.DB_FILE, timeout=5)
                c = conn.cursor()
                c.execute("SELECT nazwa FROM firma LIMIT 1")
                row = c.fetchone()
                conn.close()

                if row and row[0]:
                    nazwa_firmy = row[0]
                else:
                    nazwa_firmy = "Firma (Brak nazwy w DB)"

            except sqlite3.Error as e:
                print(f"Błąd SQL przy pobieraniu firmy: {e}")
                nazwa_firmy = "Błąd odczytu bazy"
            except Exception as e:
                print(f"Inny błąd: {e}")
        else:
            nazwa_firmy = "Plik bazy nie istnieje!"

        # --- 4. Wyświetlanie ---
        text = (
            f'&nbsp;&nbsp;&nbsp;<span style="font-size:10pt;"> '
            f'<span style="color:{baza_color}; font-weight:bold;">{baza_txt}</span> | '
            f'<b>{nazwa_firmy}</b>'
        )

        self.label_plus_status.setText(text)

if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    MainWindow = QtWidgets.QMainWindow()
    ui = Ui_MainWindow()
    ui.setupUi(MainWindow)
    MainWindow.show()
    sys.exit(app.exec())
