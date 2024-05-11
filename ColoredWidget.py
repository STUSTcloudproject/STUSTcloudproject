from PyQt5.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout
from PyQt5.QtGui import QPalette
from PyQt5.QtCore import Qt

class ColoredWidget(QWidget):
    def __init__(self, color, size=None, orientation=Qt.Horizontal, add_position=None, parent=None):
        # 初始化ColoredWidget
        super().__init__(parent)
        
        self.orientation = orientation
        self.add_position = add_position
        self.setPalette(self.get_palette(color))
        self.setAutoFillBackground(True)

        # 設置固定尺寸
        if size is not None:
            if orientation == Qt.Horizontal:
                self.setFixedHeight(size)
            else:
                self.setFixedWidth(size)
                
        self.setup_layout()

    def setup_layout(self):
        # 如果是水平布局，則設置為水平布局，否則設置為垂直布局
        if self.orientation == Qt.Horizontal:
            self.layout = QHBoxLayout(self)
        else:
            self.layout = QVBoxLayout(self)

        # 設置layout的對齊方式
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

        self.setZeroMarginsAndSpacing(self.layout)

    def get_palette(self, color):
        # 獲取調色板
        palette = QPalette()
        palette.setColor(QPalette.Window, color)
        return palette

    def addToLayout(self, widget):
        # 將widget添加到layout中
        self.layout.addWidget(widget)

    def removeAllWidgets(self):
        # 移除Layout中的所有widget
        while self.layout.count():
            child = self.layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def clearAndAddWidget(self, widget=None):
        # 清除Layout中的所有widget，然後添加widget
        self.removeAllWidgets()
        if widget:
            self.addToLayout(widget)

    def countWidgets(self):
        # 獲取Layout中widget的數量
        return self.layout.count()

    def setColor(self, color):
        # 設置顏色
        self.setPalette(self.get_palette(color))
    
    def setZeroMarginsAndSpacing(self, layout):
        # 設置佈局的邊距和間距
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
