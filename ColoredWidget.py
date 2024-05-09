from PyQt5.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout
from PyQt5.QtGui import QPalette
from PyQt5.QtCore import Qt

class ColoredWidget(QWidget):
    def __init__(self, color, size=None, orientation=Qt.Horizontal, add_position=None, parent=None):
        super().__init__(parent)
        self.orientation = orientation
        self.add_position = add_position
        self.setPalette(self.get_palette(color))
        self.setAutoFillBackground(True)

        if size is not None:
            if orientation == Qt.Horizontal:
                self.setFixedHeight(size)
            else:
                self.setFixedWidth(size)
                
        self.setup_layout()

    def setup_layout(self):
        if self.orientation == Qt.Horizontal:
            self.layout = QHBoxLayout(self)
        else:
            self.layout = QVBoxLayout(self)

        # Only set alignment if add_position is specified
        if self.add_position is not None:
            if self.orientation == Qt.Horizontal:
                if self.add_position == Qt.AlignRight:
                    self.layout.setAlignment(Qt.AlignRight)
                else:
                    self.layout.setAlignment(Qt.AlignLeft)
            else:
                if self.add_position == Qt.AlignBottom:
                    self.layout.setAlignment(Qt.AlignBottom)
                else:
                    self.layout.setAlignment(Qt.AlignTop)

        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

    def get_palette(self, color):
        palette = QPalette()
        palette.setColor(QPalette.Window, color)
        return palette

    def addToLayout(self, widget):
        """Adds a widget to the layout of this ColoredWidget."""
        self.layout.addWidget(widget)

    def removeAllWidgets(self):
        """Removes all widgets from the layout."""
        while self.layout.count():
            child = self.layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def countWidgets(self):
        """Returns the number of widgets in the layout."""
        return self.layout.count()

    def setColor(self, color):
        """Sets the background color of the widget."""
        self.setPalette(self.get_palette(color))
