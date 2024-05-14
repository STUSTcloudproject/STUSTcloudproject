from PyQt5.QtWidgets import QApplication, QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QTextEdit
from PyQt5.QtCore import Qt

class ConfirmDialog(QDialog):
    def __init__(self, title, selection, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.selection = selection
        
        self.initUI()
    
    def initUI(self):
        layout = QVBoxLayout()

        # 标题
        self.title_label = QLabel("Confirm Your Selection")
        self.title_label.setStyleSheet("font-size: 18pt; font-weight: bold; color: white;")
        layout.addWidget(self.title_label)

        # 显示选择项
        self.selection_text = QTextEdit()
        self.selection_text.setReadOnly(True)
        self.selection_text.setStyleSheet("background-color: #1E1E1E; color: #DCDCDC; font-size: 12pt;")
        selection_content = "\n".join(f"{key}: {value}" for key, value in self.selection.items())
        self.selection_text.setText(selection_content)
        layout.addWidget(self.selection_text)

        # 按钮布局
        button_layout = QHBoxLayout()
        self.ok_button = QPushButton("Confirm")
        self.ok_button.setStyleSheet("background-color: #333; color: white; font-weight: bold; padding: 5px;")
        self.ok_button.clicked.connect(self.accept)

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setStyleSheet("background-color: #333; color: white; font-weight: bold; padding: 5px;")
        self.cancel_button.clicked.connect(self.reject)

        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)

        layout.addLayout(button_layout)
        self.setLayout(layout)
        self.setStyleSheet("background-color: #1E1E1E; border: none;")

    def get_selection(self):
        return self.selection

# 主程序运行
if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    dialog = ConfirmDialog("Confirmation", {"Item 1": "Value 1", "Item 2": "Value 2"})
    result = dialog.exec_()
    if result == QDialog.Accepted:
        print("Confirmed:", dialog.get_selection())
    else:
        print("Cancelled")
    app.quit()  # 显式调用退出