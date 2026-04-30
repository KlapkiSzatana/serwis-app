import os
import sys
import datetime
import shutil
import zipfile
import configparser
import time
import sqlite3
from setup import config
from PySide6 import QtCore, QtWidgets, QtGui
from PySide6.QtWidgets import QFileDialog, QMessageBox
from modules.button import MyPushButton
from modules.utils import resource_path

# Zabezpieczenie na wypadek uruchamiania modułu niezależnie
try:
    _("Test")
except NameError:
    def _(text):
        """Realizuje pomocniczą część logiki aplikacji."""
        return text

USER_HOME = os.path.expanduser("~")
APP_DIR = os.path.join(USER_HOME, ".SerwisApp")
if not os.path.exists(APP_DIR):
    os.makedirs(APP_DIR)

# ---------------------- Helper Functions ----------------------

def force_remove_file(path, max_attempts=5, delay=0.3):
    """Spróbuj wymusić usunięcie pliku, nawet jeśli jest zablokowany."""
    for attempt in range(max_attempts):
        try:
            if os.path.exists(path):
                os.chmod(path, 0o777)
                os.remove(path)
            return True
        except OSError:
            time.sleep(delay)
    print(f"Nie udało się usunąć pliku {path} po {max_attempts} próbach.")
    return False

def clean_directory(path):
    """Bezpieczne czyszczenie katalogu, bez jego usuwania."""
    if not os.path.exists(path):
        return
    for root, dirs, files in os.walk(path, topdown=False):
        for name in files:
            force_remove_file(os.path.join(root, name))
        for name in dirs:
            dir_path = os.path.join(root, name)
            try:
                os.rmdir(dir_path)
            except OSError:
                shutil.rmtree(dir_path, ignore_errors=True)

def wykonaj_backup_logika(dst_path, progress_callback=None):
    """Tworzenie backupu katalogu APP_DIR do pliku zip."""
    if not dst_path:
        raise ValueError(_("Brak ścieżki docelowej"))

    dst_dir = os.path.dirname(dst_path)
    if dst_dir and not os.path.exists(dst_dir):
        os.makedirs(dst_dir, exist_ok=True)

    with zipfile.ZipFile(dst_path, "w", zipfile.ZIP_DEFLATED) as backup_zip:
        total_files = sum(len(files) for _, _, files in os.walk(APP_DIR))
        total_files = total_files or 1

        count = 0
        for foldername, subfolders, filenames in os.walk(APP_DIR):
            for filename in filenames:
                if filename.endswith("-wal") or filename.endswith("-shm"):
                    continue
                file_path = os.path.join(foldername, filename)
                arcname = os.path.relpath(file_path, APP_DIR)
                try:
                    backup_zip.write(file_path, arcname)
                except PermissionError:
                    print(f"Pominięto zablokowany plik: {filename}")
                count += 1
                if progress_callback:
                    progress_callback(int(count / total_files * 100))
                    QtWidgets.QApplication.processEvents()

# ---------------------- UI Class ----------------------

