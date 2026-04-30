from PySide6 import QtWidgets, QtCore, QtGui
import webbrowser

# Zabezpieczenie dla funkcji tłumaczeń _() na wypadek uruchomienia modułu niezależnie
try:
    _("Test")
except NameError:
    def _(text):
        """Zwraca tekst bez tłumaczenia, gdy mechanizm i18n nie jest aktywny."""
        return text

def pokaz_wsparcie(window):
    """
    Wyświetla okno wsparcia, które automatycznie dopasowuje kolory
    do motywu systemowego (Jasny/Ciemny).
    """
    dialog = QtWidgets.QDialog(window)
    dialog.setWindowTitle(_("Wsparcie - SerwisApp"))
    dialog.resize(480, 400)

    # Usuwamy pytajnik z paska tytułu
    dialog.setWindowFlags(dialog.windowFlags() & ~QtCore.Qt.WindowContextHelpButtonHint)

    layout = QtWidgets.QVBoxLayout(dialog)
    layout.setSpacing(15)
    layout.setContentsMargins(25, 25, 25, 25)

    # --- TREŚĆ HTML (BEZ SZTYWNYCH KOLORÓW) ---
    # Używamy standardowych tagów HTML. Qt samo podstawi odpowiednie kolory
    # (czarny dla jasnego motywu, biały dla ciemnego).
    html_content = _(
        """
        <h2 align="center">Wesprzyj Projekt SerwisApp</h2>

        <p align="center">
            Dziękuję, że korzystasz z aplikacji! Twój wkład pozwala na jej dalszy rozwój i utrzymanie.
        </p>

        <hr>

        <p align="center">
            <b>Tradycyjny przelew:</b><br>
            <span style="font-size: 14pt; font-family: Courier New, monospace;">
                <b>26 2910 0006 0000 0000 0231 2197</b>
            </span>
        </p>

        <br>

        <p align="center" style="font-size: small;">
            Masz pytania lub pomysł na funkcję?<br><br>
            <a href="https://github.com/KlapkiSzatana/serwis-app/issues"
            style="
                display: inline-block;
                padding: 10px 18px;
                background-color: #24292e;
                color: #fff;
                text-decoration: none;
                border-radius: 8px;
                font-weight: 600;
                transition: 0.2s;
            "
            onmouseover="this.style.backgroundColor='#444'"
            onmouseout="this.style.backgroundColor='#24292e'">
            🚀 Zgłoś issue na GitHub
            </a>
        </p>
        """
    )

    # --- KONFIGURACJA LABELA ---
    label = QtWidgets.QLabel(html_content)
    label.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop | QtCore.Qt.AlignmentFlag.AlignHCenter)
    label.setWordWrap(True)

    # Obsługa linków
    label.setOpenExternalLinks(False)
    label.linkActivated.connect(lambda url: webbrowser.open(url))

    layout.addWidget(label)

    # --- PRZYCISK ZAMKNIĘCIA ---
    # Dodajemy elastyczny odstęp, żeby przycisk był na dole
    layout.addStretch()

    btn_zamknij = QtWidgets.QPushButton(_("Zamknij"))
    btn_zamknij.setMinimumHeight(35)
    btn_zamknij.clicked.connect(dialog.accept)
    btn_zamknij.setShortcut(QtGui.QKeySequence("Esc")) # ESC zamyka

    # Wyśrodkowanie przycisku
    btn_layout = QtWidgets.QHBoxLayout()
    btn_layout.addStretch()
    btn_layout.addWidget(btn_zamknij)
    btn_layout.addStretch()

    layout.addLayout(btn_layout)

    dialog.exec()
