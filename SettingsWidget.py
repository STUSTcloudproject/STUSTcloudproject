from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel
from PyQt5.QtGui import QFont, QColor
from ColoredWidget import ColoredWidget
from PyQt5.QtCore import Qt

class SettingsWidget(QWidget):
    def __init__(self, title, description, parent=None):
        super().__init__(parent)
        self.unselected_color = QColor(200, 200, 200)
        self.selected_color = QColor(0, 120, 215)  # Bright blue
        self.title = title
        self.is_selected = False  # Initial state is unselected
        self.setup_layout()
        self.setup_left_widget(title, description)
        self.setup_right_widget()

    def setup_layout(self):
        self.layout = QHBoxLayout(self)
        self.setStyleSheet("background-color: transparent;")

    def setup_left_widget(self, title, description):
        self.left_widget = ColoredWidget(parent=self, orientation=Qt.Vertical)
        titleLabel = self.create_label(title, 14, True, "white")
        descriptionLabel = self.create_label(description, 10, False, "white")
        self.left_widget.addToLayout(titleLabel)
        self.left_widget.addToLayout(descriptionLabel)
        self.layout.addWidget(self.left_widget)

    def setup_right_widget(self):
        self.right_widget = ColoredWidget(parent=self, orientation=Qt.Vertical)
        self.update_right_widget_color()
        spaceLabel = QLabel("", self)
        spaceLabel.setFixedWidth(5)
        self.right_widget.addToLayout(spaceLabel)
        self.layout.addStretch(1)
        self.layout.addWidget(self.right_widget)

    def create_label(self, text, point_size, bold, color):
        label = QLabel(text, self)
        font = QFont()
        font.setPointSize(point_size)
        font.setBold(bold)
        font.setFamily("Consolas, 'Courier New', 'Lucida Console', monospace")
        label.setFont(font)
        label.setStyleSheet(f"color: {color};")
        return label

    def toggle_selection(self, selected=None):
        if selected is not None:
            self.is_selected = selected
        else:
            self.is_selected = not self.is_selected
        self.update_right_widget_color()

    def update_right_widget_color(self):
        color = self.selected_color if self.is_selected else self.unselected_color
        self.right_widget.setStyleSheet(f"background-color: {color.name()};")

    def get_title(self):
        return self.title

    def get_selected(self):
        return self.is_selected
