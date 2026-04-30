import requests
from PySide6.QtWidgets import (QWidget, QLabel, QLineEdit, QTextEdit, QPushButton,
                               QVBoxLayout, QMessageBox, QDialog, QFormLayout)
from PySide6 import QtCore
from modules import sms_store

try:
    _("Test")
except NameError:
    def _(text):
        """Zwraca tekst bez tłumaczenia, gdy mechanizm i18n nie jest aktywny."""
        return text

# Stały adres API dla SMSAPI
SMSAPI_URL = "https://api.smsapi.pl/sms.do"

# --- OKNO KONFIGURACJI ---
class SMSConfigDialog(QDialog):
    """Dialog obsługujący wydzielony fragment funkcjonalności aplikacji."""
    def __init__(self, parent=None):
        """Inicjalizuje obiekt i przygotowuje jego stan początkowy."""
        super().__init__(parent)
        self.setWindowTitle(_("Konfiguracja SMSAPI"))
        self.resize(400, 150)
        self.init_ui()

    def init_ui(self):
        """Buduje i konfiguruje interfejs użytkownika."""
        layout = QFormLayout()

        self.input_token = QLineEdit()
        self.input_token.setEchoMode(QLineEdit.Password)
        self.input_token.setPlaceholderText(_("Twój Token OAuth z panelu SMSAPI"))

        self.input_sender = QLineEdit()
        self.input_sender.setPlaceholderText(_("Pole nadawcy (np. SERWIS lub pozostaw puste)"))
        self.input_sender.setToolTip(_("Zostaw puste lub wpisz nazwę zweryfikowaną w panelu SMSAPI."))

        # Wczytanie obecnych
        token, sender = sms_store.load_sms_config()
        self.input_token.setText(token)
        self.input_sender.setText(sender)

        layout.addRow(_("Token API (OAuth):"), self.input_token)
        layout.addRow(_("Nazwa nadawcy:"), self.input_sender)

        self.btn_save = QPushButton(_("Zapisz"))
        self.btn_save.clicked.connect(self.save_config)
        layout.addRow(self.btn_save)

        self.setLayout(layout)

    def save_config(self):
        """Zapisuje dane lub ustawienia."""
        token = self.input_token.text().strip()
        sender = self.input_sender.text().strip()

        # Zabezpieczenie przed wpisaniem 'eco' przez użytkownika
        if sender.lower() == "eco":
            QMessageBox.warning(self, _("Uwaga"), _("Nazwa 'eco' jest zablokowana przez SMSAPI. Pole zostanie wyczyszczone (ustawi się domyślne 'Test')."))
            sender = ""

        if not token:
            QMessageBox.warning(self, _("Błąd"), _("Token API jest wymagany!"))
            return

        sms_store.save_sms_config(token, sender)
        QMessageBox.information(self, _("Sukces"), _("Konfiguracja SMSAPI zapisana."))
        self.accept()

