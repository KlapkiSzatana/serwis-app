import os
from typing import Callable

from PySide6 import QtCore, QtWidgets

# Zabezpieczenie na wypadek uruchamiania modułu niezależnie
try:
    _("Test")
except NameError:
    def _(text):
        """Zwraca tekst bez tłumaczenia, gdy mechanizm i18n nie jest aktywny."""
        return text


COL_ACTION = 0
COL_SERVICE = 1
COL_NETTO = 2
COL_BRUTTO = 3


def get_cennik_path():
    """Zwraca ścieżkę do pliku cennika."""
    dir_path = os.path.expanduser("~/.SerwisApp")
    os.makedirs(dir_path, exist_ok=True)
    return os.path.join(dir_path, "cennik.txt")


def _parse_kwota(text, default=0.0):
    """Konwertuje tekst pola kwoty na float."""
    try:
        normalized = str(text or "").strip().replace("PLN", "").replace(",", ".")
        return float(normalized) if normalized else default
    except (TypeError, ValueError):
        return default


def polacz_uslugi_z_naprawa(aktualna_naprawa, aktualny_koszt_uslugi, uslugi):
    """Dopisuje usługi do opisu naprawy i sumuje koszt brutto."""
    linie = [line.strip() for line in str(aktualna_naprawa or "").splitlines() if line.strip()]
    for usluga in uslugi:
        nazwa = str(usluga.get("nazwa", "")).strip()
        if nazwa:
            linie.append(nazwa)

    nowy_koszt = round(
        _parse_kwota(aktualny_koszt_uslugi, 0.0) +
        sum(_parse_kwota(usluga.get("brutto"), 0.0) for usluga in uslugi),
        2
    )
    return "\n".join(linie), nowy_koszt


