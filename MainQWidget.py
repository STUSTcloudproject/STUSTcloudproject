from PyQt5.QtWidgets import QApplication, QWidget, QHBoxLayout, QVBoxLayout, QPushButton
from PyQt5.QtGui import QColor, QPalette
from PyQt5.QtCore import QSize, Qt
from ContentSplitterWidget import ContentSplitterWidget
from ColoredWidget import ColoredWidget

class MainQWidget(QWidget):
    def __init__(self, parent=None, colors=("blue", "green", "yellow"), sizes=(70, 200, 600), orientations=(Qt.Horizontal, Qt.Horizontal, Qt.Vertical), fixed_panel='first'):
        super().__init__(parent)
        self.colors = {"panel1": QColor(colors[0]), "splitter1": QColor(colors[1]), "splitter2": QColor(colors[2])}
        self.panel_pixel = sizes[0]
        self.initial_sizes = (sizes[1], sizes[2])
        self.splitter_orientation, self.layout_orientation, self.panel1_orientation = orientations
        self.fixed_panel = fixed_panel

        self.setupLayout()

    def setupLayout(self):
        self.layout = QHBoxLayout(self) if self.layout_orientation == Qt.Horizontal else QVBoxLayout(self)
        self.setZeroMarginsAndSpacing(self.layout)

        if self.panel1_orientation == Qt.Horizontal:
            position = Qt.AlignRight
        else:
            position = Qt.AlignTop
            
        self.panel1 = ColoredWidget(self.colors["panel1"], size=self.panel_pixel, orientation=self.panel1_orientation, add_position=position, parent=self)
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
    
    def set_panel2_Content(self, panel_num, widget):
        if panel_num == 1:
            self.panel2.setPanel1Content(widget)
        else:   
            self.panel2.setPanel2Content(widget)

    def addColoredSquareToPanel1(self, color, size=50):
        """Adds a colored square to panel1, which contains a 50x50 button."""
        # 创建 ColoredWidget 实例，颜色和尺寸根据参数设置
        colored_square = ColoredWidget(QColor(color), size=size, orientation=self.layout_orientation, parent=self.panel1)
        
        # 创建一个按钮，设置固定大小
        button = QPushButton("")
        button.setFixedSize(size, size)  # 设置按钮的固定大小
        
        # 将按钮添加到 colored_square 中
        colored_square.addToLayout(button)

        # 将 ColoredWidget 实例添加到 panel1 的布局中
        self.panel1.addToLayout(colored_square)