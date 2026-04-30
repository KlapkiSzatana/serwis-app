import os
import json
import sqlite3
import configparser
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QRadioButton, QDialogButtonBox, QFileDialog, QMessageBox
)
from PySide6.QtGui import QIcon
from PySide6.QtCore import QSize
from modules.utils import resource_path

# Zabezpieczenie tłumaczeń
try:
    _("Test")
except NameError:
    def _(text):
        """Zwraca tekst bez tłumaczenia, gdy mechanizm i18n nie jest aktywny."""
        return text

def zapisz_baze(db_path, config_baza_file, local_db):
    """Zapisuje dane lub ustawienia."""
    os.makedirs(os.path.dirname(config_baza_file), exist_ok=True)
    with open(config_baza_file, "w", encoding="utf-8") as f:
        json.dump({"baza": db_path}, f)

def wczytaj_baze(config_baza_file, local_db):
    """Wczytuje dane lub ustawienia."""
    if os.path.exists(config_baza_file):
        try:
            with open(config_baza_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("baza", local_db)
        except (OSError, json.JSONDecodeError):
            return local_db
    return local_db

def wybierz_baze_dialog(parent, config_baza_file, local_db):
    """Pozwala wybrać odpowiedni element lub opcję."""
    dialog = QDialog(parent)
    dialog.setWindowTitle(_("Wybór bazy danych"))
    dialog.setFixedSize(250, 170)
    layout = QVBoxLayout()

    rb_lokalna = QRadioButton(_("Lokalna baza"))
    rb_zdalna = QRadioButton(_("Zdalna baza"))
    rb_lokalna.setChecked(True)

    try:
        rb_lokalna.setIcon(QIcon(resource_path("actions/lokalna.png")))
        rb_zdalna.setIcon(QIcon(resource_path("actions/zdalna.png")))
        rb_lokalna.setIconSize(QSize(34, 34))
        rb_zdalna.setIconSize(QSize(34, 34))
    except Exception:
        pass

    layout.addWidget(rb_lokalna)
    layout.addWidget(rb_zdalna)

    buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
    buttons.button(QDialogButtonBox.StandardButton.Ok).setText(_("Ok"))
    buttons.button(QDialogButtonBox.StandardButton.Cancel).setText(_("Anuluj"))
    layout.addWidget(buttons)

    dialog.setLayout(layout)

    def accept():
        """Zatwierdza dane i finalizuje działanie dialogu."""
        if rb_lokalna.isChecked():
            db_path = local_db
        else:
            file_name, _filter = QFileDialog.getOpenFileName(
                dialog,
                _("Wskaż zdalną bazę SQLite"),
                "",
                _("Pliki SQLite (*.db *.sqlite)")
            )

            if not file_name:
                QMessageBox.warning(dialog, _("Uwaga"), _("Nie wybrano pliku. Pozostajemy na bazie lokalnej."))
                db_path = local_db
            else:
                db_path = file_name

        zapisz_baze(db_path, config_baza_file, local_db)
        dialog.selected_db = db_path
        dialog.accept()

    def reject():
        """Anuluje bieżącą operację dialogu."""
        dialog.reject()
        dialog.selected_db = None

    buttons.accepted.connect(accept)
    buttons.rejected.connect(reject)
    dialog.exec()
    return getattr(dialog, "selected_db", None)

def init_baza(config_baza_file, local_db):
    # 1. Ustal ścieżkę do bazy
    """Inicjalizuje wymagane zasoby lub strukturę danych."""
    db_file_path = wczytaj_baze(config_baza_file, local_db)

    # Jeśli plik wskazany w konfigu nie istnieje, wracamy do lokalnej
    if not os.path.exists(db_file_path) and db_file_path != local_db:
        db_file_path = local_db

    # 2. Połącz z bazą (tworzy plik jeśli nie istnieje)
    conn = sqlite3.connect(db_file_path)
    c = conn.cursor()

    # 3. Utwórz tabele (jeśli nie istnieją) - WSZYSTKIE WYMAGANE PRZEZ PROGRAM

    # Tabela ZLECENIA (Zaktualizowana o 'wystawil')
    c.execute("""
    CREATE TABLE IF NOT EXISTS zlecenia (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        imie_nazwisko TEXT NOT NULL,
        telefon TEXT NOT NULL,
        sprzet TEXT NOT NULL,
        nr_seryjny TEXT NOT NULL,
        opis TEXT NOT NULL,
        uwagi TEXT,
        status TEXT NOT NULL,
        data_zlecenia TEXT NOT NULL,
        email TEXT,
        naprawa_opis TEXT,
        koszt_czesci REAL,
        koszt_uslugi REAL,
        pilne INTEGER DEFAULT 0,
        nr_roczny INTEGER DEFAULT NULL,
        wystawil TEXT
    )
    """)

    # Tabela FIRMA
    c.execute("""
    CREATE TABLE IF NOT EXISTS firma (
        id INTEGER PRIMARY KEY,
        nazwa TEXT NOT NULL,
        adres TEXT NOT NULL,
        telefon TEXT NOT NULL,
        email TEXT NOT NULL,
        nip TEXT,
        godziny_otwarcia TEXT
    )
    """)

    # Tabela SMTP (do maili)
    c.execute("""
    CREATE TABLE IF NOT EXISTS smtp_config (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        server TEXT,
        port INTEGER,
        email TEXT,
        password TEXT
    )
    """)

    # Tabela SMS (do smsapi)
    c.execute("""
        CREATE TABLE IF NOT EXISTS sms_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            api_token TEXT,
            sender_name TEXT
        )
    """)

    # 4. Migracje (dodawanie kolumn do starszych baz)
    # Sprawdzamy jakie kolumny ma tabela 'zlecenia'
    existing_cols = [r[1] for r in c.execute("PRAGMA table_info('zlecenia')").fetchall()]

    columns_to_check = [
        ("email", "TEXT"),
        ("naprawa_opis", "TEXT"),
        ("koszt_czesci", "REAL"),
        ("koszt_uslugi", "REAL"),
        ("pilne", "INTEGER DEFAULT 0"),
        ("nr_roczny", "INTEGER DEFAULT NULL"),
        ("wystawil", "TEXT")
    ]

    for col_name, col_type in columns_to_check:
        if col_name not in existing_cols:
            try:
                c.execute(f"ALTER TABLE zlecenia ADD COLUMN {col_name} {col_type}")
            except sqlite3.OperationalError:
                pass

    conn.commit()

    # Jeśli zmieniliśmy ścieżkę na lokalną (bo np. zdalna zniknęła), zapiszmy to w konfigu
    if db_file_path == local_db:
        zapisz_baze(local_db, config_baza_file, local_db)

    return conn, c

def zapisz_filtr(filtr, config_file=None):
    """Zapisuje dane lub ustawienia."""
    if config_file is None:
        from setup import config
        config_file = config.CONFIG_FILE

    cfg = configparser.ConfigParser()
    if os.path.exists(config_file):
        cfg.read(config_file, encoding="utf-8")

    if "FILTER" not in cfg:
        cfg["FILTER"] = {}

    cfg["FILTER"]["ostatni"] = filtr if filtr else ""

    with open(config_file, "w", encoding="utf-8") as f:
        cfg.write(f)

def wczytaj_filtr(config_file=None):
    """Wczytuje dane lub ustawienia."""
    if config_file is None:
        from setup import config
        config_file = config.CONFIG_FILE

    cfg = configparser.ConfigParser()
    if os.path.exists(config_file):
        cfg.read(config_file, encoding="utf-8")
        return cfg.get("FILTER", "ostatni", fallback="Przyjęte")
    return "Przyjęte"
