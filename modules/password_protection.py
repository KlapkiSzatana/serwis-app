import os
import sys
import sqlite3
from PySide6 import QtWidgets, QtCore
from cryptography.fernet import Fernet

# --- KONFIGURACJA ---
HOME_DIR = os.path.join(os.path.expanduser("~"), ".SerwisApp")
CONFIG_DIR = os.path.join(HOME_DIR, "config")
KEY_FILE = os.path.join(HOME_DIR, "password_secret.key")
PASS_DB = os.path.join(HOME_DIR, "users.db")

# Zmienne globalne sesji
CURRENT_USER = None
CURRENT_USER_IS_SUPER = False

# Stałe pytania
PYTANIE_1 = "Imię zwierzaka"
PYTANIE_2 = "Ulubiony kolor"
PYTANIE_3 = "Pseudonim z dzieciństwa"

try:
    _("Test")
except NameError:
    def _(text):
        """Zwraca tekst bez tłumaczenia, gdy mechanizm i18n nie jest aktywny."""
        return text

# --- NARZĘDZIA ---

def ensure_dirs():
    """Zapewnia istnienie wymaganej struktury lub ustawienia."""
    os.makedirs(HOME_DIR, exist_ok=True)
    os.makedirs(CONFIG_DIR, exist_ok=True)

def get_fernet():
    """Zwraca wymagane dane lub ustawienia."""
    ensure_dirs()
    if not os.path.exists(KEY_FILE):
        key = Fernet.generate_key()
        with open(KEY_FILE, "wb") as f:
            f.write(key)
    else:
        with open(KEY_FILE, "rb") as f:
            key = f.read()
    return Fernet(key)

def wymagany_admin(parent=None):
    """Realizuje logikę operacji wymagany admin."""
    if CURRENT_USER_IS_SUPER:
        return True
    QtWidgets.QMessageBox.warning(
        parent,
        _("Odmowa dostępu"),
        _("Ta operacja wymaga uprawnień Administratora.\nSkontaktuj się z przełożonym.")
    )
    return False

# --- BAZA DANYCH ---

