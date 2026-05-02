import configparser
import os
import sqlite3
import sys
import tempfile

APP_VERSION = "2.3.1"
APP_NAME = ""
APP_NAME2 = "SerwisApp"

# --- ŚCIEŻKI I KATALOGI ---
HOME_DIR = os.path.join(os.path.expanduser("~"), ".SerwisApp")
LOGO_DIR = os.path.join(HOME_DIR, "logo")
CONFIG_DIR = os.path.join(HOME_DIR, "config")

# Tworzenie katalogów, jeśli nie istnieją
os.makedirs(HOME_DIR, exist_ok=True)
os.makedirs(LOGO_DIR, exist_ok=True)
os.makedirs(CONFIG_DIR, exist_ok=True)

# --- PLIKI KONFIGURACYJNE I BAZY DANYCH ---
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.ini")
CONFIG_DB = os.path.join(CONFIG_DIR, "config.db")
CONFIG_BAZA_FILE = os.path.join(CONFIG_DIR, "bazadir.json")

def _resolve_base_dir():
    """Realizuje logikę operacji resolve base dir."""
    if getattr(sys, "frozen", False):
        candidates = [
            os.path.dirname(os.path.abspath(sys.executable)),
            getattr(sys, "_MEIPASS", None),
        ]
    else:
        candidates = [
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        ]

    if sys.argv and sys.argv[0]:
        candidates.append(os.path.dirname(os.path.abspath(sys.argv[0])))

    candidates.append(os.path.join(tempfile.gettempdir(), os.path.basename(sys.executable)))

    for base_dir in candidates:
        if base_dir and os.path.exists(os.path.join(base_dir, "resources", "logo", "serwisapp.png")):
            return base_dir

    for base_dir in candidates:
        if base_dir:
            return os.path.abspath(base_dir)

    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

BASE_DIR = _resolve_base_dir()

DB_FILE = os.path.join(HOME_DIR, "zlecenia.db")
SMTP_DB = os.path.join(HOME_DIR, "ptms.db") # Baza do przechowywania konfiguracji email
KEY_FILE = os.path.join(HOME_DIR, "secret.key") # Klucz szyfrowania haseł

# --- SZABLONY I ZASOBY ---
SRC_LOGO_FILE = os.path.join(BASE_DIR, "resources", "logo", "serwisapp.png")
DST_LOGO_FILE = os.path.join(LOGO_DIR, "serwisapp.png")
ICON_FILE = SRC_LOGO_FILE

def get_smtp_config():
    """
    Pobiera konfigurację SMTP z lokalnej bazy lub pliku ini.
    """
    smtp = {
        "server": "smtp.gmail.com",
        "port": 587,
        "email": "",
        "password": ""
    }

    # 1. Próba odczytu z bazy danych (priorytet)
    if os.path.exists(SMTP_DB):
        try:
            conn = sqlite3.connect(SMTP_DB)
            cursor = conn.cursor()
            cursor.execute("SELECT smtp_server, smtp_port, smtp_email, smtp_password FROM email_config LIMIT 1")
            row = cursor.fetchone()
            conn.close()
            if row:
                smtp["server"] = row[0] or smtp["server"]
                smtp["port"] = int(row[1] or smtp["port"])
                smtp["email"] = row[2] or ""
                smtp["password"] = row[3] or ""
                return smtp
        except Exception as e:
            print(f"Błąd odczytu SMTP z bazy: {e}")

    # 2. Fallback do pliku config.ini (kompatybilność wsteczna)
    if os.path.exists(CONFIG_FILE):
        try:
            cfg = configparser.ConfigParser()
            cfg.read(CONFIG_FILE)
            if "EMAIL" in cfg:
                smtp["server"] = cfg["EMAIL"].get("smtp_server", smtp["server"])
                smtp["port"] = cfg["EMAIL"].getint("smtp_port", smtp["port"])
                smtp["email"] = cfg["EMAIL"].get("smtp_email", smtp["email"])
                smtp["password"] = cfg["EMAIL"].get("smtp_password", smtp["password"])
        except Exception as e:
            print(f"Błąd odczytu SMTP z config.ini: {e}")

    return smtp
