# modules/raport.py
from PySide6 import QtWidgets, QtCore
from PySide6.QtPrintSupport import QPrinter, QPrintDialog
from PySide6.QtGui import QTextDocument
import sqlite3
from datetime import datetime
from setup import config
from modules.baza import wczytaj_baze
from modules import password_protection

# Zabezpieczenie na wypadek uruchamiania modułu niezależnie (bez main.py)
try:
    _("Test")
except NameError:
    def _(text):
        """Zwraca tekst bez tłumaczenia, gdy mechanizm i18n nie jest aktywny."""
        return text

class RaportDialog(QtWidgets.QDialog):
    """Dialog obsługujący wydzielony fragment funkcjonalności aplikacji."""
    def __init__(self, parent=None, db_path=None):
        """Inicjalizuje obiekt i przygotowuje jego stan początkowy."""
        super().__init__(parent)
        # --- BLOKADA: OCHRONA DOSTĘPU DO RAPORTÓW ---
        # Sprawdzamy czy zalogowany użytkownik to Administrator (SUPER USER)
        if not password_protection.CURRENT_USER_IS_SUPER:
            QtWidgets.QMessageBox.warning(
                self,  # Rodzicem jest to okno dialogowe (nawet jeśli jeszcze niewidoczne)
                _("Brak uprawnień"),
                _("Dostęp do raportów finansowych posiada tylko Administrator.")
            )

            QtCore.QTimer.singleShot(0, self.reject)
            return
        # ----------------------------------------------
        self.db_path = db_path or wczytaj_baze(config.CONFIG_BAZA_FILE, config.DB_FILE)
        self.setWindowTitle(_("Raport Zleceń Serwisowych"))
        self.setFixedSize(400, 380)

        layout = QtWidgets.QVBoxLayout(self)

        layout.addWidget(QtWidgets.QLabel(_("Wybierz okres:")))
        self.combo_period = QtWidgets.QComboBox()
        self.combo_period.addItems([_("Miesiąc"), _("Kwartał")])
        layout.addWidget(self.combo_period)

        layout.addWidget(QtWidgets.QLabel(_("Rok:")))
        self.spin_year = QtWidgets.QSpinBox()
        self.spin_year.setRange(2000, 2100)
        self.spin_year.setValue(datetime.now().year)
        layout.addWidget(self.spin_year)

        layout.addWidget(QtWidgets.QLabel(_("Wybierz miesiąc/kwartał:")))
        self.combo_month_qtr = QtWidgets.QComboBox()
        layout.addWidget(self.combo_month_qtr)

        self.label_result = QtWidgets.QLabel("")
        self.label_result.setWordWrap(True)
        self.label_result.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
        layout.addWidget(self.label_result)

        btn_layout = QtWidgets.QHBoxLayout()
        self.btn_print = QtWidgets.QPushButton(_("Drukuj"))
        self.btn_close = QtWidgets.QPushButton(_("Zamknij"))
        btn_layout.addWidget(self.btn_print)
        btn_layout.addWidget(self.btn_close)
        layout.addLayout(btn_layout)

        self.combo_period.currentTextChanged.connect(self.update_month_qtr)
        self.combo_month_qtr.currentIndexChanged.connect(self.pokaz_raport)
        self.spin_year.valueChanged.connect(self.pokaz_raport)
        self.combo_period.currentTextChanged.connect(self.pokaz_raport)
        self.btn_close.clicked.connect(self.close)
        self.btn_print.clicked.connect(self.drukuj_raport)

        self.update_month_qtr()
        self.pokaz_raport()

    def update_month_qtr(self):
        """Aktualizuje stan danych lub interfejsu."""
        period = self.combo_period.currentText()
        self.combo_month_qtr.clear()
        if period == _("Miesiąc"):
            self.combo_month_qtr.addItems([
                _("Styczeń"), _("Luty"), _("Marzec"), _("Kwiecień"), _("Maj"), _("Czerwiec"),
                _("Lipiec"), _("Sierpień"), _("Wrzesień"), _("Październik"), _("Listopad"), _("Grudzień"), _("Cały Rok")
            ])
        else:
            self.combo_month_qtr.addItems(["I", "II", "III", "IV"])

    def pokaz_raport(self):
        """Wyświetla wskazane dane lub okno."""
        try:
            period = self.combo_period.currentText()
            year = self.spin_year.value()
            month_qtr_index = self.combo_month_qtr.currentIndex()

            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()

            c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='zlecenia'")
            if not c.fetchone():
                QtWidgets.QMessageBox.warning(self, _("Błąd"), _("Brak tabeli 'zlecenia' w bazie danych!"))
                conn.close()
                return

            query = "SELECT SUM(koszt_czesci), SUM(koszt_uslugi), COUNT(*) FROM zlecenia WHERE strftime('%Y', data_zlecenia)=?"
            params = [str(year)]

            if period == "Miesiąc":
                if month_qtr_index == 12:  # "Cały Rok"
                    okres_text = f"{_('Cały Rok')} {year}"
                else:
                    query += " AND strftime('%m', data_zlecenia)=?"
                    params.append(f"{month_qtr_index + 1:02d}")
                    okres_text = f"{self.combo_month_qtr.currentText()} {year}"
            else:
                qtr = month_qtr_index + 1
                months = [(qtr - 1) * 3 + i for i in range(1, 4)]
                placeholders = ",".join(["?"] * 3)
                query += f" AND strftime('%m', data_zlecenia) IN ({placeholders})"
                params.extend([f"{m:02d}" for m in months])
                okres_text = f"{_('Kwartał')} {self.combo_month_qtr.currentText()} {year}"

            c.execute(query, params)
            result = c.fetchone()
            conn.close()

            koszt_czesci = result[0] or 0.0
            koszt_uslugi = result[1] or 0.0
            liczba_zlecen = result[2] or 0
            suma = koszt_czesci + koszt_uslugi

            self.label_result.setText(
                f"<strong>{okres_text}:</strong><br>"
                f"{_('Liczba zleceń:')} {liczba_zlecen}<br>"
                f"{_('Wartość usług:')} {koszt_uslugi:.2f} PLN<br>"
                f"{_('Wartość części:')} {koszt_czesci:.2f} PLN<br><br>"
                f"<strong>{_('Razem:')} {suma:.2f} PLN</strong>"
            )

        except Exception as e:
            QtWidgets.QMessageBox.critical(self, _("Błąd"), f"{_('Wystąpił błąd:')}\n{str(e)}")

    def drukuj_raport(self):
        """Przygotowuje i wykonuje wydruk."""
        try:
            html = f"""
            <html>
            <head><meta charset="UTF-8"><title>{_('Raport')}</title></head>
            <body>
            <h2>{_('Raport - ')}{self.combo_month_qtr.currentText()} {self.spin_year.value()}</h2>
            <p>{self.label_result.text()}</p>
            <hr>
            <p><i>{_('Wydrukowano z SerwisApp data: ')}{datetime.now().strftime('%d-%m-%Y %H:%M:%S')}</i></p>
            </body>
            </html>
            """

            doc = QTextDocument()
            doc.setHtml(html)

            printer = QPrinter()
            dialog = QPrintDialog(printer, self)
            dialog.setWindowTitle(_("Drukuj raport"))
            if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
                doc.print_(printer)

        except Exception as e:
            QtWidgets.QMessageBox.critical(self, _("Błąd"), f"{_('Wystąpił błąd podczas drukowania:')}\n{str(e)}")

