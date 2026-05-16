import os
import json
import sqlite3
import datetime
from io import BytesIO
import base64
import copy
import configparser

from PySide6 import QtWidgets, QtGui, QtCore
from PySide6.QtPrintSupport import QPrinter, QPrintDialog, QPrintPreviewDialog
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QPixmap, QPageSize, QTextDocument, QPageLayout, QImage
from PySide6.QtCore import QRectF, Qt, QPointF, QSize

from setup import config
try:
    import barcode
    from barcode.writer import ImageWriter
    BARCODE_AVAILABLE = True
except ImportError:
    BARCODE_AVAILABLE = False

from modules.utils import formatuj_numer_zlecenia

# Zabezpieczenie tłumaczeń
try:
    _("Test")
except NameError:
    def _(text):
        """Zwraca tekst bez tłumaczenia, gdy mechanizm i18n nie jest aktywny."""
        return text

LAYOUT_FILE = os.path.join(os.path.expanduser("~"), ".SerwisApp", "config", "print_layout.json")
DEFAULT_RODO_TEXT = (
    "1. Serwis nie odpowiada za utratę danych na nośnikach.\n"
    "2. Sprzęt nieodebrany w terminie 30 dni od powiadomienia może zostać zutylizowany.\n"
    "3. Podpisując zlecenie, klient akceptuje regulamin serwisu."
)

TEMPLATE_MAP = {
    "PRZYJĘCIE ZLECENIA": "zlecenie",
    "WYDANIE ZLECENIA": "raport"
}


def _get_podpis_text(template_key, copy_idx=None):
    """Zwraca właściwy podpis dla danego typu wydruku i kopii."""
    if template_key == "zlecenie":
        if copy_idx == 1:
            return "Podpis Klienta: ...................."
        if copy_idx == 0:
            return "Podpis Serwisu: ...................."
        return "Podpis wg kopii: Serwis / Klient"
    return "Podpis Serwisu: ...................."

# ============================================================================
# KONFIGURACJA
# ============================================================================
def _get_config():
    """Realizuje logikę operacji get config."""
    cfg = configparser.ConfigParser()
    if os.path.exists(config.CONFIG_FILE):
        cfg.read(config.CONFIG_FILE, encoding="utf-8")
    if "PRINTING" not in cfg:
        cfg["PRINTING"] = {}
    return cfg

def _save_config(cfg):
    """Realizuje logikę operacji save config."""
    with open(config.CONFIG_FILE, "w", encoding="utf-8") as f:
        cfg.write(f)
def get_print_mode():
    """Zwraca wymagane dane lub ustawienia."""
    return _get_config().get("PRINTING", "mode", fallback="visual")
def set_print_mode(mode):
    """Ustawia wskazaną wartość lub tryb działania."""
    cfg = _get_config(); cfg["PRINTING"]["mode"] = mode; _save_config(cfg)
def get_preview_mode():
    """Zwraca wymagane dane lub ustawienia."""
    return _get_config().getboolean("PRINTING", "preview", fallback=True)
def set_preview_mode(enabled):
    """Ustawia wskazaną wartość lub tryb działania."""
    cfg = _get_config(); cfg["PRINTING"]["preview"] = "yes" if enabled else "no"; _save_config(cfg)
def get_report_engine():
    """Zwraca wymagane dane lub ustawienia."""
    return _get_config().get("PRINTING", "report_engine", fallback="visual")
def set_report_engine(engine):
    """Ustawia wskazaną wartość lub tryb działania."""
    cfg = _get_config(); cfg["PRINTING"]["report_engine"] = engine; _save_config(cfg)
def get_order_engine():
    """Zwraca wymagane dane lub ustawienia."""
    return _get_config().get("PRINTING", "order_engine", fallback="visual")
def set_order_engine(engine):
    """Ustawia wskazaną wartość lub tryb działania."""
    cfg = _get_config(); cfg["PRINTING"]["order_engine"] = engine; _save_config(cfg)

# ============================================================================
# DOMYŚLNY UKŁAD
# ============================================================================
DEFAULT_LAYOUT = {
    "zlecenie": {
        "header": {"x": 20, "y": 20, "w": 520, "h": 50, "label": "Nagłówek", "font_size": 16, "bold": True, "align": "center", "visible_client": True, "visible_service": True},
        "logo": {"x": 20, "y": 80, "w": 100, "h": 100, "label": "LOGO", "type": "image", "visible_client": True, "visible_service": True},
        "firma": {"x": 130, "y": 80, "w": 220, "h": 100, "label": "Dane Firmy", "font_size": 9, "visible_client": True, "visible_service": True},
        "barcode": {"x": 360, "y": 80, "w": 180, "h": 60, "label": "Kod Kreskowy", "type": "barcode", "visible_client": True, "visible_service": True},
        "klient": {"x": 20, "y": 190, "w": 520, "h": 80, "label": "Dane Klienta", "border": True, "border_width": 1, "font_size": 11, "visible_client": True, "visible_service": True},
        "urzadzenie": {"x": 20, "y": 280, "w": 520, "h": 60, "label": "Urządzenie", "border": True, "border_width": 1, "bg": True, "font_size": 12, "visible_client": True, "visible_service": True},
        "opis": {"x": 20, "y": 350, "w": 520, "h": 150, "label": "Opis Usterki", "font_size": 11, "visible_client": True, "visible_service": True},
        "uwagi": {"x": 20, "y": 510, "w": 520, "h": 80, "label": "Uwagi", "font_size": 10, "visible_client": True, "visible_service": True},
        "rodo": {"x": 20, "y": 600, "w": 520, "h": 80, "label": "Regulamin (Edytowalny)", "font_size": 7, "text": DEFAULT_RODO_TEXT, "visible_client": True, "visible_service": True},
        "podpisy": {"x": 20, "y": 700, "w": 520, "h": 80, "label": "Podpisy", "font_size": 10, "align": "right", "visible_client": True, "visible_service": True},
        "stopka": {"x": 20, "y": 750, "w": 520, "h": 30, "label": "Stopka", "font_size": 8, "align": "center", "visible_client": True, "visible_service": True}
    },
    "raport": {
        "header": {"x": 20, "y": 20, "w": 730, "h": 50, "label": "Tytuł Raportu", "font_size": 24, "bold": True, "align": "center", "visible": True},
        "logo": {"x": 20, "y": 80, "w": 100, "h": 100, "label": "LOGO", "type": "image", "visible": True},
        "firma": {"x": 130, "y": 80, "w": 620, "h": 100, "label": "Dane Firmy", "font_size": 10, "visible": True},
        "info": {"x": 20, "y": 190, "w": 730, "h": 100, "label": "Info Zlecenia", "border": True, "border_width": 1, "font_size": 12, "visible": True},
        "naprawa": {"x": 20, "y": 310, "w": 730, "h": 200, "label": "Opis Naprawy", "border": True, "border_width": 1, "font_size": 12, "visible": True},
        "koszty": {"x": 400, "y": 530, "w": 350, "h": 150, "label": "Tabela Kosztów", "border": True, "border_width": 1, "bg": True, "font_size": 14, "visible": True},
        "podpisy": {"x": 400, "y": 700, "w": 350, "h": 80, "label": "Podpisy", "font_size": 10, "align": "right", "visible": True},
        "stopka": {"x": 20, "y": 1000, "w": 730, "h": 50, "label": "Stopka", "align": "center", "font_size": 10, "visible": True}
    }
}

