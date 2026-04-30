from PySide6 import QtWidgets, QtCore, QtGui
import datetime
from collections import Counter
from modules.utils import resource_path
from modules.zlecenia import dodaj_zlecenie

try:
    _("Test")
except NameError:
    def _(text):
        """Zwraca tekst bez tłumaczenia, gdy mechanizm i18n nie jest aktywny."""
        return text

class KlienciWindow(QtWidgets.QDialog):
    """Okno obsługujące wydzielony fragment funkcjonalności aplikacji."""
    def __init__(self, parent, conn, model, ui):
        """Inicjalizuje obiekt i przygotowuje jego stan początkowy."""
        super().__init__(parent)
        self.conn = conn
        self.model = model
        self.ui = ui

        self.setWindowTitle(_("Baza Kontrahentów"))
        self.resize(800, 600)
        self.init_ui()
        self.load_clients()

    def init_ui(self):
        """Buduje i konfiguruje interfejs użytkownika."""
        layout = QtWidgets.QHBoxLayout(self)

        left_layout = QtWidgets.QVBoxLayout()

        # --- ZMIANA: Układ poziomy dla szukania i przycisku dodawania ---
        search_layout = QtWidgets.QHBoxLayout()

        self.search_input = QtWidgets.QLineEdit()
        self.search_input.setPlaceholderText(_("Szukaj kontrahenta..."))
        self.search_input.textChanged.connect(self.filter_list)

        # Tworzymy "plusik"
        self.btn_quick_add = QtWidgets.QPushButton("+")
        self.btn_quick_add.setFixedSize(30, 30)  # Kwadratowy przycisk
        self.btn_quick_add.setToolTip(_("Dodaj nowego klienta (aktywne, gdy nie znaleziono)"))
        self.btn_quick_add.setEnabled(False)  # Domyślnie nieaktywny
        self.btn_quick_add.clicked.connect(self.quick_add_client)

        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.btn_quick_add)

        left_layout.addLayout(search_layout)
        # ----------------------------------------------------------------

        self.client_list = QtWidgets.QListWidget()
        self.client_list.itemClicked.connect(self.show_stats)
        left_layout.addWidget(self.client_list)

        btn_layout = QtWidgets.QHBoxLayout()
        self.btn_add = QtWidgets.QPushButton(_("Dodaj Zlecenie dla Klienta"))
        self.btn_add.setIcon(QtGui.QIcon(resource_path("actions/dodaj.png")))
        self.btn_add.clicked.connect(self.add_new_job_for_client)

        self.btn_del = QtWidgets.QPushButton(_("Usuń Historię Klienta"))
        self.btn_del.setIcon(QtGui.QIcon(resource_path("actions/usun.png")))
        self.btn_del.clicked.connect(self.delete_client_history)

        btn_layout.addWidget(self.btn_add)
        btn_layout.addWidget(self.btn_del)
        left_layout.addLayout(btn_layout)

        right_group = QtWidgets.QGroupBox(_("Informacje o Kontrahencie"))
        right_layout = QtWidgets.QVBoxLayout(right_group)
        right_layout.setAlignment(QtCore.Qt.AlignTop)

        self.lbl_name = QtWidgets.QLabel(_("Wybierz klienta z listy"))
        self.lbl_name.setStyleSheet("font-size: 16pt; font-weight: bold; color: #2c3e50; margin-bottom: 15px;")
        self.lbl_name.setWordWrap(True)
        self.lbl_name.setAlignment(QtCore.Qt.AlignCenter)
        right_layout.addWidget(self.lbl_name)

        line1 = QtWidgets.QFrame()
        line1.setFrameShape(QtWidgets.QFrame.HLine)
        line1.setFrameShadow(QtWidgets.QFrame.Sunken)
        right_layout.addWidget(line1)

        style_contact = "font-size: 11pt; margin: 2px;"
        self.lbl_phone = QtWidgets.QLabel()
        self.lbl_email = QtWidgets.QLabel()
        self.lbl_phone.setStyleSheet(style_contact)
        self.lbl_email.setStyleSheet(style_contact)
        self.lbl_phone.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        self.lbl_email.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)

        right_layout.addWidget(self.lbl_phone)
        right_layout.addWidget(self.lbl_email)

        line2 = QtWidgets.QFrame()
        line2.setFrameShape(QtWidgets.QFrame.HLine)
        line2.setFrameShadow(QtWidgets.QFrame.Sunken)
        right_layout.addWidget(line2)

        style_stat = "font-size: 11pt; margin: 5px;"

        self.lbl_visits = QtWidgets.QLabel()
        self.lbl_total_cost = QtWidgets.QLabel()
        self.lbl_avg_days = QtWidgets.QLabel()
        self.lbl_top_device = QtWidgets.QLabel()
        self.lbl_last_visit = QtWidgets.QLabel()

        for lbl in [self.lbl_visits, self.lbl_total_cost, self.lbl_avg_days, self.lbl_top_device, self.lbl_last_visit]:
            lbl.setStyleSheet(style_stat)
            lbl.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
            right_layout.addWidget(lbl)

        right_layout.addStretch()

        splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        left_widget = QtWidgets.QWidget()
        left_widget.setLayout(left_layout)

        splitter.addWidget(left_widget)
        splitter.addWidget(right_group)
        splitter.setSizes([300, 600])

        layout.addWidget(splitter)

    def load_clients(self):
        """Wczytuje dane lub ustawienia potrzebne do działania."""
        c = self.conn.cursor()
        c.execute("""
            SELECT imie_nazwisko, COUNT(*) as cnt
            FROM zlecenia
            GROUP BY imie_nazwisko
            ORDER BY imie_nazwisko ASC
        """)
        rows = c.fetchall()

        self.client_list.clear()
        for name, count in rows:
            if not name.strip(): continue
            item = QtWidgets.QListWidgetItem(f"{name} ({count})")
            item.setData(QtCore.Qt.UserRole, name)
            self.client_list.addItem(item)

        # Po przeładowaniu resetujemy stan wyszukiwania
        self.filter_list(self.search_input.text())

    def filter_list(self, text):
        """Filtruje dane zgodnie z bieżącymi kryteriami."""
        visible_count = 0
        for i in range(self.client_list.count()):
            item = self.client_list.item(i)
            # Sprawdzamy czy tekst pasuje
            is_match = text.lower() in item.text().lower()
            item.setHidden(not is_match)

            if is_match:
                visible_count += 1

        if len(text.strip()) > 0 and visible_count == 0:
            self.btn_quick_add.setEnabled(True)
            # Opcjonalnie: zmiana koloru przycisku, żeby rzucał się w oczy
            self.btn_quick_add.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold;")
        else:
            self.btn_quick_add.setEnabled(False)
            self.btn_quick_add.setStyleSheet("")

    def quick_add_client(self):
        """Dodaje zlecenie dla klienta wpisanego w wyszukiwarkę (nowy klient)."""
        new_name = self.search_input.text().strip()

        if not new_name:
            return

        # Przekazujemy wpisane imię/nazwisko jako prefill
        prefill_data = {
            _("Imię i nazwisko"): new_name,
            _("Telefon"): "",
            _("E-mail"): ""
        }

        try:
            # Wywołujemy dodawanie zlecenia
            dodaj_zlecenie(self.conn, self.conn.cursor(), self.model, self.ui, parent=self, prefill=prefill_data)

            # Po dodaniu czyścimy szukajkę i odświeżamy listę, żeby nowy klient się pojawił
            self.search_input.clear()
            self.load_clients()

        except Exception as e:
             QtWidgets.QMessageBox.critical(self, _("Błąd"), f"{_('Nie udało się otworzyć okna dodawania:')}\n{e}")

    def show_stats(self, item):
        """Wyświetla statystyki dla wybranego klienta."""
        name = item.data(QtCore.Qt.UserRole)
        self.lbl_name.setText(name)

        c = self.conn.cursor()

        last_contact = c.execute("""
            SELECT telefon, email
            FROM zlecenia
            WHERE imie_nazwisko = ?
            ORDER BY id DESC LIMIT 1
        """, (name,)).fetchone()

        tel = last_contact[0] if last_contact else "-"
        em = last_contact[1] if last_contact else "-"

        self.lbl_phone.setText(f"📞 {tel}")
        self.lbl_email.setText(f"📧 {em}")

        c.execute("""
            SELECT data_zlecenia, koszt_czesci, koszt_uslugi, sprzet
            FROM zlecenia
            WHERE imie_nazwisko = ?
            ORDER BY data_zlecenia ASC
        """, (name,))
        rows = c.fetchall()

        if not rows:
            return

        visits_count = len(rows)
        total_spent = 0.0
        devices = []
        dates = []

        for r in rows:
            try:
                date_obj = datetime.datetime.strptime(r[0], "%Y-%m-%d").date()
                dates.append(date_obj)
            except: pass

            k_cz = r[1] if r[1] else 0.0
            k_us = r[2] if r[2] else 0.0
            total_spent += (k_cz + k_us)

            if r[3]: devices.append(r[3])

        avg_days_str = _("Brak danych (1 wizyta)")
        if len(dates) > 1:
            first_visit = dates[0]
            last_visit = dates[-1]
            days_diff = (last_visit - first_visit).days
            if days_diff > 0:
                avg = days_diff / (len(dates) - 1)
                avg_days_str = f"{avg:.0f} {_('dni')}"
            else:
                avg_days_str = _("Wiele wizyt tego samego dnia")

        top_device_str = _("Brak")
        if devices:
            counts = Counter(devices)
            top_device, count = counts.most_common(1)[0]
            top_device_str = f"{top_device} ({count}x)"

        last_visit_str = dates[-1].strftime("%d.%m.%Y") if dates else "-"

        style_val = "<span style='font-weight:bold; color:#2980b9;'>"

        self.lbl_visits.setText(f"{_('Odwiedził nas:')} {style_val}{visits_count}x</span>")
        self.lbl_total_cost.setText(f"{_('Łączny koszt napraw:')} {style_val}{total_spent:.2f} PLN</span>")
        self.lbl_avg_days.setText(f"{_('Średnio w serwisie co:')} {style_val}{avg_days_str}</span>")
        self.lbl_top_device.setText(f"{_('Najczęściej naprawia:')} {style_val}{top_device_str}</span>")
        self.lbl_last_visit.setText(f"{_('Ostatnia wizyta:')} {style_val}{last_visit_str}</span>")

    def delete_client_history(self):
        """Usuwa wskazane dane lub elementy."""
        from modules import password_protection
        if not password_protection.wymagany_admin(self):
            return
        item = self.client_list.currentItem()
        if not item: return
        name = item.data(QtCore.Qt.UserRole)

        reply = QtWidgets.QMessageBox.warning(
            self,
            _("Potwierdzenie usunięcia"),
            _("Czy na pewno chcesz usunąć całą historię klienta:\n\n"
              "👤 {}\n\n"
              "Spowoduje to trwałe usunięcie WSZYSTKICH zleceń tego klienta!").format(name),
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )

        if reply == QtWidgets.QMessageBox.Yes:
            c = self.conn.cursor()
            c.execute("DELETE FROM zlecenia WHERE imie_nazwisko = ?", (name,))
            self.conn.commit()
            self.load_clients()
            self.lbl_name.setText(_("Usunięto pomyślnie"))
            self.lbl_phone.setText("")
            self.lbl_email.setText("")
            self.lbl_visits.setText("")
            self.lbl_total_cost.setText("")

    def add_new_job_for_client(self):
        """Dodaje nowy element lub rekord."""
        item = self.client_list.currentItem()
        if not item:
            QtWidgets.QMessageBox.warning(self, _("Uwaga"), _("Wybierz najpierw klienta z listy!"))
            return

        name = item.data(QtCore.Qt.UserRole)
        c = self.conn.cursor()

        last_data = c.execute("SELECT telefon, email FROM zlecenia WHERE imie_nazwisko=? ORDER BY id DESC LIMIT 1", (name,)).fetchone()

        prefill_data = {
            _("Imię i nazwisko"): name,
            _("Telefon"): last_data[0] if last_data else "",
            _("E-mail"): last_data[1] if last_data else ""
        }


        try:
            dodaj_zlecenie(self.conn, c, self.model, self.ui, parent=self, prefill=prefill_data)
        except Exception as e:
             QtWidgets.QMessageBox.critical(self, _("Błąd"), f"{_('Nie udało się otworzyć okna dodawania:')}\n{e}")
