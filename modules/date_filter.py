from PySide6 import QtWidgets, QtCore
import datetime

# Zabezpieczenie na wypadek uruchamiania modułu niezależnie (bez main.py)
try:
    _("Test")
except NameError:
    def _(text):
        """Zwraca tekst bez tłumaczenia, gdy mechanizm i18n nie jest aktywny."""
        return text

class DateFilterPopup(QtWidgets.QDialog):
    """Wyskakujące okno pomocnicze używane przez aplikację."""
    def __init__(self, parent=None, current_filter=None):
        """Inicjalizuje obiekt i przygotowuje jego stan początkowy."""
        super().__init__(parent, QtCore.Qt.Popup)
        self.filter_data = current_filter or {"type": "year", "from": None, "to": None}
        self.init_ui()

    def init_ui(self):
        """Buduje i konfiguruje interfejs użytkownika."""
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        self.btn_all = QtWidgets.QPushButton(_("Wszystkie daty"))
        self.btn_today = QtWidgets.QPushButton(_("Dzisiaj"))
        self.btn_this_month = QtWidgets.QPushButton(_("Miesiąc bieżący"))
        self.btn_last_30 = QtWidgets.QPushButton(_("Ostatnie 30 dni"))
        self.btn_this_year = QtWidgets.QPushButton(_("Rok bieżący"))

        layout.addWidget(self.btn_all)
        layout.addWidget(self.btn_today)
        layout.addWidget(self.btn_this_month)
        layout.addWidget(self.btn_last_30)
        layout.addWidget(self.btn_this_year)

        line = QtWidgets.QFrame()
        line.setFrameShape(QtWidgets.QFrame.HLine)
        line.setFrameShadow(QtWidgets.QFrame.Sunken)
        layout.addWidget(line)

        range_label = QtWidgets.QLabel(_("Zakres niestandardowy:"))
        range_label.setStyleSheet("font-weight: bold; margin-top: 5px;")
        layout.addWidget(range_label)

        form_layout = QtWidgets.QFormLayout()

        self.date_from = QtWidgets.QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDisplayFormat("yyyy-MM-dd")

        self.date_to = QtWidgets.QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDisplayFormat("yyyy-MM-dd")
        self.date_to.setDate(QtCore.QDate.currentDate())

        self.date_from.setDate(QtCore.QDate.currentDate().addMonths(-1))

        form_layout.addRow(_("Od:"), self.date_from)
        form_layout.addRow(_("Do:"), self.date_to)
        layout.addLayout(form_layout)

        self.btn_apply_custom = QtWidgets.QPushButton(_("Zastosuj zakres"))
        layout.addWidget(self.btn_apply_custom)

        self.btn_all.clicked.connect(lambda: self.apply_preset("all"))
        self.btn_today.clicked.connect(lambda: self.apply_preset("today"))
        self.btn_this_month.clicked.connect(lambda: self.apply_preset("month"))
        self.btn_last_30.clicked.connect(lambda: self.apply_preset("30days"))
        self.btn_this_year.clicked.connect(lambda: self.apply_preset("year"))
        self.btn_apply_custom.clicked.connect(lambda: self.apply_preset("custom"))

    def apply_preset(self, type_name):
        """Stosuje wybrane ustawienia, dane lub filtr."""
        res = {"type": type_name, "from": None, "to": None}
        today = datetime.date.today()

        if type_name == "today":
            s = today.strftime("%Y-%m-%d")
            res["from"] = s
            res["to"] = s

        elif type_name == "month":
            start = today.replace(day=1)
            res["from"] = start.strftime("%Y-%m-%d")
            res["to"] = None

        elif type_name == "30days":
            start = today - datetime.timedelta(days=30)
            res["from"] = start.strftime("%Y-%m-%d")
            res["to"] = None

        elif type_name == "year":
            start = today.replace(month=1, day=1)
            res["from"] = start.strftime("%Y-%m-%d")
            res["to"] = None

        elif type_name == "custom":
            res["from"] = self.date_from.date().toString("yyyy-MM-dd")
            res["to"] = self.date_to.date().toString("yyyy-MM-dd")

        elif type_name == "all":
            pass

        self.filter_data = res
        self.accept()

    def get_filter_data(self):
        """Zwraca wymagane dane lub ustawienia."""
        return self.filter_data

    def get_label_text(self):
        """Zwraca wymagane dane lub ustawienia."""
        t = self.filter_data["type"]

        # 1. Pobieramy i parsujemy datę 'from', żeby wiedzieć jaki to miesiąc/rok
        date_str = self.filter_data.get('from')
        dt = None
        if date_str:
            try:
                dt = datetime.datetime.strptime(date_str, "%Y-%m-%d")
            except ValueError:
                pass

        if t == "all": return _("Wszystkie daty")
        if t == "today": return _("Dzisiaj")

        if t == "month":
            if dt:
                # Słownik polskich nazw miesięcy
                nazwy_miesiecy = {
                    1: "Styczeń", 2: "Luty", 3: "Marzec", 4: "Kwiecień",
                    5: "Maj", 6: "Czerwiec", 7: "Lipiec", 8: "Sierpień",
                    9: "Wrzesień", 10: "Październik", 11: "Listopad", 12: "Grudzień"
                }
                # Zwraca np. "Grudzień" (lub "Grudzień 2025" jeśli wolisz dopisać {dt.year})
                return nazwy_miesiecy.get(dt.month, _("Miesiąc"))
            return _("Miesiąc")

        if t == "30days": return _("Ostatnie 30 dni")

        if t == "year":
            if dt:
                # Zwraca sam rok, np. "2025"
                return str(dt.year)
            return _("Rok")

        if t == "custom":
            d1 = self.filter_data['from']
            d2 = self.filter_data['to']
            if not d2: return f"{_('Od')} {d1}"
            return f"{d1} - {d2}"

        return _("Data")
