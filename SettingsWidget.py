from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt5.QtGui import QFont

class SettingsWidget(QWidget):
    def __init__(self, title, description, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        
        # 创建标题标签
        self.titleLabel = QLabel(title, self)
        titleFont = QFont()
        titleFont.setPointSize(14)  # 标题字体大小
        titleFont.setBold(True)  # 标题加粗
        self.titleLabel.setFont(titleFont)
        self.titleLabel.setStyleSheet("color: white;")  # 标题字体颜色为白色

        # 创建描述标签
        self.descriptionLabel = QLabel(description, self)
        descriptionFont = QFont()
        descriptionFont.setPointSize(10)  # 描述字体大小
        self.descriptionLabel.setFont(descriptionFont)
        self.descriptionLabel.setStyleSheet("color: white;")  # 描述字体颜色为白色

        self.layout.addWidget(self.titleLabel)
        self.layout.addWidget(self.descriptionLabel)
        self.setStyleSheet("background-color: transparent;")  # 设置背景透明

