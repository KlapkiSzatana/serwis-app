# modules/game.py
import os
import random
from PySide6 import QtWidgets, QtCore, QtGui

# Zabezpieczenie na wypadek uruchamiania modułu niezależnie
try:
    _("Test")
except NameError:
    def _(text):
        """Zwraca tekst bez tłumaczenia, gdy mechanizm i18n nie jest aktywny."""
        return text

# Prosta funkcja do ścieżek do ikon
# --- POPRAWIONA FUNKCJA ŚCIEŻEK ---
def get_img(name):
    # Ustalamy ścieżkę do katalogu, w którym znajduje się ten plik (modules/)
    """Zwraca wymagane dane lub ustawienia."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # Wychodzimy folder wyżej do głównego katalogu aplikacji i wchodzimy do actions/
    base_path = os.path.join(current_dir, "..", "actions")

    # Jeśli plik nie istnieje (np. w specyficznych warunkach instalacji),
    # próbujemy ścieżki absolutnej używanej w Linux
    full_path = os.path.normpath(os.path.join(base_path, name))

    if not os.path.exists(full_path):
        # Ostatnia szansa: sprawdzamy standardową lokalizację systemową
        system_path = f"/usr/share/serwis-app/actions/{name}"
        if os.path.exists(system_path):
            return system_path

    return full_path

# --- ŚCIEŻKI DO NAJWYŻSZYCH WYNIKÓW ---
def get_highscore_path():
    """Zwraca wymagane dane lub ustawienia."""
    dir_path = os.path.expanduser("~/.SerwisApp")
    os.makedirs(dir_path, exist_ok=True)
    return os.path.join(dir_path, "highscore.txt")

def get_highscore_snake_path():
    """Zwraca wymagane dane lub ustawienia."""
    dir_path = os.path.expanduser("~/.SerwisApp")
    os.makedirs(dir_path, exist_ok=True)
    return os.path.join(dir_path, "highscore_snake.txt")


# =========================================================================
# === KLASA WYBORU GRY (GameSelectionDialog) ===
# =========================================================================
class GameSelectionDialog(QtWidgets.QDialog):
    """Dialog obsługujący wydzielony fragment funkcjonalności aplikacji."""
    def __init__(self, parent=None):
        """Inicjalizuje obiekt i przygotowuje jego stan początkowy."""
        super().__init__(parent)
        self.setWindowTitle("Easter Egg SerwisApp - Wybierz Grę")
        self.setFixedSize(500, 300)
        self.setStyleSheet("background-color: #1C2833;")
        self.setWindowFlags(QtCore.Qt.WindowType.Dialog | QtCore.Qt.WindowType.FramelessWindowHint)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.addSpacing(20)

        tytul = QtWidgets.QLabel("Wybierz Wyzwanie:")
        tytul.setFont(QtGui.QFont("Arial", 16, QtGui.QFont.Bold))
        tytul.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(tytul)
        layout.addSpacing(30)

        # Panel przycisków wyboru
        btn_layout = QtWidgets.QHBoxLayout()
        self.btn_mario = QtWidgets.QPushButton("Serwis Mario")
        self.btn_snake = QtWidgets.QPushButton("Klasyczny Snake")

        button_style = """
            QPushButton {
                background-color: #4682B4;
                color: white;
                font-size: 14px;
                font-weight: bold;
                border-radius: 5px;
                padding: 15px;
            }
            QPushButton:hover {
                background-color: #5F9EA0;
            }
        """
        self.btn_mario.setStyleSheet(button_style)
        self.btn_snake.setStyleSheet(button_style)

        btn_layout.addWidget(self.btn_mario)
        btn_layout.addSpacing(30)
        btn_layout.addWidget(self.btn_snake)
        layout.addLayout(btn_layout)

        layout.addSpacing(30)
        btn_close = QtWidgets.QPushButton("Wyjdź do Serwisu")
        btn_close.setStyleSheet("""
            QPushButton {
                background-color: #d9534f;
                color: white;
                font-weight: bold;
                border-radius: 5px;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #c9302c;
            }
        """)
        btn_close.clicked.connect(self.close)
        layout.addWidget(btn_close, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)

        # Kod wyniku wyboru (1 = Mario, 2 = Snake)
        self.wybor = 0

        self.btn_mario.clicked.connect(self.wybierz_mario)
        self.btn_snake.clicked.connect(self.wybierz_snake)

    def wybierz_mario(self):
        """Pozwala wybrać odpowiedni element lub opcję."""
        self.wybor = 1
        self.accept()

    def wybierz_snake(self):
        """Pozwala wybrać odpowiedni element lub opcję."""
        self.wybor = 2
        self.accept()


# =========================================================================
# === KLASA SERWIS MARIO (SerwisMarioDialog) ===
# =========================================================================
class SerwisMarioDialog(QtWidgets.QDialog):
    """Dialog obsługujący wydzielony fragment funkcjonalności aplikacji."""
    def __init__(self, parent=None):
        """Inicjalizuje obiekt i przygotowuje jego stan początkowy."""
        super().__init__(parent)
        self.setWindowTitle("Serwis Mario - Przechwyć zlecenia!")
        self.setFixedSize(800, 400)
        # --- ZMIANA: Lekko ciemniejsze niebo (Stalowo-Niebieskie) ---
        self.setStyleSheet("background-color: #1C2833;")

        self.setWindowFlags(QtCore.Qt.WindowType.Window | QtCore.Qt.WindowType.FramelessWindowHint)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.scene = QtWidgets.QGraphicsScene(0, 0, 800, 400)
        self.view = QtWidgets.QGraphicsView(self.scene)
        self.view.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.view.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.view.setStyleSheet("border: 0px;")
        layout.addWidget(self.view)

        # Fizyka i logika gry
        self.is_jumping = False
        self.gravity = 1.8
        self.jump_velocity = -22
        self.velocity_y = 0
        self.ground_y = 300
        self.score = 0
        self.highscore = self.load_highscore()
        self.game_over = False

        # --- ZMIANA: Lista ikon (usunieto te suspected of having green) ---
        self.standard_icons = [
            "client.png", "firma.png", "baza.png",
            "kopiuj.png", "smsconf.png", "email.png",
            " template.png", "all.png", "actualizacja.png",
            "aktywacja.png", "detale.png", "duplikuj.png",
            "edycja.png"
        ]

        self.init_game()

    def load_highscore(self):
        """Wczytuje dane lub ustawienia potrzebne do działania."""
        path = get_highscore_path()
        if os.path.exists(path):
            try:
                with open(path, "r") as f:
                    return int(f.read().strip())
            except:
                return 0
        return 0

    def save_highscore(self):
        """Zapisuje dane lub ustawienia."""
        path = get_highscore_path()
        try:
            with open(path, "w") as f:
                f.write(str(self.highscore))
        except:
            pass

    def init_game(self):
        """Inicjalizuje wymagane zasoby lub strukturę danych."""
        self.scene.clear()
        self.score = 0
        self.game_speed = 10
        self.game_over = False
        self.obstacles = []
        self.coins = []

        self.scene.addRect(0, self.ground_y + 40, 800, 60, QtGui.QPen(QtCore.Qt.NoPen), QtGui.QBrush(QtGui.QColor("#228B22")))

        # Poprawiona ścieżka do ikonki głównej (często jest w resources lub actions)
        player_img = get_img("serwisapp.png")
        if not os.path.exists(player_img):
            # Fallback jeśli w actions nie ma ikony głównej
            player_img = get_img("../resources/logo/serwisapp.png")

        pixmap_player = QtGui.QPixmap(player_img).scaled(40, 40, QtCore.Qt.AspectRatioMode.KeepAspectRatio, QtCore.Qt.TransformationMode.SmoothTransformation)
        self.player = self.scene.addPixmap(pixmap_player)
        self.player.setPos(50, self.ground_y)

        self.score_text = self.scene.addText(f"Punkty: {self.score} | Rekord: {self.highscore}")
        self.score_text.setFont(QtGui.QFont("Courier", 16, QtGui.QFont.Bold))
        self.score_text.setDefaultTextColor(QtCore.Qt.GlobalColor.white)
        self.score_text.setPos(10, 10)

        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.game_loop)
        self.timer.start(30)

        self.spawn_timer = 0

    def game_loop(self):
        """Wykonuje pojedynczą iterację pętli gry."""
        if self.game_over:
            return

        if self.is_jumping:
            self.velocity_y += self.gravity
            new_y = self.player.y() + self.velocity_y
            if new_y >= self.ground_y:
                new_y = self.ground_y
                self.is_jumping = False
                self.velocity_y = 0
            self.player.setY(new_y)

        # Przyspieszenie gry
        przelicznik_predkosci = max(0, self.score) // 100
        self.game_speed = min(10 + przelicznik_predkosci * 2, 28)

        self.spawn_timer += 1
        spawn_limit = max(15, 45 - (self.game_speed - 10))

        if self.spawn_timer > spawn_limit:
            self.spawn_timer = 0
            if random.random() > 0.4:
                self.spawn_enemy()
            else:
                self.spawn_coin()

        # Przeszkody (Robale - śmiertelne)
        for obs in self.obstacles[:]:
            obs.setX(obs.x() - self.game_speed)
            if obs.x() < -50:
                self.scene.removeItem(obs)
                self.obstacles.remove(obs)
                self.score += 10 # 10 pkt za przeskoczenie wirusa
                self.update_score_text()
            elif self.player.collidesWithItem(obs):
                self.end_game()

        # Znajdźki (Różne ikony, bonusy i kary)
        for coin in self.coins[:]:
            coin.setX(coin.x() - self.game_speed)
            if coin.x() < -50:
                self.scene.removeItem(coin)
                self.coins.remove(coin)
            elif self.player.collidesWithItem(coin):
                self.scene.removeItem(coin)
                self.coins.remove(coin)

                coin_type = coin.data(0)
                if coin_type == "bonus":
                    self.score += 100
                elif coin_type == "penalty":
                    self.score -= 500
                else:
                    self.score += 50

                self.update_score_text()

    def update_score_text(self):
        """Odświeża tekst prezentujący aktualny wynik."""
        self.score_text.setPlainText(f"Punkty: {self.score} | Rekord: {self.highscore}")

    def spawn_enemy(self):
        """Tworzy nowy obiekt w logice gry lub interfejsu."""
        pixmap = QtGui.QPixmap(get_img("robal.png")).scaled(35, 35, QtCore.Qt.AspectRatioMode.KeepAspectRatio, QtCore.Qt.TransformationMode.SmoothTransformation)
        enemy = self.scene.addPixmap(pixmap)
        enemy.setPos(800, self.ground_y + 5)
        self.obstacles.append(enemy)

    def spawn_coin(self):
        """Tworzy nowy obiekt w logice gry lub interfejsu."""
        los = random.random()

        if los < 0.15:
            # 15% szans na karę (-500)
            icon_name = "refresh.png"
            coin_type = "penalty"
        elif los < 0.30:
            # 15% szans na bonus (+100)
            icon_name = "new.png"
            coin_type = "bonus"
        else:
            # 70% szans na zwykłą ikonkę (+50)
            icon_name = random.choice(self.standard_icons)
            coin_type = "standard"

        pixmap = QtGui.QPixmap(get_img(icon_name)).scaled(30, 30, QtCore.Qt.AspectRatioMode.KeepAspectRatio, QtCore.Qt.TransformationMode.SmoothTransformation)
        coin = self.scene.addPixmap(pixmap)
        coin.setData(0, coin_type)
        coin.setPos(800, self.ground_y - 80 - random.randint(0, 40))
        self.coins.append(coin)

    def end_game(self):
        """Kończy bieżącą rozgrywkę i zapisuje wynik."""
        self.game_over = True
        self.timer.stop()

        nowy_rekord = False
        if self.score > self.highscore:
            self.highscore = self.score
            self.save_highscore()
            nowy_rekord = True

        bg = self.scene.addRect(0, 0, 800, 400, QtGui.QPen(QtCore.Qt.NoPen), QtGui.QBrush(QtGui.QColor(0, 0, 0, 180)))

        tekst_konca = "KONIEC OPIERDALANIA!\n\n"
        if nowy_rekord:
            tekst_konca += f"NOWY REKORD: {self.score}!\n\n"
        else:
            tekst_konca += f"Twój wynik: {self.score}\n\n"

        tekst_konca += "Uderz SPACJĘ, by zrestartować\nlub ESC, by wrócić do pracy."

        game_over_text = self.scene.addText(tekst_konca)
        game_over_text.setFont(QtGui.QFont("Courier", 18, QtGui.QFont.Bold))

        if nowy_rekord:
            game_over_text.setDefaultTextColor(QtCore.Qt.GlobalColor.yellow)
        else:
            game_over_text.setDefaultTextColor(QtCore.Qt.GlobalColor.white)

        game_over_text.setPos(400 - game_over_text.boundingRect().width() / 2, 100)

    def keyPressEvent(self, event):
        """Obsługuje naciśnięcie klawisza."""
        if event.key() == QtCore.Qt.Key.Key_Escape:
            self.close()
        elif event.key() == QtCore.Qt.Key.Key_Space or event.key() == QtCore.Qt.Key.Key_Up:
            if self.game_over:
                self.init_game()
            elif not self.is_jumping:
                self.is_jumping = True
                self.velocity_y = self.jump_velocity


# =========================================================================
# === KLASA SERWIS SNAKE (SerwisSnakeDialog) ===
# =========================================================================
class SerwisSnakeDialog(QtWidgets.QDialog):
    """Dialog obsługujący wydzielony fragment funkcjonalności aplikacji."""
    def __init__(self, parent=None):
        """Inicjalizuje obiekt i przygotowuje jego stan początkowy."""
        super().__init__(parent)
        self.setWindowTitle("Klasyczny Snake - Zjadaj Robale!")
        self.setFixedSize(800, 400)
        # Zdecydowanie ciemniejsze tło dla lepszego kontrastu
        self.setStyleSheet("background-color: #1C2833;")
        self.setWindowFlags(QtCore.Qt.WindowType.Window | QtCore.Qt.WindowType.FramelessWindowHint)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.scene = QtWidgets.QGraphicsScene(0, 0, 800, 400)
        self.view = QtWidgets.QGraphicsView(self.scene)
        self.view.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.view.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.view.setStyleSheet("border: 0px;")
        # Odbieramy focus, żeby widok nie pożerał kliknięć strzałek!
        self.view.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        layout.addWidget(self.view)

        self.grid_size = 20
        self.rows = 20
        self.cols = 40
        self.score = 0
        self.highscore = self.load_highscore_snake()
        self.game_over = False

        self.direction = QtCore.Qt.Key.Key_Right
        self.next_direction = self.direction

        self.snake_body_icons = [
            "client.png", "firma.png", "baza.png",
            "edit.png", "kopiuj.png", "email.png",
            "template.png", "all.png", "actualizacja.png",
            "aktywacja.png", "smsconf.png", "details.png",
            "duplikuj.png"
        ]

        self.init_game()

    def load_highscore_snake(self):
        """Wczytuje dane lub ustawienia potrzebne do działania."""
        path = get_highscore_snake_path()
        if os.path.exists(path):
            try:
                with open(path, "r") as f:
                    return int(f.read().strip())
            except:
                return 0
        return 0

    def save_highscore_snake(self):
        """Zapisuje dane lub ustawienia."""
        path = get_highscore_snake_path()
        try:
            with open(path, "w") as f:
                f.write(str(self.highscore))
        except:
            pass

    def init_game(self):
        """Inicjalizuje wymagane zasoby lub strukturę danych."""
        self.scene.clear()

        # Rysujemy wyraźną ramkę obszaru roboczego węża
        pen = QtGui.QPen(QtGui.QColor("white"))
        pen.setWidth(2)
        self.scene.addRect(1, 40, 798, 358, pen, QtGui.QBrush(QtCore.Qt.BrushStyle.NoBrush))

        self.score = 0
        self.game_over = False
        self.direction = QtCore.Qt.Key.Key_Right
        self.next_direction = self.direction

        self.head = self.spawn_segment("serwisapp.png", 5, 10)
        self.snake = [self.head]

        for i in range(1, 4):
            icon_name = random.choice(self.snake_body_icons)
            segment = self.spawn_segment(icon_name, 5 - i, 10)
            self.snake.append(segment)

        self.food = None
        self.spawn_food()

        # Zmienne dla bonusu (new.png)
        self.bonus_food = None
        self.bonus_timer = 0

        self.score_text = self.scene.addText(f"Robale: {self.score} | Rekord: {self.highscore}")
        self.score_text.setFont(QtGui.QFont("Courier", 16, QtGui.QFont.Bold))
        self.score_text.setDefaultTextColor(QtCore.Qt.GlobalColor.white)
        self.score_text.setPos(10, 10)

        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.game_loop)
        self.timer.start(100)

    def spawn_segment(self, icon_name, col, row):
        """Tworzy nowy obiekt w logice gry lub interfejsu."""
        pixmap = QtGui.QPixmap(get_img(icon_name)).scaled(self.grid_size, self.grid_size, QtCore.Qt.AspectRatioMode.KeepAspectRatio, QtCore.Qt.TransformationMode.SmoothTransformation)
        segment = self.scene.addPixmap(pixmap)
        segment.setPos(col * self.grid_size, row * self.grid_size)
        return segment

    def spawn_food(self):
        """Tworzy nowy obiekt w logice gry lub interfejsu."""
        if self.food:
            self.scene.removeItem(self.food)
            self.food = None

        while True:
            food_col = random.randint(0, self.cols - 1)
            food_row = random.randint(2, self.rows - 1)

            spawn_on_snake = any(segment.x() == food_col * self.grid_size and segment.y() == food_row * self.grid_size for segment in self.snake)

            if not spawn_on_snake:
                break

        pixmap = QtGui.QPixmap(get_img("robal.png")).scaled(self.grid_size, self.grid_size, QtCore.Qt.AspectRatioMode.KeepAspectRatio, QtCore.Qt.TransformationMode.SmoothTransformation)
        self.food = self.scene.addPixmap(pixmap)
        self.food.setPos(food_col * self.grid_size, food_row * self.grid_size)

    def spawn_bonus_food(self):
        """Tworzy nowy obiekt w logice gry lub interfejsu."""
        if self.bonus_food:
            self.scene.removeItem(self.bonus_food)

        self.bonus_timer = 0

        while True:
            col = random.randint(0, self.cols - 1)
            row = random.randint(2, self.rows - 1)

            spawn_on_snake = any(seg.x() == col * self.grid_size and seg.y() == row * self.grid_size for seg in self.snake)
            overlap_food = (self.food and self.food.x() == col * self.grid_size and self.food.y() == row * self.grid_size)

            if not spawn_on_snake and not overlap_food:
                break

        pixmap = QtGui.QPixmap(get_img("new.png")).scaled(self.grid_size, self.grid_size, QtCore.Qt.AspectRatioMode.KeepAspectRatio, QtCore.Qt.TransformationMode.SmoothTransformation)
        self.bonus_food = self.scene.addPixmap(pixmap)
        self.bonus_food.setPos(col * self.grid_size, row * self.grid_size)

    def game_loop(self):
        """Wykonuje pojedynczą iterację pętli gry."""
        if self.game_over:
            return

        # Zarządzanie bonusem czasowym
        if self.bonus_food:
            self.bonus_timer += 1
            if self.bonus_timer >= 100: # 100 ticków * 100ms = 10 sekund
                self.scene.removeItem(self.bonus_food)
                self.bonus_food = None
        else:
            # 2% szans co klatkę na pojawienie się bonusu
            if random.random() < 0.02:
                self.spawn_bonus_food()

        self.direction = self.next_direction
        self.move_snake()

    def move_snake(self):
        """Przesuwa węża zgodnie z aktualnym kierunkiem ruchu."""
        head = self.snake[0]
        new_x = head.x()
        new_y = head.y()

        if self.direction == QtCore.Qt.Key.Key_Up:
            new_y -= self.grid_size
        elif self.direction == QtCore.Qt.Key.Key_Down:
            new_y += self.grid_size
        elif self.direction == QtCore.Qt.Key.Key_Left:
            new_x -= self.grid_size
        elif self.direction == QtCore.Qt.Key.Key_Right:
            new_x += self.grid_size

        if new_x < 0 or new_x >= 800 or new_y < self.grid_size * 2 or new_y >= 400:
            self.end_game()
            return

        for segment in self.snake[1:-1]:
            if segment.x() == new_x and segment.y() == new_y:
                self.end_game()
                return

        is_food_eaten = (new_x == self.food.x() and new_y == self.food.y())
        is_bonus_eaten = (self.bonus_food and new_x == self.bonus_food.x() and new_y == self.bonus_food.y())

        if is_food_eaten or is_bonus_eaten:
            if is_bonus_eaten:
                self.score += 50    # <--- ZMIANA: Bonus daje 50 punktów
                self.scene.removeItem(self.bonus_food)
                self.bonus_food = None
            else:
                self.score += 1     # <--- ZMIANA: Zwykły robal daje 1 punkt
                self.spawn_food()

            self.update_score_text()

            icon_name = random.choice(self.snake_body_icons)
            new_segment = self.spawn_segment(icon_name, head.x() / self.grid_size, head.y() / self.grid_size)
            self.snake.insert(1, new_segment)
            head.setPos(new_x, new_y)
        else:
            for i in range(len(self.snake) - 1, 0, -1):
                pos_przed = self.snake[i-1].pos()
                self.snake[i].setPos(pos_przed)

            head.setPos(new_x, new_y)

    def update_score_text(self):
        """Odświeża tekst prezentujący aktualny wynik."""
        self.score_text.setPlainText(f"Robale: {self.score} | Rekord: {self.highscore}")

    def end_game(self):
        """Kończy bieżącą rozgrywkę i zapisuje wynik."""
        self.game_over = True
        self.timer.stop()

        nowy_rekord = False
        if self.score > self.highscore:
            self.highscore = self.score
            self.save_highscore_snake()
            nowy_rekord = True

        bg = self.scene.addRect(0, 0, 800, 400, QtGui.QPen(QtCore.Qt.NoPen), QtGui.QBrush(QtGui.QColor(0, 0, 0, 200)))

        tekst_konca = "KONIEC OPIERDALANIA!\n\n"
        if nowy_rekord:
            tekst_konca += f"NOWY REKORD: {self.score}!\n\n"
        else:
            tekst_konca += f"Punkty: {self.score}\n\n"

        tekst_konca += "Uderz SPACJĘ, by zrestartować\nlub ESC, by wrócić do pracy."

        game_over_text = self.scene.addText(tekst_konca)
        game_over_text.setFont(QtGui.QFont("Courier", 18, QtGui.QFont.Bold))

        if nowy_rekord:
            game_over_text.setDefaultTextColor(QtCore.Qt.GlobalColor.yellow)
        else:
            game_over_text.setDefaultTextColor(QtCore.Qt.GlobalColor.white)

        game_over_text.setPos(400 - game_over_text.boundingRect().width() / 2, 100)

    def keyPressEvent(self, event):
        """Obsługuje naciśnięcie klawisza."""
        key = event.key()
        if key == QtCore.Qt.Key.Key_Escape:
            self.close()
        elif key == QtCore.Qt.Key.Key_Space:
            if self.game_over:
                self.init_game()
        elif not self.game_over:
            if key == QtCore.Qt.Key.Key_Up and self.direction != QtCore.Qt.Key.Key_Down:
                self.next_direction = QtCore.Qt.Key.Key_Up
            elif key == QtCore.Qt.Key.Key_Down and self.direction != QtCore.Qt.Key.Key_Up:
                self.next_direction = QtCore.Qt.Key.Key_Down
            elif key == QtCore.Qt.Key.Key_Left and self.direction != QtCore.Qt.Key.Key_Right:
                self.next_direction = QtCore.Qt.Key.Key_Left
            elif key == QtCore.Qt.Key.Key_Right and self.direction != QtCore.Qt.Key.Key_Left:
                self.next_direction = QtCore.Qt.Key.Key_Right
