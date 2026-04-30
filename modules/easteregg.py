# modules/easteregg.py
from PySide6 import QtWidgets, QtCore, QtGui
import random
import math

class Particle:
    """Klasa pomocnicza używana przez aplikację."""
    def __init__(self, x, y, color, speed_range=(2, 7), life_speed=5):
        """Inicjalizuje obiekt i przygotowuje jego stan początkowy."""
        self.x = x
        self.y = y
        self.color = color
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(*speed_range)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.alpha = 255
        self.gravity = 0.1
        self.life_speed = life_speed

    def update(self):
        """Realizuje logikę operacji update w klasie Particle."""
        self.x += self.vx
        self.y += self.vy
        self.vy += self.gravity
        self.alpha -= self.life_speed
        return self.alpha > 0

class EasterEggDialog(QtWidgets.QDialog):
    """Dialog obsługujący wydzielony fragment funkcjonalności aplikacji."""
    def __init__(self, parent=None):
        """Inicjalizuje obiekt i przygotowuje jego stan początkowy."""
        super().__init__(parent)
        self.setFixedSize(800, 600)
        self.setStyleSheet("background-color: black;")
        self.setWindowFlags(QtCore.Qt.WindowType.Window | QtCore.Qt.WindowType.FramelessWindowHint)

        self.stars = [QtCore.QPoint(random.randint(0, 800), random.randint(0, 600)) for _ in range(150)]
        self.particles = []

        # 1. Tekst główny
        tekst_glowny = (
            "W ODLEGŁEJ GALAKTYCE, DALEKO...\n\n"
            "A właściwie to tutaj, na Arch Linuksie.\n\n"
            "Ten program to dzieło potężnego administratora, 😉\n"
            "który ujarzmił Pythona, okienka i bazy danych.\n\n"
            "Niestraszne mu były błędy KIO,\n"
            "uparte drukarki Brothera, 😡\n"
            "ani wirtualne foldery Samby dławiące VLC. 😆\n\n"
            "Zbudował cenniki, raporty finansowe i...\n\n"
            "zhakował Plasmę. 😜\n\n"
            "NIECH PROGRAM CI SŁUŻY!"
        )

        self.label = QtWidgets.QLabel(tekst_glowny, self)
        self.label.setStyleSheet("color: #FFE81F; font-size: 24px; font-weight: bold;")
        self.label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.label.setFixedWidth(700)
        self.label.adjustSize()
        self.scroll_y = 650
        self.label.move(50, self.scroll_y)

        # 2. Napis zapowiadający
        self.intro_label = QtWidgets.QLabel("SPECJALNE PODZIĘKOWANIA DLA:", self)
        self.intro_label.setStyleSheet("color: white; font-size: 32px; font-weight: bold;")
        self.intro_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.intro_label.setFixedWidth(800)
        self.intro_label.hide()

        # 3. Napis końcowy (będzie animowany przez opacity)
        self.thanks_label = QtWidgets.QLabel("DZIĘKUJĘ", self)
        self.thanks_label.setStyleSheet("color: #FFE81F; font-size: 90px; font-weight: bold; background: transparent;")
        self.thanks_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.thanks_label.setFixedWidth(800)
        self.thanks_label.move(0, 240)
        self.thanks_label.hide()

        # Efekt przezroczystości dla napisu końcowego
        self.thanks_opacity = QtWidgets.QGraphicsOpacityEffect(self.thanks_label)
        self.thanks_label.setGraphicsEffect(self.thanks_opacity)
        self.thanks_opacity.setOpacity(0.0)

        # 4. Podziękowania specjalne
        self.special_guests = [
            {"tekst": "❤️ DLA ŻONY ELŻBIETY ❤️\n\nZa ogromną wyrozumiałość\nprzez te wszystkie noce przy klawiaturze!😉", "kolor": "#FF69B4"},
            {"tekst": "🧸 DLA CÓRECZKI ZUZANNY ❤️\n\nZa spokojny sen,\ngdy tata klikał po nocach!", "kolor": "#00BFFF"}
        ]

        self.current_guest_idx = 0
        self.finale_started = False
        self.show_fireworks = False

        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.update_all)
        self.timer.start(20)

    def update_all(self):
        # Przesuwanie tekstu głównego
        """Aktualizuje stan danych lub interfejsu."""
        self.scroll_y -= 1
        self.label.move(50, self.scroll_y)

        # Trigger podziękowań (gdy dół tekstu minie połowę)
        bottom_of_text = self.scroll_y + self.label.height()
        if bottom_of_text < 300 and not self.finale_started:
            self.finale_started = True
            self.start_intro_sequence()

        # Obsługa cząsteczek
        if self.show_fireworks or self.particles:
            if self.show_fireworks and random.random() > 0.8:
                self.create_explosion(random.randint(100, 700), random.randint(100, 400))

            for p in self.particles[:]:
                if not p.update():
                    self.particles.remove(p)

        self.update()

    def create_explosion(self, x, y, count=30, speed_range=(2, 7), color=None):
        """Tworzy efekt eksplozji w wskazanym miejscu."""
        if not color:
            colors = [QtGui.QColor("#FFE81F"), QtGui.QColor("#FF69B4"), QtGui.QColor("#00BFFF"), QtGui.QColor("#FFFFFF")]
            color = random.choice(colors)
        for _ in range(count):
            self.particles.append(Particle(x, y, color, speed_range))

    def start_intro_sequence(self):
        """Uruchamia sekwencję wprowadzającą animacji."""
        self.intro_label.show()
        anim = QtCore.QSequentialAnimationGroup(self)

        in_anim = QtCore.QPropertyAnimation(self.intro_label, b"pos")
        in_anim.setDuration(1000)
        in_anim.setStartValue(QtCore.QPoint(0, 650))
        in_anim.setEndValue(QtCore.QPoint(0, 250))
        in_anim.setEasingCurve(QtCore.QEasingCurve.Type.OutBack)

        out_anim = QtCore.QPropertyAnimation(self.intro_label, b"pos")
        out_anim.setDuration(800)
        out_anim.setStartValue(QtCore.QPoint(0, 250))
        out_anim.setEndValue(QtCore.QPoint(0, -200))
        out_anim.setEasingCurve(QtCore.QEasingCurve.Type.InCubic)

        anim.addAnimation(in_anim)
        anim.addPause(1500)
        anim.addAnimation(out_anim)
        anim.finished.connect(self.start_guest_sequence)
        anim.start()

    def start_guest_sequence(self):
        """Uruchamia sekwencję z dodatkowymi postaciami."""
        if self.current_guest_idx >= len(self.special_guests):
            self.start_grand_finale()
            return

        config = self.special_guests[self.current_guest_idx]
        lbl = QtWidgets.QLabel(config["tekst"], self)
        lbl.setStyleSheet(f"color: {config['kolor']}; font-size: 26px; font-weight: bold; background: rgba(10,10,10,240); border: 4px solid {config['kolor']}; border-radius: 25px; padding: 40px;")
        lbl.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        lbl.setFixedWidth(660); lbl.adjustSize(); lbl.move(70, 700); lbl.show()

        anim = QtCore.QSequentialAnimationGroup(self)
        v_in = QtCore.QPropertyAnimation(lbl, b"pos")
        v_in.setDuration(1100); v_in.setStartValue(QtCore.QPoint(70, 650)); v_in.setEndValue(QtCore.QPoint(70, 200))
        v_in.setEasingCurve(QtCore.QEasingCurve.Type.OutBack)

        v_out = QtCore.QPropertyAnimation(lbl, b"pos")
        v_out.setDuration(800); v_out.setStartValue(QtCore.QPoint(70, 200)); v_out.setEndValue(QtCore.QPoint(70, -500))
        v_out.setEasingCurve(QtCore.QEasingCurve.Type.InBack)

        anim.addAnimation(v_in); anim.addPause(2800); anim.addAnimation(v_out)
        anim.finished.connect(lbl.deleteLater)
        anim.finished.connect(self.next_guest)
        anim.start()

    def next_guest(self):
        """Przechodzi do kolejnego etapu sekwencji animacji."""
        self.current_guest_idx += 1
        self.start_guest_sequence()

    def start_grand_finale(self):
        # 1. Wielka eksplozja na środku
        """Uruchamia końcową sekwencję animacji."""
        self.create_explosion(400, 300, count=150, speed_range=(4, 15))

        # 2. Pojawienie się napisu DZIĘKUJĘ
        self.thanks_label.show()
        self.show_fireworks = True

        # Animacja zanikania eksplozji i pojawiania się napisu
        self.fade_anim = QtCore.QPropertyAnimation(self.thanks_opacity, b"opacity")
        self.fade_anim.setDuration(1500)
        self.fade_anim.setStartValue(0.0)
        self.fade_anim.setEndValue(1.0)
        self.fade_anim.start()

        # Zamknij po 6 sekundach pokazu
        QtCore.QTimer.singleShot(6000, self.close)

    def paintEvent(self, event):
        """Rysuje zawartość widżetu."""
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)

        # Gwiazdy
        painter.setPen(QtGui.QColor(100, 100, 100))
        for star in self.stars:
            painter.drawPoint(star)

        # Rysowanie fajerwerków
        for p in self.particles:
            color = QtGui.QColor(p.color)
            color.setAlpha(p.alpha)
            painter.setPen(QtCore.Qt.PenStyle.NoPen)
            painter.setBrush(color)
            painter.drawEllipse(QtCore.QPointF(p.x, p.y), 2.5, 2.5)

    def mousePressEvent(self, event):
        """Obsługuje naciśnięcie przycisku myszy."""
        self.close()

    def keyPressEvent(self, event):
        """Obsługuje naciśnięcie klawisza."""
        if event.key() == QtCore.Qt.Key.Key_Escape:
            self.close()
