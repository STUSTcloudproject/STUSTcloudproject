from PyQt5.QtWidgets import QMessageBox, QApplication
from PyQt5.QtGui import QColor

class ErrorDialog(QMessageBox):
    def __init__(self, parent=None, title="Error", message="An error has occurred.", background_color="#FF0000"):
        """
        初始化 ErrorDialog。

        參數:
        parent (QWidget, optional): 父級窗口。預設為 None。
        title (str, optional): 對話框標題。預設為 "Error"。
        message (str, optional): 錯誤信息。預設為 "An error has occurred."。
        background_color (str, optional): 背景顏色。預設為 "#FF0000"。
        """
        super().__init__(parent)
        self.setWindowTitle(title)  # 設置對話框標題
        self.setIcon(QMessageBox.Warning)  # 設置圖標為警告圖標
        self.setStandardButtons(QMessageBox.Ok)  # 設置標準按鈕為 Ok
        self.setText(message)  # 設置錯誤信息
        self.set_background_color(background_color)  # 設置背景顏色

    def set_background_color(self, color):
        """
        設置對話框的背景顏色。

        參數:
        color (str): 背景顏色的十六進制字符串。
        """
        self.setStyleSheet(f"""
            QMessageBox {{
                background-color: {color};
                color: white;
            }}
            QMessageBox QLabel {{
                color: white;
            }}
        """)

# 範例使用
if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    dialog = ErrorDialog(title="Validation Error", message="An error occurred during validation.", background_color="#1E1E1E")
    dialog.show()
    app.exec_()
