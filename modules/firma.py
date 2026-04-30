import os
import shutil
from PySide6 import QtWidgets, QtCore, QtGui
from modules.utils import resource_path
from modules import password_protection  # Import modułu uprawnień

# Zabezpieczenie na wypadek uruchamiania modułu niezależnie (bez main.py)
try:
    _("Test")
except NameError:
    def _(text):
        """Zwraca tekst bez tłumaczenia, gdy mechanizm i18n nie jest aktywny."""
        return text

def edytuj_dane_firmy(parent, conn):
    """
    Okno edycji danych firmy - dostępne tylko dla Administratora.
    """
    # --- 1. SPRAWDZENIE UPRAWNIEŃ ---
    if not password_protection.CURRENT_USER_IS_SUPER:
        QtWidgets.QMessageBox.warning(
            parent,
            _("Brak uprawnień"),
            _("Dane firmy może edytować tylko Administrator.")
        )
        return
    # --------------------------------
    dialog = QtWidgets.QDialog(parent)
    dialog.setWindowTitle(_("Edytuj dane firmy"))
    dialog.setModal(True)
    dialog.resize(500, 500)
    layout = QtWidgets.QVBoxLayout(dialog)
    logo_label = QtWidgets.QLabel()
    logo_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
    logo_label.setFixedSize(100, 100)
    layout.addWidget(logo_label)
    user_home = os.path.expanduser("~")
    logo_path = os.path.join(user_home, ".SerwisApp", "logo", "serwisapp.png")
    if os.path.exists(logo_path):
        pixmap = QtGui.QPixmap(logo_path)
        pixmap = pixmap.scaled(100, 100, QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                               QtCore.Qt.TransformationMode.SmoothTransformation)
        logo_label.setPixmap(pixmap)
    else:
        logo_label.setText(_("Brak loga"))
    label = QtWidgets.QLabel(_("Podaj dane swojej firmy: (* pola wymagane!)"))
    layout.addWidget(label)
    form_layout = QtWidgets.QFormLayout()
    nazwa = QtWidgets.QLineEdit()
    adres = QtWidgets.QLineEdit()
    telefon = QtWidgets.QLineEdit()
    email = QtWidgets.QLineEdit()
    nip = QtWidgets.QLineEdit()
    godziny = QtWidgets.QLineEdit()
    form_layout.addRow(_("*Nazwa Firmy:"), nazwa)
    form_layout.addRow(_("*Adres Firmy:"), adres)
    form_layout.addRow(_("*Telefon:"), telefon)
    form_layout.addRow(_("*Adres E-mail:"), email)
    form_layout.addRow(_("NIP:"), nip)
    form_layout.addRow(_("Godziny Otwarcia:"), godziny)
    layout.addLayout(form_layout)
    info_label = QtWidgets.QLabel(_("Logo firmy możesz wgrać klikając 'Wgraj Logo'"))
    layout.addWidget(info_label)
    btn_logo = QtWidgets.QPushButton(_("Wgraj logo"))
    icon = QtGui.QIcon(resource_path("actions/motyw.png"))
    btn_logo.setIcon(icon)
    btn_logo.setIconSize(QtCore.QSize(25, 25))
    h_layout = QtWidgets.QHBoxLayout()
    h_layout.addStretch()
    h_layout.addWidget(btn_logo)
    h_layout.addStretch()
    layout.addLayout(h_layout)
    def wgraj_logo():
        """Realizuje logikę operacji wgraj logo."""
        file_name, _filter = QtWidgets.QFileDialog.getOpenFileName(
            dialog,
            _("Wybierz plik logo (PNG)"),
            "",
            _("Pliki PNG (*.png)")
        )
        if not file_name:
            return
        try:
            logo_dir = os.path.join(os.path.expanduser("~"), ".SerwisApp", "logo")
            os.makedirs(logo_dir, exist_ok=True)
            target_file = os.path.join(logo_dir, "serwisapp.png")
            shutil.copyfile(file_name, target_file)
            pixmap = QtGui.QPixmap(target_file)
            if not pixmap.isNull():
                pixmap = pixmap.scaled(100, 100, QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                                       QtCore.Qt.TransformationMode.SmoothTransformation)
                logo_label.setPixmap(pixmap)
            else:
                logo_label.setText(_("Nie udało się wczytać logo"))
            QtWidgets.QMessageBox.information(
                dialog,
                _("Sukces"),
                _("Logo wgrane do {}").format(target_file)
            )

        except Exception as e:
            QtWidgets.QMessageBox.critical(
                dialog,
                _("Błąd"),
                _("Nie udało się wgrać logo: {}").format(e)
            )
    btn_logo.clicked.connect(wgraj_logo)
    btn_layout = QtWidgets.QHBoxLayout()
    btn_zapisz = QtWidgets.QPushButton(_("Zapisz"))
    btn_anuluj = QtWidgets.QPushButton(_("Anuluj"))
    btn_layout.addWidget(btn_zapisz)
    btn_layout.addWidget(btn_anuluj)
    layout.addLayout(btn_layout)
    c = conn.cursor()
    # Sprawdzamy, czy tabela istnieje (zabezpieczenie na wszelki wypadek)
    c.execute("CREATE TABLE IF NOT EXISTS firma (id INTEGER PRIMARY KEY, nazwa TEXT, adres TEXT, telefon TEXT, email TEXT, nip TEXT, godziny_otwarcia TEXT)")
    firma = c.execute("SELECT * FROM firma WHERE id=1").fetchone()
    if firma:
        nazwa.setText(firma[1])
        adres.setText(firma[2])
        telefon.setText(firma[3])
        email.setText(firma[4])
        nip.setText(firma[5])
        godziny.setText(firma[6] or "")
    def zapisz():
        """Realizuje logikę operacji zapisz."""
        if not nazwa.text().strip() or not adres.text().strip() or not telefon.text().strip() \
           or not email.text().strip():
            QtWidgets.QMessageBox.warning(dialog, _("Uwaga"), _("Wszystkie pola z * muszą być wypełnione!"))
            return
        try:
            c.execute("""
                INSERT OR REPLACE INTO firma (id, nazwa, adres, telefon, email, nip, godziny_otwarcia)
                VALUES (1, ?, ?, ?, ?, ?, ?)
            """, (nazwa.text(), adres.text(), telefon.text(), email.text(), nip.text(), godziny.text()))
            conn.commit()
            QtWidgets.QMessageBox.information(dialog, _("Sukces"), _("Dane firmy zostały zapisane!"))
            dialog.accept()
        except Exception as e:
            QtWidgets.QMessageBox.critical(
                dialog,
                _("Błąd"),
                _("Wystąpił błąd przy zapisie: {}").format(e)
            )
    btn_zapisz.clicked.connect(zapisz)
    btn_anuluj.clicked.connect(dialog.reject)
    dialog.exec()

