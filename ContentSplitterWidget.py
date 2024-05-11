from PyQt5.QtWidgets import QWidget, QHBoxLayout, QSplitter
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QPalette
from ColoredWidget import ColoredWidget

class ContentSplitterWidget(QWidget):
    def __init__(
            self, 
            parent=None, 
            orientation=Qt.Horizontal, 
            fixed_panel='first', 
            initial_sizes=(200, 600), 
            colors=("green", "yellow")
            ):
        # 初始化ContentSplitterWidget
        super().__init__(parent)

        self.orientation = orientation
        self.fixed_panel = fixed_panel
        self.initial_sizes = initial_sizes
        self.colors = {"panel1": QColor(colors[0]), "panel2": QColor(colors[1])}

        self.init_ui()

    def init_ui(self):
        # 初始化ContentSplitterWidget的UI
        self.content_splitter = QSplitter(self.orientation, self)
        self.panel1 = ColoredWidget(self.colors["panel1"], parent=self)
        self.panel2 = ColoredWidget(self.colors["panel2"], parent=self)
        
        # 將panel1和panel2添加到content_splitter中
        self.content_splitter.addWidget(self.panel1)
        self.content_splitter.addWidget(self.panel2)
        self.content_splitter.setSizes(list(self.initial_sizes))

        # 將content_splitter添加到layout中
        self.layout = QHBoxLayout(self)
        self.setZeroMarginsAndSpacing(self.layout)
        self.layout.addWidget(self.content_splitter)

        # 設置content_splitter的handle寬度
        self.content_splitter.splitterMoved.connect(self.update_panel_size)

    def update_panel_size(self):
        # 判斷固定的panel是哪一個
        if self.orientation == Qt.Horizontal and self.fixed_panel == 'first':
            self.initial_sizes = (self.panel1.width(), self.initial_sizes[1])
        elif self.orientation == Qt.Horizontal and self.fixed_panel == 'second':
            self.initial_sizes = (self.initial_sizes[0], self.panel2.width())
        elif self.orientation == Qt.Vertical and self.fixed_panel == 'first':
            self.initial_sizes = (self.panel1.height(), self.initial_sizes[1])
        else:
            self.initial_sizes = (self.initial_sizes[0], self.panel2.height())

    def resizeEvent(self, event):
        # 調整panel的尺寸
        super().resizeEvent(event)
        self.adjust_panels()

    def adjust_panels(self):
        # 依照固定panel的大小調整另外一個panel的尺寸
        total_length = self.width() if self.orientation == Qt.Horizontal else self.height()
        handle_width = self.content_splitter.handleWidth()
        if self.fixed_panel == 'first':
            second_panel_length = total_length - self.initial_sizes[0] - handle_width
            sizes = [self.initial_sizes[0], second_panel_length]
        else:
            first_panel_length = total_length - self.initial_sizes[1] - handle_width
            sizes = [first_panel_length, self.initial_sizes[1]]
        self.content_splitter.setSizes(sizes)

    def setZeroMarginsAndSpacing(self, layout):
        # 設置佈局的邊距和間距
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

    def get_panel1(self):
        # 獲取panel1
        return self.panel1

    def get_panel2(self):
        # 獲取panel2
        return self.panel2
