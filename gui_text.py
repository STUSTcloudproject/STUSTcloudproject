import sys
from PyQt5.QtWidgets import QApplication, QVBoxLayout, QWidget
from PyQt5.QtGui import QColor
from PyQt5.QtCore import QSize, Qt
from MainQWidget import MainQWidget

class MainInterface(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        # 主界面的配置，這裡直接使用tuple來傳遞顏色和尺寸
        self.main_layout_widget = MainQWidget(self, 
                                              colors=("blue", "green", "yellow"), 
                                              sizes=(70, 200, 600), 
                                              orientations=(Qt.Horizontal, Qt.Horizontal), 
                                              fixed_panel='first')

        # 嵌套的MainQWidget實例，用於設置panel2的內容
        nested_widget = MainQWidget(self, 
                                    colors=("purple", "red", "orange"), 
                                    sizes=(50, 0, 150), 
                                    orientations=(Qt.Vertical, Qt.Vertical), 
                                    fixed_panel='second')

        # 將nested_widget設為panel2的內容
        self.main_layout_widget.get_panel2().setPanel2Content(nested_widget)

        # 設置佈局
        layout = QVBoxLayout(self)
        self.setZeroMarginsAndSpacing(layout)
        layout.addWidget(self.main_layout_widget)
        self.setLayout(layout)

    def sizeHint(self):
        return QSize(800, 600)
    
    def setZeroMarginsAndSpacing(self, layout):
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

# Running the application
app = QApplication(sys.argv)
main_interface = MainInterface()
main_interface.show()
sys.exit(app.exec_())
