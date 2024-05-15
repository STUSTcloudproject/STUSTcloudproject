from PyQt5.QtWidgets import QPushButton, QApplication
from PyQt5.QtGui import QIcon, QColor
from PyQt5.QtCore import Qt, QSize
from custom_widgets.ColoredWidget import ColoredWidget

class ButtonWidget(ColoredWidget):
    def __init__(
            self, 
            name, 
            owner, 
            color, 
            icon=None, 
            callback=None, 
            size=None, 
            orientation=Qt.Horizontal, 
            add_position=None, 
            parent=None
            ):
        # 初始化ButtonWidget
        super().__init__(QColor(color), size, orientation, add_position, parent)

        self.owner = owner
        self.name = name
        self.button = QPushButton("")
        self.button.setFixedSize(size, size)

        if callback:
            self.button.clicked.connect(lambda: self._emit_button_info(callback))

        if icon:
            self.setButtonIcon(icon)
        
        # 设置按钮的样式
        self.set_button_style(color)
        
        self.addToLayout(self.button)

    def setButtonIcon(self, icon_path):
        # 根据按钮名称自定义图标缩放大小
        scale_factors = {
            "Home": 1.0,
            "Record": 0.65,
            "RunSystem": 0.8,
            "View": 1.0,
            "start": 0.75,
            "stop": 0.75,
            "record": 0.6,
        }
        
        scale_factor = scale_factors.get(self.name, 1.0)
        icon_size = QSize(int(self.button.size().width() * scale_factor), int(self.button.size().height() * scale_factor))
        
        icon = QIcon(icon_path)
        self.button.setIcon(icon)
        self.button.setIconSize(icon_size)

    def setButtonCallback(self, callback):
        # 設置按鈕的回調函數
        self.button.clicked.connect(callback)

    def set_button_style(self, color):
        # 设置按钮的样式
        if color == "transparent":
            self.button.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    border: none;
                }
                QPushButton:hover {
                    background-color: rgba(255, 255, 255, 0.3);
                    border: none;
                }
                QPushButton:focus {
                    background-color: rgba(255, 255, 255, 0.3);
                    border: none;
                }
            """)
        else:
            self.button.setStyleSheet(f"""
                QPushButton {{
                    background-color: {color};
                }}
                QPushButton:hover {{
                    background-color: rgba(255, 255, 255, 0.3);
                    border: none;
                }}
                QPushButton:focus {{
                    background-color: rgba(255, 255, 255, 0.3);
                    border: none;
                }}
            """)

    def _emit_button_info(self, callback):
        # 發送按鈕信息
        info = {'name': self.name, 'owner': self.owner}
        callback(info)  # Call the callback with the info dictionary