from PyQt5.QtWidgets import QApplication, QWidget, QHBoxLayout, QVBoxLayout, QPushButton
from PyQt5.QtGui import QColor, QPalette
from PyQt5.QtCore import QSize, Qt
from custom_widgets.ContentSplitterWidget import ContentSplitterWidget
from custom_widgets.ColoredWidget import ColoredWidget

class MainQWidget(QWidget):
    def __init__(
            self, 
            parent=None, 
            self_color = (255, 255, 255),
            colors=((0, 0, 255), (0, 255, 0), (255, 255, 0)), 
            sizes=(70, 200, 600), 
            orientations=(Qt.Horizontal, Qt.Horizontal, Qt.Vertical), 
            fixed_panel='first'
            ):
        # 初始化主界面
        super().__init__(parent)
        
        self.self_color = QColor(*self_color)
        self.colors = {"panel1": QColor(*colors[0]), "splitter1": QColor(*colors[1]), "splitter2": QColor(*colors[2])}
        self.panel_pixel = sizes[0]
        self.initial_sizes = (sizes[1], sizes[2])
        self.splitter_orientation, self.layout_orientation, self.panel1_orientation = orientations
        self.fixed_panel = fixed_panel

        self.setupLayout()
        self.setSelfBackgroundColor()

    def setupLayout(self):
        # 初始化主界面的布局
        self.layout = QHBoxLayout(self) if self.layout_orientation == Qt.Horizontal else QVBoxLayout(self)
        self.setZeroMarginsAndSpacing(self.layout)

        if self.panel1_orientation == Qt.Horizontal:
            position = Qt.AlignRight
        else:
            position = Qt.AlignTop
            
        self.panel1 = ColoredWidget(color = self.colors["panel1"], size=self.panel_pixel, orientation=self.panel1_orientation, add_position=position, parent=self)
        self.panel2 = ContentSplitterWidget(self, orientation=self.splitter_orientation, fixed_panel=self.fixed_panel, initial_sizes=self.initial_sizes, colors=(self.colors["splitter1"], self.colors["splitter2"]))

        self.layout.addWidget(self.panel1)
        self.layout.addWidget(self.panel2, 1)

    def setSelfBackgroundColor(self):
        # 使用 QPalette 设置自身背景颜色
        palette = self.palette()
        palette.setColor(QPalette.Window, self.self_color)
        self.setPalette(palette)

    def setZeroMarginsAndSpacing(self, layout):
        # 設置layout的邊距和間距
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

    def get_panel1(self):
        # 獲取panel1
        return self.panel1

    def get_panel2(self):
        # 獲取panel2
        return self.panel2