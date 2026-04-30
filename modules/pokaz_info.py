from setup import config
import webbrowser
from PySide6 import QtWidgets, QtCore
import datetime
try:
    _("Test")
except NameError:
    def _(text):
        """Zwraca tekst bez tłumaczenia, gdy mechanizm i18n nie jest aktywny."""
        return text

# Logika roku: "2025" lub "2025-2026" itd.
current_year = datetime.date.today().year
year_str = f"2025-{current_year}" if current_year > 2025 else "2025"

def pokaz_info_o_programie(window, version=None):
    """Wyświetla wskazane dane lub okno."""
    if version is None:
        version = f"{config.APP_VERSION} {config.APP_NAME}"

    dialog = QtWidgets.QDialog(window)
    dialog.setWindowTitle(_("O programie - SerwisApp"))
    dialog.resize(400, 350)

    layout = QtWidgets.QVBoxLayout(dialog)

    # --- TREŚĆ HTML ---
    html_content = _(
        '<strong><span style="font-size:16pt;">SerwisApp</span></strong><br>'
        '<span style="font-size:12pt;">Proste Prowadzenie Serwisu</span><br><br>'
        'Wersja {version}<br><br>©️ KlapkiSzatana {year_str}<br><br>'

        # Sekcja Czcionki
        '<b>Czcionki:</b> <a href="https://fonts.google.com/specimen/Comfortaa">Comfortaa Bold</a> – '
        '<i><a href="https://scripts.sil.org/OFL">SIL Open Font License (OFL) 1.1</a></i><br>'

        # Sekcja Ikony
        '<b>Ikony:</b> <a href="https://iconmonstr.com">Iconmonstr.com</a> – autor: Alexander Kahlkopf<br>'

        # Sekcja Framework
        '<b>Framework:</b> <a href="https://www.qt.io/">Qt (PySide6)</a> – '
        '<i><a href="https://www.gnu.org/licenses/lgpl-3.0.html">licencja LGPL v3</a></i><br><br>'

    ).format(version=version, year_str=year_str)

    # --- KONFIGURACJA LABELA ---
    label = QtWidgets.QLabel(html_content)
    label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

    # --- RĘCZNA OBSŁUGA LINKÓW ---
    label.setOpenExternalLinks(False)  # Wyłączamy automat Qt
    label.linkActivated.connect(lambda url: webbrowser.open(url)) # Używamy Pythona

    layout.addWidget(label)

    # --- PRZYCISKI ---
    btn_licencja = QtWidgets.QPushButton(_("Licencja"))
    btn_licencja.setMaximumWidth(120)

    # Podpięcie przycisku licencji
    # Funkcja pokaz_licencje jest w tym samym pliku, więc jest dostępna
    btn_licencja.clicked.connect(lambda: pokaz_licencje(dialog))

    btn_zamknij = QtWidgets.QPushButton(_("Zamknij"))
    btn_zamknij.setMaximumWidth(120)
    btn_zamknij.clicked.connect(dialog.accept)

    # Layout przycisków
    btn_layout = QtWidgets.QHBoxLayout()
    btn_layout.addStretch()
    btn_layout.addWidget(btn_licencja)
    btn_layout.addWidget(btn_zamknij)
    btn_layout.addStretch()

    layout.addLayout(btn_layout)

    dialog.exec()

def pokaz_licencje(parent_window):
    """
    GPLv3 License dialog (summary + link to full text)
    """
    dialog = QtWidgets.QDialog(parent_window)
    dialog.setWindowTitle(_("Licencja - SerwisApp (GPLv3)"))
    dialog.resize(700, 650)

    dialog.setWindowFlags(dialog.windowFlags() & ~QtCore.Qt.WindowContextHelpButtonHint)

    layout = QtWidgets.QVBoxLayout(dialog)
    layout.setContentsMargins(25, 25, 25, 25)
    layout.setSpacing(15)

    html_content = _("""
    <h3 align="center">GNU General Public License v3 (GPLv3)</h3>
    <p align="center"><i>Podsumowanie licencji użytkownika</i></p>

    <hr>

    <p><b>1. Wolność używania:</b><br>
    Program możesz używać w dowolnym celu, prywatnie i komercyjnie.</p>

    <p><b>2. Wolność modyfikacji:</b><br>
    Możesz analizować, modyfikować i rozwijać kod źródłowy programu.</p>

    <p><b>3. Wolność rozpowszechniania:</b><br>
    Możesz kopiować i udostępniać program innym, również w wersjach zmodyfikowanych.</p>

    <p><b>4. Warunek GPLv3:</b><br>
    Jeśli rozpowszechniasz program lub jego zmodyfikowaną wersję,
    musisz udostępnić również kod źródłowy na tej samej licencji GPLv3.</p>

    <p><b>5. Brak gwarancji:</b><br>
    Program dostarczany jest bez żadnej gwarancji. Autor nie odpowiada za ewentualne straty danych lub szkody.</p>

    <hr>

    <p><b>Komponenty:</b>
    <ul>
        <li>Qt (PySide6) – LGPL</li>
        <li>Projekt SerwisApp – GPLv3</li>
    </ul>
    </p>

    <p align="center">
        Pełny tekst licencji GPLv3 znajdziesz tutaj:<br>
        <a href="https://www.gnu.org/licenses/gpl-3.0.html">
        https://www.gnu.org/licenses/gpl-3.0.html
        </a>
    </p>

    <hr>

    <p align="center">
        To jest skrót licencji. W razie sprzeczności obowiązuje pełny tekst GPLv3.
    </p>
    """)

    # --- LABEL ---
    label = QtWidgets.QLabel(html_content)
    label.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop | QtCore.Qt.AlignmentFlag.AlignLeft)
    label.setWordWrap(True)

    # Obsługa linków (bezpieczna dla Linux/Windows)
    label.setOpenExternalLinks(False)
    label.linkActivated.connect(lambda url: webbrowser.open(url))

    # Umożliwia klikanie w linki (Qt i strona licencji)
    label.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.LinksAccessibleByMouse)

    layout.addWidget(label)

    # --- PRZYCISK ZAMKNIĘCIA ---
    layout.addStretch()

    btn_zamknij = QtWidgets.QPushButton(_("Zamknij"))
    btn_zamknij.setMinimumHeight(35)
    btn_zamknij.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
    btn_zamknij.clicked.connect(dialog.accept)

    # Wyśrodkowanie przycisku
    btn_layout = QtWidgets.QHBoxLayout()
    btn_layout.addStretch()
    btn_layout.addWidget(btn_zamknij)
    btn_layout.addStretch()

    layout.addLayout(btn_layout)

    dialog.exec()
