import html
import re
from PySide6 import QtCore, QtGui
from PySide6.QtWidgets import QSizePolicy, QMenu, QApplication
from modules.utils import formatuj_numer_zlecenia

# Zabezpieczenie na wypadek uruchamiania modułu niezależnie
try:
    _("Test")
except NameError:
    def _(text):
        """Zwraca tekst bez tłumaczenia, gdy mechanizm i18n nie jest aktywny."""
        return text

# --- OBSŁUGA MENU KONTEKSTOWEGO ---
def obsluga_menu_kontekstowego(pos, label):
    """Obsługuje wskazaną akcję interfejsu."""
    menu = QMenu(label)

    if label.hasSelectedText():
        action_copy = menu.addAction(_("Kopiuj zaznaczenie"))
        action_copy.triggered.connect(lambda: QApplication.clipboard().setText(label.selectedText()))
        menu.addSeparator()

    field_data = label.property("field_data")

    if field_data:
        header = menu.addAction(_("Skopiuj całe pole:"))
        header.setEnabled(False)

        def copy_helper(text):
            """Kopiuje dane do schowka lub nowej struktury."""
            QApplication.clipboard().setText(text)

        options_map = {
            'opis': _("Opis usterki"),
            'uwagi': _("Uwagi"),
            'naprawa': _("Czynności serwisu"),
            'telefon': _("Numer telefonu"),
            'imie': _("Imię i Nazwisko"),
            'nr_zlecenia': _("Numer zlecenia"),
            'sn': _("Numer Seryjny (S/N)"),
            'sprzet': _("Model urządzenia"),
            # Statusy
            'akcesoria_info': _("Treść Akcesoria"),
            'pilne_status': _("Status Pilne"),
            'gwarancja_status': _("Status Gwarancja"),
            'rekojmia_status': _("Status Rękojmia")
        }

        for key, label_text in options_map.items():
            if key in field_data and field_data[key]:
                if "status" in key and field_data[key] == "NIE":
                    continue
                action = menu.addAction(label_text)
                action.triggered.connect(lambda checked=False, k=key: copy_helper(field_data[k]))

    if not menu.isEmpty():
        menu.exec(label.mapToGlobal(pos))

# --------------------------------------------------

