import sqlite3
import datetime
import re
from PySide6 import QtWidgets, QtCore
from modules.odswiez_tabele import odswiez_tabele
from PySide6.QtWidgets import QCompleter
from PySide6.QtCore import QStringListModel
from modules.utils import formatuj_numer_zlecenia
from modules import password_protection

# Zabezpieczenie dla funkcji tłumaczeń _()
try:
    _("Test")
except NameError:
    def _(text):
        """Zwraca tekst bez tłumaczenia, gdy mechanizm i18n nie jest aktywny."""
        return text

def _get_filters_from_ui(ui):
    """Realizuje logikę operacji get filters from ui."""
    status_filter = None
    if hasattr(ui, "radioButton_new") and ui.radioButton_new.isChecked():
        status_filter = "Przyjęte"
    elif hasattr(ui, "radioButton_end") and ui.radioButton_end.isChecked():
        status_filter = "Ukończone"
    else:
        status_filter = None

    search_term = None
    if hasattr(ui, "lineEdit_szukajka"):
        st = ui.lineEdit_szukajka.text().strip()
        if st:
            search_term = st

    return status_filter, search_term

def ensure_pilne_column(cursor):
    """Zapewnia istnienie wymaganej struktury lub ustawienia."""
    cols = [r[1] for r in cursor.execute("PRAGMA table_info('zlecenia')").fetchall()]

    if "pilne" not in cols:
        try:
            cursor.execute("ALTER TABLE zlecenia ADD COLUMN pilne INTEGER DEFAULT 0")
        except Exception:
            pass

    if "nr_roczny" not in cols:
        try:
            cursor.execute("ALTER TABLE zlecenia ADD COLUMN nr_roczny INTEGER DEFAULT NULL")
        except Exception:
            pass

    # Dodajemy też 'wystawil' tutaj dla pewności
    if "wystawil" not in cols:
        try:
            cursor.execute("ALTER TABLE zlecenia ADD COLUMN wystawil TEXT")
        except Exception:
            pass

def pobierz_nastepny_numer_roczny(cursor):
    """Pobiera i zwraca potrzebne dane."""
    teraz = datetime.date.today()
    rok_str = str(teraz.year)
    try:
        query = "SELECT MAX(nr_roczny) FROM zlecenia WHERE strftime('%Y', data_zlecenia) = ?"
        cursor.execute(query, (rok_str,))
        wynik = cursor.fetchone()
        max_nr = wynik[0] if wynik else None
        if max_nr is None:
            return 1
        else:
            return max_nr + 1
    except Exception:
        return 1