# ============================================================================
# POMOCNICZE: DANE PRZYKŁADOWE
# ============================================================================
def get_sample_data():
    """Pobiera prawdziwe dane z bazy lub tworzy atrapę."""
    data = {
        "id": "2024/10/123", "data": datetime.date.today().strftime("%Y-%m-%d"),
        "imie": "Jan Kowalski", "telefon": "500 123 456", "email": "jan@example.com",
        "sprzet": "Laptop Dell Inspiron", "sn": "8F3K12J",
        "opis": "Laptop nie uruchamia się, czarny ekran, diody świecą.",
        "uwagi": "Zasilacz w komplecie. Obudowa porysowana.",
        "status": "W trakcie", "naprawa": "Wymiana dysku SSD, instalacja systemu, czyszczenie układu chłodzenia.",
        "koszt_czesci": "250.00 zł", "koszt_uslugi": "150.00 zł", "koszt_suma": "400.00 zł",
        "rok": str(datetime.date.today().year),
        "firma_full": "Twój Serwis Komputerowy\nul. Serwisowa 12/3\n00-001 Warszawa\nNIP: 123-456-78-90\nTel: 123 456 789"
    }

    try:
        conn = sqlite3.connect(config.DB_FILE)
        cursor = conn.cursor()

        f = cursor.execute("SELECT * FROM firma LIMIT 1").fetchone()
        if f:
            fd = f"{f[1]}\n{f[2]}\nTel: {f[3]} | Email: {f[4]}\nNIP: {f[5]}"
            if f[6]: fd += f"\n{f[6]}"
            data["firma_full"] = fd

        z = cursor.execute("SELECT * FROM zlecenia ORDER BY id DESC LIMIT 1").fetchone()
        if z:
            raw_date = z[8]
            val_nr_roczny = z[14] if len(z) >= 15 else None
            data["id"] = formatuj_numer_zlecenia(z[0], raw_date, val_nr_roczny)
            data["data"] = raw_date
            data["imie"] = z[1]
            data["telefon"] = z[2]
            data["sprzet"] = z[3]
            data["sn"] = z[4]
            data["opis"] = z[5]
            data["uwagi"] = z[6] or ""
            data["email"] = z[9] or ""
            data["naprawa"] = z[10] or ""
            try: k_cz = float(z[11] or 0); k_us = float(z[12] or 0)
            except: k_cz=0; k_us=0
            data["koszt_czesci"] = f"{k_cz:.2f} zł"
            data["koszt_uslugi"] = f"{k_us:.2f} zł"
            data["koszt_suma"] = f"{k_cz+k_us:.2f} zł"

        conn.close()
    except Exception as e:
        print(f"Błąd pobierania danych przykładowych: {e}")

    return data

# ============================================================================
# ELEMENTY GRAFICZNE
# ============================================================================
class ResizeHandle(QtWidgets.QGraphicsRectItem):
    """Pomocniczy uchwyt wykorzystywany przez interfejs aplikacji."""
    def __init__(self, parent):
        """Inicjalizuje obiekt i przygotowuje jego stan początkowy."""
        super().__init__(0, 0, 15, 15, parent)
        self.setBrush(QBrush(Qt.black))
        self.setCursor(Qt.SizeFDiagCursor)
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable, False)
        self.updatePosition()

    def updatePosition(self):
        """Aktualizuje położenie elementu pomocniczego."""
        p = self.parentItem().rect()
        self.setPos(p.width() - 15, p.height() - 15)

