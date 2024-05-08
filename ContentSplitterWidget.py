from PyQt5.QtWidgets import QWidget, QHBoxLayout, QSplitter
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QPalette

class ContentSplitterWidget(QWidget):
    def __init__(self, parent=None, orientation=Qt.Horizontal, fixed_panel='first', initial_sizes=(200, 600)):
        super().__init__(parent)
        self.orientation = orientation
        self.fixed_panel = fixed_panel
        self.initial_sizes = initial_sizes
        self.init_ui()

    def init_ui(self):
        self.content_splitter = QSplitter(self.orientation, self)
        self.panel1 = self.create_colored_widget(QColor("green"))
        self.panel2 = self.create_colored_widget(QColor("yellow"))

        self.content_splitter.addWidget(self.panel1)
        self.content_splitter.addWidget(self.panel2)
        self.content_splitter.setSizes(list(self.initial_sizes))

        layout = QHBoxLayout()
        self.setLayout(layout)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.content_splitter)

        self.content_splitter.splitterMoved.connect(self.update_panel_size)

    def create_colored_widget(self, color, fixed_width=None):
        widget = QWidget()
        palette = QPalette()
        palette.setColor(QPalette.Window, color)
        widget.setPalette(palette)
        widget.setAutoFillBackground(True)

        # 确保每个 widget 都有一个布局
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        widget.setLayout(layout)

        if fixed_width is not None:
            widget.setFixedWidth(fixed_width)

        return widget

    def update_panel_size(self):
        if self.orientation == Qt.Horizontal and self.fixed_panel == 'first':
            self.initial_sizes = (self.panel1.width(), self.initial_sizes[1])
        elif self.orientation == Qt.Horizontal and self.fixed_panel == 'second':
            self.initial_sizes = (self.initial_sizes[0], self.panel2.width())
        elif self.orientation == Qt.Vertical and self.fixed_panel == 'first':
            self.initial_sizes = (self.panel1.height(), self.initial_sizes[1])
        else:
            self.initial_sizes = (self.initial_sizes[0], self.panel2.height())

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.adjust_panels()

    def adjust_panels(self):
        total_length = self.width() if self.orientation == Qt.Horizontal else self.height()
        handle_width = self.content_splitter.handleWidth()
        if self.fixed_panel == 'first':
            second_panel_length = total_length - self.initial_sizes[0] - handle_width
            sizes = [self.initial_sizes[0], second_panel_length]
        else:
            first_panel_length = total_length - self.initial_sizes[1] - handle_width
            sizes = [first_panel_length, self.initial_sizes[1]]
        self.content_splitter.setSizes(sizes)
    def setPanel1Content(self, widget):
        # 清空当前面板的所有子控件
        for i in reversed(range(self.panel1.layout().count())):
            self.panel1.layout().itemAt(i).widget().setParent(None)
        # 设置新的内容
        self.panel1.layout().addWidget(widget)

    def setPanel2Content(self, widget):
        # 清空当前面板的所有子控件
        for i in reversed(range(self.panel2.layout().count())):
            self.panel2.layout().itemAt(i).widget().setParent(None)
        # 设置新的内容
        self.panel2.layout().addWidget(widget)
# The code to initialize and run a QApplication is the same as before, omitted here for brevity.
