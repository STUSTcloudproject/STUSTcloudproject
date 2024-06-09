from PyQt5.QtWidgets import QPushButton, QApplication
from PyQt5.QtGui import QIcon, QColor
from PyQt5.QtCore import Qt, QSize
from custom_widgets.ColoredWidget import ColoredWidget

class ButtonWidget(ColoredWidget):
    def __init__(self, name, owner, color, icon=None, callback=None, size=None, orientation=Qt.Horizontal, add_position=None, parent=None):
        """
        初始化 ButtonWidget。

        參數:
        name (str): 按鈕的名稱。
        owner (str): 按鈕的擁有者。
        color (str): 按鈕的顏色。
        icon (str, optional): 圖標的路徑。預設為 None。
        callback (callable, optional): 按鈕點擊的回調函式。預設為 None。
        size (int, optional): 按鈕的大小。預設為 None。
        orientation (Qt.Orientation, optional): 按鈕的方向。預設為 Qt.Horizontal。
        add_position (int, optional): 按鈕在佈局中的添加位置。預設為 None。
        parent (QWidget, optional): 父級窗口。預設為 None。
        """
        # 初始化 ColoredWidget
        super().__init__(QColor(color), size, orientation, add_position, parent)

        self.owner = owner
        self.name = name
        self.button = QPushButton("")
        self.button.setFixedSize(size, size)

        if callback:
            self.button.clicked.connect(lambda: self._emit_button_info(callback))

        if icon:
            self.setButtonIcon(icon)
        
        # 設置按鈕的樣式
        self.set_button_style(color)
        
        self.addToLayout(self.button)

    def setButtonIcon(self, icon_path):
        """
        設置按鈕的圖標。

        參數:
        icon_path (str): 圖標的路徑。
        """
        # 根據按鈕名稱自定義圖標縮放大小
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
        """
        設置按鈕的回調函數。

        參數:
        callback (callable): 按鈕點擊的回調函式。
        """
        self.button.clicked.connect(callback)

    def set_button_style(self, color):
        """
        設置按鈕的樣式。

        參數:
        color (str): 按鈕的顏色。
        """
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
        """
        發送按鈕信息。

        參數:
        callback (callable): 按鈕點擊的回調函式。
        """
        info = {'name': self.name, 'owner': self.owner}
        callback(info)  # 使用信息字典調用回調函式
