from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout, QTextEdit
from PyQt5.QtCore import Qt

class TextDisplayPanel(QWidget):
    def __init__(self, parent=None, title="title", content="content", background_color="#1E1E1E", font_color="#DCDCDC", title_font_size="18pt", content_font_size="12pt"):
        """
        初始化 TextDisplayPanel。

        參數:
        parent (QWidget, optional): 父級窗口。預設為 None。
        title (str, optional): 顯示的標題。預設為 "title"。
        content (str, optional): 顯示的內容。預設為 "content"。
        background_color (str, optional): 背景顏色。預設為 "#1E1E1E"。
        font_color (str, optional): 字體顏色。預設為 "#DCDCDC"。
        title_font_size (str, optional): 標題字體大小。預設為 "18pt"。
        content_font_size (str, optional): 內容字體大小。預設為 "12pt"。
        """
        super().__init__(parent)
        self.title = title
        self.content = content
        self.background_color = background_color
        self.font_color = font_color
        self.title_font_size = title_font_size
        self.content_font_size = content_font_size
        self.initUI()
    
    def initUI(self):
        """
        初始化用戶界面。
        """
        # 設置總佈局
        layout = QVBoxLayout(self)
        self.setStyleSheet(f"background-color: {self.background_color};")
        
        # 創建標題小工具並設置屬性
        self.title_widget = QWidget(self)
        self.title_layout = QVBoxLayout(self.title_widget)
        self.title_label = QLabel(self.title, self.title_widget)
        self.title_label.setStyleSheet(f"""
            font-size: {self.title_font_size};
            font-weight: bold;
            color: {self.font_color};
            font-family: 'Consolas', 'Courier New', 'Lucida Console', monospace;
        """)
        self.title_layout.addWidget(self.title_label)
        self.title_widget.setLayout(self.title_layout)
        
        # 創建內容小工具並設置屬性
        self.content_widget = QWidget(self)
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_text = QTextEdit(self.content_widget)
        self.content_text.setReadOnly(True)  # 設置為只讀
        self.content_text.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)  # 根據需要顯示垂直滾動條
        self.content_text.setStyleSheet(f"""
            background-color: {self.background_color};
            color: {self.font_color};
            border: none;
            font-size: {self.content_font_size};
            font-family: 'Consolas', 'Courier New', 'Lucida Console', monospace;
        """)
        self.content_text.setMarkdown(self.content)  # 設置內容為 Markdown 格式
        self.content_layout.addWidget(self.content_text)
        self.content_widget.setLayout(self.content_layout)

        layout.addWidget(self.title_widget)
        layout.addWidget(self.content_widget)
        self.setLayout(layout)

# 主程序執行
if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    panel = TextDisplayPanel(
        title="Markdown Content",
        content="## Heading 1\nHere is some **bold text** and *italic text*.\n\n- Bullet list item 1\n- Bullet list item 2",
        background_color="#1E1E1E",
        font_color="#DCDCDC",
        title_font_size="24pt",
        content_font_size="12pt"
    )
    panel.show()
    sys.exit(app.exec_())
