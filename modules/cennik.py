# modules/cennik.py
import os
from PySide6 import QtWidgets, QtCore, QtGui

# Zabezpieczenie na wypadek uruchamiania modułu niezależnie
try:
    _("Test")
except NameError:
    def _(text):
        """Zwraca tekst bez tłumaczenia, gdy mechanizm i18n nie jest aktywny."""
        return text

def get_cennik_path():
    """Zwraca wymagane dane lub ustawienia."""
    dir_path = os.path.expanduser("~/.SerwisApp")
    os.makedirs(dir_path, exist_ok=True)
    return os.path.join(dir_path, "cennik.txt")

class CennikDialog(QtWidgets.QDialog):
    """Dialog obsługujący wydzielony fragment funkcjonalności aplikacji."""
    def __init__(self, parent=None):
        """Inicjalizuje obiekt i przygotowuje jego stan początkowy."""
        super().__init__(parent)
        self.setWindowTitle(_("Cennik Usług"))
        self.resize(700, 600)

        layout = QtWidgets.QVBoxLayout(self)

        tytul = QtWidgets.QLabel(_("Aktualny Cennik Usług"))
        tytul_font = tytul.font()
        tytul_font.setPointSize(16)
        tytul_font.setBold(True)
        tytul.setFont(tytul_font)
        tytul.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(tytul)
        layout.addSpacing(10)

        self.table = QtWidgets.QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels([_("Usługa"), _("Cena Netto"), _("Cena Brutto")])
        self.table.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.Stretch)

        # --- ODBLOKOWANIE ZAZNACZANIA DLA KOPIOWANIA ---
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers) # Nadal nie można edytować tekstu
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection) # Pozwala zaznaczać wiele komórek
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectItems) # Zaznacza konkretne komórki, a nie całe wiersze
        self.table.setFocusPolicy(QtCore.Qt.StrongFocus) # Musi mieć focus, by przyjąć skróty z klawiatury

        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.verticalHeader().setVisible(False)

        font = self.table.font()
        font.setPointSize(11)
        self.table.setFont(font)
        self.table.horizontalHeader().setFont(font)

        layout.addWidget(self.table)

        btn_close = QtWidgets.QPushButton(_("Zamknij"))
        btn_close.setMinimumHeight(40)
        btn_close.setFixedWidth(200)
        btn_close.clicked.connect(self.close)

        layout.addWidget(btn_close, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)

        # --- MENU KONTEKSTOWE (PRAWY PRZYCISK MYSZY) ---
        self.table.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.pokaz_menu_kontekstowe)

        # --- SKRÓT KLAWISZOWY (CTRL+C) ---
        skrot_kopiuj = QtGui.QShortcut(QtGui.QKeySequence.StandardKey.Copy, self.table)
        skrot_kopiuj.activated.connect(self.kopiuj_do_schowka)

        self.zaladuj_dane()

    def pokaz_menu_kontekstowe(self, pos):
        # Pokazuje menu tylko wtedy, gdy cokolwiek jest zaznaczone
        """Wyświetla wskazane dane lub okno."""
        if not self.table.selectedItems():
            return

        menu = QtWidgets.QMenu(self)
        akcja_kopiuj = menu.addAction(_("Kopiuj"))

        # Wyświetlenie menu w miejscu kliknięcia
        wybrana_akcja = menu.exec(self.table.viewport().mapToGlobal(pos))

        if wybrana_akcja == akcja_kopiuj:
            self.kopiuj_do_schowka()

    def kopiuj_do_schowka(self):
        """Realizuje logikę operacji kopiuj do schowka w klasie CennikDialog."""
        zaznaczone = self.table.selectedItems()
        if not zaznaczone:
            return

        # Sortujemy komórki, żeby kopiowały się w odpowiedniej kolejności z góry na dół, od lewej do prawej
        zaznaczone.sort(key=lambda item: (item.row(), item.column()))

        tekst_do_schowka = ""
        obecny_wiersz = zaznaczone[0].row()

        for item in zaznaczone:
            if item.row() != obecny_wiersz:
                tekst_do_schowka += "\n" # Przejście do nowej linii dla kolejnego wiersza
                obecny_wiersz = item.row()
            elif tekst_do_schowka:
                tekst_do_schowka += "\t" # Tabulacja między kolumnami w tym samym wierszu

            tekst_do_schowka += item.text()

        # Wrzucenie tekstu do schowka systemowego
        QtWidgets.QApplication.clipboard().setText(tekst_do_schowka)

    def zaladuj_dane(self):
        """Ładuje dane do widoku lub pamięci."""
        path = get_cennik_path()
        if not os.path.exists(path):
            return

        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        self.table.setRowCount(len(lines))
        for row_idx, line in enumerate(lines):
            parts = line.strip().split(";")
            while len(parts) < 3: parts.append("0.00")

            item_usluga = QtWidgets.QTableWidgetItem(parts[0])
            self.table.setItem(row_idx, 0, item_usluga)

            try: netto_val = float(parts[1])
            except ValueError: netto_val = 0.0
            item_netto = QtWidgets.QTableWidgetItem(f"{netto_val:.2f} PLN")
            item_netto.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row_idx, 1, item_netto)

            try: brutto_val = float(parts[2])
            except ValueError: brutto_val = 0.0
            item_brutto = QtWidgets.QTableWidgetItem(f"{brutto_val:.2f} PLN")
            item_brutto.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)

            brutto_font = item_brutto.font()
            brutto_font.setBold(True)
            item_brutto.setFont(brutto_font)

            self.table.setItem(row_idx, 2, item_brutto)

