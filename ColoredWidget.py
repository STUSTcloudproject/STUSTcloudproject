from PyQt5.QtWidgets import QWidget, QHBoxLayout
from PyQt5.QtGui import QPalette
from PyQt5.QtCore import Qt

class ColoredWidget(QWidget):
    def __init__(self, color, size=None, orientation=Qt.Horizontal, parent=None):
        super().__init__(parent)
        self.setPalette(self.get_palette(color))
        self.setAutoFillBackground(True)
        if size is not None:
            if orientation == Qt.Horizontal:
                self.setFixedWidth(size)
            else:
                self.setFixedHeight(size)
        self.setup_layout()

    def setup_layout(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.setLayout(layout)

    def get_palette(self, color):
        palette = QPalette()
        palette.setColor(QPalette.Window, color)
        return palette
