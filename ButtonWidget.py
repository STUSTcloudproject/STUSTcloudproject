from PyQt5.QtWidgets import QPushButton
from PyQt5.QtGui import QIcon, QColor
from PyQt5.QtCore import Qt
from ColoredWidget import ColoredWidget

class ButtonWidget(ColoredWidget):
    def __init__(self, name, owner, color,icon=None, callback=None, size=None, orientation=Qt.Horizontal, add_position=None, parent=None):
        super().__init__(QColor(color), size, orientation, add_position, parent)
        self.owner = owner
        self.name = name
        self.button = QPushButton("")
        self.button.setFixedSize(size, size)
        if callback:
            self.button.clicked.connect(lambda: self._emit_button_info(callback))

        if icon:
            self.button.setIcon(QIcon(icon))
        
        self.addToLayout(self.button)

    def _emit_button_info(self, callback):
        """Emit button information through callback."""
        info = {'name': self.name, 'owner': self.owner}
        callback(info)  # Call the callback with the info dictionary

    def setButtonIcon(self, icon):
        self.button.setIcon(QIcon(icon))

    def setButtonCallback(self, callback):
        self.button.clicked.connect(callback)
