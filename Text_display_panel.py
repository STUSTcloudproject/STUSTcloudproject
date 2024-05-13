from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout, QTextEdit
from PyQt5.QtCore import Qt

class TextDisplayPanel(QWidget):
    def __init__(self, parent=None, title="title", content="content", background_color="#1E1E1E", font_color="#DCDCDC", title_font_size="18pt", content_font_size="12pt"):
        super().__init__(parent)
        self.title = title
        self.content = content
        self.background_color = background_color
        self.font_color = font_color
        self.title_font_size = title_font_size
        self.content_font_size = content_font_size
        self.initUI()
    
    def initUI(self):
        # 设置整体布局
        layout = QVBoxLayout(self)
        self.setStyleSheet(f"background-color: {self.background_color};")
        
        # 创建标题部件和设置
        self.title_widget = QWidget(self)
        self.title_layout = QVBoxLayout(self.title_widget)
        self.title_label = QLabel(self.title, self.title_widget)
        self.title_label.setStyleSheet(f"font-size: {self.title_font_size}; font-weight: bold; color: {self.font_color};")
        self.title_layout.addWidget(self.title_label)
        self.title_widget.setLayout(self.title_layout)
        
        # 创建内容部件和设置
        self.content_widget = QWidget(self)
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_text = QTextEdit(self.content_widget)
        self.content_text.setReadOnly(True)
        self.content_text.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.content_text.setStyleSheet(f"""
            background-color: {self.background_color};
            color: {self.font_color};
            border: none;
            font-size: {self.content_font_size};
        """)
        self.content_text.setMarkdown(self.content)
        self.content_layout.addWidget(self.content_text)
        self.content_widget.setLayout(self.content_layout)

        layout.addWidget(self.title_widget)
        layout.addWidget(self.content_widget)
        self.setLayout(layout)

# 主程序运行
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