class ReportItem(QtWidgets.QGraphicsRectItem):
    """Element graficzny wykorzystywany przez interfejs aplikacji."""
    def __init__(self, key, data, editor):
        """Inicjalizuje obiekt i przygotowuje jego stan początkowy."""
        x, y, w, h = data.get("x", 0), data.get("y", 0), data.get("w", 100), data.get("h", 50)
        super().__init__(0, 0, w, h)
        self.setPos(x, y)
        self.key = key
        self.data = data.copy()
        self.editor = editor
        self.setFlags(QtWidgets.QGraphicsItem.ItemIsMovable | QtWidgets.QGraphicsItem.ItemIsSelectable | QtWidgets.QGraphicsItem.ItemSendsGeometryChanges)
        self.handle = ResizeHandle(self)
        self._resizing = False

    def itemChange(self, change, value):
        """Reaguje na zmianę właściwości elementu."""
        if change == QtWidgets.QGraphicsItem.ItemPositionChange:
            new_pos = value
            new_pos.setX(round(new_pos.x() / 10) * 10)
            new_pos.setY(round(new_pos.y() / 10) * 10)
            self.data["x"] = int(new_pos.x())
            self.data["y"] = int(new_pos.y())
            self.editor.update_properties_panel(self)
            return new_pos
        return super().itemChange(change, value)

    def paint(self, painter, option, widget=None):
        """Renderuje zawartość elementu graficznego."""
        rect = self.rect()
        if self.isSelected():
            painter.setPen(QPen(Qt.blue, 1, Qt.DashLine))
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(rect)

        if self.data.get("bg"): painter.fillRect(rect, QColor(240, 240, 240))
        if self.data.get("border"):
            bw = self.data.get("border_width", 1)
            painter.setPen(QPen(Qt.black, bw))
            painter.drawRect(rect)

        type_ = self.data.get("type", "text")
        if type_ == "image" and self.editor.logo_pixmap:
            scaled = self.editor.logo_pixmap.scaled(QSize(int(rect.width()), int(rect.height())), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            off_x = (rect.width() - scaled.width()) / 2
            off_y = (rect.height() - scaled.height()) / 2
            painter.drawPixmap(int(off_x), int(off_y), scaled)
        elif type_ == "barcode":
            painter.fillRect(QRectF(rect.x()+5, rect.y()+5, rect.width()-10, rect.height()-10), Qt.black)
            painter.setPen(Qt.white)
            painter.drawText(rect, Qt.AlignCenter, "|| ||| || |||")
        else:
            painter.setPen(Qt.black)
            font = QFont("Arial")
            font.setPixelSize(self.data.get("font_size", 12))
            font.setBold(self.data.get("bold", False))
            painter.setFont(font)

            align = Qt.AlignLeft | Qt.AlignTop
            if self.data.get("align") == "center": align = Qt.AlignCenter
            elif self.data.get("align") == "right": align = Qt.AlignRight

            text_content = self._get_preview_text()
            text_rect = QRectF(rect)
            if self.data.get("border"):
                offset = 4 + (self.data.get("border_width", 1) / 2)
                text_rect.adjust(offset, offset, -offset, -offset)
            else:
                text_rect.adjust(2, 2, -2, -2)
            painter.drawText(text_rect, align | Qt.TextWordWrap, text_content)

    def _get_preview_text(self):
        """Realizuje logikę operacji get preview text w klasie ReportItem."""
        d = self.editor.sample_data
        k = self.key
        if k == "header": return f"POTWIERDZENIE PRZYJĘCIA\nNr: {d['id']}" if self.editor.current_template == "zlecenie" else f"RAPORT Z NAPRAWY - {d['id']}"
        elif k == "firma": return d.get("firma_full", "Dane Firmy")
        elif k == "klient": return f"KLIENT:\n{d['imie']}\nTel: {d['telefon']}\nEmail: {d['email']}"
        elif k == "urzadzenie": return f"URZĄDZENIE: {d['sprzet']}\nSN: {d['sn']}"
        elif k == "opis": return f"USTERKA:\n{d['opis']}"
        elif k == "uwagi": return f"UWAGI:\n{d['uwagi']}"
        elif k == "naprawa": return f"WYKONANE CZYNNOŚCI:\n{d['naprawa']}"
        elif k == "koszty": return f"Części: {d['koszt_czesci']}\nUsługa: {d['koszt_uslugi']}\nRAZEM: {d['koszt_suma']}"
        elif k == "rodo": return self.data.get("text", DEFAULT_RODO_TEXT)
        elif k == "stopka": return f"Wydrukowano z SerwisApp © {d['rok']}"
        elif k == "info": return f"Data: {d['data']}\nKlient: {d['imie']}\nSprzęt: {d['sprzet']}"
        elif k == "podpisy": return _get_podpis_text(self.editor.current_template)
        return self.data.get("label", k)

    def mousePressEvent(self, event):
        """Obsługuje naciśnięcie przycisku myszy."""
        if self.handle.isUnderMouse():
            self._resizing = True
            self._resize_start = event.scenePos()
            self._orig_rect = self.rect()
        else:
            self._resizing = False
            super().mousePressEvent(event)
        self.editor.update_properties_panel(self)
        self.update()

    def mouseMoveEvent(self, event):
        """Obsługuje ruch myszy nad elementem."""
        if self._resizing:
            diff = event.scenePos() - self._resize_start
            new_w = max(30, self._orig_rect.width() + diff.x())
            new_h = max(30, self._orig_rect.height() + diff.y())
            new_w = round(new_w / 10) * 10
            new_h = round(new_h / 10) * 10
            self.setRect(0, 0, new_w, new_h)
            self.handle.updatePosition()
            self.data["w"] = int(new_w)
            self.data["h"] = int(new_h)
            self.editor.update_properties_panel(self)
            self.update()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """Obsługuje zwolnienie przycisku myszy."""
        self._resizing = False
        super().mouseReleaseEvent(event)
        self.update()

# ============================================================================
# EDYTOR (OKNO GŁÓWNE)
# ============================================================================
class VisualEditor(QtWidgets.QDialog):
    """Klasa pomocnicza używana przez aplikację."""
    def __init__(self, parent):
        """Inicjalizuje obiekt i przygotowuje jego stan początkowy."""
        super().__init__(parent)
        self.setWindowTitle(_("Projektant Wydruku - WYSIWYG"))
        self.resize(1450, 950)
        self.sample_data = get_sample_data()
        self.logo_pixmap = None
        if os.path.exists(config.DST_LOGO_FILE): self.logo_pixmap = QPixmap(config.DST_LOGO_FILE)
        self.current_template = "zlecenie"
        self.items = {}
        self.layout_config = self.load_config()
        self.init_ui()
        self.load_scene()
        self.update_ui_state()

    def load_config(self):
        """Wczytuje dane lub ustawienia potrzebne do działania."""
        if os.path.exists(LAYOUT_FILE):
            try:
                with open(LAYOUT_FILE, "r", encoding="utf-8") as f: return json.load(f)
            except: pass
        return copy.deepcopy(DEFAULT_LAYOUT)

    def init_ui(self):
        """Buduje i konfiguruje interfejs użytkownika."""
        layout = QtWidgets.QHBoxLayout(self)

        panel = QtWidgets.QWidget()
        panel.setFixedWidth(340)
        p_layout = QtWidgets.QVBoxLayout(panel)

        p_layout.addWidget(QtWidgets.QLabel(_("<b>Edytowany Szablon:</b>")))
        self.combo = QtWidgets.QComboBox()
        self.combo.addItems(list(TEMPLATE_MAP.keys()))
        self.combo.currentTextChanged.connect(self.change_template)
        p_layout.addWidget(self.combo)

        p_layout.addSpacing(15)
        p_layout.addWidget(QtWidgets.QLabel(_("<b>Ustawienia Globalne:</b>")))

        self.chk_preview_mode = QtWidgets.QCheckBox(_("Pokaż podgląd przed drukiem"))
        # Wczytujemy stan, ale NIE podpinamy od razu zapisu!
        self.chk_preview_mode.setChecked(get_preview_mode())
        p_layout.addWidget(self.chk_preview_mode)

        p_layout.addSpacing(15)

        self.group_vis = QtWidgets.QGroupBox(_("Widoczne na wydruku"))
        self.grid_vis = QtWidgets.QGridLayout(self.group_vis)
        scroll_vis = QtWidgets.QScrollArea()
        scroll_vis.setWidgetResizable(True)
        scroll_vis.setWidget(self.group_vis)
        scroll_vis.setMaximumHeight(200)
        p_layout.addWidget(scroll_vis)

        p_layout.addSpacing(10)

        self.group_props = QtWidgets.QGroupBox(_("Właściwości Elementu"))
        form = QtWidgets.QFormLayout(self.group_props)
        self.lbl_id = QtWidgets.QLabel("-")
        self.spin_font = QtWidgets.QSpinBox(); self.spin_font.setRange(6, 120); self.spin_font.setSuffix(" px")
        self.chk_bold = QtWidgets.QCheckBox(_("Pogrubienie"))

        border_layout = QtWidgets.QHBoxLayout()
        self.chk_border = QtWidgets.QCheckBox(_("Ramka"))
        self.spin_border = QtWidgets.QSpinBox(); self.spin_border.setRange(1, 10); self.spin_border.setSuffix(" px")
        border_layout.addWidget(self.chk_border); border_layout.addWidget(self.spin_border)

        self.chk_center = QtWidgets.QCheckBox(_("Wyśrodkowanie"))
        self.txt_content = QtWidgets.QPlainTextEdit(); self.txt_content.setMinimumHeight(100); self.txt_content.setMaximumHeight(150)

        form.addRow("ID:", self.lbl_id); form.addRow("Rozmiar:", self.spin_font); form.addRow("", self.chk_bold)
        form.addRow("", border_layout); form.addRow("", self.chk_center); form.addRow("Treść:", self.txt_content)

        self.spin_font.valueChanged.connect(self.prop_changed)
        self.chk_bold.stateChanged.connect(self.prop_changed)
        self.chk_border.stateChanged.connect(self.prop_changed)
        self.spin_border.valueChanged.connect(self.prop_changed)
        self.chk_center.stateChanged.connect(self.prop_changed)
        self.txt_content.textChanged.connect(self.text_content_changed)

        p_layout.addWidget(self.group_props); self.group_props.setEnabled(False)
        p_layout.addStretch()

        btn_preview = QtWidgets.QPushButton(_("👁 Podgląd Wydruku"))
        btn_preview.setStyleSheet("font-weight: bold; padding: 8px;")
        btn_preview.clicked.connect(self.show_live_preview)
        p_layout.addWidget(btn_preview)

        p_layout.addSpacing(5)

        btns_layout = QtWidgets.QHBoxLayout()
        btn_reset = QtWidgets.QPushButton(_("Przywróć ustawienia"))
        btn_reset.clicked.connect(self.reset_to_defaults)
        btns_layout.addWidget(btn_reset)

        btn_save = QtWidgets.QPushButton(_("Zapisz ustawienia"))
        # TO JEDYNE MIEJSCE GDZIE ZAPISUJEMY
        btn_save.clicked.connect(self.save_all_settings)
        btns_layout.addWidget(btn_save)
        p_layout.addLayout(btns_layout)

        btn_close = QtWidgets.QPushButton(_("Zamknij"))
        btn_close.clicked.connect(self.close)
        p_layout.addWidget(btn_close)

        layout.addWidget(panel)

        self.scene = QtWidgets.QGraphicsScene()
        self.view = QtWidgets.QGraphicsView(self.scene)
        self.view.setBackgroundBrush(QBrush(QColor(180, 180, 180)))
        layout.addWidget(self.view)

        self.overlay_info = QtWidgets.QLabel(_("Edycja wizualna niedostępna w trybie 'Prosty wydruk A4'"), self.view)
        self.overlay_info.setStyleSheet("background: rgba(255, 255, 255, 200); color: red; font-size: 16px; font-weight: bold; padding: 10px;")
        self.overlay_info.setAlignment(Qt.AlignCenter)
        self.overlay_info.setVisible(False)

        self.current_item = None

    def resizeEvent(self, event):
        """Obsługuje zmianę rozmiaru widżetu."""
        if hasattr(self, 'overlay_info'): self.overlay_info.resize(self.view.size())
        super().resizeEvent(event)

    def show_live_preview(self):
        """Wyświetla podgląd generowanego wydruku lub dokumentu."""
        template_name = self.combo.currentText()
        internal_key = TEMPLATE_MAP.get(template_name, "zlecenie")
        # Zmieniamy na sztywno na "visual"
        mode = "visual"

        printer = QPrinter(QPrinter.HighResolution)
        printer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
        printer.setFullPage(True)

        # --- ZABEZPIECZENIE NAZWY PLIKU DLA PDF ---
        safe_name = self.sample_data["id"].replace("/", "_").replace("\\", "_")
        #printer.setOutputFileName(f"{safe_name}.pdf")
        printer.setDocName(self.sample_data["id"])

        if mode == "html":
            template_file = config.WZORZEC_HTML
            if internal_key == "raport" and config.WZORZEC_RAPORT:
                 template_file = config.WZORZEC_RAPORT

            if not os.path.exists(template_file):
                QtWidgets.QMessageBox.warning(self, "Błąd", "Brak pliku szablonu HTML.")
                return

            with open(template_file, "r", encoding="utf-8") as f:
                html = f.read()

            try:
                conn = sqlite3.connect(config.DB_FILE); cur = conn.cursor()
                firma = cur.execute("SELECT * FROM firma LIMIT 1").fetchone(); conn.close()
                if firma:
                    firma_html = _("""<table style="width:100%; border:none; margin-bottom:5px;"><tr><td style="width:100px; vertical-align:top;"><img src="file:///{logo}" width="80"></td><td style="vertical-align:top; padding-left:15px; line-height:1.0; width:100%;"><strong>{nazwa}</strong><br>ul. {ulica}<br>tel: {telefon} | email: {email}<br>NIP: {nip}<br>Godziny otwarcia: {godziny}</td></tr></table>""").format(
                        logo=config.DST_LOGO_FILE, nazwa=firma[1], ulica=firma[2], telefon=firma[3], email=firma[4], nip=firma[5] or "", godziny=firma[6] or "")
                    html = html.replace("<body>", f"<body>{firma_html}")
            except: pass

            d = self.sample_data
            base64_kod = generuj_kod_zlecenia_base64_maly(d["id"], d["data"], None)

            replacements = {
                "{ID}": d["id"], "{DATA}": d["data"], "{IMIE}": d["imie"],
                "{TELEFON}": d["telefon"], "{SPRZET}": d["sprzet"], "{NR_SER}": d["sn"],
                "{OPIS}": d["opis"], "{UWAGI}": d["uwagi"], "{STATUS}": d["status"],
                "{EMAIL_CLIENT}": d["email"], "{NAPRAWA}": d["naprawa"],
                "{KOSZT_CZESCI}": d["koszt_czesci"].replace(" zł", ""),
                "{KOSZT_USLUGI}": d["koszt_uslugi"].replace(" zł", ""),
                "{KOSZT_SUMA}": d["koszt_suma"].replace(" zł", ""),
                "{ROK}": d["rok"], "{IDBAR}": f"{base64_kod}"
            }
            for key, val in replacements.items(): html = html.replace(key, str(val))

            preview = QPrintPreviewDialog(printer, self)
            preview.setWindowTitle(_("Podgląd HTML - Prosty wydruk"))
            preview.setWindowFlags(preview.windowFlags() | Qt.WindowMaximizeButtonHint)
            preview.resize(1000, 800)

            def render_html(p):
                """Realizuje logikę operacji render html w klasie VisualEditor."""
                doc = QTextDocument()
                doc.setHtml(html)
                doc.print_(p)

            preview.paintRequested.connect(render_html)
            preview.exec()

        else:
            if self.current_template == "zlecenie": printer.setPageOrientation(QPageLayout.Landscape)
            else: printer.setPageOrientation(QPageLayout.Portrait)

            current_layout = {}
            for key, item in self.items.items(): current_layout[key] = item.data

            preview = QPrintPreviewDialog(printer, self)
            preview.setWindowTitle(_("Podgląd Wizualny"))
            preview.setWindowFlags(preview.windowFlags() | Qt.WindowMaximizeButtonHint)
            preview.resize(1000, 800)
            preview.paintRequested.connect(lambda p: _render_page(p, current_layout, self.sample_data, self.current_template, self.logo_pixmap))
            preview.exec()

    def update_ui_state(self):
        """Aktualizuje stan danych lub interfejsu."""
        # Ponieważ usunęliśmy ComboBoxy, mode zawsze wynosi "visual"
        mode = "visual"
        is_visual = True # Zawsze True, bo zostawiliśmy tylko ten silnik

        self.view.setEnabled(is_visual)
        self.group_props.setEnabled(is_visual and (self.current_item is not None))
        self.group_vis.setEnabled(is_visual)
        self.overlay_info.setVisible(not is_visual)
        self.overlay_info.resize(self.view.size())

    def change_template(self, text):
        """Przełącza aktywny szablon w edytorze."""
        internal_key = TEMPLATE_MAP.get(text, "zlecenie")
        self.current_template = internal_key
        self.load_scene()
        self.update_ui_state()

    def reset_to_defaults(self):
        """Przywraca domyślny układ i ustawienia."""
        reply = QtWidgets.QMessageBox.question(self, _("Potwierdzenie"), _("Czy przywrócić domyślne położenie elementów?"), QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        if reply == QtWidgets.QMessageBox.Yes:
            self.layout_config = copy.deepcopy(DEFAULT_LAYOUT)
            self.load_scene()
            # Nie zapisujemy automatycznie! Użytkownik musi kliknąć "Zapisz ustawienia"

    def load_scene(self):
        """Ładuje elementy sceny do edytora wizualnego."""
        for item in list(self.items.values()): self.scene.removeItem(item)
        self.items = {}
        self.scene.clear()
        while self.grid_vis.count():
            item = self.grid_vis.takeAt(0)
            if item.widget(): item.widget().deleteLater()

        self.view.resetTransform()
        if self.current_template == "zlecenie":
            w, h = 560, 800
            self.scene.setSceneRect(0, 0, w + 20, h + 20)
            page = QtWidgets.QGraphicsRectItem(0, 0, w, h)
            self.grid_vis.addWidget(QtWidgets.QLabel("<b>Element</b>"), 0, 0)
            self.grid_vis.addWidget(QtWidgets.QLabel("<b>Klient</b>"), 0, 1)
            self.grid_vis.addWidget(QtWidgets.QLabel("<b>Serwis</b>"), 0, 2)
        else:
            w, h = 800, 1140
            self.scene.setSceneRect(0, 0, w + 20, h + 20)
            page = QtWidgets.QGraphicsRectItem(0, 0, w, h)
            self.grid_vis.addWidget(QtWidgets.QLabel("<b>Element</b>"), 0, 0)
            self.grid_vis.addWidget(QtWidgets.QLabel("<b>Widoczność</b>"), 0, 1)
            self.view.scale(0.75, 0.75)

        page.setBrush(Qt.white); page.setPen(QPen(Qt.black, 1)); page.setZValue(-1)
        self.scene.addItem(page)

        data = self.layout_config.get(self.current_template, {})
        def sort_key(k):
            """Realizuje logikę operacji sort key w klasie VisualEditor."""
            try: return list(DEFAULT_LAYOUT[self.current_template].keys()).index(k)
            except: return 999
        sorted_keys = sorted(data.keys(), key=sort_key)

        row = 1
        for key in sorted_keys:
            props = data[key]
            item = ReportItem(key, props, self)
            self.scene.addItem(item)
            self.items[key] = item
            self.grid_vis.addWidget(QtWidgets.QLabel(props.get("label", key)), row, 0)
            if self.current_template == "zlecenie":
                chk_c = QtWidgets.QCheckBox(); chk_c.setChecked(props.get("visible_client", True)); chk_c.stateChanged.connect(lambda s, k=key: self.toggle_vis_split(k, "visible_client", s))
                self.grid_vis.addWidget(chk_c, row, 1)
                chk_s = QtWidgets.QCheckBox(); chk_s.setChecked(props.get("visible_service", True)); chk_s.stateChanged.connect(lambda s, k=key: self.toggle_vis_split(k, "visible_service", s))
                self.grid_vis.addWidget(chk_s, row, 2)
            else:
                chk = QtWidgets.QCheckBox(); chk.setChecked(props.get("visible", True)); chk.stateChanged.connect(lambda s, k=key: self.toggle_vis_simple(k, s))
                self.grid_vis.addWidget(chk, row, 1)
            row += 1
        self.grid_vis.setRowStretch(row, 1)

    def toggle_vis_simple(self, key, state):
        """Przełącza stan wybranej opcji."""
        if key in self.items: self.items[key].data["visible"] = (state == 2)

    def toggle_vis_split(self, key, param, state):
        """Przełącza stan wybranej opcji."""
        if key in self.items: self.items[key].data[param] = (state == 2)

    def update_properties_panel(self, item):
        """Odświeża panel właściwości dla zaznaczonego elementu."""
        self.group_props.setEnabled(True)
        self.spin_font.blockSignals(True); self.chk_bold.blockSignals(True)
        self.chk_border.blockSignals(True); self.spin_border.blockSignals(True)
        self.chk_center.blockSignals(True); self.txt_content.blockSignals(True)

        self.current_item = item
        self.lbl_id.setText(item.data.get("label", item.key))
        self.spin_font.setValue(item.data.get("font_size", 12))
        self.chk_bold.setChecked(item.data.get("bold", False))
        self.chk_border.setChecked(item.data.get("border", False))
        self.spin_border.setValue(item.data.get("border_width", 1))
        self.chk_center.setChecked(item.data.get("align") == "center")

        if "text" in item.data:
            self.txt_content.setEnabled(True)
            self.txt_content.setPlainText(item.data["text"])
        else:
            self.txt_content.setPlainText("")
            self.txt_content.setEnabled(False)

        self.spin_font.blockSignals(False); self.chk_bold.blockSignals(False)
        self.chk_border.blockSignals(False); self.spin_border.blockSignals(False)
        self.chk_center.blockSignals(False); self.txt_content.blockSignals(False)

    def prop_changed(self):
        """Aktualizuje właściwości zaznaczonego elementu po zmianie pola."""
        if not hasattr(self, 'current_item') or not self.current_item: return
        self.current_item.data["font_size"] = self.spin_font.value()
        self.current_item.data["bold"] = self.chk_bold.isChecked()
        self.current_item.data["border"] = self.chk_border.isChecked()
        self.current_item.data["border_width"] = self.spin_border.value()
        self.current_item.data["align"] = "center" if self.chk_center.isChecked() else "left"
        self.current_item.update()

    def text_content_changed(self):
        """Synchronizuje zmianę tekstu z aktualnie edytowanym elementem."""
        if not hasattr(self, 'current_item') or not self.current_item: return
        if "text" in self.current_item.data:
            self.current_item.data["text"] = self.txt_content.toPlainText()
            self.current_item.update()

    def save_all_settings(self):
        """Zapisuje WSZYSTKO: Układ graficzny oraz opcję podglądu."""
        # 1. Zapis konfiguracji układu (JSON)
        if self.current_template not in self.layout_config:
            self.layout_config[self.current_template] = {}

        for key, item in self.items.items():
            self.layout_config[self.current_template][key] = item.data

        try:
            os.makedirs(os.path.dirname(LAYOUT_FILE), exist_ok=True)
            with open(LAYOUT_FILE, "w", encoding="utf-8") as f:
                json.dump(self.layout_config, f, indent=4)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, _("Błąd"), f"Błąd zapisu układu: {e}")
            return

        # 2. Zapis konfiguracji globalnej (INI)
        # Zczytujemy tylko checkbox podglądu, bo on został w UI
        set_preview_mode(self.chk_preview_mode.isChecked())

        # Wymuszamy silnik wizualny w pliku konfiguracyjnym,
        # żeby system wiedział, że od teraz to jest standard.
        set_order_engine("visual")
        set_report_engine("visual")

        QtWidgets.QMessageBox.information(self, _("Sukces"), _("Zapisano wszystkie ustawienia"))

def edytuj_szablon(parent):
    """Realizuje logikę operacji edytuj szablon."""
    editor = VisualEditor(parent)
    editor.exec()

# ============================================================================
# DISPATCHER
# ============================================================================
def drukuj_zlecenie_html(zlecenie_input, parent_window, tryb=None, c=None):
    """Przygotowuje i wykonuje wydruk (Tylko silnik wizualny)."""
    zlecenie = zlecenie_input
    try:
        # Pobieranie pełnych danych z bazy, jeśli przekazano tylko ID (krótka krotka)
        if len(zlecenie) < 8:
             zlecenie_id = zlecenie[0]
             cursor_to_use = c
             should_close = False
             if cursor_to_use is None:
                 conn_full = sqlite3.connect(config.DB_FILE)
                 cursor_to_use = conn_full.cursor()
                 should_close = True
             full_row = cursor_to_use.execute("SELECT * FROM zlecenia WHERE id=?", (zlecenie_id,)).fetchone()
             if full_row: zlecenie = full_row
             if should_close: conn_full.close()
    except Exception as e:
        print(f"Błąd dispatchera: {e}")

    # Logika rozpoznawania czy to zlecenie (przyjęcie) czy raport (wydanie)
    is_report = (tryb == "raport")
    status = zlecenie[7] if len(zlecenie) > 7 else ""
    if tryb is None and status in ("Ukończone", "Zakończone", "Completed", _("Ukończone")):
        is_report = True

    # USUNIĘTO: Sprawdzanie get_order_engine / get_report_engine
    # WYMUSZONO: Zawsze silnik wizualny
    _drukuj_visual_nowy(zlecenie, parent_window, tryb, c)

# ============================================================================
# HTML ENGINE
# ============================================================================
def generuj_kod_zlecenia_base64_maly(id_zlecenia, data_zlecenia=None, val_nr_roczny=None):
    """Generuje dane wynikowe lub zasób pomocniczy."""
    if not data_zlecenia: data_zlecenia = datetime.date.today().strftime('%Y-%m-%d')
    try: dt = datetime.datetime.strptime(data_zlecenia, '%Y-%m-%d')
    except: dt = datetime.datetime.now()
    kod_text = formatuj_numer_zlecenia(id_zlecenia, data_zlecenia, val_nr_roczny)

    # Parametry rozmiaru
    desired_width_mm, desired_height_mm, dpi = 10, 1, 300
    pixels_per_mm = dpi / 25.4
    desired_width_px = int(desired_width_mm * pixels_per_mm)
    desired_height_px = int(desired_height_mm * pixels_per_mm)

    if not BARCODE_AVAILABLE:
        # Generowanie pustego obrazka PNG o określonych wymiarach
        blank = QImage(desired_width_px, desired_height_px, QImage.Format_ARGB32)
        blank.fill(Qt.white)

        # POPRAWKA: Użycie QBuffer do zapisu QImage zamiast surowego BytesIO
        ba = QtCore.QByteArray()
        buffer = QtCore.QBuffer(ba)
        buffer.open(QtCore.QIODevice.WriteOnly)
        blank.save(buffer, "PNG")

        return f'<img src="data:image/png;base64,{base64.b64encode(ba.data()).decode("utf-8")}">'

    num_modules = len(kod_text) * 10
    module_width = max(desired_width_px / num_modules / dpi * 25.4, 0.1)

    buffer = BytesIO()
    Code39 = barcode.get('code39')
    bc_instance = Code39(kod_text, writer=ImageWriter(), add_checksum=False)
    bc_instance.write(buffer, options={"module_width": module_width, "module_height": desired_height_mm, "font_size": 0, "quiet_zone": 1.0, "dpi": dpi})
    buffer.seek(0)
    return f'<img src="data:image/png;base64,{base64.b64encode(buffer.getvalue()).decode("utf-8")}">'

def _drukuj_html_stary(zlecenie, parent_window, tryb=None, c=None):
    """Realizuje logikę operacji drukuj html stary."""
    try:
        if len(zlecenie) < 8:
             conn = sqlite3.connect(config.DB_FILE); cur = conn.cursor()
             full_row = cur.execute("SELECT * FROM zlecenia WHERE id=?", (zlecenie[0],)).fetchone()
             if full_row: zlecenie = full_row
             conn.close()
    except: pass

    template_file = config.WZORZEC_HTML
    if tryb == "raport" and config.WZORZEC_RAPORT and os.path.exists(config.WZORZEC_RAPORT): template_file = config.WZORZEC_RAPORT
    elif tryb is None and len(zlecenie) > 7 and zlecenie[7] in ("Ukończone",) and config.WZORZEC_RAPORT and os.path.exists(config.WZORZEC_RAPORT): template_file = config.WZORZEC_RAPORT

    if not os.path.exists(template_file): QtWidgets.QMessageBox.critical(parent_window, _("Błąd"), _("Brak szablonu HTML!")); return
    with open(template_file, "r", encoding="utf-8") as f: html = f.read()

    conn_temp = sqlite3.connect(config.DB_FILE)
    firma = conn_temp.cursor().execute("SELECT * FROM firma LIMIT 1").fetchone()
    conn_temp.close()

    raw_date = zlecenie[8] if len(zlecenie) > 8 else ""
    val_nr_roczny = zlecenie[14] if len(zlecenie) >= 15 else None
    base64_kod = generuj_kod_zlecenia_base64_maly(zlecenie[0], raw_date, val_nr_roczny)

    if firma:
        firma_html = _("""<table style="width:100%; border:none; margin-bottom:5px;"><tr><td style="width:100px; vertical-align:top;"><img src="file:///{logo}" width="80"></td><td style="vertical-align:top; padding-left:15px; line-height:1.0; width:100%;"><strong>{nazwa}</strong><br>ul. {ulica}<br>tel: {telefon} | email: {email}<br>NIP: {nip}<br>Godziny otwarcia: {godziny}</td></tr></table>""").format(
            logo=config.DST_LOGO_FILE, nazwa=firma[1], ulica=firma[2], telefon=firma[3], email=firma[4], nip=firma[5] or "", godziny=firma[6] or "")
        html = html.replace("<body>", f"<body>{firma_html}")

    try: k_cz = float(zlecenie[11] or 0); k_us = float(zlecenie[12] or 0)
    except: k_cz=0; k_us=0

    id_formatted = formatuj_numer_zlecenia(zlecenie[0], raw_date, val_nr_roczny)

    replacements = {
        "{ID}": id_formatted, "{DATA}": raw_date, "{IMIE}": zlecenie[1],
        "{TELEFON}": zlecenie[2], "{SPRZET}": zlecenie[3], "{NR_SER}": zlecenie[4], "{OPIS}": zlecenie[5], "{UWAGI}": zlecenie[6] or "", "{STATUS}": zlecenie[7],
        "{EMAIL_CLIENT}": zlecenie[9] or "", "{NAPRAWA}": zlecenie[10] or "", "{KOSZT_CZESCI}": f"{k_cz:.2f}", "{KOSZT_USLUGI}": f"{k_us:.2f}",
        "{KOSZT_SUMA}": f"{round(k_cz+k_us, 2):.2f}", "{ROK}": f"{datetime.date.today().year}", "{IDBAR}": f"{base64_kod}"
    }
    if firma: replacements.update({"{NAZWA_FIRMY}": firma[1], "{ADRES_FIRMY}": firma[2], "{TELEFON_FIRMY}": firma[3], "{EMAIL_FIRMY}": firma[4], "{NIP_FIRMY}": firma[5], "{GODZINY_OTWARCIA}": firma[6] or "", "{LOGO_FILE}": config.DST_LOGO_FILE})
    for key, val in replacements.items(): html = html.replace(key, str(val))

    printer = QPrinter(QPrinter.HighResolution); printer.setPageSize(QPageSize(QPageSize.PageSizeId.A4)); printer.setFullPage(True)

    # --- ZABEZPIECZENIE NAZWY PLIKU DLA PDF ---
    safe_name = id_formatted.replace("/", "_").replace("\\", "_")
    #printer.setOutputFileName(f"{safe_name}.pdf")
    printer.setDocName(id_formatted)
    def print_doc(printer_obj):
        """Realizuje logikę operacji print doc."""
        doc = QTextDocument()
        doc.setHtml(html)
        doc.print_(printer_obj)

    if get_preview_mode():
        preview = QPrintPreviewDialog(printer, parent_window); preview.setWindowTitle(_(f"Podgląd")); preview.resize(1000, 800)
        preview.paintRequested.connect(print_doc); preview.exec()
    else:
        try:
            if QPrintDialog(printer, parent_window).exec() == QPrintDialog.Accepted: print_doc(printer)
        except: pass

# ============================================================================
# VISUAL ENGINE
# ============================================================================
def _generuj_kod_kreskowy_image(text):
    """Realizuje logikę operacji generuj kod kreskowy image."""
    if not BARCODE_AVAILABLE:
        # Tworzenie pustego, białego obrazu o domyślnych proporcjach kodu kreskowego
        img = QtGui.QImage(600, 200, QtGui.QImage.Format_ARGB32)
        img.fill(Qt.white)
        return img

    writer = ImageWriter(); buffer = BytesIO(); Code39 = barcode.get('code39')
    bc_instance = Code39(text, writer=writer, add_checksum=False)
    bc_instance.write(buffer, options={"dpi": 300, "module_height": 10.0, "font_size": 0, "quiet_zone": 1.0})
    buffer.seek(0); img = QtGui.QImage(); img.loadFromData(buffer.getvalue()); return img

def _render_page(printer, layout_data, data_dict, template_key, logo_pixmap):
    """Realizuje logikę operacji render page."""
    painter = QPainter(printer)
    page_rect = printer.pageRect(QPrinter.DevicePixel)
    printer_width = page_rect.width() if page_rect.width() > 0 else 4800
    base_width = 794.0 if template_key == "raport" else 1123.0
    scale = printer_width / base_width

    painter.save(); painter.scale(scale, scale)
    loop_count = 2 if template_key == "zlecenie" else 1

    for i in range(loop_count):
        painter.save()
        if i == 1: painter.translate(561.5, 0)

        for key, props in layout_data.items():
            if template_key == "zlecenie":
                if (i == 0 and not props.get("visible_client", True)) or (i == 1 and not props.get("visible_service", True)): continue
            elif not props.get("visible", True): continue

            rect = QRectF(props.get("x", 0), props.get("y", 0), props.get("w", 100), props.get("h", 50))
            if props.get("bg"): painter.fillRect(rect, QColor(240, 240, 240))
            if props.get("border"): painter.setPen(QPen(Qt.black, props.get("border_width", 1))); painter.drawRect(rect)
            else: painter.setPen(Qt.NoPen)

            type_ = props.get("type", "text")
            if type_ == "image" and logo_pixmap:
                scaled = logo_pixmap.scaled(QSize(int(rect.width()), int(rect.height())), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                painter.drawPixmap(int(rect.x() + (rect.width()-scaled.width())/2), int(rect.y() + (rect.height()-scaled.height())/2), scaled)
            elif type_ == "barcode":
                try: painter.drawImage(rect, _generuj_kod_kreskowy_image(data_dict.get("id", "ERROR")))
                except: painter.setPen(Qt.black); painter.drawText(rect, Qt.AlignCenter, "BARCODE ERROR")
            else:
                painter.setPen(Qt.black)
                font = QFont("Arial"); font.setPixelSize(props.get("font_size", 12)); font.setBold(props.get("bold", False)); painter.setFont(font)
                align = Qt.AlignCenter if props.get("align") == "center" else (Qt.AlignRight if props.get("align") == "right" else Qt.AlignLeft | Qt.AlignTop)

                text = ""
                # KLUCZOWA POPRAWKA: Dopasowanie nagłówka do szablonu raportu
                if key == "header":
                    text = f"RAPORT Z NAPRAWY - {data_dict['id']}" if template_key == "raport" else f"POTWIERDZENIE PRZYJĘCIA\nNr: {data_dict['id']}"
                elif key == "firma": text = data_dict.get('firma_full', "Dane Firmy")
                elif key == "klient": text = f"KLIENT:\n{data_dict['imie']}\nTel: {data_dict['telefon']}\nEmail: {data_dict['email']}"
                elif key == "urzadzenie": text = f"URZĄDZENIE: {data_dict['sprzet']}\nSN: {data_dict['sn']}"
                elif key == "opis": text = f"USTERKA:\n{data_dict['opis']}"
                elif key == "uwagi": text = f"UWAGI:\n{data_dict['uwagi']}"
                elif key == "naprawa": text = f"WYKONANE CZYNNOŚCI:\n{data_dict['naprawa']}"
                elif key == "koszty": text = f"Części: {data_dict['koszt_czesci']}\nUsługa: {data_dict['koszt_uslugi']}\nRAZEM: {data_dict['koszt_suma']}"
                elif key == "rodo": text = props.get("text", DEFAULT_RODO_TEXT)
                elif key == "stopka": text = f"Wydrukowano z SerwisApp © {data_dict['rok']}"
                elif key == "info": text = f"Data: {data_dict['data']}\nKlient: {data_dict['imie']}\nSprzęt: {data_dict['sprzet']}"
                elif key == "podpisy": text = _get_podpis_text(template_key, i if template_key == "zlecenie" else None)

                tr = QRectF(rect)
                if props.get("border"): offset = 4 + (props.get("border_width", 1)/2); tr.adjust(offset, offset, -offset, -offset)
                painter.drawText(tr, align | Qt.TextWordWrap, text)

        if template_key == "zlecenie":
            painter.setPen(Qt.gray); font = QFont("Arial"); font.setPixelSize(8); painter.setFont(font)
            painter.drawText(QRectF(20, 5, 500, 20), Qt.AlignRight, "DLA KLIENTA (ORYGINAŁ)" if i == 0 else "DLA SERWISU (KOPIA)")
        painter.restore()

    if template_key == "zlecenie":
        painter.setPen(QPen(Qt.black, 1, Qt.DashLine)); painter.drawLine(QPointF(561.5, 20), QPointF(561.5, 780))
    painter.restore(); painter.end()

def _drukuj_visual_nowy(zlecenie, parent_window, tryb=None, c=None):
    """Realizuje logikę operacji drukuj visual nowy."""
    try:
        if len(zlecenie) < 8:
             conn = sqlite3.connect(config.DB_FILE); cur = conn.cursor()
             full_row = cur.execute("SELECT * FROM zlecenia WHERE id=?", (zlecenie[0],)).fetchone()
             if full_row: zlecenie = full_row
             conn.close()
    except: pass

    status = zlecenie[7] if len(zlecenie) > 7 else ""
    template_key = "zlecenie" if (tryb == "wzorzec" or (tryb is None and status not in ("Ukończone", "Zakończone", "Completed", _("Ukończone")))) else "raport"
    if tryb == "raport": template_key = "raport"

    layout_data = copy.deepcopy(DEFAULT_LAYOUT.get(template_key, {}))
    if os.path.exists(LAYOUT_FILE):
        try:
            with open(LAYOUT_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f); layout_data.update(saved.get(template_key, {}))
        except: pass

    conn = sqlite3.connect(config.DB_FILE); f = conn.cursor().execute("SELECT * FROM firma LIMIT 1").fetchone(); conn.close()

    raw_date = zlecenie[8] if len(zlecenie) > 8 else ""
    val_nr_roczny = zlecenie[14] if len(zlecenie) >= 15 else None
    id_formatted = formatuj_numer_zlecenia(zlecenie[0], raw_date, val_nr_roczny)

    d = {"id": id_formatted, "data": raw_date, "imie": zlecenie[1], "telefon": zlecenie[2], "sprzet": zlecenie[3], "sn": zlecenie[4], "opis": zlecenie[5], "uwagi": zlecenie[6] or "", "status": zlecenie[7], "email": zlecenie[9] or "", "naprawa": zlecenie[10] or "", "rok": str(datetime.date.today().year)}
    try: k_cz = float(zlecenie[11] or 0); k_us = float(zlecenie[12] or 0)
    except: k_cz=0; k_us=0
    d["koszt_czesci"] = f"{k_cz:.2f} zł"; d["koszt_uslugi"] = f"{k_us:.2f} zł"; d["koszt_suma"] = f"{k_cz+k_us:.2f} zł"

    # POPRAWKA: Upewnienie się, że dane firmy trafiają do słownika danych dla renderera
    d["firma_full"] = ""
    if f: d["firma_full"] = f"{f[1]}\n{f[2]}\nTel: {f[3]} | Email: {f[4]}\nNIP: {f[5]}" + (f"\n{f[6]}" if f[6] else "")
    else: d["firma_full"] = "Dane Firmy nie zostały ustawione"

    logo = None
    if os.path.exists(config.DST_LOGO_FILE): logo = QPixmap(config.DST_LOGO_FILE)

    printer = QPrinter(QPrinter.HighResolution); printer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
    printer.setPageOrientation(QPageLayout.Landscape if template_key == "zlecenie" else QPageLayout.Portrait)
    printer.setDocName(id_formatted)

    if get_preview_mode():
        preview = QPrintPreviewDialog(printer, parent_window); preview.setWindowTitle(_(f"Podgląd - {id_formatted}")); preview.resize(1000, 800)
        preview.paintRequested.connect(lambda p: _render_page(p, layout_data, d, template_key, logo))
        preview.exec()
    else:
        if QPrintDialog(printer, parent_window).exec() == QPrintDialog.Accepted: _render_page(printer, layout_data, d, template_key, logo)
