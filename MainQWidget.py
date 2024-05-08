from PyQt5.QtWidgets import QApplication, QWidget, QHBoxLayout, QVBoxLayout
from PyQt5.QtGui import QColor, QPalette
from PyQt5.QtCore import QSize, Qt
from ContentSplitterWidget import ContentSplitterWidget

class MainQWidget(QWidget):
    def __init__(self, parent=None, panel1_color=QColor("blue"), panel1_pixel=70, 
                 splitter_orientation=Qt.Horizontal, layout_orientation=Qt.Horizontal, fixed_panel='first', initial_sizes=(200, 600)):
        super().__init__(parent)
        self.panel1_color = panel1_color
        self.panel1_pixel = panel1_pixel
        self.splitter_orientation = splitter_orientation
        self.layout_orientation = layout_orientation
        self.fixed_panel = fixed_panel
        self.initial_sizes = initial_sizes
        self.setupLayout()

    def setupLayout(self):
        if self.layout_orientation == Qt.Horizontal:
            self.layout = QHBoxLayout(self)
        else:
            self.layout = QVBoxLayout(self)
        self.setZeroMarginsAndSpacing(self.layout)

        self.panel1 = self.create_colored_widget(self.panel1_color, self.panel1_pixel)

        self.panel2 = ContentSplitterWidget(self, 
                                            orientation=self.splitter_orientation, 
                                            fixed_panel=self.fixed_panel, 
                                            initial_sizes=self.initial_sizes
                                            )
        
        self.layout.addWidget(self.panel1)
        self.layout.addWidget(self.panel2, 1)

    def create_colored_widget(self, color, panel1_pixel=None):
        widget = QWidget()
        palette = QPalette()
        palette.setColor(QPalette.Window, color)
        widget.setPalette(palette)
        widget.setAutoFillBackground(True)
        if panel1_pixel is not None:
            if self.layout_orientation == Qt.Horizontal:
                widget.setFixedWidth(panel1_pixel)
            else:
                widget.setFixedHeight(panel1_pixel)

        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        widget.setLayout(layout)

        return widget

    def setZeroMarginsAndSpacing(self, layout):
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

    def get_panel1(self):
        return self.panel1

    def get_panel2(self):
        return self.panel2