def init_users_table():
    """Inicjalizuje wymagane zasoby lub strukturę danych."""
    ensure_dirs()
    conn = sqlite3.connect(PASS_DB)
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            pass_encrypted TEXT NOT NULL,
            active INTEGER NOT NULL DEFAULT 1,
            is_superuser INTEGER NOT NULL DEFAULT 0,
            password_required INTEGER NOT NULL DEFAULT 1
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS recovery (
            id INTEGER PRIMARY KEY,
            q1 TEXT, a1_enc TEXT,
            q2 TEXT, a2_enc TEXT,
            q3 TEXT, a3_enc TEXT
        )
    """)

    try:
        c.execute("SELECT is_superuser FROM users LIMIT 1")
    except sqlite3.OperationalError:
        c.execute("ALTER TABLE users ADD COLUMN is_superuser INTEGER NOT NULL DEFAULT 0")
        c.execute("UPDATE users SET is_superuser = 1 WHERE id = (SELECT min(id) FROM users)")

    try:
        c.execute("SELECT password_required FROM users LIMIT 1")
    except sqlite3.OperationalError:
        c.execute("ALTER TABLE users ADD COLUMN password_required INTEGER NOT NULL DEFAULT 1")

    conn.commit()
    conn.close()

# --- CRUD USER ---

def db_add_user(username, password, active=1, is_superuser=0):
    """Realizuje logikę operacji db add user."""
    f = get_fernet()
    enc_pass = f.encrypt(password.strip().encode()).decode()
    try:
        conn = sqlite3.connect(PASS_DB)
        c = conn.cursor()
        c.execute("INSERT INTO users (username, pass_encrypted, active, is_superuser, password_required) VALUES (?, ?, ?, ?, 1)",
                  (username, enc_pass, active, is_superuser))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False

def db_update_pass(username, new_password):
    """Realizuje logikę operacji db update pass."""
    f = get_fernet()
    enc_pass = f.encrypt(new_password.strip().encode()).decode()
    conn = sqlite3.connect(PASS_DB)
    c = conn.cursor()
    c.execute("UPDATE users SET pass_encrypted = ? WHERE username = ?", (enc_pass, username))
    conn.commit()
    conn.close()

def db_update_status(username, active):
    """Realizuje logikę operacji db update status."""
    conn = sqlite3.connect(PASS_DB)
    c = conn.cursor()
    c.execute("UPDATE users SET active = ? WHERE username = ?", (1 if active else 0, username))
    conn.commit()
    conn.close()

def db_update_login_requirement(username, required):
    """Realizuje logikę operacji db update login requirement."""
    conn = sqlite3.connect(PASS_DB)
    c = conn.cursor()
    c.execute("UPDATE users SET password_required = ? WHERE username = ?", (1 if required else 0, username))
    conn.commit()
    conn.close()

def db_delete_user(username):
    """Realizuje logikę operacji db delete user."""
    conn = sqlite3.connect(PASS_DB)
    c = conn.cursor()
    c.execute("DELETE FROM users WHERE username = ?", (username,))
    conn.commit()
    conn.close()

def db_get_all_users():
    """Realizuje logikę operacji db get all users."""
    if not os.path.exists(PASS_DB): return []
    conn = sqlite3.connect(PASS_DB)
    c = conn.cursor()
    c.execute("SELECT username, active, is_superuser, password_required FROM users ORDER BY is_superuser DESC, username ASC")
    rows = c.fetchall()
    conn.close()
    return rows

def db_get_active_users():
    """Realizuje logikę operacji db get active users."""
    if not os.path.exists(PASS_DB): return []
    conn = sqlite3.connect(PASS_DB)
    c = conn.cursor()
    # ZMIANA: Pobieramy też is_superuser, żeby wiedzieć komu pokazać przycisk awaryjny
    c.execute("SELECT username, password_required, is_superuser FROM users WHERE active = 1 ORDER BY username")
    rows = c.fetchall()
    conn.close()
    return rows

def db_verify_user(username, password):
    """Realizuje logikę operacji db verify user."""
    if not os.path.exists(PASS_DB): return False, False
    conn = sqlite3.connect(PASS_DB)
    c = conn.cursor()
    c.execute("SELECT pass_encrypted, is_superuser, password_required FROM users WHERE username = ? AND active = 1", (username,))
    row = c.fetchone()
    conn.close()

    if row:
        enc_pass, is_super, pass_req = row
        if pass_req == 0 and not password:
            return True, bool(is_super)

        f = get_fernet()
        try:
            decrypted = f.decrypt(enc_pass.encode()).decode()
            if decrypted == password:
                return True, bool(is_super)
        except:
            pass
    return False, False

def db_check_password_only(username, password):
    """Realizuje logikę operacji db check password only."""
    if not os.path.exists(PASS_DB): return False
    conn = sqlite3.connect(PASS_DB)
    c = conn.cursor()
    c.execute("SELECT pass_encrypted FROM users WHERE username = ?", (username,))
    row = c.fetchone()
    conn.close()

    if row:
        f = get_fernet()
        try:
            decrypted = f.decrypt(row[0].encode()).decode()
            return decrypted == password
        except:
            pass
    return False

def db_count_superusers():
    """Realizuje logikę operacji db count superusers."""
    conn = sqlite3.connect(PASS_DB)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users WHERE is_superuser = 1 AND active = 1")
    count = c.fetchone()[0]
    conn.close()
    return count

# --- CRUD RECOVERY ---

def db_save_recovery_questions(q1, a1, q2, a2, q3, a3):
    """Realizuje logikę operacji db save recovery questions."""
    f = get_fernet()
    a1_enc = f.encrypt(a1.strip().lower().encode()).decode()
    a2_enc = f.encrypt(a2.strip().lower().encode()).decode()
    a3_enc = f.encrypt(a3.strip().lower().encode()).decode()

    conn = sqlite3.connect(PASS_DB)
    c = conn.cursor()
    c.execute("DELETE FROM recovery")
    c.execute("INSERT INTO recovery (id, q1, a1_enc, q2, a2_enc, q3, a3_enc) VALUES (1, ?, ?, ?, ?, ?, ?)",
              (q1, a1_enc, q2, a2_enc, q3, a3_enc))
    conn.commit()
    conn.close()

def db_get_recovery_questions():
    """Realizuje logikę operacji db get recovery questions."""
    conn = sqlite3.connect(PASS_DB)
    c = conn.cursor()
    c.execute("SELECT q1, a1_enc, q2, a2_enc, q3, a3_enc FROM recovery WHERE id=1")
    row = c.fetchone()
    conn.close()
    return row

def db_verify_recovery_answers(ans1, ans2, ans3):
    """Realizuje logikę operacji db verify recovery answers."""
    row = db_get_recovery_questions()
    if not row: return False

    _, a1_enc, _, a2_enc, _, a3_enc = row
    f = get_fernet()
    try:
        real_a1 = f.decrypt(a1_enc.encode()).decode()
        real_a2 = f.decrypt(a2_enc.encode()).decode()
        real_a3 = f.decrypt(a3_enc.encode()).decode()
        c1 = (real_a1 == ans1.strip().lower())
        c2 = (real_a2 == ans2.strip().lower())
        c3 = (real_a3 == ans3.strip().lower())
        return c1 and c2 and c3
    except Exception as e:
        print(f"Błąd weryfikacji pytań: {e}")
        return False

def potwierdz_tozsamosc_admina(parent):
    """Potwierdza uprawnienia lub zgodność danych."""
    if not CURRENT_USER: return False
    if not CURRENT_USER_IS_SUPER: return False

    pass_text, ok = QtWidgets.QInputDialog.getText(
        parent, _("Wymagana Autoryzacja"),
        _("Potwierdź operację wpisując SWOJE hasło administratora:"),
        QtWidgets.QLineEdit.EchoMode.Password
    )

    if not ok: return False

    if db_check_password_only(CURRENT_USER, pass_text):
        return True
    else:
        QtWidgets.QMessageBox.warning(parent, _("Błąd"), _("Niepoprawne hasło."))
        return False

# --- OKNA DIALOGOWE ---

class SetupRecoveryDialog(QtWidgets.QDialog):
    """Dialog obsługujący wydzielony fragment funkcjonalności aplikacji."""
    def __init__(self, parent=None):
        """Inicjalizuje obiekt i przygotowuje jego stan początkowy."""
        super().__init__(parent)
        self.setWindowTitle(_("Konfiguracja Odzyskiwania Dostępu"))
        self.setFixedWidth(400)
        self.setModal(True)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(QtWidgets.QLabel(_("Odpowiedz na 3 pytania bezpieczeństwa.\nBędą one wymagane do awaryjnego odblokowania programu.")))
        layout.addSpacing(10)

        layout.addWidget(QtWidgets.QLabel(f"1. {PYTANIE_1}:"))
        self.a1_edit = QtWidgets.QLineEdit(); self.a1_edit.setPlaceholderText(_("Twoja odpowiedź..."))
        layout.addWidget(self.a1_edit); layout.addSpacing(5)

        layout.addWidget(QtWidgets.QLabel(f"2. {PYTANIE_2}:"))
        self.a2_edit = QtWidgets.QLineEdit(); self.a2_edit.setPlaceholderText(_("Twoja odpowiedź..."))
        layout.addWidget(self.a2_edit); layout.addSpacing(5)

        layout.addWidget(QtWidgets.QLabel(f"3. {PYTANIE_3}:"))
        self.a3_edit = QtWidgets.QLineEdit(); self.a3_edit.setPlaceholderText(_("Twoja odpowiedź..."))
        layout.addWidget(self.a3_edit); layout.addSpacing(15)

        btn = QtWidgets.QPushButton(_("Zapisz i Zakończ"))
        btn.clicked.connect(self.save)
        layout.addWidget(btn)
        self.setLayout(layout)

    def save(self):
        """Zapisuje wprowadzone dane."""
        a1, a2, a3 = self.a1_edit.text(), self.a2_edit.text(), self.a3_edit.text()
        if not all([a1, a2, a3]):
            QtWidgets.QMessageBox.warning(self, _("Błąd"), _("Musisz podać wszystkie odpowiedzi!"))
            return
        db_save_recovery_questions(PYTANIE_1, a1, PYTANIE_2, a2, PYTANIE_3, a3)
        QtWidgets.QMessageBox.information(self, _("Sukces"), _("Odpowiedzi bezpieczeństwa zostały zapisane."))
        self.accept()

class EmergencyRecoveryDialog(QtWidgets.QDialog):
    """Dialog obsługujący wydzielony fragment funkcjonalności aplikacji."""
    def __init__(self, parent=None):
        """Inicjalizuje obiekt i przygotowuje jego stan początkowy."""
        super().__init__(parent)
        self.setWindowTitle(_("Awaryjne Odblokowanie"))
        self.setFixedWidth(400)

        data = db_get_recovery_questions()
        if not data:
            QtWidgets.QMessageBox.critical(self, _("Błąd"), _("Pytania bezpieczeństwa nie zostały skonfigurowane!"))
            self.reject(); return

        self.q1_txt, self.q2_txt, self.q3_txt = data[0], data[2], data[4]

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(QtWidgets.QLabel(_("Odpowiedz na pytania bezpieczeństwa, aby uzyskać dostęp tymczasowy.")))
        layout.addSpacing(10)

        layout.addWidget(QtWidgets.QLabel(f"1. {self.q1_txt}"))
        self.a1_in = QtWidgets.QLineEdit(); layout.addWidget(self.a1_in)
        layout.addWidget(QtWidgets.QLabel(f"2. {self.q2_txt}"))
        self.a2_in = QtWidgets.QLineEdit(); layout.addWidget(self.a2_in)
        layout.addWidget(QtWidgets.QLabel(f"3. {self.q3_txt}"))
        self.a3_in = QtWidgets.QLineEdit(); layout.addWidget(self.a3_in)

        layout.addSpacing(15)
        btn = QtWidgets.QPushButton(_("Odblokuj"))
        btn.clicked.connect(self.verify)
        layout.addWidget(btn)
        self.setLayout(layout)

    def verify(self):
        """Weryfikuje dane wejściowe użytkownika."""
        if db_verify_recovery_answers(self.a1_in.text(), self.a2_in.text(), self.a3_in.text()):
            self.accept()
        else:
            QtWidgets.QMessageBox.warning(self, _("Błąd"), _("Niepoprawne odpowiedzi."))

# --- SETUP FLOW ---

def wymus_stworzenie_superusera(parent=None):
    """Wymusza wykonanie wymaganej akcji."""
    while True:
        QtWidgets.QMessageBox.information(parent, _("Konfiguracja"),
            _("To pierwsze uruchomienie menedżera haseł.\nMusisz utworzyć konto Administratora."))

        name, ok = QtWidgets.QInputDialog.getText(parent, _("Administrator"), _("Nazwa Super Użytkownika:"))
        if not ok or not name.strip(): return False

        pass1, ok1 = QtWidgets.QInputDialog.getText(parent, _("Hasło"), _("Hasło dla") + f" {name}:", QtWidgets.QLineEdit.EchoMode.Password)
        if not ok1 or not pass1.strip(): continue

        pass2, ok2 = QtWidgets.QInputDialog.getText(parent, _("Potwierdź"), _("Powtórz hasło:"), QtWidgets.QLineEdit.EchoMode.Password)
        if pass1 != pass2:
            QtWidgets.QMessageBox.warning(parent, _("Błąd"), _("Hasła nie są identyczne."))
            continue

        if db_add_user(name.strip(), pass1, is_superuser=1):
            QtWidgets.QMessageBox.information(parent, _("Sukces"), _("Konto utworzone. Teraz podaj odpowiedzi na pytania bezpieczeństwa."))
            SetupRecoveryDialog(parent).exec()
            return True
        else:
            QtWidgets.QMessageBox.warning(parent, _("Błąd"), _("Błąd bazy danych."))

class ChangeOwnPasswordDialog(QtWidgets.QDialog):
    """Dialog obsługujący wydzielony fragment funkcjonalności aplikacji."""
    def __init__(self, username, parent=None):
        """Inicjalizuje obiekt i przygotowuje jego stan początkowy."""
        super().__init__(parent)
        self.setWindowTitle(_("Zmiana Hasła"))
        self.username = username
        self.setFixedWidth(300)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(QtWidgets.QLabel(_("Stare hasło:")))
        self.inp_old = QtWidgets.QLineEdit(); self.inp_old.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
        layout.addWidget(self.inp_old)

        layout.addWidget(QtWidgets.QLabel(_("Nowe hasło:")))
        self.inp_new1 = QtWidgets.QLineEdit(); self.inp_new1.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
        layout.addWidget(self.inp_new1)

        layout.addWidget(QtWidgets.QLabel(_("Powtórz nowe hasło:")))
        self.inp_new2 = QtWidgets.QLineEdit(); self.inp_new2.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
        layout.addWidget(self.inp_new2)

        layout.addSpacing(10)
        btn_box = QtWidgets.QHBoxLayout()
        self.btn_ok = QtWidgets.QPushButton(_("Zmień Hasło"))
        self.btn_ok.clicked.connect(self.accept_change)
        self.btn_cancel = QtWidgets.QPushButton(_("Anuluj"))
        self.btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(self.btn_cancel); btn_box.addWidget(self.btn_ok)
        layout.addLayout(btn_box)
        self.setLayout(layout)

    def accept_change(self):
        """Realizuje logikę operacji accept change w klasie ChangeOwnPasswordDialog."""
        old = self.inp_old.text()
        n1 = self.inp_new1.text()
        n2 = self.inp_new2.text()

        if not db_check_password_only(self.username, old):
            QtWidgets.QMessageBox.warning(self, _("Błąd"), _("Stare hasło jest niepoprawne."))
            return
        if not n1.strip():
            QtWidgets.QMessageBox.warning(self, _("Błąd"), _("Hasło nie może być puste."))
            return
        if n1 != n2:
            QtWidgets.QMessageBox.warning(self, _("Błąd"), _("Nowe hasła nie są identyczne."))
            return

        db_update_pass(self.username, n1)
        QtWidgets.QMessageBox.information(self, _("Sukces"), _("Hasło zostało zmienione."))
        self.accept()

class LoginDialog(QtWidgets.QDialog):
    """Dialog obsługujący wydzielony fragment funkcjonalności aplikacji."""
    def __init__(self, users_list_tuples, parent=None):
        """Inicjalizuje obiekt i przygotowuje jego stan początkowy."""
        super().__init__(parent)
        self.setWindowTitle(_("Logowanie - SerwisApp"))
        self.setFixedSize(300, 180)
        self.username = None
        self.is_superuser = False
        self.users_data = users_list_tuples

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(QtWidgets.QLabel(_("Użytkownik:")))
        self.combo_user = QtWidgets.QComboBox()
        for u, req, is_super in self.users_data:
            # Zapisujemy tuple (req, is_super) w UserData comboboxa
            self.combo_user.addItem(u, (req, is_super))

        self.combo_user.currentIndexChanged.connect(self.on_user_change)
        layout.addWidget(self.combo_user)

        self.lbl_pass = QtWidgets.QLabel(_("Hasło:"))
        layout.addWidget(self.lbl_pass)
        self.pass_input = QtWidgets.QLineEdit()
        self.pass_input.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
        layout.addWidget(self.pass_input)

        layout.addSpacing(10)
        btn_layout = QtWidgets.QHBoxLayout()
        self.btn_login = QtWidgets.QPushButton(_("Zaloguj"))
        self.btn_login.clicked.connect(self.check_login)
        self.btn_login.setDefault(True)
\
        self.btn_exit = QtWidgets.QPushButton(_("Wyjdź"))
        self.btn_exit.clicked.connect(self.reject)
        self.btn_exit.setAutoDefault(False)

        btn_layout.addWidget(self.btn_exit); btn_layout.addWidget(self.btn_login)
        layout.addLayout(btn_layout)

        self.lbl_forgot = QtWidgets.QLabel(f"<a href='#'>{_('Awaryjne odblokowanie')}</a>")
        self.lbl_forgot.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.lbl_forgot.linkActivated.connect(self.emergency_mode)
        layout.addWidget(self.lbl_forgot)

        self.setLayout(layout)
        self.on_user_change()

    def on_user_change(self):
        # Pobieramy dane z comboboxa: (req, is_super)
        """Obsługuje zmianę stanu lub zdarzenie interfejsu."""
        data = self.combo_user.currentData()
        if not data: return

        req, is_super = data

        # 1. Obsługa pola hasła
        if req == 0:
            self.pass_input.setPlaceholderText(_("(Hasło nie jest wymagane)"))
            self.pass_input.setFocus()
        else:
            self.pass_input.setPlaceholderText("")
            self.pass_input.clear()
            self.pass_input.setFocus()

        # 2. Ukrywanie linku awaryjnego dla nie-administratorów
        self.lbl_forgot.setVisible(bool(is_super))

    def check_login(self):
        """Realizuje logikę operacji check login w klasie LoginDialog."""
        user = self.combo_user.currentText()
        password = self.pass_input.text()
        valid, is_super = db_verify_user(user, password)
        if valid:
            self.username = user
            self.is_superuser = is_super
            self.accept()
        else:
            QtWidgets.QMessageBox.warning(self, _("Błąd"), _("Niepoprawne hasło."))
            self.pass_input.clear()
            self.pass_input.setFocus()

    def emergency_mode(self):
        """Realizuje logikę operacji emergency mode w klasie LoginDialog."""
        if not db_get_recovery_questions():
             QtWidgets.QMessageBox.critical(self, _("Błąd"), _("Odzyskiwanie nie zostało skonfigurowane."))
             return

        dlg = EmergencyRecoveryDialog(self)
        if dlg.exec():
            QtWidgets.QMessageBox.information(self, _("Sukces"), _("Dostęp przyznany. Jesteś tymczasowym Administratorem."))
            menedzer_hasel(self, force_admin=True)
            # Odśwież listę po powrocie
            self.users_data = db_get_active_users()
            self.combo_user.clear()
            for u, req, is_super in self.users_data:
                self.combo_user.addItem(u, (req, is_super))
            self.on_user_change()

# --- GUI: MENEDŻER HASEŁ ---

class PasswordManagerDialog(QtWidgets.QDialog):
    """Dialog obsługujący wydzielony fragment funkcjonalności aplikacji."""
    def __init__(self, parent=None, force_admin=False):
        """Inicjalizuje obiekt i przygotowuje jego stan początkowy."""
        super().__init__(parent)
        self.setWindowTitle(_("Zarządzanie Użytkownikami"))
        self.resize(650, 400)
        self.is_admin = force_admin or CURRENT_USER_IS_SUPER

        # Flaga trybu awaryjnego:
        self.is_emergency = (CURRENT_USER is None)

        layout = QtWidgets.QVBoxLayout()

        # --- SEKCJA MOJE KONTO ---
        me_lbl = _("Moje Konto")
        if self.is_emergency: me_lbl += _(" (Tryb Awaryjny)")
        elif CURRENT_USER: me_lbl += f" ({CURRENT_USER})"

        grp_me = QtWidgets.QGroupBox(me_lbl)
        lay_me = QtWidgets.QVBoxLayout()

        self.chk_my_login_req = QtWidgets.QCheckBox(_("Wymagaj podawania hasła przy logowaniu"))

        # Przycisk zmiany hasła
        self.btn_my_pass = QtWidgets.QPushButton(_("Zmień moje hasło"))
        self.btn_my_pass.setStyleSheet("text-align: left; padding: 5px;")

        if not self.is_emergency and CURRENT_USER:
            my_data = [x for x in db_get_all_users() if x[0] == CURRENT_USER]
            if my_data: self.chk_my_login_req.setChecked(bool(my_data[0][3]))
            self.chk_my_login_req.clicked.connect(self.action_toggle_my_requirement)
            self.btn_my_pass.clicked.connect(self.action_change_my_pass)
        else:
            # W trybie awaryjnym blokujemy "Moje Konto"
            self.chk_my_login_req.setEnabled(False)
            self.btn_my_pass.setEnabled(False)
            self.btn_my_pass.setText(_("Aby zmienić hasło, wybierz użytkownika z listy i kliknij Resetuj"))

        lay_me.addWidget(self.chk_my_login_req)
        lay_me.addWidget(self.btn_my_pass)
        grp_me.setLayout(lay_me)
        layout.addWidget(grp_me)

        # --- TABELA UŻYTKOWNIKÓW ---
        lbl_users = QtWidgets.QLabel(_("Lista Użytkowników")); lbl_users.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout.addWidget(lbl_users)

        self.table = QtWidgets.QTableWidget(); self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels([_("Użytkownik"), _("Rola"), _("Logowanie"), _("Status")])
        self.table.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        layout.addWidget(self.table)

        btn_box = QtWidgets.QHBoxLayout()
        self.btn_add = QtWidgets.QPushButton(_("Dodaj"))
        self.btn_reset = QtWidgets.QPushButton(_("Resetuj Hasło")) # Zmieniono nazwę
        self.btn_toggle = QtWidgets.QPushButton(_("Blokuj/Odblokuj"))
        self.btn_del = QtWidgets.QPushButton(_("Usuń"))

        self.btn_add.clicked.connect(self.action_add)
        self.btn_reset.clicked.connect(self.action_reset_other_pass)
        self.btn_toggle.clicked.connect(self.action_toggle_status)
        self.btn_del.clicked.connect(self.action_delete)

        btn_box.addWidget(self.btn_add); btn_box.addWidget(self.btn_reset)
        btn_box.addWidget(self.btn_toggle); btn_box.addWidget(self.btn_del)
        layout.addLayout(btn_box)

        if self.is_admin:
            info_txt = _("Jesteś Administratorem. Masz pełną kontrolę."); info_col = "green"
        else:
            info_txt = _("Jesteś zwykłym użytkownikiem. Tabela jest tylko do odczytu."); info_col = "gray"
            self.btn_add.setEnabled(False); self.btn_reset.setEnabled(False)
            self.btn_toggle.setEnabled(False); self.btn_del.setEnabled(False)

        info_lbl = QtWidgets.QLabel(info_txt); info_lbl.setStyleSheet(f"color: {info_col}; font-weight: bold;")
        layout.addWidget(info_lbl)
        self.setLayout(layout)
        self.refresh_list()

    def refresh_list(self):
        """Realizuje logikę operacji refresh list w klasie PasswordManagerDialog."""
        users = db_get_all_users()
        self.table.setRowCount(0)
        for u, active, is_super, pass_req in users:
            row = self.table.rowCount(); self.table.insertRow(row)
            display_name = u + (_(" (Ty)") if u == CURRENT_USER else "")

            item_name = QtWidgets.QTableWidgetItem(display_name)
            item_role = QtWidgets.QTableWidgetItem(_("ADMINISTRATOR") if is_super else _("Użytkownik"))
            item_req = QtWidgets.QTableWidgetItem(_("Hasło") if pass_req else _("Bez hasła"))
            item_status = QtWidgets.QTableWidgetItem(_("Aktywny") if active else _("Zablokowany"))

            self.table.setItem(row, 0, item_name); self.table.setItem(row, 1, item_role)
            self.table.setItem(row, 2, item_req); self.table.setItem(row, 3, item_status)

            item_name.setData(QtCore.Qt.UserRole, u)
            item_name.setData(QtCore.Qt.UserRole + 1, active)
            item_name.setData(QtCore.Qt.UserRole + 2, is_super)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.Interactive); self.table.setColumnWidth(1, 130)
        header.setSectionResizeMode(2, QtWidgets.QHeaderView.Interactive); self.table.setColumnWidth(2, 100)
        header.setSectionResizeMode(3, QtWidgets.QHeaderView.Interactive); self.table.setColumnWidth(3, 100)

    def get_selected_data(self):
        """Zwraca wymagane dane lub ustawienia."""
        rows = self.table.selectionModel().selectedRows()
        if not rows: return None, None, None
        idx = rows[0].row()
        item = self.table.item(idx, 0)
        return item.data(QtCore.Qt.UserRole), item.data(QtCore.Qt.UserRole + 1), item.data(QtCore.Qt.UserRole + 2)

    def action_toggle_my_requirement(self):
        """Realizuje logikę operacji action toggle my requirement w klasie PasswordManagerDialog."""
        if not CURRENT_USER: return
        db_update_login_requirement(CURRENT_USER, self.chk_my_login_req.isChecked())
        self.refresh_list()

    def action_change_my_pass(self):
        """Realizuje logikę operacji action change my pass w klasie PasswordManagerDialog."""
        if not CURRENT_USER: return
        ChangeOwnPasswordDialog(CURRENT_USER, self).exec()

    def action_add(self):
        """Realizuje logikę operacji action add w klasie PasswordManagerDialog."""
        if not self.is_admin: return
        name, ok = QtWidgets.QInputDialog.getText(self, _("Nowy użytkownik"), _("Nazwa użytkownika:"))
        if not ok or not name.strip(): return
        pass1, ok1 = QtWidgets.QInputDialog.getText(self, _("Hasło"), _("Hasło dla") + f" {name.strip()}:", QtWidgets.QLineEdit.EchoMode.Password)
        if not ok1: return

        is_super = 0
        if QtWidgets.QMessageBox.question(self, _("Uprawnienia"), _("Czy ten użytkownik ma być Administratorem?"),
           QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No) == QtWidgets.QMessageBox.Yes: is_super = 1

        if db_add_user(name.strip(), pass1, is_superuser=is_super):
            self.refresh_list()
            QtWidgets.QMessageBox.information(self, _("Sukces"), _("Użytkownik dodany."))
        else: QtWidgets.QMessageBox.warning(self, _("Błąd"), _("Taki użytkownik już istnieje."))

    def action_reset_other_pass(self):
        """Realizuje logikę operacji action reset other pass w klasie PasswordManagerDialog."""
        if not self.is_admin: return
        # POPRAWKA CRASHU (używamy _ign zamiast _)
        target_user, _ign1, _ign2 = self.get_selected_data()
        if not target_user: return

        if target_user == CURRENT_USER and not self.is_emergency:
             QtWidgets.QMessageBox.information(self, _("Info"), _("Użyj opcji 'Zmień moje hasło'."))
             return

        # W trybie awaryjnym pomijamy "potwierdz_tozsamosc_admina"
        if not self.is_emergency:
            if not potwierdz_tozsamosc_admina(self): return

        pass1, ok = QtWidgets.QInputDialog.getText(self, _("Reset Hasła"), _("Nowe hasło dla") + f" {target_user}:", QtWidgets.QLineEdit.EchoMode.Password)
        if ok and pass1:
            db_update_pass(target_user, pass1); db_update_login_requirement(target_user, 1)
            self.refresh_list()
            QtWidgets.QMessageBox.information(self, _("Sukces"), _("Hasło zostało zmienione."))

    def action_toggle_status(self):
        """Realizuje logikę operacji action toggle status w klasie PasswordManagerDialog."""
        if not self.is_admin: return
        target_user, active, _ = self.get_selected_data()
        if not target_user: return
        if target_user == CURRENT_USER and not self.is_emergency:
             QtWidgets.QMessageBox.warning(self, _("Błąd"), _("Nie możesz zablokować samego siebie."))
             return
        if not self.is_emergency:
            if not potwierdz_tozsamosc_admina(self): return

        db_update_status(target_user, not active)
        self.refresh_list()

    def action_delete(self):
        """Realizuje logikę operacji action delete w klasie PasswordManagerDialog."""
        if not self.is_admin: return
        target_user, _, is_super = self.get_selected_data()
        if not target_user: return
        if target_user == CURRENT_USER and not self.is_emergency:
             QtWidgets.QMessageBox.warning(self, _("Błąd"), _("Nie możesz usunąć samego siebie."))
             return
        if is_super and db_count_superusers() <= 1:
             QtWidgets.QMessageBox.critical(self, _("Błąd"), _("To ostatni aktywny Administrator."))
             return
        if not self.is_emergency:
            if not potwierdz_tozsamosc_admina(self): return

        if QtWidgets.QMessageBox.question(self, _("Potwierdzenie"), _("Czy usunąć?") + f" {target_user}?", QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No) == QtWidgets.QMessageBox.Yes:
            db_delete_user(target_user)
            self.refresh_list()

# --- GŁÓWNE FUNKCJE ---

def sprawdz_haslo_przy_starcie(parent=None):
    """Sprawdza warunki wymagane do wykonania operacji."""
    global CURRENT_USER, CURRENT_USER_IS_SUPER
    init_users_table()

    if not db_get_all_users():
        CURRENT_USER = "Admin (Startowy)"
        CURRENT_USER_IS_SUPER = True
        return

    active_users = db_get_active_users()
    if not active_users:
        QtWidgets.QMessageBox.critical(parent, _("Błąd"), _("Brak aktywnych użytkowników."))
        sys.exit(0)

    dialog = LoginDialog(active_users, parent)
    if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
        CURRENT_USER = dialog.username
        CURRENT_USER_IS_SUPER = dialog.is_superuser
        return
    else:
        sys.exit(0)

def menedzer_hasel(parent=None, force_admin=False):
    """Realizuje logikę operacji menedzer hasel."""
    init_users_table()
    if not db_get_all_users():
        if not wymus_stworzenie_superusera(parent): return
        global CURRENT_USER, CURRENT_USER_IS_SUPER
        users = db_get_all_users()
        if users:
            CURRENT_USER = users[0][0]; CURRENT_USER_IS_SUPER = True

    dlg = PasswordManagerDialog(parent, force_admin)
    dlg.exec()
