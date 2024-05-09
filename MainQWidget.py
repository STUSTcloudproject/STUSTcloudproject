from PyQt5.QtWidgets import QApplication, QWidget, QHBoxLayout, QVBoxLayout
from PyQt5.QtGui import QColor, QPalette
from PyQt5.QtCore import QSize, Qt
from ContentSplitterWidget import ContentSplitterWidget
from ColoredWidget import ColoredWidget

class MainQWidget(QWidget):
    def __init__(self, parent=None, colors=("blue", "green", "yellow"), sizes=(70, 200, 600), orientations=(Qt.Horizontal, Qt.Horizontal), fixed_panel='first'):
        super().__init__(parent)
        self.colors = {"panel1": QColor(colors[0]), "splitter1": QColor(colors[1]), "splitter2": QColor(colors[2])}
        self.panel_pixel = sizes[0]
        self.initial_sizes = (sizes[1], sizes[2])
        self.splitter_orientation, self.layout_orientation = orientations
        self.fixed_panel = fixed_panel

        self.setupLayout()

    def setupLayout(self):
        self.layout = QHBoxLayout(self) if self.layout_orientation == Qt.Horizontal else QVBoxLayout(self)
        self.setZeroMarginsAndSpacing(self.layout)

        self.panel1 = ColoredWidget(self.colors["panel1"], self.panel_pixel, self.layout_orientation, self)
        self.panel2 = ContentSplitterWidget(self, orientation=self.splitter_orientation, fixed_panel=self.fixed_panel, initial_sizes=self.initial_sizes, colors=(self.colors["splitter1"], self.colors["splitter2"]))

        self.layout.addWidget(self.panel1)
        self.layout.addWidget(self.panel2, 1)

    def setZeroMarginsAndSpacing(self, layout):
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

    def get_panel1(self):
        return self.panel1

    def get_panel2(self):
        return self.panel2