import sqlite3
from setup import config


def _get_db_file():
    """Realizuje logikę operacji get db file."""
    return getattr(config, "DB_FILE", "serwis.db")

def init_sms_table():
    """Inicjalizuje wymagane zasoby lub strukturę danych."""
    conn = sqlite3.connect(_get_db_file())
    try:
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS sms_config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                api_token TEXT,
                sender_name TEXT
            )
        ''')
        conn.commit()
    finally:
        conn.close()

def save_sms_config(api_token, sender_name):
    """Zapisuje dane lub ustawienia."""
    init_sms_table()
    conn = sqlite3.connect(_get_db_file())
    try:
        c = conn.cursor()
        c.execute("DELETE FROM sms_config") # Kasujemy starą konfigurację (trzymamy tylko jedną)
        c.execute("INSERT INTO sms_config (api_token, sender_name) VALUES (?, ?)",
                  (api_token, sender_name))
        conn.commit()
    finally:
        conn.close()

def load_sms_config():
    """Wczytuje dane lub ustawienia potrzebne do działania."""
    init_sms_table()
    conn = sqlite3.connect(_get_db_file())
    try:
        c = conn.cursor()
        c.execute("SELECT api_token, sender_name FROM sms_config LIMIT 1")
        row = c.fetchone()
    finally:
        conn.close()

    if row:
        return row[0], row[1]
    return "", ""
