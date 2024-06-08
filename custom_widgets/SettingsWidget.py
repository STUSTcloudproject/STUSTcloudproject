from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel
from PyQt5.QtGui import QFont, QColor
from PyQt5.QtCore import Qt
from custom_widgets.ColoredWidget import ColoredWidget

class SettingsWidget(QWidget):
    def __init__(self, title, description, group_name, parent=None):
        """
        初始化 SettingsWidget。

        參數:
        title (str): 設定項的標題。
        description (str): 設定項的描述。
        group_name (str): 設定項所屬的分組名稱。
        parent (QWidget, optional): 父級窗口。預設為 None。
        """
        super().__init__(parent)
        self.unselected_color = QColor(200, 200, 200)  # 未選中狀態的顏色
        self.selected_color = QColor(0, 120, 215)  # 選中狀態的亮藍色
        self.title = title
        self.group_name = group_name
        self.is_selected = False  # 初始狀態為未選中
        self.setup_layout()
        self.setup_left_widget(title, description)
        self.setup_right_widget()

    def setup_layout(self):
        """
        初始化佈局。
        """
        self.layout = QHBoxLayout(self)
        self.setStyleSheet("background-color: transparent;")

    def setup_left_widget(self, title, description):
        """
        初始化左側小工具，包含標題和描述。

        參數:
        title (str): 設定項的標題。
        description (str): 設定項的描述。
        """
        self.left_widget = ColoredWidget(parent=self, orientation=Qt.Vertical)
        titleLabel = self.create_label(title, 14, True, "white")  # 創建標題標籤
        descriptionLabel = self.create_label(description, 10, False, "white")  # 創建描述標籤
        self.left_widget.addToLayout(titleLabel)
        self.left_widget.addToLayout(descriptionLabel)
        self.layout.addWidget(self.left_widget)

    def setup_right_widget(self):
        """
        初始化右側小工具，顯示選中狀態。
        """
        self.right_widget = ColoredWidget(parent=self, orientation=Qt.Vertical)
        self.update_right_widget_color()  # 設置初始顏色
        spaceLabel = QLabel("", self)  # 添加空白標籤以創建間距
        spaceLabel.setFixedWidth(5)
        self.right_widget.addToLayout(spaceLabel)
        self.layout.addStretch(1)
        self.layout.addWidget(self.right_widget)

    def create_label(self, text, point_size, bold, color):
        """
        創建標籤。

        參數:
        text (str): 標籤文本。
        point_size (int): 字體大小。
        bold (bool): 是否加粗。
        color (str): 字體顏色。

        回傳:
        QLabel: 創建的標籤。
        """
        label = QLabel(text, self)
        font = QFont()
        font.setPointSize(point_size)
        font.setBold(bold)
        font.setFamily("Consolas, 'Courier New', 'Lucida Console', monospace")
        label.setFont(font)
        label.setStyleSheet(f"color: {color};")
        return label

    def toggle_selection(self, selected=None):
        """
        切換選中狀態。

        參數:
        selected (bool, optional): 指定的選中狀態。若為 None，則切換當前狀態。
        """
        if selected is not None:
            self.is_selected = selected
        else:
            self.is_selected = not self.is_selected
        self.update_right_widget_color()

    def update_right_widget_color(self):
        """
        更新右側小工具的背景顏色。
        """
        color = self.selected_color if self.is_selected else self.unselected_color
        self.right_widget.setStyleSheet(f"background-color: {color.name()};")

    def get_title(self):
        """
        獲取標題。

        回傳:
        str: 標題。
        """
        return self.title

    def get_selected(self):
        """
        獲取選中狀態。

        回傳:
        bool: 是否選中。
        """
        return self.is_selected

    def get_group_name(self):
        """
        獲取分組名稱。

        回傳:
        str: 分組名稱。
        """
        return self.group_name

    def setWidgetVisibility(self, visible):
        """
        設置小工具的可見性。

        參數:
        visible (bool): 是否可見。
        """
        self.setVisible(visible)