class Ui_MainWindow(object):
    """Klasa budująca i przechowująca elementy interfejsu użytkownika."""
    LAST_PATH_FILE = os.path.join(APP_DIR, "last_path.txt")

    def setupUi(self, MainWindow):
        """Buduje i konfiguruje interfejs użytkownika."""
        self.main_window_ref = MainWindow
        MainWindow.setObjectName("MainWindow")
        MainWindow.setFixedSize(500, 340)
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        MainWindow.setCentralWidget(self.centralwidget)

        # Logo
        logo_size = 40
        margin_right = 15
        margin_bottom = 1
        margin_top = 20
        self.logo_label = QtWidgets.QLabel(self.centralwidget)
        pixmap = QtGui.QPixmap(resource_path("resources/logo/serwisapp.png"))
        self.logo_label.setPixmap(pixmap.scaled(logo_size, logo_size, QtCore.Qt.KeepAspectRatio))
        self.logo_label.resize(logo_size, logo_size)

        # App name
        self.app_name_label = QtWidgets.QLabel(_("SerwisApp - Backup"), self.centralwidget)
        font = QtGui.QFont()
        font.setPointSize(14)
        font.setBold(True)
        self.app_name_label.setFont(font)
        self.app_name_label.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        self.app_name_label.adjustSize()

        def adjust_positions():
            """Realizuje logikę operacji adjust positions w klasie Ui_MainWindow."""
            window_width = self.centralwidget.width()
            window_height = self.centralwidget.height()
            self.logo_label.move(window_width - logo_size - margin_right,
                                 window_height - logo_size - margin_bottom)
            x_center = (window_width - self.app_name_label.width()) // 2
            self.app_name_label.move(x_center, margin_top)
        QtCore.QTimer.singleShot(0, adjust_positions)

        # Path input
        self.lineEdit = QtWidgets.QLineEdit(self.centralwidget)
        self.lineEdit.setGeometry(QtCore.QRect(90, 90, 281, 32))
        self.lineEdit.setText(self.load_last_path())
        self.toolButton = QtWidgets.QToolButton(self.centralwidget)
        self.toolButton.setGeometry(QtCore.QRect(380, 90, 33, 31))
        self.toolButton.clicked.connect(lambda: self.choose_file(MainWindow))

        # Backup button
        self.pushButton = MyPushButton(_("Utwórz Kopię Bazy"), self.centralwidget)
        self.pushButton.setGeometry(QtCore.QRect(90, 160, 156, 34))
        icon_size = QtCore.QSize(24, 24)
        self.pushButton.setIcon(QtGui.QIcon(resource_path("actions/create.png")))
        self.pushButton.setIconSize(icon_size)
        self.pushButton.show()
        self.pushButton.clicked.connect(self.create_backup)

        # Restore button
        self.pushButton_2 = MyPushButton(_("Przywróć Kopię"), self.centralwidget)
        self.pushButton_2.setGeometry(QtCore.QRect(250, 160, 156, 34))
        self.pushButton_2.setIcon(QtGui.QIcon(resource_path("actions/restore.png")))
        self.pushButton_2.setIconSize(icon_size)
        self.pushButton_2.show()
        self.pushButton_2.clicked.connect(self.restore_backup_action)

        # Auto backup checkbox
        self.checkBoxAuto = QtWidgets.QCheckBox(self.centralwidget)
        self.checkBoxAuto.setGeometry(QtCore.QRect(90, 210, 320, 20))
        self.checkBoxAuto.setText(_("Wykonuj kopię automatycznie przy zamykaniu programu"))
        self.checkBoxAuto.setChecked(self.load_auto_backup_state())
        self.checkBoxAuto.stateChanged.connect(self.save_auto_backup_state)

        # Progress bar
        self.progressBar = QtWidgets.QProgressBar(self.centralwidget)
        self.progressBar.setGeometry(QtCore.QRect(90, 250, 321, 23))
        self.progressBar.setProperty("value", 0)

        # Label
        self.label2 = QtWidgets.QLabel(_("Podaj nazwę dla pliku kopii"), self.centralwidget)
        self.label2.setGeometry(QtCore.QRect(0, 55, 500, 30))
        self.label2.setAlignment(QtCore.Qt.AlignCenter)

        # Menubar & statusbar
        self.menubar = QtWidgets.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 500, 30))
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(MainWindow)
        MainWindow.setStatusBar(self.statusbar)
        # Obliczamy rok
        curr_year = datetime.date.today().year
        year_str = f"2025-{curr_year}" if curr_year > 2025 else "2025"

        # Tworzymy etykietę (dodałem spację przed rokiem dla czytelności)
        copyright_label = QtWidgets.QLabel(f"© KlapkiSzatana {year_str}")
        font = QtGui.QFont()
        font.setPointSize(8)
        font.setBold(False)
        copyright_label.setFont(font)
        copyright_label.setAlignment(QtCore.Qt.AlignCenter)
        self.statusbar.addPermanentWidget(copyright_label)

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    # ---------------------- UI Helper Methods ----------------------

    def retranslateUi(self, MainWindow):
        """Ustawia teksty interfejsu zgodnie z aktywnym tłumaczeniem."""
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", _("Backup Bazy")))
        self.pushButton.setText(_translate("MainWindow", _("Utwórz Kopię")))
        self.pushButton_2.setText(_translate("MainWindow", _("Przywróć Kopię")))
        self.toolButton.setText(_translate("MainWindow", "..."))
        self.label2.setText(_translate("MainWindow", _("Wskaż lokalizację pliku kopii")))
        self.checkBoxAuto.setText(_translate("MainWindow", _("Automatycznie przy zamykaniu programu")))

    def save_last_path(self, path):
        """Zapisuje dane lub ustawienia."""
        try:
            with open(self.LAST_PATH_FILE, "w", encoding="utf-8") as f:
                f.write(path)
        except OSError as e:
            print(f"{_('Nie udało się zapisać ostatniej ścieżki: ')}{e}")

    def load_last_path(self):
        """Wczytuje dane lub ustawienia potrzebne do działania."""
        try:
            if os.path.exists(self.LAST_PATH_FILE):
                with open(self.LAST_PATH_FILE, "r", encoding="utf-8") as f:
                    return f.read().strip()
        except OSError as e:
            print(f"{_('Nie udało się wczytać ostatniej ścieżki: ')}{e}")
        return ""

    def load_auto_backup_state(self):
        """Wczytuje dane lub ustawienia potrzebne do działania."""
        cfg = configparser.ConfigParser()
        if os.path.exists(config.CONFIG_FILE):
            cfg.read(config.CONFIG_FILE, encoding="utf-8")
            if "BACKUP" in cfg:
                return cfg.getboolean("BACKUP", "auto_backup", fallback=False)
        return False

    def save_auto_backup_state(self):
        """Zapisuje dane lub ustawienia."""
        cfg = configparser.ConfigParser()
        if os.path.exists(config.CONFIG_FILE):
            cfg.read(config.CONFIG_FILE, encoding="utf-8")
        if "BACKUP" not in cfg:
            cfg["BACKUP"] = {}
        cfg["BACKUP"]["auto_backup"] = str(self.checkBoxAuto.isChecked())
        with open(config.CONFIG_FILE, "w", encoding="utf-8") as f:
            cfg.write(f)

    def choose_file(self, parent=None):
        """Pozwala wybrać wymagany zasób lub opcję."""
        if parent is None:
            parent = self.centralwidget
        path, _unused = QFileDialog.getSaveFileName(
            parent,
            _("Wybierz nazwę pliku kopii"),
            self.lineEdit.text() or "",
            _("Kopie SerwisApp (*.bak);;Wszystkie pliki (*)"),
            options=QFileDialog.DontUseNativeDialog | QFileDialog.DontConfirmOverwrite
        )
        if path and not path.lower().endswith(".bak"):
            path += ".bak"
        if path:
            self.lineEdit.setText(path)
            self.save_last_path(path)

    def create_backup(self):
        """Tworzy wymagany obiekt lub zestaw danych."""
        dst = self.lineEdit.text().strip()
        if not dst:
            QMessageBox.warning(None, _("Błąd"), _("Nieprawidłowa ścieżka do zapisania kopii!"))
            return
        if os.path.exists(dst):
            reply = QMessageBox.question(
                None,
                _("Plik już istnieje"),
                _("Plik {} już istnieje.\nCzy chcesz go nadpisać?").format(dst),
                QMessageBox.Yes | QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return

        self.save_last_path(dst)
        self.progressBar.setValue(0)
        try:
            wykonaj_backup_logika(dst, lambda val: self.progressBar.setValue(val))
            self.progressBar.setValue(100)
            QMessageBox.information(None, _("Sukces"), f"{_('Kopia katalogu została utworzona w:')}\n{dst}")
        except Exception as e:
            QMessageBox.critical(None, _("Błąd"), f"{_('Błąd podczas tworzenia kopii:')}\n{str(e)}")

    # ---------------------- DB Helper Methods ----------------------

    def get_main_app_connection(self):
        """Zwraca wymagane dane lub ustawienia."""
        if hasattr(self.main_window_ref, 'conn'):
            return self.main_window_ref.conn, self.main_window_ref
        parent = self.main_window_ref.parent()
        if parent and hasattr(parent, 'conn'):
            return parent.conn, parent
        return None, None

    def close_db_if_open(self):
        """Realizuje logikę operacji close db if open w klasie Ui_MainWindow."""
        conn, parent_obj = self.get_main_app_connection()
        if conn:
            try:
                conn.close()
                if parent_obj:
                    parent_obj.conn = None
                print("DEBUG: Połączenie z bazą zamknięte.")
                return True, parent_obj
            except Exception as e:
                print(f"Błąd zamykania bazy: {e}")
        return False, None

    def reopen_db(self, parent_obj):
        """Realizuje logikę operacji reopen db w klasie Ui_MainWindow."""
        if parent_obj and hasattr(parent_obj, 'polacz_z_baza'):
            try:
                parent_obj.polacz_z_baza()
                if hasattr(parent_obj, 'odswiez_tabele'):
                    parent_obj.odswiez_tabele()
                if hasattr(parent_obj, 'update_plus_status'):
                    parent_obj.update_plus_status()
                print("DEBUG: Połączenie z bazą przywrócone.")
            except Exception as e:
                print(f"Błąd ponownego łączenia: {e}")
        elif parent_obj:
            try:
                parent_obj.conn = sqlite3.connect(config.DB_FILE)
                parent_obj.c = parent_obj.conn.cursor()
            except sqlite3.Error:
                pass

    # ---------------------- Restore Methods ----------------------

    def restore_backup_action(self):
        """Przywraca dane lub stan z kopii albo konfiguracji."""
        path = self.lineEdit.text().strip()
        if not path or not os.path.exists(path):
            QMessageBox.warning(None, _("Błąd"), _("Nie wskazano pliku kopii lub plik nie istnieje!"))
            return

        reply = QMessageBox.question(
            None,
            _("Potwierdzenie"),
            f"{_('Czy na pewno chcesz przywrócić kopię z pliku:')}\n{path}\n\n"
            f"{_('Obecna baza danych zostanie nadpisana!')}",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply != QtWidgets.QMessageBox.Yes:
            return

        closed, parent_obj = self.close_db_if_open()
        QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
        time.sleep(0.3)
        success = self.restore_backup(path)
        QtWidgets.QApplication.restoreOverrideCursor()

        if closed and parent_obj:
            self.reopen_db(parent_obj)
        if success:
            self.save_last_path(path)

    def restore_backup(self, src):
        """Przywraca dane lub stan z kopii albo konfiguracji."""
        self.progressBar.setValue(0)
        try:
            # Usuń katalog .SerwisApp
            if os.path.exists(APP_DIR):
                for root, dirs, files in os.walk(APP_DIR, topdown=False):
                    for f in files:
                        force_remove_file(os.path.join(root, f))
                    for d in dirs:
                        try:
                            os.rmdir(os.path.join(root, d))
                        except:
                            shutil.rmtree(os.path.join(root, d), ignore_errors=True)
                shutil.rmtree(APP_DIR, ignore_errors=True)

            os.makedirs(APP_DIR, exist_ok=True)

            # Rozpakuj backup
            with zipfile.ZipFile(src, "r") as backup_zip:
                members = backup_zip.namelist()
                total = len(members) or 1
                for i, member in enumerate(members, 1):
                    backup_zip.extract(member, APP_DIR)
                    self.progressBar.setValue(int(i / total * 100))
                    QtWidgets.QApplication.processEvents()

            self.progressBar.setValue(100)
            QMessageBox.information(None, _("Sukces"), _("Backup został przywrócony pomyślnie."))
            return True

        except Exception as e:
            QMessageBox.critical(None, _("Błąd"), f"{_('Błąd podczas przywracania kopii:')}\n{str(e)}")
            return False

# ---------------------- Main ----------------------

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    MainWindow = QtWidgets.QMainWindow()
    ui = Ui_MainWindow()
    ui.setupUi(MainWindow)
    MainWindow.show()
    sys.exit(app.exec())