def dodaj_zlecenie(conn: sqlite3.Connection, cursor: sqlite3.Cursor, model, ui=None, parent=None, prefill=None):
    """Realizuje logikę operacji dodaj zlecenie."""
    try:
        ensure_pilne_column(cursor)
        conn.commit()
    except Exception:
        pass

    dialog = QtWidgets.QDialog(parent)
    dialog.setWindowTitle(_("Dodaj zlecenie"))
    dialog.resize(500, 550)
    layout = QtWidgets.QFormLayout(dialog)

    fields = {}
    form_structure = [
        ("imie", _("Imię i nazwisko")),
        ("telefon", _("Telefon")),
        ("sprzet", _("Sprzęt")),
        ("sn", _("Nr seryjny")),
        ("opis", _("Opis")),
        ("uwagi", _("Uwagi")),
        ("email", _("E-mail"))
    ]

    for key, label_text in form_structure:
        if key in ["opis", "uwagi"]:
            te = QtWidgets.QTextEdit()
            te.setTabChangesFocus(True)
            layout.addRow(label_text, te)
            fields[key] = te
        else:
            le = QtWidgets.QLineEdit()
            layout.addRow(label_text, le)
            fields[key] = le

    checkbox_layout = QtWidgets.QHBoxLayout()
    chk_akcesoria = QtWidgets.QCheckBox(_("Akcesoria"))
    chk_gwarancja = QtWidgets.QCheckBox(_("Gwarancja"))
    chk_rkj = QtWidgets.QCheckBox(_("Rękojmia (NTZU)"))
    chk_pilne = QtWidgets.QCheckBox(_("Pilne"))
    checkbox_layout.addWidget(chk_akcesoria)
    checkbox_layout.addWidget(chk_gwarancja)
    checkbox_layout.addWidget(chk_rkj)
    checkbox_layout.addWidget(chk_pilne)
    layout.addRow(_("Dodatkowe opcje:"), checkbox_layout)

    akcesoria_input = QtWidgets.QLineEdit()
    akcesoria_input.setPlaceholderText(_("Wpisz jakie akcesoria..."))
    akcesoria_input.hide()
    layout.addRow(_("Akcesoria (opis):"), akcesoria_input)

    def toggle_akcesoria():
        """Przełącza stan wybranej opcji."""
        akcesoria_input.setVisible(chk_akcesoria.isChecked())
    chk_akcesoria.stateChanged.connect(lambda _: toggle_akcesoria())

    if prefill:
        trans_map = {
            _("Imię i nazwisko"): "imie",
            _("Telefon"): "telefon",
            _("E-mail"): "email",
            _("Sprzęt"): "sprzet",
            _("Nr seryjny"): "sn"
        }

        for p_key, value in prefill.items():
            target_key = p_key
            if p_key in trans_map:
                target_key = trans_map[p_key]

            if target_key in fields:
                if isinstance(fields[target_key], QtWidgets.QLineEdit):
                    fields[target_key].setText(value or "")
                elif isinstance(fields[target_key], QtWidgets.QTextEdit):
                    fields[target_key].setPlainText(value or "")

        if prefill.get("akcesoria_text"):
            chk_akcesoria.setChecked(True)
            akcesoria_input.setText(prefill.get("akcesoria_text") or "")
            akcesoria_input.show()
        if prefill.get("gwarancja"):
            chk_gwarancja.setChecked(bool(prefill.get("gwarancja")))
        if prefill.get("rkj"):
            chk_rkj.setChecked(bool(prefill.get("rkj")))
        if prefill.get("pilne"):
            chk_pilne.setChecked(bool(prefill.get("pilne")))

    cursor.execute("SELECT imie_nazwisko FROM zlecenia ORDER BY id DESC")
    rows = [r[0] for r in cursor.fetchall() if r[0]]
    klienci_list = []
    seen = set()
    for name in rows:
        name_strip = name.strip()
        if name_strip and name_strip not in seen:
            klienci_list.append(name_strip)
            seen.add(name_strip)

    class CustomCompleter(QCompleter):
        """Klasa pomocnicza używana przez aplikację."""
        def __init__(self, items, parent=None, max_items=7):
            """Inicjalizuje obiekt i przygotowuje jego stan początkowy."""
            super().__init__(items, parent)
            self.setCaseSensitivity(QtCore.Qt.CaseSensitivity.CaseInsensitive)
            self.max_items = max_items
            self.all_items = items if isinstance(items, list) else list(items)
            self.model = QStringListModel()
            self.setModel(self.model)

        def pathFromIndex(self, index):
            """Realizuje logikę operacji path from index w klasie CustomCompleter."""
            return index.data()

        def splitPath(self, path):
            """Realizuje logikę operacji split path w klasie CustomCompleter."""
            path_lower = path.lower()
            matches = [item for item in self.all_items if path_lower in item.lower()]
            return matches[:self.max_items]

    completer = CustomCompleter(klienci_list)
    fields["imie"].setCompleter(completer)
    fields["imie"].textChanged.connect(lambda text: completer.model.setStringList(
        [item for item in klienci_list if text.lower() in item.lower()][:7]
    ))

    cursor.execute("SELECT imie_nazwisko, telefon, email FROM zlecenia ORDER BY id DESC")
    klienci = cursor.fetchall()

    def fill_fields(name=None):
        """Realizuje logikę operacji fill fields."""
        text = name if name is not None else fields["imie"].text()
        text_parts = set(text.lower().split())
        for k in klienci:
            db_parts = set(k[0].lower().split())
            if text_parts.issubset(db_parts) or db_parts.issubset(text_parts) or (text_parts & db_parts):
                fields["telefon"].setText(k[1] or "")
                fields["email"].setText(k[2] or "")
                break

    completer.activated.connect(fill_fields)

    def zapisz():
        """Realizuje logikę operacji zapisz."""
        imie = fields["imie"].text().strip()
        telefon = fields["telefon"].text().strip()
        sprzet = fields["sprzet"].text().strip()
        email = fields["email"].text().strip()
        sn_val = fields["sn"].text().strip()
        opis_val = fields["opis"].toPlainText().strip()
        uwagi_val = fields["uwagi"].toPlainText().strip()

        if not imie or not telefon or not sprzet:
            QtWidgets.QMessageBox.warning(dialog, _("Uwaga"), _("Imię, Telefon i Sprzęt są wymagane!"))
            return

        data_zlecenia = datetime.date.today().isoformat()
        status = "Przyjęte"

        # --- ZAPIS AUTORA ---
        kto_wystawil = password_protection.CURRENT_USER if password_protection.CURRENT_USER else ""

        if chk_akcesoria.isChecked() and akcesoria_input.text().strip():
            akcesoria_text = akcesoria_input.text().strip()
            opis_val += f" | { _('Akcesoria:') } {akcesoria_text}"

        dodatki = []
        if chk_gwarancja.isChecked():
            dodatki.append(_("Na gwarancji"))
        if chk_rkj.isChecked():
            dodatki.append(_("Rękojmia"))
        if chk_pilne.isChecked():
            dodatki.append(_("Pilne – wysoki priorytet"))
        if dodatki:
            uwagi_val += (" | " if uwagi_val else "") + " | ".join(dodatki)

        try:
            nr_roczny = pobierz_nastepny_numer_roczny(cursor)

            cursor.execute("""
                INSERT INTO zlecenia (imie_nazwisko, telefon, sprzet, nr_seryjny, opis, uwagi, status, data_zlecenia, email, pilne, nr_roczny, wystawil)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                imie, telefon, sprzet, sn_val,
                opis_val, uwagi_val, status, data_zlecenia, email,
                1 if chk_pilne.isChecked() else 0,
                nr_roczny,
                kto_wystawil
            ))
            conn.commit()

            new_id = cursor.lastrowid
            highlight_id = formatuj_numer_zlecenia(new_id, data_zlecenia, nr_roczny)

            status_filter, search_term = _get_filters_from_ui(ui) if ui else (None, None)

            odswiez_tabele(cursor if cursor else conn, model,
                           table_view=(ui.tableView if ui else None),
                           status_filter=status_filter,
                           search_term=search_term,
                           highlight_id=highlight_id)

            dialog.accept()
        except Exception as e:
            QtWidgets.QMessageBox.critical(
                dialog,
                _("Błąd"),
                _("Nie udało się dodać zlecenia: {error}").format(error=e)
            )

    btn = QtWidgets.QPushButton(_("Zapisz"))
    btn.setMaximumWidth(120)
    btn.clicked.connect(zapisz)
    btn_layout = QtWidgets.QHBoxLayout()
    btn_layout.addStretch()
    btn_layout.addWidget(btn)
    btn_layout.addStretch()
    layout.addRow(btn_layout)

    dialog.exec()


def zakoncz_zlecenie(conn: sqlite3.Connection, cursor: sqlite3.Cursor, model, ui=None, parent=None):
    """Realizuje logikę operacji zakoncz zlecenie."""
    indexes = ui.tableView.selectionModel().selectedRows()
    if not indexes:
        QtWidgets.QMessageBox.warning(parent, _("Uwaga"), _("Zaznacz zlecenie do zakończenia"))
        return

    index = indexes[0]

    item_id = model.itemFromIndex(index.sibling(index.row(), 0))
    real_id_db = item_id.data(QtCore.Qt.UserRole)

    if real_id_db:
        id_num = int(real_id_db)
    else:
        id_raw = index.sibling(index.row(), 0).data()
        id_num = int(str(id_raw).split("/")[0])

    z = cursor.execute("SELECT * FROM zlecenia WHERE id=?", (id_num,)).fetchone()
    if not z:
        QtWidgets.QMessageBox.warning(parent, _("Błąd"), _("Nie znaleziono zlecenia w bazie"))
        return

    stat = z[7]
    if stat == "Ukończone" or stat == _("Ukończone"):
        QtWidgets.QMessageBox.information(parent, _("Info"), _("Zlecenie jest już zakończone"))
        return

    reply = QtWidgets.QMessageBox.question(parent, _("Potwierdzenie"), _("Zmień status na 'Ukończone'?"),
                                           QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.Cancel)
    if reply == QtWidgets.QMessageBox.StandardButton.Yes:
        cursor.execute("UPDATE zlecenia SET status='Ukończone' WHERE id=?", (id_num,))
        conn.commit()

        status_filter, search_term = _get_filters_from_ui(ui)
        odswiez_tabele(cursor, model, table_view=ui.tableView,
                       status_filter=status_filter, search_term=search_term)

class CopyableLineEdit(QtWidgets.QLineEdit):
    """Klasa pomocnicza używana przez aplikację."""
    def __init__(self, text="", parent=None, read_only=False):
        """Inicjalizuje obiekt i przygotowuje jego stan początkowy."""
        super().__init__(text, parent)
        self.setReadOnly(read_only)
        self.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

    def show_context_menu(self, pos):
        """Wyświetla menu kontekstowe dla kontrolki."""
        menu = self.createStandardContextMenu()
        copy_all_action = menu.addAction(_("Kopiuj wszystko"))
        copy_all_action.triggered.connect(lambda: QtWidgets.QApplication.clipboard().setText(self.text()))
        menu.exec(self.mapToGlobal(pos))


class CopyableTextEdit(QtWidgets.QTextEdit):
    """Klasa pomocnicza używana przez aplikację."""
    def __init__(self, text="", parent=None, read_only=False):
        """Inicjalizuje obiekt i przygotowuje jego stan początkowy."""
        super().__init__(parent)
        self.setText(text)
        self.setReadOnly(read_only)
        self.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

    def show_context_menu(self, pos):
        """Wyświetla menu kontekstowe dla kontrolki."""
        menu = self.createStandardContextMenu()
        copy_all_action = menu.addAction(_("Kopiuj wszystko"))
        copy_all_action.triggered.connect(lambda: QtWidgets.QApplication.clipboard().setText(self.toPlainText()))
        menu.exec(self.mapToGlobal(pos))

import sqlite3
import re
from PySide6 import QtWidgets, QtCore

def _wspolna_logika_okna(conn: sqlite3.Connection, cursor: sqlite3.Cursor, id_num, parent, odswiez_funkcja):
    """Jeden, wspólny dialog zawierający absolutnie wszystkie pola z obu pierwotnych funkcji."""
    z = cursor.execute("SELECT * FROM zlecenia WHERE id=?", (id_num,)).fetchone()
    if not z:
        QtWidgets.QMessageBox.warning(parent, _("Błąd"), _("Nie znaleziono zlecenia w bazie"))
        return

    colnames = [desc[1] for desc in cursor.execute("PRAGMA table_info('zlecenia')").fetchall()]

    # Formatowanie numeru do tytułu
    nr_roczny_idx = colnames.index("nr_roczny") if "nr_roczny" in colnames else -1
    val_nr_roczny = z[nr_roczny_idx] if nr_roczny_idx != -1 else None
    id_formatted = formatuj_numer_zlecenia(z[0], z[8], val_nr_roczny)

    dialog = QtWidgets.QDialog(parent)
    dialog.setWindowTitle(_("Dane zlecenia {id}").format(id=id_formatted))
    dialog.resize(500, 650) # Stały, zgrabny rozmiar
    layout = QtWidgets.QFormLayout(dialog)

    # --- LOGIKA UPRAWNIEŃ ---
    stat = z[7]
    is_finished = (stat == "Ukończone" or stat == _("Ukończone"))
    is_admin = password_protection.CURRENT_USER_IS_SUPER
    is_read_only = is_finished and not is_admin

    if is_read_only:
        dialog.setWindowTitle(_("Podgląd zlecenia (Ukończone)"))

    # --- INICJALIZACJA PÓL (ZACHOWANE ORYGINALNE WYSOKOŚCI) ---
    imie = CopyableLineEdit(z[1])
    telefon = CopyableLineEdit(z[2])
    email = CopyableLineEdit(z[9])
    sprzet = CopyableLineEdit(z[3])
    nr_seryjny = CopyableLineEdit(z[4])

    opis = CopyableTextEdit(z[5] or "")
    opis.setFixedHeight(80) # Oryginał z popraw_dane
    opis.setTabChangesFocus(True)

    uwagi = CopyableTextEdit(z[6] or "")
    uwagi.setFixedHeight(150) # Oryginał z popraw_dane
    uwagi.setTabChangesFocus(True)

    naprawa_val = z[colnames.index("naprawa_opis")] if "naprawa_opis" in colnames else ""
    naprawa = CopyableTextEdit(naprawa_val or "")
    naprawa.setFixedHeight(60) # Oryginał z pokaz_szczegoly
    naprawa.setTabChangesFocus(True)

    koszt_cz_val = z[colnames.index("koszt_czesci")] if "koszt_czesci" in colnames else 0.0
    koszt_us_val = z[colnames.index("koszt_uslugi")] if "koszt_uslugi" in colnames else 0.0
    koszt_cz_edit = CopyableLineEdit(f"{float(koszt_cz_val or 0.0):.2f}")
    koszt_us_edit = CopyableLineEdit(f"{float(koszt_us_val or 0.0):.2f}")

    # --- UKŁAD FORMULARZA ---
    layout.addRow(_("Imię i Nazwisko:"), imie)
    layout.addRow(_("Telefon:"), telefon)
    layout.addRow(_("E-mail:"), email)
    layout.addRow(_("Sprzęt:"), sprzet)
    layout.addRow(_("Nr seryjny:"), nr_seryjny)
    layout.addRow(_("Opis:"), opis)
    layout.addRow(_("Uwagi:"), uwagi)
    layout.addRow(_("Naprawa:"), naprawa)
    layout.addRow(_("Koszt Części:"), koszt_cz_edit)
    layout.addRow(_("Koszt Usługi:"), koszt_us_edit)

    # --- SEKCOJA SUMY (ZGRABNA, NIE ROZWLACZONA) ---
    suma_container = QtWidgets.QWidget()
    suma_h_layout = QtWidgets.QHBoxLayout(suma_container)
    suma_h_layout.setContentsMargins(0, 0, 0, 0)
    suma_label = QtWidgets.QLabel()
    suma_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #2e7d32;")
    suma_h_layout.addWidget(suma_label)
    suma_h_layout.addStretch() # Spycha tekst do lewej

    def update_suma():
        """Aktualizuje stan danych lub interfejsu."""
        try:
            cz = float(koszt_cz_edit.text().replace(',', '.'))
            us = float(koszt_us_edit.text().replace(',', '.'))
            suma_label.setText(f"{round(cz + us, 2):.2f} PLN")
        except ValueError: suma_label.setText("--- PLN")

    koszt_cz_edit.textChanged.connect(update_suma)
    koszt_us_edit.textChanged.connect(update_suma)
    update_suma()
    layout.addRow(_("Razem:"), suma_container)

    # --- CHECKBOXY I DODATKI ---
    checkbox_layout = QtWidgets.QHBoxLayout()
    chk_akcesoria = QtWidgets.QCheckBox(_("Akcesoria"))
    chk_gwarancja = QtWidgets.QCheckBox(_("Gwarancja"))
    chk_rkj = QtWidgets.QCheckBox(_("Rękojmia (NTZU)"))
    chk_pilne = QtWidgets.QCheckBox(_("Pilne"))
    for cb in [chk_akcesoria, chk_gwarancja, chk_rkj, chk_pilne]: checkbox_layout.addWidget(cb)
    layout.addRow(_("Opcje:"), checkbox_layout)

    akcesoria_input = QtWidgets.QLineEdit()
    akcesoria_input.setPlaceholderText(_("Wpisz jakie akcesoria..."))
    akcesoria_input.hide()
    layout.addRow(_("Akcesoria (opis):"), akcesoria_input)
    chk_akcesoria.stateChanged.connect(lambda _: akcesoria_input.setVisible(chk_akcesoria.isChecked()))

    # --- WCZYTYWANIE FLAG Z BAZY ---
    opis_full = z[5] or ""
    acc_label = _("Akcesoria:")
    match_acc = re.search(r"\|\s*" + re.escape(acc_label) + r"\s*(.*)", opis_full)
    if match_acc:
        chk_akcesoria.setChecked(True)
        akcesoria_input.setText(match_acc.group(1).strip())
        akcesoria_input.show()

    uwagi_full = z[6] or ""
    if _("Na gwarancji") in uwagi_full: chk_gwarancja.setChecked(True)
    if _("Rękojmia") in uwagi_full: chk_rkj.setChecked(True)

    pilne_db_val = z[colnames.index("pilne")] if "pilne" in colnames else 0
    if pilne_db_val == 1 or _("Pilne – wysoki priorytet") in uwagi_full: chk_pilne.setChecked(True)

    # --- BLOKADA DLA ZWYKŁYCH USERÓW ---
    if is_read_only:
        for w in [imie, telefon, email, sprzet, nr_seryjny, opis, uwagi, naprawa, koszt_cz_edit, koszt_us_edit, akcesoria_input]:
            w.setReadOnly(True)
            w.setStyleSheet("background-color: #f5f5f5; color: #666;")
        for c in [chk_akcesoria, chk_gwarancja, chk_rkj, chk_pilne]: c.setEnabled(False)

    btn_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.StandardButton.Ok |
                                         QtWidgets.QDialogButtonBox.StandardButton.Cancel)
    layout.addRow(btn_box)

    def zapisz():
        """Realizuje logikę operacji zapisz."""
        if is_read_only:
            dialog.accept()
            return
        try:
            nowy_opis_txt = opis.toPlainText().strip()
            nowe_uwagi_txt = uwagi.toPlainText().strip()

            # Czyszczenie starych flag przed zapisem
            nowy_opis_txt = re.sub(r"\|\s*" + re.escape(acc_label) + r".*", "", nowy_opis_txt).strip()
            for flag in [_("Na gwarancji"), _("Rękojmia"), _("Pilne – wysoki priorytet")]:
                nowe_uwagi_txt = nowe_uwagi_txt.replace(" | " + flag, "").replace(flag, "").strip()

            if chk_akcesoria.isChecked() and akcesoria_input.text().strip():
                nowy_opis_txt += f" | {acc_label} {akcesoria_input.text().strip()}"

            dodatki = []
            if chk_gwarancja.isChecked(): dodatki.append(_("Na gwarancji"))
            if chk_rkj.isChecked(): dodatki.append(_("Rękojmia"))
            if chk_pilne.isChecked(): dodatki.append(_("Pilne – wysoki priorytet"))
            if dodatki: nowe_uwagi_txt = (nowe_uwagi_txt + " | " if nowe_uwagi_txt else "") + " | ".join(dodatki)

            params = (
                imie.text().strip(), telefon.text().strip(), email.text().strip(),
                sprzet.text().strip(), nr_seryjny.text().strip(),
                nowy_opis_txt, nowe_uwagi_txt.strip(" |"), naprawa.toPlainText().strip(),
                float(koszt_cz_edit.text().replace(',', '.')), float(koszt_us_edit.text().replace(',', '.')),
                1 if chk_pilne.isChecked() else 0, id_num
            )

            cursor.execute("""UPDATE zlecenia SET
                              imie_nazwisko=?, telefon=?, email=?, sprzet=?, nr_seryjny=?,
                              opis=?, uwagi=?, naprawa_opis=?, koszt_czesci=?, koszt_uslugi=?, pilne=?
                              WHERE id=?""", params)
            conn.commit()
            if odswiez_funkcja: odswiez_funkcja()
            dialog.accept()
        except Exception as e: QtWidgets.QMessageBox.critical(dialog, _("Błąd"), str(e))

    btn_box.accepted.connect(zapisz)
    btn_box.rejected.connect(dialog.reject)
    dialog.exec()

# --- FUNKCJE WRAPPERY ---

def popraw_dane(conn, cursor, model, ui=None, parent=None, odswiez_funkcja=None):
    """Aktualizuje lub poprawia dane wejściowe."""
    indexes = ui.tableView.selectionModel().selectedRows()
    if not indexes:
        QtWidgets.QMessageBox.warning(parent, _("Uwaga"), _("Zaznacz zlecenie do edycji"))
        return
    idx = indexes[0]
    item_id = model.itemFromIndex(idx.sibling(idx.row(), 0))
    real_id_db = item_id.data(QtCore.Qt.ItemDataRole.UserRole)
    id_num = int(real_id_db) if real_id_db else int(str(idx.sibling(idx.row(), 0).data()).split("/")[0])
    _wspolna_logika_okna(conn, cursor, id_num, parent, odswiez_funkcja)

def pokaz_szczegoly(conn, cursor, index, model, ui=None, parent=None, odswiez_funkcja=None):
    """Wyświetla wskazane dane lub okno."""
    if not index.isValid():
        QtWidgets.QMessageBox.warning(parent, _("Uwaga"), _("Zaznacz zlecenie"))
        return
    item_id = model.itemFromIndex(index.sibling(index.row(), 0))
    real_id_db = item_id.data(QtCore.Qt.ItemDataRole.UserRole)
    id_num = int(real_id_db) if real_id_db else int(str(index.sibling(index.row(), 0).data()).split("/")[0])
    _wspolna_logika_okna(conn, cursor, id_num, parent, odswiez_funkcja)
