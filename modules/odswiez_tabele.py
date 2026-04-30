import datetime
import re
from PySide6.QtGui import QStandardItem, QColor, QIcon
from PySide6 import QtCore
from modules.utils import resource_path, formatuj_numer_zlecenia

# Zabezpieczenie na wypadek uruchamiania modułu niezależnie (bez main.py)
try:
    _("Test")
except NameError:
    def _(text):
        """Zwraca tekst bez tłumaczenia, gdy mechanizm i18n nie jest aktywny."""
        return text

def strip_html_tags(text):
    """Usuwa zbędne fragmenty z przekazanego tekstu."""
    if not text:
        return ""
    return re.sub(r"<[^>]*?>", "", text)

def odswiez_tabele(c, model, table_view=None, status_filter=None, search_term=None,
                   date_from=None, date_to=None, highlight_id=None):

    """Odświeża dane lub widok interfejsu."""
    icons_map = {
        _("Przyjęte"): QIcon(resource_path("actions/new.png")),
        _("Ukończone"): QIcon(resource_path("actions/zakoncz.png")),
        "Accepted": QIcon(resource_path("actions/new.png")),
        "Completed": QIcon(resource_path("actions/zakoncz.png")),
    }

    try:
        pragma = c.execute("PRAGMA table_info('zlecenia')").fetchall()
        colnames = [r[1] for r in pragma]
    except Exception:
        colnames = []

    def idx(name, fallback=None):
        """Realizuje logikę operacji idx."""
        try:
            return colnames.index(name)
        except ValueError:
            return fallback

    id_idx = idx('id', 0)
    imie_idx = idx('imie_nazwisko', 1)
    tel_idx = idx('telefon', 2)
    sprzet_idx = idx('sprzet', 3)
    nr_idx = idx('nr_seryjny', 4)
    opis_idx = idx('opis', 5)
    uwagi_idx = idx('uwagi', 6)
    status_idx = idx('status', 7)
    data_idx = idx('data_zlecenia', 8)
    email_idx = idx('email', 9)
    pilne_idx = idx('pilne', None)
    nr_roczny_idx = idx('nr_roczny', None)

    selected_ids = []
    v_scroll_pos = h_scroll_pos = 0
    if table_view:
        try:
            sm = table_view.selectionModel()
            if sm:
                indexes = sm.selectedRows()
                for idx_sel in indexes:
                    item = model.itemFromIndex(idx_sel.sibling(idx_sel.row(), 0))
                    if item:
                        real_id = item.data(QtCore.Qt.UserRole)
                        if real_id:
                            selected_ids.append(str(real_id))
                        else:
                            val = idx_sel.sibling(idx_sel.row(), 0).data()
                            selected_ids.append(str(val).split('/')[0])

            v_scroll_pos = table_view.verticalScrollBar().value()
            h_scroll_pos = table_view.horizontalScrollBar().value()
        except Exception:
            selected_ids = []
            v_scroll_pos = h_scroll_pos = 0

    try:
        model.removeRows(0, model.rowCount())
    except Exception:
        pass

    query = "SELECT * FROM zlecenia"
    conditions = []
    params = []

    if not search_term:
        if status_filter:
            if isinstance(status_filter, str):
                status_filter = [status_filter]
            if status_filter:
                placeholders = ",".join("?" for _ in status_filter)
                conditions.append(f"status IN ({placeholders})")
                params.extend(status_filter)

        if date_from:
            conditions.append("data_zlecenia >= ?")
            params.append(date_from)

        if date_to:
            conditions.append("data_zlecenia <= ?")
            params.append(date_to)

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " ORDER BY id DESC"

    try:
        results = c.execute(query, params).fetchall()
    except Exception:
        results = []

    if search_term:
        search_term_lower = search_term.lower()
        filtered_results = []
        for z in results:
            data_zlecenia = z[data_idx] if data_idx is not None and len(z) > data_idx else ""
            val_nr_roczny = z[nr_roczny_idx] if nr_roczny_idx is not None else None

            id_formatted = formatuj_numer_zlecenia(z[id_idx], data_zlecenia, val_nr_roczny)

            text_to_search = " ".join([
                id_formatted,
                str(z[id_idx]),
                (z[imie_idx] if imie_idx is not None else ""),
                (z[tel_idx] if tel_idx is not None else ""),
                (z[sprzet_idx] if sprzet_idx is not None else ""),
                (z[nr_idx] if nr_idx is not None else ""),
                (z[uwagi_idx] if uwagi_idx is not None else ""),
                (z[status_idx] if status_idx is not None else ""),
            ]).lower()

            if search_term_lower in text_to_search:
                filtered_results.append(z)
        results = filtered_results

    for z in results:
        data_zlecenia = z[data_idx] if data_idx is not None and len(z) > data_idx else ""
        val_nr_roczny = z[nr_roczny_idx] if nr_roczny_idx is not None else None

        id_formatted = formatuj_numer_zlecenia(z[id_idx], data_zlecenia, val_nr_roczny)

        raw_status = z[status_idx] if status_idx is not None else ""
        status_display = _(raw_status)

        imie_val = z[imie_idx] if imie_idx is not None else ""
        tel_val = z[tel_idx] if tel_idx is not None else ""
        sprzet_val = z[sprzet_idx] if sprzet_idx is not None else ""
        nr_val = z[nr_idx] if nr_idx is not None else ""
        uwagi_raw = z[uwagi_idx] if uwagi_idx is not None else ""
        uwagi_display = strip_html_tags(uwagi_raw)

        item_id = QStandardItem(str(id_formatted))
        item_id.setData(z[id_idx], QtCore.Qt.UserRole)
        item_id.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        row = [
            item_id,
            QStandardItem(data_zlecenia),
            QStandardItem(imie_val),
            QStandardItem(tel_val),
            QStandardItem(sprzet_val),
            QStandardItem(nr_val),
            QStandardItem(uwagi_display),
            QStandardItem(status_display)
        ]

        icon = icons_map.get(status_display)
        if icon and not icon.isNull():
            row[7].setIcon(icon)

        pilne_val = 0
        if pilne_idx is not None:
            try:
                pilne_val = int(z[pilne_idx] or 0)
            except (TypeError, ValueError):
                pass

        if pilne_val == 1:
            try:
                data_dt = datetime.datetime.strptime(data_zlecenia, "%Y-%m-%d").date()
                diff_days = (datetime.date.today() - data_dt).days
            except ValueError:
                diff_days = 999

            if diff_days <= 1:
                red_color = QColor(220, 60, 60)
                for item in row:
                    item.setEditable(False)
                    item.setForeground(red_color)
            else:
                pass

        if status_display in (_("Ukończone"), _("Zakończone"), "Completed"):
            gray_color = QColor(180, 180, 180)
            for item in row:
                item.setEditable(False)
                item.setForeground(gray_color)
        else:
            try:
                data_dt = datetime.datetime.strptime(data_zlecenia, "%Y-%m-%d").date()
                diff_days = (datetime.date.today() - data_dt).days
            except ValueError:
                diff_days = 0

            if pilne_val == 1 and diff_days <= 1:
                pass
            
            else:
                for item in row:
                    item.setEditable(False)

        model.appendRow(row)

    if table_view:
        try:
            selection_model = table_view.selectionModel()
            if selection_model:
                selection_model.clearSelection()

                if highlight_id:
                    for row_idx in range(model.rowCount()):
                        item = model.item(row_idx, 0)
                        if item.text() == str(highlight_id):
                            index = model.index(row_idx, 0)
                            selection_model.select(index, QtCore.QItemSelectionModel.Select | QtCore.QItemSelectionModel.Rows)
                            table_view.scrollTo(index)
                            return

                        real_id = item.data(QtCore.Qt.UserRole)
                        try:
                            hl_int = int(str(highlight_id).split('/')[0])
                            if real_id == hl_int:
                                index = model.index(row_idx, 0)
                                selection_model.select(index, QtCore.QItemSelectionModel.Select | QtCore.QItemSelectionModel.Rows)
                                table_view.scrollTo(index)
                                return
                        except (TypeError, ValueError, IndexError):
                            pass

                if selected_ids:
                    for row_idx in range(model.rowCount()):
                        item = model.item(row_idx, 0)
                        real_id = item.data(QtCore.Qt.UserRole)
                        if str(real_id) in selected_ids:
                            index = model.index(row_idx, 0)
                            selection_model.select(
                                index,
                                QtCore.QItemSelectionModel.SelectionFlag.Select | QtCore.QItemSelectionModel.SelectionFlag.Rows
                            )

            table_view.verticalScrollBar().setValue(v_scroll_pos)
            table_view.horizontalScrollBar().setValue(h_scroll_pos)
        except Exception:
            pass
