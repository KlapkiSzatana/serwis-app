import os
import sys
import datetime
import tempfile


def _candidate_base_paths():
    """Realizuje logikę operacji candidate base paths."""
    candidates = []

    if getattr(sys, "frozen", False):
        executable_dir = os.path.dirname(os.path.abspath(sys.executable))
        candidates.append(executable_dir)

        bundled_dir = getattr(sys, "_MEIPASS", None)
        if bundled_dir:
            candidates.append(bundled_dir)
    else:
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        candidates.append(project_root)

    if sys.argv and sys.argv[0]:
        entry_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        if entry_dir not in candidates:
            candidates.append(entry_dir)

    temp_bundle_dir = os.path.join(tempfile.gettempdir(), os.path.basename(sys.executable))
    if temp_bundle_dir not in candidates:
        candidates.append(temp_bundle_dir)

    return candidates

def resource_path(relative_path):
    """Realizuje logikę operacji resource path."""
    candidates = _candidate_base_paths()

    for base_path in candidates:
        candidate = os.path.join(base_path, relative_path)
        if os.path.exists(candidate):
            return candidate

    return os.path.join(candidates[0], relative_path)

def formatuj_numer_zlecenia(id_db, data_str, nr_roczny_db=None):
    """
    Inteligentne formatowanie numeru zlecenia.

    Zasada:
    1. Jeśli istnieje 'nr_roczny_db' (nowy system) -> Zwraca: NR_ROCZNY/MM/RRRR
    2. Jeśli brak (stare zlecenia) -> Zwraca: ID/MM/RRRR

    Argumenty:
    id_db -- Prawdziwe ID z bazy (Primary Key)
    data_str -- Data zlecenia (string YYYY-MM-DD)
    nr_roczny_db -- Wartość kolumny nr_roczny (może być None)
    """
    try:
        rok = str(datetime.date.today().year)
        miesiac = f"{datetime.date.today().month:02d}"

        if data_str:
            try:
                parts = data_str.split("-")
                if len(parts) == 3:
                    rok = parts[0]
                    miesiac = f"{int(parts[1]):02d}"
            except (TypeError, ValueError):
                pass

        if nr_roczny_db is not None and isinstance(nr_roczny_db, int) and nr_roczny_db > 0:
            return f"{nr_roczny_db}/{miesiac}/{rok}"
        else:
            return f"{id_db}/{miesiac}/{rok}"

    except (TypeError, ValueError):
        return str(id_db)
