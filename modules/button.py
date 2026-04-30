from PySide6 import QtWidgets

class MyPushButton(QtWidgets.QPushButton):
    """Klasa pomocnicza używana przez aplikację."""
    def __init__(self, text="", parent=None):
        """Inicjalizuje obiekt i przygotowuje jego stan początkowy."""
        super().__init__(text, parent)
        self.setStyleSheet("""
            QPushButton {
                border-radius: 6px;
                padding: 6px 12px;
                border: 1px solid palette(mid); /* używa systemowego koloru */
            }
            QPushButton:hover {
                border: 1px solid palette(highlight);
                background-color: palette(button); /* lekko podświetla systemowo */
            }
            QPushButton:pressed {
                border: 1px solid palette(dark);
                background-color: palette(button); /* ciut ciemniejsze po kliknięciu */
            }
        """)

