import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from PySide6.QtWidgets import QWidget, QLabel, QLineEdit, QTextEdit, QPushButton, QVBoxLayout, QMessageBox
from PySide6 import QtCore
from modules import smtp_store
from setup import config

# Zabezpieczenie na wypadek uruchamiania modułu niezależnie (bez main.py)
try:
    _("Test")
except NameError:
    def _(text):
        """Realizuje pomocniczą część logiki aplikacji."""
        return text

class MailClient(QWidget):
    """Klasa odpowiedzialna za komunikację z usługą lub odbiorcą."""
    def __init__(self, email_klienta, nr_zlecenia, sprzet, dane_firmy=None):
        """Inicjalizuje obiekt i przygotowuje jego stan początkowy."""
        super().__init__()
        self.email_klienta = email_klienta
        self.nr_zlecenia = nr_zlecenia
        self.sprzet = sprzet
        self.dane_firmy = dane_firmy if dane_firmy else _("Pozdrawiamy,\nSerwisApp")

        self.smtp_server, self.smtp_port, self.smtp_email, self.smtp_password = smtp_store.load_smtp()
        if not all([self.smtp_server, self.smtp_port, self.smtp_email, self.smtp_password]):
            QMessageBox.critical(self, _("Błąd"), _("Nie znaleziono konfiguracji SMTP w bazie!"))
            self.close()
            return

        self.init_ui()

    def init_ui(self):
        """Buduje i konfiguruje interfejs użytkownika."""
        self.setWindowTitle(_("Wyślij maila do klienta"))

        self.label_temat = QLabel(_("Temat:"))

        temat_domyslny = _("Naprawa zakończona – Zlecenie {}").format(self.nr_zlecenia)
        self.input_temat = QLineEdit(temat_domyslny)

        self.label_tresc = QLabel(_("Treść:"))
        self.input_tresc = QTextEdit()
        self.input_tresc.setAcceptRichText(True)

        tresc_html = _(
            """
            <p>Twoja naprawa (Zlecenie {nr_zlecenia}) dla sprzętu: {sprzet} została zakończona.<br>
            Zapraszamy do odbioru.</p>
            <pre>{dane_firmy}</pre>
            """
        ).format(
            nr_zlecenia=self.nr_zlecenia,
            sprzet=self.sprzet,
            dane_firmy=self.dane_firmy
        )

        self.input_tresc.setHtml(tresc_html)

        self.btn_wyslij = QPushButton(_("Wyślij"))
        self.btn_wyslij.clicked.connect(self.send_email_smtp)

        info_label = QLabel(_("⚠️ Treść i temat można edytować – domyślne: Zakończenie Naprawy"))
        font = info_label.font()
        font.setPointSize(10)
        font.setBold(True)
        info_label.setFont(font)
        info_label.setStyleSheet("color: gray;")
        info_label.setWordWrap(True)
        info_label.setAlignment(QtCore.Qt.AlignCenter)

        layout = QVBoxLayout()
        layout.addWidget(QLabel(f"Do: {self.email_klienta}"))
        layout.addWidget(self.label_temat)
        layout.addWidget(self.input_temat)
        layout.addWidget(self.label_tresc)
        layout.addWidget(self.input_tresc)
        layout.addWidget(info_label)
        layout.addWidget(self.btn_wyslij)

        self.setLayout(layout)
        self.resize(500, 400)

    def send_email_smtp(self):
        """Wysyła dane do zewnętrznej usługi lub odbiorcy."""
        temat = self.input_temat.text()
        tresc_html = self.input_tresc.toHtml()

        msg = MIMEMultipart('related')
        msg['From'] = self.smtp_email
        msg['To'] = self.email_klienta
        msg['Subject'] = temat

        html_body = f"""
        <html>
        <body>
            {tresc_html}<br>
            <img src="cid:logo_cid" width="120" alt="Logo firmy">
        </body>
        </html>
        """
        msg_html = MIMEText(html_body, 'html')
        msg.attach(msg_html)

        logo_path = os.path.join(config.LOGO_DIR, "serwisapp.png")
        if os.path.exists(logo_path):
            with open(logo_path, 'rb') as f:
                img = MIMEImage(f.read())
                img.add_header('Content-ID', '<logo_cid>')
                img.add_header('Content-Disposition', 'inline', filename="logo.png")
                msg.attach(img)

        try:
            if self.smtp_port == 465:
                server = smtplib.SMTP_SSL(self.smtp_server, self.smtp_port)
            else:
                server = smtplib.SMTP(self.smtp_server, self.smtp_port)
                server.starttls()

            server.login(self.smtp_email, self.smtp_password)
            server.send_message(msg)
            server.quit()

            QMessageBox.information(
                self,
                _("Sukces"),
                _("Wysłano maila do {}").format(self.email_klienta)
            )
            self.close()

        except smtplib.SMTPAuthenticationError as e:
            QMessageBox.critical(self, _("Błąd"), _("Błąd logowania do serwera SMTP:\n{}").format(e))
        except Exception as e:
            QMessageBox.critical(self, _("Błąd"), _("Nie udało się połączyć z serwerem SMTP:\n{}").format(e))
