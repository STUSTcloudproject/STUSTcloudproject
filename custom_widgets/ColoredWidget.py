from PyQt5.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout
from PyQt5.QtGui import QPalette
from PyQt5.QtCore import Qt

class ColoredWidget(QWidget):
    def __init__(self, color=None, size=None, orientation=Qt.Horizontal, add_position=None, parent=None):
        """
        初始化 ColoredWidget。

        參數:
        color (QColor, optional): 小工具的背景顏色。預設為 None。
        size (int, optional): 小工具的大小。預設為 None。
        orientation (Qt.Orientation, optional): 小工具的佈局方向。預設為 Qt.Horizontal。
        add_position (Qt.AlignmentFlag, optional): 小工具在佈局中的對齊方式。預設為 None。
        parent (QWidget, optional): 父級窗口。預設為 None。
        """
        super().__init__(parent)

        self.orientation = orientation
        self.add_position = add_position
        self.setAutoFillBackground(True)  # 設置自動填充背景
        if color is not None:
            self.setPalette(self.get_palette(color))  # 設置調色板

        # 設置固定尺寸
        if size is not None:
            if orientation == Qt.Horizontal:
                self.setFixedHeight(size)
            else:
                self.setFixedWidth(size)
                
        self.setup_layout()  # 初始化佈局

    def setup_layout(self):
        """
        初始化佈局，根據方向設置為水平佈局或垂直佈局。
        """
        if self.orientation == Qt.Horizontal:
            self.layout = QHBoxLayout(self)
        else:
            self.layout = QVBoxLayout(self)

        # 設置佈局的對齊方式
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

        self.setZeroMarginsAndSpacing(self.layout)  # 設置佈局的邊距和間距為零

    def get_palette(self, color):
        """
        獲取調色板。

        參數:
        color (QColor): 要設置的顏色。

        回傳:
        QPalette: 設置了指定顏色的調色板。
        """
        palette = QPalette()
        palette.setColor(QPalette.Window, color)
        return palette

    def addToLayout(self, widget):
        """
        將小工具添加到佈局中。

        參數:
        widget (QWidget): 要添加的小工具。
        """
        self.layout.addWidget(widget)

    def removeAllWidgets(self):
        """
        移除佈局中的所有小工具。
        """
        while self.layout.count():
            child = self.layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def clearAndAddWidget(self, widget=None):
        """
        清除佈局中的所有小工具，然後添加指定的小工具。

        參數:
        widget (QWidget, optional): 要添加的小工具。預設為 None。
        """
        self.removeAllWidgets()
        if widget:
            self.addToLayout(widget)

    def countWidgets(self):
        """
        獲取佈局中小工具的數量。

        回傳:
        int: 佈局中小工具的數量。
        """
        return self.layout.count()

    def setColor(self, color):
        """
        設置小工具的背景顏色。

        參數:
        color (QColor): 要設置的顏色。
        """
        self.setPalette(self.get_palette(color))

    def setZeroMarginsAndSpacing(self, layout):
        """
        設置佈局的邊距和間距為零。

        參數:
        layout (QLayout): 要設置的佈局。
        """
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

    def setWidgetVisibility(self, visible):
        """
        設置佈局中所有小工具的可見性。

        參數:
        visible (bool): 是否可見。
        """
        for i in range(self.layout.count()):
            widget = self.layout.itemAt(i).widget()
            if widget:
                widget.setVisible(visible)