# --- OKNO WYSYŁANIA ---
class SMSClient(QWidget):
    """Klasa odpowiedzialna za komunikację z usługą lub odbiorcą."""
    def __init__(self, telefon_klienta, nr_zlecenia, sprzet, dane_firmy=None):
        """Inicjalizuje obiekt i przygotowuje jego stan początkowy."""
        super().__init__()

        # Czyszczenie numeru (zostawiamy tylko cyfry)
        raw_phone = ''.join(filter(str.isdigit, str(telefon_klienta)))
        # Jeśli numer ma 9 cyfr, dodajemy '48' (Polska)
        if len(raw_phone) == 9:
            self.telefon = "48" + raw_phone
        else:
            self.telefon = raw_phone

        self.nr_zlecenia = nr_zlecenia
        self.sprzet = sprzet

        # Ładowanie konfigu
        self.api_token, self.sender_name = sms_store.load_sms_config()

        if not self.api_token:
            QMessageBox.critical(self, _("Błąd"), _("Brak konfiguracji SMS! Wejdź w Opcje -> Konfiguracja SMS."))
            self.close()
            return

        self.init_ui()

    def init_ui(self):
        """Buduje i konfiguruje interfejs użytkownika."""
        self.setWindowTitle(_("Wyślij SMS (SMSAPI)"))
        self.resize(400, 300)

        layout = QVBoxLayout()

        layout.addWidget(QLabel(f"{_('Odbiorca:')} +{self.telefon}"))

        self.label_tresc = QLabel(_("Treść wiadomości:"))
        self.input_tresc = QTextEdit()

        # Domyślna treść
        tekst_domyslny = _("Zlecenie nr {nr} dla: {sprzet} jest gotowe do odbioru. Zapraszamy!").format(
            nr=self.nr_zlecenia,
            sprzet=self.sprzet
        )

        self.input_tresc.setText(tekst_domyslny)
        self.input_tresc.textChanged.connect(self.update_counter)

        # Licznik znaków
        self.counter_label = QLabel("Znaków: 0 (1 SMS)")
        self.counter_label.setAlignment(QtCore.Qt.AlignRight)

        # Info o polskich znakach
        self.info_label = QLabel(_("Polskie znaki skracają długość SMS do 70 znaków!"))
        self.info_label.setStyleSheet("color: orange; font-size: 10px;")
        self.info_label.setVisible(False)

        self.btn_wyslij = QPushButton(_("Wyślij SMS"))
        self.btn_wyslij.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 10px;")
        self.btn_wyslij.clicked.connect(self.send_sms)

        layout.addWidget(self.label_tresc)
        layout.addWidget(self.input_tresc)
        layout.addWidget(self.info_label)
        layout.addWidget(self.counter_label)
        layout.addWidget(self.btn_wyslij)

        self.setLayout(layout)
        self.update_counter()

    def update_counter(self):
        """Przelicza liczbę znaków i segmentów wiadomości."""
        txt = self.input_tresc.toPlainText()
        length = len(txt)

        # Sprawdzamy czy są znaki spoza GSM (polskie ogonki)
        has_unicode = any(ord(c) > 127 for c in txt)

        if has_unicode:
            limit = 70
            self.info_label.setVisible(True)
        else:
            limit = 160
            self.info_label.setVisible(False)

        # Obliczenie ilości SMS
        if length == 0:
            sms_count = 0
        elif length <= limit:
            sms_count = 1
        else:
            # W przypadku łączonych SMS, limit jest mniejszy o nagłówki (153 / 67)
            part_limit = 67 if has_unicode else 153
            sms_count = (length // part_limit) + 1

        self.counter_label.setText(f"{_('Znaków:')} {length} ({sms_count} SMS)")

    def send_sms(self):
        """Wysyła dane do zewnętrznej usługi lub odbiorcy."""
        msg_content = self.input_tresc.toPlainText()
        if not msg_content: return

        # ZABEZPIECZENIE PRZED BŁĘDEM 110 (ECO)
        nadawca = self.sender_name.strip()
        # Jeśli pole puste LUB ktoś wpisał "eco" (wielkość liter bez znaczenia) -> ustawiamy "Test"
        if not nadawca or nadawca.lower() == "eco":
            nadawca = "Test"

        try:
            # Parametry wg dokumentacji SMSAPI
            params = {
                "to": self.telefon,
                "message": msg_content,
                "format": "json",
                "from": nadawca  # Tutaj używamy bezpiecznej nazwy
            }

            # Autoryzacja przez nagłówek
            headers = {
                "Authorization": f"Bearer {self.api_token}"
            }

            # Wysłanie z Timeoutem 10 sekund (żeby nie wisiało)
            response = requests.post(SMSAPI_URL, data=params, headers=headers, timeout=10)

            # Obsługa odpowiedzi HTTP
            if response.status_code == 200:
                data = response.json()

                # SMSAPI zwraca 200 nawet jak jest błąd logiczny (np. brak środków), trzeba sprawdzić JSON
                if "list" in data and len(data["list"]) > 0:
                    # Sukces
                    QMessageBox.information(self, _("Sukces"), _("Wiadomość została wysłana!"))
                    self.close()
                elif "error" in data:
                    # Błąd SMSAPI (np. 101 - złe hasło, 103 - brak punktów, 110 - zły nadawca)
                    err_code = data.get("error")
                    err_msg = data.get("message", "Nieznany błąd")

                    if str(err_code) == "110":
                        err_msg += "\n\n(Twoja nazwa nadawcy jest niepoprawna lub niezweryfikowana. Zmień w ustawieniach na pustą lub wpisz 'Test')"

                    QMessageBox.warning(self, _("Błąd SMSAPI"), f"Kod błędu: {err_code}\nOpis: {err_msg}")
                else:
                    # Inny przypadek
                    QMessageBox.warning(self, _("Info"), _("Wysłano, ale odpowiedź serwera jest nietypowa."))
                    self.close()
            elif response.status_code == 401:
                QMessageBox.critical(self, _("Błąd"), _("Nieautoryzowany dostęp (Błąd 401).\nTwój Token jest nieprawidłowy!"))
            else:
                QMessageBox.critical(self, _("Błąd Sieci"), f"Kod HTTP: {response.status_code}\n{response.text}")

        # --- OBSŁUGA BŁĘDÓW POŁĄCZENIA (Fix crasha przy braku neta) ---
        except requests.exceptions.ConnectionError:
            QMessageBox.critical(self, _("Błąd Połączenia"),
                                 _("Nie można połączyć się z serwerem SMSAPI.\n"
                                   "Sprawdź swoje połączenie z internetem."))
        except requests.exceptions.Timeout:
            QMessageBox.warning(self, _("Czas minął"),
                                _("Serwer SMSAPI nie odpowiada (Timeout).\nSpróbuj ponownie później."))
        except Exception as e:
            QMessageBox.critical(self, _("Błąd"), f"{_('Wystąpił nieoczekiwany wyjątek:')}\n{e}")