class CennikDialog(QtWidgets.QDialog):
    """Jeden wspólny dialog cennika z edycją i wyborem usług."""

    def __init__(self, parent=None, order_label="", service_apply_callback: Callable | None = None):
        super().__init__(parent)
        self.order_label = order_label
        self.service_apply_callback = service_apply_callback
        self._is_updating = False
        self._selected_keys = set()
        self._next_row_key = 1

        self.setWindowTitle(_("Cennik"))
        self.resize(860, 620)

        layout = QtWidgets.QVBoxLayout(self)

        title = QtWidgets.QLabel(_("Cennik Usług"))
        title_font = title.font()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        self.target_info = QtWidgets.QLabel()
        self.target_info.setWordWrap(True)
        self.target_info.setVisible(bool(self.order_label))
        self.target_info.setStyleSheet("color: light-dark(#111, #fff); font-size: 11px;")
        if self.order_label:
            self.target_info.setText(_("Wybrane usługi możesz dodać do zlecenia: {nr}").format(nr=self.order_label))
        layout.addWidget(self.target_info)

        top_layout = QtWidgets.QHBoxLayout()

        top_layout.addWidget(QtWidgets.QLabel(_("Stawka VAT (%):")))
        self.spin_vat = QtWidgets.QSpinBox()
        self.spin_vat.setRange(0, 100)
        self.spin_vat.setValue(23)
        self.spin_vat.setFixedWidth(70)
        self.spin_vat.valueChanged.connect(self.przelicz_cala_tabele)
        top_layout.addWidget(self.spin_vat)

        top_layout.addStretch()

        self.btn_add = QtWidgets.QPushButton(_("Dodaj pozycję"))
        self.btn_remove = QtWidgets.QPushButton(_("Usuń zaznaczone"))
        top_layout.addWidget(self.btn_add)
        top_layout.addWidget(self.btn_remove)
        layout.addLayout(top_layout)

        self.table = QtWidgets.QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["+", _("Usługa"), _("Cena Netto"), _("Cena Brutto")])
        self.table.horizontalHeader().setSectionResizeMode(COL_ACTION, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(COL_SERVICE, QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(COL_NETTO, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(COL_BRUTTO, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        layout.addWidget(self.table)

        summary_layout = QtWidgets.QHBoxLayout()
        self.selection_summary = QtWidgets.QLabel(_("Nie wybrano pozycji do dodania"))
        self.selection_summary.setStyleSheet("font-weight: bold; color: #2e7d32;")
        summary_layout.addWidget(self.selection_summary)
        summary_layout.addStretch()
        layout.addLayout(summary_layout)

        buttons_layout = QtWidgets.QHBoxLayout()
        buttons_layout.addStretch()
        self.btn_save = QtWidgets.QPushButton(_("Zapisz"))
        self.btn_close = QtWidgets.QPushButton(_("Zamknij"))
        buttons_layout.addWidget(self.btn_save)
        buttons_layout.addWidget(self.btn_close)
        layout.addLayout(buttons_layout)

        self.btn_add.clicked.connect(self.dodaj_wiersz)
        self.btn_remove.clicked.connect(self.usun_wiersz)
        self.btn_save.clicked.connect(self.zapisz_dane)
        self.btn_close.clicked.connect(self.reject)
        self.table.itemChanged.connect(self.on_item_changed)
        self.table.itemDelegate().closeEditor.connect(self.po_zakonczeniu_edycji)

        self.zaladuj_dane()

    def _create_toggle_button(self, row_key):
        """Buduje przycisk + dla wskazanego wiersza."""
        button = QtWidgets.QToolButton(self.table)
        button.setText("+")
        button.setCheckable(True)
        button.setFixedSize(28, 28)
        button.setProperty("row_key", row_key)
        button.setToolTip(_("Dodaj lub usuń usługę z wyboru"))
        button.toggled.connect(lambda checked, key=row_key: self.toggle_service_selection(key, checked))
        button.setStyleSheet(
            "QToolButton { font-weight: bold; font-size: 16px; padding-bottom: 2px; }"
            "QToolButton:checked { background-color: #2e7d32; color: white; border-radius: 4px; }"
        )
        return button

    def _next_key(self):
        """Zwraca kolejny unikalny klucz wiersza."""
        row_key = self._next_row_key
        self._next_row_key += 1
        return row_key

    def _get_row_key(self, row):
        """Odczytuje klucz przypisany do wiersza tabeli."""
        item = self.table.item(row, COL_SERVICE)
        if not item:
            return None
        return item.data(QtCore.Qt.ItemDataRole.UserRole)

    def _set_row_items(self, row, nazwa="", netto=0.0, brutto=0.0, row_key=None):
        """Tworzy lub aktualizuje komplet komórek dla wiersza cennika."""
        if row_key is None:
            row_key = self._next_key()

        button = self._create_toggle_button(row_key)
        self.table.setCellWidget(row, COL_ACTION, button)

        service_item = QtWidgets.QTableWidgetItem(str(nazwa))
        service_item.setData(QtCore.Qt.ItemDataRole.UserRole, row_key)
        self.table.setItem(row, COL_SERVICE, service_item)

        netto_item = QtWidgets.QTableWidgetItem(f"{_parse_kwota(netto):.2f}")
        netto_item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.table.setItem(row, COL_NETTO, netto_item)

        brutto_item = QtWidgets.QTableWidgetItem(f"{_parse_kwota(brutto):.2f}")
        brutto_item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)
        brutto_font = brutto_item.font()
        brutto_font.setBold(True)
        brutto_item.setFont(brutto_font)
        self.table.setItem(row, COL_BRUTTO, brutto_item)

    def toggle_service_selection(self, row_key, checked):
        """Zaznacza lub odznacza usługę do późniejszego dodania."""
        if checked:
            self._selected_keys.add(row_key)
        else:
            self._selected_keys.discard(row_key)
        self.odswiez_podsumowanie()

    def odswiez_podsumowanie(self):
        """Aktualizuje licznik wybranych usług i ich sumę brutto."""
        wybrane = self.pobierz_wybrane_uslugi()
        if not wybrane:
            self.selection_summary.setText(_("Nie wybrano pozycji do dodania"))
            return

        suma = sum(_parse_kwota(usluga["brutto"]) for usluga in wybrane)
        self.selection_summary.setText(
            _("Wybrano {count} pozycji | suma brutto: {amount:.2f} PLN").format(
                count=len(wybrane), amount=suma
            )
        )

    def pobierz_wybrane_uslugi(self):
        """Zwraca listę usług zaznaczonych przez przyciski +."""
        wynik = []
        for row in range(self.table.rowCount()):
            row_key = self._get_row_key(row)
            if row_key not in self._selected_keys:
                continue

            nazwa_item = self.table.item(row, COL_SERVICE)
            netto_item = self.table.item(row, COL_NETTO)
            brutto_item = self.table.item(row, COL_BRUTTO)
            nazwa = nazwa_item.text().strip() if nazwa_item else ""

            if not nazwa:
                continue

            wynik.append({
                "nazwa": nazwa,
                "netto": _parse_kwota(netto_item.text() if netto_item else 0.0),
                "brutto": _parse_kwota(brutto_item.text() if brutto_item else 0.0),
            })
        return wynik

    def po_zakonczeniu_edycji(self, editor, hint):
        """Dodaje nowy wiersz po wejściu w ostatnią pozycję klawiaturą."""
        if hint == QtWidgets.QAbstractItemDelegate.EndEditHint.SubmitModelCache and self.table.currentRow() == self.table.rowCount() - 1:
            QtCore.QTimer.singleShot(0, self.dodaj_wiersz)

    def dodaj_wiersz(self):
        """Dodaje nową pozycję cennika."""
        self._is_updating = True
        row = self.table.rowCount()
        self.table.insertRow(row)
        self._set_row_items(row)
        self._is_updating = False
        self.table.setCurrentCell(row, COL_SERVICE)
        self.table.editItem(self.table.item(row, COL_SERVICE))

    def usun_wiersz(self):
        """Usuwa zaznaczone wiersze cennika."""
        rows = sorted({index.row() for index in self.table.selectionModel().selectedRows()}, reverse=True)
        if not rows:
            return

        self._is_updating = True
        for row in rows:
            row_key = self._get_row_key(row)
            self._selected_keys.discard(row_key)
            self.table.removeRow(row)
        self._is_updating = False
        self.odswiez_podsumowanie()

    def on_item_changed(self, item):
        """Przelicza netto/brutto po zmianie kwoty w wierszu."""
        if self._is_updating or item.column() not in (COL_NETTO, COL_BRUTTO):
            return

        row = item.row()
        vat = self.spin_vat.value() / 100.0
        wartosc = _parse_kwota(item.text())

        self._is_updating = True
        try:
            if item.column() == COL_NETTO:
                brutto = wartosc * (1 + vat)
                brutto_item = self.table.item(row, COL_BRUTTO)
                if not brutto_item:
                    brutto_item = QtWidgets.QTableWidgetItem()
                    self.table.setItem(row, COL_BRUTTO, brutto_item)
                brutto_item.setText(f"{brutto:.2f}")
                item.setText(f"{wartosc:.2f}")
            else:
                netto = wartosc / (1 + vat) if vat != -1 else wartosc
                netto_item = self.table.item(row, COL_NETTO)
                if not netto_item:
                    netto_item = QtWidgets.QTableWidgetItem()
                    self.table.setItem(row, COL_NETTO, netto_item)
                netto_item.setText(f"{netto:.2f}")
                item.setText(f"{wartosc:.2f}")
        finally:
            self._is_updating = False
            self.odswiez_podsumowanie()

    def przelicz_cala_tabele(self):
        """Przelicza kolumnę brutto dla całej tabeli według aktualnej stawki VAT."""
        self._is_updating = True
        vat = self.spin_vat.value() / 100.0
        for row in range(self.table.rowCount()):
            netto_item = self.table.item(row, COL_NETTO)
            brutto_item = self.table.item(row, COL_BRUTTO)
            if not netto_item or not brutto_item:
                continue
            netto = _parse_kwota(netto_item.text())
            brutto_item.setText(f"{netto * (1 + vat):.2f}")
        self._is_updating = False
        self.odswiez_podsumowanie()

    def zaladuj_dane(self):
        """Wczytuje pozycje cennika z pliku."""
        path = get_cennik_path()
        if not os.path.exists(path):
            return

        self._is_updating = True
        with open(path, "r", encoding="utf-8") as handle:
            lines = handle.readlines()

        self.table.setRowCount(0)
        for line in lines:
            parts = line.strip().split(";")
            while len(parts) < 3:
                parts.append("0.00")
            row = self.table.rowCount()
            self.table.insertRow(row)
            self._set_row_items(
                row,
                nazwa=parts[0],
                netto=_parse_kwota(parts[1]),
                brutto=_parse_kwota(parts[2]),
            )
        self._is_updating = False
        self.odswiez_podsumowanie()

    def _collect_rows_to_save(self):
        """Waliduje wiersze i zwraca dane gotowe do zapisu do pliku."""
        rows_to_save = []
        for row in range(self.table.rowCount()):
            nazwa_item = self.table.item(row, COL_SERVICE)
            netto_item = self.table.item(row, COL_NETTO)
            brutto_item = self.table.item(row, COL_BRUTTO)

            nazwa = nazwa_item.text().strip() if nazwa_item else ""
            netto = _parse_kwota(netto_item.text() if netto_item else 0.0)
            brutto = _parse_kwota(brutto_item.text() if brutto_item else 0.0)

            if not nazwa and netto == 0.0 and brutto == 0.0:
                continue

            if not nazwa:
                raise ValueError(_("Każda pozycja z ceną musi mieć nazwę usługi."))

            rows_to_save.append((nazwa.replace(";", ","), netto, brutto))
        return rows_to_save

    def _zapisz_plik_cennika(self, rows_to_save):
        """Zapisuje aktualny cennik na dysku."""
        path = get_cennik_path()
        with open(path, "w", encoding="utf-8") as handle:
            for nazwa, netto, brutto in rows_to_save:
                handle.write(f"{nazwa};{netto:.2f};{brutto:.2f}\n")

    def zapisz_dane(self):
        """Zapisuje cennik i opcjonalnie dodaje wybrane usługi do zlecenia."""
        try:
            rows_to_save = self._collect_rows_to_save()
            self._zapisz_plik_cennika(rows_to_save)

            wybrane = self.pobierz_wybrane_uslugi()
            if wybrane and self.service_apply_callback:
                reply = QtWidgets.QMessageBox.question(
                    self,
                    _("Potwierdzenie"),
                    _("Czy na pewno chcesz dodać wybrane pozycje usług do zlecenia {nr}?").format(
                        nr=self.order_label or "---"
                    ),
                    QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.Cancel
                )
                if reply == QtWidgets.QMessageBox.StandardButton.Yes:
                    wynik = self.service_apply_callback(wybrane)
                    if wynik is False:
                        return

            QtWidgets.QMessageBox.information(self, _("Sukces"), _("Cennik został zapisany pomyślnie."))
            self.accept()
        except Exception as error:
            QtWidgets.QMessageBox.critical(
                self,
                _("Błąd"),
                f"{_('Nie udało się zapisać cennika:')}\n{error}"
            )
