import os
import configparser
import webbrowser
from PySide6 import QtWidgets, QtCore
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QCheckBox,
                               QPushButton, QApplication, QScrollArea, QWidget)
from PySide6.QtCore import Qt
from setup import config

try:
    _("Test")
except NameError:
    def _(text):
        """Zwraca tekst bez tłumaczenia, gdy mechanizm i18n nie jest aktywny."""
        return text

# Ścieżka do pliku konfiguracyjnego popupu
POPUP_CONFIG_FILE = os.path.join(os.path.expanduser("~"), ".SerwisApp", f"welcome_{config.APP_VERSION}.ini")

# Linki
SUPPORT_LINK = ""

class StartupPopup(QDialog):
    """Wyskakujące okno pomocnicze używane przez aplikację."""
    def __init__(self, parent=None):
        """Inicjalizuje obiekt i przygotowuje jego stan początkowy."""
        super().__init__(parent)
        self.setWindowTitle(f"Witamy w {config.APP_NAME2}!")
        self.resize(650, 720)

        # Usuwamy "pytajnik" z paska tytułu
        self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.WindowContextHelpButtonHint)

        # Główny layout okna
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # --- OBSZAR PRZEWIJANIA (ScrollArea) ---
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)

        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)
        layout.setSpacing(15)
        layout.setContentsMargins(25, 25, 25, 25)

        # --- 1. LOGIKA TREŚCI POWITANIA ---

        # Nagłówek
        header_html = _(
            "<h2 align='center'>{app_name} {version}</h2>"
            "<p align='center' style='font-size: 11pt;'>"
            "    Dziękuję za instalację i korzystanie z aplikacji.<br>"
            "    Program powstał, aby ułatwić Twoją i moją codzienną pracę."
            "</p>"
            "<hr>"
        ).format(
            app_name=getattr(config, 'APP_NAME2', 'SerwisApp'),
            version=config.APP_VERSION
        )

        # Treść powitania (Bez sekcji o statusie wersji)
        welcome_body_html = _(
            "<h3 align='center'>☕ Wsparcie rozwoju</h3>"
            "<p align='center'>"
            "    Projekt jest rozwijany hobbystycznie. Jeśli program dobrze Ci służy i chcesz zmotywować mnie "
            "    do dalszej pracy nad nowymi funkcjami, zawsze możesz postawić mi wirtualną kawę."
            "</p>"
            "<p align='center'>"
            "Przelew: <span style='font-size: 12pt; font-family: Courier New, monospace;'>"
            "    <b>26 2910 0006 0000 0000 0231 2197</b>"
            "</span>"
            "</p>"
        ).format(link=SUPPORT_LINK)

        # Składamy HTML powitania
        full_welcome_html = header_html + welcome_body_html

        label_welcome = QLabel(full_welcome_html)
        self._setup_label(label_welcome)
        layout.addWidget(label_welcome)

        # --- 2. TREŚĆ ZMIAN (STAŁA) ---
        html_changes = _(
            "<hr>"
            "<h3 align='center'>Co nowego w wersji {version}?</h3>"
            "<p align='center'>"
            "<b>🔥 Najważniejsze zmiany:</b><br>"
            "• <b>Wizualny edytor wydruków</b> – możliwość pełnej edycji szablonu.<br>"
            "• <b>Zaawansowany filtr dat</b> – wybieranie zakresu zamiast listy.<br><br>"

            "<b>🎨 Interfejs (UI):</b><br>"
            "• Przebudowane Menu Główne i nowe okno Kontrahentów.<br>"
            "• Odświeżone okienka informacji i usunięcie zbędnych plików.<br><br>"

            "<b>⚙️ Silnik i Stabilność:</b><br>"
            "• Zweryfikowane i poprawione moduły SMSAPI oraz E-mail.<br>"
            "• Nowa logika odświeżania tabeli (większa stabilność).<br></p>"

            "<p align='center'><b>Miłego korzystania!</b></p>"
        ).format(
            version=config.APP_VERSION
        )

        label_changes = QLabel(html_changes)
        self._setup_label(label_changes)
        layout.addWidget(label_changes)

        layout.addStretch()
        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll)

        # --- 3. DOLNY PASEK ---
        bottom_widget = QWidget()
        bottom_layout = QVBoxLayout(bottom_widget)
        bottom_layout.setContentsMargins(20, 10, 20, 20)

        self.checkbox = QCheckBox(_("Nie pokazuj więcej dla tej wersji"))
        bottom_layout.addWidget(self.checkbox, alignment=Qt.AlignmentFlag.AlignCenter)

        ok_button = QPushButton(_("Startujemy!"))
        ok_button.setFixedWidth(160)
        ok_button.setMinimumHeight(40)
        ok_button.setCursor(Qt.CursorShape.PointingHandCursor)
        ok_button.setStyleSheet("font-weight: bold; font-size: 11pt;")
        ok_button.clicked.connect(self.on_ok)
        bottom_layout.addWidget(ok_button, alignment=Qt.AlignmentFlag.AlignCenter)

        main_layout.addWidget(bottom_widget)

        # --- KONFIGURACJA INI ---
        self.config_ini = configparser.ConfigParser()
        if os.path.exists(POPUP_CONFIG_FILE):
            self.config_ini.read(POPUP_CONFIG_FILE)
        else:
            self.config_ini["STARTUP"] = {"show_popup": "yes"}

    def _setup_label(self, label):
        """Pomocnicza funkcja do konfiguracji labeli."""
        label.setWordWrap(True)
        label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        label.setOpenExternalLinks(False)
        label.linkActivated.connect(lambda url: webbrowser.open(url))
        label.setTextInteractionFlags(Qt.TextInteractionFlag.LinksAccessibleByMouse | Qt.TextInteractionFlag.TextSelectableByMouse)

    def on_ok(self):
        """Zapisuje ustawienia i zamyka okno."""
        if "STARTUP" not in self.config_ini:
            self.config_ini["STARTUP"] = {}

        self.config_ini["STARTUP"]["show_popup"] = "no" if self.checkbox.isChecked() else "yes"

        try:
            os.makedirs(os.path.dirname(POPUP_CONFIG_FILE), exist_ok=True)
            with open(POPUP_CONFIG_FILE, "w", encoding="utf-8") as f:
                self.config_ini.write(f)
        except OSError as e:
            print(f"Błąd zapisu konfiguracji popupu: {e}")

        self.accept()


def show_startup_if_needed():
    """Sprawdza plik konfiguracyjny i wyświetla okno jeśli trzeba."""
    config_parser = configparser.ConfigParser()
    show = "yes"

    if os.path.exists(POPUP_CONFIG_FILE):
        try:
            config_parser.read(POPUP_CONFIG_FILE)
            show = config_parser.get("STARTUP", "show_popup", fallback="yes")
        except (configparser.Error, OSError):
            show = "yes"

    if show.lower() == "yes":
        app = QApplication.instance()
        created_app = False
        if app is None:
            app = QApplication([])
            created_app = True

        popup = StartupPopup()
        popup.exec()

        if created_app:
            app.quit()