def okno_konfiguracji_firmy(parent, conn):
    """Realizuje logikę operacji okno konfiguracji firmy."""
    dialog = QtWidgets.QDialog(parent)
    dialog.setWindowTitle(_("Konfiguracja początkowa")) # Używamy tłumaczenia
    dialog.setModal(True)
    dialog.resize(500, 500)

    layout = QtWidgets.QVBoxLayout(dialog)

    logo_label = QtWidgets.QLabel()
    logo_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
    logo_label.setFixedSize(100, 100)
    layout.addWidget(logo_label)

    user_home = os.path.expanduser("~")
    logo_path = os.path.join(user_home, ".SerwisApp", "logo", "serwisapp.png")
    if os.path.exists(logo_path):
        pixmap = QtGui.QPixmap(logo_path)
        pixmap = pixmap.scaled(100, 100, QtCore.Qt.AspectRatioMode.KeepAspectRatio, QtCore.Qt.TransformationMode.SmoothTransformation)
        logo_label.setPixmap(pixmap)
    else:
        logo_label.setText(_("Brak loga"))

    label = QtWidgets.QLabel(_("Podaj dane swojej firmy: (* pola wymagane!)"))
    layout.addWidget(label)

    form_layout = QtWidgets.QFormLayout()
    nazwa = QtWidgets.QLineEdit()
    adres = QtWidgets.QLineEdit()
    telefon = QtWidgets.QLineEdit()
    email = QtWidgets.QLineEdit()
    nip = QtWidgets.QLineEdit()
    godziny = QtWidgets.QLineEdit()
    form_layout.addRow(_("*Nazwa Firmy:"), nazwa)
    form_layout.addRow(_("*Adres Firmy:"), adres)
    form_layout.addRow(_("*Telefon:"), telefon)
    form_layout.addRow(_("*Adres E-mail:"), email)
    form_layout.addRow(_("NIP:"), nip)
    form_layout.addRow(_("Godziny Otwarcia:"), godziny)
    layout.addLayout(form_layout)

    info_label = QtWidgets.QLabel(_("Logo firmy możesz wgrać klikając 'Wgraj Logo'"))
    layout.addWidget(info_label)

    btn_logo = QtWidgets.QPushButton(_("Wgraj logo"))
    icon = QtGui.QIcon(resource_path("actions/motyw.png"))
    btn_logo.setIcon(icon)
    btn_logo.setIconSize(QtCore.QSize(25, 25))
    h_layout = QtWidgets.QHBoxLayout()
    h_layout.addStretch()
    h_layout.addWidget(btn_logo)
    h_layout.addStretch()
    layout.addLayout(h_layout)

    def wgraj_logo():
        """Realizuje logikę operacji wgraj logo."""
        file_name, _ = QtWidgets.QFileDialog.getOpenFileName(
            dialog,
            _("Wybierz plik logo (PNG)"),
            "",
            _("Pliki PNG (*.png)")
        )
        if not file_name:
            return
        try:
            logo_dir = os.path.join(os.path.expanduser("~"), ".SerwisApp", "logo")
            os.makedirs(logo_dir, exist_ok=True)
            target_file = os.path.join(logo_dir, "serwisapp.png")
            shutil.copyfile(file_name, target_file)
            pixmap = QtGui.QPixmap(target_file)
            if not pixmap.isNull():
                pixmap = pixmap.scaled(100, 100, QtCore.Qt.AspectRatioMode.KeepAspectRatio, QtCore.Qt.TransformationMode.SmoothTransformation)
                logo_label.setPixmap(pixmap)
            else:
                logo_label.setText(_("Nie udało się wczytać logo"))
            QtWidgets.QMessageBox.information(dialog, _("Sukces"), _("Logo wgrane do {}").format(target_file))
        except Exception as e:
            QtWidgets.QMessageBox.critical(dialog, _("Błąd"), _("Nie udało się wgrać logo: {}").format(e))

    btn_logo.clicked.connect(wgraj_logo)

    btn_layout = QtWidgets.QHBoxLayout()
    btn_zapisz = QtWidgets.QPushButton(_("Zapisz"))
    btn_anuluj = QtWidgets.QPushButton(_("Anuluj"))
    btn_layout.addWidget(btn_zapisz)
    btn_layout.addWidget(btn_anuluj)
    layout.addLayout(btn_layout)

    def zapisz():
        """Realizuje logikę operacji zapisz."""
        if not nazwa.text().strip() or not adres.text().strip() or not telefon.text().strip() \
           or not email.text().strip():
            QtWidgets.QMessageBox.warning(dialog, _("Uwaga"), _("Wszystkie pola z * muszą być wypełnione!"))
            return
        try:
            c = conn.cursor()
            # Zabezpieczenie przed brakiem tabeli
            c.execute("CREATE TABLE IF NOT EXISTS firma (id INTEGER PRIMARY KEY, nazwa TEXT, adres TEXT, telefon TEXT, email TEXT, nip TEXT, godziny_otwarcia TEXT)")

            c.execute("""
                INSERT OR REPLACE INTO firma (id, nazwa, adres, telefon, email, nip, godziny_otwarcia)
                VALUES (1, ?, ?, ?, ?, ?, ?)
            """, (nazwa.text(), adres.text(), telefon.text(), email.text(), nip.text(), godziny.text()))
            conn.commit()
            QtWidgets.QMessageBox.information(dialog, _("Sukces"), _("Dane firmy zostały zapisane!"))
            dialog.accept()
        except Exception as e:
            QtWidgets.QMessageBox.critical(dialog, _("Błąd"), _("Wystąpił błąd przy zapisie: {}").format(e))

    btn_zapisz.clicked.connect(zapisz)
    btn_anuluj.clicked.connect(dialog.reject)

    dialog.exec()
