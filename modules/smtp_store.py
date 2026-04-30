import os
import sqlite3
from cryptography.fernet import Fernet

# --- KONFIGURACJA ŚCIEŻEK ---
HOME_DIR = os.path.join(os.path.expanduser("~"), ".SerwisApp")
if not os.path.exists(HOME_DIR):
    os.makedirs(HOME_DIR)

SMTP_DB = os.path.join(HOME_DIR, "ptms.db")
KEY_FILE = os.path.join(HOME_DIR, "secret.key")

# --- INICJALIZACJA KLUCZA SZYFROWANIA ---
if not os.path.exists(KEY_FILE):
    key = Fernet.generate_key()
    with open(KEY_FILE, "wb") as f:
        f.write(key)
else:
    with open(KEY_FILE, "rb") as f:
        key = f.read()

fernet = Fernet(key)

def ensure_table():
    """Zapewnia istnienie wymaganej struktury lub ustawienia."""
    conn = sqlite3.connect(SMTP_DB)
    c = conn.cursor()
    c.execute('''
    CREATE TABLE IF NOT EXISTS email_config (
        id INTEGER PRIMARY KEY,
        smtp_server TEXT NOT NULL,
        smtp_port INTEGER NOT NULL,
        smtp_email TEXT NOT NULL,
        smtp_password TEXT NOT NULL
    )
    ''')
    conn.commit()
    conn.close()

def save_smtp(server: str, port: int, email: str, password: str):
    """Zapisuje dane lub ustawienia."""
    ensure_table()
    encrypted_pw = fernet.encrypt(password.encode()).decode()
    conn = sqlite3.connect(SMTP_DB)
    c = conn.cursor()
    c.execute("DELETE FROM email_config")
    c.execute(
        "INSERT INTO email_config (smtp_server, smtp_port, smtp_email, smtp_password) VALUES (?, ?, ?, ?)",
        (server, port, email, encrypted_pw)
    )
    conn.commit()
    conn.close()

def load_smtp():
    """Wczytuje dane lub ustawienia potrzebne do działania."""
    ensure_table()
    conn = sqlite3.connect(SMTP_DB)
    c = conn.cursor()
    c.execute("SELECT smtp_server, smtp_port, smtp_email, smtp_password FROM email_config LIMIT 1")
    row = c.fetchone()
    conn.close()

    if row:
        server, port, email, encrypted_pw = row
        try:
            password = fernet.decrypt(encrypted_pw.encode()).decode()
        except Exception:
            password = ""
        return server, port, email, password
    return None, None, None, None

def get_smtp_config():
    """Pomocnicza funkcja zwracająca słownik (używana np. w config.py)"""
    server, port, email, password = load_smtp()
    return {
        "server": server or "",
        "port": port or 587,
        "email": email or "",
        "password": password or ""
    }
