from PyQt5.QtWidgets import QWidget, QHBoxLayout, QSplitter
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from custom_widgets.ColoredWidget import ColoredWidget

class ContentSplitterWidget(QWidget):
    def __init__(self, parent=None, orientation=Qt.Horizontal, fixed_panel='first', initial_sizes=(200, 600), colors=("green", "yellow")):
        """
        初始化 ContentSplitterWidget。

        參數:
        parent (QWidget, optional): 父級窗口。預設為 None。
        orientation (Qt.Orientation, optional): 分割方向。預設為 Qt.Horizontal。
        fixed_panel (str, optional): 固定面板。'first' 或 'second'。預設為 'first'。
        initial_sizes (tuple, optional): 初始大小。預設為 (200, 600)。
        colors (tuple, optional): 面板顏色。預設為 ("green", "yellow")。
        """
        super().__init__(parent)

        self.orientation = orientation
        self.fixed_panel = fixed_panel
        self.initial_sizes = initial_sizes
        self.colors = {"panel1": QColor(colors[0]), "panel2": QColor(colors[1])}

        self.init_ui()

    def init_ui(self):
        """
        初始化 ContentSplitterWidget 的 UI。
        """
        panel_orientation = Qt.Vertical if self.orientation == Qt.Vertical else Qt.Horizontal
        self.content_splitter = QSplitter(self.orientation, self)
        self.panel1 = ColoredWidget(color=self.colors["panel1"], parent=self, orientation=panel_orientation)
        self.panel2 = ColoredWidget(color=self.colors["panel2"], parent=self, orientation=panel_orientation)
        
        # 將 panel1 和 panel2 添加到 content_splitter 中
        self.content_splitter.addWidget(self.panel1)
        self.content_splitter.addWidget(self.panel2)
        self.content_splitter.setSizes(list(self.initial_sizes))

        # 將 content_splitter 添加到 layout 中
        self.layout = QHBoxLayout(self)
        self.setZeroMarginsAndSpacing(self.layout)
        self.layout.addWidget(self.content_splitter)

        # 設置 content_splitter 的 handle 寬度變動監聽
        self.content_splitter.splitterMoved.connect(self.update_panel_size)

    def update_panel_size(self):
        """
        更新面板大小。
        """
        if self.orientation == Qt.Horizontal and self.fixed_panel == 'first':
            self.initial_sizes = (self.panel1.width(), self.initial_sizes[1])
        elif self.orientation == Qt.Horizontal and self.fixed_panel == 'second':
            self.initial_sizes = (self.initial_sizes[0], self.panel2.width())
        elif self.orientation == Qt.Vertical and self.fixed_panel == 'first':
            self.initial_sizes = (self.panel1.height(), self.initial_sizes[1])
        else:
            self.initial_sizes = (self.initial_sizes[0], self.panel2.height())

    def resizeEvent(self, event):
        """
        處理調整大小事件。

        參數:
        event (QResizeEvent): 調整大小事件。
        """
        super().resizeEvent(event)
        self.adjust_panels()

    def adjust_panels(self):
        """
        根據固定面板的大小調整另一個面板的尺寸。
        """
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
        """
        設置佈局的邊距和間距為零。

        參數:
        layout (QLayout): 佈局。
        """
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

    def get_panel1(self):
        """
        獲取 panel1。

        回傳:
        ColoredWidget: 第一個面板。
        """
        return self.panel1

    def get_panel2(self):
        """
        獲取 panel2。

        回傳:
        ColoredWidget: 第二個面板。
        """
        return self.panel2