class RaportTopSprzetDialog(QtWidgets.QDialog):
    """Dialog obsługujący wydzielony fragment funkcjonalności aplikacji."""
    def __init__(self, parent=None, db_path=None):
        """Inicjalizuje obiekt i przygotowuje jego stan początkowy."""
        super().__init__(parent)
        if not password_protection.CURRENT_USER_IS_SUPER:
            QtWidgets.QMessageBox.warning(self, _("Brak uprawnień"), _("Dostęp do raportów posiada tylko Administrator."))
            QtCore.QTimer.singleShot(0, self.reject)
            return

        self.db_path = db_path or wczytaj_baze(config.CONFIG_BAZA_FILE, config.DB_FILE)
        self.setWindowTitle(_("Top 10 - Najczęściej naprawiany sprzęt"))
        self.resize(450, 400)

        layout = QtWidgets.QVBoxLayout(self)

        self.table = QtWidgets.QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels([_("Sprzęt"), _("Liczba napraw")])
        self.table.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        layout.addWidget(self.table)

        btn_close = QtWidgets.QPushButton(_("Zamknij"))
        btn_close.clicked.connect(self.close)
        layout.addWidget(btn_close)

        self.zaladuj_dane()

    def zaladuj_dane(self):
        """Ładuje dane do widoku lub pamięci."""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            # Grupuje po nazwie sprzętu i liczy wystąpienia, sortuje malejąco, ucina do 10
            c.execute('''
                SELECT sprzet, COUNT(*) as ilosc
                FROM zlecenia
                WHERE sprzet IS NOT NULL AND sprzet != ''
                GROUP BY sprzet
                ORDER BY ilosc DESC
                LIMIT 10
            ''')
            rows = c.fetchall()
            conn.close()

            self.table.setRowCount(len(rows))
            for row_idx, row in enumerate(rows):
                self.table.setItem(row_idx, 0, QtWidgets.QTableWidgetItem(str(row[0])))
                item_ilosc = QtWidgets.QTableWidgetItem(str(row[1]))
                item_ilosc.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row_idx, 1, item_ilosc)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, _("Błąd"), f"{_('Wystąpił błąd:')}\n{str(e)}")