class EdytujCennikDialog(QtWidgets.QDialog):
    """Dialog obsługujący wydzielony fragment funkcjonalności aplikacji."""
    def __init__(self, parent=None):
        """Inicjalizuje obiekt i przygotowuje jego stan początkowy."""
        super().__init__(parent)
        self.setWindowTitle(_("Edytuj Cennik"))
        self.resize(650, 600)
        self._is_updating = False # Flaga zabezpieczająca przed nieskończoną pętlą przeliczania

        layout = QtWidgets.QVBoxLayout(self)

        # Panel górny (VAT i przyciski wierszy)
        top_layout = QtWidgets.QHBoxLayout()

        vat_layout = QtWidgets.QHBoxLayout()
        vat_layout.addWidget(QtWidgets.QLabel(_("Stawka VAT (%):")))
        self.spin_vat = QtWidgets.QSpinBox()
        self.spin_vat.setRange(0, 100)
        self.spin_vat.setValue(23)
        self.spin_vat.setFixedWidth(60)
        # Przelicz całą tabelę przy zmianie VAT (opcjonalnie)
        self.spin_vat.valueChanged.connect(self.przelicz_cala_tabele)
        vat_layout.addWidget(self.spin_vat)
        vat_layout.addStretch()

        btn_add = QtWidgets.QPushButton(_("Dodaj pozycję"))
        btn_del = QtWidgets.QPushButton(_("Usuń zaznaczone"))

        top_layout.addLayout(vat_layout)
        top_layout.addWidget(btn_add)
        top_layout.addWidget(btn_del)
        layout.addLayout(top_layout)

        self.table = QtWidgets.QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels([_("Usługa"), _("Cena Netto"), _("Cena Brutto")])
        self.table.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)

        # Przyciski zapisu i wyjścia
        btn_bottom = QtWidgets.QHBoxLayout()
        btn_save = QtWidgets.QPushButton(_("Zapisz cennik"))
        btn_close = QtWidgets.QPushButton(_("Anuluj"))
        btn_bottom.addWidget(btn_save)
        btn_bottom.addWidget(btn_close)
        layout.addLayout(btn_bottom)

        btn_add.clicked.connect(self.dodaj_wiersz)
        btn_del.clicked.connect(self.usun_wiersz)
        btn_save.clicked.connect(self.zapisz_dane)
        btn_close.clicked.connect(self.close)

        # Podłączenie sygnału zmiany komórki do przeliczania VAT
        self.table.itemChanged.connect(self.on_item_changed)

        # --- NOWOŚĆ: Przechwytywanie klawisza Enter podczas edycji ---
        self.table.itemDelegate().closeEditor.connect(self.po_zakonczeniu_edycji)

        self.zaladuj_dane()

    def po_zakonczeniu_edycji(self, editor, hint):
        # hint wskazuje na to, jak zakończono edycję. SubmitModelCache oznacza wciśnięcie Enter.
        """Porządkuje dane po zakończeniu edycji komórki."""
        if hint == QtWidgets.QAbstractItemDelegate.EndEditHint.SubmitModelCache:
            # Jeśli wcisnęliśmy Enter będąc na absolutnie ostatnim wierszu:
            if self.table.currentRow() == self.table.rowCount() - 1:
                # Używamy QTimer z opóźnieniem 0ms. To sztuczka Qt, która pozwala systemowi
                # dokończyć niszczenie edytora komórki zanim odpalimy funkcję tworzącą nowy wiersz.
                QtCore.QTimer.singleShot(0, self.dodaj_wiersz)

    def dodaj_wiersz(self):
        """Realizuje logikę operacji dodaj wiersz w klasie EdytujCennikDialog."""
        self._is_updating = True
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QtWidgets.QTableWidgetItem(""))
        self.table.setItem(row, 1, QtWidgets.QTableWidgetItem("0.00"))
        self.table.setItem(row, 2, QtWidgets.QTableWidgetItem("0.00"))
        self._is_updating = False

        # --- NOWOŚĆ: Po dodaniu wiersza, automatycznie przeskocz do niego i rozpocznij edycję ---
        self.table.setCurrentCell(row, 0)
        self.table.editItem(self.table.item(row, 0))

    def usun_wiersz(self):
        """Realizuje logikę operacji usun wiersz w klasie EdytujCennikDialog."""
        self._is_updating = True
        for item in self.table.selectedItems():
            self.table.removeRow(item.row())
        self._is_updating = False

    def on_item_changed(self, item):
        """Reaguje na zmianę danych w edytowanej tabeli."""
        if self._is_updating:
            return

        col = item.column()
        if col not in [1, 2]:
            return

        row = item.row()
        vat = self.spin_vat.value() / 100.0

        tekst = item.text().replace(',', '.')

        try:
            wartosc = float(tekst)
        except ValueError:
            return

        self._is_updating = True
        try:
            if col == 1: # Zmieniono Netto
                brutto = wartosc * (1 + vat)
                item_brutto = self.table.item(row, 2)
                if not item_brutto:
                    item_brutto = QtWidgets.QTableWidgetItem()
                    self.table.setItem(row, 2, item_brutto)
                item_brutto.setText(f"{brutto:.2f}")
                item.setText(f"{wartosc:.2f}")

            elif col == 2: # Zmieniono Brutto
                netto = wartosc / (1 + vat)
                item_netto = self.table.item(row, 1)
                if not item_netto:
                    item_netto = QtWidgets.QTableWidgetItem()
                    self.table.setItem(row, 1, item_netto)
                item_netto.setText(f"{netto:.2f}")
                item.setText(f"{wartosc:.2f}")
        finally:
            self._is_updating = False

    def przelicz_cala_tabele(self):
        """Przelicza wartości na podstawie bieżących danych."""
        self._is_updating = True
        vat = self.spin_vat.value() / 100.0
        for row in range(self.table.rowCount()):
            item_netto = self.table.item(row, 1)
            item_brutto = self.table.item(row, 2)
            if item_netto and item_brutto:
                try:
                    netto = float(item_netto.text().replace(',', '.'))
                    brutto = netto * (1 + vat)
                    item_brutto.setText(f"{brutto:.2f}")
                except ValueError:
                    pass
        self._is_updating = False

    def zaladuj_dane(self):
        """Ładuje dane do widoku lub pamięci."""
        path = get_cennik_path()
        if not os.path.exists(path):
            return

        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        self._is_updating = True
        self.table.setRowCount(len(lines))
        for row_idx, line in enumerate(lines):
            parts = line.strip().split(";")
            while len(parts) < 3: parts.append("0.00")
            self.table.setItem(row_idx, 0, QtWidgets.QTableWidgetItem(parts[0]))
            self.table.setItem(row_idx, 1, QtWidgets.QTableWidgetItem(parts[1]))
            self.table.setItem(row_idx, 2, QtWidgets.QTableWidgetItem(parts[2]))
        self._is_updating = False

    def zapisz_dane(self):
        """Zapisuje dane lub ustawienia."""
        path = get_cennik_path()
        try:
            with open(path, "w", encoding="utf-8") as f:
                for row in range(self.table.rowCount()):
                    usluga = self.table.item(row, 0).text() if self.table.item(row, 0) else ""
                    netto = self.table.item(row, 1).text().replace(',', '.') if self.table.item(row, 1) else "0.00"
                    brutto = self.table.item(row, 2).text().replace(',', '.') if self.table.item(row, 2) else "0.00"

                    usluga = usluga.replace(";", ",")

                    f.write(f"{usluga};{netto};{brutto}\n")

            QtWidgets.QMessageBox.information(self, _("Sukces"), _("Cennik został zapisany pomyślnie!"))
            self.accept()
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, _("Błąd"), f"{_('Nie udało się zapisać pliku:')}\n{str(e)}")