def pokaz_szczegoly_w_labelach(ui, c, selected, deselected):
    """
    Wyświetla szczegóły zlecenia w 4 KOLUMNACH.
    WERSJA STABILNA - BEZ DYNAMICZNEGO SCROLLA (FIX SIGSEGV)
    """

    # Styl dla Labeli
    LABEL_STYLE = """
        QLabel {
            border: 1px solid gray;
            border-radius: 6px;
            padding: 6px;
            background-color: transparent;
        }
        QLabel:hover {
            border: 1px solid #e67e22;
        }
    """

    COLOR_ACCENT = "#e67e22"
    COLOR_URGENT = "#e74c3c"

    all_labels = [ui.label_lewy, ui.label_srodek, ui.label_prawy]
    if hasattr(ui, 'label_dodatki'):
        all_labels.append(ui.label_dodatki)

    # --- RESET ---
    indexes = ui.tableView.selectionModel().selectedRows()
    if not indexes:
        for label in all_labels:
            label.setText("")
            label.setToolTip("")
            label.setStyleSheet(LABEL_STYLE)
            label.setProperty("field_data", {})
        return

    # --- DANE ---
    index = indexes[0]
    model = ui.tableView.model()
    item = model.itemFromIndex(index.sibling(index.row(), 0))
    real_id = item.data(QtCore.Qt.UserRole)

    if real_id:
        id_num = int(real_id)
    else:
        id_raw = index.sibling(index.row(), 0).data()
        try:
            id_num = int(str(id_raw).split("/")[0])
        except (ValueError, IndexError):
            return

    z = c.execute("SELECT * FROM zlecenia WHERE id=?", (id_num,)).fetchone()
    if not z:
        return

    colnames = [d[0] for d in c.description]
    nr_roczny_val = z[colnames.index("nr_roczny")] if "nr_roczny" in colnames else None

    # --- PARSOWANIE DANYCH ---
    opis_raw = z[5] or ""
    uwagi_raw = z[6] or ""

    # 1. AKCESORIA
    acc_label = _("Akcesoria:")
    acc_pattern = r"\|\s*" + re.escape(acc_label) + r"\s*(.*)"
    match_acc = re.search(acc_pattern, opis_raw) if opis_raw else None

    is_akcesoria = False
    akcesoria_text = ""
    opis_clean = opis_raw

    if match_acc:
        is_akcesoria = True
        akcesoria_text = match_acc.group(1).strip()
        opis_clean = re.sub(acc_pattern, "", opis_raw).strip()
        opis_clean = opis_clean.rstrip("|").strip()

    # 2. STATUSY
    flag_gwarancja = _("Na gwarancji")
    flag_rkj = _("Rękojmia")
    flag_pilne_txt = _("Pilne – wysoki priorytet")

    is_gwarancja = flag_gwarancja in uwagi_raw
    is_rkj = flag_rkj in uwagi_raw

    is_pilne = False
    if "pilne" in colnames and z[colnames.index("pilne")] == 1:
        is_pilne = True
    elif flag_pilne_txt in uwagi_raw:
        is_pilne = True

    uwagi_clean = uwagi_raw
    for flag in [flag_gwarancja, flag_rkj, flag_pilne_txt]:
        uwagi_clean = uwagi_clean.replace(" | " + flag, "").replace(flag, "")
    uwagi_clean = uwagi_clean.strip().strip("|").strip()

    # --- HELPERY DO HTML ---
    def prepare_text(val, max_len=None):
        """Realizuje logikę operacji prepare text."""
        full_text = str(val) if val is not None else ""
        clean_text = full_text.replace('\n', ' ').replace('\r', '')
        display_text = clean_text
        if max_len and len(clean_text) > max_len:
            display_text = clean_text[:max_len].strip() + "..."
        return html.escape(display_text), full_text

    def format_status(is_true, urgent_style=False):
        """Formatuje dane do oczekiwanej postaci."""
        if is_true:
            if urgent_style:
                return f"<span style='color:{COLOR_URGENT}; font-weight:bold;'>TAK</span>"
            return "<b>TAK</b>"
        else:
            return "<span style='opacity:0.5;'>NIE</span>"

    # --- GENEROWANIE HTML STATUSÓW ---
    html_pilne = format_status(is_pilne, urgent_style=True)
    html_gwarancja = format_status(is_gwarancja)
    html_rkj = format_status(is_rkj)

    html_akcesoria = format_status(is_akcesoria)
    if is_akcesoria and akcesoria_text:
        acc_short, _trash = prepare_text(akcesoria_text, 50)
        html_akcesoria += f"<div style='font-size:8pt; color:#666; margin-top:2px; line-height:1.1;'>{acc_short}</div>"

    # --- TREŚĆ GŁÓWNA ---
    # Zwiększamy limit znaków, bo nie mamy scrolla
    limit_srodek = 105

    opis_html, opis_full = prepare_text(opis_clean, limit_srodek)
    uwagi_html, uwagi_full = prepare_text(uwagi_clean, limit_srodek)
    naprawa_html, naprawa_full = prepare_text(z[10] if len(z) > 10 else "", limit_srodek)

    imie_html, imie_full = prepare_text(z[1], 35)
    tel_html, tel_full = prepare_text(z[2], 20)
    data_html, _trash = prepare_text(z[8])
    nr_zlecenia_str = formatuj_numer_zlecenia(z[0], z[8], nr_roczny_val)
    sprzet_html, sprzet_full = prepare_text(z[3], 30)
    sn_html, sn_full = prepare_text(z[4], 25)

    koszt_cz = z[11] if len(z) > 11 and z[11] is not None else 0.0
    koszt_us = z[12] if len(z) > 12 and z[12] is not None else 0.0
    suma = koszt_cz + koszt_us

    wystawil_val = ""
    if "wystawil" in colnames:
        wystawil_val = z[colnames.index("wystawil")]
    wystawil_html, _trash = prepare_text(wystawil_val, 25)

    # --- HTML CONTENT ---
    html_lewy = f"""
    <h4 style='margin:0; padding:0; text-transform:uppercase;'>{_("DANE KLIENTA")}</h4>
    <table width="100%" cellspacing="0" cellpadding="0">
        <tr><td style='opacity:0.7;' width="50"><b>{_("Imię:")}</b></td><td>{imie_html}</td></tr>
        <tr><td style='opacity:0.7;'><b>{_("Tel:")}</b></td><td>{tel_html}</td></tr>
    </table>
    <hr style='border: 0; border-top: 1px solid gray; margin: 4px 0; opacity: 0.3;'>
    <h4 style='margin:0; padding:0; text-transform:uppercase;'>{_("ZLECENIE")}</h4>
    <table width="100%" cellspacing="0" cellpadding="0">
        <tr><td style='opacity:0.7;' width="50"><b>{_("Data:")}</b></td><td>{data_html}</td></tr>
        <tr><td style='opacity:0.7;'><b>{_("Nr:")}</b></td><td><span style='font-size:12pt; color:{COLOR_ACCENT}; font-weight:bold;'>{nr_zlecenia_str}</span></td></tr>
        <tr><td style='opacity:0.7;'>{_("Wystawił:")}</td><td align='right' style='font-size:9pt; color:#555;'>{wystawil_html}</td></tr>
    </table>
    """

    html_srodek = f"""
    <div style='margin-bottom:4px;'><b style='opacity:0.7; font-size:9pt'>{_("OPIS:")}</b><br>{opis_html}</div>
    <div style='margin-bottom:4px;'><b style='opacity:0.7; font-size:9pt'>{_("UWAGI:")}</b><br>{uwagi_html if uwagi_html else "---"}</div>
    <hr style='border: 0; border-top: 1px solid gray; margin: 4px 0; opacity: 0.3;'>
    <div><b style='opacity:0.7; font-size:9pt'>{_("Serwis:")}</b><br>{naprawa_html if naprawa_html else "---"}</div>
    """

    html_prawy = f"""
    <h4 style='margin:0; padding:0; text-transform:uppercase;'>{_("SPRZĘT")}</h4>
    <table width="100%" cellspacing="0" cellpadding="0">
        <tr><td style='opacity:0.7;' width="50"><b>{_("Model:")}</b></td><td>{sprzet_html}</td></tr>
        <tr><td style='opacity:0.7;'><b>{_("S/N:")}</b></td><td>{sn_html if sn_html else "---"}</td></tr>
    </table>
    <hr style='border: 0; border-top: 1px solid gray; margin: 4px 0; opacity: 0.3;'>
    <h4 style='margin:0; padding:0; text-transform:uppercase;'>{_("KOSZTY")}</h4>
    <table width="100%" cellspacing="0" cellpadding="0">
        <tr><td style='opacity:0.7;'>{_("Usługa:")}</td><td align='right'>{koszt_us:.2f} zł</td></tr>
        <tr><td style='opacity:0.7;'>{_("Części:")}</td><td align='right'>{koszt_cz:.2f} zł</td></tr>
        <tr><td colspan='2' style='padding-top:3px;' align='center'>
            <span style='font-size:14pt; font-weight:bold; color:{COLOR_ACCENT};'>{suma:.2f} PLN</span>
        </td></tr>
    </table>
    """

    html_dodatki = f"""
    <h4 style='margin:0; padding:0; text-transform:uppercase;'>{_("OPCJE")}</h4>
    <hr style='border: 0; border-top: 1px solid gray; margin: 4px 0; opacity: 0.3;'>
    <table width="100%" cellspacing="0" cellpadding="2">
        <tr><td style='opacity:0.7; vertical-align:top;'>{_("Pilne:")}</td><td align='right' style='vertical-align:top;'>{html_pilne}</td></tr>
        <tr><td style='opacity:0.7; vertical-align:top;'>{_("Gwarancja:")}</td><td align='right' style='vertical-align:top;'>{html_gwarancja}</td></tr>
        <tr><td style='opacity:0.7; vertical-align:top;'>{_("Rękojmia:")}</td><td align='right' style='vertical-align:top;'>{html_rkj}</td></tr>
        <tr><td style='opacity:0.7; vertical-align:top;'>{_("Akcesoria:")}</td><td align='right' style='vertical-align:top;'>{html_akcesoria}</td></tr>
    </table>
    """

    data_lewy = {'imie': imie_full, 'telefon': tel_full, 'nr_zlecenia': nr_zlecenia_str}
    data_srodek = {'opis': opis_full, 'uwagi': uwagi_full, 'naprawa': naprawa_full}
    data_prawy = {'sprzet': sprzet_full, 'sn': sn_full}
    data_dodatki = {
        'pilne_status': "TAK" if is_pilne else "NIE",
        'gwarancja_status': "TAK" if is_gwarancja else "NIE",
        'rekojmia_status': "TAK" if is_rkj else "NIE",
        'akcesoria_info': akcesoria_text if is_akcesoria else "NIE"
    }

    tooltip_lewy = f"Klient: {imie_full}\nTelefon: {tel_full}\nNr: {nr_zlecenia_str}"
    tooltip_srodek = f"Opis: {opis_full}\nUwagi: {uwagi_full}\nCzynności: {naprawa_full}"
    tooltip_prawy = f"Sprzęt: {sprzet_full}\nSN: {sn_full}\nKoszt: {suma:.2f}"
    acc_tooltip_str = akcesoria_text if is_akcesoria else "BRAK"
    tooltip_dodatki = f"Pilne: {'TAK' if is_pilne else 'NIE'}\nGwarancja: {'TAK' if is_gwarancja else 'NIE'}\nRękojmia: {'TAK' if is_rkj else 'NIE'}\nAkcesoria: {acc_tooltip_str}"

    labels_config = [
        (ui.label_lewy, html_lewy, tooltip_lewy, data_lewy, 5),
        (ui.label_srodek, html_srodek, tooltip_srodek, data_srodek, 10),
        (ui.label_prawy, html_prawy, tooltip_prawy, data_prawy, 8)
    ]

    if hasattr(ui, 'label_dodatki'):
        labels_config.append(
            (ui.label_dodatki, html_dodatki, tooltip_dodatki, data_dodatki, 5)
        )

    # --- PĘTLA APLIKUJĄCA USTAWIENIA (Czysta, bez podmiany widgetów) ---
    for label, html_content, tooltip_text, field_data, stretch_factor in labels_config:

        # Przywracamy podstawowy styl (upewniamy się że nie ma śmieci po starym scrollu)
        label.setStyleSheet(LABEL_STYLE)
        label.setMinimumHeight(200)
        label.setMaximumHeight(270)

        sizePolicy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(stretch_factor)
        label.setSizePolicy(sizePolicy)

        font = QtGui.QFont()
        font.setPointSize(10)
        label.setFont(font)
        label.setWordWrap(True)
        label.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignTop)

        label.setText(html_content)
        label.setToolTip(tooltip_text)
        label.setProperty("field_data", field_data)

        # Menu kontekstowe
        label.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        if label.property("menu_connected"):
            try:
                label.customContextMenuRequested.disconnect()
            except (RuntimeError, TypeError):
                pass

        label.customContextMenuRequested.connect(lambda pos, l=label: obsluga_menu_kontekstowego(pos, l))
        label.setProperty("menu_connected", True)

        label.setTextInteractionFlags(
            QtCore.Qt.TextInteractionFlag.TextSelectableByMouse |
            QtCore.Qt.TextInteractionFlag.TextSelectableByKeyboard
        )