class RaportTopNaprawyDialog(QtWidgets.QDialog):
    """Dialog obsługujący wydzielony fragment funkcjonalności aplikacji."""
    def __init__(self, parent=None, db_path=None):
        """Inicjalizuje obiekt i przygotowuje jego stan początkowy."""
        super().__init__(parent)
        if not password_protection.CURRENT_USER_IS_SUPER:
            QtWidgets.QMessageBox.warning(self, _("Brak uprawnień"), _("Dostęp do raportów posiada tylko Administrator."))
            QtCore.QTimer.singleShot(0, self.reject)
            return

        self.db_path = db_path or wczytaj_baze(config.CONFIG_BAZA_FILE, config.DB_FILE)
        self.setWindowTitle(_("Top 10 - Najdroższe naprawy"))
        self.resize(600, 400)

        layout = QtWidgets.QVBoxLayout(self)

        # --- ZMIANA: 3 kolumny, usunięto ID, przesunięto rozciąganie ---
        self.table = QtWidgets.QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels([_("Klient"), _("Sprzęt"), _("Koszt całkowity")])
        self.table.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        layout.addWidget(self.table)

        btn_close = QtWidgets.QPushButton(_("Zamknij"))
        btn_close.clicked.connect(self.close)
        layout.addWidget(btn_close)

        self.zaladuj_dane()

    def zaladuj_dane(self):
        """Ładuje dane do widoku lub pamięci."""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            # --- ZMIANA: Wyciągamy tylko 3 wartości z bazy (bez id) ---
            c.execute('''
                SELECT imie_nazwisko, sprzet,
                       (IFNULL(koszt_czesci, 0) + IFNULL(koszt_uslugi, 0)) as suma
                FROM zlecenia
                ORDER BY suma DESC
                LIMIT 10
            ''')
            rows = c.fetchall()
            conn.close()

            self.table.setRowCount(len(rows))
            for row_idx, row in enumerate(rows):
                # --- ZMIANA: Dopasowane indeksy (0-Klient, 1-Sprzęt, 2-Suma) ---
                self.table.setItem(row_idx, 0, QtWidgets.QTableWidgetItem(str(row[0])))
                self.table.setItem(row_idx, 1, QtWidgets.QTableWidgetItem(str(row[1])))

                item_suma = QtWidgets.QTableWidgetItem(f"{row[2]:.2f} PLN")
                item_suma.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)
                self.table.setItem(row_idx, 2, item_suma)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, _("Błąd"), f"{_('Wystąpił błąd:')}\n{str(e)}")
